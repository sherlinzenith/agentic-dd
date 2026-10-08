from __future__ import annotations

from database.session import SessionLocal
from retrieval.repositories.project_repository import ProjectRepository


class ProjectService:

    DEFAULT_WORKSTREAMS = [
        {
            "name": "financial",
            "description": "Financial due diligence investigation.",
        },
        {
            "name": "legal",
            "description": "Legal due diligence investigation.",
        },
    ]

    def create_project(
        self,
        *,
        name: str,
        target_company: str,
        deal_type: str | None = None,
        industry: str | None = None,
        diligence_period: str | None = None,
        description: str | None = None,
    ) -> dict:

        session = SessionLocal()

        try:
            repository = ProjectRepository(session)

            project = repository.create_project(
                name=name,
                target_company=target_company,
                deal_type=deal_type,
                industry=industry,
                diligence_period=diligence_period,
                description=description,
            )

            workstreams = []

            for config in self.DEFAULT_WORKSTREAMS:
                workstream = repository.create_workstream(
                    project_id=project.id,
                    name=config["name"],
                    description=config["description"],
                )

                workstreams.append(
                    {
                        "id": workstream.id,
                        "name": workstream.name,
                        "description": workstream.description,
                        "enabled": workstream.enabled,
                        "status": workstream.status,
                    }
                )

            repository.save()

            return {
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "target_company": project.target_company,
                    "deal_type": project.deal_type,
                    "industry": project.industry,
                    "diligence_period": project.diligence_period,
                    "description": project.description,
                    "status": project.status,
                },
                "workstreams": workstreams,
            }

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()

    def get_project(
        self,
        project_id: str,
    ) -> dict | None:

        session = SessionLocal()

        try:
            repository = ProjectRepository(session)

            project = repository.get_project(project_id)

            if project is None:
                return None

            workstreams = repository.get_workstreams(project_id)

            return {
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "target_company": project.target_company,
                    "deal_type": project.deal_type,
                    "industry": project.industry,
                    "diligence_period": project.diligence_period,
                    "description": project.description,
                    "status": project.status,
                },
                "workstreams": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "description": item.description,
                        "enabled": item.enabled,
                        "status": item.status,
                    }
                    for item in workstreams
                ],
            }

        finally:
            session.close()

    def list_projects(self) -> list[dict]:

        session = SessionLocal()

        try:
            repository = ProjectRepository(session)

            projects = repository.list_projects()

            return [
                {
                    "id": project.id,
                    "name": project.name,
                    "target_company": project.target_company,
                    "deal_type": project.deal_type,
                    "industry": project.industry,
                    "status": project.status,
                    "created_at": project.created_at,
                }
                for project in projects
            ]

        finally:
            session.close()
