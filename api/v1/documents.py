import logging
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from typing import Optional

from database.session import SessionLocal
from retrieval.repositories.project_repository import ProjectRepository
from retrieval.repositories.document_repository import DocumentRepository
from retrieval.services.document_search import DocumentSearchService
from storage.document_storage import LocalDocumentStorage
from ingestion.pipeline.document_pipeline import DocumentIngestionPipeline

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
)

storage = LocalDocumentStorage()
_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = DocumentIngestionPipeline()
    return _pipeline


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    project_id: str = Form(...),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is required.",
        )

    # Validate that the target project exists
    with SessionLocal() as db_session:
        proj_repo = ProjectRepository(db_session)
        if not proj_repo.get_project(project_id):
            raise HTTPException(
                status_code=404,
                detail=f"Project '{project_id}' not found.",
            )

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        storage_key = storage.save(
            file_name=file.filename,
            content=content,
            project_id=project_id,
        )

        pipeline = get_pipeline()
        result = pipeline.ingest(
            file_path=storage_key,
            project_id=project_id,
        )

        return {
            "success": True,
            "document": result,
            "storage_key": storage_key,
        }

    except HTTPException:
        raise

    except Exception as error:
        logger.exception("Failed to ingest document %s for project %s", file.filename, project_id)
        raise HTTPException(
            status_code=500,
            detail="Failed to ingest document. Please verify file format and try again.",
        )



class SearchRequest(BaseModel):
    query: str
    project_id: str = "REAL-INGESTION-TEST"
    limit: int = 5
    category: Optional[str] = None


class RunAgentRequest(BaseModel):
    project_id: str = "REAL-INGESTION-TEST"
    workstream: str = "financial"
    objective: str


@router.get("")
def list_documents(project_id: Optional[str] = None):
    session = SessionLocal()
    try:
        repo = DocumentRepository(session)
        docs = repo.list_documents(project_id)
        result = []
        for d in docs:
            chunks = repo.get_document_chunks(d.id)
            tables = repo.get_document_tables(d.id)
            result.append({
                "id": d.id,
                "project_id": d.project_id,
                "file_name": d.file_name,
                "category": d.category,
                "document_type": d.document_type,
                "storage_key": d.storage_key,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "chunk_count": len(chunks),
                "table_count": len(tables),
            })
        return {"documents": result, "total": len(result)}
    finally:
        session.close()


@router.get("/{document_id}/tables")
def get_document_tables(document_id: str):
    session = SessionLocal()
    try:
        repo = DocumentRepository(session)
        tables = repo.get_document_tables(document_id)
        return {
            "tables": [
                {
                    "id": t.id,
                    "table_index": t.table_index,
                    "page_number": t.page_number,
                    "section": t.section,
                    "content": t.content,
                }
                for t in tables
            ]
        }
    finally:
        session.close()


@router.post("/search")
def search_documents(request: SearchRequest):
    search_service = DocumentSearchService()
    results = search_service.search(
        query=request.query,
        project_id=request.project_id,
        limit=request.limit,
        category=request.category,
    )
    return {"query": request.query, "results": results, "count": len(results)}


@router.post("/run-agent")
def run_agent(request: RunAgentRequest):
    from agents.financial.agent import create_financial_agent
    from agents.legal.agent import create_legal_agent
    from agents.cross_domain.agent import create_cross_domain_agent
    from agents.engine.runner import AgentRunner
    from findings.repository import FindingRepository

    if request.workstream.lower() == "legal":
        agent = create_legal_agent()
    elif request.workstream.lower() in ("cross_domain", "cross-domain"):
        agent = create_cross_domain_agent()
    else:
        agent = create_financial_agent()

    runner = AgentRunner(agent=agent, max_iterations=3)
    state = runner.run(
        project_id=request.project_id,
        investigation_id=None,
        workstream=request.workstream.lower(),
        objective=request.objective,
    )

    session = SessionLocal()
    try:
        repo = FindingRepository(session)
        findings = repo.list_for_project(request.project_id)
        return {
            "status": state.get("status"),
            "iterations": state.get("iteration"),
            "tool_calls": state.get("tool_calls", []),
            "final_answer": state.get("final_answer"),
            "persisted_findings_count": len(findings),
        }
    finally:
        session.close()
