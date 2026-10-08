from __future__ import annotations

from typing import Any

from database.session import SessionLocal
from retrieval.models.documents import Document
from retrieval.repositories.project_repository import ProjectRepository
from retrieval.repositories.scope_repository import ScopeRepository

from agents.engine.tool_registry import AgentTool, ToolRegistry


def get_project_context(
    project_id: str,
) -> dict[str, Any]:

    session = SessionLocal()

    try:
        project_repository = ProjectRepository(session)
        scope_repository = ScopeRepository(session)

        project = project_repository.get_project(
            project_id
        )

        if project is None:
            return {
                "status": "NOT_FOUND",
                "project_id": project_id,
            }

        workstreams = project_repository.get_workstreams(
            project_id
        )

        documents = (
            session.query(Document)
            .filter(
                Document.project_id == project_id
            )
            .order_by(Document.created_at)
            .all()
        )

        scopes: dict[str, dict] = {}

        for workstream in workstreams:

            if not workstream.enabled:
                continue

            existing_scope = (
                scope_repository.get_scope(
                    project_id=project_id,
                    workstream=workstream.name,
                )
            )

            if existing_scope:
                scopes[workstream.name] = (
                    existing_scope.scope
                )

        return {
            "status": "OK",

            "project": {
                "id": project.id,
                "name": project.name,
                "target_company": project.target_company,
                "deal_type": project.deal_type,
                "industry": project.industry,
                "diligence_period": (
                    project.diligence_period
                ),
                "description": project.description,
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
                if item.enabled
            ],

            "documents": [
                {
                    "id": document.id,
                    "file_name": document.file_name,
                    "category": document.category,
                    "document_type": (
                        document.document_type
                    ),
                    "processing_status": (
                        document.processing_status
                    ),
                }
                for document in documents
            ],

            "scopes": scopes,
        }

    finally:
        session.close()


def get_project_documents(
    project_id: str,
) -> dict[str, Any]:

    session = SessionLocal()

    try:

        documents = (
            session.query(Document)
            .filter(
                Document.project_id == project_id
            )
            .order_by(Document.created_at)
            .all()
        )

        return {
            "status": "OK",
            "documents": [
                {
                    "id": document.id,
                    "file_name": document.file_name,
                    "category": document.category,
                    "document_type": (
                        document.document_type
                    ),
                    "processing_status": (
                        document.processing_status
                    ),
                }
                for document in documents
            ],
        }

    finally:
        session.close()


def create_planner_tool_registry() -> ToolRegistry:

    registry = ToolRegistry()

    registry.register(
        AgentTool(
            name="get_project_context",

            description=(
                "Retrieve the DD project information, "
                "enabled workstreams, configured scopes, "
                "and uploaded document metadata."
            ),

            parameters={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": (
                            "The DD project ID."
                        ),
                    }
                },
                "required": ["project_id"],
            },

            function=get_project_context,
        )
    )

    registry.register(
        AgentTool(
            name="get_project_documents",

            description=(
                "Retrieve all uploaded documents "
                "belonging to a DD project."
            ),

            parameters={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": (
                            "The DD project ID."
                        ),
                    }
                },
                "required": ["project_id"],
            },

            function=get_project_documents,
        )
    )

    return registry
