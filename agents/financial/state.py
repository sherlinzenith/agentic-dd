from __future__ import annotations

from typing import Any, TypedDict


class FinancialAgentState(TypedDict, total=False):
    """
    Runtime state used by the Financial Agent.

    There is intentionally no field such as:

        next_check = "revenue"

    or:

        step = "balance_sheet"

    The agent is free to choose its next action based on
    the objective and evidence available.
    """

    project_id: str
    investigation_id: str
    objective: str

    messages: list[dict[str, Any]]

    observations: list[str]

    evidence: list[dict[str, Any]]

    findings: list[dict[str, Any]]

    missing_information: list[str]

    unresolved_questions: list[str]

    status: str

    iteration: int
