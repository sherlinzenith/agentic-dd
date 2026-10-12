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

    def update_project(
        self,
        project_id: str,
        *,
        name: str | None = None,
        target_company: str | None = None,
        deal_type: str | None = None,
        industry: str | None = None,
        diligence_period: str | None = None,
        description: str | None = None,
        status: str | None = None,
    ) -> DDProject | None:
        project = self.get_project(project_id)
        if project is None:
            return None

        if name is not None:
            project.name = name
        if target_company is not None:
            project.target_company = target_company
        if deal_type is not None:
            project.deal_type = deal_type
        if industry is not None:
            project.industry = industry
        if diligence_period is not None:
            project.diligence_period = diligence_period
        if description is not None:
            project.description = description
        if status is not None:
            project.status = status

        self.session.flush()
        return project

    def create_workstream(
        self,
        *,
        project_id: str,
        name: str,
        description: str | None = None,
        enabled: bool = True,
    ) -> DDWorkstream:

        workstream = DDWorkstream(
            project_id=project_id,
            name=name,
            description=description,
            enabled=enabled,
            status="pending",
        )

        self.session.add(workstream)
        self.session.flush()

        return workstream

    def update_workstream(
        self,
        project_id: str,
        name: str,
        *,
        enabled: bool | None = None,
        status: str | None = None,
    ) -> DDWorkstream | None:
        workstream = (
            self.session.query(DDWorkstream)
            .filter(
                DDWorkstream.project_id == project_id,
                DDWorkstream.name == name,
            )
            .first()
        )
        if workstream is None:
            return None

        if enabled is not None:
            workstream.enabled = enabled
        if status is not None:
            workstream.status = status

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
