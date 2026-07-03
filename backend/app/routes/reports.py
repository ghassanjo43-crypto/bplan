"""Business plan report generator routes (Word + PDF)."""
from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from ..schemas.reports import ReportFile, ReportPreview, ReportRequest, ReportResponse
from ..services import ProjectService
from ..services import pdf_report_service as pdfsvc
from ..services import report_data_service as rd
from ..services import word_report_service as wordsvc
from .deps import get_service, project_or_404

router = APIRouter(prefix="/projects/{project_id}/reports", tags=["reports"])

Scenario = Query("base")   # a scenario id or a legacy type; resolved server-side
View = Query("yearly", pattern="^(monthly|yearly|annual)$")
Style = Query("investor", pattern="^(investor|bank|board|management|full)$")

_MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "html": "text/html",
}


def _download_url(project_id: str, report_id: str) -> str:
    return f"/api/projects/{project_id}/reports/{report_id}/download"


def _to_response(project_id: str, f: ReportFile) -> ReportResponse:
    return ReportResponse(**f.model_dump(), download_url=_download_url(project_id, f.report_id))


@router.get("/business-plan/preview", response_model=ReportPreview)
def report_preview(project_id: str, scenario: str = Scenario, view: str = View, report_style: str = Style,
                   service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    options = ReportRequest(scenario=scenario, view=view, report_style=report_style)
    return rd.build_report_preview(project, scenario, view, options)


@router.post("/business-plan/generate-word", response_model=ReportResponse)
def generate_word(project_id: str, request: ReportRequest, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    try:
        report = wordsvc.generate_business_plan_docx(project, request)
    except Exception as exc:  # surface the real cause to the client
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Word report generation failed: {type(exc).__name__}: {exc}")
    return _to_response(project_id, report)


@router.post("/business-plan/generate-pdf", response_model=ReportResponse)
def generate_pdf(project_id: str, request: ReportRequest, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    try:
        report = pdfsvc.generate_business_plan_pdf(project, request)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"PDF report generation failed: {type(exc).__name__}: {exc}")
    return _to_response(project_id, report)


@router.get("", response_model=list[ReportResponse])
def list_reports(project_id: str, service: ProjectService = Depends(get_service)):
    project_or_404(project_id, service)
    out = []
    for entry in rd.load_index(project_id):
        try:
            out.append(_to_response(project_id, ReportFile(**entry)))
        except Exception:
            continue
    return out


@router.get("/{report_id}/download")
def download_report(project_id: str, report_id: str, service: ProjectService = Depends(get_service)):
    project_or_404(project_id, service)
    entry = next((e for e in rd.load_index(project_id) if e.get("report_id") == report_id), None)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    path = rd.report_path(project_id, entry["file_name"])
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file is missing")
    media_type = _MIME.get(entry.get("format"), mimetypes.guess_type(str(path))[0] or "application/octet-stream")
    return FileResponse(path, media_type=media_type, filename=entry["file_name"])


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(project_id: str, report_id: str, service: ProjectService = Depends(get_service)):
    project_or_404(project_id, service)
    if not rd.delete_report(project_id, report_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return None
