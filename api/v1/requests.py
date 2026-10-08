from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import SessionLocal
from dd_requests.schemas import (
    RequestCreate,
    RequestStatusUpdate,
    TaskCreateFromRequest,
)
from services.request_service import RequestService

router = APIRouter(prefix="/api/v1/requests", tags=["requests"])
service = RequestService()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("")
def create_request(payload: RequestCreate, db: Session = Depends(get_db)):
    return service.create_request(db, **payload.model_dump())


@router.get("/{request_id}")
def get_request(request_id: str, db: Session = Depends(get_db)):
    request = service.get(db, request_id)

    if request is None:
        raise HTTPException(status_code=404, detail="Request not found.")

    return request


@router.get("/project/{project_id}")
def list_requests(project_id: str, db: Session = Depends(get_db)):
    return service.list_project_requests(db, project_id)


@router.patch("/{request_id}/status")
def update_status(
    request_id: str,
    payload: RequestStatusUpdate,
    db: Session = Depends(get_db),
):
    try:
        return service.update_status(db, request_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{request_id}/task")
def create_task(
    request_id: str,
    payload: TaskCreateFromRequest,
    db: Session = Depends(get_db),
):
    try:
        return service.create_task_from_request(
            db,
            request_id,
            assigned_to=payload.assigned_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
