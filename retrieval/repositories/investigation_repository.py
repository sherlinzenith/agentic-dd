from __future__ import annotations

from retrieval.models.investigations import DDInvestigation


class InvestigationRepository:

    def __init__(self, session):
        self.session = session

    def create(
        self,
        *,
        project_id: str,
        objective: str,
    ) -> DDInvestigation:

        investigation = DDInvestigation(
            project_id=project_id,
            objective=objective,
            status="planning",
        )

        self.session.add(investigation)
        self.session.flush()

        return investigation

    def get(
        self,
        investigation_id: str,
    ) -> DDInvestigation | None:

        return self.session.get(
            DDInvestigation,
            investigation_id,
        )

    def update_plan(
        self,
        investigation_id: str,
        plan: dict,
    ) -> DDInvestigation | None:

        investigation = self.get(
            investigation_id
        )

        if investigation is None:
            return None

        investigation.plan = plan
        investigation.status = "plan_ready"

        self.session.flush()

        return investigation

    def update_status(
        self,
        investigation_id: str,
        status: str,
        plan: dict | None = None,
    ) -> DDInvestigation | None:
        investigation = self.get(investigation_id)
        if investigation is None:
            return None

        investigation.status = status
        if plan is not None:
            investigation.plan = plan

        self.session.flush()
        return investigation

    def get_latest_for_project(
        self,
        project_id: str,
    ) -> DDInvestigation | None:
        from sqlalchemy import select
        stmt = (
            select(DDInvestigation)
            .where(DDInvestigation.project_id == project_id)
            .order_by(DDInvestigation.created_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def save(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
