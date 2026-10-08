from __future__ import annotations

from typing import Any, TypedDict


class CrossDomainAgentState(TypedDict, total=False):
    """
    State used by the Cross-Domain Due Diligence Agent.

    The agent uses this state to investigate relationships between
    financial and legal evidence.
    """

    project_id: str
    investigation_id: str

    investigation_goal: str

    financial_findings: list[dict[str, Any]]
    legal_findings: list[dict[str, Any]]

    financial_evidence: list[dict[str, Any]]
    legal_evidence: list[dict[str, Any]]

    cross_domain_findings: list[dict[str, Any]]

    contradictions: list[dict[str, Any]]

    missing_information: list[str]

    investigation_notes: list[str]

    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]

    next_action: str | None

    investigation_complete: bool

    final_summary: str