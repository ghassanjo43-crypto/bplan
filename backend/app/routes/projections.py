"""Projection period + revenue/direct-cost/expense projection grid routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..models import BusinessPlanProject
from ..schemas.projection import (
    ApplyGrowthRequest,
    BulkPatch,
    CellPatch,
    FillRightRequest,
    ProjectionGrid,
    ProjectionPeriod,
)
from ..services import ProjectService
from ..services import direct_cost_projection_service as dcp
from ..services import operating_expense_projection_service as oep
from ..services import projection_period_service as pps
from ..services import revenue_projection_service as rps
from .deps import get_service, project_or_404

router = APIRouter(prefix="/projects/{project_id}", tags=["projections"])

Mode = Query("monthly", pattern="^(monthly|annual)$")


def _save(service: ProjectService, project: BusinessPlanProject) -> None:
    project.touch()
    service.storage.save_project(project)


# -- Projection periods -----------------------------------------------------
@router.get("/projection-periods", response_model=list[ProjectionPeriod])
def projection_periods(project_id: str, mode: str = Mode, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return pps.periods_for(project, mode)


# -- Setup list aliases (Setup tabs) ---------------------------------------
# NOTE: the former "/revenue-streams" alias (which returned project.products)
# was removed — that slug now belongs to the Revenue Stream wizard's generic
# collection router (GET/POST/PUT/DELETE over project.revenue_streams). Leaving
# the alias here shadowed the collection GET, so the wizard's list read back
# products and edits could not locate the stream being edited.
@router.get("/direct-cost-items")
def direct_cost_items(project_id: str, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return project.direct_costs


@router.get("/operating-expense-items")
def operating_expense_items(project_id: str, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return project.operating_expenses


# -- Revenue projection -----------------------------------------------------
@router.get("/revenue-projection", response_model=ProjectionGrid, response_model_exclude_none=True)
def revenue_grid(project_id: str, mode: str = Mode, service: ProjectService = Depends(get_service)):
    # Viewing is read-only: schedules are seeded deterministically in-memory and
    # only persisted when the user edits a cell (avoids writing on every view).
    project = project_or_404(project_id, service)
    return rps.generate_revenue_grid(project, mode)


@router.put("/revenue-projection/cell", response_model=ProjectionGrid, response_model_exclude_none=True)
def revenue_cell(project_id: str, patch: CellPatch, mode: str = Mode, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    rps.apply_cell_patch(project, patch, mode)
    _save(service, project)
    return rps.generate_revenue_grid(project, mode)


@router.put("/revenue-projection/bulk", response_model=ProjectionGrid, response_model_exclude_none=True)
def revenue_bulk(project_id: str, payload: BulkPatch, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    for patch in payload.cells:
        rps.apply_cell_patch(project, patch, payload.mode)
    _save(service, project)
    return rps.generate_revenue_grid(project, payload.mode)


@router.post("/revenue-projection/apply-growth", response_model=ProjectionGrid, response_model_exclude_none=True)
def revenue_apply_growth(project_id: str, req: ApplyGrowthRequest, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    rps.apply_growth(project, req)
    _save(service, project)
    return rps.generate_revenue_grid(project, req.mode)


@router.post("/revenue-projection/fill-right", response_model=ProjectionGrid, response_model_exclude_none=True)
def revenue_fill_right(project_id: str, req: FillRightRequest, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    rps.fill_right(project, req.item_id, req.from_index, req.mode)
    _save(service, project)
    return rps.generate_revenue_grid(project, req.mode)


# -- Direct cost projection -------------------------------------------------
@router.get("/direct-cost-projection", response_model=ProjectionGrid, response_model_exclude_none=True)
def direct_cost_grid(project_id: str, mode: str = Mode, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return dcp.generate_direct_cost_grid(project, mode)


@router.put("/direct-cost-projection/cell", response_model=ProjectionGrid, response_model_exclude_none=True)
def direct_cost_cell(project_id: str, patch: CellPatch, mode: str = Mode, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    dcp.apply_cell_patch(project, patch, mode)
    _save(service, project)
    return dcp.generate_direct_cost_grid(project, mode)


@router.put("/direct-cost-projection/bulk", response_model=ProjectionGrid, response_model_exclude_none=True)
def direct_cost_bulk(project_id: str, payload: BulkPatch, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    for patch in payload.cells:
        dcp.apply_cell_patch(project, patch, payload.mode)
    _save(service, project)
    return dcp.generate_direct_cost_grid(project, payload.mode)


@router.post("/direct-cost-projection/apply-inflation", response_model=ProjectionGrid, response_model_exclude_none=True)
def direct_cost_apply_inflation(project_id: str, req: ApplyGrowthRequest, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    dcp.apply_inflation(project, req)
    _save(service, project)
    return dcp.generate_direct_cost_grid(project, req.mode)


@router.post("/direct-cost-projection/fill-right", response_model=ProjectionGrid, response_model_exclude_none=True)
def direct_cost_fill_right(project_id: str, req: FillRightRequest, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    dcp.fill_right(project, req.item_id, req.from_index, req.mode)
    _save(service, project)
    return dcp.generate_direct_cost_grid(project, req.mode)


# -- Operating expense projection ------------------------------------------
@router.get("/operating-expense-projection", response_model=ProjectionGrid, response_model_exclude_none=True)
def expense_grid(project_id: str, mode: str = Mode, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return oep.generate_expense_grid(project, mode)


@router.put("/operating-expense-projection/cell", response_model=ProjectionGrid, response_model_exclude_none=True)
def expense_cell(project_id: str, patch: CellPatch, mode: str = Mode, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    oep.apply_cell_patch(project, patch, mode)
    _save(service, project)
    return oep.generate_expense_grid(project, mode)


@router.put("/operating-expense-projection/bulk", response_model=ProjectionGrid, response_model_exclude_none=True)
def expense_bulk(project_id: str, payload: BulkPatch, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    for patch in payload.cells:
        oep.apply_cell_patch(project, patch, payload.mode)
    _save(service, project)
    return oep.generate_expense_grid(project, payload.mode)


@router.post("/operating-expense-projection/apply-inflation", response_model=ProjectionGrid, response_model_exclude_none=True)
def expense_apply_inflation(project_id: str, req: ApplyGrowthRequest, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    oep.apply_inflation(project, req)
    _save(service, project)
    return oep.generate_expense_grid(project, req.mode)


@router.post("/operating-expense-projection/fill-right", response_model=ProjectionGrid, response_model_exclude_none=True)
def expense_fill_right(project_id: str, req: FillRightRequest, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    oep.fill_right(project, req.item_id, req.from_index, req.mode)
    _save(service, project)
    return oep.generate_expense_grid(project, req.mode)
