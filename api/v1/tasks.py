from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database.session import SessionLocal
from tasks.schemas import TaskStatusUpdate, TaskCreate
from services.task_service import TaskService
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
service = TaskService()


class GeneratePlanTasksRequest(BaseModel):
    investigation_id: Optional[str] = None
    enabled_workstreams: Optional[list[str]] = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("")
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    try:
        return service.create_task(
            db,
            project_id=payload.project_id,
            title=payload.title,
            description=payload.description,
            task_type=payload.task_type,
            priority=payload.priority,
            assigned_to=payload.assigned_to,
            assigned_agent=payload.assigned_agent,
            investigation_id=payload.investigation_id,
            finding_id=payload.finding_id,
            request_id=payload.request_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/project/{project_id}/generate-plan")
def generate_plan_tasks(
    project_id: str,
    payload: GeneratePlanTasksRequest,
    db: Session = Depends(get_db),
):
    try:
        created = service.generate_plan_tasks(
            db,
            project_id=project_id,
            investigation_id=payload.investigation_id,
            enabled_workstreams=payload.enabled_workstreams,
        )
        return {
            "success": True,
            "tasks": created,
            "count": len(created),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


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
