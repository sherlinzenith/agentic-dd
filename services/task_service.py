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

    def create_task(
        self,
        db,
        *,
        project_id: str,
        title: str,
        description: str,
        task_type: str = "INVESTIGATION_CHECK",
        priority: str = "medium",
        assigned_to: str | None = None,
        assigned_agent: str | None = None,
        investigation_id: str | None = None,
        finding_id: str | None = None,
        request_id: str | None = None,
    ) -> DDTask:
        task = DDTask(
            project_id=project_id,
            investigation_id=investigation_id,
            request_id=request_id,
            finding_id=finding_id,
            task_type=task_type,
            title=title,
            description=description,
            priority=priority,
            assigned_to=assigned_to,
            assigned_agent=assigned_agent,
            status="TODO",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def generate_plan_tasks(
        self,
        db,
        *,
        project_id: str,
        investigation_id: str | None = None,
        enabled_workstreams: list[str] | None = None,
    ) -> list[DDTask]:
        """Generate investigation tasks for enabled workstreams without duplicating open tasks."""
        workstreams = enabled_workstreams or ["financial", "legal"]
        created = []

        existing = set(
            db.scalars(
                select(DDTask.title).where(
                    DDTask.project_id == project_id,
                    DDTask.investigation_id == investigation_id,
                )
            ).all()
        )

        task_defs = []
        if "financial" in workstreams:
            task_defs.extend([
                {
                    "title": "Financial DD: Verify Reported Revenue & Profitability",
                    "description": "Examine income statements, revenue growth, gross profit margins, and EBITDA from uploaded financial documents.",
                    "assigned_agent": "financial",
                    "task_type": "FINANCIAL_CHECK",
                    "priority": "high",
                },
                {
                    "title": "Financial DD: Audit Debt Obligations & Working Capital",
                    "description": "Inspect balance sheet and cash flow statements for outstanding debt, related-party transactions, and liquidity risks.",
                    "assigned_agent": "financial",
                    "task_type": "FINANCIAL_CHECK",
                    "priority": "medium",
                },
            ])

        if "legal" in workstreams:
            task_defs.extend([
                {
                    "title": "Legal DD: Review Material Contracts & Change of Control",
                    "description": "Inspect term sheets, customer agreements, and vendor contracts for change of control clauses, assignment restrictions, and termination triggers.",
                    "assigned_agent": "legal",
                    "task_type": "LEGAL_CHECK",
                    "priority": "high",
                },
                {
                    "title": "Legal DD: Assess Liabilities & Compliance Risks",
                    "description": "Analyze litigation disclosures, indemnification liabilities, IP ownership restrictions, and regulatory obligations.",
                    "assigned_agent": "legal",
                    "task_type": "LEGAL_CHECK",
                    "priority": "medium",
                },
            ])

        if "financial" in workstreams and "legal" in workstreams:
            task_defs.append({
                "title": "Cross-Domain DD: Correlate Financial Commitments with Legal Contracts",
                "description": "Cross-reference financial debt figures and revenue concentrations against credit agreement covenants and customer termination rights.",
                "assigned_agent": "cross_domain",
                "task_type": "CROSS_DOMAIN_CHECK",
                "priority": "high",
            })

        for t_def in task_defs:
            if t_def["title"] not in existing:
                t = self.create_task(
                    db,
                    project_id=project_id,
                    investigation_id=investigation_id,
                    title=t_def["title"],
                    description=t_def["description"],
                    assigned_agent=t_def["assigned_agent"],
                    task_type=t_def["task_type"],
                    priority=t_def["priority"],
                )
                created.append(t)

        return created
