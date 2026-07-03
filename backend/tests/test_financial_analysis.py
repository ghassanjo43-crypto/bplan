"""Tests for the Financial Analysis dashboard."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.demo_builder import build_demo_project
from app.services import financial_analysis_service as fas


@pytest.fixture(scope="module")
def project():
    return build_demo_project()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/api/demo/load-aquapure")
        yield c


def _section(resp, key):
    return next(s for s in resp.sections if s.key == key)


def _chart(section, key):
    return next(c for c in section.charts if c.key == key)


# 1 & 2. Routes return 200
def test_routes_200(client):
    assert client.get("/api/projects/demo_aquapure/financial-analysis?scenario=base&view=yearly").status_code == 200
    assert client.get("/api/projects/demo_aquapure/financial-analysis/kpis?scenario=base").status_code == 200


# 3. Executive overview present
def test_executive_overview(project):
    r = fas.generate_financial_analysis(project, "base", "yearly")
    assert _section(r, "overview")


# 4 & 5. Revenue trend + margin trend have data
def test_overview_charts_have_data(project):
    ov = _section(fas.generate_financial_analysis(project, "base", "yearly"), "overview")
    assert len(_chart(ov, "revenue_profit_trend").data) == 5
    assert len(_chart(ov, "margin_trend").data) == 5


# 6. Cash flow chart has data
def test_cash_charts(project):
    cash = _section(fas.generate_financial_analysis(project, "base", "yearly"), "cash")
    assert len(_chart(cash, "cash_flow_by_activity").data) == 5
    assert _chart(cash, "closing_cash_trend").data


# 7. Balance sheet chart has data
def test_balance_sheet_charts(project):
    bs = _section(fas.generate_financial_analysis(project, "base", "yearly"), "balance_sheet")
    assert _chart(bs, "assets_composition").data
    assert _chart(bs, "debt_vs_equity").data


# 8. Scenario comparison returns all three scenarios
def test_scenario_comparison(client):
    r = client.get("/api/projects/demo_aquapure/financial-analysis/scenario-comparison?view=yearly")
    assert r.status_code == 200
    d = r.json()
    keys = {m["key"] for m in d["metrics"]}
    assert {"revenue", "gross_profit", "gross_margin", "ebitda", "net_profit",
            "cash_balance", "break_even", "funding_requirement"} <= keys
    rev = next(m for m in d["metrics"] if m["key"] == "revenue")
    # Series are keyed by scenario id (not the legacy type string), 2–3 of them.
    assert 2 <= len(rev["series"]) <= 3


# 9. Does not crash with a near-empty project
def test_empty_project_does_not_crash():
    from app.models import BusinessPlanProject, ProjectSetup
    from app.models.enums import ProjectionPeriod
    from datetime import date
    p = BusinessPlanProject(name="Empty", setup=ProjectSetup(
        business_name="Empty Co", currency="USD", projection_start_date=date(2026, 1, 1),
        projection_period=ProjectionPeriod.THREE_YEARS))
    r = fas.generate_financial_analysis(p, "base", "yearly")
    assert len(r.periods) == 3
    assert r.sections


# 10. Negative values flagged
def test_negative_values_flagged(project):
    r = fas.generate_financial_analysis(project, "base", "yearly")
    codes = {w.code for w in r.warnings}
    assert "negative_cash" in codes  # demo is underfunded


# 11. Warnings generated
def test_warnings(project):
    r = fas.generate_financial_analysis(project, "base", "yearly")
    assert len(r.warnings) >= 1


# 12 & 13 & 14. Periods match view
def test_periods_match_view(project):
    assert len(fas.generate_financial_analysis(project, "base", "yearly").periods) == 5
    assert len(fas.generate_financial_analysis(project, "base", "monthly").periods) == 60


# KPIs cover the groups
def test_kpis_cover_groups(project):
    r = fas.generate_financial_analysis(project, "base", "yearly")
    groups = {k.group for k in r.kpis}
    assert {"profitability", "liquidity", "leverage", "efficiency", "cash"} <= groups


# Scenario revenue ordering (conservative < base < optimistic), by scenario id
def test_scenario_ordering(project):
    by_id = {s.id: s.scenario_type.value for s in project.scenarios}
    sc = fas.build_scenario_comparison(project, list(by_id), "yearly")
    rev = next(m for m in sc.metrics if m.key == "revenue")
    tot = {by_id[s.scenario]: sum(s.values) for s in rev.series}
    assert tot["conservative"] < tot["base"] < tot["optimistic"]
