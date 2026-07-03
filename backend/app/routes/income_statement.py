"""IFRS Statement of Profit or Loss routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..schemas.income_statement import (
    IncomeStatementReconciliation,
    IncomeStatementResponse,
    IncomeStatementSummary,
)
from ..services import income_statement_service as svc
from .deps import get_service, project_or_404
from ..services import ProjectService

router = APIRouter(prefix="/projects/{project_id}/income-statement", tags=["income-statement"])

Scenario = Query("base")   # a scenario id or a legacy type; resolved server-side
View = Query("yearly", pattern="^(monthly|yearly)$")


@router.get("", response_model=IncomeStatementResponse)
def income_statement(
    project_id: str,
    scenario: str = Scenario,
    view: str = View,
    start_period: int | None = Query(None, ge=0),
    end_period: int | None = Query(None, ge=0),
    service: ProjectService = Depends(get_service),
):
    project = project_or_404(project_id, service)
    return svc.generate_income_statement(project, scenario, view, start_period, end_period)


@router.get("/summary", response_model=IncomeStatementSummary)
def income_statement_summary(
    project_id: str,
    scenario: str = Scenario,
    service: ProjectService = Depends(get_service),
):
    project = project_or_404(project_id, service)
    return svc.build_summary(project, scenario)


@router.get("/reconciliation", response_model=IncomeStatementReconciliation)
def income_statement_reconciliation(
    project_id: str,
    scenario: str = Scenario,
    service: ProjectService = Depends(get_service),
):
    project = project_or_404(project_id, service)
    return svc.build_reconciliation(project, scenario)
