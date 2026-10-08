from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.session import Base


class DDReanalysisRun(Base):
    __tablename__ = "dd_reanalysis_runs"

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

    request_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("dd_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    trigger_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="QUEUED", index=True
    )

    reason: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    result_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
