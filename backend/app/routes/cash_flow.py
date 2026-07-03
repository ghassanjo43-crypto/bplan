"""Statement of Cash Flows (indirect method) routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..schemas.cash_flow import (
    CashFlowReconciliation,
    CashFlowResponse,
    CashFlowSummary,
)
from ..services import ProjectService
from ..services import cash_flow_service as cfs
from .deps import get_service, project_or_404

router = APIRouter(prefix="/projects/{project_id}/cash-flow", tags=["cash-flow"])

Scenario = Query("base")   # a scenario id or a legacy type; resolved server-side
View = Query("yearly", pattern="^(monthly|yearly|annual)$")
Method = Query("indirect", pattern="^(indirect)$")


@router.get("", response_model=CashFlowResponse, response_model_exclude_none=True)
def cash_flow(
    project_id: str,
    scenario: str = Scenario,
    view: str = View,
    method: str = Method,
    service: ProjectService = Depends(get_service),
):
    project = project_or_404(project_id, service)
    return cfs.generate_cash_flow_statement(project, scenario, view, method)


@router.get("/summary", response_model=CashFlowSummary)
def cash_flow_summary(project_id: str, scenario: str = Scenario, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return cfs.build_summary(project, scenario)


@router.get("/reconciliation", response_model=CashFlowReconciliation)
def cash_flow_reconciliation(project_id: str, scenario: str = Scenario, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return cfs.build_reconciliation(project, scenario)


@router.get("/drilldown/{line_item_key}")
def cash_flow_drilldown(
    project_id: str,
    line_item_key: str,
    scenario: str = Scenario,
    view: str = View,
    service: ProjectService = Depends(get_service),
):
    project = project_or_404(project_id, service)
    return cfs.drilldown(project, scenario, line_item_key, "annual" if view in ("annual", "yearly") else "monthly")
