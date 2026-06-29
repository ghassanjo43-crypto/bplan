"""Pages 2-4 — Products/Services, Revenue assumptions, Direct costs.

A RevenueAssumption references a ProductService via ``product_id``. Direct
costs are modelled as flexible ``DirectCostItem`` records that can be associated
with one, many, all, or no products/services.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator

from .base import EntityBase
from .enums import (
    CostAllocationMethod,
    CostBehavior,
    CostCalculationMethod,
    DirectCostCategory,
    PaymentTerms,
    RefundBasis,
    RevenueType,
)


# --------------------------------------------------------------------------
# Page 2 — Products & Services
# --------------------------------------------------------------------------
class ProductService(EntityBase):
    name: str = Field(..., min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    revenue_type: RevenueType
    selling_price: float = Field(..., ge=0)
    unit_of_sale: str | None = Field(default="unit", max_length=60)
    launch_date: date | None = None
    active: bool = True


# --------------------------------------------------------------------------
# Page 3 — Revenue Assumptions (one per product/service)
# --------------------------------------------------------------------------
class SeasonalityMonth(EntityBase):
    """Monthly multiplier (100 = neutral) used when seasonality is enabled."""

    month: int = Field(..., ge=1, le=12)
    adjustment_percent: float = Field(default=100.0, ge=0, le=400)


class RevenueAssumption(EntityBase):
    product_id: str = Field(..., description="FK -> ProductService.id")

    # Volume / growth
    starting_monthly_volume: float = Field(default=0, ge=0)
    annual_growth_rate: float = Field(default=0, description="percent, may be negative")
    monthly_growth_rate: float | None = Field(default=None, description="percent, optional")

    # Customer economics
    number_of_customers: float | None = Field(default=None, ge=0)
    customer_growth_rate: float | None = Field(default=None)
    average_order_value: float | None = Field(default=None, ge=0)
    purchase_frequency: float | None = Field(default=None, ge=0)
    repeat_purchase_rate: float | None = Field(default=None, ge=0, le=100)

    # Subscription
    subscription_price: float | None = Field(default=None, ge=0)
    churn_rate: float | None = Field(default=None, ge=0, le=100)

    # Contract / commission / licensing
    contract_value: float | None = Field(default=None, ge=0)
    number_of_contracts: float | None = Field(default=None, ge=0)
    commission_rate: float | None = Field(default=None, ge=0, le=100)
    licensing_fee: float | None = Field(default=None, ge=0)

    # Adjustments
    discount_percent: float = Field(default=0, ge=0, le=100)
    refund_percent: float = Field(default=0, ge=0, le=100)
    refund_basis: RefundBasis = RefundBasis.PERCENT_OF_REVENUE

    # Seasonality
    seasonality_enabled: bool = False
    seasonality: list[SeasonalityMonth] = Field(default_factory=list)

    # Collections
    payment_terms: PaymentTerms = PaymentTerms.CASH
    custom_payment_days: int | None = Field(default=None, ge=0, le=365)


# --------------------------------------------------------------------------
# Page 4 — Direct Costs / COGS (flexible item builder)
# --------------------------------------------------------------------------
class CostAllocation(BaseModel):
    """Manual allocation weight of a shared cost item to a product/service."""

    product_id: str
    percent: float = Field(default=0, ge=0, le=100)


class DirectCostItem(EntityBase):
    """A single, flexible direct-cost line item.

    Association model:
      * ``apply_to_all`` — the cost applies to every product/service.
      * ``product_ids``  — explicit list (one or many) when not applied to all.
      * neither set      — the item is *unassigned* (a draft to classify later).
    """

    name: str = Field(..., min_length=1, max_length=160)
    category: DirectCostCategory

    # Association
    apply_to_all: bool = False
    product_ids: list[str] = Field(default_factory=list)

    # Behaviour & method
    cost_behavior: CostBehavior = CostBehavior.VARIABLE
    calculation_method: CostCalculationMethod

    # Values (amount XOR percent depending on the method)
    amount: float = Field(default=0, ge=0)
    percent: float = Field(default=0, ge=0, le=100)

    # Allocation across multiple products/services
    allocation_method: CostAllocationMethod | None = None
    manual_allocations: list[CostAllocation] = Field(default_factory=list)

    # Supplier & economics
    supplier_name: str | None = Field(default=None, max_length=160)
    supplier_payment_terms: PaymentTerms = PaymentTerms.NET_30
    cost_inflation_rate: float = Field(default=0, description="percent per year")
    waste_defect_rate_percent: float = Field(default=0, ge=0, le=100)
    minimum_order_quantity: float | None = Field(default=None, ge=0)
    currency_override: str | None = Field(default=None, max_length=3)
    vat_applicable: bool = False

    # Lifecycle. ``start_date`` is optional: when a cost is linked to a
    # product/service and left blank, the projection follows that product's
    # launch date (see direct_cost_projection_service._cost_start). This keeps
    # the launch date a single source of truth instead of re-entering it here.
    start_date: date | None = None
    end_date: date | None = None
    active: bool = True

    # -- derived -----------------------------------------------------------
    @property
    def is_unassigned(self) -> bool:
        return not self.apply_to_all and len(self.product_ids) == 0

    @property
    def spans_multiple(self) -> bool:
        return self.apply_to_all or len(self.product_ids) > 1

    def applies_to(self, product_id: str) -> bool:
        return self.apply_to_all or product_id in self.product_ids

    # -- cross-field validation -------------------------------------------
    @model_validator(mode="after")
    def _validate(self) -> "DirectCostItem":
        if self.spans_multiple and self.allocation_method is None:
            raise ValueError(
                "allocation_method is required when a cost spans multiple "
                "products/services"
            )
        if self.allocation_method == CostAllocationMethod.MANUAL:
            total = sum(a.percent for a in self.manual_allocations)
            if abs(total - 100) > 0.01:
                raise ValueError(
                    f"manual allocation percentages must total 100% (got {total:g}%)"
                )
        return self
