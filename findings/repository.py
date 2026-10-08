from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from evidence.models import Evidence
from findings.models import Finding, FindingReview


class FindingRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_finding(self, data: dict) -> Finding:
        finding = Finding(**data)

        self.db.add(finding)
        self.db.flush()

        return finding

    def add_evidence(self, data: dict) -> Evidence:
        evidence = Evidence(**data)

        self.db.add(evidence)
        self.db.flush()

        return evidence

    def get(self, finding_id: str) -> Finding | None:

        return self.db.execute(
            select(Finding)
            .options(
                joinedload(Finding.evidence),
                joinedload(Finding.reviews),
            )
            .where(Finding.id == finding_id)
        ).unique().scalar_one_or_none()

    def list_for_project(
        self,
        project_id: str,
    ) -> list[Finding]:

        return list(
            self.db.execute(
                select(Finding)
                .where(
                    Finding.project_id == project_id
                )
                .order_by(
                    Finding.created_at.desc()
                )
            ).scalars()
        )

    def add_review(
        self,
        finding: Finding,
        action: str,
        reviewer: str,
        comment: str | None,
    ) -> FindingReview:

        review = FindingReview(
            finding_id=finding.id,
            action=action,
            reviewer=reviewer,
            comment=comment,
        )

        self.db.add(review)

        return review

    def apply_reanalysis_result(
        self,
        finding: Finding,
        conclusion: str,
    ) -> Finding:
        """
        Apply the textual conclusion produced by a re-analysis run.

        Re-analysis never automatically approves a finding.
        The finding is returned to human review.
        """

        conclusion = (conclusion or "").strip()

        if not conclusion:
            raise ValueError(
                "Re-analysis conclusion cannot be empty."
            )

        finding.evidence_conclusion = conclusion
        finding.status = "REVIEW_REQUIRED"

        self.db.flush()

        return finding

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
