from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


DocumentCategory = Literal[
    "financial",
    "legal",
    "other",
]


class ClassificationResult(BaseModel):
    category: DocumentCategory

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    reasoning: str

    document_type: str

    signals: list[str] = Field(
        default_factory=list
    )
