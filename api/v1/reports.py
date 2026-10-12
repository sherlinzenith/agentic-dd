from __future__ import annotations

import json
import logging
import re
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from database.session import SessionLocal
from reports.schemas import DueDiligenceReport
from reports.service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/reports",
    tags=["reports"],
)

report_service = ReportService()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w\-_.]", "_", name.strip())
    return cleaned or "due_diligence"


@router.get("/preview", response_model=DueDiligenceReport)
def preview_report(project_id: str, legal_privilege: bool = False, db: Session = Depends(get_db)):
    """
    Compiles and returns the full structured Due Diligence report for the project.
    Can be used for interactive dashboard preview and verification.
    """
    try:
        report = report_service.compile_report(project_id=project_id, session=db, legal_privilege=legal_privilege)
        return report
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as exc:
        logger.exception("Failed to compile report for project %s", project_id)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(exc)}")


@router.get("/export/json")
def export_report_json(project_id: str, legal_privilege: bool = False, db: Session = Depends(get_db)):
    """
    Exports the Due Diligence report as a downloadable JSON file.
    """
    try:
        report = report_service.compile_report(project_id=project_id, session=db, legal_privilege=legal_privilege)
        data = report_service.generate_json(report)
        json_bytes = json.dumps(data, indent=2, default=str).encode("utf-8")
        filename = f"{_safe_filename(report.metadata.target_company)}_dd_report.json"

        return Response(
            content=json_bytes,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as exc:
        logger.exception("Failed to export JSON report for project %s", project_id)
        raise HTTPException(status_code=500, detail=f"Failed to export JSON report: {str(exc)}")


@router.get("/export/pdf")
def export_report_pdf(project_id: str, legal_privilege: bool = False, db: Session = Depends(get_db)):
    """
    Exports the Due Diligence report as an executive-ready, downloadable PDF document.
    """
    try:
        report = report_service.compile_report(project_id=project_id, session=db, legal_privilege=legal_privilege)
        pdf_bytes = report_service.generate_pdf(report)
        filename = f"{_safe_filename(report.metadata.target_company)}_dd_report.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as exc:
        logger.exception("Failed to export PDF report for project %s", project_id)
        raise HTTPException(status_code=500, detail=f"Failed to export PDF report: {str(exc)}")
