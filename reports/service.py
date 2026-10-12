from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from database.session import SessionLocal
from dd_requests.models import DDRequest
from evidence.models import Evidence
from findings.models import Finding, FindingReview
from reports.schemas import (
    DueDiligenceReport,
    ReportEvidenceCitation,
    ReportExecutiveSummary,
    ReportFindingItem,
    ReportMetadata,
    ReportOutstandingItem,
    ReportReviewHistory,
    ReportScopeSummary,
    ScopeWorkstreamDetail,
)
from retrieval.models.documents import Document
from retrieval.models.projects import DDProject
from retrieval.models.scopes import DDScope
from retrieval.models.workstreams import DDWorkstream
from tasks.models import DDTask

logger = logging.getLogger(__name__)


# ====================================================================
# TWO-PASS NUMBERED CANVAS (Page X of Y & Running Header/Footer)
# ====================================================================

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass ReportLab canvas to compute total page count and render
    professional headers and footers on every page.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "CONFIDENTIAL & PRIVILEGED — DUE DILIGENCE REPORT")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)

        self.drawString(54, 32, "Strictly for internal transaction advisory and diligence review only.")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)

        self.restoreState()


# ====================================================================
# REPORT SERVICE
# ====================================================================

class ReportService:
    """
    Core Due Diligence Report Compilation and Export Service.
    Compiles database findings, scope, validation records, and tasks into
    cohesive structured JSON and executive-ready PDF documents.
    """

    def compile_report(self, project_id: str, session: Optional[Session] = None) -> DueDiligenceReport:
        """
        Compiles the complete, project-isolated Due Diligence report from PostgreSQL records.
        """
        local_session = session or SessionLocal()
        try:
            # 1. Project details
            project = local_session.get(DDProject, project_id)
            if not project:
                raise ValueError(f"Project '{project_id}' not found.")

            metadata = ReportMetadata(
                project_id=project.id,
                project_name=project.name,
                target_company=project.target_company,
                deal_type=project.deal_type or "N/A",
                industry=project.industry or "N/A",
                diligence_period=project.diligence_period or "N/A",
                description=project.description,
                status=project.status,
                generated_at=datetime.utcnow(),
            )

            # 2. Scope & Workstreams
            workstreams = (
                local_session.query(DDWorkstream)
                .filter(DDWorkstream.project_id == project_id)
                .all()
            )
            scopes = (
                local_session.query(DDScope)
                .filter(DDScope.project_id == project_id)
                .all()
            )
            scope_map = {s.workstream.lower(): s for s in scopes}

            enabled_workstreams: List[str] = []
            workstream_details: List[ScopeWorkstreamDetail] = []
            for ws in workstreams:
                is_on = getattr(ws, "enabled", True)
                ws_name = getattr(ws, "name", "financial")
                if is_on:
                    enabled_workstreams.append(ws_name.upper())
                s_obj = scope_map.get(ws_name.lower())
                s_dict = s_obj.scope if (s_obj and hasattr(s_obj, "scope") and isinstance(s_obj.scope, dict)) else {}
                custom_q = s_dict.get("key_questions", []) if s_dict else (getattr(s_obj, "key_questions", []) or [])
                review_a = s_dict.get("review_areas", []) if s_dict else (getattr(s_obj, "review_areas", []) or [])
                workstream_details.append(
                    ScopeWorkstreamDetail(
                        workstream=ws_name,
                        is_enabled=is_on,
                        status=ws.status,
                        custom_questions=custom_q,
                        review_areas=review_a,
                    )
                )

            scope_summary = ReportScopeSummary(
                enabled_workstreams=enabled_workstreams,
                workstream_details=workstream_details,
            )

            # 3. Documents Map (for filename lookup)
            docs = (
                local_session.query(Document)
                .filter(Document.project_id == project_id)
                .all()
            )
            doc_map = {d.id: d.file_name for d in docs}

            # 4. Findings with attached Evidence and Reviews
            findings = (
                local_session.query(Finding)
                .options(
                    joinedload(Finding.evidence),
                    joinedload(Finding.reviews),
                )
                .filter(Finding.project_id == project_id)
                .order_by(Finding.created_at.asc())
                .all()
            )

            financial_items: List[ReportFindingItem] = []
            legal_items: List[ReportFindingItem] = []
            cross_domain_items: List[ReportFindingItem] = []
            all_items: List[ReportFindingItem] = []

            high_count = 0
            med_count = 0
            low_count = 0
            approved_count = 0
            pending_count = 0
            rejected_count = 0
            more_ev_count = 0
            unverified_ev_count = 0

            for f in findings:
                # Evidence citations
                citations: List[ReportEvidenceCitation] = []
                for ev in (f.evidence or []):
                    doc_name = doc_map.get(ev.document_id, ev.source_label or "Unknown Document")
                    status_val = (ev.validation_status or "UNVERIFIED").upper()
                    if status_val != "VERIFIED":
                        unverified_ev_count += 1

                    citations.append(
                        ReportEvidenceCitation(
                            id=ev.id,
                            document_id=ev.document_id,
                            document_name=doc_name,
                            page_number=ev.page_number,
                            chunk_id=ev.chunk_id,
                            evidence_type=ev.evidence_type or "document",
                            quoted_text=ev.quoted_text,
                            extracted_value=ev.extracted_value,
                            validation_status=status_val,
                            validation_reason=ev.validation_reason,
                            match_method=ev.match_method,
                            confidence=ev.confidence,
                        )
                    )

                # Review history
                reviews_list: List[ReportReviewHistory] = []
                for rv in (f.reviews or []):
                    reviews_list.append(
                        ReportReviewHistory(
                            id=rv.id,
                            action=rv.action,
                            reviewer_name=getattr(rv, "reviewer", getattr(rv, "reviewer_name", "Human Reviewer")),
                            comments=getattr(rv, "comment", getattr(rv, "comments", None)),
                            requested_clarification=getattr(rv, "requested_clarification", None),
                            reviewed_at=rv.reviewed_at,
                        )
                    )

                # Finding item
                sev = (f.risk_severity or "medium").lower()
                if sev == "high":
                    high_count += 1
                elif sev == "low":
                    low_count += 1
                else:
                    med_count += 1

                st = (f.status or "REVIEW_REQUIRED").upper()
                if st in ["APPROVED", "ACCEPTED"]:
                    approved_count += 1
                elif st == "REJECTED":
                    rejected_count += 1
                elif st in ["MORE_EVIDENCE_REQUIRED", "REQUEST_MORE_EVIDENCE"]:
                    more_ev_count += 1
                else:
                    pending_count += 1

                item = ReportFindingItem(
                    id=f.id,
                    workstream=f.workstream,
                    agent_name=f.agent_name,
                    title=f.title,
                    issue=f.issue,
                    why_it_matters=f.why_it_matters,
                    evidence_conclusion=f.evidence_conclusion,
                    recommended_action=f.recommended_action,
                    risk_severity=f.risk_severity or "medium",
                    status=f.status or "REVIEW_REQUIRED",
                    confidence=f.confidence or "medium",
                    created_at=f.created_at,
                    evidence=citations,
                    reviews=reviews_list,
                )

                all_items.append(item)
                ws_lower = (f.workstream or "").lower()
                if "financial" in ws_lower:
                    financial_items.append(item)
                elif "legal" in ws_lower:
                    legal_items.append(item)
                elif "cross" in ws_lower:
                    cross_domain_items.append(item)
                else:
                    financial_items.append(item)

            # 5. Outstanding items (DDRequests + DDTasks)
            outstanding_items: List[ReportOutstandingItem] = []
            requests = (
                local_session.query(DDRequest)
                .filter(DDRequest.project_id == project_id)
                .all()
            )
            for req in requests:
                outstanding_items.append(
                    ReportOutstandingItem(
                        item_type="request",
                        id=req.id,
                        title=req.title,
                        description=req.description,
                        status=req.status,
                        priority=req.priority,
                        requested_from_or_assigned_to=req.requested_from,
                        due_at=req.due_at,
                        created_at=req.created_at,
                    )
                )

            tasks = (
                local_session.query(DDTask)
                .filter(DDTask.project_id == project_id)
                .all()
            )
            for t in tasks:
                if t.status != "COMPLETED":
                    outstanding_items.append(
                        ReportOutstandingItem(
                            item_type="task",
                            id=t.id,
                            title=t.title,
                            description=t.description,
                            status=t.status,
                            priority=t.priority,
                            requested_from_or_assigned_to=t.assigned_to,
                            due_at=t.due_at,
                            created_at=t.created_at,
                        )
                    )

            # 6. Executive Overview narrative synthesis (strictly grounded)
            total_findings = len(all_items)
            if total_findings == 0:
                overview_text = (
                    f"Due diligence investigation for {project.target_company} has completed initial scope setup. "
                    "No findings have been recorded yet in the project repository."
                )
            else:
                top_high_titles = [item.title for item in all_items if item.risk_severity.lower() == "high"][:3]
                high_summary = ""
                if top_high_titles:
                    high_summary = f" Critical risk areas identified include: {'; '.join(top_high_titles)}."

                overview_text = (
                    f"Due diligence analysis for {project.target_company} identified a total of {total_findings} finding(s) "
                    f"across {len(enabled_workstreams) or 1} active workstream(s), comprising {high_count} high-risk, "
                    f"{med_count} medium-risk, and {low_count} low-risk issue(s). "
                    f"Human review status shows {approved_count} approved, {pending_count} pending review, "
                    f"{more_ev_count} requiring additional evidence, and {rejected_count} rejected.{high_summary}"
                )

            exec_summary = ReportExecutiveSummary(
                total_findings=total_findings,
                high_risk_count=high_count,
                medium_risk_count=med_count,
                low_risk_count=low_count,
                financial_count=len(financial_items),
                legal_count=len(legal_items),
                cross_domain_count=len(cross_domain_items),
                approved_count=approved_count,
                pending_review_count=pending_count,
                rejected_count=rejected_count,
                more_evidence_required_count=more_ev_count,
                unverified_evidence_count=unverified_ev_count,
                executive_overview=overview_text,
            )

            # 7. Limitations & Disclaimers
            limitations = [
                "AI-assisted analysis: All findings and extractions are generated by specialized agentic intelligence and require human review and corroboration prior to transaction execution.",
            ]
            if unverified_ev_count > 0:
                limitations.append(
                    f"Evidence Verification Alert: {unverified_ev_count} cited evidence item(s) could not be strictly verified against underlying document text or contain fuzzy matches. These items are flagged with 'UNVERIFIED' in the report."
                )
            if pending_count > 0:
                limitations.append(
                    f"Pending Human Review: {pending_count} finding(s) are currently awaiting review and have not been confirmed by a domain lead."
                )
            if more_ev_count > 0 or len([oi for oi in outstanding_items if oi.status == "OPEN"]) > 0:
                limitations.append(
                    "Information Gap: Outstanding evidence requests remain active. Final risk conclusions are subject to receipt of requested supporting documentation."
                )

            return DueDiligenceReport(
                metadata=metadata,
                scope=scope_summary,
                executive_summary=exec_summary,
                financial_findings=financial_items,
                legal_findings=legal_items,
                cross_domain_findings=cross_domain_items,
                all_findings=all_items,
                outstanding_items=outstanding_items,
                limitations=limitations,
            )
        finally:
            if session is None:
                local_session.close()

    def generate_json(self, report: DueDiligenceReport) -> Dict[str, Any]:
        """Serializes report data to structured JSON dictionary."""
        return report.model_dump(mode="json")

    def generate_pdf(self, report: DueDiligenceReport) -> bytes:
        """
        Compiles the report into an executive-grade, beautifully formatted PDF document.
        """
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
        )

        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#475569"),
            spaceAfter=14,
        )

        h1_style = ParagraphStyle(
            "SectionHeading1",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        )

        h2_style = ParagraphStyle(
            "SectionHeading2",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#334155"),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            "BodyDark",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=6,
        )

        meta_label_style = ParagraphStyle(
            "MetaLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#475569"),
        )

        meta_val_style = ParagraphStyle(
            "MetaVal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#0f172a"),
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
        )

        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b"),
        )

        table_cell_bold = ParagraphStyle(
            "TableCellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0f172a"),
        )

        story = []

        # -------------------------------------------------------------
        # 1. TITLE & TRANSACTION PROFILE
        # -------------------------------------------------------------
        story.append(Paragraph("DUE DILIGENCE INVESTIGATION REPORT", title_style))
        story.append(
            Paragraph(
                f"Target Entity: <b>{report.metadata.target_company}</b> &nbsp;|&nbsp; "
                f"Project: <b>{report.metadata.project_name}</b> &nbsp;|&nbsp; "
                f"Generated: {report.metadata.generated_at.strftime('%B %d, %Y %H:%M UTC')}",
                subtitle_style,
            )
        )
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4338ca"), spaceAfter=12))

        # Project Metadata Table
        meta_data = [
            [
                Paragraph("Target Company", meta_label_style),
                Paragraph(report.metadata.target_company, meta_val_style),
                Paragraph("Deal Type", meta_label_style),
                Paragraph(report.metadata.deal_type or "N/A", meta_val_style),
            ],
            [
                Paragraph("Industry Sector", meta_label_style),
                Paragraph(report.metadata.industry or "N/A", meta_val_style),
                Paragraph("Diligence Period", meta_label_style),
                Paragraph(report.metadata.diligence_period or "N/A", meta_val_style),
            ],
            [
                Paragraph("Investigation Status", meta_label_style),
                Paragraph(report.metadata.status.upper(), meta_val_style),
                Paragraph("Active Workstreams", meta_label_style),
                Paragraph(", ".join(report.scope.enabled_workstreams) or "Financial, Legal", meta_val_style),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[110, 142, 110, 142])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # -------------------------------------------------------------
        # 2. EXECUTIVE SUMMARY & RISK MATRIX
        # -------------------------------------------------------------
        story.append(Paragraph("1. Executive Summary & Risk Matrix", h1_style))
        story.append(Paragraph(report.executive_summary.executive_overview, body_style))

        # Metrics KPI Summary Table
        kpi_data = [
            [
                Paragraph("Total Findings", table_header_style),
                Paragraph("High Risk", table_header_style),
                Paragraph("Medium Risk", table_header_style),
                Paragraph("Low Risk", table_header_style),
                Paragraph("Approved", table_header_style),
                Paragraph("Pending Review", table_header_style),
                Paragraph("Unverified Citations", table_header_style),
            ],
            [
                Paragraph(str(report.executive_summary.total_findings), table_cell_bold),
                Paragraph(str(report.executive_summary.high_risk_count), table_cell_bold),
                Paragraph(str(report.executive_summary.medium_risk_count), table_cell_bold),
                Paragraph(str(report.executive_summary.low_risk_count), table_cell_bold),
                Paragraph(str(report.executive_summary.approved_count), table_cell_bold),
                Paragraph(str(report.executive_summary.pending_review_count), table_cell_bold),
                Paragraph(str(report.executive_summary.unverified_evidence_count), table_cell_bold),
            ],
        ]
        kpi_table = Table(kpi_data, colWidths=[72, 72, 72, 72, 72, 72, 72])
        kpi_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e1b4b")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f1f5f9")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(kpi_table)
        story.append(Spacer(1, 14))

        # -------------------------------------------------------------
        # 3. WORKSTREAM FINDINGS
        # -------------------------------------------------------------
        sections = [
            ("2. Financial Due Diligence Findings", report.financial_findings),
            ("3. Legal Due Diligence Findings", report.legal_findings),
            ("4. Cross-Domain Due Diligence Findings", report.cross_domain_findings),
        ]

        for sec_title, findings_group in sections:
            story.append(Paragraph(sec_title, h1_style))
            if not findings_group:
                story.append(Paragraph("<i>No findings recorded for this workstream.</i>", body_style))
                story.append(Spacer(1, 10))
                continue

            for f in findings_group:
                # Severity and Review Badges
                sev_color = "#b91c1c" if f.risk_severity.lower() == "high" else "#d97706" if f.risk_severity.lower() == "medium" else "#059669"
                rv_color = "#047857" if f.status.upper() in ["APPROVED", "ACCEPTED"] else "#b91c1c" if f.status.upper() == "REJECTED" else "#b45309"

                header_html = (
                    f"<b>{f.title}</b> &nbsp;&nbsp;"
                    f"<font color='{sev_color}'>[SEVERITY: {f.risk_severity.upper()}]</font> &nbsp;&nbsp;"
                    f"<font color='{rv_color}'>[STATUS: {f.status.upper()}]</font>"
                )

                card_flowables = [
                    Paragraph(header_html, h2_style),
                    Paragraph(f"<b>Issue:</b> {f.issue}", body_style),
                ]

                if f.why_it_matters:
                    card_flowables.append(Paragraph(f"<b>Commercial Impact / Why It Matters:</b> {f.why_it_matters}", body_style))
                if f.recommended_action:
                    card_flowables.append(Paragraph(f"<b>Recommended Mitigant / Action:</b> {f.recommended_action}", body_style))

                # Attached Evidence Table
                if f.evidence:
                    ev_rows = [
                        [
                            Paragraph("Source Document", table_header_style),
                            Paragraph("Page", table_header_style),
                            Paragraph("Quoted Text / Extracted Claim", table_header_style),
                            Paragraph("Validation Status", table_header_style),
                        ]
                    ]
                    for ev in f.evidence:
                        v_color = "#0284c7" if ev.validation_status == "VERIFIED" else "#dc2626"
                        snippet = ev.quoted_text or ev.extracted_value or "No direct quote recorded"
                        if len(snippet) > 160:
                            snippet = snippet[:157] + "..."

                        ev_rows.append([
                            Paragraph(ev.document_name, table_cell_bold),
                            Paragraph(str(ev.page_number or "-"), table_cell_style),
                            Paragraph(f"&ldquo;{snippet}&rdquo;", table_cell_style),
                            Paragraph(f"<font color='{v_color}'><b>{ev.validation_status}</b></font>", table_cell_style),
                        ])

                    ev_table = Table(ev_rows, colWidths=[120, 36, 260, 88])
                    ev_table.setStyle(
                        TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ])
                    )
                    card_flowables.append(Spacer(1, 4))
                    card_flowables.append(ev_table)

                card_flowables.append(Spacer(1, 8))
                story.append(KeepTogether(card_flowables))

            story.append(Spacer(1, 8))

        # -------------------------------------------------------------
        # 4. OUTSTANDING REQUESTS & ACTION ITEMS
        # -------------------------------------------------------------
        story.append(Paragraph("5. Outstanding Requests & Open Tasks", h1_style))
        if not report.outstanding_items:
            story.append(Paragraph("<i>No outstanding document requests or unresolved investigation tasks.</i>", body_style))
        else:
            req_rows = [
                [
                    Paragraph("Type", table_header_style),
                    Paragraph("Title / Description", table_header_style),
                    Paragraph("Status", table_header_style),
                    Paragraph("Priority", table_header_style),
                ]
            ]
            for item in report.outstanding_items:
                req_rows.append([
                    Paragraph(item.item_type.upper(), table_cell_bold),
                    Paragraph(f"<b>{item.title}</b><br/>{item.description[:120]}...", table_cell_style),
                    Paragraph(item.status, table_cell_style),
                    Paragraph(item.priority.upper(), table_cell_style),
                ])
            req_table = Table(req_rows, colWidths=[60, 314, 65, 65])
            req_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e1b4b")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ])
            )
            story.append(req_table)

        story.append(Spacer(1, 14))

        # -------------------------------------------------------------
        # 5. DILIGENCE LIMITATIONS & AUDIT TRAIL
        # -------------------------------------------------------------
        story.append(Paragraph("6. Diligence Limitations & Disclaimers", h1_style))
        for lim in report.limitations:
            story.append(Paragraph(f"&bull; {lim}", body_style))

        # Build PDF with two-pass canvas
        doc.build(story, canvasmaker=NumberedCanvas)
        return buf.getvalue()
