from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.session import Base


class Finding(Base):
    __tablename__ = "dd_findings"

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

    workstream: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    agent_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    issue: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    why_it_matters: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    evidence_conclusion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    recommended_action: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    risk_severity: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="medium",
    )

    confidence: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="medium",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="REVIEW_REQUIRED",
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

    evidence = relationship(
        "Evidence",
        back_populates="finding",
        cascade="all, delete-orphan",
    )

    reviews = relationship(
        "FindingReview",
        back_populates="finding",
        cascade="all, delete-orphan",
        order_by="FindingReview.reviewed_at",
    )


class FindingReview(Base):
    __tablename__ = "dd_finding_reviews"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    finding_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "dd_findings.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    reviewer: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Human Reviewer",
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    finding = relationship(
        "Finding",
        back_populates="reviews",
    )
