from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """
    Shared state used by DD agents.

    The state is deliberately generic so the same engine can later
    support Financial, Legal, and Cross-Domain investigations.
    """

    project_id: str
    investigation_id: str
    workstream: str

    objective: str

    messages: list[dict[str, Any]]

    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]

    evidence: list[dict[str, Any]]
    findings: list[dict[str, Any]]

    next_action: str
    status: str

    iteration: int
    max_iterations: int

    final_answer: str
