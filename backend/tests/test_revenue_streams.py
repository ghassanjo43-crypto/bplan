"""Revenue Stream wizard — the four forecast types, forecast totals, income
statement integration, and backward compatibility."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.revenue_stream import RevenueStream
from app.services import income_statement_service as isvc
from app.services import revenue_stream_service as rss
from app.services.demo_builder import build_demo_project


def _stream(**kw):
    return RevenueStream(**kw)


# -- 1. Unit Sales : revenue = units x unit_price --------------------------
def test_unit_sales_constant_and_varying():
    s = _stream(name="Widgets", stream_type="unit_sales", quantity_constant=100, price_constant=5)
    assert rss.compute_monthly(s, 4) == [500, 500, 500, 500]

    v = _stream(name="W", stream_type="unit_sales", quantity_method="varying",
                quantity_monthly=[10, 20, 30], price_constant=5)
    assert rss.compute_monthly(v, 4) == [50, 100, 150, 0]     # padded 0 beyond inputs


# -- 2. Billable Hours : revenue = hours x hourly_rate ---------------------
def test_billable_hours():
    s = _stream(name="Consult", stream_type="billable_hours", quantity_constant=10,
                price_method="varying", price_monthly=[100, 150])
    assert rss.compute_monthly(s, 3) == [1000, 1500, 0]


# -- 3. Recurring Charges : signups + churn + upfront ----------------------
def test_recurring_charges_signups_churn_upfront():
    s = _stream(name="SaaS", stream_type="recurring_charges", initial_customers=100,
                signups_constant=10, recurring_charge=20, churn_rate_percent=5, upfront_fee=50)
    out = rss.compute_monthly(s, 2)
    # m0: end = 100 + 10 - 100*0.05 = 105 -> 105*20 + 10*50 = 2600
    assert out[0] == 2600
    # m1: begin=105, end = 105 + 10 - 5.25 = 109.75 -> 109.75*20 + 500 = 2695
    assert out[1] == 2695


def test_recurring_yearly_billing_spreads():
    s = _stream(name="Annual", stream_type="recurring_charges", initial_customers=12,
                signups_constant=0, recurring_charge=1200, billing_frequency="yearly")
    # 12 customers * (1200/12) = 1200 per month
    assert rss.compute_monthly(s, 2) == [1200, 1200]


# -- 4. Revenue Only -------------------------------------------------------
def test_revenue_only():
    assert rss.compute_monthly(_stream(name="R", stream_type="revenue_only", revenue_constant=9000), 3) == [9000, 9000, 9000]
    v = _stream(name="R", stream_type="revenue_only", revenue_method="varying", revenue_monthly=[1, 2, 3])
    assert rss.compute_monthly(v, 3) == [1, 2, 3]


def test_inactive_stream_is_zero():
    s = _stream(name="Off", stream_type="unit_sales", quantity_constant=10, price_constant=5, active=False)
    assert rss.compute_monthly(s, 3) == [0, 0, 0]


# -- forecast totals (monthly + annual) ------------------------------------
def test_forecast_totals_monthly_and_annual():
    p = build_demo_project()
    p.revenue_streams = [
        _stream(name="A", stream_type="revenue_only", revenue_constant=1000),
        _stream(name="B", stream_type="unit_sales", quantity_constant=10, price_constant=100),  # 1000/mo
    ]
    monthly = rss.build_forecast(p, "monthly")
    assert monthly["totals_by_period"][0] == 2000        # 1000 + 1000
    annual = rss.build_forecast(p, "annual")
    assert annual["totals_by_period"][0] == 24000        # 2000 * 12
    assert annual["grand_total"] == 24000 * len(annual["periods"])


# -- income statement integration: streams take precedence over products ----
def _months(p):
    from app.services.income_statement_service import build_projection_periods
    return build_projection_periods(p)[2]


def test_income_statement_uses_streams_and_does_not_double_count():
    """When a project has revenue streams, revenue comes from the streams only —
    the legacy per-product revenue is not added on top (no double counting)."""
    p = build_demo_project()
    legacy = isvc.generate_income_statement(p, "base", "yearly").totals.total_revenue
    assert legacy > 0                                     # legacy product revenue

    p.revenue_streams.append(_stream(name="Extra", stream_type="revenue_only", revenue_constant=1000))
    after = isvc.generate_income_statement(p, "base", "yearly").totals.total_revenue
    n = _months(p)
    assert round(after) == 1000 * n                       # streams REPLACE products
    assert round(after) != round(legacy + 1000 * n)       # explicitly not additive


def test_streams_with_zero_products_show_revenue():
    """A project with revenue streams and NO products still reports revenue in
    the financial statements (the new primary workflow standing on its own)."""
    p = build_demo_project()
    p.products, p.revenue, p.direct_costs = [], [], []    # a pure revenue-streams project
    p.revenue_streams = [_stream(name="Direct", stream_type="revenue_only", revenue_constant=5000)]
    r = isvc.generate_income_statement(p, "base", "yearly")
    n = _months(p)
    assert r.totals.total_revenue > 0
    assert round(r.totals.total_revenue) == 5000 * n
    assert round(r.totals.total_revenue) == round(sum(rss.compute_monthly(p.revenue_streams[0], n)))


def test_legacy_products_only_still_load_export_and_report():
    """Old projects with only products/revenue (no streams) keep working: the
    income statement uses the legacy path and the project round-trips through
    (de)serialisation like the JSON export."""
    from app.models import BusinessPlanProject
    p = build_demo_project()
    assert p.revenue_streams == [] and len(p.products) > 0   # legacy shape
    r = isvc.generate_income_statement(p, "base", "yearly")
    assert r.totals.total_revenue > 0                        # legacy revenue intact
    # export/serialise + reload without loss (mirrors the /export-json round-trip)
    reloaded = BusinessPlanProject(**p.model_dump())
    assert len(reloaded.products) == len(p.products)
    assert isvc.generate_income_statement(reloaded, "base", "yearly").totals.total_revenue > 0


# -- edit flow: PUT updates in place (regression for "cannot edit streams") --
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/api/demo/load-aquapure")
        yield c


def test_edit_updates_stream_without_creating_a_duplicate(client):
    base = "/api/projects/demo_aquapure/revenue-streams"
    forecast_url = "/api/projects/demo_aquapure/revenue-streams-forecast?view=yearly"
    before = len(client.get(base).json())

    created = client.post(base, json={
        "name": "Editable", "stream_type": "revenue_only", "revenue_constant": 1000,
    })
    assert created.status_code == 201
    sid = created.json()["id"]
    assert len(client.get(base).json()) == before + 1

    # forecast picks the new stream up: 1000/mo -> 12000 in year one
    row = next(r for r in client.get(forecast_url).json()["rows"] if r["id"] == sid)
    assert row["values"][0] == 12000

    # Edit via PUT on the same id -> must update in place, not duplicate.
    upd = client.put(f"{base}/{sid}", json={
        **created.json(), "name": "Edited", "revenue_constant": 2000,
    })
    assert upd.status_code == 200
    streams = client.get(base).json()
    assert len(streams) == before + 1                       # no duplicate row
    assert sum(1 for s in streams if s["id"] == sid) == 1
    assert next(s for s in streams if s["id"] == sid)["name"] == "Edited"

    # forecast reflects the edited amount automatically: 2000/mo -> 24000
    row2 = next(r for r in client.get(forecast_url).json()["rows"] if r["id"] == sid)
    assert row2["values"][0] == 24000

    # delete confirmation lives in the UI; the API delete removes it cleanly.
    assert client.delete(f"{base}/{sid}").status_code in (200, 204)
    assert len(client.get(base).json()) == before
