"""Statement of Financial Position (Balance Sheet) routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..schemas.balance_sheet import (
    BalanceSheetReconciliation,
    BalanceSheetResponse,
    BalanceSheetSummary,
)
from ..services import ProjectService
from ..services import balance_sheet_service as bss
from .deps import get_service, project_or_404

router = APIRouter(prefix="/projects/{project_id}/balance-sheet", tags=["balance-sheet"])

Scenario = Query("base")   # a scenario id or a legacy type; resolved server-side
View = Query("yearly", pattern="^(monthly|yearly|annual)$")


@router.get("", response_model=BalanceSheetResponse, response_model_exclude_none=True)
def balance_sheet(
    project_id: str,
    scenario: str = Scenario,
    view: str = View,
    start_period: int | None = Query(None, ge=0),
    end_period: int | None = Query(None, ge=0),
    service: ProjectService = Depends(get_service),
):
    project = project_or_404(project_id, service)
    return bss.generate_balance_sheet(project, scenario, view, start_period, end_period)


@router.get("/summary", response_model=BalanceSheetSummary)
def balance_sheet_summary(project_id: str, scenario: str = Scenario, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return bss.build_summary(project, scenario)


@router.get("/reconciliation", response_model=BalanceSheetReconciliation)
def balance_sheet_reconciliation(project_id: str, scenario: str = Scenario, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return bss.build_reconciliation(project, scenario)


@router.get("/drilldown/{line_item_key}")
def balance_sheet_drilldown(
    project_id: str,
    line_item_key: str,
    scenario: str = Scenario,
    view: str = View,
    service: ProjectService = Depends(get_service),
):
    project = project_or_404(project_id, service)
    if line_item_key == "cash":
        return bss.cash_bridge_drilldown(project, scenario, "annual" if view in ("annual", "yearly") else "monthly")
    # Generic drilldown returns the line's values + note for now.
    stmt = bss.generate_balance_sheet(project, scenario, view)
    for row in stmt.rows:
        if row.key == line_item_key:
            return {"key": row.key, "label": row.label, "periods": [p.label for p in stmt.periods],
                    "values_by_period": row.values_by_period}
    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Line item {line_item_key!r} not found")
