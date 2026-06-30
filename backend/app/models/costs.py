"""Pages 6-8 — Operating Expenses, Startup Costs, Fixed Assets."""
from __future__ import annotations

from datetime import date

from pydantic import Field, model_validator

from .base import EntityBase
from .enums import (
    DepreciationMethod,
    ExpenseCategory,
    ExpenseFrequency,
    FinancingSource,
    FixedAssetCategory,
    RecognitionMethod,
    StartupCostCategory,
)


# --------------------------------------------------------------------------
# Page 6 — Operating Expenses
# --------------------------------------------------------------------------
class OperatingExpense(EntityBase):
    name: str = Field(..., min_length=1, max_length=160)
    category: ExpenseCategory = ExpenseCategory.OTHER
    amount: float = Field(default=0, ge=0)
    frequency: ExpenseFrequency = ExpenseFrequency.MONTHLY
    # Quarterly/annual amounts are SPREAD (smoothed) across the period by default,
    # which preserves legacy behaviour. LUMP recognises the whole amount in the
    # period's first month (cash timing). Ignored for monthly/one-time.
    recognition_method: RecognitionMethod = RecognitionMethod.SPREAD
    start_date: date | None = None
    end_date: date | None = None
    inflation_percent: float = Field(default=0, description="annual escalation %")
    vat_applicable: bool = False
    is_fixed: bool = True

    @property
    def monthly_equivalent(self) -> float:
        factor = {
            ExpenseFrequency.MONTHLY: 1.0,
            ExpenseFrequency.QUARTERLY: 1 / 3,
            ExpenseFrequency.YEARLY: 1 / 12,
            ExpenseFrequency.ONE_TIME: 0.0,
        }[self.frequency]
        return self.amount * factor


# --------------------------------------------------------------------------
# Page 7 — Startup Costs
# --------------------------------------------------------------------------
class StartupCost(EntityBase):
    name: str = Field(..., min_length=1, max_length=160)
    category: StartupCostCategory = StartupCostCategory.OTHER
    amount: float = Field(default=0, ge=0)
    payment_date: date
    capitalized: bool = Field(default=False, description="True=capitalised, False=expensed")


# --------------------------------------------------------------------------
# Page 8 — Capital Expenditure / Fixed Assets
# --------------------------------------------------------------------------
class FixedAsset(EntityBase):
    name: str = Field(..., min_length=1, max_length=160)
    category: FixedAssetCategory = FixedAssetCategory.EQUIPMENT
    description: str | None = Field(default=None, max_length=2000)
    purchase_amount: float = Field(default=0, ge=0)
    purchase_date: date | None = None
    ready_for_use_date: date | None = None
    useful_life_years: float = Field(default=5, ge=0)
    depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE
    residual_value: float = Field(default=0, ge=0)
    capitalized: bool = True
    replacement_cycle_years: float | None = Field(default=None, ge=0)
    maintenance_cost_percent: float = Field(default=0, ge=0, le=100)
    financing_source: FinancingSource = FinancingSource.CASH
    supplier_name: str | None = Field(default=None, max_length=160)
    vat_applicable: bool = False
    active: bool = True

    @property
    def depreciation_start(self) -> date | None:
        """Depreciation begins when the asset is ready for use (else purchase)."""
        return self.ready_for_use_date or self.purchase_date

    @property
    def annual_straight_line_depreciation(self) -> float:
        if (
            self.depreciation_method == DepreciationMethod.NONE
            or self.useful_life_years <= 0
        ):
            return 0.0
        return (self.purchase_amount - self.residual_value) / self.useful_life_years

    @model_validator(mode="after")
    def _validate(self) -> "FixedAsset":
        if self.residual_value > self.purchase_amount:
            raise ValueError("Residual value cannot exceed the purchase amount.")
        if self.depreciation_method != DepreciationMethod.NONE and self.useful_life_years <= 0:
            raise ValueError("Useful life must be greater than zero when the asset is depreciated.")
        return self
