from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from database.session import Base
import retrieval.models.projects  # noqa: F401


# ================================================================
# SQLALCHEMY ORM MODELS
# ================================================================

class DDConversation(Base):
    """Represents a project-scoped due diligence Q&A chat session."""
    __tablename__ = "dd_conversations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("dd_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="New Due Diligence Chat",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    messages: Mapped[List["DDConversationMessage"]] = relationship(
        "DDConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="DDConversationMessage.created_at",
    )


class DDConversationMessage(Base):
    """An individual message (user question or assistant answer) in a DD conversation."""
    __tablename__ = "dd_conversation_messages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("dd_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # "user" or "assistant"
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Serialized JSON list of source citations
    sources_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    is_insufficient_evidence: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    conversation: Mapped["DDConversation"] = relationship(
        "DDConversation",
        back_populates="messages",
    )

    @property
    def sources(self) -> list[dict[str, Any]]:
        if not self.sources_json:
            return []
        try:
            return json.loads(self.sources_json)
        except Exception:
            return []

    @sources.setter
    def sources(self, value: list[dict[str, Any]] | None) -> None:
        if value is None:
            self.sources_json = None
        else:
            self.sources_json = json.dumps(value)


# ================================================================
# PYDANTIC SCHEMAS
# ================================================================

class SourceCitation(BaseModel):
    document_id: Optional[str] = None
    document_name: str
    page_number: Optional[int] = None
    chunk_id: Optional[str] = None
    finding_id: Optional[str] = None
    source_type: str = "document"  # "document" or "finding"
    snippet: str
    similarity_score: Optional[float] = None
    validation_status: Optional[str] = None  # "VERIFIED", "RETRIEVED_SOURCE", etc.


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Due Diligence Chat"


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, description="The user's question or follow-up query")


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sources: List[SourceCitation] = []
    is_insufficient_evidence: bool = False
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationDetailResponse(BaseModel):
    id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []
