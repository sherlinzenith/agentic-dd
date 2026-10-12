from __future__ import annotations

from typing import Any

from database.session import SessionLocal
from findings.repository import FindingRepository
from ingestion.embeddings.bge import BGEEmbeddingModel
from retrieval.repositories.document_repository import DocumentRepository


class LegalAgentTools:
    """
    Tools available to the Legal Due Diligence Agent.

    The LLM decides when to use these tools.
    The tools perform deterministic retrieval/database operations.
    """

    def __init__(self):
        self.embedder = BGEEmbeddingModel()

    def search_legal_documents(
        self,
        query: str,
        project_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Find documents in a project that are classified as legal.
        """

        session = SessionLocal()

        try:
            repository = DocumentRepository(session)
            chunks = []

            try:
                query_embedding = self.embedder.embed_query(query)
                chunks = repository.search_similar_chunks(
                    query_embedding=query_embedding,
                    project_id=project_id,
                    limit=limit,
                )
            except Exception:
                chunks = []

            # Reliable keyword search fallback if vector search produces 0 chunks
            if not chunks and query.strip():
                from sqlalchemy import select, or_
                from retrieval.models.documents import Document, DocumentChunk
                words = [w for w in query.split() if len(w) > 3]
                stmt = select(DocumentChunk).join(Document).where(
                    Document.project_id == project_id,
                    Document.category == "legal",
                )
                if words:
                    conds = [DocumentChunk.content.ilike(f"%{w}%") for w in words[:3]]
                    stmt = stmt.where(or_(*conds))
                stmt = stmt.limit(limit)
                chunks = session.scalars(stmt).all()

            results = []

            for chunk in chunks:
                document = chunk.document

                if document.category != "legal":
                    continue

                results.append(
                    {
                        "document_id": document.id,
                        "file_name": document.file_name,
                        "document_type": document.document_type,
                        "chunk_id": chunk.id,
                        "content": chunk.content,
                        "page_number": chunk.page_number,
                        "section": chunk.section,
                    }
                )

            return results

        finally:
            session.close()

    def search_contract_clause(
        self,
        clause_query: str,
        project_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search legal documents for contract language relevant to a query.

        Examples:
            change of control
            termination
            assignment
            consent
            indemnification
        """

        return self.search_legal_documents(
            query=clause_query,
            project_id=project_id,
            limit=limit,
        )

    def search_legal_evidence(
        self,
        query: str,
        project_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Semantic evidence search across legal documents.
        """

        return self.search_legal_documents(
            query=query,
            project_id=project_id,
            limit=limit,
        )

    def read_document_page(
        self,
        document_id: str,
        page_number: int,
    ) -> dict[str, Any]:
        """
        Retrieve chunks associated with a specific document page.
        """

        session = SessionLocal()

        try:
            repository = DocumentRepository(session)

            document = repository.get_document(document_id)

            if document is None:
                return {
                    "found": False,
                    "error": f"Document not found: {document_id}",
                }

            chunks = repository.get_document_chunks(
                document_id
            )

            page_chunks = [
                chunk
                for chunk in chunks
                if chunk.page_number == page_number
            ]

            return {
                "found": True,
                "document_id": document.id,
                "file_name": document.file_name,
                "page_number": page_number,
                "chunks": [
                    {
                        "chunk_id": chunk.id,
                        "content": chunk.content,
                        "section": chunk.section,
                    }
                    for chunk in page_chunks
                ],
            }

        finally:
            session.close()

    def record_finding(
        self,
        finding: dict[str, Any],
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Validate and persist a structured legal finding into PostgreSQL.
        """

        required_fields = [
            "title",
            "issue",
            "why_it_matters",
        ]

        missing = [
            field
            for field in required_fields
            if not finding.get(field)
        ]

        if missing:
            return {
                "recorded": False,
                "error": f"Missing required fields: {missing}",
            }

        target_project_id = project_id or finding.get("project_id") or "REAL-INGESTION-TEST"
        session = SessionLocal()
        try:
            repo = FindingRepository(session)
            f_record = repo.create_finding({
                "project_id": target_project_id,
                "investigation_id": finding.get("investigation_id"),
                "workstream": "legal",
                "agent_name": "legal_dd_agent",
                "title": finding["title"],
                "issue": finding["issue"],
                "why_it_matters": finding["why_it_matters"],
                "evidence_conclusion": finding.get("conclusion") or finding.get("evidence_conclusion"),
                "recommended_action": finding.get("recommended_action"),
                "risk_severity": finding.get("risk_level", "medium"),
                "confidence": str(finding.get("confidence", "high")),
                "status": "REVIEW_REQUIRED",
            })

            from retrieval.repositories.document_repository import DocumentRepository
            from services.evidence_validation_service import validate_single_evidence

            doc_repo = DocumentRepository(session)
            raw_docs = doc_repo.list_documents(target_project_id)
            project_docs = {d.file_name.lower(): d for d in raw_docs}
            doc_by_id = {d.id: d for d in raw_docs}

            evidence_items = finding.get("evidence", [])
            saved_evidence = []
            from retrieval.models.documents import Document, DocumentChunk
            for ev in (evidence_items or []):
                ev_doc_id = ev.get("document_id")
                if ev_doc_id and not session.get(Document, ev_doc_id):
                    ev_doc_id = None
                ev_chunk_id = ev.get("chunk_id")
                if ev_chunk_id and not session.get(DocumentChunk, ev_chunk_id):
                    ev_chunk_id = None

                ev_record = repo.add_evidence({
                    "project_id": target_project_id,
                    "finding_id": f_record.id,
                    "document_id": ev_doc_id,
                    "chunk_id": ev_chunk_id,
                    "evidence_type": ev.get("evidence_type", "document"),
                    "page_number": ev.get("page_number") or ev.get("page"),
                    "location": ev.get("location"),
                    "quoted_text": ev.get("quoted_text") or ev.get("content") or ev.get("text"),
                    "extracted_value": str(ev.get("extracted_value") or ev.get("value") or ""),
                    "source_label": ev.get("source_label") or ev.get("file_name"),
                    "validation_status": "UNVERIFIED",
                })

                val_res = validate_single_evidence(
                    ev=ev_record,
                    finding=f_record,
                    doc_repo=doc_repo,
                    project_docs=project_docs,
                    doc_by_id=doc_by_id,
                )
                ev_record.validation_status = val_res["status"]
                ev_record.validation_reason = val_res["reason"]
                ev_record.match_method = val_res["match_method"]
                ev_record.confidence = val_res["confidence"]
                if val_res["chunk_id"]:
                    ev_record.chunk_id = val_res["chunk_id"]
                if val_res["page_number"] and not ev_record.page_number:
                    ev_record.page_number = val_res["page_number"]
                if val_res["document_id"] and not ev_record.document_id:
                    ev_record.document_id = val_res["document_id"]

                saved_evidence.append(ev_record.id)

            repo.commit()

            return {
                "recorded": True,
                "status": "PERSISTED",
                "finding_id": f_record.id,
                "finding": finding,
                "evidence_count": len(saved_evidence),
            }
        except Exception as exc:
            repo.rollback()
            return {
                "recorded": False,
                "error": str(exc),
            }
        finally:
            session.close()

    def request_evidence(
        self,
        description: str,
        project_id: str,
    ) -> dict[str, Any]:
        """
        Create a structured evidence request.

        Persistent request storage will be connected in the
        Requests/Tasks phase.
        """

        if not description.strip():
            return {
                "created": False,
                "error": "Evidence request description is required.",
            }

        return {
            "created": True,
            "project_id": project_id,
            "description": description,
            "status": "OPEN",
        }
