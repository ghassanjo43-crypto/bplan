"""Project-level routes: CRUD, completion, review, export."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..models import BusinessPlanProject, CompletionReport, ProjectSummary, ReviewStatus
from ..services import ProjectService, build_completion_report, build_review_status
from ..storage.base import NotFoundError
from .deps import get_service, project_or_404

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class CompanyNameUpdate(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200)


@router.get("", response_model=list[ProjectSummary])
def list_projects(request: Request, service: ProjectService = Depends(get_service)):
    summaries = service.list_summaries()
    user = getattr(request.state, "user", None)
    if user is not None and getattr(user, "role", None) != "admin":
        from ..dependencies.auth import authorized_company_ids
        allowed = set(authorized_company_ids(user) or [])
        summaries = [s for s in summaries if s.company_id in allowed]
    return summaries


@router.post("", response_model=BusinessPlanProject, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, request: Request, service: ProjectService = Depends(get_service)):
    project = BusinessPlanProject(name=payload.name)
    user = getattr(request.state, "user", None)
    # Normal users always create projects inside their own company (no orphans).
    if user is not None and getattr(user, "role", None) != "admin" and getattr(user, "company_id", None):
        project.company_id = user.company_id
    return service.create(project)


@router.get("/{project_id}", response_model=BusinessPlanProject)
def get_project(project_id: str, service: ProjectService = Depends(get_service)):
    return project_or_404(project_id, service)


@router.put("/{project_id}", response_model=BusinessPlanProject)
def replace_project(
    project_id: str,
    payload: BusinessPlanProject,
    service: ProjectService = Depends(get_service),
):
    try:
        return service.replace(project_id, payload)
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project {project_id!r} not found")


@router.put("/{project_id}/company-name", response_model=ProjectSummary)
def update_company_name(
    project_id: str,
    payload: CompanyNameUpdate,
    service: ProjectService = Depends(get_service),
):
    """Rename the company/business name (the project's main title)."""
    try:
        service.update_business_name(project_id, payload.business_name.strip())
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project {project_id!r} not found")
    return next((s for s in service.list_summaries() if s.id == project_id))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, service: ProjectService = Depends(get_service)):
    try:
        service.delete(project_id)
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project {project_id!r} not found")


@router.get("/{project_id}/completion", response_model=CompletionReport)
def get_completion(project_id: str, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return build_completion_report(project)


@router.get("/{project_id}/review", response_model=ReviewStatus)
def get_review(project_id: str, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return build_review_status(project)


@router.get("/{project_id}/export-json")
def export_json(project_id: str, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    filename = f"{project.name.replace(' ', '_')}_assumptions.json"
    return JSONResponse(
        content=project.model_dump(mode="json"),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
