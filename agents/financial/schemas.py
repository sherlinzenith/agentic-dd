from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EvidenceReference(BaseModel):
    document_id: str
    document_name: str
    page: int | None = None
    location: str | None = None
    quoted_text: str | None = None
    value: str | None = None


class FinancialFinding(BaseModel):
    title: str
    issue: str
    why_it_matters: str
    conclusion: str

    risk_level: Literal[
        "low",
        "medium",
        "high",
        "critical",
    ]

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    evidence: list[EvidenceReference] = Field(
        default_factory=list
    )

    recommended_action: str | None = None


class FinancialInvestigationState(BaseModel):
    """
    State for one Financial DD investigation.

    The state contains observations and results.
    It does NOT prescribe the next investigation step.

    Qwen3 decides what should happen next.
    """

    project_id: str
    investigation_id: str

    objective: str

    observations: list[str] = Field(
        default_factory=list
    )

    evidence: list[EvidenceReference] = Field(
        default_factory=list
    )

    findings: list[FinancialFinding] = Field(
        default_factory=list
    )

    missing_information: list[str] = Field(
        default_factory=list
    )

    unresolved_questions: list[str] = Field(
        default_factory=list
    )

    status: Literal[
        "pending",
        "running",
        "completed",
        "needs_evidence",
        "failed",
    ] = "pending"
