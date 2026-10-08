from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import SessionLocal
from reanalysis.schemas import ReanalysisCreate
from services.reanalysis_service import ReanalysisService

router = APIRouter(
    prefix="/api/v1/reanalysis",
    tags=["reanalysis"],
)

service = ReanalysisService()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("")
def queue_reanalysis(
    payload: ReanalysisCreate,
    db: Session = Depends(get_db),
):
    return service.queue(db, **payload.model_dump())


@router.get("/{run_id}")
def get_reanalysis(
    run_id: str,
    db: Session = Depends(get_db),
):
    run = service.get(db, run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Re-analysis run not found.",
        )

    return run


@router.get("/project/{project_id}")
def list_reanalysis(
    project_id: str,
    db: Session = Depends(get_db),
):
    return service.list_project_runs(db, project_id)
