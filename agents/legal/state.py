from __future__ import annotations

from typing import Any, TypedDict


class LegalAgentState(TypedDict, total=False):
    """
    Runtime state maintained during a legal DD investigation.
    """

    project_id: str

    investigation_goal: str

    scope: list[str]

    available_documents: list[dict[str, Any]]

    investigation_notes: list[str]

    evidence: list[dict[str, Any]]

    findings: list[dict[str, Any]]

    missing_documents: list[str]

    tool_calls: list[dict[str, Any]]

    next_action: str | None

    investigation_complete: bool

    final_summary: str