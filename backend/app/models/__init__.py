"""Pydantic domain models for the business plan projection app."""
from __future__ import annotations

from .base import EntityBase, TimestampedModel
from .enums import (
    BusinessModel,
    CostAllocationMethod,
    CostBehavior,
    CostCalculationMethod,
    DepreciationMethod,
    Department,
    DirectCostCategory,
    ExpenseCategory,
    ExpenseFrequency,
    FinancingSource,
    FixedAssetCategory,
    PaymentTerms,
    ProjectionFrequency,
    ProjectionPeriod,
    RefundBasis,
    ReportingStandard,
    RepaymentType,
    RevenueType,
    ScenarioType,
    StockPurchaseCycle,
    TaxFrequency,
)
from .identity import ProjectSetup
from .catalog import (
    CostAllocation,
    DirectCostItem,
    ProductService,
    RevenueAssumption,
    SeasonalityMonth,
)
from .revenue_stream import RevenueStream
from .people import StaffRole
from .costs import FixedAsset, OperatingExpense, StartupCost
from .capital import (
    EquityFunding,
    Financing,
    GrantFunding,
    LoanFunding,
    WorkingCapitalAssumption,
)
from .compliance import TaxAssumption
from .planning import KPIAssumption, RevenueMilestone, ScenarioAssumption
from .projection import DirectCostCell, OpexCell, ProjectionData, RevenueCell
from .text_plan import (
    TextPlanDocument,
    TextPlanImage,
    TextPlanSection,
    TextPlanTopic,
)
from .company import Company, CompanySummary
from .user import AuditLog, User
from .project import (
    BusinessPlanProject,
    CompletionReport,
    ProjectSummary,
    ReviewStatus,
    SectionStatus,
)

__all__ = [
    "EntityBase",
    "TimestampedModel",
    "BusinessModel",
    "CostAllocationMethod",
    "CostBehavior",
    "CostCalculationMethod",
    "DepreciationMethod",
    "Department",
    "DirectCostCategory",
    "ExpenseCategory",
    "ExpenseFrequency",
    "FinancingSource",
    "FixedAssetCategory",
    "PaymentTerms",
    "ProjectionFrequency",
    "ProjectionPeriod",
    "RefundBasis",
    "ReportingStandard",
    "RepaymentType",
    "RevenueType",
    "ScenarioType",
    "StockPurchaseCycle",
    "TaxFrequency",
    "ProjectSetup",
    "ProductService",
    "RevenueAssumption",
    "RevenueStream",
    "SeasonalityMonth",
    "CostAllocation",
    "DirectCostItem",
    "StaffRole",
    "OperatingExpense",
    "StartupCost",
    "FixedAsset",
    "WorkingCapitalAssumption",
    "EquityFunding",
    "LoanFunding",
    "GrantFunding",
    "Financing",
    "TaxAssumption",
    "ScenarioAssumption",
    "RevenueMilestone",
    "KPIAssumption",
    "BusinessPlanProject",
    "ProjectSummary",
    "ReviewStatus",
    "SectionStatus",
    "CompletionReport",
    "ProjectionData",
    "RevenueCell",
    "DirectCostCell",
    "OpexCell",
    "TextPlanDocument",
    "TextPlanSection",
    "TextPlanTopic",
    "TextPlanImage",
    "Company",
    "CompanySummary",
    "User",
    "AuditLog",
]
