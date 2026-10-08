from __future__ import annotations

from typing import Any


def search_financial_documents(
    query: str,
    project_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Search financial-related document content.

    The implementation will later query PostgreSQL + pgvector/BGE-M3.

    This function intentionally does not decide what query to perform.
    Qwen3 decides the query.
    """

    return {
        "status": "NOT_CONNECTED",
        "tool": "search_financial_documents",
        "project_id": project_id,
        "query": query,
        "limit": limit,
        "message": (
            "Financial document retrieval is not connected yet. "
            "The production implementation will query the document "
            "and vector retrieval layer."
        ),
    }


def read_document_page(
    document_id: str,
    page: int,
) -> dict[str, Any]:
    """
    Read a specific document page.

    Qwen3 decides which document/page requires inspection.
    """

    return {
        "status": "NOT_CONNECTED",
        "tool": "read_document_page",
        "document_id": document_id,
        "page": page,
        "message": (
            "Document page retrieval will be connected to the "
            "Docling processed document store."
        ),
    }


def extract_financial_table(
    document_id: str,
    table_description: str,
) -> dict[str, Any]:
    """
    Retrieve a structured financial table from a document.

    Qwen3 decides whether a table is required and describes what
    it needs.
    """

    return {
        "status": "NOT_CONNECTED",
        "tool": "extract_financial_table",
        "document_id": document_id,
        "table_description": table_description,
        "message": (
            "Structured table extraction will be connected to the "
            "Docling document representation."
        ),
    }


def calculate_metric(
    expression: str,
) -> dict[str, Any]:
    """
    Deterministic financial calculation tool.

    The agent chooses the expression.
    Python performs the arithmetic.
    """

    try:
        allowed = set(
            "0123456789.+-*/()% "
        )

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
            {
                "__builtins__": {},
            },
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
    """
    Deterministically compare two values.

    The agent decides which metric and periods matter.
    """

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
    """
    Compare values reported by different sources.

    The agent decides which values need reconciliation.
    """

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
    """
    Search for supporting evidence across the project.

    This will later use the shared evidence/retrieval layer.
    """

    return {
        "status": "NOT_CONNECTED",
        "tool": "search_evidence",
        "project_id": project_id,
        "query": query,
        "limit": limit,
        "message": (
            "Evidence retrieval will be connected to PostgreSQL "
            "and pgvector."
        ),
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
    """
    Record a finding produced by the agent.

    Persistence will later be handled by the findings repository.
    """

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
