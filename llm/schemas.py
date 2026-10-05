"""Structured outputs shared by model-driven agents."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class InvestigationTask(BaseModel):
    workstream: Literal["financial", "legal"]
    task: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    priority: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    evidence_documents: List[str] = Field(default_factory=list)

class InvestigationPlan(BaseModel):
    summary: str
    tasks: List[InvestigationTask] = Field(default_factory=list)

class AgentFinding(BaseModel):
    category: str
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    description: str
    evidence_documents: List[str] = Field(default_factory=list)
