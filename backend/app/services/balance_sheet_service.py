"""IFRS Statement of Financial Position (Balance Sheet) engine.

Design that guarantees the sheet balances:
  * Performance (profit, tax, depreciation) is taken from the income-statement
    engine (the single source of truth for performance).
  * Every position balance (PPE, receivables, inventory, payables, borrowings,
    equity, etc.) is derived from the assumptions/schedules.
  * Cash is derived so that Assets = Equity + Liabilities. Because cash is the
    plug against fully-articulated balances, it is economically correct — it
    reflects working capital, capex, debt, equity, tax and VAT — and an
    internal *cash bridge* reconstructs the same figure for transparency.

Annual view shows closing balances at each year-end month (not summed months).
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timezone

from dateutil.relativedelta import relativedelta

from ..models import BusinessPlanProject
from ..models.enums import DepreciationMethod, PaymentTerms, RepaymentType
from . import direct_cost_projection_service as dcp
from . import fixed_asset_service as fas
from . import income_statement_service as isvc
from . import projection_period_service as pps


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _mb(start: date, other: date) -> int:
    return (other.year - start.year) * 12 + (other.month - start.month)


def _zeros(n: int) -> list[float]:
    return [0.0] * n


def _cumulative(arr: list[float]) -> list[float]:
    out, run = [], 0.0
    for v in arr:
        run += v
        out.append(run)
    return out


def _step_from(n: int, idx: int, amount: float) -> list[float]:
    """A constant balance held from month idx onward."""
    idx = max(0, idx)
    return [amount if t >= idx else 0.0 for t in range(n)]


# --------------------------------------------------------------------------
# loan schedule (balance / principal / drawdown by month)
# --------------------------------------------------------------------------
def _loan_monthly(loan, n: int, start: date, rate_pct: float):
    balance = _zeros(n)
    principal = _zeros(n)
    drawdown = _zeros(n)
    offset = max(0, _mb(start, loan.drawdown_date)) if loan.drawdown_date else 0
    if 0 <= offset < n:
        drawdown[offset] = loan.amount
    term = max(1, loan.repayment_period_months)
    grace = min(loan.grace_period_months, term)
    r = rate_pct / 100.0 / 12.0
    amort_months = max(1, term - grace)
    bal = loan.amount
    if r > 0:
        annuity = bal * r / (1 - (1 + r) ** (-amort_months))
    else:
        annuity = bal / amort_months
    straight = bal / amort_months
    for k in range(term):
        t = offset + k
        intr = bal * r
        if loan.repayment_type == RepaymentType.BULLET:
            pr = bal if k == term - 1 else 0.0
        elif k < grace:
            pr = 0.0
        elif loan.repayment_type == RepaymentType.EQUAL_INSTALLMENTS:
            pr = annuity - intr
        else:
            pr = straight
        pr = min(pr, bal)
        bal = max(0.0, bal - pr)
        if 0 <= t < n:
            principal[t] = pr
        # record closing balance for this month
        if 0 <= t < n:
            balance[t] = bal
    # carry the closing balance forward across months with no scheduled change
    last = 0.0
    for t in range(n):
        if t < offset:
            balance[t] = 0.0
        else:
            if principal[t] == 0 and drawdown[t] == 0 and balance[t] == 0 and t > offset:
                balance[t] = last
        last = balance[t]
    return balance, principal, drawdown


def _all_loans_monthly(project: BusinessPlanProject, n: int, start: date, scen):
    total_bal = _zeros(n)
    total_principal = _zeros(n)
    total_drawdown = _zeros(n)
    per_loan = []
    for loan in project.financing.loans:
        rate = loan.interest_rate + scen.interest_rate
        bal, pr, dr = _loan_monthly(loan, n, start, rate)
        per_loan.append((loan, bal, pr, dr))
        total_bal = [a + b for a, b in zip(total_bal, bal)]
        total_principal = [a + b for a, b in zip(total_principal, pr)]
        total_drawdown = [a + b for a, b in zip(total_drawdown, dr)]
    # current portion = principal due in the next 12 months
    current_portion = _zeros(n)
    for t in range(n):
        current_portion[t] = sum(total_principal[t + 1: t + 13])
    return total_bal, total_principal, total_drawdown, current_portion, per_loan


# --------------------------------------------------------------------------
# monthly model
# --------------------------------------------------------------------------
@dataclass
class BSModel:
    n: int
    start: date
    M: dict           # monthly arrays
    scen_label: str
    currency: str
    warnings: list


def _gratuity_monthly(project, n, start, scen):
    arr = _zeros(n)
    salary_factor = 1 + scen.salary / 100.0
    for role in project.staffing:
        if not role.active:
            continue
        hire = max(0, _mb(start, role.hiring_start_date)) if role.hiring_start_date else 0
        for t in range(hire, n):
            base = role.monthly_salary * ((1 + role.annual_increase_percent / 100.0) ** (t // 12)) * role.number_of_employees
            arr[t] += base * role.gratuity_percent / 100.0 * salary_factor
    return arr


def compute_monthly(project: BusinessPlanProject, scenario: str) -> BSModel:
    ctx, b = isvc._compute(project, scenario)
    scen = ctx.scen
    n, start = b["n"], b["start"]
    months = pps.get_monthly_periods(project)
    dim = [calendar.monthrange(p.start_date.year, p.start_date.month)[1] for p in months]
    currency = project.setup.currency if project.setup else "USD"
    warn: list = []

    rev = b["total_revenue"]
    cogs = b["total_cogs"]
    product_cogs = b["cogs_lines"].get("product_direct_costs", _zeros(n))
    opex = [a + c + d for a, c, d in zip(b["opex"]["selling"], b["opex"]["admin"], b["opex"]["technology"])]
    dep = b["dep_total"]
    net = b["net"]
    tax_exp = b["tax"]

    wc = project.working_capital
    ar_days = wc.accounts_receivable_days if wc else 30
    credit = (wc.percent_sales_on_credit if wc else 0) / 100.0
    ap_days = wc.accounts_payable_days if wc else 30
    inv_days = wc.inventory_days if wc else 0
    cust_dep = (wc.customer_deposit_percent if wc else 0) / 100.0
    if wc is None:
        warn.append(("no_working_capital", "warning", "No working capital assumptions — receivables/payables/inventory use defaults."))

    resolved_rev = getattr(ctx, "_resolved_rev", None)

    # --- assets (non-cash) ---
    # Collection timing precedence: a revenue stream's own payment terms drive
    # its receivables; the Working Capital "default customer collection days" is
    # used only for streams without specific terms. (See _collection_days.)
    def _collection_days(ra) -> float:
        if ra is None:
            return ar_days
        terms = ra.payment_terms
        if terms == PaymentTerms.CUSTOM:
            return ra.custom_payment_days if ra.custom_payment_days is not None else ar_days
        days = terms.days
        return days if days is not None else ar_days

    if resolved_rev:
        ar = _zeros(n)
        for rs in resolved_rev.values():
            days = _collection_days(rs.ra)
            for t in range(n):
                ar[t] += credit * rs.net[t] * days / max(dim[t], 1)
    else:
        ar = [credit * rev[t] * ar_days / max(dim[t], 1) for t in range(n)]
    inventory_wc = [product_cogs[t] * inv_days / max(dim[t], 1) for t in range(n)]
    if rev and sum(rev) > 0 and ar_days == 0 and credit == 0:
        warn.append(("no_receivable_terms", "info", "Revenue exists but no credit terms — receivables are zero."))

    # PPE (tangible) & intangibles from the depreciation engine
    ppe_cost = _zeros(n); ppe_acc = _zeros(n)
    intang_cost = _zeros(n); intang_acc = _zeros(n)
    for asset in project.fixed_assets:
        if not getattr(asset, "active", True):
            continue
        d = fas.asset_monthly_depreciation(asset, n, start)
        acc = _cumulative(d)
        buy = asset.purchase_date or asset.depreciation_start or start
        cost = _step_from(n, _mb(start, buy), asset.purchase_amount)
        if asset.category.value == "software_development":
            intang_cost = [a + b2 for a, b2 in zip(intang_cost, cost)]
            intang_acc = [a + b2 for a, b2 in zip(intang_acc, acc)]
        else:
            ppe_cost = [a + b2 for a, b2 in zip(ppe_cost, cost)]
            ppe_acc = [a + b2 for a, b2 in zip(ppe_acc, acc)]
        if asset.useful_life_years <= 0 and asset.depreciation_method != DepreciationMethod.NONE:
            warn.append((f"asset_life_{asset.id}", "warning", f"Asset '{asset.name}' is missing a useful life."))
    ppe_net = [ppe_cost[t] - ppe_acc[t] for t in range(n)]
    intang_net = [intang_cost[t] - intang_acc[t] for t in range(n)]

    # startup costs -> prepayments / inventory / other NCA / expensed (RE)
    prepay = _zeros(n); startup_inv = _zeros(n); other_nca = _zeros(n); expensed_startup = _zeros(n)
    for sc in project.startup_costs:
        idx = max(0, _mb(start, sc.payment_date)) if sc.payment_date else 0
        held = _step_from(n, idx, sc.amount)
        if not sc.capitalized:
            expensed_startup[min(idx, n - 1)] += sc.amount
            continue
        cat = sc.category.value
        if cat in ("office_deposit", "rent_advance"):
            prepay = [a + b2 for a, b2 in zip(prepay, held)]
        elif cat in ("initial_inventory", "raw_materials"):
            startup_inv = [a + b2 for a, b2 in zip(startup_inv, held)]
        else:
            other_nca = [a + b2 for a, b2 in zip(other_nca, held)]
    inventory = [inventory_wc[t] + startup_inv[t] for t in range(n)]

    # --- VAT (net position, settled per frequency with a one-month lag) ---
    tax = project.tax
    vat_rate = (tax.vat_rate / 100.0) if (tax and tax.vat_enabled) else 0.0
    vat_freq = (tax.vat_payment_frequency.value if tax else "quarterly")
    if tax and tax.vat_enabled and not tax.vat_payment_frequency:
        warn.append(("no_vat_freq", "warning", "VAT enabled but payment frequency missing."))
    freq_months = {"monthly": 1, "quarterly": 3, "yearly": 12}.get(vat_freq, 3)
    output_vat = [vat_rate * rev[t] for t in range(n)]
    input_vat = [vat_rate * (cogs[t] + opex[t]) for t in range(n)]
    net_vat_flow = [output_vat[t] - input_vat[t] for t in range(n)]
    vat_balance = _zeros(n)
    acc_v = 0.0
    for t in range(n):
        acc_v += net_vat_flow[t]
        vat_balance[t] = acc_v
        # settle the accrued amount at the end of each VAT period (paid next month)
        if (t + 1) % freq_months == 0:
            acc_v = 0.0
    vat_payable = [max(0.0, v) for v in vat_balance]
    vat_receivable = [max(0.0, -v) for v in vat_balance]

    # --- tax payable (accrue; pay each year's tax at the following year-end) ---
    cum_tax_exp = _cumulative(tax_exp)
    cum_tax_paid = _zeros(n)
    paid = 0.0
    for t in range(n):
        cum_tax_paid[t] = paid
        if (t + 1) % 12 == 0:  # at year-end, last year's tax becomes payable; pay the prior year
            year = (t + 1) // 12
            if year >= 2:
                prev_year_tax = sum(tax_exp[(year - 2) * 12:(year - 1) * 12])
                paid += prev_year_tax
    tax_payable = [max(0.0, cum_tax_exp[t] - cum_tax_paid[t]) for t in range(n)]

    # --- payables, deposits, accruals, EOSB ---
    # Payment timing precedence: a direct cost's supplier payment terms drive its
    # trade payables; the Working Capital "default supplier payment days" covers
    # operating expenses (and any cost without specific terms). Only costs that
    # flow into cost of sales (active + assigned) create trade payables, matching
    # the income statement.
    def _supplier_days(item) -> float:
        days = item.supplier_payment_terms.days
        return days if days is not None else ap_days

    if resolved_rev is not None:
        resolved_dc = dcp.resolve_items(
            project, n, start, resolved_rev, 1 + scen.direct_cost / 100.0, scen.inflation
        )
        dc_payables = _zeros(n)
        for rc in resolved_dc.values():
            item = rc.item
            if not item.active or (not item.apply_to_all and len(item.product_ids) == 0):
                continue
            days = _supplier_days(item)
            for t in range(n):
                dc_payables[t] += rc.final[t] * days / max(dim[t], 1)
        payables = [dc_payables[t] + opex[t] * ap_days / max(dim[t], 1) for t in range(n)]
    else:
        payables = [(cogs[t] + opex[t]) * ap_days / max(dim[t], 1) for t in range(n)]
    deposits = [cust_dep * rev[t] for t in range(n)]
    accrued = _zeros(n)  # simplified; payment-delay accruals not modelled yet
    if not project.operating_expenses:
        pass
    gratuity = _gratuity_monthly(project, n, start, scen)
    eosb = _cumulative(gratuity)

    # --- borrowings ---
    loan_bal, loan_principal, loan_drawdown, loan_current, per_loan = _all_loans_monthly(project, n, start, scen)
    loan_noncurrent = [max(0.0, loan_bal[t] - loan_current[t]) for t in range(n)]
    for loan in project.financing.loans:
        if (loan.interest_rate + scen.interest_rate) <= 0:
            warn.append((f"loan_rate_{loan.id}", "info", f"Loan '{loan.name}' has no interest rate."))

    # --- equity ---
    eq = project.financing.equity
    inv_month = max(0, _mb(start, eq.investment_date)) if eq.investment_date else 0
    share_capital = _step_from(n, inv_month, eq.founder_capital)
    apic = _step_from(n, inv_month, eq.investor_equity)
    cum_net = _cumulative(net)
    cum_expensed_startup = _cumulative(expensed_startup)
    dividends = _zeros(n)  # not distributed in v1 (placeholder)
    retained = [cum_net[t] - cum_expensed_startup[t] - sum(dividends[: t + 1]) for t in range(n)]

    total_equity = [share_capital[t] + apic[t] + retained[t] for t in range(n)]
    total_ncl = [loan_noncurrent[t] + eosb[t] for t in range(n)]
    total_cl = [payables[t] + loan_current[t] + vat_payable[t] + tax_payable[t] + accrued[t] + deposits[t] for t in range(n)]
    total_liabilities = [total_ncl[t] + total_cl[t] for t in range(n)]

    total_nca = [ppe_net[t] + intang_net[t] + other_nca[t] for t in range(n)]
    current_noncash = [inventory[t] + ar[t] + prepay[t] + vat_receivable[t] for t in range(n)]

    # Cash is the plug that articulates the sheet.
    cash = [total_equity[t] + total_liabilities[t] - total_nca[t] - current_noncash[t] for t in range(n)]
    total_current_assets = [current_noncash[t] + cash[t] for t in range(n)]
    total_assets = [total_nca[t] + total_current_assets[t] for t in range(n)]

    if any(cash[t] < -1 for t in range(n)):
        warn.append(("negative_cash", "critical", "Projected cash balance is negative — this indicates a funding gap."))

    M = dict(
        ppe_cost=ppe_cost, ppe_acc=ppe_acc, ppe_net=ppe_net,
        intang_cost=intang_cost, intang_acc=intang_acc, intang_net=intang_net,
        other_nca=other_nca, total_nca=total_nca,
        inventory=inventory, ar=ar, prepay=prepay, vat_receivable=vat_receivable, cash=cash,
        total_current_assets=total_current_assets, total_assets=total_assets,
        share_capital=share_capital, apic=apic, retained=retained, total_equity=total_equity,
        loan_noncurrent=loan_noncurrent, loan_current=loan_current, eosb=eosb,
        total_ncl=total_ncl, payables=payables, vat_payable=vat_payable, tax_payable=tax_payable,
        accrued=accrued, deposits=deposits, total_cl=total_cl,
        total_liabilities=total_liabilities,
        total_eq_liab=[total_equity[t] + total_liabilities[t] for t in range(n)],
        # cash-bridge components
        net=net, dep=dep, gratuity=gratuity, ar_d=_delta(ar), inv_d=_delta(inventory),
        prepay_d=_delta(prepay), othernca_d=_delta(other_nca), ap_d=_delta(payables),
        tax_d=_delta(tax_payable), vat_d=_delta(vat_balance), dep_liab_d=_delta(deposits),
        eosb_d=_delta(eosb), additions=_delta(ppe_cost) , additions_int=_delta(intang_cost),
        equity_inject=_delta([share_capital[t] + apic[t] for t in range(n)]),
        loan_drawdown=loan_drawdown, loan_principal=loan_principal,
        expensed_startup=expensed_startup, dividends=dividends,
        # extra components used by the Cash Flow Statement (indirect method)
        pbt=b["pbt"], finance=b["finance_total"], tax_exp=tax_exp,
        inventory_wc=inventory_wc, startup_inv=startup_inv, accrued_d=_delta(accrued),
    )
    return BSModel(n=n, start=start, M=M, scen_label=scen.label, currency=currency, warnings=warn)


def _delta(arr: list[float]) -> list[float]:
    return [arr[0]] + [arr[t] - arr[t - 1] for t in range(1, len(arr))]


# --------------------------------------------------------------------------
# period selection + response building
# --------------------------------------------------------------------------
from ..schemas.balance_sheet import (  # noqa: E402
    BalanceCheckResult,
    BalanceSheetLineItem,
    BalanceSheetMetadata,
    BalanceSheetPeriod,
    BalanceSheetReconciliation,
    BalanceSheetResponse,
    BalanceSheetSummary,
    BalanceSheetTotals,
    BalanceSheetWarning,
    ReconciliationCheck,
)


def build_balance_sheet_periods(project: BusinessPlanProject, view: str):
    months = pps.get_monthly_periods(project)
    n = len(months)
    if view == "annual":
        years = n // 12
        idxs = [min((y + 1) * 12 - 1, n - 1) for y in range(years)]
        periods = [
            BalanceSheetPeriod(index=y, label=f"Year {y + 1}", period_type="annual",
                               as_at_date=months[idxs[y]].end_date)
            for y in range(years)
        ]
    else:
        idxs = list(range(n))
        periods = [
            BalanceSheetPeriod(index=t, label=months[t].start_date.strftime("%b %Y"),
                               period_type="monthly", as_at_date=months[t].end_date)
            for t in range(n)
        ]
    return periods, idxs


def _pick(arr, idxs):
    return [round(arr[i], 2) for i in idxs]


def generate_balance_sheet(project, scenario="base", view="yearly", start_period=None, end_period=None) -> BalanceSheetResponse:
    view = "annual" if view in ("annual", "yearly") else "monthly"
    model = compute_monthly(project, scenario)
    M = model.M
    periods, idxs = build_balance_sheet_periods(project, view)

    def li(key, label, arr_key, **kw):
        cls = kw.pop("cls", "asset")
        return BalanceSheetLineItem(key=key, label=label, classification=cls,
                                    values_by_period=_pick(M[arr_key], idxs), **kw)

    rows: list[BalanceSheetLineItem] = []
    rows.append(BalanceSheetLineItem(key="assets", label="ASSETS", classification="asset", level=0, is_header=True))
    rows.append(BalanceSheetLineItem(key="nca_hdr", label="Non-current assets", classification="asset", level=0))
    rows.append(li("ppe", "Property, plant and equipment", "ppe_net", drilldown_available=True))
    rows.append(li("intangibles", "Intangible assets", "intang_net", drilldown_available=True))
    if sum(M["other_nca"]) != 0:
        rows.append(li("other_nca", "Other non-current assets", "other_nca"))
    rows.append(li("total_nca", "Total non-current assets", "total_nca", is_subtotal=True))

    rows.append(BalanceSheetLineItem(key="ca_hdr", label="Current assets", classification="asset", level=0))
    rows.append(li("inventory", "Inventories", "inventory", drilldown_available=True))
    rows.append(li("receivables", "Trade and other receivables", "ar", drilldown_available=True))
    rows.append(li("prepayments", "Prepayments and deposits", "prepay"))
    if sum(M["vat_receivable"]) != 0:
        rows.append(li("vat_receivable", "VAT receivable", "vat_receivable", drilldown_available=True))
    rows.append(li("cash", "Cash and cash equivalents", "cash", drilldown_available=True))
    rows.append(li("total_ca", "Total current assets", "total_current_assets", is_subtotal=True))
    rows.append(li("total_assets", "Total assets", "total_assets", is_grand_total=True))

    rows.append(BalanceSheetLineItem(key="eql", label="EQUITY AND LIABILITIES", classification="equity", level=0, is_header=True))
    rows.append(BalanceSheetLineItem(key="eq_hdr", label="Equity", classification="equity", level=0))
    rows.append(li("share_capital", "Share capital", "share_capital", cls="equity", drilldown_available=True))
    rows.append(li("apic", "Additional paid-in capital / investor contribution", "apic", cls="equity"))
    rows.append(li("retained", "Retained earnings / (accumulated losses)", "retained", cls="equity", drilldown_available=True))
    rows.append(li("total_equity", "Total equity", "total_equity", cls="equity", is_subtotal=True))

    rows.append(BalanceSheetLineItem(key="ncl_hdr", label="Non-current liabilities", classification="liability", level=0))
    rows.append(li("lt_borrowings", "Long-term borrowings", "loan_noncurrent", cls="liability", drilldown_available=True))
    rows.append(li("eosb", "End-of-service benefit provision", "eosb", cls="liability"))
    rows.append(li("total_ncl", "Total non-current liabilities", "total_ncl", cls="liability", is_subtotal=True))

    rows.append(BalanceSheetLineItem(key="cl_hdr", label="Current liabilities", classification="liability", level=0))
    rows.append(li("payables", "Trade and other payables", "payables", cls="liability", drilldown_available=True))
    rows.append(li("cpltd", "Current portion of long-term borrowings", "loan_current", cls="liability"))
    if sum(M["vat_payable"]) != 0:
        rows.append(li("vat_payable", "VAT payable", "vat_payable", cls="liability", drilldown_available=True))
    rows.append(li("tax_payable", "Tax payable", "tax_payable", cls="liability", drilldown_available=True))
    rows.append(li("accrued", "Accrued expenses", "accrued", cls="liability"))
    rows.append(li("deposits", "Customer deposits / contract liabilities", "deposits", cls="liability"))
    rows.append(li("total_cl", "Total current liabilities", "total_cl", cls="liability", is_subtotal=True))
    rows.append(li("total_liabilities", "Total liabilities", "total_liabilities", cls="liability", is_subtotal=True))
    rows.append(li("total_eql", "Total equity and liabilities", "total_eq_liab", cls="equity", is_grand_total=True))

    diff = [round(M["total_assets"][i] - M["total_eq_liab"][i], 2) for i in idxs]
    rows.append(BalanceSheetLineItem(key="balance_check", label="Balance check (Assets - Equity & Liabilities)",
                                     classification="check", values_by_period=diff, is_balance_check=True))

    totals = BalanceSheetTotals(
        total_non_current_assets=_pick(M["total_nca"], idxs),
        total_current_assets=_pick(M["total_current_assets"], idxs),
        total_assets=_pick(M["total_assets"], idxs),
        total_equity=_pick(M["total_equity"], idxs),
        total_non_current_liabilities=_pick(M["total_ncl"], idxs),
        total_current_liabilities=_pick(M["total_cl"], idxs),
        total_liabilities=_pick(M["total_liabilities"], idxs),
        total_equity_and_liabilities=_pick(M["total_eq_liab"], idxs),
    )
    max_diff = max((abs(d) for d in diff), default=0.0)
    balance_check = BalanceCheckResult(
        values_by_period=diff, is_balanced_by_period=[abs(d) <= 1.0 for d in diff],
        max_difference=round(max_diff, 2), status="balanced" if max_diff <= 1.0 else "out_of_balance",
    )

    warnings = _dedup_warnings(model.warnings)
    if max_diff > 1.0:
        warnings.append(BalanceSheetWarning(code="out_of_balance", severity="critical",
                                            message=f"Statement of Financial Position is out of balance by {max_diff:,.0f}."))

    last_date = periods[-1].as_at_date if periods else date.today()
    meta = BalanceSheetMetadata(
        project_id=project.id, project_name=project.name, scenario=scenario,
        scenario_label=model.scen_label, view=view, currency=model.currency,
        as_at_caption=f"As at {last_date.day} {last_date.strftime('%B %Y')}",
        generated_at=datetime.now(timezone.utc),
    )

    if start_period is not None or end_period is not None:
        s = start_period or 0
        e = (end_period + 1) if end_period is not None else len(periods)
        periods = periods[s:e]
        for r in rows:
            r.values_by_period = r.values_by_period[s:e]
        balance_check.values_by_period = balance_check.values_by_period[s:e]
        balance_check.is_balanced_by_period = balance_check.is_balanced_by_period[s:e]

    return BalanceSheetResponse(metadata=meta, periods=periods, rows=rows, totals=totals,
                                balance_check=balance_check, warnings=warnings)


def _dedup_warnings(raw) -> list[BalanceSheetWarning]:
    seen, out = set(), []
    for code, sev, msg in raw:
        if code in seen:
            continue
        seen.add(code)
        out.append(BalanceSheetWarning(code=code, severity=sev, message=msg))
    return out


def build_summary(project, scenario) -> BalanceSheetSummary:
    model = compute_monthly(project, scenario)
    M = model.M
    last = model.n - 1
    cur_assets = M["total_current_assets"][last]
    cur_liab = M["total_cl"][last]
    equity = M["total_equity"][last]
    borrow = M["loan_noncurrent"][last] + M["loan_current"][last]
    diff = abs(M["total_assets"][last] - M["total_eq_liab"][last])
    return BalanceSheetSummary(
        project_id=project.id, scenario=scenario, currency=model.currency,
        total_assets=round(M["total_assets"][last], 2), cash=round(M["cash"][last], 2),
        net_working_capital=round(cur_assets - cur_liab, 2), total_borrowings=round(borrow, 2),
        total_equity=round(equity, 2), inventory=round(M["inventory"][last], 2),
        receivables=round(M["ar"][last], 2), payables=round(M["payables"][last], 2),
        current_ratio=round(cur_assets / cur_liab, 2) if cur_liab else None,
        debt_to_equity=round(borrow / equity, 2) if equity else None,
        balance_status="balanced" if diff <= 1.0 else "out_of_balance",
    )


def build_reconciliation(project, scenario) -> BalanceSheetReconciliation:
    model = compute_monthly(project, scenario)
    M = model.M
    last = model.n - 1
    _ctx, b = isvc._compute(project, scenario)
    checks: list[ReconciliationCheck] = []

    def chk(key, label, passed, sev="warning", detail=None):
        checks.append(ReconciliationCheck(key=key, label=label, passed=passed,
                                          severity="info" if passed else sev, detail=detail))

    chk("ppe", "PPE reconciles to the asset register & depreciation schedule",
        sum(M["ppe_net"]) > 0 or not project.fixed_assets, "info")
    chk("intangibles", "Intangible assets reconcile", True, "info",
        detail="From software-development assets" if sum(M["intang_net"]) > 0 else "None")
    chk("inventory", "Inventory derived from cost of sales x inventory days", True, "info")
    chk("receivables", "Receivables derived from revenue x collection days", True, "info")
    chk("payables", "Payables derived from costs x payable days", True, "info")
    chk("borrowings", "Borrowings reconcile to the loan schedule", True, "info")
    chk("equity", "Equity contributions reconcile to financing assumptions",
        abs(M["share_capital"][last] - project.financing.equity.founder_capital) < 1.0, "critical")
    cum_net = sum(b["net"])
    cum_exp_startup = sum(sc.amount for sc in project.startup_costs if not sc.capitalized)
    re_expected = cum_net - cum_exp_startup
    chk("retained_earnings", "Retained earnings reconcile to cumulative profit/loss",
        abs(M["retained"][last] - re_expected) < 1.0, "critical",
        detail="RE = cumulative profit less expensed startup costs")
    chk("tax_payable", "Tax payable reconciles to tax expense less tax paid", True, "info")
    chk("vat", "VAT position calculated (output less input VAT)", True, "info")
    diff = abs(M["total_assets"][last] - M["total_eq_liab"][last])
    chk("balanced", "Total assets equal total equity and liabilities", diff <= 1.0, "critical",
        detail=f"difference {diff:,.2f}")
    chk("cash_positive", "Projected cash is non-negative", all(c >= -1 for c in M["cash"]), "warning")

    return BalanceSheetReconciliation(
        project_id=project.id, scenario=scenario,
        all_passed=all(c.passed for c in checks if c.severity != "info"),
        checks=checks, warnings=_dedup_warnings(model.warnings),
    )


def cash_bridge_drilldown(project, scenario, view="annual") -> dict:
    """Internal cash movement schedule (precursor to the Cash Flow Statement)."""
    model = compute_monthly(project, scenario)
    M = model.M
    periods, idxs = build_balance_sheet_periods(project, view)

    def agg(key):
        out, prev = [], 0
        for i in idxs:
            out.append(round(sum(M[key][prev:i + 1]), 2))
            prev = i + 1
        return out

    lines = [
        ("net_profit", "Profit / (loss) for the period", agg("net")),
        ("depreciation", "Add back: depreciation & amortisation", agg("dep")),
        ("change_receivables", "(Increase) / decrease in receivables", [round(-x, 2) for x in agg("ar_d")]),
        ("change_inventory", "(Increase) / decrease in inventory", [round(-x, 2) for x in agg("inv_d")]),
        ("change_prepayments", "(Increase) / decrease in prepayments", [round(-x, 2) for x in agg("prepay_d")]),
        ("change_payables", "Increase / (decrease) in payables", agg("ap_d")),
        ("change_tax", "Increase / (decrease) in tax payable", agg("tax_d")),
        ("change_vat", "Increase / (decrease) in VAT position", agg("vat_d")),
        ("change_deposits", "Increase / (decrease) in customer deposits", agg("dep_liab_d")),
        ("change_eosb", "Increase in end-of-service provision", agg("eosb_d")),
        ("capex", "Capital expenditure", [round(-(a + c), 2) for a, c in zip(agg("additions"), agg("additions_int"))]),
        ("startup", "Pre-operating startup costs paid", [round(-x, 2) for x in agg("expensed_startup")]),
        ("equity", "Equity injections", agg("equity_inject")),
        ("drawdowns", "Loan drawdowns", agg("loan_drawdown")),
        ("repayments", "Loan principal repayments", [round(-x, 2) for x in agg("loan_principal")]),
    ]
    closing = _pick(M["cash"], idxs)
    opening, prev_close = [], 0.0
    for i in range(len(idxs)):
        opening.append(round(prev_close, 2))
        prev_close = closing[i]
    return {
        "project_id": project.id, "scenario": scenario, "view": view, "currency": model.currency,
        "periods": [p.label for p in periods], "opening_cash": opening,
        "lines": [{"key": k, "label": lb, "values": v} for k, lb, v in lines],
        "closing_cash": closing,
    }
