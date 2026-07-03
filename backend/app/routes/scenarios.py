"""Scenario default + ensure-default routes.

CRUD for scenarios is auto-generated from the section registry
(``/projects/{id}/scenarios``). These add the two behaviours CRUD alone can't:
setting the project's default scenario, and ensuring a project always has at
least a Base Case default (used to migrate older projects on first open).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..models import ScenarioAssumption
from ..services import ProjectService
from ..services import scenario_service as scn
from .deps import get_service, project_or_404

router = APIRouter(prefix="/projects/{project_id}/scenarios", tags=["Scenarios"])


@router.post("/ensure-default", response_model=list[ScenarioAssumption])
def ensure_default(project_id: str, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    if scn.ensure_default(project):
        project.touch()
        service.storage.save_project(project)
    return project.scenarios


@router.post("/{scenario_id}/default", response_model=ScenarioAssumption)
def set_default(project_id: str, scenario_id: str, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    match = scn.set_default(project, scenario_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scenario not found")
    project.touch()
    service.storage.save_project(project)
    return match
