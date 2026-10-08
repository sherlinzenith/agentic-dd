from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.planner_service import PlannerService


router = APIRouter(
    prefix="/api/v1/projects",
    tags=["planner"],
)

service = PlannerService()


class StartInvestigationRequest(BaseModel):

    objective: str = Field(
        min_length=1,
        description="Objective of the due diligence investigation.",
    )


@router.post("/{project_id}/investigations")
def start_investigation(
    project_id: str,
    request: StartInvestigationRequest,
):

    try:

        result = service.start_investigation(
            project_id=project_id,
            objective=request.objective,
        )

        return {
            "success": True,
            "investigation": result,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@router.get("/investigations/{investigation_id}")
def get_investigation(
    investigation_id: str,
):

    try:

        result = service.get_investigation(
            investigation_id,
        )

        if result is None:

            raise HTTPException(
                status_code=404,
                detail="Investigation not found.",
            )

        return {
            "success": True,
            "investigation": result,
        }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )
