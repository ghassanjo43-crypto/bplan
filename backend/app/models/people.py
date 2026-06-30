"""Page 5 — Staffing Plan model."""
from __future__ import annotations

from datetime import date

from pydantic import Field

from .base import EntityBase
from .enums import Department


class StaffRole(EntityBase):
    department: Department = Department.OPERATIONS
    job_title: str = Field(..., min_length=1, max_length=160)
    number_of_employees: int = Field(default=1, ge=1)
    monthly_salary: float = Field(default=0, ge=0, description="per employee")
    hiring_start_date: date | None = None

    annual_increase_percent: float = Field(default=0, ge=0, le=100)
    benefits_percent: float = Field(default=0, ge=0, le=100)
    health_insurance_amount: float = Field(default=0, ge=0)
    visa_permit_cost: float = Field(default=0, ge=0)
    bonus_amount: float = Field(default=0, ge=0)
    bonus_percent: float = Field(default=0, ge=0, le=100)
    sales_commission_percent: float = Field(default=0, ge=0, le=100)
    # Optional role-specific override of the employer social-security rate.
    # When None, the projection uses the global Tax & Regulatory default
    # (``TaxAssumption.employer_social_security_rate``) — see the income
    # statement payroll build. This avoids asking for the same rate twice.
    employer_social_security_percent: float | None = Field(default=None, ge=0, le=100)
    gratuity_percent: float = Field(default=0, ge=0, le=100)

    active: bool = True

    @property
    def base_monthly_cost(self) -> float:
        return self.monthly_salary * self.number_of_employees
