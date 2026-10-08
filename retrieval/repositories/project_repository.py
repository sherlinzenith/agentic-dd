from __future__ import annotations

from typing import Any

from retrieval.models.projects import DDProject
from retrieval.models.workstreams import DDWorkstream


class ProjectRepository:

    def __init__(self, session):
        self.session = session

    def create_project(
        self,
        *,
        name: str,
        target_company: str,
        deal_type: str | None = None,
        industry: str | None = None,
        diligence_period: str | None = None,
        description: str | None = None,
    ) -> DDProject:

        project = DDProject(
            name=name,
            target_company=target_company,
            deal_type=deal_type,
            industry=industry,
            diligence_period=diligence_period,
            description=description,
            status="setup",
        )

        self.session.add(project)
        self.session.flush()

        return project

    def get_project(
        self,
        project_id: str,
    ) -> DDProject | None:

        return self.session.get(
            DDProject,
            project_id,
        )

    def list_projects(
        self,
        active_only: bool = True,
    ) -> list[DDProject]:

        query = self.session.query(DDProject)

        if active_only:
            query = query.filter(
                DDProject.is_active.is_(True)
            )

        return query.order_by(
            DDProject.created_at.desc()
        ).all()

    def create_workstream(
        self,
        *,
        project_id: str,
        name: str,
        description: str | None = None,
    ) -> DDWorkstream:

        workstream = DDWorkstream(
            project_id=project_id,
            name=name,
            description=description,
            enabled=True,
            status="pending",
        )

        self.session.add(workstream)
        self.session.flush()

        return workstream

    def get_workstreams(
        self,
        project_id: str,
    ) -> list[DDWorkstream]:

        return (
            self.session.query(DDWorkstream)
            .filter(
                DDWorkstream.project_id == project_id
            )
            .order_by(
                DDWorkstream.created_at
            )
            .all()
        )

    def save(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
