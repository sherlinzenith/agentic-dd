from __future__ import annotations

from fastapi import HTTPException

from findings.models import Finding
from findings.repository import FindingRepository

from services.request_service import RequestService
from services.reanalysis_service import ReanalysisService


VALID_REVIEW_ACTIONS = {
    "APPROVE": "APPROVED",
    "REJECT": "REJECTED",
    "REQUEST_MORE_EVIDENCE": "MORE_EVIDENCE_REQUIRED",
}


class FindingService:

    def __init__(self, db):
        self.repo = FindingRepository(db)
        self.request_service = RequestService()
        self.reanalysis_service = ReanalysisService()

    def create_finding(self, payload):

        finding = self.repo.create_finding(payload)

        self.repo.commit()

        return self.repo.get(finding.id)

    def add_evidence(
        self,
        finding_id: str,
        payload: dict,
    ):

        finding = self.repo.get(finding_id)

        if not finding:
            raise HTTPException(
                status_code=404,
                detail="Finding not found.",
            )

        payload["finding_id"] = finding_id
        payload["project_id"] = finding.project_id

        request_id = payload.get("request_id")

        evidence = self.repo.add_evidence(payload)

        # -----------------------------------------------------
        # EVIDENCE SUBMISSION -> REQUEST RESOLUTION
        # -----------------------------------------------------
        request = None
        task = None

        if request_id:
            from dd_requests.models import DDRequest
            from tasks.models import DDTask

            request = self.repo.db.get(
                DDRequest,
                request_id,
            )

            if not request:
                raise HTTPException(
                    status_code=404,
                    detail="Evidence request not found.",
                )

            if request.finding_id != finding_id:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Evidence request does not belong "
                        "to this finding."
                    ),
                )

            # Link evidence to the request.
            evidence.request_id = request_id

            # Resolve the evidence request.
            request.status = "RESOLVED"
            from datetime import datetime
            request.resolved_at = datetime.utcnow()

            # Complete the evidence-collection task.
            task = (
                self.repo.db.query(DDTask)
                .filter(
                    DDTask.request_id == request_id
                )
                .order_by(DDTask.created_at.desc())
                .first()
            )

            if task:
                task.status = "DONE"
                task.completed_at = datetime.utcnow()

        # -----------------------------------------------------
        # FINDING RETURNS TO HUMAN REVIEW
        # -----------------------------------------------------
        if finding.status == "MORE_EVIDENCE_REQUIRED":
            finding.status = "REVIEW_REQUIRED"

        self.repo.commit()

        return self.repo.get(finding_id)

    def review(
        self,
        finding_id: str,
        *,
        action: str,
        reviewer: str = "Human Reviewer",
        comment: str | None = None,
    ):

        if action not in VALID_REVIEW_ACTIONS:
            raise ValueError(
                f"Invalid review action: {action}"
            )

        finding = self.repo.get(finding_id)

        if finding is None:
            raise ValueError("Finding not found.")

        new_status = VALID_REVIEW_ACTIONS[action]

        review = self.repo.add_review(
            finding=finding,
            action=action,
            reviewer=reviewer,
            comment=comment,
        )

        finding.status = new_status

        self.repo.commit()

        # -----------------------------------------------------
        # HUMAN REVIEW -> EVIDENCE REQUEST -> TASK -> REANALYSIS
        # -----------------------------------------------------
        if action == "REQUEST_MORE_EVIDENCE":

            request_title = (
                f"Additional evidence required: {finding.title}"
            )

            request_description = (
                comment
                if comment
                else (
                    "Additional evidence is required before this "
                    "finding can be finalized."
                )
            )

            request = self.request_service.create_request(
                self.repo.db,
                project_id=finding.project_id,
                investigation_id=finding.investigation_id,
                finding_id=finding.id,
                request_type="EVIDENCE",
                title=request_title,
                description=request_description,
                requested_items=[
                    "Supporting evidence for the finding",
                    "Source document or missing documentation",
                ],
                priority=finding.risk_severity,
            )

            task = self.request_service.create_task_from_request(
                self.repo.db,
                request.id,
            )

            reanalysis = self.reanalysis_service.queue(
                self.repo.db,
                project_id=finding.project_id,
                investigation_id=finding.investigation_id,
                finding_id=finding.id,
                request_id=request.id,
                trigger_type="NEW_EVIDENCE",
                reason=(
                    "Human reviewer requested additional evidence "
                    "before finalizing the finding."
                ),
            )

            return {
                "finding": finding,
                "review": review,
                "request": request,
                "task": task,
                "reanalysis": reanalysis,
            }

        return {
            "finding": finding,
            "review": review,
        }

    def reopen(self, finding_id: str):

        finding = self.repo.get(finding_id)

        if not finding:
            raise HTTPException(
                status_code=404,
                detail="Finding not found.",
            )

        if finding.status != "MORE_EVIDENCE_REQUIRED":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Only findings requiring more evidence "
                    "can be reopened."
                ),
            )

        finding.status = "REVIEW_REQUIRED"

        self.repo.commit()

        return self.repo.get(finding_id)
