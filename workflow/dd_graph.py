import uuid
from pathlib import Path

from langgraph.types import Command

from agents.lead_agent import plan_types
from processing.document_processor import extract_all_documents
from findings.finding_store import reset_findings, set_job
from workflow.checkpointer import get_checkpointer
from workflow.orchestrator import build_dd_graph

DOCUMENTS_DIR = Path(__file__).resolve().parent.parent / "documents"

LAST_JOB_FILE = Path(__file__).resolve().parent.parent / "results" / "last_job.txt"

_graph = None


def latest_job_id():
    if LAST_JOB_FILE.exists():
        return LAST_JOB_FILE.read_text(encoding="utf-8").strip() or None
    return None


def get_graph():
    """One graph + one checkpointer per process."""
    global _graph
    if _graph is None:
        _graph = build_dd_graph(checkpointer=get_checkpointer())
    return _graph


def _config(job_id):
    return {"configurable": {"thread_id": job_id}}


def job_status(job_id):
    """Return {"job_id", "status", "waiting_for", "findings"} for a job."""

    snapshot = get_graph().get_state(_config(job_id))
    values = snapshot.values or {}

    if not values:
        return {"job_id": job_id, "status": "NOT_FOUND", "waiting_for": None, "findings": 0}

    waiting = snapshot.next[0] if snapshot.next else None

    if waiting == "review":
        status = "AWAITING_REVIEW"
    elif waiting == "await_evidence":
        status = "AWAITING_EVIDENCE"
    elif waiting:
        status = "RUNNING"
    else:
        status = values.get("status", "COMPLETE")

    return {
        "job_id": job_id,
        "status": status,
        "waiting_for": waiting,
        "findings": len(values.get("findings", [])),
    }


def job_details(job_id):
    """Everything the UI needs for the Overview / Financial / Legal pages."""

    info = job_status(job_id)

    if info["status"] == "NOT_FOUND":
        return info

    values = get_graph().get_state(_config(job_id)).values or {}

    return {
        **info,
        "inventory": values.get("inventory", []),
        "inventory_summary": values.get("inventory_summary", {}),
        "readiness": values.get("readiness", {}),
        "plan": values.get("plan", []),
        "lead_notes": values.get("lead_notes", []),
        "activity": values.get("activity", []),
    }


def start_job(job_id=None, dd_types=None, documents=None, overrides=None):
    """Load documents and run until the graph finishes or pauses for human review."""

    dd_types = dd_types or ["financial"]
    plan_types(dd_types)  # fails early if no agent exists

    job_id = job_id or f"DD-{uuid.uuid4().hex[:8]}"

    LAST_JOB_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_JOB_FILE.write_text(job_id, encoding="utf-8")

    set_job(job_id)
    reset_findings()

    if documents is None:
        print("\n[DD Workflow] Loading documents...")
        documents = extract_all_documents(str(DOCUMENTS_DIR))
    print(f"[DD Workflow] {len(documents)} documents in the workspace.")

    get_graph().invoke(
        {
            "documents": documents,
            "findings": [],
            "status": "STARTED",
            "dd_types": dd_types,
            "overrides": overrides or {},
        },
        _config(job_id),
    )

    return job_status(job_id)


def resume_job(job_id):
    """Continue a paused job (after reviews were saved, or new documents were added)."""

    if job_status(job_id)["status"] == "NOT_FOUND":
        raise ValueError(f"Job {job_id} not found.")

    get_graph().invoke(Command(resume=True), _config(job_id))

    return job_status(job_id)


def run_financial_dd():
    """Backward compatible: start a job and return its result."""

    info = start_job()
    values = get_graph().get_state(_config(info["job_id"])).values

    return {**values, "status": info["status"], "job_id": info["job_id"]}


if __name__ == "__main__":

    info = start_job()

    print("\n===== JOB =====")
    print(info)

    if info["status"] == "AWAITING_REVIEW":
        print("\nJob is paused for human review.")
        print("Review the findings in the UI, then resume with:")
        print("  python -m workflow.resume " + info["job_id"])
