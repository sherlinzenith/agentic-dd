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
