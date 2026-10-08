from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from tasks.models import DDTask


class TaskService:

    VALID_STATUSES = {
        "TODO",
        "IN_PROGRESS",
        "BLOCKED",
        "DONE",
        "CANCELLED",
    }

    def get(self, db, task_id: str):
        return db.get(DDTask, task_id)

    def list_project_tasks(self, db, project_id: str):
        stmt = (
            select(DDTask)
            .where(DDTask.project_id == project_id)
            .order_by(DDTask.created_at.desc())
        )
        return list(db.scalars(stmt).all())

    def update_status(self, db, task_id: str, status: str):
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid task status: {status}")

        task = db.get(DDTask, task_id)

        if task is None:
            raise ValueError("Task not found.")

        task.status = status

        if status == "DONE":
            task.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(task)

        return task
