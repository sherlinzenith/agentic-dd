from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.new_main import app
from database.session import SessionLocal
from dd_requests.models import DDRequest
from evidence.models import Evidence
from findings.models import Finding, FindingReview
from reanalysis.models import DDReanalysisRun
from retrieval.models.documents import Document, DocumentChunk
from retrieval.models.projects import DDProject
from services.finding_service import FindingService
from tasks.models import DDTask
from workers.reanalysis_worker import ReanalysisWorker, process_next_reanalysis


class TestHumanReviewAndReanalysis(unittest.TestCase):
    def _clean_db(self):
        try:
            for r in self.session.query(DDReanalysisRun).filter(DDReanalysisRun.project_id == self.project_id).all():
                self.session.delete(r)
            for t in self.session.query(DDTask).filter(DDTask.project_id == self.project_id).all():
                self.session.delete(t)
            for req in self.session.query(DDRequest).filter(DDRequest.project_id == self.project_id).all():
                self.session.delete(req)
            for rev in self.session.query(FindingReview).all():
                if rev.finding_id == "find-review-test-1":
                    self.session.delete(rev)
            for ev in self.session.query(Evidence).filter(Evidence.project_id == self.project_id).all():
                self.session.delete(ev)
            for f in self.session.query(Finding).filter(Finding.project_id == self.project_id).all():
                self.session.delete(f)
            for c in self.session.query(DocumentChunk).filter(DocumentChunk.document_id == "doc-review-test-1").all():
                self.session.delete(c)
            for d in self.session.query(Document).filter(Document.project_id == self.project_id).all():
                self.session.delete(d)
            proj = self.session.get(DDProject, self.project_id)
            if proj:
                self.session.delete(proj)
            self.session.commit()
        except Exception:
            self.session.rollback()

    def setUp(self):
        self.project_id = "TEST-REVIEW-REANALYSIS-PROJ"
        self.session = SessionLocal()
        self.client = TestClient(app)

        # Ensure previous run leftover is cleaned up
        self._clean_db()

        # 1. Ensure test project exists
        proj = self.session.get(DDProject, self.project_id)
        if not proj:
            proj = DDProject(
                id=self.project_id,
                name="Review Test Project",
                target_company="Acme Corporation",
            )
            self.session.add(proj)

        # 2. Create test document & chunk
        self.doc = Document(
            id="doc-review-test-1",
            project_id=self.project_id,
            file_name="01_income_statement.pdf",
            storage_key="test/01_income_statement.pdf",
            category="financial",
        )
        self.session.add(self.doc)

        self.chunk = DocumentChunk(
            id="chunk-review-test-1",
            document_id=self.doc.id,
            chunk_index=0,
            content="Total Revenue for FY 2025-26 was INR 100.00 crore. Gross Profit stood at INR 42.00 crore.",
            page_number=1,
            section="Income Statement",
        )
        self.session.add(self.chunk)

        # 3. Create a test finding
        self.finding = Finding(
            id="find-review-test-1",
            project_id=self.project_id,
            workstream="financial",
            title="Revenue Uncertainty",
            issue="Revenue reports require further audit clarification",
            why_it_matters="Potential financial variance",
            evidence_conclusion="Preliminary review indicates possible mismatch.",
            status="REVIEW_REQUIRED",
            risk_severity="medium",
            confidence="0.80",
        )
        self.session.add(self.finding)

        # 4. Attach evidence
        self.ev = Evidence(
            id="ev-review-test-1",
            project_id=self.project_id,
            finding_id=self.finding.id,
            source_label="01_income_statement.pdf",
            quoted_text="Total Revenue for FY 2025-26 was INR 100.00 crore.",
            extracted_value="100.00",
            validation_status="VERIFIED",
        )
        self.session.add(self.ev)

        self.session.commit()
        self.finding_service = FindingService(self.session)

    def tearDown(self):
        self._clean_db()
        self.session.close()

    def test_approve_finding_persists_decision_and_status(self):
        """Test APPROVE updates finding status to APPROVED and persists audit review."""
        res = self.finding_service.review(
            self.finding.id,
            action="APPROVE",
            reviewer="Partner Jane",
            comment="Auditor verified revenue match.",
        )

        self.assertEqual(res["finding"].status, "APPROVED")
        self.assertEqual(res["review"].action, "APPROVE")
        self.assertEqual(res["review"].reviewer, "Partner Jane")
        self.assertEqual(res["review"].comment, "Auditor verified revenue match.")
        self.assertIsNotNone(res["review"].reviewed_at)

        # Verify DB persistence
        reloaded = self.session.get(Finding, self.finding.id)
        self.assertEqual(reloaded.status, "APPROVED")
        self.assertEqual(len(reloaded.reviews), 1)

    def test_reject_finding_persists_decision_and_status(self):
        """Test REJECT updates finding status to REJECTED and persists audit review."""
        res = self.finding_service.review(
            self.finding.id,
            action="REJECT",
            reviewer="Analyst John",
            comment="Immaterial variance below threshold.",
        )

        self.assertEqual(res["finding"].status, "REJECTED")
        self.assertEqual(res["review"].action, "REJECT")
        self.assertEqual(res["review"].reviewer, "Analyst John")

        reloaded = self.session.get(Finding, self.finding.id)
        self.assertEqual(reloaded.status, "REJECTED")

    def test_request_more_evidence_creates_request_task_and_reanalysis(self):
        """Test REQUEST_MORE_EVIDENCE creates linked DDRequest, DDTask, and DDReanalysisRun."""
        res = self.finding_service.review(
            self.finding.id,
            action="REQUEST_MORE_EVIDENCE",
            reviewer="Senior Associate",
            comment="Need reconciliation against Q4 revenue breakdown.",
        )

        self.assertEqual(res["finding"].status, "MORE_EVIDENCE_REQUIRED")
        self.assertEqual(res["review"].action, "REQUEST_MORE_EVIDENCE")

        # Verify linked DDRequest
        request = res["request"]
        self.assertIsNotNone(request)
        self.assertEqual(request.status, "OPEN")
        self.assertEqual(request.finding_id, self.finding.id)
        self.assertIn("Q4 revenue breakdown", request.description)

        # Verify linked DDTask
        task = res["task"]
        self.assertIsNotNone(task)
        self.assertEqual(task.status, "TODO")
        self.assertEqual(task.request_id, request.id)
        self.assertEqual(task.finding_id, self.finding.id)

        # Verify linked DDReanalysisRun
        reanalysis = res["reanalysis"]
        self.assertIsNotNone(reanalysis)
        self.assertEqual(reanalysis.status, "QUEUED")
        self.assertEqual(reanalysis.finding_id, self.finding.id)
        self.assertEqual(reanalysis.request_id, request.id)

    def test_reanalysis_worker_run_once_success(self):
        """Test ReanalysisWorker picks up queued job, updates task/request, and returns finding to review."""
        # 1. Queue a reanalysis job via review
        res = self.finding_service.review(
            self.finding.id,
            action="REQUEST_MORE_EVIDENCE",
            reviewer="Reviewer Test",
            comment="Clarify gross profit calculation.",
        )
        run_id = res["reanalysis"].id

        # 2. Mock the agent runner so we do not call external heavy LLM in unit test
        mock_runner = MagicMock()
        mock_runner.run.return_value = {
            "status": "COMPLETE",
            "final_answer": "Re-analysis confirmed Gross Profit of INR 42.00 crore in 01_income_statement.pdf page 1.",
        }

        worker = ReanalysisWorker()
        worker.get_agent = MagicMock(return_value={"agent": MagicMock(name="financial_dd_agent"), "runner": mock_runner})

        # 3. Execute the worker on the queued run
        worker_res = worker.run_once(run_id=run_id)

        self.assertEqual(worker_res["status"], "COMPLETE")
        self.assertEqual(worker_res["finding_id"], self.finding.id)

        # 4. Verify DB state updates
        self.session.expire_all()
        updated_run = self.session.get(DDReanalysisRun, run_id)
        self.assertEqual(updated_run.status, "COMPLETE")
        self.assertIsNotNone(updated_run.completed_at)
        self.assertIn("Re-analysis confirmed Gross Profit", updated_run.result_summary)

        # Finding must be returned to REVIEW_REQUIRED with updated conclusion
        updated_finding = self.session.get(Finding, self.finding.id)
        self.assertEqual(updated_finding.status, "REVIEW_REQUIRED")
        self.assertIn("42.00 crore", updated_finding.evidence_conclusion)

        # Linked DDRequest and DDTask must be resolved/done
        updated_request = self.session.get(DDRequest, updated_run.request_id)
        self.assertEqual(updated_request.status, "RESOLVED")

        updated_task = self.session.query(DDTask).filter(DDTask.request_id == updated_run.request_id).first()
        self.assertEqual(updated_task.status, "DONE")

    def test_reanalysis_worker_failure_handling(self):
        """Test ReanalysisWorker honestly transitions to FAILED and records error message when an exception occurs."""
        res = self.finding_service.review(
            self.finding.id,
            action="REQUEST_MORE_EVIDENCE",
            reviewer="Reviewer Test",
            comment="Failing test run.",
        )
        run_id = res["reanalysis"].id

        # Mock runner to raise an exception
        mock_runner = MagicMock()
        mock_runner.run.side_effect = RuntimeError("Simulated agent connection failure")

        worker = ReanalysisWorker()
        worker.get_agent = MagicMock(return_value={"agent": MagicMock(name="financial_dd_agent"), "runner": mock_runner})

        worker_res = worker.run_once(run_id=run_id)

        self.assertEqual(worker_res["status"], "FAILED")
        self.assertIn("Simulated agent connection failure", worker_res["error"])

        # Verify DB records FAILED state and does not hang in RUNNING
        self.session.expire_all()
        updated_run = self.session.get(DDReanalysisRun, run_id)
        self.assertEqual(updated_run.status, "FAILED")
        self.assertIn("Simulated agent connection failure", updated_run.result_summary)

        updated_task = self.session.query(DDTask).filter(DDTask.request_id == updated_run.request_id).first()
        self.assertEqual(updated_task.status, "FAILED")

    def test_reanalysis_worker_no_work(self):
        """Test ReanalysisWorker gracefully reports NO_WORK when queue is empty."""
        worker = ReanalysisWorker()
        # Clean any queued runs first
        self.session.query(DDReanalysisRun).filter(DDReanalysisRun.status == "QUEUED").delete()
        self.session.commit()

        res = worker.run_once()
        self.assertEqual(res["status"], "NO_WORK")

    @patch("api.v1.findings.process_next_reanalysis")
    def test_review_api_endpoints(self, mock_process):
        """Test HTTP API endpoints for reviewing findings and fetching reanalysis status."""
        # 1. API: APPROVE
        resp_approve = self.client.post(
            f"/api/v1/findings/{self.finding.id}/review",
            json={"action": "APPROVE", "reviewer": "API Tester", "comment": "Approved via API"},
        )
        self.assertEqual(resp_approve.status_code, 200)
        self.assertEqual(resp_approve.json()["finding"]["status"], "APPROVED")

        # 2. API: REQUEST_MORE_EVIDENCE
        resp_req = self.client.post(
            f"/api/v1/findings/{self.finding.id}/review",
            json={"action": "REQUEST_MORE_EVIDENCE", "reviewer": "API Tester", "comment": "Need notes from 10-K"},
        )
        self.assertEqual(resp_req.status_code, 200)
        data = resp_req.json()
        self.assertEqual(data["finding"]["status"], "MORE_EVIDENCE_REQUIRED")
        self.assertIn("request", data)
        self.assertIn("reanalysis", data)
        mock_process.assert_called_once()

        # 3. API: List project reanalysis runs
        resp_list = self.client.get(f"/api/v1/reanalysis/project/{self.project_id}")
        self.assertEqual(resp_list.status_code, 200)
        self.assertGreaterEqual(len(resp_list.json()), 1)

    def test_recover_stale_jobs_resets_orphaned_runs_to_queued(self):
        """Test that orphaned runs left in RUNNING status from previous server crashes are recovered to QUEUED."""
        stale_run = DDReanalysisRun(
            id="run-stale-test-1",
            project_id=self.project_id,
            finding_id=self.finding.id,
            trigger_type="HUMAN_REVIEW",
            status="RUNNING",
            started_at=datetime.utcnow(),
        )
        self.session.add(stale_run)
        self.session.commit()

        worker = ReanalysisWorker()
        recovered = worker.recover_stale_jobs(self.session)

        self.assertGreaterEqual(recovered, 1)
        self.session.expire_all()
        reloaded = self.session.get(DDReanalysisRun, "run-stale-test-1")
        self.assertEqual(reloaded.status, "QUEUED")
        self.assertIsNone(reloaded.started_at)

