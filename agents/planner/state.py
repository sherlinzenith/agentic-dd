from __future__ import annotations

from typing import Any, TypedDict


class PlannerState(TypedDict, total=False):
    # Project context
    project_id: str
    investigation_id: str

    project: dict[str, Any]
    documents: list[dict[str, Any]]
    workstreams: list[dict[str, Any]]
    scopes: dict[str, dict[str, Any]]

    # Planner objective
    objective: str

    # AI conversation
    messages: list[dict[str, Any]]

    # Agent actions
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]

    # Investigation planning
    investigation_plan: list[dict[str, Any]]
    missing_information: list[str]
    unresolved_questions: list[str]

    # Execution control
    next_action: str
    status: str
    iteration: int
    max_iterations: int

    # Final planner response
    final_answer: str