"""IFRS-style Statement of Profit or Loss calculation engine.

Everything is derived from the stored assumptions — no figures are entered
manually. The engine computes a full monthly model, then aggregates to the
requested view (monthly / yearly) and applies the selected scenario's
adjustments at calculation time (base assumptions are never mutated).
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from dateutil.relativedelta import relativedelta

from ..models import BusinessPlanProject
from ..models.enums import (
    CostCalculationMethod as CM,
    DepreciationMethod,
    RepaymentType,
    ScenarioType,
)
from ..schemas.income_statement import (
    IncomeStatementLineItem,
    IncomeStatementMargins,
    IncomeStatementMetadata,
    IncomeStatementPeriod,
    IncomeStatementReconciliation,
    IncomeStatementResponse,
    IncomeStatementSection,
    IncomeStatementSummary,
    IncomeStatementTotals,
    IncomeStatementWarning,
    ReconciliationCheck,
)

# --------------------------------------------------------------------------
# Classification maps
# --------------------------------------------------------------------------
REVENUE_LINES: list[tuple[str, str, set[str]]] = [
    ("product_revenue", "Product revenue", {"unit_sales"}),
    ("service_revenue", "Service revenue", {"service_contract"}),
    ("subscription_revenue", "Subscription revenue", {"subscription"}),
    ("contract_revenue", "Contract revenue", {"project_based"}),
    ("commission_revenue", "Commission revenue", {"commission"}),
    ("licensing_revenue", "Licensing revenue", {"licensing"}),
    ("other_revenue", "Other revenue", {"other"}),
]
REVENUE_TYPE_TO_LINE = {rt: key for key, _, types in REVENUE_LINES for rt in types}

COGS_LINES: list[tuple[str, str]] = [
    ("product_direct_costs", "Product direct costs"),
    ("service_delivery_costs", "Service delivery costs"),
    ("subscription_direct_costs", "Subscription direct costs"),
    ("payment_gateway_fees", "Payment gateway fees"),
    ("sales_commissions", "Sales commissions"),
    ("warranty_provision", "Warranty provision"),
    ("import_customs_costs", "Import/customs costs"),
    ("other_direct_costs", "Other direct costs"),
]
COGS_CATEGORY_MAP = {
    "raw_materials": "product_direct_costs",
    "purchased_goods": "product_direct_costs",
    "manufacturing": "product_direct_costs",
    "packaging": "product_direct_costs",
    "direct_labor": "service_delivery_costs",
    "installation": "service_delivery_costs",
    "maintenance": "service_delivery_costs",
    "hosting": "subscription_direct_costs",
    "payment_gateway": "payment_gateway_fees",
    "sales_commission": "sales_commissions",
    "warranty": "warranty_provision",
    "customs": "import_customs_costs",
    "subcontractor": "other_direct_costs",
    "other": "other_direct_costs",
}

SELLING_CATEGORIES = {"marketing", "advertising"}
TECH_CATEGORIES = {"software"}

DEP_CATEGORY_LABEL = {
    "equipment": "Depreciation of equipment",
    "machinery": "Depreciation of equipment",
    "vehicle": "Depreciation of vehicles",
    "furniture": "Depreciation of furniture and fit-out",
    "computers": "Depreciation of computers",
    "software_development": "Amortisation of software development",
    "leasehold_improvements": "Depreciation of leasehold improvements",
}
DEFAULT_DEP_LABEL = "Depreciation of other assets"

DEPARTMENT_LABEL = {
    "management": "Management",
    "sales": "Sales",
    "marketing": "Marketing",
    "operations": "Operations",
    "finance": "Finance & administration",
    "administration": "Finance & administration",
    "technology": "Technology",
    "production": "Production",
    "customer_support": "Customer support",
    "other": "Other",
}


# --------------------------------------------------------------------------
# Scenario adjustment view (never mutates base assumptions)
# --------------------------------------------------------------------------
@dataclass
class ScenarioAdj:
    scenario_type: str = "base"
    label: str = "Base Case"
    sales_volume: float = 0.0
    selling_price: float = 0.0
    direct_cost: float = 0.0
    salary: float = 0.0
    rent: float = 0.0
    marketing: float = 0.0
    customer_growth: float = 0.0
    interest_rate: float = 0.0
    tax_rate: float = 0.0
    inflation: float = 0.0


def _resolve_scenario(project: BusinessPlanProject, scenario: str):
    """Find the saved scenario for a request identifier.

    Named scenarios are selected by id (the primary path); a legacy type string
    ("base"/"conservative"/...) still matches by type; and when the identifier
    doesn't match anything we fall back to the project's default scenario (else
    None → a synthetic base case). This is the single point that makes the whole
    statement engine scenario-id aware.
    """
    scenarios = project.scenarios
    for s in scenarios:                       # by id (named scenarios)
        if s.id == scenario:
            return s
    for s in scenarios:                       # by legacy type string
        if s.scenario_type.value == scenario:
            return s
    for s in scenarios:                       # the project default
        if getattr(s, "is_default", False):
            return s
    return None


def _scenario_adj(project: BusinessPlanProject, scenario: str) -> ScenarioAdj:
    s = _resolve_scenario(project, scenario)
    if s is not None:
        stype = s.scenario_type.value
        return ScenarioAdj(
            scenario_type=stype,
            label=(s.name or s.label or stype.title()),
            sales_volume=s.sales_volume_adjustment,
            selling_price=s.selling_price_adjustment,
            direct_cost=s.direct_cost_adjustment,
            salary=s.salary_adjustment,
            rent=s.rent_adjustment,
            marketing=s.marketing_adjustment,
            customer_growth=s.customer_growth_adjustment,
            interest_rate=s.interest_rate_adjustment,
            tax_rate=s.tax_rate_adjustment,
            inflation=s.inflation_adjustment,
        )
    label = {"base": "Base Case", "conservative": "Conservative Case", "optimistic": "Optimistic Case"}.get(scenario, scenario.title())
    return ScenarioAdj(scenario_type=scenario, label=label)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _months_between(start: date, other: date) -> int:
    return (other.year - start.year) * 12 + (other.month - start.month)


def _zeros(n: int) -> list[float]:
    return [0.0] * n


def _add(a: list[float], b: list[float]) -> list[float]:
    return [x + y for x, y in zip(a, b)]


def _sub(a: list[float], b: list[float]) -> list[float]:
    return [x - y for x, y in zip(a, b)]


def _round(a: list[float]) -> list[float]:
    return [round(x, 2) for x in a]


@dataclass
class Ctx:
    project: BusinessPlanProject
    scen: ScenarioAdj
    n: int                       # number of months
    start: date
    years: int
    warnings: list[IncomeStatementWarning] = field(default_factory=list)

    def warn(self, code: str, severity: str, message: str) -> None:
        if not any(w.code == code for w in self.warnings):
            self.warnings.append(IncomeStatementWarning(code=code, severity=severity, message=message))

    def year_index(self, month_idx: int) -> int:
        return month_idx // 12


# --------------------------------------------------------------------------
# Periods
# --------------------------------------------------------------------------
def build_projection_periods(project: BusinessPlanProject) -> tuple[date, int, int]:
    """Return (start_date, years, n_months)."""
    setup = project.setup
    if setup and setup.projection_start_date and setup.projection_period:
        start = setup.projection_start_date
        years = setup.projection_period.years
    else:
        start = date(date.today().year, 1, 1)
        years = 5
    return start, years, years * 12


def _monthly_periods(start: date, n: int) -> list[IncomeStatementPeriod]:
    out = []
    for i in range(n):
        d = start + relativedelta(months=i)
        last_day = calendar.monthrange(d.year, d.month)[1]
        out.append(IncomeStatementPeriod(
            index=i, label=d.strftime("%b %Y"), period_type="month",
            year_index=i // 12, month=d.month, year=d.year,
            start_date=date(d.year, d.month, 1), end_date=date(d.year, d.month, last_day),
        ))
    return out


def _yearly_periods(start: date, years: int) -> list[IncomeStatementPeriod]:
    out = []
    for y in range(years):
        first = start + relativedelta(months=y * 12)
        last = start + relativedelta(months=(y + 1) * 12 - 1)
        last_day = calendar.monthrange(last.year, last.month)[1]
        out.append(IncomeStatementPeriod(
            index=y, label=f"Year {y + 1}", period_type="year", year_index=y,
            month=None, year=first.year,
            start_date=date(first.year, first.month, 1), end_date=date(last.year, last.month, last_day),
        ))
    return out


# --------------------------------------------------------------------------
# Product revenue drivers
# --------------------------------------------------------------------------
@dataclass
class ProductModel:
    product: object
    ra: object
    units: list[float]
    price: list[float]
    revenue: list[float]
    customers: list[float]
    purchased_unit: list[float]   # per-unit purchased (fixed_per_unit) cost base


def _growth_monthly(ra, scen: ScenarioAdj) -> float:
    if ra is None:
        return 0.0
    if ra.monthly_growth_rate is not None:
        base = ra.monthly_growth_rate / 100.0
    else:
        annual = (ra.annual_growth_rate or 0.0)
        base = (1 + annual / 100.0) ** (1 / 12) - 1
    # scenario customer-growth adjustment scales the growth rate
    return base * (1 + scen.customer_growth / 100.0)


def _seasonality_factor(ra, month: int) -> float:
    if ra is None or not ra.seasonality_enabled:
        return 1.0
    for s in ra.seasonality:
        if s.month == month:
            return s.adjustment_percent / 100.0
    return 1.0


def calculate_revenue(ctx: Ctx) -> dict[str, ProductModel]:
    """Read net revenue from the per-stream monthly projection schedule.

    Scenario sales-volume / selling-price adjustments are applied at calc time;
    the stored projection quantities remain the base source of truth.
    """
    from . import revenue_projection_service as rps

    project, scen, n, start = ctx.project, ctx.scen, ctx.n, ctx.start
    vol_factor = 1 + scen.sales_volume / 100.0
    price_factor = 1 + scen.selling_price / 100.0
    # Per-product resolution — the source of truth for receivables / VAT / cash
    # flow and for the legacy P&L path (income statement revenue is gated to use
    # revenue streams when present, in _compute).
    resolved = rps.resolve_streams(project, n, start, vol_factor, price_factor)
    ctx._resolved_rev = resolved  # type: ignore[attr-defined]

    models: dict[str, ProductModel] = {}
    for pid, rs in resolved.items():
        if not rs.product.active:
            ctx.warn("inactive_product", "info", f"'{rs.product.name}' is inactive and excluded from revenue.")
        elif sum(rs.net) == 0:
            ctx.warn(f"rev_no_projection_{pid}", "warning",
                     f"Revenue stream '{rs.product.name}' has no projection values.")
        models[pid] = ProductModel(rs.product, rs.ra, rs.quantity, rs.price, rs.net, rs.customers, _zeros(n))
    return models


# --------------------------------------------------------------------------
# Direct costs
# --------------------------------------------------------------------------
def _assoc_product_ids(item, all_ids: list[str]) -> list[str]:
    if item.apply_to_all:
        return all_ids
    return list(item.product_ids)


def _amount_at(amount: float, infl_rate: float, scen: ScenarioAdj, year_idx: int, waste: float = 0.0) -> float:
    rate = (infl_rate + scen.inflation) / 100.0
    return amount * ((1 + rate) ** year_idx) * (1 + waste / 100.0)


def calculate_direct_costs(ctx: Ctx, products: dict[str, ProductModel]) -> dict[str, list[float]]:
    """Read final cost-of-sales amounts from the direct-cost projection schedule."""
    from . import direct_cost_projection_service as dcp

    project, scen, n, start = ctx.project, ctx.scen, ctx.n, ctx.start
    # Direct costs associate with the unified revenue sources — revenue streams
    # when the project has them, else legacy products. This is intentionally
    # separate from ctx._resolved_rev (per-product, used by receivables/VAT).
    from . import revenue_projection_service as rps
    resolved_rev = rps.resolve_revenue_sources(
        project, n, start,
        1 + scen.sales_volume / 100.0, 1 + scen.selling_price / 100.0)

    resolved = dcp.resolve_items(project, n, start, resolved_rev,
                                 1 + scen.direct_cost / 100.0, scen.inflation)
    lines = {key: _zeros(n) for key, _ in COGS_LINES}
    drill: dict[str, list[IncomeStatementLineItem]] = {key: [] for key, _ in COGS_LINES}

    if any((not c.apply_to_all and len(c.product_ids) == 0) for c in project.direct_costs):
        ctx.warn("unassigned_direct_cost", "warning",
                 "One or more direct cost items are unassigned and excluded from cost of sales.")

    has_assigned = False
    for cid, rc in resolved.items():
        item = rc.item
        if not item.active or (not item.apply_to_all and len(item.product_ids) == 0):
            continue
        has_assigned = True
        if sum(rc.final) == 0:
            ctx.warn(f"dc_no_projection_{cid}", "info",
                     f"Direct cost '{item.name}' has no projection values.")
        line_key = COGS_CATEGORY_MAP.get(item.category.value, "other_direct_costs")
        lines[line_key] = _add(lines[line_key], rc.final)
        drill[line_key].append(IncomeStatementLineItem(
            key=f"dc_{cid}", label=item.name, classification="cost_of_sales",
            values_by_period=rc.final, total=sum(rc.final), drilldown_available=False,
            note=item.calculation_method.value.replace("_", " "),
        ))

    if not has_assigned and project.direct_costs:
        ctx.warn("no_assigned_direct_costs", "critical",
                 "No direct costs are assigned to a revenue stream — cost of sales is zero.")
    if not project.direct_costs:
        ctx.warn("no_direct_costs", "critical", "No direct costs configured — cost of sales is zero.")

    ctx._cogs_drill = drill  # type: ignore[attr-defined]
    return lines


# --------------------------------------------------------------------------
# Operating expenses
# --------------------------------------------------------------------------
FREQ_FACTOR = {"monthly": 1.0, "quarterly": 1 / 3, "yearly": 1 / 12, "one_time": 0.0}


def calculate_operating_expenses(ctx: Ctx) -> dict[str, list[float]]:
    """Read final operating-expense amounts from the expense projection schedule."""
    from . import operating_expense_projection_service as oep

    project, scen, n, start = ctx.project, ctx.scen, ctx.n, ctx.start
    resolved = oep.resolve_items(project, n, start, scen.inflation,
                                 1 + scen.rent / 100.0, 1 + scen.marketing / 100.0)
    buckets = {"selling": _zeros(n), "admin": _zeros(n), "technology": _zeros(n)}
    drill: dict[str, list[IncomeStatementLineItem]] = {"selling": [], "admin": [], "technology": []}
    cls_to_bucket = {
        "selling_distribution": "selling",
        "administrative": "admin",
        "technology_platform": "technology",
    }

    for eid, re in resolved.items():
        cls_key, _ = oep.ifrs_classification(re.item.category.value)
        bucket = cls_to_bucket[cls_key]
        buckets[bucket] = _add(buckets[bucket], re.final)
        if sum(re.final) == 0:
            ctx.warn(f"opex_no_projection_{eid}", "info",
                     f"Expense '{re.item.name}' has no projection values.")
        drill[bucket].append(IncomeStatementLineItem(
            key=f"opex_{eid}", label=re.item.name, classification="operating_expense",
            values_by_period=re.final, total=sum(re.final),
            note=f"{re.item.category.value} · {re.item.frequency.value}",
        ))

    if not project.operating_expenses:
        ctx.warn("no_opex", "info", "No operating expenses entered.")
    ctx._opex_drill = drill  # type: ignore[attr-defined]
    return buckets


# --------------------------------------------------------------------------
# Staff costs
# --------------------------------------------------------------------------
def calculate_staff_costs(ctx: Ctx) -> tuple[list[float], list[IncomeStatementLineItem]]:
    project, scen, n, start = ctx.project, ctx.scen, ctx.n, ctx.start
    total = _zeros(n)
    by_dept: dict[str, list[float]] = {}
    dept_roles: dict[str, list[IncomeStatementLineItem]] = {}

    # Avoid double-counting commissions that already exist as a direct cost.
    commission_in_cogs = any(
        c.active and c.category.value == "sales_commission" for c in project.direct_costs
    )
    if commission_in_cogs:
        ctx.warn("commission_in_cogs", "info",
                 "Sales commissions are recognised in cost of sales; excluded from staff costs to avoid double-counting.")

    scen_mult = 1 + scen.salary / 100.0

    # Employer social security: a role may override the rate; otherwise the
    # global Tax & Regulatory default applies. Single source of truth — the rate
    # is not asked for twice.
    global_ss_rate = (project.tax.employer_social_security_rate if project.tax else 0.0) or 0.0

    for role in project.staffing:
        if not role.active:
            continue
        hire_idx = max(0, _months_between(start, role.hiring_start_date)) if role.hiring_start_date else 0
        num = role.number_of_employees
        ss_rate = role.employer_social_security_percent
        if ss_rate is None:
            ss_rate = global_ss_rate
        arr = _zeros(n)
        for t in range(hire_idx, n):
            yi = ctx.year_index(t)
            base = role.monthly_salary * ((1 + role.annual_increase_percent / 100.0) ** yi) * num
            benefits = base * role.benefits_percent / 100.0
            health = role.health_insurance_amount * num / 12.0
            visa = role.visa_permit_cost * num / 12.0
            bonus = base * role.bonus_percent / 100.0 + role.bonus_amount * num / 12.0
            emp_ss = base * ss_rate / 100.0
            gratuity = base * role.gratuity_percent / 100.0
            commission = 0.0 if commission_in_cogs else base * role.sales_commission_percent / 100.0
            arr[t] = (base + benefits + health + visa + bonus + emp_ss + gratuity + commission) * scen_mult

        dept = DEPARTMENT_LABEL.get(role.department.value, "Other")
        by_dept.setdefault(dept, _zeros(n))
        by_dept[dept] = _add(by_dept[dept], arr)
        dept_roles.setdefault(dept, []).append(IncomeStatementLineItem(
            key=f"staff_{role.id}", label=f"{role.job_title} ({num})", classification="staff_cost",
            values_by_period=arr, total=sum(arr),
        ))
        total = _add(total, arr)

    if not project.staffing:
        ctx.warn("no_staff", "info", "No staffing roles entered — staff costs are zero.")

    children = []
    for dept in sorted(by_dept):
        children.append(IncomeStatementLineItem(
            key=f"staff_dept_{dept}", label=dept, classification="staff_cost",
            values_by_period=by_dept[dept], total=sum(by_dept[dept]),
            drilldown_available=True, children=dept_roles.get(dept, []),
        ))
    return total, children


# --------------------------------------------------------------------------
# Depreciation & amortisation
# --------------------------------------------------------------------------
def calculate_depreciation(ctx: Ctx) -> tuple[list[float], list[IncomeStatementLineItem]]:
    """Depreciation & amortisation, sourced from the fixed-asset service so the
    statement always agrees with the CapEx depreciation schedule."""
    from . import fixed_asset_service as fas

    project, n, start = ctx.project, ctx.n, ctx.start
    by_label, per_asset = fas.depreciation_by_category(project, n, start)

    if not project.fixed_assets:
        ctx.warn("no_assets", "info", "No fixed assets entered. Depreciation and amortisation is zero.")
    if any(a.depreciation_method == DepreciationMethod.REDUCING_BALANCE for a in project.fixed_assets):
        ctx.warn("reducing_balance", "info",
                 "Reducing-balance assets are depreciated straight-line in this version.")

    drill: dict[str, list[IncomeStatementLineItem]] = {}
    for asset, arr in per_asset:
        label = fas.CATEGORY_DEP_LABEL.get(asset.category.value, fas.DEFAULT_DEP_LABEL)
        drill.setdefault(label, []).append(IncomeStatementLineItem(
            key=f"dep_{asset.id}", label=asset.name, classification="depreciation",
            values_by_period=arr, total=sum(arr),
            note=f"{asset.category.value} · life {asset.useful_life_years}y",
        ))

    children: list[IncomeStatementLineItem] = []
    total = _zeros(n)
    for label, arr in by_label.items():
        children.append(IncomeStatementLineItem(
            key=f"dep_line_{label}", label=label, classification="depreciation",
            values_by_period=arr, total=sum(arr),
            drilldown_available=True, children=drill.get(label, []),
        ))
        total = _add(total, arr)
    return total, children


# --------------------------------------------------------------------------
# Finance costs
# --------------------------------------------------------------------------
def _loan_schedule(loan, n: int, start_offset: int, rate_pct: float) -> tuple[list[float], list[float]]:
    """Return (interest_array, arrangement_fee_array) of length n."""
    interest = _zeros(n)
    fee = _zeros(n)
    term = max(1, loan.repayment_period_months)
    grace = min(loan.grace_period_months, term)
    r = rate_pct / 100.0 / 12.0
    bal = loan.amount

    fee_monthly = (loan.arrangement_fee or 0.0) / term
    amort_months = max(1, term - grace)
    # Equal-installment annuity payment (computed once principal repayment begins).
    if r > 0:
        annuity = bal * r / (1 - (1 + r) ** (-amort_months))
    else:
        annuity = bal / amort_months
    straight_principal = bal / amort_months

    for k in range(term):
        t = start_offset + k
        intr = bal * r
        if loan.repayment_type == RepaymentType.BULLET:
            principal = bal if k == term - 1 else 0.0
        elif k < grace:
            principal = 0.0
        elif loan.repayment_type == RepaymentType.EQUAL_INSTALLMENTS:
            principal = annuity - intr
        else:  # INTEREST_ONLY then principal, and CUSTOM placeholder
            principal = straight_principal
        if 0 <= t < n:
            interest[t] = intr
            fee[t] = fee_monthly
        bal = max(0.0, bal - principal)
    return interest, fee


def calculate_finance_costs(ctx: Ctx) -> tuple[list[float], list[IncomeStatementLineItem]]:
    project, scen, n, start = ctx.project, ctx.scen, ctx.n, ctx.start
    total = _zeros(n)
    children = []
    for loan in project.financing.loans:
        offset = max(0, _months_between(start, loan.drawdown_date)) if loan.drawdown_date else 0
        rate = loan.interest_rate + scen.interest_rate
        if rate <= 0:
            ctx.warn(f"loan_no_rate_{loan.id}", "warning",
                     f"Loan '{loan.name}' has no interest rate — finance cost from it is zero.")
        interest, fee = _loan_schedule(loan, n, offset, rate)
        combined = _add(interest, fee)
        total = _add(total, combined)
        children.append(IncomeStatementLineItem(
            key=f"loan_{loan.id}", label=loan.name, classification="finance_cost",
            values_by_period=combined, total=sum(combined), drilldown_available=True,
            note=f"{loan.repayment_type.value.replace('_', ' ')} · {rate:.2f}% p.a.",
            children=[
                IncomeStatementLineItem(key=f"loan_int_{loan.id}", label="Loan interest expense",
                                        classification="finance_cost", values_by_period=interest, total=sum(interest)),
                IncomeStatementLineItem(key=f"loan_fee_{loan.id}", label="Arrangement fee amortisation",
                                        classification="finance_cost", values_by_period=fee, total=sum(fee)),
            ],
        ))
    return total, children


# --------------------------------------------------------------------------
# Other income (grants)
# --------------------------------------------------------------------------
def calculate_other_income(ctx: Ctx) -> tuple[list[float], list[IncomeStatementLineItem]]:
    project, scen, n, start = ctx.project, ctx.scen, ctx.n, ctx.start
    arr = _zeros(n)
    children = []
    for grant in project.financing.grants:
        if grant.scenario_dependent and scen.scenario_type != ScenarioType.OPTIMISTIC.value:
            ctx.warn(f"grant_excluded_{grant.id}", "info",
                     f"Grant '{grant.name}' is scenario-dependent and recognised only in the optimistic case.")
            continue
        g = _zeros(n)
        if grant.expected_date:
            idx = _months_between(start, grant.expected_date)
            if 0 <= idx < n:
                g[idx] = grant.amount
        arr = _add(arr, g)
        children.append(IncomeStatementLineItem(
            key=f"grant_{grant.id}", label=f"{grant.name} (grant income)", classification="other_income",
            values_by_period=g, total=sum(g),
        ))
    return arr, children


# --------------------------------------------------------------------------
# Tax (annual basis with loss carryforward)
# --------------------------------------------------------------------------
def calculate_tax(ctx: Ctx, pbt: list[float]) -> list[float]:
    project, scen, n, years = ctx.project, ctx.scen, ctx.n, ctx.years
    tax = project.tax
    if tax is None or not tax.corporate_tax_enabled:
        ctx.warn("no_tax", "warning", "No corporate tax configured — income tax expense is zero.")
        return _zeros(n)
    rate = (tax.corporate_tax_rate + scen.tax_rate) / 100.0
    if rate <= 0:
        ctx.warn("no_tax_rate", "warning", "Corporate tax rate is zero — income tax expense is zero.")

    out = _zeros(n)
    carryforward = 0.0
    for y in range(years):
        months = range(y * 12, min(n, (y + 1) * 12))
        year_pbt = sum(pbt[t] for t in months)
        taxable = year_pbt
        if tax.tax_loss_carryforward_enabled and carryforward < 0:
            taxable += carryforward  # carryforward is negative
        if taxable > 0:
            year_tax = taxable * rate
            carryforward = 0.0
        else:
            year_tax = 0.0
            if tax.tax_loss_carryforward_enabled:
                carryforward = taxable  # negative pool carried forward
        # Allocate the year's tax across months with positive PBT (else evenly).
        pos = [pbt[t] for t in months if pbt[t] > 0]
        pos_sum = sum(pos)
        for t in months:
            if pos_sum > 0:
                out[t] = year_tax * (pbt[t] / pos_sum) if pbt[t] > 0 else 0.0
            else:
                out[t] = year_tax / max(1, len(list(months)))
    return out


# --------------------------------------------------------------------------
# View transform
# --------------------------------------------------------------------------
def _aggregate_to_years(arr: list[float], years: int) -> list[float]:
    return [round(sum(arr[y * 12:(y + 1) * 12]), 2) for y in range(years)]


def _transform_tree(item: IncomeStatementLineItem, view: str, years: int) -> IncomeStatementLineItem:
    vals = item.values_by_period if view == "monthly" else _aggregate_to_years(item.values_by_period, years)
    vals = _round(vals)
    return IncomeStatementLineItem(
        key=item.key, label=item.label, classification=item.classification,
        values_by_period=vals, total=round(sum(vals), 2),
        is_subtotal=item.is_subtotal, is_grand_total=item.is_grand_total,
        display_order=item.display_order, drilldown_available=item.drilldown_available,
        note=item.note, children=[_transform_tree(c, view, years) for c in item.children],
    )


# --------------------------------------------------------------------------
# Main entry
# --------------------------------------------------------------------------
def _compute(project: BusinessPlanProject, scenario: str) -> tuple[Ctx, dict]:
    start, years, n = build_projection_periods(project)
    ctx = Ctx(project=project, scen=_scenario_adj(project, scenario), n=n, start=start, years=years)

    products = calculate_revenue(ctx)

    # Revenue lines by IFRS type
    rev_lines: dict[str, list[float]] = {key: _zeros(n) for key, _, _ in REVENUE_LINES}
    rev_children: dict[str, list[IncomeStatementLineItem]] = {key: [] for key, _, _ in REVENUE_LINES}
    # Revenue Streams (the wizard) are the primary revenue source. When a project
    # has any active revenue stream, revenue is taken *entirely* from the streams
    # and the legacy per-product revenue is NOT added — this prevents
    # double-counting for migrated projects. Projects with no revenue streams
    # fall back to the legacy product/revenue model exactly as before. (The
    # per-product `products` model is still resolved above because direct costs
    # depend on it — e.g. per-customer, per-contract, and percent-of-revenue.)
    from . import revenue_stream_service as rss
    active_streams = [s for s in getattr(project, "revenue_streams", [])
                      if getattr(s, "active", True)]

    if not active_streams:
        for pid, pm in products.items():
            key = REVENUE_TYPE_TO_LINE.get(pm.product.revenue_type.value, "other_revenue")
            rev_lines[key] = _add(rev_lines[key], pm.revenue)
            rev_children[key].append(IncomeStatementLineItem(
                key=f"rev_{pid}", label=pm.product.name, classification="revenue",
                values_by_period=pm.revenue, total=sum(pm.revenue),
                note=pm.product.revenue_type.value.replace("_", " "),
            ))

    # Each stream maps to an IFRS line and is scaled by the scenario sales-volume
    # adjustment like product revenue.
    vol_factor = 1 + ctx.scen.sales_volume / 100.0
    for stream in active_streams:
        monthly = [round(v * vol_factor, 4) for v in rss.compute_monthly(stream, n)]
        key = rss.IFRS_LINE.get(stream.stream_type.value, "other_revenue")
        rev_lines[key] = _add(rev_lines[key], monthly)
        rev_children[key].append(IncomeStatementLineItem(
            key=f"rs_{stream.id}", label=stream.name, classification="revenue",
            values_by_period=monthly, total=sum(monthly),
            note="revenue stream · " + stream.stream_type.value.replace("_", " "),
        ))

    total_revenue = _zeros(n)
    for key in rev_lines:
        total_revenue = _add(total_revenue, rev_lines[key])

    # Cost of sales
    cogs_lines = calculate_direct_costs(ctx, products)
    cogs_drill = getattr(ctx, "_cogs_drill", {})
    total_cogs = _zeros(n)
    for key in cogs_lines:
        total_cogs = _add(total_cogs, cogs_lines[key])
    gross_profit = _sub(total_revenue, total_cogs)

    # Other income
    other_income, other_children = calculate_other_income(ctx)

    # Operating expenses
    opex = calculate_operating_expenses(ctx)
    opex_drill = getattr(ctx, "_opex_drill", {})
    staff_total, staff_children = calculate_staff_costs(ctx)
    dep_total, dep_children = calculate_depreciation(ctx)
    total_opex = opex["selling"]
    for arr in (opex["admin"], staff_total, opex["technology"], dep_total):
        total_opex = _add(total_opex, arr)

    operating_profit = _sub(_add(gross_profit, other_income), total_opex)
    ebitda = _add(operating_profit, dep_total)

    # Finance + tax
    finance_total, finance_children = calculate_finance_costs(ctx)
    pbt = _sub(operating_profit, finance_total)
    tax_arr = calculate_tax(ctx, pbt)
    net = _sub(pbt, tax_arr)

    bundle = dict(
        n=n, start=start, years=years, products=products,
        rev_lines=rev_lines, rev_children=rev_children, total_revenue=total_revenue,
        cogs_lines=cogs_lines, cogs_drill=cogs_drill, total_cogs=total_cogs, gross_profit=gross_profit,
        other_income=other_income, other_children=other_children,
        opex=opex, opex_drill=opex_drill, staff_total=staff_total, staff_children=staff_children,
        dep_total=dep_total, dep_children=dep_children, total_opex=total_opex,
        operating_profit=operating_profit, ebitda=ebitda,
        finance_total=finance_total, finance_children=finance_children,
        pbt=pbt, tax=tax_arr, net=net,
    )
    return ctx, bundle


def _margins(rev, gp, ebitda, op, net) -> list[list[float]]:
    def pct(num, den):
        return [round((nu / d * 100.0), 2) if d else 0.0 for nu, d in zip(num, den)]
    return [pct(gp, rev), ebitda, pct(ebitda, rev), pct(op, rev), pct(net, rev)]


def generate_income_statement(
    project: BusinessPlanProject,
    scenario: str = "base",
    view: str = "yearly",
    start_period: int | None = None,
    end_period: int | None = None,
) -> IncomeStatementResponse:
    ctx, b = _compute(project, scenario)
    years, n = b["years"], b["n"]
    periods = _monthly_periods(b["start"], n) if view == "monthly" else _yearly_periods(b["start"], years)

    def line(key, label, arr, classification, **kw):
        return _transform_tree(IncomeStatementLineItem(
            key=key, label=label, classification=classification,
            values_by_period=arr, total=sum(arr), **kw), view, years)

    sections: list[IncomeStatementSection] = []

    # 1. Revenue
    rev_items = []
    for key, label, _ in REVENUE_LINES:
        arr = b["rev_lines"][key]
        if sum(abs(x) for x in arr) == 0 and not b["rev_children"][key]:
            continue
        li = IncomeStatementLineItem(key=key, label=label, classification="revenue",
                                     values_by_period=arr, total=sum(arr),
                                     drilldown_available=bool(b["rev_children"][key]),
                                     children=b["rev_children"][key])
        rev_items.append(_transform_tree(li, view, years))
    sections.append(IncomeStatementSection(
        key="revenue", title="Revenue", display_order=1, line_items=rev_items,
        subtotal=line("total_revenue", "Total revenue", b["total_revenue"], "revenue", is_subtotal=True),
    ))

    # 2. Cost of sales
    cogs_items = []
    for key, label in COGS_LINES:
        arr = b["cogs_lines"][key]
        children = b["cogs_drill"].get(key, [])
        if sum(abs(x) for x in arr) == 0 and not children:
            continue
        li = IncomeStatementLineItem(key=key, label=label, classification="cost_of_sales",
                                     values_by_period=arr, total=sum(arr),
                                     drilldown_available=bool(children), children=children)
        cogs_items.append(_transform_tree(li, view, years))
    sections.append(IncomeStatementSection(
        key="cost_of_sales", title="Cost of sales", display_order=2, line_items=cogs_items,
        subtotal=line("total_cost_of_sales", "Total cost of sales", b["total_cogs"], "cost_of_sales", is_subtotal=True),
    ))

    # 3. Gross profit
    sections.append(IncomeStatementSection(
        key="gross_profit", title="Gross profit", display_order=3, line_items=[],
        subtotal=line("gross_profit", "Gross profit", b["gross_profit"], "gross_profit", is_subtotal=True),
    ))

    # 4. Other income (only if present)
    if sum(abs(x) for x in b["other_income"]) > 0:
        other_items = [_transform_tree(c, view, years) for c in b["other_children"]]
        sections.append(IncomeStatementSection(
            key="other_income", title="Other income", display_order=4, line_items=other_items,
            subtotal=line("total_other_income", "Total other income", b["other_income"], "other_income", is_subtotal=True),
        ))

    # 5. Operating expenses
    opex_items = [
        _transform_tree(IncomeStatementLineItem(
            key="selling_distribution", label="Selling and distribution expenses",
            classification="operating_expense", values_by_period=b["opex"]["selling"],
            total=sum(b["opex"]["selling"]), drilldown_available=bool(b["opex_drill"].get("selling")),
            children=b["opex_drill"].get("selling", [])), view, years),
        _transform_tree(IncomeStatementLineItem(
            key="administrative", label="Administrative expenses",
            classification="operating_expense", values_by_period=b["opex"]["admin"],
            total=sum(b["opex"]["admin"]), drilldown_available=bool(b["opex_drill"].get("admin")),
            children=b["opex_drill"].get("admin", [])), view, years),
        _transform_tree(IncomeStatementLineItem(
            key="staff_costs", label="Staff costs", classification="operating_expense",
            values_by_period=b["staff_total"], total=sum(b["staff_total"]),
            drilldown_available=bool(b["staff_children"]), children=b["staff_children"]), view, years),
        _transform_tree(IncomeStatementLineItem(
            key="technology_platform", label="Technology and platform expenses",
            classification="operating_expense", values_by_period=b["opex"]["technology"],
            total=sum(b["opex"]["technology"]), drilldown_available=bool(b["opex_drill"].get("technology")),
            children=b["opex_drill"].get("technology", [])), view, years),
        _transform_tree(IncomeStatementLineItem(
            key="depreciation_amortisation", label="Depreciation and amortisation",
            classification="operating_expense", values_by_period=b["dep_total"],
            total=sum(b["dep_total"]), drilldown_available=bool(b["dep_children"]),
            children=b["dep_children"]), view, years),
    ]
    sections.append(IncomeStatementSection(
        key="operating_expenses", title="Operating expenses", display_order=5, line_items=opex_items,
        subtotal=line("total_operating_expenses", "Total operating expenses", b["total_opex"], "operating_expense", is_subtotal=True),
    ))

    # 6. Operating profit
    sections.append(IncomeStatementSection(
        key="operating_profit", title="Operating profit / (loss)", display_order=6, line_items=[],
        subtotal=line("operating_profit", "Operating profit / (loss)", b["operating_profit"], "operating_profit", is_subtotal=True),
    ))

    # 7. Finance costs
    sections.append(IncomeStatementSection(
        key="finance_costs", title="Finance costs", display_order=7,
        line_items=[_transform_tree(c, view, years) for c in b["finance_children"]],
        subtotal=line("total_finance_costs", "Total finance costs", b["finance_total"], "finance_cost", is_subtotal=True),
    ))

    # 8. Profit before tax
    sections.append(IncomeStatementSection(
        key="profit_before_tax", title="Profit / (loss) before tax", display_order=8, line_items=[],
        subtotal=line("profit_before_tax", "Profit / (loss) before tax", b["pbt"], "profit_before_tax", is_subtotal=True),
    ))

    # 9. Income tax
    sections.append(IncomeStatementSection(
        key="income_tax", title="Income tax expense", display_order=9, line_items=[],
        subtotal=line("income_tax_expense", "Income tax expense", [-x for x in b["tax"]], "tax", is_subtotal=True),
    ))

    # 10. Profit for the period (grand total)
    sections.append(IncomeStatementSection(
        key="profit_for_period", title="Profit / (loss) for the period", display_order=10, line_items=[],
        subtotal=line("profit_for_period", "Profit / (loss) for the period", b["net"], "net_profit",
                      is_grand_total=True),
    ))

    # Margins (recomputed per view from aggregated arrays)
    def view_arr(arr):
        return arr if view == "monthly" else _aggregate_to_years(arr, years)
    rev_v = view_arr(b["total_revenue"]); gp_v = view_arr(b["gross_profit"])
    eb_v = view_arr(b["ebitda"]); op_v = view_arr(b["operating_profit"]); net_v = view_arr(b["net"])
    gm, ebitda_v, ebm, om, nm = _margins(rev_v, gp_v, eb_v, op_v, net_v)

    tr = round(sum(b["total_revenue"]), 2)
    margins = IncomeStatementMargins(
        gross_margin_pct=gm, ebitda=_round(eb_v), ebitda_margin_pct=ebm,
        operating_margin_pct=om, net_margin_pct=nm,
        gross_margin_total_pct=round(sum(b["gross_profit"]) / tr * 100, 2) if tr else 0.0,
        ebitda_margin_total_pct=round(sum(b["ebitda"]) / tr * 100, 2) if tr else 0.0,
        operating_margin_total_pct=round(sum(b["operating_profit"]) / tr * 100, 2) if tr else 0.0,
        net_margin_total_pct=round(sum(b["net"]) / tr * 100, 2) if tr else 0.0,
    )

    analytical = [
        line("ebitda", "EBITDA", b["ebitda"], "analytical"),
    ]

    # Optional window slicing
    if start_period is not None or end_period is not None:
        s = start_period or 0
        e = (end_period + 1) if end_period is not None else len(periods)
        periods = periods[s:e]
        _slice_sections(sections, s, e)
        for li in analytical:
            li.values_by_period = li.values_by_period[s:e]
            li.total = round(sum(li.values_by_period), 2)

    totals = IncomeStatementTotals(
        total_revenue=tr, total_cost_of_sales=round(sum(b["total_cogs"]), 2),
        gross_profit=round(sum(b["gross_profit"]), 2), total_other_income=round(sum(b["other_income"]), 2),
        total_operating_expenses=round(sum(b["total_opex"]), 2), operating_profit=round(sum(b["operating_profit"]), 2),
        ebitda=round(sum(b["ebitda"]), 2), total_finance_costs=round(sum(b["finance_total"]), 2),
        profit_before_tax=round(sum(b["pbt"]), 2), income_tax_expense=round(sum(b["tax"]), 2),
        profit_for_period=round(sum(b["net"]), 2),
    )

    meta = IncomeStatementMetadata(
        project_id=project.id, project_name=project.name, scenario=scenario,
        scenario_label=ctx.scen.label, view=view,
        currency=(project.setup.currency if project.setup else "USD"),
        period_caption=_period_caption(b["start"], n),
        generated_at=datetime.now(timezone.utc),
    )

    return IncomeStatementResponse(
        metadata=meta, periods=periods, sections=sections, totals=totals,
        margins=margins, analytical=analytical, warnings=ctx.warnings,
    )


def _slice_sections(sections: list[IncomeStatementSection], s: int, e: int) -> None:
    def slice_li(li: IncomeStatementLineItem):
        li.values_by_period = li.values_by_period[s:e]
        li.total = round(sum(li.values_by_period), 2)
        for c in li.children:
            slice_li(c)
    for sec in sections:
        for li in sec.line_items:
            slice_li(li)
        if sec.subtotal:
            slice_li(sec.subtotal)


def _period_caption(start: date, n: int) -> str:
    last = start + relativedelta(months=n - 1)
    last_day = calendar.monthrange(last.year, last.month)[1]
    return f"For the projected period ending {last_day} {last.strftime('%B %Y')}"


# --------------------------------------------------------------------------
# Summary + reconciliation
# --------------------------------------------------------------------------
def build_summary(project: BusinessPlanProject, scenario: str) -> IncomeStatementSummary:
    stmt = generate_income_statement(project, scenario, view="yearly")
    t = stmt.totals
    rev = t.total_revenue or 0.0
    return IncomeStatementSummary(
        project_id=project.id, scenario=scenario, currency=stmt.metadata.currency,
        total_revenue=t.total_revenue, gross_profit=t.gross_profit, ebitda=t.ebitda,
        operating_profit=t.operating_profit, profit_before_tax=t.profit_before_tax, net_profit=t.profit_for_period,
        gross_margin=round(t.gross_profit / rev * 100, 2) if rev else 0.0,
        ebitda_margin=round(t.ebitda / rev * 100, 2) if rev else 0.0,
        net_profit_margin=round(t.profit_for_period / rev * 100, 2) if rev else 0.0,
    )


def build_reconciliation(project: BusinessPlanProject, scenario: str) -> IncomeStatementReconciliation:
    ctx, b = _compute(project, scenario)
    checks: list[ReconciliationCheck] = []

    def chk(key, label, passed, severity="warning", detail=None):
        checks.append(ReconciliationCheck(key=key, label=label, passed=passed,
                                          severity="info" if passed else severity, detail=detail))

    has_revenue = sum(b["total_revenue"]) > 0
    chk("revenue_found", "Revenue calculated from product assumptions", has_revenue, "critical")
    chk("active_products", "Active products / services found",
        any(p.active for p in project.products), "critical")
    assigned = [c for c in project.direct_costs if c.active and (c.apply_to_all or c.product_ids)]
    chk("direct_costs_linked", "Direct costs linked to revenue streams", bool(assigned), "critical")
    unassigned = [c for c in project.direct_costs if not c.apply_to_all and not c.product_ids]
    chk("unassigned_identified", "Unassigned direct costs identified",
        True, detail=f"{len(unassigned)} unassigned item(s) excluded" if unassigned else "None")
    chk("opex_included", "Operating expenses included", bool(project.operating_expenses), "warning")
    chk("staff_included", "Staffing costs included", sum(b["staff_total"]) > 0, "warning")
    chk("depreciation_included", "Fixed asset depreciation included", sum(b["dep_total"]) > 0, "info")
    chk("finance_included", "Loan finance costs included",
        sum(b["finance_total"]) > 0 or not project.financing.loans, "info")
    chk("tax_included", "Tax calculation included",
        project.tax is not None and project.tax.corporate_tax_enabled, "warning")

    # Reconciliation identities
    gp_ok = abs(sum(b["gross_profit"]) - (sum(b["total_revenue"]) - sum(b["total_cogs"]))) < 1.0
    chk("gross_profit_reconciles", "Gross profit reconciles (Revenue − Cost of sales)", gp_ok, "critical")
    ebitda_ok = abs(sum(b["ebitda"]) - (sum(b["operating_profit"]) + sum(b["dep_total"]))) < 1.0
    chk("ebitda_reconciles", "EBITDA reconciles (Operating profit + D&A)", ebitda_ok, "critical")
    net_ok = abs(sum(b["net"]) - (sum(b["pbt"]) - sum(b["tax"]))) < 1.0
    chk("net_profit_reconciles", "Net profit reconciles (PBT − Tax)", net_ok, "critical")

    # Extra warnings (Big-4 style)
    for p in project.products:
        if p.active and not any(r.product_id == p.id for r in project.revenue):
            ctx.warn(f"product_no_rev_{p.id}", "warning", f"Product '{p.name}' has no revenue assumption.")
    gm_total = sum(b["gross_profit"])
    if sum(b["total_revenue"]) > 0 and gm_total < 0:
        ctx.warn("negative_gross_margin", "critical", "Projected gross margin is negative.")
    for s in project.scenarios:
        for fld in ("sales_volume_adjustment", "selling_price_adjustment", "direct_cost_adjustment"):
            if abs(getattr(s, fld)) > 50:
                ctx.warn(f"extreme_scenario_{s.scenario_type.value}", "info",
                         f"Scenario '{s.label or s.scenario_type.value}' has an unusually large adjustment.")

    return IncomeStatementReconciliation(
        project_id=project.id, scenario=scenario,
        all_passed=all(c.passed for c in checks if c.severity != "info"),
        checks=checks, warnings=ctx.warnings,
    )
