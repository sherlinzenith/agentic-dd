from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import SessionLocal

from findings.schemas import (
    EvidenceCreate,
    FindingCreate,
    FindingListResponse,
    FindingResponse,
    ReviewCreate,
)

from services.finding_service import FindingService


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
    db: Session = Depends(get_db),
):

    return FindingService(db).review(
        finding_id,
        payload.action,
        payload.reviewer,
        payload.comment,
    )


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
