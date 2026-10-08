from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import SessionLocal
from tasks.schemas import TaskStatusUpdate
from services.task_service import TaskService

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
service = TaskService()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = service.get(db, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    return task


@router.get("/project/{project_id}")
def list_tasks(project_id: str, db: Session = Depends(get_db)):
    return service.list_project_tasks(db, project_id)


@router.patch("/{task_id}/status")
def update_task_status(
    task_id: str,
    payload: TaskStatusUpdate,
    db: Session = Depends(get_db),
):
    try:
        return service.update_status(db, task_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
