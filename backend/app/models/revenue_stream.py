"""Revenue Stream wizard model (LivePlan-inspired but original).

One RevenueStream captures the forecast inputs for a single stream in one of
four styles. The monthly revenue is *computed* from these inputs by
``revenue_stream_service`` (the calculated series is derived, never stored
stale) and flows into the Income Statement additively — a project with no
revenue streams behaves exactly as before.
"""
from __future__ import annotations

from pydantic import Field

from .base import EntityBase
from .enums import BillingFrequency, ForecastInputMethod, RevenueStreamType


class RevenueStream(EntityBase):
    name: str = Field(..., min_length=1, max_length=200)
    stream_type: RevenueStreamType
    active: bool = True

    # -- Unit Sales (units) / Billable Hours (hours): the "quantity" driver ---
    quantity_method: ForecastInputMethod = ForecastInputMethod.CONSTANT
    quantity_constant: float = Field(default=0, ge=0)
    quantity_monthly: list[float] = Field(default_factory=list)   # per-month, when varying

    # -- Unit price / hourly rate --------------------------------------------
    price_method: ForecastInputMethod = ForecastInputMethod.CONSTANT
    price_constant: float = Field(default=0, ge=0)
    price_monthly: list[float] = Field(default_factory=list)

    # -- Recurring Charges ---------------------------------------------------
    initial_customers: float = Field(default=0, ge=0)
    signups_method: ForecastInputMethod = ForecastInputMethod.CONSTANT
    signups_constant: float = Field(default=0, ge=0)
    signups_monthly: list[float] = Field(default_factory=list)    # new customers per month
    recurring_charge: float = Field(default=0, ge=0)
    billing_frequency: BillingFrequency = BillingFrequency.MONTHLY
    upfront_fee: float = Field(default=0, ge=0)
    churn_rate_percent: float = Field(default=0, ge=0, le=100)    # monthly churn %

    # -- Revenue Only --------------------------------------------------------
    revenue_method: ForecastInputMethod = ForecastInputMethod.CONSTANT
    revenue_constant: float = Field(default=0, ge=0)
    revenue_monthly: list[float] = Field(default_factory=list)
