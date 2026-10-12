from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from database.session import Base, engine, SessionLocal
from evidence.models import Evidence
from findings.models import Finding
from retrieval.models.documents import Document, DocumentChunk
from retrieval.models.investigations import DDInvestigation
from retrieval.models.projects import DDProject
from services.orchestrator_service import (
    DDOrchestratorService,
    deduplicate_project_findings,
    validate_project_evidence,
)


class TestEvidenceValidation(unittest.TestCase):
    def setUp(self):
        self.session = SessionLocal()
        self.project_id = "TEST-ORCH-EV-001"

        # Create test project
        proj = self.session.get(DDProject, self.project_id)
        if not proj:
            proj = DDProject(
                id=self.project_id,
                name="Orchestrator Test Company",
                target_company="Test Corp",
            )
            self.session.add(proj)

        # Create test document and chunk
        self.doc = Document(
            id="doc-test-orch-1",
            project_id=self.project_id,
            file_name="01_income_statement.pdf",
            storage_key="test/01_income_statement.pdf",
            category="financial",
        )
        self.session.add(self.doc)

        self.chunk = DocumentChunk(
            id="chunk-test-orch-1",
            document_id=self.doc.id,
            chunk_index=0,
            content="Total Revenue for FY 2025-26 was INR 100.00 crore with Gross Profit of INR 42.00 crore.",
            page_number=1,
            section="Income Statement",
        )
        self.session.add(self.chunk)

        # Finding with valid quote
        self.finding_valid = Finding(
            id="find-orch-valid",
            project_id=self.project_id,
            workstream="financial",
            title="Revenue Verification",
            issue="Revenue confirmed from source table",
            risk_severity="low",
            confidence="high",
            status="REVIEW_REQUIRED",
        )
        self.session.add(self.finding_valid)

        self.ev_valid = Evidence(
            id="ev-orch-valid",
            project_id=self.project_id,
            finding_id=self.finding_valid.id,
            source_label="01_income_statement.pdf",
            quoted_text="Total Revenue for FY 2025-26 was INR 100.00 crore",
            extracted_value="100.00",
            validation_status="UNVERIFIED",
        )
        self.session.add(self.ev_valid)

        # Finding with hallucinated / fake quote
        self.finding_fake = Finding(
            id="find-orch-fake",
            project_id=self.project_id,
            workstream="financial",
            title="Invented Debt Claim",
            issue="Debt without proof",
            risk_severity="high",
            confidence="low",
            status="REVIEW_REQUIRED",
        )
        self.session.add(self.finding_fake)

        self.ev_fake = Evidence(
            id="ev-orch-fake",
            project_id=self.project_id,
            finding_id=self.finding_fake.id,
            source_label="01_income_statement.pdf",
            quoted_text="Undisclosed offshore debt of USD 500 million in bank accounts",
            extracted_value="500",
            validation_status="UNVERIFIED",
        )
        self.session.add(self.ev_fake)

        self.session.commit()

    def tearDown(self):
        # Clean up test rows
        self.session.query(Evidence).filter(Evidence.project_id == self.project_id).delete()
        self.session.query(Finding).filter(Finding.project_id == self.project_id).delete()
        self.session.query(DocumentChunk).filter(DocumentChunk.document_id == "doc-test-orch-1").delete()
        self.session.query(Document).filter(Document.id == "doc-test-orch-1").delete()
        self.session.query(DDProject).filter(DDProject.id == self.project_id).delete()
        self.session.commit()
        self.session.close()

    def test_evidence_validation_marks_real_as_verified_and_fake_as_unverified(self):
        res = validate_project_evidence(self.project_id, self.session)

        self.assertEqual(res["total_evidence"], 2)
        self.assertEqual(res["verified_count"], 1)
        self.assertEqual(res["unverified_count"], 1)

        # Refresh from DB
        ev_v = self.session.get(Evidence, "ev-orch-valid")
        ev_f = self.session.get(Evidence, "ev-orch-fake")

        self.assertEqual(ev_v.validation_status, "VERIFIED")
        self.assertEqual(ev_v.chunk_id, "chunk-test-orch-1")
        self.assertEqual(ev_v.page_number, 1)

        self.assertEqual(ev_f.validation_status, "UNVERIFIED")
        self.assertIsNone(ev_f.chunk_id)

    def test_deduplicate_project_findings(self):
        # Create a duplicate finding with identical workstream and title
        dup_finding = Finding(
            id="find-orch-dup",
            project_id=self.project_id,
            workstream="financial",
            title="Revenue Verification",
            issue="Duplicate revenue verification",
            risk_severity="low",
            confidence="high",
            status="REVIEW_REQUIRED",
        )
        self.session.add(dup_finding)
        self.session.commit()

        cleaned = deduplicate_project_findings(self.project_id, self.session)
        self.assertGreaterEqual(cleaned, 1)

        # Verify only one finding with that title remains
        remaining = self.session.query(Finding).filter(
            Finding.project_id == self.project_id,
            Finding.title == "Revenue Verification",
        ).all()
        self.assertEqual(len(remaining), 1)


class TestOrchestratorService(unittest.TestCase):
    def setUp(self):
        self.session = SessionLocal()
        self.project_id = "TEST-ORCH-SVC-001"

        proj = self.session.get(DDProject, self.project_id)
        if not proj:
            proj = DDProject(
                id=self.project_id,
                name="Svc Test Project",
                target_company="Svc Target Inc",
            )
            self.session.add(proj)
            self.session.commit()

        self.service = DDOrchestratorService()

    def tearDown(self):
        self.session.query(DDInvestigation).filter(DDInvestigation.project_id == self.project_id).delete()
        self.session.query(DDProject).filter(DDProject.id == self.project_id).delete()
        self.session.commit()
        self.session.close()

    @patch("services.orchestrator_service.PlannerService.start_investigation")
    def test_run_full_dd_skips_missing_documents_honestly(self, mock_planner):
        mock_planner.return_value = {
            "plan": {"summary": "Planned scope"},
            "iterations": 1,
        }

        # Project has no documents
        res = self.service.run_full_dd(project_id=self.project_id)

        self.assertTrue(res["success"])
        self.assertIn("stages", res)
        # Financial and Legal should be SKIPPED honestly because no documents exist
        self.assertEqual(res["stages"]["financial"]["status"], "SKIPPED")
        self.assertEqual(res["stages"]["legal"]["status"], "SKIPPED")
        self.assertEqual(res["stages"]["cross_domain"]["status"], "SKIPPED")
        self.assertEqual(res["stages"]["planner"]["status"], "SUCCESS")

    @patch("services.orchestrator_service.PlannerService.start_investigation")
    def test_run_full_dd_partial_failure_handling(self, mock_planner):
        mock_planner.side_effect = RuntimeError("Planner timeout")

        res = self.service.run_full_dd(project_id=self.project_id)

        # When the only active stage (planner) fails, status is not COMPLETED
        self.assertEqual(res["stages"]["planner"]["status"], "FAILED")
        self.assertIn("stage_errors", res)
        self.assertGreater(len(res["stage_errors"]), 0)


class TestOrchestratorAPI(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from app.new_main import app
        self.client = TestClient(app)

    def test_orchestrator_routes_exist(self):
        # Non-existent project returns 404
        response = self.client.post("/api/v1/projects/NON-EXISTENT-PROJECT-999/run-full-dd")
        self.assertEqual(response.status_code, 404)

        # Status check for non-existent returns 404
        status_resp = self.client.get("/api/v1/projects/NON-EXISTENT-PROJECT-999/orchestrator/status")
        self.assertEqual(status_resp.status_code, 404)
