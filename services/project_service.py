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
        enabled_workstreams: list[str] | None = None,
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
                is_enabled = (
                    config["name"] in enabled_workstreams
                    if enabled_workstreams is not None
                    else True
                )
                workstream = repository.create_workstream(
                    project_id=project.id,
                    name=config["name"],
                    description=config["description"],
                    enabled=is_enabled,
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
    ) -> dict | None:
        session = SessionLocal()
        try:
            repository = ProjectRepository(session)
            project = repository.update_project(
                project_id=project_id,
                name=name,
                target_company=target_company,
                deal_type=deal_type,
                industry=industry,
                diligence_period=diligence_period,
                description=description,
                status=status,
            )
            if project is None:
                return None

            repository.save()
            return self.get_project(project_id)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_workstreams(
        self,
        project_id: str,
        workstream_configs: list[dict],
    ) -> list[dict]:
        session = SessionLocal()
        try:
            repository = ProjectRepository(session)
            for ws in workstream_configs:
                name = ws.get("name")
                if not name:
                    continue
                repository.update_workstream(
                    project_id=project_id,
                    name=name,
                    enabled=ws.get("enabled"),
                    status=ws.get("status"),
                )
            repository.save()
            workstreams = repository.get_workstreams(project_id)
            return [
                {
                    "id": item.id,
                    "name": item.name,
                    "description": item.description,
                    "enabled": item.enabled,
                    "status": item.status,
                }
                for item in workstreams
            ]
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_project_summary(
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

            from retrieval.repositories.document_repository import DocumentRepository
            from findings.repository import FindingRepository
            from tasks.models import DDTask
            from dd_requests.models import DDRequest
            from retrieval.repositories.investigation_repository import InvestigationRepository
            from services.scope_service import ScopeService

            doc_repo = DocumentRepository(session)
            finding_repo = FindingRepository(session)
            inv_repo = InvestigationRepository(session)
            scope_service = ScopeService()

            docs = doc_repo.list_documents(project_id)
            findings = finding_repo.list_for_project(project_id)
            tasks = session.query(DDTask).filter(DDTask.project_id == project_id).all()
            requests = session.query(DDRequest).filter(DDRequest.project_id == project_id).all()
            latest_inv = inv_repo.get_latest_for_project(project_id)

            scopes = {}
            for ws in workstreams:
                s = scope_service.get_scope(project_id=project_id, workstream=ws.name)
                scopes[ws.name] = s.get("scope", {})

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
                    "created_at": project.created_at.isoformat() if project.created_at else None,
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
                "scopes": scopes,
                "counts": {
                    "documents": len(docs),
                    "findings": len(findings),
                    "tasks": len(tasks),
                    "requests": len(requests),
                },
                "latest_investigation": {
                    "id": latest_inv.id,
                    "status": latest_inv.status,
                    "objective": latest_inv.objective,
                } if latest_inv else None,
            }
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
                    "description": project.description,
                    "diligence_period": project.diligence_period,
                    "status": project.status,
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                }
                for project in projects
            ]

        finally:
            session.close()
