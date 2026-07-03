"""Declarative registry of assumption sections.

A single source of truth that drives:
  * generic CRUD routers (collection vs singleton),
  * the completion / review engine,
  * the export ordering.

Adding a new section is a one-line change here plus a model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from pydantic import BaseModel

from ..models import (
    DirectCostItem,
    Financing,
    FixedAsset,
    KPIAssumption,
    OperatingExpense,
    ProductService,
    ProjectSetup,
    RevenueAssumption,
    RevenueStream,
    ScenarioAssumption,
    StaffRole,
    StartupCost,
    TaxAssumption,
    WorkingCapitalAssumption,
)


@dataclass(frozen=True)
class SectionSpec:
    key: str            # URL slug, e.g. "operating-expenses"
    attr: str           # attribute name on BusinessPlanProject
    label: str          # human-readable label
    model: Type[BaseModel]
    is_collection: bool
    required: bool = False
    # Fields that must be non-empty for a singleton section to count complete.
    required_fields: tuple[str, ...] = field(default_factory=tuple)


# Collection sections expose POST / PUT{item} / DELETE{item}
COLLECTION_SECTIONS: dict[str, SectionSpec] = {
    s.key: s
    for s in [
        # Products & Services is retired from the user-facing flow (Revenue
        # Assumptions is now the primary revenue workflow). The section, route,
        # model, and data are kept for backward compatibility, but it is no
        # longer required and is excluded from SECTION_ORDER so it does not
        # affect the completion % (a new project can reach 100% without it).
        SectionSpec("products", "products", "Products & Services", ProductService, True, required=False),
        SectionSpec("revenue", "revenue", "Revenue Assumptions", RevenueAssumption, True),
        # Auto-CRUD for the Add Revenue Stream wizard. Intentionally NOT added to
        # SECTION_ORDER so it does not affect completion % or export ordering.
        SectionSpec("revenue-streams", "revenue_streams", "Revenue Streams", RevenueStream, True),
        SectionSpec("direct-costs", "direct_costs", "Direct Costs / COGS", DirectCostItem, True),
        SectionSpec("staffing", "staffing", "Staffing Plan", StaffRole, True),
        SectionSpec("operating-expenses", "operating_expenses", "Operating Expenses", OperatingExpense, True),
        SectionSpec("startup-costs", "startup_costs", "Startup Costs", StartupCost, True),
        SectionSpec("fixed-assets", "fixed_assets", "Capital Expenditure", FixedAsset, True),
        SectionSpec("scenarios", "scenarios", "Scenario Assumptions", ScenarioAssumption, True),
    ]
}

# Singleton sections expose GET / PUT
SINGLETON_SECTIONS: dict[str, SectionSpec] = {
    s.key: s
    for s in [
        SectionSpec(
            "setup", "setup", "Project Setup", ProjectSetup, False,
            required=True,
            required_fields=("business_name", "project_name", "currency",
                             "projection_period", "projection_start_date"),
        ),
        SectionSpec("working-capital", "working_capital", "Working Capital", WorkingCapitalAssumption, False),
        SectionSpec("financing", "financing", "Financing", Financing, False),
        SectionSpec("tax", "tax", "Tax & Regulatory", TaxAssumption, False),
        SectionSpec("kpis", "kpis", "KPIs & Targets", KPIAssumption, False),
    ]
}

ALL_SECTIONS: dict[str, SectionSpec] = {**SINGLETON_SECTIONS, **COLLECTION_SECTIONS}

# Order used for completion %, review page, and JSON export.
# Note: "products" is intentionally omitted — it is hidden from the menu and no
# longer required, so it must not count toward completion (same rationale as
# "revenue-streams" above).
SECTION_ORDER: tuple[str, ...] = (
    "setup",
    "revenue",
    "direct-costs",
    "staffing",
    "operating-expenses",
    "startup-costs",
    "fixed-assets",
    "working-capital",
    "financing",
    "tax",
    "scenarios",
    "kpis",
)
