from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from findings.finding_store import (
    load_findings,
    load_metrics,
    save_review,
    set_job,
)


from processing.document_classifier import classify_documents
from processing.document_processor import extract_all_documents
from reports.report_generator import save_report

DOCUMENTS_DIR = Path(__file__).resolve().parent.parent / "documents"


app = FastAPI(
    title="Agentic Due Diligence API",
    version="0.1.0",
)


def _scope(job_id: Optional[str] = None):
    """Findings belong to a job. No job_id -> the latest job."""

    from workflow.dd_graph import latest_job_id

    set_job(job_id or latest_job_id())


class ReviewRequest(BaseModel):

    action: str

    reviewer: str = "Human Reviewer"

    comment: str = ""


@app.get("/")
def root():

    return {
        "system": "Agentic Due Diligence",
        "status": "running",
    }


@app.get("/findings")
def get_findings(job_id: Optional[str] = None):

    _scope(job_id)

    return {
        "findings": load_findings()
    }


@app.get("/findings/{finding_id}")
def get_finding(finding_id: str, job_id: Optional[str] = None):

    _scope(job_id)

    findings = load_findings()

    for finding in findings:

        if finding.get("finding_id") == finding_id:
            return finding

    raise HTTPException(
        status_code=404,
        detail="Finding not found.",
    )


@app.post("/findings/{finding_id}/review")
def review_finding(
    finding_id: str,
    request: ReviewRequest,
    job_id: Optional[str] = None,
):

    _scope(job_id)

    action = request.action.upper()

    allowed_actions = {
        "APPROVE",
        "REJECT",
        "REQUEST_MORE_EVIDENCE",
    }

    if action not in allowed_actions:

        raise HTTPException(
            status_code=400,
            detail=(
                "Action must be APPROVE, "
                "REJECT, or REQUEST_MORE_EVIDENCE."
            ),
        )

    try:

        finding = save_review(
            finding_id=finding_id,
            action=action,
            reviewer=request.reviewer,
            comment=request.comment,
        )

        return {
            "success": True,
            "finding": finding,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


@app.get("/documents")
def get_documents():

    try:
        docs = extract_all_documents(str(DOCUMENTS_DIR))
    except FileNotFoundError:
        return {"documents": []}

    types = {c["document"]: c for c in classify_documents(docs)}

    return {
        "documents": [
            {
                "document": d["document"],
                "pages": len(d["pages"]),
                "type": types[d["document"]]["type"],
                "confidence": types[d["document"]]["confidence"],
            }
            for d in docs
        ]
    }


@app.post("/run")
def run_dd(types: str = "financial"):
    """Start a DD job. It runs until it pauses for human review."""

    from workflow.dd_graph import start_job

    try:
        return start_job(dd_types=[t for t in types.split(",") if t.strip()])
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/jobs/latest")
def latest_job():

    from workflow.dd_graph import latest_job_id

    return {"job_id": latest_job_id()}


@app.get("/metrics")
def get_metrics(job_id: Optional[str] = None):

    _scope(job_id)

    return {"metrics": load_metrics()}


@app.get("/jobs/{job_id}/details")
def get_job_details(job_id: str):

    from workflow.dd_graph import job_details

    info = job_details(job_id)

    if info["status"] == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Job not found.")

    return info


@app.get("/jobs/{job_id}")
def get_job(job_id: str):

    from workflow.dd_graph import job_status

    info = job_status(job_id)

    if info["status"] == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Job not found.")

    return info


@app.post("/jobs/{job_id}/resume")
def resume(job_id: str):
    """Continue a paused job after findings were reviewed / new documents added."""

    from workflow.dd_graph import resume_job

    try:
        return resume_job(job_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.get("/report", response_class=HTMLResponse)
def get_report(job_id: Optional[str] = None):

    _scope(job_id)

    try:
        docs = extract_all_documents(str(DOCUMENTS_DIR))
    except FileNotFoundError:
        docs = []

    return save_report(load_findings(), docs, metrics=load_metrics())
