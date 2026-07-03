"""Revenue Stream wizard — monthly revenue computation for the four types.

Revenue is always *derived* from the stored inputs here (never persisted stale).
The four formulas:

  * Unit Sales      : revenue = units x unit_price
  * Billable Hours  : revenue = hours x hourly_rate
  * Recurring       : ending = beginning + new_signups - beginning*churn
                      revenue = active(ending) x recurring_charge + new_signups x upfront_fee
  * Revenue Only    : revenue entered directly

Each stream maps to an IFRS revenue line so it slots into the Income Statement.
"""
from __future__ import annotations

from ..models.enums import RevenueStreamType

# IFRS revenue line each wizard type contributes to (matches income_statement).
IFRS_LINE = {
    "unit_sales": "product_revenue",
    "billable_hours": "service_revenue",
    "recurring_charges": "subscription_revenue",
    "revenue_only": "other_revenue",
}


def _val(v) -> str:
    return v.value if hasattr(v, "value") else v


def _series(method, constant: float, monthly: list[float], n: int) -> list[float]:
    """A length-n monthly series: a constant repeated, or the explicit values
    (padded with 0 beyond what was provided)."""
    if _val(method) == "constant":
        return [float(constant or 0)] * n
    out = [float(x or 0) for x in (monthly or [])][:n]
    if len(out) < n:
        out += [0.0] * (n - len(out))
    return out


def compute_monthly(stream, n: int) -> list[float]:
    """Monthly revenue for a stream over ``n`` months."""
    if not getattr(stream, "active", True) or n <= 0:
        return [0.0] * max(n, 0)
    t = _val(stream.stream_type)

    if t in ("unit_sales", "billable_hours"):
        q = _series(stream.quantity_method, stream.quantity_constant, stream.quantity_monthly, n)
        p = _series(stream.price_method, stream.price_constant, stream.price_monthly, n)
        return [round(q[i] * p[i], 4) for i in range(n)]

    if t == "recurring_charges":
        signups = _series(stream.signups_method, stream.signups_constant, stream.signups_monthly, n)
        churn = (stream.churn_rate_percent or 0) / 100.0
        per_month = stream.recurring_charge or 0
        if _val(stream.billing_frequency) == "yearly":
            per_month = per_month / 12.0     # spread an annual charge across the year
        out = [0.0] * n
        beginning = float(stream.initial_customers or 0)
        for i in range(n):
            churned = beginning * churn
            ending = beginning + signups[i] - churned
            if ending < 0:
                ending = 0.0
            recurring = ending * per_month
            upfront = signups[i] * (stream.upfront_fee or 0)
            out[i] = round(recurring + upfront, 4)
            beginning = ending
        return out

    if t == "revenue_only":
        return _series(stream.revenue_method, stream.revenue_constant, stream.revenue_monthly, n)

    return [0.0] * n


def active_customers(stream, n: int) -> list[float]:
    """Month-by-month active customer count for a recurring-charges stream."""
    signups = _series(stream.signups_method, stream.signups_constant, stream.signups_monthly, n)
    churn = (stream.churn_rate_percent or 0) / 100.0
    out = [0.0] * n
    beginning = float(stream.initial_customers or 0)
    for i in range(n):
        ending = beginning + signups[i] - beginning * churn
        if ending < 0:
            ending = 0.0
        out[i] = round(ending, 4)
        beginning = ending
    return out


def driver_series(stream, n: int) -> tuple[list[float], list[float], list[float]]:
    """Return (quantity, unit_price, customers) monthly series for a stream.

    Used by direct-cost association so a cost linked to a revenue stream can be
    priced from the stream's forecast quantity (per-unit) or its customers
    (per-customer). ``revenue_only`` streams have no unit concept, so per-unit
    drivers are zero (percent-of-revenue still works off ``compute_monthly``).
    """
    if not getattr(stream, "active", True) or n <= 0:
        z = [0.0] * max(n, 0)
        return list(z), list(z), list(z)
    t = _val(stream.stream_type)
    if t in ("unit_sales", "billable_hours"):
        q = _series(stream.quantity_method, stream.quantity_constant, stream.quantity_monthly, n)
        p = _series(stream.price_method, stream.price_constant, stream.price_monthly, n)
        return q, p, list(q)
    if t == "recurring_charges":
        customers = active_customers(stream, n)
        charge = [float(stream.recurring_charge or 0)] * n
        return list(customers), charge, customers
    return [0.0] * n, [0.0] * n, [0.0] * n


def annual_totals(monthly: list[float], years: int) -> list[float]:
    return [round(sum(monthly[y * 12:(y + 1) * 12]), 2) for y in range(years)]


def build_forecast(project, view: str = "yearly") -> dict:
    """Per-stream + total revenue for the wizard's list/preview (monthly/annual)."""
    from . import projection_period_service as periods

    start, years, n = periods.build_projection_periods(project)
    currency = project.setup.currency if project.setup else "USD"
    view = "monthly" if view == "monthly" else "annual"

    def shape(monthly: list[float]) -> list[float]:
        return [round(v, 2) for v in monthly] if view == "monthly" else annual_totals(monthly, years)

    rows = []
    totals_len = n if view == "monthly" else years
    totals = [0.0] * totals_len
    for s in project.revenue_streams:
        monthly = compute_monthly(s, n)
        values = shape(monthly)
        for i, v in enumerate(values):
            totals[i] += v
        rows.append({
            "id": s.id, "name": s.name, "stream_type": _val(s.stream_type),
            "values": values, "total": round(sum(monthly), 2), "active": s.active,
        })
    labels = ([m.start_date.strftime("%b %Y") for m in periods.get_monthly_periods(project)]
              if view == "monthly" else [f"Year {y + 1}" for y in range(years)])
    return {
        "project_id": project.id, "currency": currency, "view": view,
        "periods": labels, "rows": rows,
        "totals_by_period": [round(x, 2) for x in totals],
        "grand_total": round(sum(r["total"] for r in rows), 2),
    }
