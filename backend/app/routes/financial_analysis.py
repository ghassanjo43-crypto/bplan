"""Financial Analysis dashboard routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..schemas.financial_analysis import (
    FinancialAnalysisKPI,
    FinancialAnalysisResponse,
    FinancialAnalysisSection,
    ScenarioComparisonResponse,
)
from ..services import ProjectService
from ..services import financial_analysis_service as fas
from .deps import get_service, project_or_404

router = APIRouter(prefix="/projects/{project_id}/financial-analysis", tags=["financial-analysis"])

Scenario = Query("base")   # a scenario id or a legacy type; resolved server-side
View = Query("yearly", pattern="^(monthly|yearly|annual)$")
ChartSet = Query(None, pattern="^(overview|profitability|cost_profitability|revenue|cash|balance_sheet|working_capital|scenarios)$")


@router.get("", response_model=FinancialAnalysisResponse, response_model_exclude_none=True)
def financial_analysis(project_id: str, scenario: str = Scenario, view: str = View,
                       chart_set: str | None = ChartSet, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return fas.generate_financial_analysis(project, scenario, view, chart_set)


@router.get("/charts", response_model=list[FinancialAnalysisSection], response_model_exclude_none=True)
def financial_analysis_charts(project_id: str, scenario: str = Scenario, view: str = View,
                              chart_set: str | None = ChartSet, service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return fas.generate_financial_analysis(project, scenario, view, chart_set).sections


@router.get("/kpis", response_model=list[FinancialAnalysisKPI])
def financial_analysis_kpis(project_id: str, scenario: str = Scenario, view: str = View,
                            service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    return fas.build_kpis_only(project, scenario, view)


@router.get("/scenario-comparison", response_model=ScenarioComparisonResponse)
def scenario_comparison(project_id: str, view: str = View,
                        scenarios: str | None = Query(None, description="Comma-separated scenario ids (2–3)"),
                        service: ProjectService = Depends(get_service)):
    project = project_or_404(project_id, service)
    ids = [s.strip() for s in scenarios.split(",") if s.strip()] if scenarios else None
    return fas.build_scenario_comparison(project, ids, view)
