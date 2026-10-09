from __future__ import annotations

import re
from typing import Any

from database.session import SessionLocal
from retrieval.repositories.document_repository import DocumentRepository
from retrieval.services.document_search import DocumentSearchService


_search_service = DocumentSearchService()


def search_financial_documents(
    query: str,
    project_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Semantic search over financial documents for the Financial DD Agent.
    """

    results = _search_service.search(
        query=query,
        project_id=project_id,
        limit=limit,
        category="financial",
    )

    return {
        "status": "OK",
        "tool": "search_financial_documents",
        "query": query,
        "project_id": project_id,
        "results": results,
        "result_count": len(results),
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
    limit: int = 10,
) -> dict[str, Any]:

    results = _search_service.search(
        query=query,
        project_id=project_id,
        limit=limit,
    )

    return {
        "status": "OK",
        "tool": "search_evidence",
        "query": query,
        "project_id": project_id,
        "results": results,
        "result_count": len(results),
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
) -> dict[str, Any]:

    return {
        "status": "READY_FOR_PERSISTENCE",
        "title": title,
        "issue": issue,
        "why_it_matters": why_it_matters,
        "conclusion": conclusion,
        "risk_level": risk_level,
        "confidence": confidence,
        "evidence": evidence,
        "recommended_action": recommended_action,
    }
