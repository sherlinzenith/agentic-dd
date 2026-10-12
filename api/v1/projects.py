from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.project_service import ProjectService


router = APIRouter(
    prefix="/api/v1/projects",
    tags=["projects"],
)

service = ProjectService()


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1)
    target_company: str = Field(min_length=1)
    deal_type: str | None = None
    industry: str | None = None
    diligence_period: str | None = None
    description: str | None = None
    enabled_workstreams: list[str] | None = None


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    target_company: str | None = None
    deal_type: str | None = None
    industry: str | None = None
    diligence_period: str | None = None
    description: str | None = None
    status: str | None = None


class WorkstreamItem(BaseModel):
    name: str
    enabled: bool = True
    status: str | None = None


class UpdateWorkstreamsRequest(BaseModel):
    workstreams: list[WorkstreamItem]


@router.post("")
def create_project(
    request: CreateProjectRequest,
):
    try:
        return {
            "success": True,
            **service.create_project(
                name=request.name,
                target_company=request.target_company,
                deal_type=request.deal_type,
                industry=request.industry,
                diligence_period=request.diligence_period,
                description=request.description,
                enabled_workstreams=request.enabled_workstreams,
            ),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@router.get("")
def list_projects():
    try:
        return {
            "success": True,
            "projects": service.list_projects(),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@router.get("/{project_id}")
def get_project(
    project_id: str,
):
    project = service.get_project(project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    return {
        "success": True,
        **project,
    }


@router.put("/{project_id}")
def update_project(
    project_id: str,
    request: UpdateProjectRequest,
):
    try:
        updated = service.update_project(
            project_id=project_id,
            name=request.name,
            target_company=request.target_company,
            deal_type=request.deal_type,
            industry=request.industry,
            diligence_period=request.diligence_period,
            description=request.description,
            status=request.status,
        )

        if updated is None:
            raise HTTPException(
                status_code=404,
                detail="Project not found.",
            )

        return {
            "success": True,
            **updated,
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@router.put("/{project_id}/workstreams")
def update_workstreams(
    project_id: str,
    request: UpdateWorkstreamsRequest,
):
    try:
        workstreams = service.update_workstreams(
            project_id=project_id,
            workstream_configs=[w.model_dump() for w in request.workstreams],
        )

        return {
            "success": True,
            "workstreams": workstreams,
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@router.get("/{project_id}/summary")
def get_project_summary(
    project_id: str,
):
    summary = service.get_project_summary(project_id)
    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    return {
        "success": True,
        **summary,
    }
