
from __future__ import annotations

from datetime import datetime

from database.session import SessionLocal

from reanalysis.models import DDReanalysisRun
from findings.models import Finding
from findings.repository import FindingRepository
from dd_requests.models import DDRequest
from evidence.models import Evidence

from agents.engine.runner import AgentRunner

from agents.financial.agent import create_financial_agent
from agents.legal.agent import LegalAgent
from agents.cross_domain.agent import CrossDomainAgent


class ReanalysisWorker:

    def __init__(self, max_iterations: int = 12):

        # Financial agent is created through its factory.
        financial_agent = create_financial_agent()

        # FinancialAgent factory returns BaseAgent,
        # so create its runner here.
        financial_runner = AgentRunner(
            agent=financial_agent,
            max_iterations=max_iterations,
        )

        # Legal and Cross-Domain already expose their runners.
        legal_agent = LegalAgent(
            max_iterations=max_iterations,
        )

        cross_domain_agent = CrossDomainAgent(
            max_iterations=max_iterations,
        )

        self.agents = {
            "financial": {
                "agent": financial_agent,
                "runner": financial_runner,
            },
            "legal": {
                "agent": legal_agent,
                "runner": legal_agent.runner,
            },
            "cross_domain": {
                "agent": cross_domain_agent,
                "runner": cross_domain_agent.runner,
            },
        }

    def get_next_run(self, db):

        return (
            db.query(DDReanalysisRun)
            .filter(
                DDReanalysisRun.status == "QUEUED"
            )
            .order_by(
                DDReanalysisRun.created_at.asc()
            )
            .first()
        )

    def load_context(self, db, run):

        finding = None
        request = None
        evidence = []

        if run.finding_id:
            finding = db.get(
                Finding,
                run.finding_id,
            )

        if run.request_id:
            request = db.get(
                DDRequest,
                run.request_id,
            )

        if run.finding_id:
            evidence = (
                db.query(Evidence)
                .filter(
                    Evidence.finding_id == run.finding_id
                )
                .order_by(
                    Evidence.created_at.asc()
                )
                .all()
            )

        return {
            "finding": finding,
            "request": request,
            "evidence": evidence,
        }

    def select_agent(self, finding):

        if not finding:
            raise ValueError(
                "Reanalysis finding could not be found."
            )

        workstream = (
            finding.workstream or ""
        ).lower()

        if workstream not in self.agents:
            raise ValueError(
                f"No DD agent configured for workstream: {workstream}"
            )

        return self.agents[workstream]

    def run_once(self):

        db = SessionLocal()

        try:

            run = self.get_next_run(db)

            if not run:
                return {
                    "status": "NO_WORK",
                    "message": "No queued re-analysis runs.",
                }

            run.status = "RUNNING"
            run.started_at = datetime.utcnow()

            db.commit()
            db.refresh(run)

            try:

                context = self.load_context(
                    db,
                    run,
                )

                finding = context["finding"]
                request = context["request"]
                evidence = context["evidence"]

                selected = self.select_agent(
                    finding
                )

                runner = selected["runner"]
                agent = selected["agent"]

                evidence_context = []

                for item in evidence:

                    evidence_context.append({
                        "evidence_id": item.id,
                        "document_id": item.document_id,
                        "chunk_id": item.chunk_id,
                        "page_number": item.page_number,
                        "location": item.location,
                        "quoted_text": item.quoted_text,
                        "extracted_value": item.extracted_value,
                        "source_label": item.source_label,
                        "validation_status": item.validation_status,
                    })

                objective = (
                    f"Re-investigate finding '{finding.title}'.\n\n"
                    f"Original issue:\n"
                    f"{finding.issue}\n\n"
                    f"Why it matters:\n"
                    f"{finding.why_it_matters or 'Not specified'}\n\n"
                    f"Newly submitted evidence:\n"
                    f"{evidence_context}\n\n"
                    "Determine whether the evidence changes the "
                    "finding, risk severity, confidence, conclusion, "
                    "or required next investigation step. "
                    "Use available tools to inspect source evidence "
                    "and do not assume the submitted evidence is sufficient."
                )

                state = runner.run(
                    project_id=run.project_id,
                    investigation_id=run.investigation_id or "",
                    workstream=finding.workstream,
                    objective=objective,
                )

                result_summary = (
                    state.get("final_answer")
                    or "Re-analysis completed."
                )

                # Persist the agent's re-analysis conclusion back to
                # the production Finding record.
                #
                # IMPORTANT:
                # We do not automatically change risk severity,
                # confidence, or approve the finding from free-form LLM text.
                finding_repository = FindingRepository(db)

                finding_repository.apply_reanalysis_result(
                    finding=finding,
                    conclusion=result_summary,
                )

                run.status = "COMPLETE"
                run.result_summary = result_summary
                run.completed_at = datetime.utcnow()

                db.commit()

                return {
                    "status": "COMPLETE",
                    "run_id": run.id,
                    "finding_id": finding.id,
                    "agent": agent.name,
                    "finding_status": finding.status,
                    "result": run.result_summary,
                }

            except Exception as exc:

                db.rollback()

                failed_run = db.get(
                    DDReanalysisRun,
                    run.id,
                )

                failed_run.status = "FAILED"
                failed_run.result_summary = str(exc)
                failed_run.completed_at = datetime.utcnow()

                db.commit()

                return {
                    "status": "FAILED",
                    "run_id": run.id,
                    "error": str(exc),
                }

        finally:
            db.close()


def process_next_reanalysis():

    worker = ReanalysisWorker()

    return worker.run_once()
