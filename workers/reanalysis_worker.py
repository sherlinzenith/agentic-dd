from __future__ import annotations

import logging
import sys
import threading
import time
from datetime import datetime
from typing import Any

from database.session import SessionLocal
from dd_requests.models import DDRequest
from evidence.models import Evidence
from findings.models import Finding
from findings.repository import FindingRepository
from reanalysis.models import DDReanalysisRun
from retrieval.repositories.document_repository import DocumentRepository
from services.evidence_validation_service import validate_project_evidence_service
from tasks.models import DDTask

logger = logging.getLogger(__name__)


class ReanalysisWorker:
    """
    Automated Human Review & Follow-Up Reanalysis Worker.

    Picks up queued re-analysis runs, inspects requested source clarifications,
    executes targeted agent investigations, runs evidence validation against stored chunks,
    and updates findings, tasks, and requests with full audit history.
    """

    def __init__(self, max_iterations: int = 10):
        self.max_iterations = max_iterations
        self._agents: dict[str, Any] = {}

    def get_agent(self, workstream: str) -> dict[str, Any]:
        """Lazy-load the appropriate agent runner for the target workstream."""
        ws = (workstream or "").lower()
        if ws in self._agents:
            return self._agents[ws]

        if ws == "financial":
            from agents.engine.runner import AgentRunner
            from agents.financial.agent import create_financial_agent

            fin_agent = create_financial_agent()
            runner = AgentRunner(agent=fin_agent, max_iterations=self.max_iterations)
            self._agents["financial"] = {"agent": fin_agent, "runner": runner}
            return self._agents["financial"]

        elif ws == "legal":
            from agents.legal.agent import LegalAgent

            leg_agent = LegalAgent(max_iterations=self.max_iterations)
            self._agents["legal"] = {"agent": leg_agent, "runner": leg_agent.runner}
            return self._agents["legal"]

        elif ws == "cross_domain":
            from agents.cross_domain.agent import CrossDomainAgent

            cross_agent = CrossDomainAgent(max_iterations=self.max_iterations)
            self._agents["cross_domain"] = {"agent": cross_agent, "runner": cross_agent.runner}
            return self._agents["cross_domain"]

        else:
            raise ValueError(f"No DD agent configured for workstream: '{workstream}'")

    def get_next_run(self, db) -> DDReanalysisRun | None:
        """Fetch the oldest queued re-analysis run."""
        return (
            db.query(DDReanalysisRun)
            .filter(DDReanalysisRun.status == "QUEUED")
            .order_by(DDReanalysisRun.created_at.asc())
            .first()
        )

    def load_context(self, db, run: DDReanalysisRun) -> dict[str, Any]:
        """Load finding, request, linked task, existing evidence, and document catalog."""
        finding = db.get(Finding, run.finding_id) if run.finding_id else None
        request = db.get(DDRequest, run.request_id) if run.request_id else None

        task = None
        if run.request_id:
            task = (
                db.query(DDTask)
                .filter(DDTask.request_id == run.request_id)
                .order_by(DDTask.created_at.desc())
                .first()
            )

        evidence = []
        if run.finding_id:
            evidence = (
                db.query(Evidence)
                .filter(Evidence.finding_id == run.finding_id)
                .order_by(Evidence.created_at.asc())
                .all()
            )

        doc_repo = DocumentRepository(db)
        documents = doc_repo.list_documents(run.project_id)

        return {
            "finding": finding,
            "request": request,
            "task": task,
            "evidence": evidence,
            "documents": documents,
        }

    def run_once(self, run_id: str | None = None) -> dict[str, Any]:
        """
        Execute a single reanalysis run (either a specific run_id or the next queued run).
        Transitions state: QUEUED -> RUNNING -> COMPLETE / FAILED.
        """
        db = SessionLocal()
        try:
            if run_id:
                run = db.get(DDReanalysisRun, run_id)
            else:
                run = self.get_next_run(db)

            if not run:
                return {
                    "status": "NO_WORK",
                    "message": "No queued re-analysis runs found.",
                }

            # 1. Transition to RUNNING state
            run.status = "RUNNING"
            run.started_at = datetime.utcnow()

            # Update linked task to IN_PROGRESS
            if run.request_id:
                task = (
                    db.query(DDTask)
                    .filter(DDTask.request_id == run.request_id)
                    .order_by(DDTask.created_at.desc())
                    .first()
                )
                if task and task.status == "TODO":
                    task.status = "IN_PROGRESS"

            db.commit()
            db.refresh(run)

            try:
                # 2. Load context
                context = self.load_context(db, run)
                finding = context["finding"]
                request = context["request"]
                task = context["task"]
                evidence = context["evidence"]
                documents = context["documents"]

                if not finding:
                    raise ValueError(f"Associated finding '{run.finding_id}' not found.")

                selected = self.get_agent(finding.workstream)
                runner = selected["runner"]
                agent = selected["agent"]

                # 3. Build evidence context
                evidence_context = []
                for item in evidence:
                    evidence_context.append({
                        "evidence_id": item.id,
                        "document": item.source_label,
                        "page": item.page_number,
                        "chunk_id": item.chunk_id,
                        "quote": item.quoted_text,
                        "extracted_value": item.extracted_value,
                        "validation_status": item.validation_status,
                        "validation_reason": item.validation_reason,
                    })

                req_clarification = (
                    request.description
                    if request and request.description
                    else (run.reason or "Clarify evidence and verify source facts.")
                )

                available_docs_str = ", ".join([d.file_name for d in documents]) or "None"

                objective = (
                    f"Re-investigate finding: '{finding.title}'.\n\n"
                    f"Workstream: {finding.workstream.upper()}\n"
                    f"Current Issue:\n{finding.issue}\n\n"
                    f"Why It Matters:\n{finding.why_it_matters or 'Material DD risk factor'}\n\n"
                    f"Reviewer Clarification Request:\n{req_clarification}\n\n"
                    f"Available Project Documents:\n{available_docs_str}\n\n"
                    f"Existing Cited Evidence:\n{evidence_context}\n\n"
                    "INSTRUCTIONS:\n"
                    "1. Search project documents and retrieve exact text/tables to investigate the reviewer's request.\n"
                    "2. Verify whether source evidence supports, clarifies, or refutes the issue.\n"
                    "3. Record any new findings or supporting evidence with exact quotes.\n"
                    "4. Provide a clear, factual reanalysis conclusion."
                )

                # 4. Execute the agent runner
                state = runner.run(
                    project_id=run.project_id,
                    investigation_id=run.investigation_id or "",
                    workstream=finding.workstream,
                    objective=objective,
                )

                result_summary = (
                    state.get("final_answer")
                    or f"Re-analysis completed for '{finding.title}'. Source clarified according to reviewer request."
                )

                # 5. Run Evidence Validation Service on project to verify any new evidence
                validate_project_evidence_service(run.project_id, db)

                # 6. Apply conclusion and return finding to REVIEW_REQUIRED for human review
                finding_repo = FindingRepository(db)
                finding_repo.apply_reanalysis_result(
                    finding=finding,
                    conclusion=result_summary,
                )

                # 7. Update run, request, and task states
                run.status = "COMPLETE"
                run.result_summary = result_summary
                run.completed_at = datetime.utcnow()

                if request:
                    request.status = "RESOLVED"
                    request.resolved_at = datetime.utcnow()

                if task:
                    task.status = "DONE"
                    task.completed_at = datetime.utcnow()

                db.commit()

                logger.info(f"Re-analysis run '{run.id}' completed successfully.")
                return {
                    "status": "COMPLETE",
                    "run_id": run.id,
                    "finding_id": finding.id,
                    "agent": getattr(agent, "name", finding.workstream),
                    "finding_status": finding.status,
                    "result_summary": result_summary,
                }

            except Exception as exc:
                db.rollback()
                logger.error(f"Re-analysis run '{run.id}' failed: {exc}", exc_info=True)

                failed_run = db.get(DDReanalysisRun, run.id)
                if failed_run:
                    failed_run.status = "FAILED"
                    failed_run.result_summary = str(exc)
                    failed_run.completed_at = datetime.utcnow()

                if run.request_id:
                    failed_task = (
                        db.query(DDTask)
                        .filter(DDTask.request_id == run.request_id)
                        .order_by(DDTask.created_at.desc())
                        .first()
                    )
                    if failed_task:
                        failed_task.status = "FAILED"

                db.commit()

                return {
                    "status": "FAILED",
                    "run_id": run.id,
                    "error": str(exc),
                }

        finally:
            db.close()


def process_next_reanalysis() -> dict[str, Any]:
    """Public helper to process the next queued re-analysis run."""
    worker = ReanalysisWorker()
    return worker.run_once()


# =====================================================================
# Background Daemon Loop
# =====================================================================
_worker_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _background_worker_loop(poll_interval: float = 3.0):
    logger.info("Background Reanalysis Worker loop started.")
    worker = ReanalysisWorker()
    while not _stop_event.is_set():
        try:
            res = worker.run_once()
            if res.get("status") in ("COMPLETE", "FAILED"):
                logger.info(f"Background worker processed job: {res}")
                time.sleep(1.0)
            else:
                time.sleep(poll_interval)
        except Exception as exc:
            logger.error(f"Error in background worker loop: {exc}")
            time.sleep(poll_interval)


def start_background_worker(poll_interval: float = 3.0):
    """Start the background reanalysis worker thread if not already running."""
    global _worker_thread
    if _worker_thread is not None and _worker_thread.is_alive():
        return

    _stop_event.clear()
    _worker_thread = threading.Thread(
        target=_background_worker_loop,
        args=(poll_interval,),
        daemon=True,
        name="DDReanalysisWorkerThread",
    )
    _worker_thread.start()
    logger.info("Background Reanalysis Worker thread launched.")


def stop_background_worker():
    """Signal the background worker thread to stop."""
    global _worker_thread
    _stop_event.set()
    if _worker_thread:
        _worker_thread.join(timeout=2.0)
        _worker_thread = None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print("=" * 60)
    print("Agentic Due Diligence — Reanalysis Worker Process")
    print("=" * 60)
    print("Starting worker loop (polling for QUEUED jobs)... Press Ctrl+C to exit.")

    worker = ReanalysisWorker()
    try:
        while True:
            res = worker.run_once()
            if res.get("status") in ("COMPLETE", "FAILED"):
                print(f"[{datetime.utcnow().isoformat()}] Processed run: {res}")
                time.sleep(1.0)
            else:
                time.sleep(3.0)
    except KeyboardInterrupt:
        print("\nReanalysis Worker stopped by user.")
        sys.exit(0)
