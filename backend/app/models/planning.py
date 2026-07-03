"""Pages 12-13 — Scenario assumptions and KPI targets."""
from __future__ import annotations

from datetime import date

from pydantic import Field

from .base import EntityBase
from .enums import ScenarioType


# --------------------------------------------------------------------------
# Page 12 — Scenario Assumptions
# --------------------------------------------------------------------------
class ScenarioAssumption(EntityBase):
    """Adjustment percentages applied on top of the base assumptions.

    All values are deltas in percent (e.g. -10 means "10% lower than base").
    """

    scenario_type: ScenarioType = ScenarioType.BASE
    # Named saved scenarios: `name` is the user-facing name; `label` is kept for
    # backward compatibility (older data + the ScenarioAdj label). Exactly one
    # scenario per project is the default (enforced by scenario_service).
    name: str = Field(default="", max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_default: bool = False
    label: str | None = Field(default=None, max_length=120)

    sales_volume_adjustment: float = 0
    selling_price_adjustment: float = 0
    direct_cost_adjustment: float = 0
    salary_adjustment: float = 0
    rent_adjustment: float = 0
    marketing_adjustment: float = 0
    customer_growth_adjustment: float = 0
    collection_days_adjustment: float = 0
    inventory_days_adjustment: float = 0
    interest_rate_adjustment: float = 0
    exchange_rate_adjustment: float = 0
    tax_rate_adjustment: float = 0
    inflation_adjustment: float = 0


# --------------------------------------------------------------------------
# Page 13 — KPIs & Business Targets
# --------------------------------------------------------------------------
class RevenueMilestone(EntityBase):
    label: str = Field(..., min_length=1, max_length=160)
    target_date: date | None = None
    target_amount: float = Field(default=0, ge=0)
    is_profit_milestone: bool = False


class KPIAssumption(EntityBase):
    target_gross_margin_percent: float | None = Field(default=None, ge=0, le=100)
    target_ebitda_margin_percent: float | None = Field(default=None, ge=-100, le=100)
    target_net_profit_margin_percent: float | None = Field(default=None, ge=-100, le=100)
    break_even_target_date: date | None = None
    min_monthly_revenue_target: float = Field(default=0, ge=0)
    min_cash_balance_target: float = Field(default=0, ge=0)
    cac_target: float = Field(default=0, ge=0, description="customer acquisition cost")
    ltv_target: float = Field(default=0, ge=0, description="lifetime value")
    payback_period_target_months: float | None = Field(default=None, ge=0)
    roi_target_percent: float | None = Field(default=None)
    dscr_target: float | None = Field(default=None, ge=0)
    current_ratio_target: float | None = Field(default=None, ge=0)
    milestones: list[RevenueMilestone] = Field(default_factory=list)
