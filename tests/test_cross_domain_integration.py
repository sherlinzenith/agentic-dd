from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.new_main import app
from database.session import SessionLocal
from evidence.models import Evidence
from findings.models import Finding, FindingReview
from findings.repository import FindingRepository
from retrieval.models.documents import Document, DocumentChunk
from retrieval.models.investigations import DDInvestigation
from retrieval.models.projects import DDProject
from services.orchestrator_service import (
    DDOrchestratorService,
    deduplicate_project_findings,
    validate_project_evidence,
)
from agents.cross_domain.tools import CrossDomainAgentTools


class TestCrossDomainIntegration(unittest.TestCase):
    def _clean_db(self):
        try:
            for inv in self.session.query(DDInvestigation).filter(DDInvestigation.project_id == self.project_id).all():
                self.session.delete(inv)
            for rev in self.session.query(FindingReview).all():
                if rev.finding_id in ["find-test-fin-1", "find-test-leg-1", "find-test-cross-1"]:
                    self.session.delete(rev)
            for ev in self.session.query(Evidence).filter(Evidence.project_id == self.project_id).all():
                self.session.delete(ev)
            for f in self.session.query(Finding).filter(Finding.project_id == self.project_id).all():
                self.session.delete(f)
            for c in self.session.query(DocumentChunk).all():
                if c.document_id in ["doc-test-fin-1", "doc-test-leg-1"]:
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
        self.project_id = "TEST-CROSS-DOMAIN-PROJ"
        self.session = SessionLocal()
        self.client = TestClient(app)

        self._clean_db()

        # 1. Test Project
        self.project = DDProject(
            id=self.project_id,
            name="CrossDomain Test Project",
            target_company="Stark Industries",
        )
        self.session.add(self.project)

        # 2. Financial Document & Chunk
        self.doc_fin = Document(
            id="doc-test-fin-1",
            project_id=self.project_id,
            file_name="financial_statement_2025.pdf",
            storage_key="test/financial_statement_2025.pdf",
            category="financial",
        )
        self.session.add(self.doc_fin)

        self.chunk_fin = DocumentChunk(
            id="chunk-test-fin-1",
            document_id=self.doc_fin.id,
            chunk_index=0,
            content="Total Outstanding Debt stands at USD 45,000,000 as of December 31, 2025.",
            page_number=1,
            section="Balance Sheet - Liabilities",
        )
        self.session.add(self.chunk_fin)

        # 3. Legal Document & Chunk
        self.doc_leg = Document(
            id="doc-test-leg-1",
            project_id=self.project_id,
            file_name="credit_facility_agreement.pdf",
            storage_key="test/credit_facility_agreement.pdf",
            category="legal",
        )
        self.session.add(self.doc_leg)

        self.chunk_leg = DocumentChunk(
            id="chunk-test-leg-1",
            document_id=self.doc_leg.id,
            chunk_index=0,
            content="The Borrower shall maintain Total Debt below USD 30,000,000. Breach constitutes an Event of Default.",
            page_number=1,
            section="Section 8.2 - Negative Covenants",
        )
        self.session.add(self.chunk_leg)
        self.session.flush()

        # 4. Financial Finding
        self.finding_fin = Finding(
            id="find-test-fin-1",
            project_id=self.project_id,
            workstream="financial",
            title="Elevated Debt Level",
            issue="Company carries USD 45,000,000 in total debt obligations",
            why_it_matters="High debt load increases debt service requirements",
            evidence_conclusion="Balance sheet confirms 45M debt load.",
            status="REVIEW_REQUIRED",
            risk_severity="high",
            confidence="0.95",
        )
        self.session.add(self.finding_fin)

        self.ev_fin = Evidence(
            id="ev-test-fin-1",
            project_id=self.project_id,
            finding_id=self.finding_fin.id,
            document_id=self.doc_fin.id,
            chunk_id=self.chunk_fin.id,
            source_label="financial_statement_2025.pdf",
            quoted_text="Total Outstanding Debt stands at USD 45,000,000",
            extracted_value="45000000",
            validation_status="VERIFIED",
        )
        self.session.add(self.ev_fin)

        # 5. Legal Finding
        self.finding_leg = Finding(
            id="find-test-leg-1",
            project_id=self.project_id,
            workstream="legal",
            title="Credit Facility Debt Ceiling Covenant",
            issue="Credit Agreement restricts total borrowings to USD 30,000,000",
            why_it_matters="Exceeding limit triggers default and immediate repayment acceleration",
            evidence_conclusion="Section 8.2 establishes 30M debt cap.",
            status="REVIEW_REQUIRED",
            risk_severity="high",
            confidence="0.90",
        )
        self.session.add(self.finding_leg)

        self.ev_leg = Evidence(
            id="ev-test-leg-1",
            project_id=self.project_id,
            finding_id=self.finding_leg.id,
            document_id=self.doc_leg.id,
            chunk_id=self.chunk_leg.id,
            source_label="credit_facility_agreement.pdf",
            quoted_text="maintain Total Debt below USD 30,000,000. Breach constitutes an Event of Default.",
            extracted_value="30000000",
            validation_status="VERIFIED",
        )
        self.session.add(self.ev_leg)

        self.session.commit()
        self.orchestrator = DDOrchestratorService()

    def tearDown(self):
        self._clean_db()
        self.session.close()

    def test_compare_findings_identifies_cross_domain_risk_correlation(self):
        """Test CrossDomainAgentTools.compare_findings detects debt-covenant conflict between workstreams."""
        tools = CrossDomainAgentTools()
        fin_list = [{
            "id": self.finding_fin.id,
            "title": self.finding_fin.title,
            "issue": self.finding_fin.issue,
            "workstream": "financial",
        }]
        leg_list = [{
            "id": self.finding_leg.id,
            "title": self.finding_leg.title,
            "issue": self.finding_leg.issue,
            "workstream": "legal",
        }]

        result = tools.compare_findings(financial_findings=fin_list, legal_findings=leg_list)

        self.assertTrue(result["comparison_ready"])
        self.assertEqual(result["financial_count"], 1)
        self.assertEqual(result["legal_count"], 1)
        self.assertGreaterEqual(len(result["correlations"]), 1)
        self.assertEqual(result["correlations"][0]["type"], "DEBT_COVENANT_RISK")

    def test_record_cross_domain_finding_grounds_and_validates_evidence(self):
        """Test record_cross_domain_finding links supporting findings' evidence and runs validation."""
        tools = CrossDomainAgentTools()

        payload = {
            "title": "Debt Covenant Breach and Default Risk",
            "issue": "Reported debt of 45M exceeds the 30M restrictive ceiling in Credit Agreement",
            "why_it_matters": "Lenders can immediately accelerate repayment, risking insolvency",
            "conclusion": "Cross-domain contradiction verified between financial balance sheet and credit agreement.",
            "risk_level": "high",
            "confidence": 0.95,
            "supporting_finding_ids": [self.finding_fin.id, self.finding_leg.id],
        }

        res = tools.record_cross_domain_finding(finding=payload, project_id=self.project_id)

        self.assertTrue(res["recorded"])
        finding_id = res["finding_id"]

        self.session.expire_all()
        created_finding = self.session.get(Finding, finding_id)
        self.assertIsNotNone(created_finding)
        self.assertEqual(created_finding.workstream, "cross_domain")
        self.assertEqual(created_finding.project_id, self.project_id)
        # Check that evidence was automatically linked and validated from supporting findings
        self.assertGreaterEqual(len(created_finding.evidence), 2)
        verified_count = sum(1 for e in created_finding.evidence if e.validation_status == "VERIFIED")
        self.assertGreaterEqual(verified_count, 1)

    def test_handoff_financial_and_legal_to_cross_domain_in_orchestrator(self):
        """Test orchestrator gathers all findings and evidence and correctly passes them to Cross-Domain Agent."""
        captured_handoff = {}

        def mock_cross_investigate(*args, **kwargs):
            captured_handoff["project_id"] = kwargs.get("project_id")
            captured_handoff["initial_findings"] = kwargs.get("initial_findings")
            captured_handoff["initial_evidence"] = kwargs.get("initial_evidence")
            captured_handoff["objective"] = kwargs.get("objective")
            return {
                "iteration": 1,
                "tool_calls": ["compare_findings"],
                "final_answer": "Cross-domain analysis identified severe debt covenant violation.",
            }

        mock_cross_agent = MagicMock()
        mock_cross_agent.investigate = mock_cross_investigate

        with patch("agents.cross_domain.agent.create_cross_domain_agent", return_value=mock_cross_agent), \
             patch("services.planner_service.PlannerService.start_investigation", return_value={"iterations": 1}), \
             patch("agents.financial.agent.create_financial_agent"), \
             patch("agents.engine.runner.AgentRunner.run", return_value={"iteration": 1, "tool_calls": []}), \
             patch("agents.legal.agent.create_legal_agent") as mock_leg:

            mock_leg.return_value.investigate.return_value = {"iteration": 1, "tool_calls": []}

            res = self.orchestrator.run_full_dd(project_id=self.project_id)

            self.assertEqual(res["overall_status"], "COMPLETED")
            self.assertEqual(res["stages"]["cross_domain"]["status"], "SUCCESS")

            # Verify handoff contents
            self.assertEqual(captured_handoff["project_id"], self.project_id)
            findings_passed = captured_handoff["initial_findings"]
            self.assertGreaterEqual(len(findings_passed), 2)
            workstreams_passed = {f["workstream"] for f in findings_passed}
            self.assertIn("financial", workstreams_passed)
            self.assertIn("legal", workstreams_passed)

            evidence_passed = captured_handoff["initial_evidence"]
            self.assertGreaterEqual(len(evidence_passed), 2)

    def test_cross_domain_explicitly_skipped_when_legal_domain_missing(self):
        """Test Cross-Domain produces explicit SKIPPED state when one domain is completely absent."""
        # Delete legal document and legal finding
        self.session.delete(self.ev_leg)
        self.session.delete(self.finding_leg)
        self.session.delete(self.chunk_leg)
        self.session.delete(self.doc_leg)
        self.session.commit()

        with patch("services.planner_service.PlannerService.start_investigation", return_value={"iterations": 1}), \
             patch("agents.engine.runner.AgentRunner.run", return_value={"iteration": 1, "tool_calls": []}):

            res = self.orchestrator.run_full_dd(project_id=self.project_id)

            self.assertEqual(res["stages"]["legal"]["status"], "SKIPPED")
            self.assertEqual(res["stages"]["cross_domain"]["status"], "SKIPPED")
            self.assertIn("No legal documents or findings available", res["stages"]["cross_domain"]["reason"])

    def test_partial_agent_failure_does_not_discard_successful_agent_findings(self):
        """Test that if Legal Agent fails, Financial findings are preserved and status is PARTIAL_FAILURE."""
        with patch("services.planner_service.PlannerService.start_investigation", return_value={"iterations": 1}), \
             patch("agents.engine.runner.AgentRunner.run", return_value={"iteration": 1, "tool_calls": []}), \
             patch("agents.legal.agent.create_legal_agent") as mock_leg:

            mock_leg.return_value.investigate.side_effect = RuntimeError("Contract parsing failure")

            res = self.orchestrator.run_full_dd(project_id=self.project_id)

            self.assertEqual(res["overall_status"], "PARTIAL_FAILURE")
            self.assertEqual(res["stages"]["legal"]["status"], "FAILED")
            self.assertIn("Contract parsing failure", res["stages"]["legal"]["error"])

            # Financial finding MUST be preserved in the DB
            self.session.expire_all()
            reloaded_fin = self.session.get(Finding, self.finding_fin.id)
            self.assertIsNotNone(reloaded_fin)
            self.assertEqual(reloaded_fin.title, "Elevated Debt Level")

    def test_deduplication_preserves_human_review_history_and_evidence(self):
        """Test deduplicate_project_findings preserves reviewer audit trail and status on pipeline reruns."""
        # 1. Add human review to the primary finding
        repo = FindingRepository(self.session)
        review = repo.add_review(
            finding=self.finding_fin,
            action="APPROVE",
            reviewer="Partner Dave",
            comment="Audited and approved debt reconciliation",
        )
        self.finding_fin.status = "APPROVED"
        self.session.commit()

        # 2. Simulate pipeline rerun creating a duplicate unreviewed finding with identical workstream & title
        dup_finding = Finding(
            id="find-test-fin-dup",
            project_id=self.project_id,
            workstream="financial",
            title="Elevated Debt Level",
            issue="Duplicate run finding",
            status="REVIEW_REQUIRED",
            risk_severity="high",
            confidence="0.80",
        )
        self.session.add(dup_finding)
        self.session.commit()

        # 3. Run deduplication
        cleaned = deduplicate_project_findings(self.project_id, self.session)
        self.assertEqual(cleaned, 1)

        # 4. Confirm the approved finding and its review history are completely intact
        self.session.expire_all()
        preserved = self.session.get(Finding, self.finding_fin.id)
        self.assertIsNotNone(preserved)
        self.assertEqual(preserved.status, "APPROVED")
        self.assertEqual(len(preserved.reviews), 1)
        self.assertEqual(preserved.reviews[0].reviewer, "Partner Dave")
        self.assertEqual(preserved.reviews[0].comment, "Audited and approved debt reconciliation")

    def test_orchestrator_api_endpoints(self):
        """Test API endpoints for starting orchestration and inspecting status."""
        with patch.object(DDOrchestratorService, "run_full_dd") as mock_run:
            mock_run.return_value = {
                "overall_status": "COMPLETED",
                "investigation_id": "inv-123",
                "project_id": self.project_id,
                "stages": {
                    "planner": {"status": "SUCCESS"},
                    "financial": {"status": "SUCCESS"},
                    "legal": {"status": "SUCCESS"},
                    "cross_domain": {"status": "SUCCESS"},
                    "evidence_validation": {"status": "SUCCESS"},
                },
                "stage_errors": [],
                "findings_count": 2,
            }

            resp = self.client.post(
                f"/api/v1/projects/{self.project_id}/run-full-dd",
                json={"objective": "Test full DD", "max_agent_iterations": 2},
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["overall_status"], "COMPLETED")
            self.assertEqual(data["findings_count"], 2)
            self.assertIn("cross_domain", data["stages"])
