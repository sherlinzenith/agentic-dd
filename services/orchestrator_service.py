from __future__ import annotations

import logging
import re
from typing import Any

from database.session import SessionLocal
from evidence.models import Evidence
from findings.models import Finding
from findings.repository import FindingRepository
from retrieval.models.documents import Document, DocumentChunk
from retrieval.models.investigations import DDInvestigation
from retrieval.repositories.document_repository import DocumentRepository
from retrieval.repositories.investigation_repository import InvestigationRepository
from retrieval.repositories.project_repository import ProjectRepository
from services.evidence_validation_service import (
    normalize_quotation,
    validate_project_evidence_service,
)
from services.planner_service import PlannerService
from services.scope_service import ScopeService

logger = logging.getLogger(__name__)


def validate_project_evidence(project_id: str, session) -> dict[str, Any]:
    """
    Validate all evidence records for a project against actual documents and chunks in PostgreSQL.
    Delegates to the enhanced Evidence Validation Service for deterministic normalization,
    conservative n-gram fuzzy matching, source resolution, and numeric/discrepancy verification.
    """
    return validate_project_evidence_service(project_id, session)


def deduplicate_project_findings(project_id: str, session) -> int:
    """
    Remove or merge redundant duplicate findings with identical workstream and title.
    Preserves all reviewer audit history, reviewed status, and attached evidence.
    Returns count of duplicate findings cleaned up.
    """
    finding_repo = FindingRepository(session)
    findings = finding_repo.list_for_project(project_id)

    seen = {}
    duplicates_removed = 0

    for finding in findings:
        key = (finding.workstream.lower(), normalize_quotation(finding.title))
        if key in seen:
            primary = seen[key]
            # If the duplicate has human reviews and primary doesn't, promote duplicate to primary
            if (finding.reviews and not primary.reviews) or (len(finding.reviews) > len(primary.reviews)):
                primary, finding = finding, primary
                seen[key] = primary

            # Transfer any reviews from duplicate finding to primary
            for rev in list(finding.reviews or []):
                rev.finding_id = primary.id

            # Preserve human review status if already set on either
            if primary.status not in ("APPROVED", "REJECTED", "MORE_EVIDENCE_REQUIRED"):
                if finding.status in ("APPROVED", "REJECTED", "MORE_EVIDENCE_REQUIRED"):
                    primary.status = finding.status

            # Transfer any evidence from duplicate to primary finding avoiding exact duplicates
            existing_ev_keys = {
                (e.source_label, normalize_quotation(e.quoted_text or ""))
                for e in (primary.evidence or [])
            }
            for ev in list(finding.evidence or []):
                ev_key = (ev.source_label, normalize_quotation(ev.quoted_text or ""))
                if ev_key not in existing_ev_keys:
                    ev.finding_id = primary.id
                    existing_ev_keys.add(ev_key)
                else:
                    session.delete(ev)

            session.delete(finding)
            duplicates_removed += 1
        else:
            seen[key] = finding

    if duplicates_removed > 0:
        session.commit()

    return duplicates_removed


class DDOrchestratorService:
    """
    Central Due Diligence Orchestration Service.

    Coordinates the complete Due Diligence workflow:
    1. Context & Scope Loading
    2. Lead Planner Agent (creates investigation plan)
    3. Financial DD Agent (runs financial checks and records findings)
    4. Legal DD Agent (runs contract checks and records findings)
    5. Cross-Domain Agent (receives financial and legal findings, identifies connected risks)
    6. Evidence Validation (verifies citations against actual document chunks)
    7. Deduplication & Final Status Persistence
    """

    def __init__(self):
        self.planner_service = PlannerService()
        self.scope_service = ScopeService()

    def run_full_dd(
        self,
        *,
        project_id: str,
        objective: str | None = None,
        max_agent_iterations: int = 5,
    ) -> dict[str, Any]:
        session = SessionLocal()

        try:
            # Step 1: Verify Project Existence
            proj_repo = ProjectRepository(session)
            project = proj_repo.get_project(project_id)
            if not project:
                raise ValueError(f"Project not found: {project_id}")

            target_company = project.target_company or project.name

            # Step 2: Load Documents and Workstreams
            doc_repo = DocumentRepository(session)
            documents = doc_repo.list_documents(project_id)

            financial_docs = [d for d in documents if d.category == "financial"]
            legal_docs = [d for d in documents if d.category == "legal"]

            workstreams = proj_repo.get_workstreams(project_id)
            enabled_ws = {w.name for w in workstreams if w.enabled} if workstreams else {"financial", "legal"}

            # Step 3: Load Scopes
            scope_fin = self.scope_service.get_scope(project_id=project_id, workstream="financial")
            scope_leg = self.scope_service.get_scope(project_id=project_id, workstream="legal")

            # Step 4: Create Investigation Record
            inv_repo = InvestigationRepository(session)
            full_objective = (
                objective
                or f"Conduct full Due Diligence on {target_company} covering Financial, Legal, and Cross-Domain risks."
            )

            investigation = inv_repo.create(
                project_id=project_id,
                objective=full_objective,
            )
            investigation_id = investigation.id
            inv_repo.save()

            # Step 5: Persist real DDTasks for the investigation plan
            from services.task_service import TaskService
            from tasks.models import DDTask
            task_service = TaskService()
            task_service.generate_plan_tasks(
                session,
                project_id=project_id,
                investigation_id=investigation_id,
                enabled_workstreams=list(enabled_ws),
            )

        finally:
            session.close()

        def _set_agent_tasks_status(agent_name: str, new_status: str):
            task_session = SessionLocal()
            try:
                tasks_to_update = task_session.query(DDTask).filter(
                    DDTask.project_id == project_id,
                    DDTask.assigned_agent == agent_name,
                ).all()
                for t in tasks_to_update:
                    t.status = new_status
                task_session.commit()
            except Exception:
                task_session.rollback()
            finally:
                task_session.close()

        stages: dict[str, Any] = {}
        stage_errors: list[str] = []

        # =====================================================================
        # STAGE 1: PLANNER AGENT
        # =====================================================================
        try:
            planner_res = self.planner_service.start_investigation(
                project_id=project_id,
                objective=full_objective,
            )
            stages["planner"] = {
                "status": "SUCCESS",
                "investigation_id": investigation_id,
                "plan_summary": planner_res.get("plan", {}).get("summary", "Investigation plan ready."),
                "iterations": planner_res.get("iterations", 1),
            }
        except Exception as exc:
            err_msg = f"Planner Agent failed: {exc}"
            logger.error(err_msg, exc_info=True)
            stage_errors.append(err_msg)
            stages["planner"] = {
                "status": "FAILED",
                "error": str(exc),
            }

        # =====================================================================
        # STAGE 2: FINANCIAL DD AGENT
        # =====================================================================
        if "financial" not in enabled_ws:
            stages["financial"] = {
                "status": "SKIPPED",
                "reason": "Financial workstream is disabled in project configuration",
            }
        elif financial_docs:
            _set_agent_tasks_status("financial", "IN_PROGRESS")
            try:
                from agents.engine.runner import AgentRunner
                from agents.financial.agent import create_financial_agent

                fin_agent = create_financial_agent()
                fin_runner = AgentRunner(agent=fin_agent, max_iterations=max_agent_iterations)

                fin_obj = (
                    f"Perform financial due diligence for {target_company}. "
                    "Analyze income statements, revenue, gross profit, debt, and cash flow. "
                    "Verify figures, calculate financial metrics, and record findings with evidence."
                )

                fin_state = fin_runner.run(
                    project_id=project_id,
                    investigation_id=investigation_id,
                    workstream="financial",
                    objective=fin_obj,
                )

                stages["financial"] = {
                    "status": "SUCCESS",
                    "iterations": fin_state.get("iteration", 0),
                    "tool_calls": len(fin_state.get("tool_calls", [])),
                    "final_answer": fin_state.get("final_answer", "")[:300],
                }
                _set_agent_tasks_status("financial", "DONE")
            except Exception as exc:
                err_msg = f"Financial Agent failed: {exc}"
                logger.error(err_msg, exc_info=True)
                stage_errors.append(err_msg)
                stages["financial"] = {
                    "status": "FAILED",
                    "error": str(exc),
                }
                _set_agent_tasks_status("financial", "BLOCKED")
        else:
            stages["financial"] = {
                "status": "SKIPPED",
                "reason": "No financial documents available in project library",
            }

        # =====================================================================
        # STAGE 3: LEGAL DD AGENT
        # =====================================================================
        if "legal" not in enabled_ws:
            stages["legal"] = {
                "status": "SKIPPED",
                "reason": "Legal workstream is disabled in project configuration",
            }
        elif legal_docs:
            _set_agent_tasks_status("legal", "IN_PROGRESS")
            try:
                from agents.legal.agent import create_legal_agent

                leg_agent = create_legal_agent(max_iterations=max_agent_iterations)

                leg_obj = (
                    f"Perform legal due diligence for {target_company}. "
                    "Analyze customer agreements, master services agreements, and term sheets. "
                    "Check for change of control, assignment restrictions, termination clauses, liabilities, and non-competes. "
                    "Record legal findings with supporting evidence."
                )

                leg_state = leg_agent.investigate(
                    project_id=project_id,
                    investigation_id=investigation_id,
                    objective=leg_obj,
                )

                stages["legal"] = {
                    "status": "SUCCESS",
                    "iterations": leg_state.get("iteration", 0),
                    "tool_calls": len(leg_state.get("tool_calls", [])),
                    "final_answer": leg_state.get("final_answer", "")[:300],
                }
                _set_agent_tasks_status("legal", "DONE")
            except Exception as exc:
                err_msg = f"Legal Agent failed: {exc}"
                logger.error(err_msg, exc_info=True)
                stage_errors.append(err_msg)
                stages["legal"] = {
                    "status": "FAILED",
                    "error": str(exc),
                }
                _set_agent_tasks_status("legal", "BLOCKED")
        else:
            stages["legal"] = {
                "status": "SKIPPED",
                "reason": "No legal documents available in project library",
            }


        # =====================================================================
        # STAGE 4: CROSS-DOMAIN AGENT
        # =====================================================================
        # Collect current findings & evidence from Financial and Legal investigations to feed into Cross-Domain
        session = SessionLocal()
        existing_findings_data = []
        all_evidence_data = []
        try:
            finding_repo = FindingRepository(session)
            db_findings = finding_repo.list_for_project(project_id)
            for f in db_findings:
                ev_list = []
                for ev in (f.evidence or []):
                    ev_dict = {
                        "id": ev.id,
                        "source_label": ev.source_label,
                        "page_number": ev.page_number,
                        "quoted_text": ev.quoted_text,
                        "extracted_value": ev.extracted_value,
                        "validation_status": ev.validation_status,
                        "chunk_id": ev.chunk_id,
                        "document_id": ev.document_id,
                    }
                    ev_list.append(ev_dict)
                    all_evidence_data.append(ev_dict)

                existing_findings_data.append({
                    "id": f.id,
                    "workstream": f.workstream,
                    "title": f.title,
                    "issue": f.issue,
                    "why_it_matters": f.why_it_matters,
                    "risk_severity": f.risk_severity,
                    "conclusion": f.evidence_conclusion,
                    "evidence": ev_list,
                })
        finally:
            session.close()

        fin_findings = [f for f in existing_findings_data if f["workstream"] == "financial"]
        leg_findings = [f for f in existing_findings_data if f["workstream"] == "legal"]

        # Check preconditions: Cross-domain requires both financial and legal inputs (documents or findings)
        has_financial_input = bool(fin_findings or financial_docs)
        has_legal_input = bool(leg_findings or legal_docs)

        if not has_financial_input and not has_legal_input:
            stages["cross_domain"] = {
                "status": "SKIPPED",
                "reason": "Neither financial nor legal documents/findings are available in project library",
            }
        elif not has_financial_input:
            stages["cross_domain"] = {
                "status": "SKIPPED",
                "reason": "No financial documents or findings available to perform cross-domain comparison against legal domain",
            }
        elif not has_legal_input:
            stages["cross_domain"] = {
                "status": "SKIPPED",
                "reason": "No legal documents or findings available to perform cross-domain comparison against financial domain",
            }
        else:
            _set_agent_tasks_status("cross_domain", "IN_PROGRESS")
            try:
                from agents.cross_domain.agent import create_cross_domain_agent

                cross_agent = create_cross_domain_agent(max_iterations=max_agent_iterations)

                fin_titles = [f["title"] for f in fin_findings]
                leg_titles = [f["title"] for f in leg_findings]

                cross_obj = (
                    f"Perform cross-domain due diligence for {target_company}.\n"
                    f"Financial Domain Context: {len(fin_findings)} findings ({', '.join(fin_titles) if fin_titles else 'Documents available'}).\n"
                    f"Legal Domain Context: {len(leg_findings)} findings ({', '.join(leg_titles) if leg_titles else 'Documents available'}).\n"
                    "Compare financial metrics, revenue, and debt against legal commitments, change of control clauses, and customer agreements. "
                    "Identify contradictions, covenant risks, and cross-workstream dependencies. "
                    "Record cross-domain findings with evidence."
                )

                cross_state = cross_agent.investigate(
                    project_id=project_id,
                    investigation_id=investigation_id,
                    objective=cross_obj,
                    initial_findings=existing_findings_data,
                    initial_evidence=all_evidence_data,
                )

                stages["cross_domain"] = {
                    "status": "SUCCESS",
                    "iterations": cross_state.get("iteration", 0),
                    "tool_calls": len(cross_state.get("tool_calls", [])),
                    "final_answer": cross_state.get("final_answer", "")[:300],
                }
                _set_agent_tasks_status("cross_domain", "DONE")
            except Exception as exc:
                err_msg = f"Cross-Domain Agent failed: {exc}"
                logger.error(err_msg, exc_info=True)
                stage_errors.append(err_msg)
                stages["cross_domain"] = {
                    "status": "FAILED",
                    "error": str(exc),
                }
                _set_agent_tasks_status("cross_domain", "BLOCKED")

        # =====================================================================
        # STAGE 5: EVIDENCE VALIDATION & DEDUPLICATION
        # =====================================================================
        session = SessionLocal()
        try:
            dedup_count = deduplicate_project_findings(project_id, session)
            validation_res = validate_project_evidence(project_id, session)

            stages["evidence_validation"] = {
                "status": "SUCCESS",
                "total_evidence": validation_res["total_evidence"],
                "verified_count": validation_res["verified_count"],
                "unverified_count": validation_res["unverified_count"],
                "discrepancy_count": validation_res.get("discrepancy_count", 0),
                "ambiguous_count": validation_res.get("ambiguous_count", 0),
                "unsupported_count": validation_res.get("unsupported_count", 0),
                "duplicates_cleaned": dedup_count,
            }
        except Exception as exc:
            err_msg = f"Evidence Validation failed: {exc}"
            logger.error(err_msg, exc_info=True)
            stage_errors.append(err_msg)
            stages["evidence_validation"] = {
                "status": "FAILED",
                "error": str(exc),
            }
        finally:
            session.close()

        # =====================================================================
        # STAGE 6: OVERALL WORKFLOW STATUS & PERSISTENCE
        # =====================================================================
        active_stages = [v for k, v in stages.items() if v.get("status") != "SKIPPED"]
        failed_stages = [v for v in active_stages if v.get("status") == "FAILED"]

        if not active_stages or len(failed_stages) == len(active_stages):
            overall_status = "FAILED"
        elif failed_stages:
            overall_status = "PARTIAL_FAILURE"
        else:
            overall_status = "COMPLETED"

        # Update Investigation status and plan summary in DB
        session = SessionLocal()
        try:
            inv_repo = InvestigationRepository(session)
            investigation = inv_repo.get(investigation_id)
            if investigation:
                plan_data = dict(investigation.plan or {})
                plan_data["orchestration_summary"] = {
                    "overall_status": overall_status,
                    "stages": stages,
                    "stage_errors": stage_errors,
                }
                inv_repo.update_status(
                    investigation_id=investigation_id,
                    status=overall_status,
                    plan=plan_data,
                )
                inv_repo.save()

            # Retrieve final findings count
            finding_repo = FindingRepository(session)
            final_findings = finding_repo.list_for_project(project_id)
            findings_summary = [
                {
                    "id": f.id,
                    "workstream": f.workstream,
                    "title": f.title,
                    "risk_severity": f.risk_severity,
                    "status": f.status,
                    "evidence_count": len(f.evidence or []),
                    "verified_evidence_count": len([e for e in (f.evidence or []) if e.validation_status == "VERIFIED"]),
                    "discrepancy_evidence_count": len([e for e in (f.evidence or []) if e.validation_status == "FLAGGED_DISCREPANCY"]),
                    "unverified_evidence_count": len([e for e in (f.evidence or []) if e.validation_status not in ["VERIFIED", "FLAGGED_DISCREPANCY"]]),
                }
                for f in final_findings
            ]
        finally:
            session.close()

        return {
            "success": overall_status != "FAILED",
            "overall_status": overall_status,
            "investigation_id": investigation_id,
            "project_id": project_id,
            "stages": stages,
            "stage_errors": stage_errors,
            "findings_count": len(findings_summary),
            "findings_summary": findings_summary,
        }

    def get_latest_status(self, project_id: str) -> dict[str, Any] | None:
        """Retrieve the latest full DD orchestration status for a project."""
        session = SessionLocal()
        try:
            inv_repo = InvestigationRepository(session)
            latest = inv_repo.get_latest_for_project(project_id)
            if not latest:
                return None

            plan_data = latest.plan or {}
            orch_summary = plan_data.get("orchestration_summary", {})

            finding_repo = FindingRepository(session)
            findings = finding_repo.list_for_project(project_id)

            return {
                "investigation_id": latest.id,
                "project_id": latest.project_id,
                "overall_status": latest.status,
                "objective": latest.objective,
                "created_at": latest.created_at.isoformat() if latest.created_at else None,
                "stages": orch_summary.get("stages", {}),
                "stage_errors": orch_summary.get("stage_errors", []),
                "findings_count": len(findings),
            }
        finally:
            session.close()
