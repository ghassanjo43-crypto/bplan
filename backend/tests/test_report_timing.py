"""Phase 4 — report/export data includes timing assumptions."""
from __future__ import annotations

from datetime import date

from app.models.catalog import DirectCostItem, ProductService, RevenueAssumption
from app.models.costs import OperatingExpense
from app.models.enums import (
    CostAllocationMethod, CostCalculationMethod, DirectCostCategory, ExpenseCategory,
    ExpenseFrequency, PaymentTerms, RecognitionMethod, RevenueTiming, RevenueType, SellingUnit,
)
from app.services import report_data_service as rd
from app.services.demo_builder import build_demo_project


class _Opts:
    include_charts = False
    include_assumptions = True
    include_text_plan = False
    report_style = "investor"


def _product(**kw):
    kw.setdefault("id", "p1")
    kw.setdefault("name", "Prod")
    kw.setdefault("revenue_type", RevenueType.UNIT_SALES)
    kw.setdefault("selling_price", 10)
    return ProductService(**kw)


# -- revenue timing rows ----------------------------------------------------
def test_revenue_timing_row_labels():
    p = _product(name="Sand", selling_price=2, selling_unit=SellingUnit.KG, launch_date=date(2026, 1, 1))
    row = rd._revenue_timing_row(p, RevenueAssumption(product_id="p1", starting_monthly_volume=100,
                                                      payment_terms=PaymentTerms.NET_30))
    assert row["timing"] == "Continuous monthly"
    assert row["unit"] == "Kg"
    assert row["recognition"] == "–"                 # only annual/contract show recognition
    assert "30 days" in row["payment_terms"]

    annual = rd._revenue_timing_row(p, RevenueAssumption(
        product_id="p1", revenue_timing=RevenueTiming.ANNUAL_RECURRING,
        recognition_method=RecognitionMethod.LUMP))
    assert annual["timing"] == "Annual recurring"
    assert annual["recognition"] == "Lump / cash timing"

    contract = rd._revenue_timing_row(p, RevenueAssumption(
        product_id="p1", starting_monthly_volume=10, revenue_timing=RevenueTiming.CONTRACT_PERIOD,
        contract_duration_months=6))
    assert contract["timing"].startswith("Contract")
    assert contract["duration"] == "6"


def test_one_time_labelled_revenue_date():
    p = _product(launch_date=date(2026, 1, 1))
    one_time = rd._revenue_timing_row(p, RevenueAssumption(
        product_id="p1", revenue_timing=RevenueTiming.ONE_TIME, starting_monthly_volume=100))
    assert one_time["timing"] == "One-time"
    assert one_time["start_label"] == "Revenue Date"     # not "Start Date"
    assert one_time["end"] == "–"                          # no end for one-time

    recurring = rd._revenue_timing_row(p, RevenueAssumption(
        product_id="p1", revenue_timing=RevenueTiming.MONTHLY_RECURRING))
    assert recurring["start_label"] == "Start Date"

    # legacy / continuous default also uses "Start Date"
    assert rd._revenue_timing_row(p, None)["start_label"] == "Start Date"


def test_revenue_timing_legacy_defaults():
    p = _product(launch_date=date(2026, 1, 1))
    row = rd._revenue_timing_row(p, None)            # legacy stream with no assumption
    assert row["timing"] == "Continuous monthly"
    assert row["recognition"] == "–"
    assert row["start"] == "01 Jan 2026"             # falls back to launch date


# -- operating expense rows -------------------------------------------------
def test_opex_detail_labels():
    monthly = rd._opex_detail_row(OperatingExpense(name="Rent", category=ExpenseCategory.RENT,
                                                   amount=1000, frequency=ExpenseFrequency.MONTHLY))
    assert monthly["timing"] == "Monthly recurring"
    assert monthly["recognition"] == "–"

    annual = rd._opex_detail_row(OperatingExpense(name="Ins", category=ExpenseCategory.INSURANCE,
                                                  amount=12000, frequency=ExpenseFrequency.YEARLY,
                                                  recognition_method=RecognitionMethod.LUMP))
    assert annual["timing"] == "Annual"
    assert annual["recognition"] == "Lump / cash timing"


# -- direct cost rows -------------------------------------------------------
def test_direct_cost_detail_linked_vs_independent():
    p = _product()
    linked = rd._direct_cost_detail_row(DirectCostItem(
        name="Steel", category=DirectCostCategory.RAW_MATERIALS, product_ids=["p1"],
        calculation_method=CostCalculationMethod.FIXED_PER_UNIT, amount=5,
        supplier_payment_terms=PaymentTerms.NET_45), [p])
    assert linked["method"] == "Cost per selling unit"
    assert linked["linked"] == "Linked"
    assert linked["association"] == "Prod"
    assert "45 days" in linked["supplier_terms"]

    indep = rd._direct_cost_detail_row(DirectCostItem(
        name="Misc", category=DirectCostCategory.OTHER,
        calculation_method=CostCalculationMethod.MONTHLY_ALLOCATED, amount=100), [p])
    assert indep["linked"] == "Independent"
    assert indep["association"] == "Independent / unassigned"

    pct = rd._direct_cost_detail_row(DirectCostItem(
        name="Gateway", category=DirectCostCategory.PAYMENT_GATEWAY, apply_to_all=True,
        allocation_method=CostAllocationMethod.REVENUE_SHARE,
        calculation_method=CostCalculationMethod.PERCENT_OF_REVENUE, percent=2.5), [p])
    assert pct["method"] == "Percentage of revenue"
    assert "%" in pct["value"]
    assert pct["association"] == "All products"


# -- end to end: context carries the tables (Word/PDF/Excel inherit these) --
def test_context_includes_timing_tables():
    ctx = rd.build_report_context(build_demo_project(), "base", "yearly", _Opts())
    for key in ("revenue_timing", "operating_expenses_detail", "direct_costs_detail", "timing_notes"):
        assert key in ctx and ctx[key], f"missing/empty {key}"
    assert len(ctx["timing_notes"]) == 3
    assert all("timing" in r and "recognition" in r for r in ctx["revenue_timing"])
    assert all("method" in r and "linked" in r for r in ctx["direct_costs_detail"])
    assert all("timing" in r for r in ctx["operating_expenses_detail"])
