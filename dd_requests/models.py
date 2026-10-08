from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.session import Base


class DDRequest(Base):
    __tablename__ = "dd_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    project_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )

    investigation_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("dd_investigations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    finding_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("dd_findings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    request_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="EVIDENCE"
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    requested_items: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="OPEN", index=True
    )

    priority: Mapped[str] = mapped_column(
        String(30), nullable=False, default="medium"
    )

    requested_from: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    due_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
