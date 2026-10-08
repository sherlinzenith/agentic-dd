from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select

from dd_requests.models import DDRequest
from tasks.models import DDTask


class RequestService:

    VALID_STATUSES = {
        "OPEN",
        "SUBMITTED",
        "RESOLVED",
        "CANCELLED",
    }

    def create_request(
        self,
        db,
        *,
        project_id: str,
        investigation_id: str | None = None,
        finding_id: str | None = None,
        request_type: str = "EVIDENCE",
        title: str,
        description: str,
        requested_items: list[str] | None = None,
        priority: str = "medium",
        requested_from: str | None = None,
        due_at=None,
    ):
        request = DDRequest(
            project_id=project_id,
            investigation_id=investigation_id,
            finding_id=finding_id,
            request_type=request_type,
            title=title,
            description=description,
            requested_items=json.dumps(requested_items or []),
            priority=priority,
            requested_from=requested_from,
            due_at=due_at,
        )

        db.add(request)
        db.commit()
        db.refresh(request)

        return request

    def get(self, db, request_id: str):
        return db.get(DDRequest, request_id)

    def list_project_requests(self, db, project_id: str):
        stmt = (
            select(DDRequest)
            .where(DDRequest.project_id == project_id)
            .order_by(DDRequest.created_at.desc())
        )
        return list(db.scalars(stmt).all())

    def update_status(self, db, request_id: str, status: str):
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid request status: {status}")

        request = db.get(DDRequest, request_id)

        if request is None:
            raise ValueError("Request not found.")

        request.status = status

        if status == "RESOLVED":
            request.resolved_at = datetime.utcnow()

        db.commit()
        db.refresh(request)

        return request

    def create_task_from_request(
        self,
        db,
        request_id: str,
        *,
        assigned_to: str | None = None,
    ):
        request = db.get(DDRequest, request_id)

        if request is None:
            raise ValueError("Request not found.")

        task = DDTask(
            project_id=request.project_id,
            investigation_id=request.investigation_id,
            request_id=request.id,
            finding_id=request.finding_id,
            task_type="EVIDENCE_COLLECTION",
            title=request.title,
            description=request.description,
            priority=request.priority,
            assigned_to=assigned_to or request.requested_from,
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        return task
