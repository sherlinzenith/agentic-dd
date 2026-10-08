from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from reanalysis.models import DDReanalysisRun


class ReanalysisService:

    def queue(
        self,
        db,
        *,
        project_id: str,
        investigation_id: str | None = None,
        finding_id: str | None = None,
        request_id: str | None = None,
        trigger_type: str = "NEW_EVIDENCE",
        reason: str | None = None,
    ):
        run = DDReanalysisRun(
            project_id=project_id,
            investigation_id=investigation_id,
            finding_id=finding_id,
            request_id=request_id,
            trigger_type=trigger_type,
            status="QUEUED",
            reason=reason,
        )

        db.add(run)
        db.commit()
        db.refresh(run)

        return run

    def get(self, db, run_id: str):
        return db.get(DDReanalysisRun, run_id)

    def list_project_runs(self, db, project_id: str):
        stmt = (
            select(DDReanalysisRun)
            .where(DDReanalysisRun.project_id == project_id)
            .order_by(DDReanalysisRun.created_at.desc())
        )
        return list(db.scalars(stmt).all())

    def mark_running(self, db, run_id: str):
        run = db.get(DDReanalysisRun, run_id)

        if run is None:
            raise ValueError("Re-analysis run not found.")

        run.status = "RUNNING"
        run.started_at = datetime.utcnow()

        db.commit()
        db.refresh(run)

        return run

    def mark_complete(self, db, run_id: str, result_summary: str | None = None):
        run = db.get(DDReanalysisRun, run_id)

        if run is None:
            raise ValueError("Re-analysis run not found.")

        run.status = "COMPLETE"
        run.result_summary = result_summary
        run.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(run)

        return run

    def mark_failed(self, db, run_id: str, result_summary: str):
        run = db.get(DDReanalysisRun, run_id)

        if run is None:
            raise ValueError("Re-analysis run not found.")

        run.status = "FAILED"
        run.result_summary = result_summary
        run.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(run)

        return run
