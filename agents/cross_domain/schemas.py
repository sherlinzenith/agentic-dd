from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CrossDomainRiskLevel = Literal[
    "low",
    "medium",
    "high",
    "critical",
]


class CrossDomainFinding(BaseModel):
    """
    Finding produced when evidence from multiple DD workstreams
    creates a combined issue or risk.
    """

    title: str = Field(
        min_length=1,
        description="Short title describing the cross-domain issue.",
    )

    issue: str = Field(
        min_length=1,
        description="What was identified across multiple workstreams.",
    )

    why_it_matters: str = Field(
        min_length=1,
        description="Why the combined issue matters to the transaction.",
    )

    risk_level: CrossDomainRiskLevel = "medium"

    related_workstreams: list[str] = Field(
        default_factory=list,
    )

    financial_finding_ids: list[str] = Field(
        default_factory=list,
    )

    legal_finding_ids: list[str] = Field(
        default_factory=list,
    )

    evidence: list[dict] = Field(
        default_factory=list,
    )

    contradiction: str | None = None

    missing_information: list[str] = Field(
        default_factory=list,
    )

    recommended_action: str | None = None

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )


class CrossDomainInvestigationResult(BaseModel):
    """
    Final structured result of a cross-domain investigation.
    """

    findings: list[CrossDomainFinding] = Field(
        default_factory=list,
    )

    contradictions: list[dict] = Field(
        default_factory=list,
    )

    missing_information: list[str] = Field(
        default_factory=list,
    )

    investigation_summary: str = ""

    investigation_complete: bool = False