from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class InvestigationTask(BaseModel):
    task_id: str = Field(
        description="Unique identifier for this investigation task."
    )

    title: str = Field(
        description="Short name of the investigation task."
    )

    description: str = Field(
        description="What the agent needs to investigate."
    )

    workstream: Literal[
        "financial",
        "legal",
        "cross_domain",
    ]

    priority: Literal[
        "high",
        "medium",
        "low",
    ] = "medium"

    objective: str = Field(
        description="The specific question this task should answer."
    )

    required_evidence: list[str] = Field(
        default_factory=list,
        description="Evidence needed to complete the task."
    )

    assigned_agent: Literal[
        "financial_agent",
        "legal_agent",
        "cross_domain_agent",
    ]

    depends_on: list[str] = Field(
        default_factory=list,
        description="Task IDs that should be completed first."
    )


class InvestigationPlan(BaseModel):
    plan_id: str = Field(
        description="Unique identifier for the investigation plan."
    )

    summary: str = Field(
        description="Short explanation of the overall investigation strategy."
    )

    reasoning: str = Field(
        description="Why these investigation tasks are required."
    )

    tasks: list[InvestigationTask] = Field(
        default_factory=list
    )

    missing_information: list[str] = Field(
        default_factory=list,
        description="Important information or documents currently missing."
    )

    unresolved_questions: list[str] = Field(
        default_factory=list,
        description="Questions that require further investigation."
    )