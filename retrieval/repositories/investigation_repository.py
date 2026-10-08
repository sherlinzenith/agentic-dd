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

    def save(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
