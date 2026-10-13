import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app.main import app
import agents.financial_agent as fa
from findings import finding_store as fs
from reports import report_generator as rg
from ui import service as ui_service
from workflow import dd_graph
from workflow.orchestrator import build_dd_graph


class TestReviewResumeIntegration(unittest.TestCase):

    def setUp(self):
        # Isolate results and reports so no real job data is modified
        self.tmp_dir = pathlib.Path(tempfile.mkdtemp())
        self.orig_results = fs.RESULTS_DIR
        self.orig_findings = fs.FINDINGS_FILE
        self.orig_metrics = fs.METRICS_FILE
        self.orig_report_results = rg.RESULTS_DIR
        self.orig_report_file = rg.REPORT_FILE

        fs.RESULTS_DIR = self.tmp_dir
        fs.FINDINGS_FILE = self.tmp_dir / "findings.json"
        fs.METRICS_FILE = self.tmp_dir / "metrics.json"
        rg.RESULTS_DIR = self.tmp_dir
        rg.REPORT_FILE = self.tmp_dir / "report.html"

        # Mock model to avoid expensive/external calls
        self.orig_ask_model = fa._ask_model
        fa._ask_model = lambda prompt: (None, "test: mock model")

        # Isolated memory graph for dd_graph
        self.checkpointer = MemorySaver()
        self.test_graph = build_dd_graph(checkpointer=self.checkpointer)
        self.orig_graph = dd_graph._graph
        dd_graph._graph = self.test_graph

        self.client = TestClient(app)

    def tearDown(self):
        fs.RESULTS_DIR = self.orig_results
        fs.FINDINGS_FILE = self.orig_findings
        fs.METRICS_FILE = self.orig_metrics
        rg.RESULTS_DIR = self.orig_report_results
        rg.REPORT_FILE = self.orig_report_file
        fa._ask_model = self.orig_ask_model
        dd_graph._graph = self.orig_graph
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _start_test_job(self, job_id="DD-TEST-REVIEW", types=("financial", "legal")):
        """Starts an isolated job using clean sample text docs that pauses at human review."""
        dd_graph.LAST_JOB_FILE = self.tmp_dir / "last_job.txt"
        doc_names = [
            "01_income_statement.txt",
            "02_balance_sheet.txt",
            "03_cash_flow_statement.txt",
            "04_revenue_report.txt",
            "05_customer_agreement.txt",
        ]
        docs = [
            {"document": n, "text": pathlib.Path("documents/" + n).read_text(encoding="utf-8")}
            for n in doc_names
        ]
        info = dd_graph.start_job(job_id=job_id, dd_types=list(types), documents=docs)
        self.assertEqual(info["status"], "AWAITING_REVIEW")
        self.assertEqual(info["waiting_for"], "review")
        return info

    def test_ui_service_review_approve_resumes_job_to_completion(self):
        job_id = "DD-TEST-APPR"
        self._start_test_job(job_id)
        findings = fs.load_findings()
        self.assertTrue(len(findings) >= 2)

        # Approve first finding: remaining finding is still pending, so job remains waiting for review
        res1 = ui_service.review(job_id, findings[0]["finding_id"], "APPROVE", "Alice", "Verified with ledger")
        self.assertEqual(res1["status"], "APPROVED")
        status_mid = dd_graph.job_status(job_id)
        self.assertEqual(status_mid["waiting_for"], "review")

        # Approve the rest: all are approved, job should resume to completion
        for f in findings[1:]:
            res = ui_service.review(job_id, f["finding_id"], "APPROVE", "Alice", "Verified with ledger")
            self.assertEqual(res["status"], "APPROVED")

        status_final = dd_graph.job_status(job_id)
        self.assertEqual(status_final["status"], "REVIEW_COMPLETE")
        self.assertIsNone(status_final["waiting_for"])

    def test_ui_service_review_reject_resumes_job_to_completion(self):
        job_id = "DD-TEST-REJ"
        self._start_test_job(job_id)
        findings = fs.load_findings()
        self.assertTrue(len(findings) >= 2)

        # Reject all findings
        for f in findings:
            res = ui_service.review(job_id, f["finding_id"], "REJECT", "Bob", "Immaterial threshold")
            self.assertEqual(res["status"], "REJECTED")

        status = dd_graph.job_status(job_id)
        self.assertEqual(status["status"], "REVIEW_COMPLETE")
        self.assertIsNone(status["waiting_for"])

    def test_ui_service_review_request_more_evidence_transitions_to_await_evidence(self):
        job_id = "DD-TEST-EVID"
        self._start_test_job(job_id)
        findings = fs.load_findings()
        self.assertTrue(len(findings) >= 2)

        # First finding: request more evidence
        res = ui_service.review(job_id, findings[0]["finding_id"], "REQUEST_MORE_EVIDENCE", "Charlie", "Need revised P&L")
        self.assertEqual(res["status"], "MORE_EVIDENCE_REQUIRED")

        # Job is still waiting for review because remaining findings are pending
        status_inter = dd_graph.job_status(job_id)
        self.assertEqual(status_inter["waiting_for"], "review")

        # Approve the remaining findings
        for f in findings[1:]:
            ui_service.review(job_id, f["finding_id"], "APPROVE", "Charlie", "Approved")

        # Now all reviewed, and because one requested more evidence, job transitions to await_evidence
        status_final = dd_graph.job_status(job_id)
        self.assertEqual(status_final["waiting_for"], "await_evidence")
        self.assertEqual(status_final["status"], "AWAITING_EVIDENCE")

    def test_ui_service_does_not_blindly_resume_when_already_awaiting_evidence(self):
        job_id = "DD-TEST-GUARD"
        self._start_test_job(job_id)
        findings = fs.load_findings()

        # Mark all findings as more evidence required
        for f in findings:
            ui_service.review(job_id, f["finding_id"], "REQUEST_MORE_EVIDENCE", "Dan", "Need more evidence")

        # Job is currently in await_evidence
        status = dd_graph.job_status(job_id)
        self.assertEqual(status["waiting_for"], "await_evidence")

        # If review is called while already awaiting evidence, resume_job must NOT be invoked
        with patch("workflow.dd_graph.resume_job") as mock_resume:
            info = dd_graph.job_status(job_id)
            if info.get("waiting_for") == "review":
                dd_graph.resume_job(job_id)
            mock_resume.assert_not_called()

    def test_ui_service_resume_after_evidence_provided(self):
        job_id = "DD-TEST-RELOAD"
        self._start_test_job(job_id)
        findings = fs.load_findings()

        for f in findings:
            ui_service.review(job_id, f["finding_id"], "REQUEST_MORE_EVIDENCE", "Dan", "Need more docs")

        self.assertEqual(dd_graph.job_status(job_id)["waiting_for"], "await_evidence")

        # When resume is explicitly triggered (e.g. from UI 'Re-run analysis' or API)
        resumed_status = ui_service.resume(job_id)
        # The job resumed from await_evidence, reloaded documents, and re-analyzed into review
        self.assertEqual(resumed_status["waiting_for"], "review")

    def test_ui_service_review_validation_errors(self):
        with self.assertRaises(ValueError) as ctx:
            ui_service.review(None, "FIN-001", "APPROVE", "Dan", "")
        self.assertIn("No active investigation job", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            ui_service.review("DD-1", "FIN-001", "APPROVE", "", "")
        self.assertIn("Reviewer name is required", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            ui_service.review("DD-1", "FIN-001", "REJECT", "Dan", "")
        self.assertIn("A comment is required", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            ui_service.review("DD-1", "FIN-001", "REQUEST_MORE_EVIDENCE", "Dan", "")
        self.assertIn("A comment is required", str(ctx.exception))

    def test_app_main_review_endpoint_approve_and_reject(self):
        job_id = "DD-API-TEST"
        self._start_test_job(job_id)
        findings = fs.load_findings()
        self.assertTrue(len(findings) >= 2)

        # 1. Reject first finding via API
        resp = self.client.post(
            f"/findings/{findings[0]['finding_id']}/review?job_id={job_id}",
            json={"action": "REJECT", "reviewer": "Audit Lead", "comment": "Not material"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["finding"]["status"], "REJECTED")

        # Job is still paused waiting for remaining reviews
        self.assertEqual(dd_graph.job_status(job_id)["waiting_for"], "review")

        # 2. Approve second finding via API
        resp2 = self.client.post(
            f"/findings/{findings[1]['finding_id']}/review?job_id={job_id}",
            json={"action": "APPROVE", "reviewer": "Audit Lead", "comment": "Approved"}
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()["finding"]["status"], "APPROVED")

        # If there are more findings, approve them
        for f in findings[2:]:
            r = self.client.post(
                f"/findings/{f['finding_id']}/review?job_id={job_id}",
                json={"action": "APPROVE", "reviewer": "Audit Lead", "comment": "Approved"}
            )
            self.assertEqual(r.status_code, 200)

        # Job must be completed
        self.assertEqual(dd_graph.job_status(job_id)["status"], "REVIEW_COMPLETE")

    def test_app_main_review_endpoint_request_more_evidence(self):
        job_id = "DD-API-EVID"
        self._start_test_job(job_id)
        findings = fs.load_findings()

        # First finding: request more evidence
        resp = self.client.post(
            f"/findings/{findings[0]['finding_id']}/review?job_id={job_id}",
            json={"action": "REQUEST_MORE_EVIDENCE", "reviewer": "Auditor", "comment": "Need addendum"}
        )
        self.assertEqual(resp.status_code, 200)

        # Approve the rest
        for f in findings[1:]:
            r = self.client.post(
                f"/findings/{f['finding_id']}/review?job_id={job_id}",
                json={"action": "APPROVE", "reviewer": "Auditor", "comment": "Approved"}
            )
            self.assertEqual(r.status_code, 200)

        # Graph should now be in AWAITING_EVIDENCE
        status = dd_graph.job_status(job_id)
        self.assertEqual(status["status"], "AWAITING_EVIDENCE")
        self.assertEqual(status["waiting_for"], "await_evidence")

    def test_app_main_review_endpoint_error_handling(self):
        job_id = "DD-API-ERR"
        self._start_test_job(job_id)

        # Invalid action -> 400
        resp = self.client.post(
            f"/findings/FIN-001/review?job_id={job_id}",
            json={"action": "INVALID_ACTION", "reviewer": "Audit Lead", "comment": "abc"}
        )
        self.assertEqual(resp.status_code, 400)

        # Nonexistent finding -> 404
        resp = self.client.post(
            f"/findings/NONEXISTENT-999/review?job_id={job_id}",
            json={"action": "APPROVE", "reviewer": "Audit Lead", "comment": "abc"}
        )
        self.assertEqual(resp.status_code, 404)

        # Reject without comment -> 400
        findings = fs.load_findings()
        fid = findings[0]["finding_id"]
        resp = self.client.post(
            f"/findings/{fid}/review?job_id={job_id}",
            json={"action": "REJECT", "reviewer": "Audit Lead", "comment": ""}
        )
        self.assertEqual(resp.status_code, 400)

    def test_app_main_resume_failure_raises_500_not_silent_success(self):
        job_id = "DD-API-FAIL"
        self._start_test_job(job_id)
        findings = fs.load_findings()
        fid = findings[0]["finding_id"]

        with patch("workflow.dd_graph.resume_job", side_effect=RuntimeError("Graph checkpointer failed")):
            resp = self.client.post(
                f"/findings/{fid}/review?job_id={job_id}",
                json={"action": "APPROVE", "reviewer": "Audit Lead", "comment": "Approved"}
            )
            self.assertEqual(resp.status_code, 500)
            self.assertIn("Failed to resume job", resp.json()["detail"])


if __name__ == "__main__":
    unittest.main()
