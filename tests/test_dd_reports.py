import io
import uuid
import pytest
from fastapi.testclient import TestClient

from app.new_main import app
from database.session import SessionLocal
from evidence.models import Evidence
from findings.models import Finding, FindingReview
from reports.service import ReportService
from retrieval.models.documents import Document
from retrieval.models.projects import DDProject
from retrieval.models.scopes import DDScope
from retrieval.models.workstreams import DDWorkstream


@pytest.fixture
def populated_report_project():
    """Sets up an isolated test project with multi-domain findings and evidence."""
    session = SessionLocal()
    proj_id = f"TEST-REPORT-PROJ-{uuid.uuid4().hex[:6]}"
    other_proj_id = f"OTHER-REPORT-PROJ-{uuid.uuid4().hex[:6]}"

    # Project under test
    proj = DDProject(
        id=proj_id,
        name="Project Apex Diligence",
        target_company="Apex Global Software Inc.",
        deal_type="Acquisition",
        industry="Enterprise B2B SaaS",
        diligence_period="FY 2025-26",
        description="Comprehensive buy-side due diligence investigation.",
        status="investigating",
    )
    # Isolated Other Project
    other_proj = DDProject(
        id=other_proj_id,
        name="Other Project Isolated",
        target_company="Other Entity Corp",
        deal_type="Merger",
    )
    session.add(proj)
    session.add(other_proj)

    # Workstreams & Scope
    ws_fin = DDWorkstream(id=f"ws-{uuid.uuid4().hex[:6]}", project_id=proj_id, name="financial", enabled=True, status="in_progress")
    ws_leg = DDWorkstream(id=f"ws-{uuid.uuid4().hex[:6]}", project_id=proj_id, name="legal", enabled=True, status="in_progress")
    session.add(ws_fin)
    session.add(ws_leg)

    scope_fin = DDScope(
        id=f"sc-{uuid.uuid4().hex[:6]}",
        project_id=proj_id,
        workstream="financial",
        scope={
            "key_questions": ["Validate FY25 EBITDA margins", "Verify credit agreement covenants"],
            "review_areas": ["Revenue Recognition", "Indebtedness"],
        },
    )
    session.add(scope_fin)

    # Document
    doc = Document(
        id=f"doc-{uuid.uuid4().hex[:6]}",
        project_id=proj_id,
        file_name="apex_audited_financials_2025.pdf",
        storage_key="docs/apex_audit.pdf",
        category="financial",
    )
    session.add(doc)
    session.flush()

    # Finding 1: Financial Finding (High Risk, Approved)
    f1 = Finding(
        id=f"find-1-{uuid.uuid4().hex[:6]}",
        project_id=proj_id,
        workstream="financial",
        title="Debt Covenant Pressure on Revolving Facility",
        issue="Apex is at 3.4x leverage against a 3.5x maximum debt-to-EBITDA covenant.",
        why_it_matters="A 5% EBITDA decline will trigger covenant default.",
        recommended_action="Negotiate lender waiver prior to transaction closing.",
        risk_severity="high",
        status="APPROVED",
    )
    session.add(f1)
    session.flush()

    # Evidence 1 (Verified)
    ev1 = Evidence(
        id=f"ev-1-{uuid.uuid4().hex[:6]}",
        project_id=proj_id,
        finding_id=f1.id,
        document_id=doc.id,
        page_number=42,
        quoted_text="The company's consolidated leverage ratio was 3.4x at year-end.",
        extracted_value="3.4x",
        validation_status="VERIFIED",
    )
    session.add(ev1)

    # Review 1
    rv1 = FindingReview(
        id=f"rv-1-{uuid.uuid4().hex[:6]}",
        finding_id=f1.id,
        action="APPROVE",
        reviewer="Sarah Jenkins (Financial Lead)",
        comment="Covenant risk confirmed against credit agreement schedule.",
    )
    session.add(rv1)

    # Finding 2: Legal Finding (Medium Risk, Review Required)
    f2 = Finding(
        id=f"find-2-{uuid.uuid4().hex[:6]}",
        project_id=proj_id,
        workstream="legal",
        title="Onerous Customer Change-of-Control Termination Clause",
        issue="Master Services Agreement with Tier-1 customer allows termination upon 50%+ equity sale.",
        why_it_matters="Account represents 18% of annualized recurring revenue.",
        recommended_action="Obtain written consent prior to signing definitive agreement.",
        risk_severity="medium",
        status="REVIEW_REQUIRED",
    )
    session.add(f2)
    session.flush()

    # Evidence 2 (Unverified Source Mismatch)
    ev2 = Evidence(
        id=f"ev-2-{uuid.uuid4().hex[:6]}",
        project_id=proj_id,
        finding_id=f2.id,
        document_id=doc.id,
        page_number=12,
        quoted_text="Termination for convenience upon any direct or indirect ownership change.",
        validation_status="UNVERIFIED",
        validation_reason="Clause wording found in draft exhibit, not executed agreement.",
    )
    session.add(ev2)

    # Finding 3: Cross-Domain Finding (High Risk)
    f3 = Finding(
        id=f"find-3-{uuid.uuid4().hex[:6]}",
        project_id=proj_id,
        workstream="cross_domain",
        title="Revenue Concentration Compounds Change-of-Control Default Risk",
        issue="Customer contract termination clause directly imperils the EBITDA stream required to service debt covenants.",
        why_it_matters="Loss of customer triggers immediate lender acceleration.",
        recommended_action="Make customer consent a closing condition.",
        risk_severity="high",
        status="REVIEW_REQUIRED",
    )
    session.add(f3)

    # Finding in OTHER project (should NEVER appear in proj_id report)
    f_other = Finding(
        id=f"find-other-{uuid.uuid4().hex[:6]}",
        project_id=other_proj_id,
        workstream="financial",
        title="Unrelated Project Tax Leakage",
        issue="Severe tax liability in foreign subsidiary.",
        risk_severity="high",
        status="REVIEW_REQUIRED",
    )
    session.add(f_other)

    doc_id_val = doc.id
    session.commit()
    session.close()

    yield {
        "proj_id": proj_id,
        "other_proj_id": other_proj_id,
        "doc_id": doc_id_val,
    }

    # Cleanup
    clean = SessionLocal()
    for pid in [proj_id, other_proj_id]:
        p = clean.get(DDProject, pid)
        if p:
            clean.delete(p)
    clean.commit()
    clean.close()


class TestDueDiligenceReport:

    def test_compile_report_structure_and_metrics(self, populated_report_project):
        """Verifies report compilation groups findings by workstream and calculates exact KPIs."""
        proj_id = populated_report_project["proj_id"]
        service = ReportService()
        report = service.compile_report(project_id=proj_id)

        # Metadata
        assert report.metadata.project_id == proj_id
        assert report.metadata.target_company == "Apex Global Software Inc."
        assert report.metadata.deal_type == "Acquisition"

        # Executive Summary KPIs
        assert report.executive_summary.total_findings == 3
        assert report.executive_summary.high_risk_count == 2
        assert report.executive_summary.medium_risk_count == 1
        assert report.executive_summary.low_risk_count == 0
        assert report.executive_summary.financial_count == 1
        assert report.executive_summary.legal_count == 1
        assert report.executive_summary.cross_domain_count == 1
        assert report.executive_summary.approved_count == 1
        assert report.executive_summary.pending_review_count == 2
        assert report.executive_summary.unverified_evidence_count == 1

        # Workstream separation
        assert len(report.financial_findings) == 1
        assert report.financial_findings[0].title == "Debt Covenant Pressure on Revolving Facility"
        assert len(report.legal_findings) == 1
        assert report.legal_findings[0].title == "Onerous Customer Change-of-Control Termination Clause"
        assert len(report.cross_domain_findings) == 1
        assert report.cross_domain_findings[0].title == "Revenue Concentration Compounds Change-of-Control Default Risk"

        # Evidence & Review Attached
        f1 = report.financial_findings[0]
        assert len(f1.evidence) == 1
        assert f1.evidence[0].validation_status == "VERIFIED"
        assert f1.evidence[0].document_name == "apex_audited_financials_2025.pdf"
        assert len(f1.reviews) == 1
        assert f1.reviews[0].action == "APPROVE"

        # Unverified Evidence Alert in Limitations
        assert any("UNVERIFIED" in lim for lim in report.limitations)
        assert any("Pending Human Review" in lim for lim in report.limitations)

    def test_project_isolation(self, populated_report_project):
        """Report for Project A must strictly contain zero findings or items from Project B."""
        proj_id = populated_report_project["proj_id"]
        service = ReportService()
        report = service.compile_report(project_id=proj_id)

        titles = [f.title for f in report.all_findings]
        assert "Unrelated Project Tax Leakage" not in titles
        for f in report.all_findings:
            assert "Unrelated" not in f.title

    def test_empty_project_generates_clean_report(self):
        """A project with zero findings compiles cleanly without crashing."""
        session = SessionLocal()
        empty_id = f"EMPTY-{uuid.uuid4().hex[:6]}"
        proj = DDProject(
            id=empty_id,
            name="Empty Diligence",
            target_company="Zero Data LLC",
        )
        session.add(proj)
        session.commit()
        session.close()

        try:
            service = ReportService()
            report = service.compile_report(project_id=empty_id)
            assert report.executive_summary.total_findings == 0
            assert report.executive_summary.high_risk_count == 0
            assert len(report.all_findings) == 0
            assert "No findings have been recorded" in report.executive_summary.executive_overview
        finally:
            clean = SessionLocal()
            p = clean.get(DDProject, empty_id)
            if p:
                clean.delete(p)
            clean.commit()
            clean.close()

    def test_missing_project_raises_value_error(self):
        service = ReportService()
        with pytest.raises(ValueError) as exc:
            service.compile_report(project_id="NON-EXISTENT-PROJECT-UUID")
        assert "not found" in str(exc.value)

    def test_json_export_and_consistency(self, populated_report_project):
        """Verifies JSON generation contains identical structure and counts as preview."""
        proj_id = populated_report_project["proj_id"]
        service = ReportService()
        report = service.compile_report(project_id=proj_id)
        data = service.generate_json(report)

        assert isinstance(data, dict)
        assert data["metadata"]["target_company"] == "Apex Global Software Inc."
        assert data["executive_summary"]["total_findings"] == 3
        assert len(data["financial_findings"]) == 1
        assert len(data["legal_findings"]) == 1
        assert len(data["cross_domain_findings"]) == 1
        assert len(data["all_findings"]) == 3

    def test_pdf_export_validity(self, populated_report_project):
        """Verifies PDF generation returns a valid, non-empty binary beginning with %PDF-."""
        proj_id = populated_report_project["proj_id"]
        service = ReportService()
        report = service.compile_report(project_id=proj_id)
        pdf_bytes = service.generate_pdf(report)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 2000
        assert pdf_bytes.startswith(b"%PDF-")

    def test_api_endpoints_via_testclient(self, populated_report_project):
        """Test FastAPI endpoints for preview, JSON export, and PDF export."""
        client = TestClient(app)
        proj_id = populated_report_project["proj_id"]

        # 1. Preview endpoint
        preview_res = client.get(f"/api/v1/projects/{proj_id}/reports/preview")
        assert preview_res.status_code == 200
        preview_json = preview_res.json()
        assert preview_json["metadata"]["target_company"] == "Apex Global Software Inc."
        assert preview_json["executive_summary"]["total_findings"] == 3

        # 2. JSON export endpoint
        json_res = client.get(f"/api/v1/projects/{proj_id}/reports/export/json")
        assert json_res.status_code == 200
        assert json_res.headers["content-type"] == "application/json"
        assert "attachment" in json_res.headers["content-disposition"]
        exported_data = json_res.json()
        assert exported_data["metadata"]["project_id"] == proj_id

        # 3. PDF export endpoint
        pdf_res = client.get(f"/api/v1/projects/{proj_id}/reports/export/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert "attachment" in pdf_res.headers["content-disposition"]
        assert pdf_res.content.startswith(b"%PDF-")
        assert len(pdf_res.content) > 2000

        # 4. 404 for missing project
        bad_res = client.get("/api/v1/projects/DOES-NOT-EXIST-PROJ/reports/preview")
        assert bad_res.status_code == 404
