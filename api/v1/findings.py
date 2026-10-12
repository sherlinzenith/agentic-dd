from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import SessionLocal

from findings.schemas import (
    EvidenceCreate,
    FindingCreate,
    FindingListResponse,
    FindingResponse,
    ReviewCreate,
    ReviewResponse,
)

from services.finding_service import FindingService
from workers.reanalysis_worker import process_next_reanalysis


router = APIRouter(
    prefix="/api/v1",
    tags=["findings"],
)


def get_db():

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/findings",
    response_model=FindingResponse,
)
def create_finding(
    payload: FindingCreate,
    db: Session = Depends(get_db),
):

    return FindingService(db).create_finding(
        payload.model_dump()
    )


@router.get(
    "/projects/{project_id}/findings",
    response_model=FindingListResponse,
)
def list_findings(
    project_id: str,
    db: Session = Depends(get_db),
):

    return {
        "findings": FindingService(
            db
        ).repo.list_for_project(project_id)
    }


@router.get(
    "/findings/{finding_id}",
    response_model=FindingResponse,
)
def get_finding(
    finding_id: str,
    db: Session = Depends(get_db),
):

    finding = FindingService(db).repo.get(
        finding_id
    )

    if not finding:
        raise HTTPException(
            status_code=404,
            detail="Finding not found.",
        )

    return finding


@router.post(
    "/findings/{finding_id}/evidence",
    response_model=FindingResponse,
)
def add_evidence(
    finding_id: str,
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
):

    return FindingService(db).add_evidence(
        finding_id,
        payload.model_dump(
            exclude_none=True
        ),
    )


@router.post(
    "/findings/{finding_id}/review",
)
def review_finding(
    finding_id: str,
    payload: ReviewCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    result = FindingService(db).review(
        finding_id,
        action=payload.action,
        reviewer=payload.reviewer,
        comment=payload.comment,
    )

    if payload.action == "REQUEST_MORE_EVIDENCE":
        background_tasks.add_task(process_next_reanalysis)

    out = {
        "finding": FindingResponse.model_validate(result["finding"]).model_dump(),
        "review": ReviewResponse.model_validate(result["review"]).model_dump(),
    }
    if "request" in result and result["request"]:
        req = result["request"]
        out["request"] = {
            "id": req.id,
            "project_id": req.project_id,
            "finding_id": req.finding_id,
            "title": req.title,
            "description": req.description,
            "status": req.status,
            "priority": req.priority,
            "created_at": req.created_at.isoformat() if req.created_at else None,
        }
    if "task" in result and result["task"]:
        task = result["task"]
        out["task"] = {
            "id": task.id,
            "request_id": task.request_id,
            "finding_id": task.finding_id,
            "title": task.title,
            "status": task.status,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }
    if "reanalysis" in result and result["reanalysis"]:
        run = result["reanalysis"]
        out["reanalysis"] = {
            "id": run.id,
            "project_id": run.project_id,
            "finding_id": run.finding_id,
            "request_id": run.request_id,
            "trigger_type": run.trigger_type,
            "status": run.status,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }

    return out


@router.post(
    "/findings/{finding_id}/reopen",
    response_model=FindingResponse,
)
def reopen_finding(
    finding_id: str,
    db: Session = Depends(get_db),
):

    return FindingService(db).reopen(
        finding_id
    )
