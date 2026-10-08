from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.scope_service import ScopeService


router = APIRouter(
    prefix="/api/v1/projects",
    tags=["scopes"],
)

service = ScopeService()


class SaveScopeRequest(BaseModel):
    workstream: str = Field(min_length=1)
    scope: dict


@router.put("/{project_id}/scope")
def save_scope(
    project_id: str,
    request: SaveScopeRequest,
):
    try:
        return {
            "success": True,
            "scope": service.save_scope(
                project_id=project_id,
                workstream=request.workstream,
                scope=request.scope,
            ),
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


@router.get("/{project_id}/scope/{workstream}")
def get_scope(
    project_id: str,
    workstream: str,
):
    try:
        return {
            "success": True,
            "scope": service.get_scope(
                project_id=project_id,
                workstream=workstream,
            ),
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