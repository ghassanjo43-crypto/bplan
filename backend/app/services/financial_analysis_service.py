"""Financial Analysis dashboard service.

Aggregates the three projected statements (P&L, Balance Sheet, Cash Flow) into
chart-ready data, KPIs, automatic insights, scenario comparison and warnings.
No figures are recomputed here that the statement engines already produce — the
statements remain the source of truth.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from ..models import BusinessPlanProject
from ..schemas.financial_analysis import (
    ChartSeries,
    FinancialAnalysisChart,
    FinancialAnalysisKPI,
    FinancialAnalysisMetadata,
    FinancialAnalysisPeriod,
    FinancialAnalysisResponse,
    FinancialAnalysisSection,
    FinancialAnalysisWarning,
    ScenarioComparisonResponse,
    ScenarioMetric,
    ScenarioSeries,
)
from . import balance_sheet_service as bss
from . import cash_flow_service as cfs
from . import income_statement_service as isvc

# Calm, financial palette
BLUE = "#2563eb"
EMERALD = "#059669"
TEAL = "#0d9488"
AMBER = "#d97706"
SLATE = "#64748b"
SLATE_LIGHT = "#94a3b8"
RED = "#dc2626"
INDIGO = "#4f46e5"
PALETTE = [BLUE, EMERALD, AMBER, SLATE, INDIGO, TEAL, SLATE_LIGHT, "#0891b2", "#7c3aed", "#b45309"]

SCENARIO_LABELS = {"base": "Base Case", "conservative": "Conservative", "optimistic": "Optimistic"}


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def _z(n):
    return [0.0] * n


def _add(*arrs):
    return [sum(v) for v in zip(*arrs)]


def _div(num, den):
    return [round(n / d, 4) if d else 0.0 for n, d in zip(num, den)]


def _points(labels, mapping):
    out = []
    for i, lbl in enumerate(labels):
        row = {"period": lbl}
        for k, arr in mapping.items():
            row[k] = round(arr[i], 2) if i < len(arr) else 0.0
        out.append(row)
    return out


# --------------------------------------------------------------------------
# pull period-aligned arrays from the three statements
# --------------------------------------------------------------------------
def _statement_data(project: BusinessPlanProject, scenario: str, view: str) -> dict:
    vv = "monthly" if view == "monthly" else "yearly"
    inc = isvc.generate_income_statement(project, scenario, vv)
    bs = bss.generate_balance_sheet(project, scenario, vv)
    cf = cfs.generate_cash_flow_statement(project, scenario, vv)

    labels = [p.label for p in inc.periods]
    n = len(labels)
    sub = {s.key: (s.subtotal.values_by_period if s.subtotal else _z(n)) for s in inc.sections}
    inc_section = {s.key: s for s in inc.sections}

    def cat_map(section_key):
        s = inc_section.get(section_key)
        return {li.label: li.values_by_period for li in (s.line_items if s else [])}

    # income statement
    revenue = sub.get("revenue", _z(n))
    cogs = sub.get("cost_of_sales", _z(n))
    gross_profit = sub.get("gross_profit", _z(n))
    opex = sub.get("operating_expenses", _z(n))
    operating_profit = sub.get("operating_profit", _z(n))
    finance = sub.get("finance_costs", _z(n))
    pbt = sub.get("profit_before_tax", _z(n))
    tax = [abs(x) for x in sub.get("income_tax", _z(n))]
    net = sub.get("profit_for_period", _z(n))
    ebitda = inc.margins.ebitda or _z(n)
    dep = _z(n)
    for li in inc_section.get("operating_expenses").line_items if inc_section.get("operating_expenses") else []:
        if li.key == "depreciation_amortisation":
            dep = li.values_by_period

    # revenue products (children of revenue categories) for "top streams"
    products = {}
    if inc_section.get("revenue"):
        for cat in inc_section["revenue"].line_items:
            for child in cat.children:
                products[child.label] = child.values_by_period

    # balance sheet
    bsmap = {r.key: r.values_by_period for r in bs.rows if r.values_by_period}
    borrowings = _add(bsmap.get("lt_borrowings", _z(n)), bsmap.get("cpltd", _z(n)))
    current_assets = bs.totals.total_current_assets
    current_liabilities = bs.totals.total_current_liabilities

    # cash flow
    cfmap = {r.key: r.values_by_period for r in cf.rows if r.values_by_period}
    capex = _add(cfmap.get("ppe_purchase", _z(n)), cfmap.get("intangible_purchase", _z(n)))
    fcf = _add(cf.totals.net_cash_from_operating_activities, capex)

    return dict(
        labels=labels, n=n, currency=inc.metadata.currency,
        revenue=revenue, cogs=cogs, gross_profit=gross_profit, opex=opex,
        operating_profit=operating_profit, finance=finance, pbt=pbt, tax=tax, net=net,
        ebitda=ebitda, dep=dep,
        gross_margin=inc.margins.gross_margin_pct, ebitda_margin=inc.margins.ebitda_margin_pct,
        net_margin=inc.margins.net_margin_pct, operating_margin=inc.margins.operating_margin_pct,
        revenue_by_category=cat_map("revenue"), cogs_by_category=cat_map("cost_of_sales"),
        opex_by_class=cat_map("operating_expenses"), products=products,
        cash=bsmap.get("cash", _z(n)), ar=bsmap.get("receivables", _z(n)),
        inventory=bsmap.get("inventory", _z(n)), payables=bsmap.get("payables", _z(n)),
        prepay=bsmap.get("prepayments", _z(n)), ppe=bsmap.get("ppe", _z(n)),
        intangibles=bsmap.get("intangibles", _z(n)), total_assets=bsmap.get("total_assets", _z(n)),
        total_equity=bsmap.get("total_equity", _z(n)), retained=bsmap.get("retained", _z(n)),
        tax_payable=bsmap.get("tax_payable", _z(n)), vat_payable=bsmap.get("vat_payable", _z(n)),
        deposits=bsmap.get("deposits", _z(n)), borrowings=borrowings,
        current_assets=current_assets, current_liabilities=current_liabilities,
        nwc=[current_assets[i] - current_liabilities[i] for i in range(n)],
        current_ratio=_div(current_assets, current_liabilities),
        cf_operating=cf.totals.net_cash_from_operating_activities,
        cf_investing=cf.totals.net_cash_used_in_investing_activities,
        cf_financing=cf.totals.net_cash_from_financing_activities,
        cf_closing=cf.totals.closing_cash, cf_opening=cf.totals.opening_cash,
        cf_net_change=cf.totals.net_change_in_cash, capex=capex, fcf=fcf,
        balance_status=bs.balance_check.status, cash_recon=cf.cash_reconciliation.status,
    )


def _series(items):
    out = []
    for i, (key, label, fmt, *rest) in enumerate(items):
        color = rest[0] if rest else PALETTE[i % len(PALETTE)]
        typ = rest[1] if len(rest) > 1 else None
        out.append(ChartSeries(key=key, label=label, format=fmt, color=color, type=typ))
    return out


def _cat_chart(key, title, desc, ctype, cat_map, labels, unit="currency", colors=None):
    """Build a stacked/donut chart from a {label: array} category map."""
    cats = [(lbl, arr) for lbl, arr in cat_map.items() if sum(abs(x) for x in arr) > 0]
    series = []
    mapping = {}
    for i, (lbl, arr) in enumerate(cats):
        s = _slug(lbl)
        mapping[s] = arr
        color = (colors[i % len(colors)] if colors else PALETTE[i % len(PALETTE)])
        series.append(ChartSeries(key=s, label=lbl, format=unit, color=color))
    if ctype in ("donut", "pie"):
        data = [{"name": lbl, "key": _slug(lbl), "value": round(sum(arr), 2)} for lbl, arr in cats]
    else:
        data = _points(labels, mapping)
    return FinancialAnalysisChart(key=key, title=title, description=desc, chart_type=ctype,
                                  unit=unit, data=data, series=series)


# --------------------------------------------------------------------------
# chart sections
# --------------------------------------------------------------------------
def build_executive_overview_charts(d):
    L = d["labels"]
    charts = [
        FinancialAnalysisChart(
            key="revenue_profit_trend", title="Revenue, EBITDA and Net Profit Trend",
            description="Top-line growth alongside profitability.", chart_type="line",
            data=_points(L, {"revenue": d["revenue"], "ebitda": d["ebitda"], "net_profit": d["net"]}),
            series=_series([("revenue", "Revenue", "currency", BLUE),
                            ("ebitda", "EBITDA", "currency", EMERALD),
                            ("net_profit", "Net profit", "currency", TEAL)]),
        ),
        FinancialAnalysisChart(
            key="revenue_vs_costs", title="Revenue vs Total Costs",
            description="Whether the business scales profitably.", chart_type="combo",
            data=_points(L, {"cost_of_sales": d["cogs"], "operating_expenses": d["opex"],
                             "finance": d["finance"], "tax": d["tax"], "revenue": d["revenue"]}),
            series=_series([("cost_of_sales", "Cost of sales", "currency", AMBER, "bar"),
                            ("operating_expenses", "Operating expenses", "currency", SLATE, "bar"),
                            ("finance", "Finance costs", "currency", SLATE_LIGHT, "bar"),
                            ("tax", "Tax", "currency", "#b45309", "bar"),
                            ("revenue", "Revenue", "currency", BLUE, "line")]),
        ),
        FinancialAnalysisChart(
            key="margin_trend", title="Margin Trend", description="Profitability margins over time.",
            chart_type="line", unit="percent",
            data=_points(L, {"gross_margin": d["gross_margin"], "ebitda_margin": d["ebitda_margin"],
                             "net_margin": d["net_margin"]}),
            series=_series([("gross_margin", "Gross margin", "percent", BLUE),
                            ("ebitda_margin", "EBITDA margin", "percent", EMERALD),
                            ("net_margin", "Net margin", "percent", AMBER)]),
        ),
        _profit_bridge(d),
    ]
    return FinancialAnalysisSection(key="overview", title="Executive Overview",
                                    description="Headline growth, profitability and how revenue converts to profit.",
                                    charts=charts)


def _profit_bridge(d):
    rev = sum(d["revenue"]); cogs = sum(d["cogs"]); gp = sum(d["gross_profit"])
    opex_excl_dep = sum(d["opex"]) - sum(d["dep"])
    dep = sum(d["dep"]); fin = sum(d["finance"]); tax = sum(d["tax"]); net = sum(d["net"])
    steps = [
        ("Revenue", rev, "total"), ("Cost of sales", -cogs, "neg"), ("Gross profit", gp, "subtotal"),
        ("Operating expenses", -opex_excl_dep, "neg"), ("Depreciation & amortisation", -dep, "neg"),
        ("Finance costs", -fin, "neg"), ("Income tax", -tax, "neg"), ("Net profit / (loss)", net, "total"),
    ]
    data = [{"name": s[0], "value": round(s[1], 2), "kind": s[2]} for s in steps]
    return FinancialAnalysisChart(key="profit_bridge", title="Profit Bridge",
                                  description="How revenue converts into net profit (whole projection).",
                                  chart_type="waterfall", data=data, series=[])


def build_revenue_analysis_charts(d):
    L = d["labels"]
    top = sorted(d["products"].items(), key=lambda kv: sum(kv[1]), reverse=True)[:8]
    top_data = [{"name": lbl, "value": round(sum(arr), 2)} for lbl, arr in top]
    growth = _growth(d["revenue"])
    charts = [
        _cat_chart("revenue_by_stream", "Revenue by Stream", "Revenue contribution by IFRS category.",
                   "stacked_bar", d["revenue_by_category"], L),
        _cat_chart("revenue_mix", "Revenue Mix", "Total revenue split by category.",
                   "donut", d["revenue_by_category"], L),
        FinancialAnalysisChart(key="top_revenue_streams", title="Top Revenue Streams",
                               description="Largest streams by total projected revenue.", chart_type="bar",
                               data=top_data, series=_series([("value", "Total revenue", "currency", BLUE)])),
        FinancialAnalysisChart(key="revenue_growth", title="Revenue Growth Rate",
                               description="Period-over-period revenue growth.", chart_type="line", unit="percent",
                               data=_points(L, {"growth": growth}),
                               series=_series([("growth", "Revenue growth", "percent", EMERALD)])),
    ]
    return FinancialAnalysisSection(key="revenue", title="Revenue Analysis",
                                    description="Revenue composition, concentration and growth.", charts=charts)


def build_cost_profitability_charts(d):
    L = d["labels"]
    charts = [
        _cat_chart("cogs_by_category", "Cost of Sales by Category", "Direct cost composition.",
                   "stacked_bar", d["cogs_by_category"], L, colors=[AMBER, SLATE, "#b45309", SLATE_LIGHT, "#a16207"]),
        _cat_chart("opex_by_class", "Operating Expenses by IFRS Classification", "Operating expense composition.",
                   "stacked_bar", d["opex_by_class"], L),
        _cat_chart("expense_mix", "Expense Mix", "Total operating expenses by classification.",
                   "donut", d["opex_by_class"], L),
        FinancialAnalysisChart(key="gross_profit_margin", title="Gross Profit and Gross Margin",
                               description="Gross profit value with margin overlay.", chart_type="combo",
                               data=_points(L, {"gross_profit": d["gross_profit"], "gross_margin": d["gross_margin"]}),
                               series=[ChartSeries(key="gross_profit", label="Gross profit", format="currency", color=BLUE, type="bar"),
                                       ChartSeries(key="gross_margin", label="Gross margin", format="percent", color=EMERALD, type="line", axis="right")]),
    ]
    return FinancialAnalysisSection(key="cost_profitability", title="Cost & Profitability Analysis",
                                    description="Cost structure and gross profitability.", charts=charts)


def build_cash_flow_charts(d):
    L = d["labels"]
    min_cash = (project_min_cash(d))
    charts = [
        FinancialAnalysisChart(key="cash_flow_by_activity", title="Cash Flow by Activity",
                               description="Operating, investing and financing cash flows.", chart_type="stacked_bar",
                               data=_points(L, {"operating": d["cf_operating"], "investing": d["cf_investing"], "financing": d["cf_financing"]}),
                               series=_series([("operating", "Operating", "currency", EMERALD),
                                               ("investing", "Investing", "currency", SLATE),
                                               ("financing", "Financing", "currency", BLUE)])),
        FinancialAnalysisChart(key="closing_cash_trend", title="Closing Cash Balance Trend",
                               description="Projected cash position at each period end.", chart_type="area",
                               data=_points(L, {"closing_cash": d["cf_closing"]}),
                               series=_series([("closing_cash", "Closing cash", "currency", BLUE)])),
        FinancialAnalysisChart(key="free_cash_flow_trend", title="Free Cash Flow Trend",
                               description="Operating cash flow less capital expenditure.", chart_type="line",
                               data=_points(L, {"fcf": d["fcf"]}),
                               series=_series([("fcf", "Free cash flow", "currency", TEAL)])),
        _cash_bridge(d),
    ]
    if min_cash is not None:
        charts.append(FinancialAnalysisChart(
            key="funding_gap", title="Cash vs Minimum Cash Target",
            description="Closing cash against the minimum cash balance target.", chart_type="line",
            data=_points(L, {"closing_cash": d["cf_closing"], "min_cash": [min_cash] * d["n"]}),
            series=_series([("closing_cash", "Closing cash", "currency", BLUE),
                            ("min_cash", "Minimum cash target", "currency", RED)])))
    return FinancialAnalysisSection(key="cash", title="Cash Flow Analysis",
                                    description="Cash generation, free cash flow and funding adequacy.", charts=charts)


def _cash_bridge(d):
    op = sum(d["cf_operating"]); inv = sum(d["cf_investing"]); fin = sum(d["cf_financing"])
    closing = d["cf_closing"][-1] if d["cf_closing"] else 0.0
    data = [
        {"name": "Opening cash", "value": 0.0, "kind": "total"},
        {"name": "Operating", "value": round(op, 2), "kind": "pos" if op >= 0 else "neg"},
        {"name": "Investing", "value": round(inv, 2), "kind": "pos" if inv >= 0 else "neg"},
        {"name": "Financing", "value": round(fin, 2), "kind": "pos" if fin >= 0 else "neg"},
        {"name": "Closing cash", "value": round(closing, 2), "kind": "total"},
    ]
    return FinancialAnalysisChart(key="cash_movement_bridge", title="Cash Movement Bridge",
                                  description="Opening + operating + investing + financing = closing cash.",
                                  chart_type="waterfall", data=data, series=[])


def build_balance_sheet_charts(d):
    L = d["labels"]
    charts = [
        FinancialAnalysisChart(key="assets_composition", title="Assets Composition",
                               description="Make-up of total assets over time.", chart_type="stacked_bar",
                               data=_points(L, {"cash": d["cash"], "receivables": d["ar"], "inventory": d["inventory"],
                                                "prepayments": d["prepay"], "ppe": d["ppe"], "intangibles": d["intangibles"]}),
                               series=_series([("cash", "Cash", "currency", BLUE), ("receivables", "Receivables", "currency", "#0891b2"),
                                               ("inventory", "Inventory", "currency", SLATE), ("prepayments", "Prepayments", "currency", SLATE_LIGHT),
                                               ("ppe", "PP&E", "currency", INDIGO), ("intangibles", "Intangibles", "currency", "#7c3aed")])),
        FinancialAnalysisChart(key="liabilities_equity", title="Liabilities and Equity Composition",
                               description="Funding structure of the business.", chart_type="stacked_bar",
                               data=_points(L, {"payables": d["payables"], "borrowings": d["borrowings"], "tax_payable": d["tax_payable"],
                                                "vat_payable": d["vat_payable"], "deposits": d["deposits"], "equity": d["total_equity"]}),
                               series=_series([("payables", "Trade payables", "currency", AMBER), ("borrowings", "Borrowings", "currency", "#b45309"),
                                               ("tax_payable", "Tax payable", "currency", SLATE), ("vat_payable", "VAT payable", "currency", SLATE_LIGHT),
                                               ("deposits", "Customer deposits", "currency", "#a16207"), ("equity", "Equity", "currency", EMERALD)])),
        FinancialAnalysisChart(key="debt_vs_equity", title="Debt vs Equity",
                               description="Capital structure: borrowings against equity.", chart_type="grouped_bar",
                               data=_points(L, {"borrowings": d["borrowings"], "equity": d["total_equity"]}),
                               series=_series([("borrowings", "Total borrowings", "currency", AMBER),
                                               ("equity", "Total equity", "currency", EMERALD)])),
        FinancialAnalysisChart(key="nwc_trend", title="Net Working Capital Trend",
                               description="Current assets less current liabilities.", chart_type="line",
                               data=_points(L, {"nwc": d["nwc"]}),
                               series=_series([("nwc", "Net working capital", "currency", BLUE)])),
        FinancialAnalysisChart(key="current_ratio_trend", title="Current Ratio Trend",
                               description="Current assets / current liabilities.", chart_type="line", unit="ratio",
                               data=_points(L, {"current_ratio": d["current_ratio"]}),
                               series=_series([("current_ratio", "Current ratio", "ratio", EMERALD)])),
    ]
    return FinancialAnalysisSection(key="balance_sheet", title="Balance Sheet Analysis",
                                    description="Asset composition, capital structure and liquidity.", charts=charts)


def build_working_capital_charts(d):
    L = d["labels"]
    wc = project_working_capital(d)
    ccc = wc["inv_days"] + wc["ar_days"] - wc["ap_days"]
    wcr = [d["inventory"][i] + d["ar"][i] - d["payables"][i] for i in range(d["n"])]
    charts = [
        FinancialAnalysisChart(key="rip_trend", title="Receivables, Inventory and Payables Trend",
                               description="The core working-capital balances.", chart_type="line",
                               data=_points(L, {"receivables": d["ar"], "inventory": d["inventory"], "payables": d["payables"]}),
                               series=_series([("receivables", "Receivables", "currency", BLUE),
                                               ("inventory", "Inventory", "currency", AMBER),
                                               ("payables", "Payables", "currency", SLATE)])),
        FinancialAnalysisChart(key="ccc", title="Cash Conversion Cycle",
                               description="Inventory days + receivable days − payable days.", chart_type="line", unit="number",
                               data=_points(L, {"ccc": [ccc] * d["n"]}),
                               series=_series([("ccc", "Cash conversion cycle (days)", "number", INDIGO)])),
        FinancialAnalysisChart(key="wcr", title="Working Capital Requirement",
                               description="Inventory + receivables − payables.", chart_type="bar",
                               data=_points(L, {"wcr": wcr}),
                               series=_series([("wcr", "Working capital requirement", "currency", BLUE)])),
        FinancialAnalysisChart(key="receivables_vs_revenue", title="Receivables vs Revenue",
                               description="Collection burden as revenue grows.", chart_type="combo",
                               data=_points(L, {"revenue": d["revenue"], "receivables": d["ar"]}),
                               series=[ChartSeries(key="revenue", label="Revenue", format="currency", color=BLUE, type="bar"),
                                       ChartSeries(key="receivables", label="Receivables", format="currency", color=AMBER, type="line")]),
    ]
    return FinancialAnalysisSection(key="working_capital", title="Working Capital Analysis",
                                    description="Receivables, inventory, payables and the cash cycle.", charts=charts)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _growth(arr):
    out = [0.0]
    for t in range(1, len(arr)):
        prev = arr[t - 1]
        out.append(round((arr[t] - prev) / abs(prev) * 100, 2) if prev else 0.0)
    return out


def project_min_cash(d):
    return d.get("_min_cash")


def project_working_capital(d):
    return d.get("_wc", {"inv_days": 0, "ar_days": 0, "ap_days": 0})


def _cagr(arr):
    first = next((v for v in arr if v > 0), None)
    last = arr[-1] if arr else None
    if not first or not last or last <= 0 or len(arr) < 2:
        return None
    years = len(arr) - 1
    return round(((last / first) ** (1 / years) - 1) * 100, 1)


# --------------------------------------------------------------------------
# KPIs
# --------------------------------------------------------------------------
def build_kpi_dashboard(project, d):
    n = d["n"]
    rev_total = sum(d["revenue"])
    gp = sum(d["gross_profit"]); eb = sum(d["ebitda"]); net = sum(d["net"]); fin = sum(d["finance"])
    ta = d["total_assets"][-1] if d["total_assets"] else 0
    eq = d["total_equity"][-1] if d["total_equity"] else 0
    borrow = d["borrowings"][-1] if d["borrowings"] else 0
    ca = d["current_assets"][-1] if d["current_assets"] else 0
    cl = d["current_liabilities"][-1] if d["current_liabilities"] else 0
    inv = d["inventory"][-1] if d["inventory"] else 0
    wc = project_working_capital(d)

    def pct(num, den):
        return round(num / den * 100, 1) if den else None

    def ratio(num, den):
        return round(num / den, 2) if den else None

    K = FinancialAnalysisKPI
    kpis = [
        K(key="gross_margin", label="Gross margin", value=pct(gp, rev_total), format="percent", group="profitability", good=(gp > 0)),
        K(key="ebitda_margin", label="EBITDA margin", value=pct(eb, rev_total), format="percent", group="profitability", good=(eb > 0)),
        K(key="net_margin", label="Net profit margin", value=pct(net, rev_total), format="percent", group="profitability", good=(net > 0)),
        K(key="roa", label="Return on assets", value=pct(net, ta), format="percent", group="profitability", good=(net > 0)),
        K(key="roe", label="Return on equity", value=pct(net, eq), format="percent", group="profitability", good=(net > 0 and eq > 0)),
        K(key="current_ratio", label="Current ratio", value=ratio(ca, cl), format="ratio", group="liquidity", good=(ca >= cl)),
        K(key="quick_ratio", label="Quick ratio", value=ratio(ca - inv, cl), format="ratio", group="liquidity", good=((ca - inv) >= cl)),
        K(key="cash", label="Closing cash", value=round(d["cf_closing"][-1], 2) if d["cf_closing"] else 0, format="currency", group="liquidity", good=(d["cf_closing"][-1] >= 0 if d["cf_closing"] else True)),
        K(key="nwc", label="Net working capital", value=round(d["nwc"][-1], 2) if d["nwc"] else 0, format="currency", group="liquidity"),
        K(key="debt_to_equity", label="Debt-to-equity", value=ratio(borrow, eq), format="ratio", group="leverage", good=(eq > 0 and (borrow / eq < 2 if eq else False))),
        K(key="debt_to_assets", label="Debt-to-assets", value=ratio(borrow, ta), format="ratio", group="leverage"),
        K(key="interest_coverage", label="Interest coverage", value=ratio(eb, fin), format="ratio", group="leverage", good=(fin == 0 or eb > fin)),
        K(key="receivable_days", label="Receivable days", value=float(wc["ar_days"]), format="number", group="efficiency"),
        K(key="inventory_days", label="Inventory days", value=float(wc["inv_days"]), format="number", group="efficiency"),
        K(key="payable_days", label="Payable days", value=float(wc["ap_days"]), format="number", group="efficiency"),
        K(key="ccc", label="Cash conversion cycle", value=float(wc["inv_days"] + wc["ar_days"] - wc["ap_days"]), format="number", group="efficiency"),
        K(key="operating_cf", label="Operating cash flow", value=round(sum(d["cf_operating"]), 2), format="currency", group="cash", good=(sum(d["cf_operating"]) > 0)),
        K(key="free_cash_flow", label="Free cash flow", value=round(sum(d["fcf"]), 2), format="currency", group="cash", good=(sum(d["fcf"]) > 0)),
    ]
    return kpis


# --------------------------------------------------------------------------
# insights
# --------------------------------------------------------------------------
def _insights(d):
    out = []
    cagr = _cagr(d["revenue"])
    if cagr is not None and len(d["revenue"]) >= 2:
        out.append(f"Revenue grows from {d['revenue'][0]:,.0f} to {d['revenue'][-1]:,.0f} {d['currency']}, "
                   f"a CAGR of {cagr}%.")
    if d["gross_margin"]:
        out.append(f"Gross margin moves from {d['gross_margin'][0]:.1f}% to {d['gross_margin'][-1]:.1f}% across the projection.")
    if any(c < 0 for c in d["cf_closing"]):
        first_neg = next((d["labels"][i] for i, c in enumerate(d["cf_closing"]) if c < 0), None)
        out.append(f"Closing cash turns negative in {first_neg}, indicating a potential funding gap.")
    else:
        out.append("Cash remains positive throughout the projection.")
    if d["ar"] and d["ar"][-1] > d["ar"][0]:
        out.append("Receivables rise as credit sales grow, increasing working capital requirements.")
    if d["borrowings"] and d["total_equity"] and d["total_equity"][-1] != 0:
        de0 = d["borrowings"][0] / d["total_equity"][0] if d["total_equity"][0] else None
        de1 = d["borrowings"][-1] / d["total_equity"][-1] if d["total_equity"][-1] else None
        if de0 is not None and de1 is not None and de1 < de0:
            out.append("Debt-to-equity declines over the projection as borrowings are repaid.")
    return out


# --------------------------------------------------------------------------
# warnings
# --------------------------------------------------------------------------
def build_financial_analysis_warnings(d):
    W = FinancialAnalysisWarning
    out = []
    if any(c < -1 for c in d["cf_closing"]):
        out.append(W(code="negative_cash", severity="critical", message="Projected cash balance is negative in one or more periods."))
    if sum(d["gross_profit"]) < 0:
        out.append(W(code="negative_gross_margin", severity="critical", message="Projected gross margin is negative."))
    if sum(d["ebitda"]) < 0:
        out.append(W(code="negative_ebitda", severity="warning", message="Projected EBITDA is negative over the projection."))
    if d["current_ratio"] and d["current_ratio"][-1] < 1.0:
        out.append(W(code="low_current_ratio", severity="warning", message="Current ratio is below 1.0 — short-term liquidity pressure."))
    if d["total_equity"] and d["total_equity"][-1] != 0 and d["borrowings"]:
        de = d["borrowings"][-1] / d["total_equity"][-1] if d["total_equity"][-1] else None
        if de is not None and de > 3:
            out.append(W(code="high_leverage", severity="warning", message="Debt-to-equity is unusually high."))
    if d.get("balance_status") != "balanced":
        out.append(W(code="out_of_balance", severity="critical", message="Balance sheet is out of balance."))
    if d.get("cash_recon") != "reconciled":
        out.append(W(code="cash_not_reconciled", severity="critical", message="Cash flow does not reconcile to the balance sheet."))
    return out


# --------------------------------------------------------------------------
# entrypoints
# --------------------------------------------------------------------------
def _enrich(project, d):
    wc = project.working_capital
    d["_wc"] = {
        "ar_days": (wc.accounts_receivable_days if wc else 0),
        "inv_days": (wc.inventory_days if wc else 0),
        "ap_days": (wc.accounts_payable_days if wc else 0),
    }
    d["_min_cash"] = (wc.minimum_cash_balance if wc else None)
    return d


def generate_financial_analysis(project, scenario="base", view="yearly", chart_set=None) -> FinancialAnalysisResponse:
    view = "monthly" if view == "monthly" else "yearly"
    d = _enrich(project, _statement_data(project, scenario, view))

    builders = {
        "overview": build_executive_overview_charts,
        "revenue": build_revenue_analysis_charts,
        "cost_profitability": build_cost_profitability_charts,
        "cash": build_cash_flow_charts,
        "balance_sheet": build_balance_sheet_charts,
        "working_capital": build_working_capital_charts,
    }
    keys = [chart_set] if chart_set in builders else list(builders.keys())
    sections = [builders[k](d) for k in keys]

    periods = [FinancialAnalysisPeriod(index=i, label=lbl, period_type=("annual" if view == "yearly" else "monthly"))
               for i, lbl in enumerate(d["labels"])]
    meta = FinancialAnalysisMetadata(
        project_id=project.id, project_name=project.name, scenario=scenario,
        scenario_label=SCENARIO_LABELS.get(scenario, scenario.title()), view=view,
        currency=d["currency"], generated_at=datetime.now(timezone.utc),
    )
    return FinancialAnalysisResponse(
        metadata=meta, periods=periods, kpis=build_kpi_dashboard(project, d),
        sections=sections, insights=_insights(d), warnings=build_financial_analysis_warnings(d),
    )


def build_kpis_only(project, scenario, view):
    d = _enrich(project, _statement_data(project, scenario, view))
    return build_kpi_dashboard(project, d)


def _cumsum(arr) -> list[float]:
    out, run = [], 0.0
    for x in arr:
        run += x
        out.append(round(run, 2))
    return out


def build_scenario_comparison(project, scenario_ids=None, view="yearly") -> ScenarioComparisonResponse:
    """Side-by-side comparison of 2–3 saved scenarios, selected by scenario id.

    Every series comes from the same statement engines the individual Income
    Statement / Balance Sheet / Cash Flow use (via ``_statement_data``), so the
    numbers match exactly. Unknown ids fall back to the project's default
    scenario (the route convention), never overwriting any assumptions.
    """
    from . import scenario_service as scn

    view = "monthly" if view == "monthly" else "yearly"
    by_id = {s.id: s for s in project.scenarios}
    default = next((s for s in project.scenarios if getattr(s, "is_default", False)),
                   project.scenarios[0] if project.scenarios else None)

    chosen: list = []
    for sid in (scenario_ids or []):
        s = by_id.get(sid) or default          # unknown id → default (safe fallback)
        if s is not None and s.id not in {c.id for c in chosen}:
            chosen.append(s)
    if not chosen:                             # nothing requested → all saved (cap 3)
        chosen = list(project.scenarios)[:3]
    chosen = chosen[:3]

    if chosen:
        order = [s.id for s in chosen]
        label_by_id = {s.id: scn.display_name(s) for s in chosen}
    else:                                      # project with no scenarios at all
        order = ["base"]
        label_by_id = {"base": "Base Case"}

    data = {sid: _enrich(project, _statement_data(project, sid, view)) for sid in order}
    for sid in order:
        d = data[sid]
        d["cum_net"] = _cumsum(d["net"])       # break-even = crosses 0
        pre_financing = _add(d["cf_operating"], d["cf_investing"])
        d["funding_need"] = _cumsum(pre_financing)   # trough = peak external funding required

    first = data[order[0]]
    labels, currency = first["labels"], first["currency"]

    def metric(key, label, fmt, field):
        return ScenarioMetric(key=key, label=label, format=fmt, series=[
            ScenarioSeries(scenario=sid, label=label_by_id[sid],
                           values=[round(x, 2) for x in data[sid][field]])
            for sid in order
        ])

    metrics = [
        metric("revenue", "Revenue", "currency", "revenue"),
        metric("gross_profit", "Gross profit", "currency", "gross_profit"),
        metric("gross_margin", "Gross margin", "percent", "gross_margin"),
        metric("ebitda", "EBITDA", "currency", "ebitda"),
        metric("net_profit", "Net profit", "currency", "net"),
        metric("cash_balance", "Cash balance (closing)", "currency", "cf_closing"),
        metric("break_even", "Cumulative net profit (break-even at ≥ 0)", "currency", "cum_net"),
        metric("funding_requirement", "Cumulative cash before financing (funding need = trough)", "currency", "funding_need"),
    ]
    return ScenarioComparisonResponse(
        project_id=project.id, project_name=project.name, view=view, currency=currency,
        periods=labels, metrics=metrics, generated_at=datetime.now(timezone.utc),
    )
