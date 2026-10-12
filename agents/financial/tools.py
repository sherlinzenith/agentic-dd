from __future__ import annotations

import re
from typing import Any

from database.session import SessionLocal
from findings.repository import FindingRepository
from retrieval.repositories.document_repository import DocumentRepository
from retrieval.services.document_search import DocumentSearchService


_search_service = DocumentSearchService()


def search_financial_documents(
    query: str,
    project_id: str,
    limit: int = 3,
) -> dict[str, Any]:
    """
    Semantic search over financial documents for the Financial DD Agent.
    """
    actual_limit = min(limit, 3)
    results = _search_service.search(
        query=query,
        project_id=project_id,
        limit=actual_limit,
        category="financial",
    )

    compact_results = []
    for r in results:
        compact_results.append({
            "document": r.get("document_name"),
            "page": r.get("page_number"),
            "section": r.get("section"),
            "content": r.get("content"),
            "chunk_id": r.get("chunk_id"),
            "document_id": r.get("document_id"),
        })

    return {
        "status": "OK",
        "tool": "search_financial_documents",
        "query": query,
        "results": compact_results,
        "result_count": len(compact_results),
    }


def read_document_page(
    document_id: str,
    page: int,
) -> dict[str, Any]:
    """Read persisted text chunks for a specific source-document page."""

    if page < 1:
        return {
            "status": "ERROR",
            "tool": "read_document_page",
            "message": "Page numbers start at 1.",
        }

    session = SessionLocal()
    try:
        repository = DocumentRepository(session)
        document = repository.get_document(document_id)

        if document is None:
            return {
                "status": "NOT_FOUND",
                "tool": "read_document_page",
                "document_id": document_id,
                "page": page,
                "message": "Document was not found in the ingestion database.",
            }

        chunks = repository.get_document_page_chunks(document_id, page)

        if not chunks:
            return {
                "status": "NOT_FOUND",
                "tool": "read_document_page",
                "document_id": document_id,
                "document_name": document.file_name,
                "page": page,
                "message": (
                    "No persisted chunks were found for this page. "
                    "The page may be absent or the document may need re-ingestion."
                ),
            }

        return {
            "status": "OK",
            "tool": "read_document_page",
            "document_id": document.id,
            "document_name": document.file_name,
            "page": page,
            "chunks": [
                {
                    "chunk_index": chunk.chunk_index,
                    "section": chunk.section,
                    "content": chunk.content,
                }
                for chunk in chunks
            ],
            "content": "\n\n".join(chunk.content for chunk in chunks),
        }
    finally:
        session.close()


def extract_financial_table(
    document_id: str,
    table_description: str,
) -> dict[str, Any]:
    """Retrieve a persisted Docling table matching a description."""

    session = SessionLocal()
    try:
        repository = DocumentRepository(session)
        document = repository.get_document(document_id)

        if document is None:
            return {
                "status": "NOT_FOUND",
                "tool": "extract_financial_table",
                "document_id": document_id,
                "message": "Document was not found in the ingestion database.",
            }

        tables = repository.get_document_tables(document_id)

        if not tables:
            return {
                "status": "NOT_FOUND",
                "tool": "extract_financial_table",
                "document_id": document_id,
                "document_name": document.file_name,
                "message": (
                    "No persisted tables exist for this document. "
                    "Re-ingest it after table persistence is enabled."
                ),
            }

        query_terms = {
            token.lower()
            for token in re.findall(r"[a-zA-Z0-9]+", table_description or "")
            if len(token) > 1
        }

        def score(table):
            text_terms = {
                token.lower()
                for token in re.findall(r"[a-zA-Z0-9]+", table.content)
                if len(token) > 1
            }
            section_terms = {
                token.lower()
                for token in re.findall(r"[a-zA-Z0-9]+", table.section or "")
                if len(token) > 1
            }
            return len(query_terms & (text_terms | section_terms))

        ranked = sorted(tables, key=score, reverse=True)
        best_score = score(ranked[0]) if ranked else 0

        if table_description.strip() and best_score == 0 and len(tables) > 1:
            return {
                "status": "NOT_FOUND",
                "tool": "extract_financial_table",
                "document_id": document.id,
                "document_name": document.file_name,
                "table_description": table_description,
                "available_tables": [
                    {
                        "table_index": table.table_index,
                        "page_number": table.page_number,
                        "section": table.section,
                    }
                    for table in tables
                ],
                "message": (
                    "No table matched the description. Choose from the "
                    "available table metadata rather than assuming a match."
                ),
            }

        selected = ranked[0]
        return {
            "status": "OK",
            "tool": "extract_financial_table",
            "document_id": document.id,
            "document_name": document.file_name,
            "table_index": selected.table_index,
            "page_number": selected.page_number,
            "section": selected.section,
            "table_description": table_description,
            "content": selected.content,
            "match_score": best_score,
        }
    finally:
        session.close()


def calculate_metric(expression: str) -> dict[str, Any]:
    try:
        allowed = set("0123456789.+-*/()% ")

        if not expression or any(
            character not in allowed
            for character in expression
        ):
            return {
                "status": "ERROR",
                "message": "Unsupported calculation expression.",
            }

        result = eval(
            expression,
            {"__builtins__": {}},
            {},
        )

        return {
            "status": "OK",
            "expression": expression,
            "result": result,
        }

    except Exception as exc:
        return {
            "status": "ERROR",
            "expression": expression,
            "message": str(exc),
        }


def compare_periods(
    metric: str,
    period_a: str,
    value_a: float,
    period_b: str,
    value_b: float,
) -> dict[str, Any]:

    if value_a == 0:
        percentage_change = None
    else:
        percentage_change = (
            (value_b - value_a) / abs(value_a)
        ) * 100

    return {
        "status": "OK",
        "metric": metric,
        "period_a": period_a,
        "value_a": value_a,
        "period_b": period_b,
        "value_b": value_b,
        "absolute_change": value_b - value_a,
        "percentage_change": percentage_change,
    }


def reconcile_values(
    item: str,
    source_a: str,
    value_a: float,
    source_b: str,
    value_b: float,
) -> dict[str, Any]:

    difference = value_a - value_b

    return {
        "status": "OK",
        "item": item,
        "source_a": source_a,
        "value_a": value_a,
        "source_b": source_b,
        "value_b": value_b,
        "difference": difference,
        "matches": difference == 0,
    }


def search_evidence(
    query: str,
    project_id: str,
    limit: int = 3,
) -> dict[str, Any]:
    actual_limit = min(limit, 3)
    results = _search_service.search(
        query=query,
        project_id=project_id,
        limit=actual_limit,
    )

    compact_results = []
    for r in results:
        compact_results.append({
            "document": r.get("document_name"),
            "page": r.get("page_number"),
            "section": r.get("section"),
            "content": r.get("content"),
            "chunk_id": r.get("chunk_id"),
            "document_id": r.get("document_id"),
        })

    return {
        "status": "OK",
        "tool": "search_evidence",
        "query": query,
        "results": compact_results,
        "result_count": len(compact_results),
    }


def record_finding(
    title: str,
    issue: str,
    why_it_matters: str,
    conclusion: str,
    risk_level: str,
    confidence: float,
    evidence: list[dict[str, Any]],
    recommended_action: str | None = None,
    project_id: str | None = None,
    investigation_id: str | None = None,
) -> dict[str, Any]:
    target_project = project_id or "REAL-INGESTION-TEST"
    session = SessionLocal()
    try:
        from retrieval.models.investigations import DDInvestigation
        from retrieval.models.documents import Document, DocumentChunk

        valid_inv_id = None
        if investigation_id and session.get(DDInvestigation, investigation_id):
            valid_inv_id = investigation_id

        repo = FindingRepository(session)
        finding = repo.create_finding({
            "project_id": target_project,
            "investigation_id": valid_inv_id,
            "workstream": "financial",
            "agent_name": "financial_dd_agent",
            "title": title,
            "issue": issue,
            "why_it_matters": why_it_matters,
            "evidence_conclusion": conclusion,
            "recommended_action": recommended_action,
            "risk_severity": risk_level,
            "confidence": str(confidence),
            "status": "REVIEW_REQUIRED",
        })

        from retrieval.repositories.document_repository import DocumentRepository
        from services.evidence_validation_service import validate_single_evidence

        doc_repo = DocumentRepository(session)
        raw_docs = doc_repo.list_documents(target_project)
        project_docs = {d.file_name.lower(): d for d in raw_docs}
        doc_by_id = {d.id: d for d in raw_docs}

        saved_evidence = []
        for ev in (evidence or []):
            ev_doc_id = ev.get("document_id")
            if ev_doc_id and not session.get(Document, ev_doc_id):
                ev_doc_id = None

            ev_chunk_id = ev.get("chunk_id")
            if ev_chunk_id and not session.get(DocumentChunk, ev_chunk_id):
                ev_chunk_id = None

            ev_record = repo.add_evidence({
                "project_id": target_project,
                "finding_id": finding.id,
                "investigation_id": valid_inv_id,
                "document_id": ev_doc_id,
                "chunk_id": ev_chunk_id,
                "evidence_type": ev.get("evidence_type", "document"),
                "page_number": ev.get("page_number") or ev.get("page"),
                "location": ev.get("location"),
                "quoted_text": ev.get("quoted_text") or ev.get("content") or ev.get("text"),
                "extracted_value": str(ev.get("extracted_value") or ev.get("value") or ""),
                "source_label": ev.get("source_label") or ev.get("document") or ev.get("file_name"),
                "validation_status": "UNVERIFIED",
            })

            # Run deterministic validation against document chunks
            val_res = validate_single_evidence(
                ev=ev_record,
                finding=finding,
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
            "status": "PERSISTED",
            "finding_id": finding.id,
            "project_id": target_project,
            "title": title,
            "risk_level": risk_level,
            "confidence": confidence,
            "evidence_count": len(saved_evidence),
            "evidence_ids": saved_evidence,
        }
    except Exception as exc:
        repo.rollback()
        return {
            "status": "ERROR",
            "message": str(exc),
        }
    finally:
        session.close()
