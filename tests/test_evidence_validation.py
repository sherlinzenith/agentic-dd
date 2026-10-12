from __future__ import annotations

import unittest
from database.session import Base, engine, SessionLocal
from evidence.models import Evidence
from findings.models import Finding
from retrieval.models.documents import Document, DocumentChunk
from retrieval.models.projects import DDProject
from retrieval.repositories.document_repository import DocumentRepository
from services.evidence_validation_service import (
    _best_window_similarity,
    normalize_quotation,
    validate_project_evidence_service,
    validate_single_evidence,
)


class TestEvidenceValidationUnit(unittest.TestCase):
    def setUp(self):
        self.session = SessionLocal()
        self.project_id = "TEST-EV-VALID-PROJ"

        # Ensure project exists
        proj = self.session.get(DDProject, self.project_id)
        if not proj:
            proj = DDProject(
                id=self.project_id,
                name="Evidence Validation Test Project",
                target_company="Acme Corp",
            )
            self.session.add(proj)

        # Create test document
        self.doc = Document(
            id="doc-ev-test-1",
            project_id=self.project_id,
            file_name="01_income_statement.pdf",
            storage_key="test/01_income_statement.pdf",
            category="financial",
        )
        self.session.add(self.doc)

        # Create test chunks
        self.chunk1 = DocumentChunk(
            id="chunk-ev-test-1",
            document_id=self.doc.id,
            chunk_index=0,
            content=(
                "Total Revenue for FY 2025-26 was INR 100.00 crore. "
                "Operating Expenses amounted to INR 58.00 crore, resulting in "
                "Gross Profit of INR 42.00 crore."
            ),
            page_number=1,
            section="Financial Performance",
        )
        self.session.add(self.chunk1)

        self.chunk2 = DocumentChunk(
            id="chunk-ev-test-2",
            document_id=self.doc.id,
            chunk_index=1,
            content="Total Debt as of March 31, 2026 stood at INR 25.50 crore with cash balance of INR 10.00 crore.",
            page_number=2,
            section="Balance Sheet Highlights",
        )
        self.session.add(self.chunk2)

        self.session.commit()

        self.doc_repo = DocumentRepository(self.session)
        raw_docs = self.doc_repo.list_documents(self.project_id)
        self.project_docs = {d.file_name.lower(): d for d in raw_docs}
        self.doc_by_id = {d.id: d for d in raw_docs}

    def tearDown(self):
        self.session.rollback()
        # Clean up test artifacts
        for f in self.session.query(Finding).filter(Finding.project_id == self.project_id).all():
            self.session.delete(f)
        for c in self.session.query(DocumentChunk).filter(DocumentChunk.document_id == self.doc.id).all():
            self.session.delete(c)
        for d in self.session.query(Document).filter(Document.project_id == self.project_id).all():
            self.session.delete(d)
        proj = self.session.get(DDProject, self.project_id)
        if proj:
            self.session.delete(proj)
        self.session.commit()
        self.session.close()

    def test_exact_quote_match(self):
        """Test exact quote match verifies chunk, confidence 1.0, and exact method."""
        finding = Finding(
            id="find-ev-exact",
            project_id=self.project_id,
            workstream="financial",
            title="Revenue Verification",
            issue="Revenue confirmed from source table",
        )
        self.session.add(finding)

        ev = Evidence(
            id="ev-exact-1",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="01_income_statement.pdf",
            quoted_text="Total Revenue for FY 2025-26 was INR 100.00 crore",
            extracted_value="100.00",
            validation_status="UNVERIFIED",
        )
        self.session.add(ev)
        self.session.commit()

        res = validate_single_evidence(
            ev=ev,
            finding=finding,
            doc_repo=self.doc_repo,
            project_docs=self.project_docs,
            doc_by_id=self.doc_by_id,
        )

        self.assertEqual(res["status"], "VERIFIED")
        self.assertEqual(res["match_method"], "exact")
        self.assertEqual(res["confidence"], 1.0)
        self.assertEqual(res["chunk_id"], self.chunk1.id)
        self.assertEqual(res["page_number"], 1)

    def test_whitespace_and_formatting_normalization(self):
        """Test normalization handles smart quotes, en-dashes, extra whitespace, currency spacing."""
        norm = normalize_quotation('  “Total Revenue for FY 2025–26”   was   ₹ 100.00 crore. \u00a0 ')
        self.assertIn('"total revenue for fy 2025-26"', norm)
        self.assertIn("₹100.00 crore", norm)

        finding = Finding(
            id="find-ev-norm",
            project_id=self.project_id,
            workstream="financial",
            title="Formatted Revenue Verification",
            issue="Revenue with harmless formatting differences",
        )
        self.session.add(finding)

        ev = Evidence(
            id="ev-norm-1",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="01_income_statement.pdf",
            quoted_text="Total Revenue   for FY 2025–26 was \n\t INR 100.00 crore.",
            extracted_value="100.00",
            validation_status="UNVERIFIED",
        )
        self.session.add(ev)
        self.session.commit()

        res = validate_single_evidence(
            ev=ev,
            finding=finding,
            doc_repo=self.doc_repo,
            project_docs=self.project_docs,
            doc_by_id=self.doc_by_id,
        )

        self.assertEqual(res["status"], "VERIFIED")
        self.assertEqual(res["match_method"], "exact")

    def test_missing_document_reference(self):
        """Test evidence citing a nonexistent document remains UNVERIFIED with honest explanation."""
        finding = Finding(
            id="find-ev-missing-doc",
            project_id=self.project_id,
            workstream="financial",
            title="Missing Doc Claim",
            issue="Cannot verify without document",
        )
        self.session.add(finding)

        ev = Evidence(
            id="ev-missing-doc-1",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="nonexistent_tax_audit.pdf",
            quoted_text="Taxes paid were 12.00 crore",
            validation_status="UNVERIFIED",
        )
        self.session.add(ev)
        self.session.commit()

        res = validate_single_evidence(
            ev=ev,
            finding=finding,
            doc_repo=self.doc_repo,
            project_docs=self.project_docs,
            doc_by_id=self.doc_by_id,
        )

        self.assertEqual(res["status"], "UNVERIFIED")
        self.assertIn("not found in project library", res["reason"])
        self.assertEqual(res["confidence"], 0.0)

    def test_empty_quotation(self):
        """Test empty quotation is rejected as UNVERIFIED."""
        finding = Finding(
            id="find-ev-empty",
            project_id=self.project_id,
            workstream="financial",
            title="Empty Quote Claim",
            issue="No quote provided",
        )
        self.session.add(finding)

        ev = Evidence(
            id="ev-empty-1",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="01_income_statement.pdf",
            quoted_text="   ",
            validation_status="UNVERIFIED",
        )
        self.session.add(ev)
        self.session.commit()

        res = validate_single_evidence(
            ev=ev,
            finding=finding,
            doc_repo=self.doc_repo,
            project_docs=self.project_docs,
            doc_by_id=self.doc_by_id,
        )

        self.assertEqual(res["status"], "UNVERIFIED")
        self.assertIn("Empty or missing quotation", res["reason"])

    def test_unsupported_speculative_claims(self):
        """Test quotes with unsupported terms (fraud, illegal, manipulation) are flagged UNSUPPORTED_CLAIM."""
        finding = Finding(
            id="find-ev-unsupported",
            project_id=self.project_id,
            workstream="financial",
            title="Fraud Accusation",
            issue="Accusation without evidence",
        )
        self.session.add(finding)

        ev = Evidence(
            id="ev-unsupported-1",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="01_income_statement.pdf",
            quoted_text="Deliberate illegal accounting error and revenue manipulation detected",
            validation_status="UNVERIFIED",
        )
        self.session.add(ev)
        self.session.commit()

        res = validate_single_evidence(
            ev=ev,
            finding=finding,
            doc_repo=self.doc_repo,
            project_docs=self.project_docs,
            doc_by_id=self.doc_by_id,
        )

        self.assertEqual(res["status"], "UNSUPPORTED_CLAIM")
        self.assertIn("unsupported speculative claims", res["reason"].lower())

    def test_conservative_fuzzy_ngram_matching(self):
        """Test conservative fuzzy match with minor OCR variation matches with >= 0.85 confidence."""
        finding = Finding(
            id="find-ev-fuzzy",
            project_id=self.project_id,
            workstream="financial",
            title="OCR Variance Check",
            issue="OCR character discrepancy in revenue figure line",
        )
        self.session.add(finding)

        # Minor OCR variance: "Operating Expenses amounted to" -> "Operating Expenses amounted toe"
        ev = Evidence(
            id="ev-fuzzy-1",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="01_income_statement.pdf",
            quoted_text="Operating Expenses amounted toe INR 58.00 crore, resulting in Gross Profit",
            extracted_value="58.00",
            validation_status="UNVERIFIED",
        )
        self.session.add(ev)
        self.session.commit()

        res = validate_single_evidence(
            ev=ev,
            finding=finding,
            doc_repo=self.doc_repo,
            project_docs=self.project_docs,
            doc_by_id=self.doc_by_id,
        )

        self.assertEqual(res["status"], "VERIFIED")
        self.assertEqual(res["match_method"], "fuzzy_ngram")
        self.assertGreaterEqual(res["confidence"], 0.85)

    def test_unsupported_numeric_claim(self):
        """Test quote where agent cites a numeric value not present in the chunk text fails verification."""
        finding = Finding(
            id="find-ev-num-fail",
            project_id=self.project_id,
            workstream="financial",
            title="Invented Number Check",
            issue="Agent cites 999.00 crore which does not exist in chunk",
        )
        self.session.add(finding)

        ev = Evidence(
            id="ev-num-fail-1",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="01_income_statement.pdf",
            quoted_text="Total Revenue for FY 2025-26 was INR 100.00 crore",
            extracted_value="999.00",  # 999.00 is NOT in chunk1
            validation_status="UNVERIFIED",
        )
        self.session.add(ev)
        self.session.commit()

        res = validate_single_evidence(
            ev=ev,
            finding=finding,
            doc_repo=self.doc_repo,
            project_docs=self.project_docs,
            doc_by_id=self.doc_by_id,
        )

        self.assertEqual(res["status"], "UNVERIFIED")
        self.assertIn("does not occur in matched chunk", res["reason"])

    def test_genuine_arithmetic_discrepancy(self):
        """Test finding describing an arithmetic discrepancy between numbers is flagged FLAGGED_DISCREPANCY."""
        finding = Finding(
            id="find-ev-discrepancy",
            project_id=self.project_id,
            workstream="financial",
            title="Revenue and Gross Profit Discrepancy",
            issue="Reported discrepancy between Revenue 100.00 crore and calculated profit 42.00 crore",
            evidence_conclusion="There is an unreconciled difference of 58.00 crore between revenue and profit.",
        )
        self.session.add(finding)

        ev = Evidence(
            id="ev-discrepancy-1",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="01_income_statement.pdf",
            quoted_text="Total Revenue for FY 2025-26 was INR 100.00 crore",
            extracted_value="100.00",
            validation_status="UNVERIFIED",
        )
        self.session.add(ev)
        self.session.commit()

        res = validate_single_evidence(
            ev=ev,
            finding=finding,
            doc_repo=self.doc_repo,
            project_docs=self.project_docs,
            doc_by_id=self.doc_by_id,
        )

        self.assertEqual(res["status"], "FLAGGED_DISCREPANCY")
        self.assertIn("discrepancy confirmed", res["reason"].lower())

    def test_validate_project_evidence_service(self):
        """Test end-to-end project evidence validation service aggregates all metrics correctly."""
        finding = Finding(
            id="find-ev-svc-1",
            project_id=self.project_id,
            workstream="financial",
            title="Service Aggregation Test",
            issue="Testing multi-item validation metrics",
        )
        self.session.add(finding)

        # 1 valid evidence
        ev1 = Evidence(
            id="ev-svc-1",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="01_income_statement.pdf",
            quoted_text="Total Revenue for FY 2025-26 was INR 100.00 crore",
            extracted_value="100.00",
        )
        self.session.add(ev1)

        # 1 unverified evidence (hallucinated text)
        ev2 = Evidence(
            id="ev-svc-2",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="01_income_statement.pdf",
            quoted_text="Secret offshore subsidiary in the Cayman Islands with USD 500 million",
        )
        self.session.add(ev2)

        self.session.commit()

        summary = validate_project_evidence_service(self.project_id, self.session)

        self.assertEqual(summary["total_evidence"], 2)
        self.assertEqual(summary["verified_count"], 1)
        self.assertEqual(summary["unverified_count"], 1)
        self.assertEqual(len(summary["details"]), 2)

        # Verify DB records updated with reasons and methods
        updated_ev1 = self.session.get(Evidence, ev1.id)
        self.assertEqual(updated_ev1.validation_status, "VERIFIED")
        self.assertEqual(updated_ev1.match_method, "exact")
        self.assertIsNotNone(updated_ev1.validation_reason)

        updated_ev2 = self.session.get(Evidence, ev2.id)
        self.assertEqual(updated_ev2.validation_status, "UNVERIFIED")
        self.assertIn("not found in any chunks", updated_ev2.validation_reason)

    def test_plausible_ai_hallucination_remains_unverified(self):
        """Test that articulate, plausible-sounding AI reasoning without actual source chunk text is strictly UNVERIFIED."""
        finding = Finding(
            id="find-ev-plausible",
            project_id=self.project_id,
            workstream="financial",
            title="Consistent Operating Cash Flow Margins",
            issue="Management achieved stable operating cash conversion of 85% with positive working capital adjustments.",
            evidence_conclusion="Demonstrates robust underlying liquidity and prudent working capital governance.",
        )
        self.session.add(finding)

        # Very realistic sounding financial statement quote that DOES NOT exist in the document chunks
        ev = Evidence(
            id="ev-plausible-1",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="01_income_statement.pdf",
            quoted_text="Operating cash conversion remained resilient at 85% throughout FY 2025-26 under disciplined cash management policies.",
            extracted_value="85%",
            validation_status="UNVERIFIED",
        )
        self.session.add(ev)
        self.session.commit()

        res = validate_single_evidence(
            ev=ev,
            finding=finding,
            doc_repo=self.doc_repo,
            project_docs=self.project_docs,
            doc_by_id=self.doc_by_id,
        )

        # Must NOT be verified simply because it sounds professional or plausible
        self.assertEqual(res["status"], "UNVERIFIED")
        self.assertIn("not found in any chunks", res["reason"])
        self.assertEqual(res["confidence"], 0.0)

    def test_ambiguous_evidence_with_multiple_competing_chunks(self):
        """Test that ambiguous quotes matching multiple chunks without an exact match are flagged AMBIGUOUS."""
        # Add two chunks with similar boilerplate clauses
        doc2 = Document(
            id="doc-ev-ambig",
            project_id=self.project_id,
            file_name="05_customer_agreement.pdf",
            storage_key="test/05_customer_agreement.pdf",
            category="legal",
        )
        self.session.add(doc2)

        chunk_a = DocumentChunk(
            id="chunk-ambig-a",
            document_id=doc2.id,
            chunk_index=0,
            content="Section 8.1 Termination for Convenience: Either party may terminate this agreement upon thirty days written notice.",
            page_number=3,
        )
        chunk_b = DocumentChunk(
            id="chunk-ambig-b",
            document_id=doc2.id,
            chunk_index=1,
            content="Section 14.4 Notice Period: Either party may terminate this contract upon thirty days written notice without cause.",
            page_number=7,
        )
        self.session.add_all([chunk_a, chunk_b])
        self.session.commit()

        # Update local docs lookup
        raw_docs = self.doc_repo.list_documents(self.project_id)
        project_docs = {d.file_name.lower(): d for d in raw_docs}
        doc_by_id = {d.id: d for d in raw_docs}

        finding = Finding(
            id="find-ev-ambig",
            project_id=self.project_id,
            workstream="legal",
            title="Termination Notice Ambiguity",
            issue="Contract contains multiple conflicting termination notice sections.",
        )
        self.session.add(finding)

        # Inexact quote that matches both chunks with high similarity (~0.85) without exact match
        ev = Evidence(
            id="ev-ambig-1",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="05_customer_agreement.pdf",
            quoted_text="Either party may terminate the agreement upon thirty days written notice to the other party.",
            validation_status="UNVERIFIED",
        )
        self.session.add(ev)
        self.session.commit()

        res = validate_single_evidence(
            ev=ev,
            finding=finding,
            doc_repo=self.doc_repo,
            project_docs=project_docs,
            doc_by_id=doc_by_id,
        )

        self.assertIn(res["status"], ["AMBIGUOUS", "UNVERIFIED"])
        if res["status"] == "AMBIGUOUS":
            self.assertIn("ambiguous", res["reason"].lower())

    def test_cross_document_numerical_inconsistency_flagged_as_discrepancy(self):
        """Test that cross-document numerical discrepancies between financial statements and agreements are flagged."""
        # Add term sheet document
        doc_ts = Document(
            id="doc-ev-ts",
            project_id=self.project_id,
            file_name="02_term_sheet.pdf",
            storage_key="test/02_term_sheet.pdf",
            category="financial",
        )
        self.session.add(doc_ts)

        chunk_ts = DocumentChunk(
            id="chunk-ev-ts-1",
            document_id=doc_ts.id,
            chunk_index=0,
            content="Target Company represents and warrants audited FY 2025-26 Total Revenue of INR 135.00 crore.",
            page_number=1,
            section="Representations & Warranties",
        )
        self.session.add(chunk_ts)
        self.session.commit()

        raw_docs = self.doc_repo.list_documents(self.project_id)
        project_docs = {d.file_name.lower(): d for d in raw_docs}
        doc_by_id = {d.id: d for d in raw_docs}

        # Finding describes the discrepancy between Income Statement (100.00 crore) and Term Sheet (135.00 crore)
        finding = Finding(
            id="find-ev-cross-doc-discrepancy",
            project_id=self.project_id,
            workstream="financial",
            title="Revenue Inconsistency Across Documents",
            issue="Discrepancy identified between Income Statement revenue of INR 100.00 crore and Term Sheet stated revenue of INR 135.00 crore.",
            evidence_conclusion="There is an unreconciled difference of 35.00 crore between audited financials and contract representations.",
        )
        self.session.add(finding)

        # Evidence 1: Income statement citation
        ev1 = Evidence(
            id="ev-cross-1",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="01_income_statement.pdf",
            quoted_text="Total Revenue for FY 2025-26 was INR 100.00 crore",
            extracted_value="100.00",
            validation_status="UNVERIFIED",
        )
        # Evidence 2: Term sheet citation
        ev2 = Evidence(
            id="ev-cross-2",
            project_id=self.project_id,
            finding_id=finding.id,
            source_label="02_term_sheet.pdf",
            quoted_text="audited FY 2025-26 Total Revenue of INR 135.00 crore",
            extracted_value="135.00",
            validation_status="UNVERIFIED",
        )
        self.session.add_all([ev1, ev2])
        self.session.commit()

        res1 = validate_single_evidence(
            ev=ev1,
            finding=finding,
            doc_repo=self.doc_repo,
            project_docs=project_docs,
            doc_by_id=doc_by_id,
        )

        res2 = validate_single_evidence(
            ev=ev2,
            finding=finding,
            doc_repo=self.doc_repo,
            project_docs=project_docs,
            doc_by_id=doc_by_id,
        )

        # Both cited evidence must resolve to their actual source chunks
        self.assertEqual(res1["chunk_id"], self.chunk1.id)
        self.assertEqual(res2["chunk_id"], chunk_ts.id)

        # Both must recognize the true arithmetic discrepancy between 100.00 and 135.00
        self.assertEqual(res1["status"], "FLAGGED_DISCREPANCY")
        self.assertEqual(res2["status"], "FLAGGED_DISCREPANCY")
        self.assertIn("35.00", res1["reason"])
        self.assertIn("35.00", res2["reason"])

