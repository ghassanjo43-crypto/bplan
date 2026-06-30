"""Collects and formats all data needed for the business plan report.

This module never recomputes financials — it calls the statement/analysis
services and shapes their results into a single ``context`` dict consumed by the
Word and PDF generators.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

from ..models import BusinessPlanProject
from . import balance_sheet_service as bss
from . import cash_flow_service as cfs
from . import financial_analysis_service as fas
from . import fixed_asset_service as fasset
from . import income_statement_service as isvc
from .completion import build_completion_report

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "generated_reports"

PREPARED_FOR = {
    "investor": "Prospective Investors",
    "bank": "Financing Bank / Lender",
    "board": "Board of Directors",
    "management": "Internal Management",
    "full": "Investors, Lenders and Management",
}
SCENARIO_LABELS = {"base": "Base Case", "conservative": "Conservative Case", "optimistic": "Optimistic Case"}

SECTIONS = [
    ("executive_summary", "Executive Summary"),
    ("business_overview", "Business Overview"),
    ("products_revenue", "Products and Revenue Model"),
    ("assumptions", "Projection Assumptions"),
    ("operating_model", "Operating Model"),
    ("capex", "Capital Expenditure and Assets"),
    ("working_capital_financing", "Working Capital and Financing"),
    ("statements", "Financial Statements"),
    ("analysis", "Financial Analysis"),
    ("scenarios", "Scenario Comparison"),
    ("risks", "Risks, Warnings and Reconciliations"),
    ("appendices", "Appendices"),
]


# --------------------------------------------------------------------------
# formatting helpers (shared by Word + PDF generators)
# --------------------------------------------------------------------------
def fmt_num(v, decimals=0):
    if v is None:
        return "–"
    r = round(float(v), decimals)
    if r == 0:
        return "–"
    body = f"{abs(r):,.{decimals}f}"
    return f"({body})" if r < 0 else body


def fmt_pct(v):
    if v is None:
        return "–"
    r = round(float(v), 1)
    return f"({abs(r):.1f}%)" if r < 0 else f"{r:.1f}%"


def fmt_ratio(v):
    if v is None:
        return "–"
    return f"({abs(v):.2f}x)" if v < 0 else f"{v:.2f}x"


def fmt_date(d):
    if not d:
        return "–"
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d[:10])
        except Exception:
            return d
    return d.strftime("%d %b %Y")


def _lbl(v):
    return str(v).replace("_", " ").title() if v else "–"


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return name[:60] or "report"


# --------------------------------------------------------------------------
# storage / index
# --------------------------------------------------------------------------
def _project_dir(project_id: str) -> Path:
    p = REPORTS_DIR / sanitize_filename(project_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _index_path(project_id: str) -> Path:
    return _project_dir(project_id) / "_index.json"


def load_index(project_id: str) -> list[dict]:
    path = _index_path(project_id)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_index(project_id: str, entries: list[dict]) -> None:
    _index_path(project_id).write_text(json.dumps(entries, indent=2, default=str), encoding="utf-8")


def add_index_entry(project_id: str, entry: dict) -> None:
    entries = load_index(project_id)
    entries = [e for e in entries if e.get("report_id") != entry["report_id"]]
    entries.insert(0, entry)
    save_index(project_id, entries)


def delete_report(project_id: str, report_id: str) -> bool:
    entries = load_index(project_id)
    entry = next((e for e in entries if e.get("report_id") == report_id), None)
    if not entry:
        return False
    f = _project_dir(project_id) / entry["file_name"]
    if f.exists():
        f.unlink()
    save_index(project_id, [e for e in entries if e.get("report_id") != report_id])
    return True


def report_path(project_id: str, file_name: str) -> Path:
    return _project_dir(project_id) / file_name


# --------------------------------------------------------------------------
# statement flattening
# --------------------------------------------------------------------------
def _flatten_income(inc):
    rows = []
    for s in inc.sections:
        if s.line_items:
            rows.append({"label": s.title, "values": [], "kind": "section"})
        for li in s.line_items:
            rows.append({"label": li.label, "values": li.values_by_period, "kind": "line"})
        if s.subtotal:
            kind = "grand" if s.subtotal.is_grand_total else "subtotal"
            rows.append({"label": s.subtotal.label, "values": s.subtotal.values_by_period, "kind": kind})
    return rows


def _flatten_bs(bs):
    rows = []
    for r in bs.rows:
        kind = ("section" if r.is_header else "group" if (r.level == 0 and not r.is_header)
                else "grand" if r.is_grand_total else "subtotal" if r.is_subtotal
                else "check" if r.is_balance_check else "line")
        rows.append({"label": r.label, "values": r.values_by_period, "kind": kind})
    return rows


def _flatten_cf(cf):
    rows = []
    for r in cf.rows:
        kind = ("section" if r.is_section_header else "group" if (r.level == 0 and not r.is_section_header)
                else "grand" if r.is_grand_total else "subtotal" if r.is_subtotal else "line")
        rows.append({"label": r.label, "values": r.values_by_period, "kind": kind})
    return rows


def _cat_table(section, currency):
    """Build a category table {rows:[{label, values, total}], total_row} from an inc section."""
    rows = []
    for li in (section.line_items if section else []):
        rows.append({"label": li.label, "values": li.values_by_period, "total": sum(li.values_by_period)})
    return rows


# --------------------------------------------------------------------------
# warnings
# --------------------------------------------------------------------------
def collect_warnings_and_reconciliations(project, scenario, view):
    inc = isvc.generate_income_statement(project, scenario, view)
    bs = bss.generate_balance_sheet(project, scenario, view)
    cf = cfs.generate_cash_flow_statement(project, scenario, view)
    fa = fas.generate_financial_analysis(project, scenario, view)
    seen, out = set(), []

    def add(code, sev, msg):
        if msg in seen:
            return
        seen.add(msg)
        out.append({"code": code, "severity": sev, "message": msg})

    for w in inc.warnings:
        add(w.code, w.severity, w.message)
    for w in bs.warnings:
        add(w.code, w.severity, w.message)
    for w in cf.warnings:
        add(w.code, w.severity, w.message)
    for w in fa.warnings:
        add(w.code, w.severity, w.message)
    if bs.balance_check.status != "balanced":
        add("out_of_balance", "critical", f"Balance sheet is out of balance by {bs.balance_check.max_difference:,.0f}.")
    if cf.cash_reconciliation.status != "reconciled":
        add("cash_recon", "critical", "Cash flow does not reconcile to the balance sheet.")
    reconciliations = [
        {"label": "Balance sheet balances (Assets = Equity + Liabilities)", "status": bs.balance_check.status == "balanced"},
        {"label": "Cash flow reconciles to balance sheet cash", "status": cf.cash_reconciliation.status == "reconciled"},
    ]
    return out, reconciliations


# --------------------------------------------------------------------------
# main context
# --------------------------------------------------------------------------
def build_report_context(project: BusinessPlanProject, scenario: str, view: str, options) -> dict:
    vv = "monthly" if view == "monthly" else "yearly"
    setup = project.setup
    currency = setup.currency if setup else "USD"
    start_year = setup.projection_start_date.year if setup and setup.projection_start_date else date.today().year
    years = setup.projection_period.years if setup and setup.projection_period else 5
    end_year = start_year + years - 1

    inc = isvc.generate_income_statement(project, scenario, vv)
    bs = bss.generate_balance_sheet(project, scenario, vv)
    cf = cfs.generate_cash_flow_statement(project, scenario, vv)
    fa = fas.generate_financial_analysis(project, scenario, vv)
    scomp = fas.build_scenario_comparison(project, vv)
    inc_sections = {s.key: s for s in inc.sections}

    periods = [p.label for p in inc.periods]

    def sub(key):
        s = inc_sections.get(key)
        return s.subtotal.values_by_period if s and s.subtotal else [0] * len(periods)

    revenue = sub("revenue")
    closing_cash = cf.totals.closing_cash
    borrowings = next((r.values_by_period for r in bs.rows if r.key == "lt_borrowings"), [0] * len(periods))
    cpltd = next((r.values_by_period for r in bs.rows if r.key == "cpltd"), [0] * len(periods))
    total_borrow = [borrowings[i] + cpltd[i] for i in range(len(periods))]

    highlights = [
        {"label": "Total projected revenue", "value": fmt_num(inc.totals.total_revenue)},
        {"label": f"Year {years} revenue", "value": fmt_num(revenue[-1] if revenue else 0)},
        {"label": "Gross margin", "value": fmt_pct(inc.margins.gross_margin_total_pct)},
        {"label": "EBITDA margin", "value": fmt_pct(inc.margins.ebitda_margin_total_pct)},
        {"label": "Net profit margin", "value": fmt_pct(inc.margins.net_margin_total_pct)},
        {"label": "Closing cash (final year)", "value": fmt_num(closing_cash[-1] if closing_cash else 0)},
        {"label": "Total assets (final year)", "value": fmt_num(bs.totals.total_assets[-1] if bs.totals.total_assets else 0)},
        {"label": "Total borrowings (final year)", "value": fmt_num(total_borrow[-1] if total_borrow else 0)},
        {"label": "Total equity (final year)", "value": fmt_num(bs.totals.total_equity[-1] if bs.totals.total_equity else 0)},
        {"label": "Break-even target", "value": fmt_date(project.kpis.break_even_target_date) if project.kpis else "–"},
    ]

    # staffing per department from income statement drilldown
    staff_line = next((li for li in (inc_sections.get("operating_expenses").line_items if inc_sections.get("operating_expenses") else []) if li.key == "staff_costs"), None)
    staff_by_dept = []
    if staff_line:
        for dept in staff_line.children:
            staff_by_dept.append({"label": dept.label, "values": dept.values_by_period, "total": sum(dept.values_by_period)})

    # fixed assets + depreciation schedule
    dep_sched = fasset.generate_depreciation_schedule(project, "annual")
    nbv_by_asset = {a.asset_id: a.closing_net_book_value for a in dep_sched.assets}
    asset_summary = fasset.build_summary(project)

    warnings, reconciliations = collect_warnings_and_reconciliations(project, scenario, vv)

    # scenario comparison single-value table
    def scen_value(metric):
        balance_keys = {"closing_cash", "total_assets", "borrowings", "equity"}
        out = {}
        for s in metric.series:
            v = s.values[-1] if metric.key in balance_keys or metric.format == "percent" else sum(s.values)
            out[s.scenario] = v
        return out

    scenario_rows = [{"label": m.label, "format": m.format, "values": scen_value(m)} for m in scomp.metrics]

    # chart data tables for the analysis section
    chart_tables = []
    if options.include_charts:
        wanted = {"revenue_profit_trend", "margin_trend", "cash_flow_by_activity", "closing_cash_trend",
                  "assets_composition", "debt_vs_equity"}
        for sec in fa.sections:
            for ch in sec.charts:
                if ch.key in wanted and ch.chart_type not in ("donut", "pie", "waterfall"):
                    chart_tables.append({
                        "title": ch.title, "unit": ch.unit,
                        "columns": [s.label for s in ch.series],
                        "series_keys": [s.key for s in ch.series],
                        "rows": ch.data,
                    })

    # all charts (grouped by analysis section) for image rendering in the report
    chart_sections = []
    if options.include_charts:
        for sec in fa.sections:
            if sec.charts:
                chart_sections.append({"key": sec.key, "title": sec.title,
                                       "description": sec.description, "charts": list(sec.charts)})

    ctx = dict(
        currency=currency, scenario=scenario, scenario_label=SCENARIO_LABELS.get(scenario, scenario.title()),
        view=vv, periods=periods, app_name="Business Plan Studio",
        meta=dict(
            # Company (legal/reporting entity) comes from the parent Company
            # record; project (study title) from the project's own setup.
            company=_company_name(project, setup),
            project_name=(setup.project_name if setup else ""),
            title="Business Plan Financial Projection Report",
            subtitle=f"{_words(years)}-Year Projected Financial Study",
            period_range=f"{start_year}–{end_year}", currency=currency,
            scenario_label=SCENARIO_LABELS.get(scenario, scenario.title()),
            prepared_date=date.today().strftime("%d %B %Y"),
            prepared_for=PREPARED_FOR.get(options.report_style, "Investors"),
            report_style=_lbl(options.report_style),
        ),
        options=options,
        highlights=highlights,
        overview=_overview(project, setup),
        products=[_product_row(p) for p in project.products],
        revenue_table=_cat_table(inc_sections.get("revenue"), currency),
        direct_cost_table=_cat_table(inc_sections.get("cost_of_sales"), currency),
        opex_table=_cat_table(inc_sections.get("operating_expenses"), currency),
        # Phase 4 — timing / recurrence assumption tables (shared by Word/PDF/Excel)
        revenue_timing=[
            _revenue_timing_row(p, next((r for r in project.revenue if r.product_id == p.id), None))
            for p in project.products
        ],
        operating_expenses_detail=[_opex_detail_row(e) for e in project.operating_expenses],
        direct_costs_detail=[_direct_cost_detail_row(c, project.products) for c in project.direct_costs],
        timing_notes=TIMING_NOTES,
        staff_by_dept=staff_by_dept,
        staffing=[_staff_row(s) for s in project.staffing],
        fixed_assets=[_asset_row(a, nbv_by_asset.get(a.id, 0)) for a in project.fixed_assets],
        asset_summary=asset_summary,
        working_capital=_wc(project.working_capital),
        financing=_financing(project.financing),
        tax=_tax(project.tax),
        scenarios=[_scenario_row(s) for s in project.scenarios],
        kpis=_kpis(project.kpis),
        income_statement=dict(rows=_flatten_income(inc), periods=periods),
        balance_sheet=dict(rows=_flatten_bs(bs), periods=periods),
        cash_flow=dict(rows=_flatten_cf(cf), periods=periods),
        chart_tables=chart_tables,
        chart_sections=chart_sections,
        scenario_metrics=list(scomp.metrics),
        scenario_periods=list(scomp.periods),
        scenario_comparison=dict(periods=scomp.periods, rows=scenario_rows),
        warnings=warnings, reconciliations=reconciliations,
        fa_kpis=[{"label": k.label, "value": _kpi_fmt(k), "group": k.group} for k in fa.kpis],
        insights=fa.insights,
        text_plan=collect_text_plan(project, options),
    )
    return ctx


def collect_text_plan(project, options) -> dict:
    """Collect the written business plan for the report (filtered by options).

    Images are inline rich-text nodes inside each topic's ``content_html`` — the
    single source of truth for placement. We build an ``image_index`` (imageId ->
    file metadata) so the Word/PDF generators can embed each image at its node
    position. ``include_text_plan_images=False`` strips the image nodes instead.
    """
    if not getattr(options, "include_text_plan", True):
        return {"sections": [], "has_content": False, "image_index": {}}

    from . import text_plan_image_service as imgsvc
    from . import text_plan_service as tps

    inc_completed = getattr(options, "text_plan_include_completed", True)
    inc_drafts = getattr(options, "text_plan_include_drafts", True)
    inc_images = getattr(options, "text_plan_include_images", True)
    inc_guidance = getattr(options, "text_plan_include_guidance", False)

    # Migrate legacy attached images into content in-memory (idempotent, not persisted).
    tps.migrate_document(project.id, project.text_plan)
    image_index = imgsvc.build_image_index(project) if inc_images else {}

    def topic_allowed(t):
        if not t.include_in_report:
            return False
        if t.status == "completed":
            return inc_completed
        if t.status in ("draft", "in_review"):
            return inc_drafts
        return inc_drafts and bool(t.plain_text.strip())

    def strip_images(html: str) -> str:
        return re.sub(r"<img\b[^>]*>", "", html or "")

    sections = []
    for s in project.text_plan.sections:
        if not s.include_in_report:
            continue
        topics = []
        for t in sorted(s.topics, key=lambda x: x.order_index):
            if not topic_allowed(t):
                continue
            content_html = t.content_html or ""
            if not inc_images:
                content_html = strip_images(content_html)
            topics.append({
                "title": t.title, "content_html": content_html, "plain_text": t.plain_text,
                "status": t.status, "guidance": t.guidance_text if inc_guidance else "",
            })
        if topics:
            sections.append({
                "title": s.title, "subtitle": s.subtitle, "description": s.description,
                "page_break_before": s.page_break_before, "topics": topics,
            })
    return {"sections": sections, "has_content": bool(sections), "image_index": image_index,
            "title": project.text_plan.title or "Business Plan"}


def _company_name(project, setup):
    """Reporting entity name: parent Company record, else setup, else plan name."""
    try:
        from .companies import company_service
        name = company_service().company_name_for_project(project)
        if name:
            return name
    except Exception:
        pass
    if setup and setup.business_name:
        return setup.business_name
    return project.name


def _words(n):
    return {3: "Three", 5: "Five", 10: "Ten"}.get(n, str(n))


def _kpi_fmt(k):
    if k.value is None:
        return "–"
    if k.format == "percent":
        return fmt_pct(k.value)
    if k.format == "ratio":
        return fmt_ratio(k.value)
    if k.format == "number":
        return fmt_num(k.value)
    return fmt_num(k.value)


def _overview(project, setup):
    if not setup:
        return {}
    return {
        "Business name": setup.business_name,
        "Project": setup.project_name or "–",
        "Country / City": ", ".join(filter(None, [setup.city, setup.country])) or "–",
        "Industry": setup.industry or "–",
        "Business model": _lbl(setup.business_model.value) if setup.business_model else "–",
        "Tax jurisdiction": setup.tax_jurisdiction or "–",
        "Reporting standard": _lbl(setup.reporting_standard.value),
        "Projection start": fmt_date(setup.projection_start_date),
        "Projection period": _lbl(setup.projection_period.value),
        "Projection frequency": _lbl(setup.projection_frequency.value),
        "Description": setup.business_description or "–",
    }


# --------------------------------------------------------------------------
# Timing / recurrence presentation (Phase 4 — reports & exports)
# --------------------------------------------------------------------------
REVENUE_TIMING_LABELS = {
    "continuous": "Continuous monthly", "one_time": "One-time", "monthly_recurring": "Monthly recurring",
    "annual_recurring": "Annual recurring / yearly renewal", "contract_period": "Contract / project over fixed period",
    "seasonal": "Seasonal", "custom": "Custom month-by-month schedule",
}
EXPENSE_TIMING_LABELS = {
    "monthly": "Monthly recurring", "quarterly": "Quarterly", "yearly": "Annual", "one_time": "One-time",
}
RECOGNITION_LABELS = {"spread": "Spread / smoothed", "lump": "Lump / cash timing"}
COST_METHOD_LABELS = {
    "fixed_per_unit": "Cost per selling unit", "percent_of_revenue": "Percentage of revenue",
    "percent_of_selling_price": "Percentage of selling price", "per_customer": "Amount per customer",
    "per_order": "Amount per order", "per_contract": "Fixed amount per contract",
    "per_service_delivery": "Amount per service delivery", "percent_of_purchase_cost": "Percentage of purchased goods cost",
    "monthly_allocated": "Fixed direct cost per month", "annual_allocated": "Annual allocated direct cost",
    "one_time": "One-time direct cost", "manual_by_period": "Manual by period",
}
_PAYMENT_TERMS_DAYS = {"cash": 0, "net_15": 15, "net_30": 30, "net_45": 45, "net_60": 60, "net_90": 90}

TIMING_NOTES = [
    "Revenue projections are driven by timing assumptions including one-time, recurring, "
    "contract-period, seasonal, or custom schedules.",
    "Operating expenses may be smoothed (spread) or lumped depending on the recognition method.",
    "Direct costs may be linked to product quantities/revenue or treated as independent/unassigned.",
]


def _enum_val(v, default=""):
    if v is None:
        return default
    return v.value if hasattr(v, "value") else v


def _payment_terms_label(terms_value, custom_days=None):
    if terms_value == "custom":
        return f"Custom ({custom_days} days)" if custom_days is not None else "Custom"
    days = _PAYMENT_TERMS_DAYS.get(terms_value)
    base = _lbl(terms_value)
    return f"{base} ({days} days)" if days is not None else base


def _product_row(p):
    return {"name": p.name, "category": p.category or "–", "revenue_type": _lbl(p.revenue_type.value),
            "unit": p.unit_label or "–", "price": p.selling_price, "launch": fmt_date(p.launch_date),
            "active": "Active" if p.active else "Inactive", "description": p.description or "–"}


def _revenue_timing_row(p, ra):
    """Per-stream timing/recurrence row. Legacy streams (no assumption or no
    timing) display the safe defaults: Continuous monthly / Spread / Unit."""
    timing = _enum_val(getattr(ra, "revenue_timing", None), "continuous")
    recognition = _enum_val(getattr(ra, "recognition_method", None), "spread")
    start = fmt_date(getattr(ra, "revenue_start_date", None) if ra else None)
    if start == "–":
        start = fmt_date(p.launch_date)
    duration = getattr(ra, "contract_duration_months", None) if ra else None
    show_recognition = timing in ("annual_recurring", "contract_period")
    return {
        "name": p.name,
        "timing": REVENUE_TIMING_LABELS.get(timing, "Continuous monthly"),
        "unit": p.unit_label or "Unit",
        # One-time revenue is recognised on a fixed date, not a "start" date.
        "start_label": "Revenue Date" if timing == "one_time" else "Start Date",
        "start": start,
        "end": fmt_date(getattr(ra, "revenue_end_date", None) if ra else None),
        "duration": str(int(duration)) if (timing == "contract_period" and duration) else "–",
        "recognition": RECOGNITION_LABELS.get(recognition, "Spread / smoothed") if show_recognition else "–",
        "payment_terms": _payment_terms_label(
            _enum_val(getattr(ra, "payment_terms", None), "cash") if ra else "cash",
            getattr(ra, "custom_payment_days", None) if ra else None,
        ),
    }


def _opex_detail_row(e):
    freq = _enum_val(e.frequency, "monthly")
    recognition = _enum_val(getattr(e, "recognition_method", None), "spread")
    return {
        "name": e.name,
        "category": _lbl(_enum_val(e.category)),
        "timing": EXPENSE_TIMING_LABELS.get(freq, "Monthly recurring"),
        "recognition": RECOGNITION_LABELS.get(recognition, "Spread / smoothed") if freq in ("quarterly", "yearly") else "–",
        "start": fmt_date(e.start_date),
        "end": fmt_date(e.end_date),
        "inflation": fmt_pct(e.inflation_percent),
        "amount": e.amount,
    }


def _direct_cost_detail_row(c, products):
    name_by_id = {p.id: p.name for p in products}
    if c.apply_to_all:
        association, linked = "All products", "Linked"
    elif c.product_ids:
        association = ", ".join(name_by_id.get(pid, "?") for pid in c.product_ids)
        linked = "Linked"
    else:
        association, linked = "Independent / unassigned", "Independent"
    method = _enum_val(c.calculation_method)
    if method in ("percent_of_revenue", "percent_of_selling_price", "percent_of_purchase_cost"):
        value = fmt_pct(c.percent)
    else:
        value = fmt_num(c.amount)
    return {
        "name": c.name,
        "category": _lbl(_enum_val(c.category)),
        "method": COST_METHOD_LABELS.get(method, _lbl(method)),
        "association": association,
        "linked": linked,
        "supplier_terms": _payment_terms_label(_enum_val(getattr(c, "supplier_payment_terms", None), "net_30")),
        "start": fmt_date(c.start_date),
        "end": fmt_date(c.end_date),
        "value": value,
    }


def _staff_row(s):
    return {"department": _lbl(s.department.value), "title": s.job_title, "employees": s.number_of_employees,
            "salary": s.monthly_salary, "start": fmt_date(s.hiring_start_date), "active": s.active}


def _asset_row(a, nbv):
    return {"name": a.name, "category": _lbl(a.category.value), "purchase_amount": a.purchase_amount,
            "useful_life": a.useful_life_years, "method": _lbl(a.depreciation_method.value),
            "residual": a.residual_value, "financing": _lbl(a.financing_source.value), "nbv": nbv}


def _wc(wc):
    if not wc:
        return {}
    return {
        "Accounts receivable days": wc.accounts_receivable_days, "% sales on credit": wc.percent_sales_on_credit,
        "Accounts payable days": wc.accounts_payable_days, "Inventory days": wc.inventory_days,
        "Minimum cash balance": wc.minimum_cash_balance, "Bad debt %": wc.bad_debt_percent,
        "Customer deposit %": wc.customer_deposit_percent, "Supplier advance %": wc.supplier_advance_percent,
        "Safety stock %": wc.safety_stock_percent, "Stock purchase cycle": _lbl(wc.stock_purchase_cycle.value),
    }


def _financing(fin):
    eq = fin.equity
    return {
        "equity": {"Founder capital": eq.founder_capital, "Investor equity": eq.investor_equity,
                   "Investor name": eq.investor_name or "–", "Shareholding %": eq.shareholding_percent,
                   "Use of funds": eq.use_of_funds or "–", "Dividend policy %": eq.dividend_policy_percent},
        "loans": [{"name": l.name, "lender": l.lender or "–", "amount": l.amount, "rate": l.interest_rate,
                   "term": l.repayment_period_months, "grace": l.grace_period_months,
                   "type": _lbl(l.repayment_type.value), "fee": l.arrangement_fee} for l in fin.loans],
        "grants": [{"name": g.name, "amount": g.amount, "date": fmt_date(g.expected_date),
                    "restrictions": g.restrictions or "–"} for g in fin.grants],
    }


def _tax(tax):
    if not tax:
        return {}
    return {
        "Corporate tax rate": fmt_pct(tax.corporate_tax_rate), "VAT / sales tax rate": fmt_pct(tax.vat_rate),
        "VAT registration threshold": fmt_num(tax.vat_registration_threshold), "Customs duty rate": fmt_pct(tax.customs_duty_rate),
        "Withholding tax rate": fmt_pct(tax.withholding_tax_rate), "Tax payment frequency": _lbl(tax.tax_payment_frequency.value),
        "VAT payment frequency": _lbl(tax.vat_payment_frequency.value),
        "Tax loss carryforward": "Enabled" if tax.tax_loss_carryforward_enabled else "Disabled",
    }


def _scenario_row(s):
    return {"label": s.label or _lbl(s.scenario_type.value), "sales_volume": s.sales_volume_adjustment,
            "selling_price": s.selling_price_adjustment, "direct_cost": s.direct_cost_adjustment,
            "salary": s.salary_adjustment, "marketing": s.marketing_adjustment, "inflation": s.inflation_adjustment}


def _kpis(k):
    if not k:
        return {}
    return {
        "Target gross margin": fmt_pct(k.target_gross_margin_percent), "Target EBITDA margin": fmt_pct(k.target_ebitda_margin_percent),
        "Target net margin": fmt_pct(k.target_net_profit_margin_percent), "Break-even target": fmt_date(k.break_even_target_date),
        "Min. monthly revenue": fmt_num(k.min_monthly_revenue_target), "CAC target": fmt_num(k.cac_target),
        "LTV target": fmt_num(k.ltv_target), "ROI target": fmt_pct(k.roi_target_percent),
    }


# --------------------------------------------------------------------------
# preview
# --------------------------------------------------------------------------
def build_report_preview(project, scenario, view, options):
    from ..schemas.reports import ReportPreview, ReportSection, ReportWarning
    setup = project.setup
    currency = setup.currency if setup else "USD"
    start_year = setup.projection_start_date.year if setup and setup.projection_start_date else date.today().year
    years = setup.projection_period.years if setup and setup.projection_period else 5
    completion = build_completion_report(project)
    warnings, _rec = collect_warnings_and_reconciliations(project, scenario, "yearly") if setup else ([], [])

    inc = isvc.generate_income_statement(project, scenario, "yearly") if setup else None
    highlights = []
    if inc:
        highlights = [
            {"label": "Total revenue", "value": fmt_num(inc.totals.total_revenue)},
            {"label": "Gross margin", "value": fmt_pct(inc.margins.gross_margin_total_pct)},
            {"label": "Net margin", "value": fmt_pct(inc.margins.net_margin_total_pct)},
        ]

    blocking = []
    if setup is None:
        blocking.append("Project setup is required before generating a report.")
    if not project.products:
        blocking.append("At least one product / revenue stream is required.")

    return ReportPreview(
        project_id=project.id, title="Business Plan Financial Projection Report",
        company=_company_name(project, setup),
        project_name=(setup.project_name if setup else None),
        scenario=scenario, scenario_label=SCENARIO_LABELS.get(scenario, scenario.title()), view=view,
        currency=currency, period_range=f"{start_year}–{start_year + years - 1}",
        prepared_date=date.today().strftime("%d %B %Y"), prepared_for=PREPARED_FOR.get(options.report_style, "Investors"),
        sections=[ReportSection(key=k, title=t) for k, t in SECTIONS],
        completion_percent=completion.completion_percent, data_ready=len(blocking) == 0,
        can_generate=len(blocking) == 0, blocking=blocking,
        warnings=[ReportWarning(**w) for w in warnings], highlights=highlights,
    )


def now_iso():
    return datetime.now(timezone.utc)
