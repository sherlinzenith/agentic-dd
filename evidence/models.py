from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.session import Base


class Evidence(Base):
    __tablename__ = "dd_evidence"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    project_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    investigation_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "dd_investigations.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    finding_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "dd_findings.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "dd_requests.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    document_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "documents.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    chunk_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "document_chunks.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    evidence_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="document",
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    quoted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    extracted_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_label: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    validation_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UNVERIFIED",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    finding = relationship(
        "Finding",
        back_populates="evidence",
    )
