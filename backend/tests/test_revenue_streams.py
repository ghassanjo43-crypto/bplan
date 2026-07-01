"""Revenue Stream wizard — the four forecast types, forecast totals, income
statement integration, and backward compatibility."""
from __future__ import annotations

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


# -- income statement integration (additive) -------------------------------
def test_income_statement_includes_streams():
    p = build_demo_project()
    base = isvc.generate_income_statement(p, "base", "yearly").totals.total_revenue
    p.revenue_streams.append(_stream(name="Extra", stream_type="revenue_only", revenue_constant=1000))
    after = isvc.generate_income_statement(p, "base", "yearly").totals.total_revenue
    assert round(after - base) == 60000                  # 1000/mo * 60 months


def test_legacy_project_unaffected():
    p = build_demo_project()
    assert p.revenue_streams == []                        # default empty
    # a project with no streams produces the same revenue as before this feature
    r = isvc.generate_income_statement(p, "base", "yearly")
    assert r.totals.total_revenue > 0
