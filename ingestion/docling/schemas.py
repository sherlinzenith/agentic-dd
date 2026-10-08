from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


DocumentCategory = Literal[
    "financial",
    "legal",
    "other",
]


class ProcessedDocument(BaseModel):
    file_name: str
    file_path: str
    source_format: str

    text: str

    category: DocumentCategory | None = None

    metadata: dict = Field(
        default_factory=dict
    )


class DocumentChunk(BaseModel):
    document_id: str
    chunk_index: int

    text: str

    page: int | None = None
    section: str | None = None

    metadata: dict = Field(
        default_factory=dict
    )
