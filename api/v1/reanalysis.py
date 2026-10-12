from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import SessionLocal
from reanalysis.schemas import ReanalysisCreate
from services.reanalysis_service import ReanalysisService
from workers.reanalysis_worker import ReanalysisWorker

router = APIRouter(
    tags=["reanalysis"],
)

service = ReanalysisService()
worker = ReanalysisWorker()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/api/v1/reanalysis")
def queue_reanalysis(
    payload: ReanalysisCreate,
    db: Session = Depends(get_db),
):
    return service.queue(db, **payload.model_dump())


@router.post("/api/v1/reanalysis/process-next")
def process_next():
    """Trigger the worker to process the next queued re-analysis run."""
    res = worker.run_once()
    return res


@router.post("/api/v1/reanalysis/{run_id}/execute")
def execute_specific_run(run_id: str):
    """Execute a specific re-analysis run immediately."""
    res = worker.run_once(run_id=run_id)
    if res.get("status") == "FAILED":
        raise HTTPException(status_code=500, detail=res.get("error", "Re-analysis failed."))
    return res


@router.get("/api/v1/reanalysis/{run_id}")
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


@router.get("/api/v1/reanalysis/project/{project_id}")
@router.get("/api/v1/projects/{project_id}/reanalysis")
def list_reanalysis(
    project_id: str,
    db: Session = Depends(get_db),
):
    return service.list_project_runs(db, project_id)
