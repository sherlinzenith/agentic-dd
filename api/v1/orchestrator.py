from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.orchestrator_service import DDOrchestratorService

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["orchestrator"],
)

service = DDOrchestratorService()


class RunFullDDRequest(BaseModel):
    objective: Optional[str] = Field(
        default=None,
        description="Optional high-level objective for the full due diligence investigation.",
    )
    max_agent_iterations: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Maximum reasoning iterations per specialist agent.",
    )


@router.post("/{project_id}/run-full-dd")
@router.post("/{project_id}/orchestrator/run")
def run_full_due_diligence(
    project_id: str,
    request: RunFullDDRequest = RunFullDDRequest(),
):
    """
    Execute the central Due Diligence orchestration workflow:
    Planner -> Financial Agent -> Legal Agent -> Cross-Domain Agent -> Evidence Validation.
    """
    try:
        result = service.run_full_dd(
            project_id=project_id,
            objective=request.objective,
            max_agent_iterations=request.max_agent_iterations,
        )
        return result

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@router.get("/{project_id}/orchestrator/status")
def get_orchestration_status(
    project_id: str,
):
    """
    Get the latest central orchestration workflow status, stages, and findings summary.
    """
    try:
        status = service.get_latest_status(project_id)
        if status is None:
            raise HTTPException(
                status_code=404,
                detail=f"No orchestration runs found for project {project_id}",
            )
        return {
            "success": True,
            "status": status,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )
