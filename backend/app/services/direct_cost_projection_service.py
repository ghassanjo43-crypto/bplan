"""Direct cost projection service (setup + monthly schedule).

Final cost per period is computed from the item's calculation method using the
linked revenue stream's projected drivers, then optionally overridden per cell
(amount/percentage/manual). The income statement reads the final amounts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..models import BusinessPlanProject
from ..models.enums import CostCalculationMethod as CM
from ..models.projection import DirectCostCell
from ..schemas.projection import GridCell, GridRow, ProjectionGrid
from . import projection_period_service as periods
from . import revenue_projection_service as rev

COGS_CATEGORY_MAP = {
    "raw_materials": ("product_direct_costs", "Product direct costs"),
    "purchased_goods": ("product_direct_costs", "Product direct costs"),
    "manufacturing": ("product_direct_costs", "Product direct costs"),
    "packaging": ("product_direct_costs", "Product direct costs"),
    "direct_labor": ("service_delivery_costs", "Service delivery costs"),
    "installation": ("service_delivery_costs", "Service delivery costs"),
    "maintenance": ("service_delivery_costs", "Service delivery costs"),
    "hosting": ("subscription_direct_costs", "Subscription direct costs"),
    "payment_gateway": ("payment_gateway_fees", "Payment gateway fees"),
    "sales_commission": ("sales_commissions", "Sales commissions"),
    "warranty": ("warranty_provision", "Warranty provision"),
    "customs": ("import_customs_costs", "Import/customs costs"),
    "subcontractor": ("other_direct_costs", "Other direct costs"),
    "other": ("other_direct_costs", "Other direct costs"),
}


def _mb(start: date, other: date) -> int:
    return (other.year - start.year) * 12 + (other.month - start.month)


def _amount_at(amount: float, infl: float, year_idx: int, waste: float = 0.0, extra_infl: float = 0.0) -> float:
    rate = (infl + extra_infl) / 100.0
    return amount * ((1 + rate) ** year_idx) * (1 + waste / 100.0)


def _assoc(item, all_ids: list[str]) -> list[str]:
    return all_ids if item.apply_to_all else list(item.product_ids)


def _cost_start(item, project) -> date | None:
    """Effective start date for a direct cost.

    Explicit ``start_date`` wins. When blank and the cost is linked to one or
    more products/services, it follows the earliest linked product launch date
    so the launch date stays a single source of truth (instead of re-entering
    it as a cost start date). Falls back to ``None`` (period start) otherwise.
    """
    if item.start_date:
        return item.start_date
    ids = [p.id for p in project.products] if item.apply_to_all else list(item.product_ids)
    launches = [p.launch_date for p in project.products if p.id in ids and p.launch_date]
    return min(launches) if launches else None


@dataclass
class ResolvedCost:
    item: object
    cells: list[DirectCostCell]
    final: list[float] = field(default_factory=list)
    computed: list[float] = field(default_factory=list)


def _purchased_base(project, all_ids, n, start, extra_infl) -> dict[str, list[float]]:
    """Per-source per-month purchased per-unit cost (fixed_per_unit items)."""
    base: dict[str, list[float]] = {sid: [0.0] * n for sid in all_ids}
    for item in project.direct_costs:
        if not item.active or item.calculation_method != CM.FIXED_PER_UNIT:
            continue
        sd = _cost_start(item, project)
        s_idx = max(0, _mb(start, sd)) if sd else 0
        for pid in _assoc(item, all_ids):
            if pid not in base:
                continue
            for t in range(s_idx, n):
                base[pid][t] += _amount_at(item.amount, item.cost_inflation_rate, t // 12,
                                           item.waste_defect_rate_percent, extra_infl)
    return base


def get_cells(project: BusinessPlanProject, item, n: int) -> list[DirectCostCell]:
    stored = project.projections.direct_costs.get(item.id)
    if stored is not None:
        cells = list(stored)
        if len(cells) < n:
            cells += [DirectCostCell() for _ in range(n - len(cells))]
        return cells[:n]
    return [DirectCostCell() for _ in range(n)]


def resolve_items(
    project: BusinessPlanProject, n: int, start: date, resolved_rev: dict,
    direct_cost_factor: float = 1.0, extra_infl: float = 0.0,
) -> dict[str, ResolvedCost]:
    # Association universe = whatever revenue sources were resolved (revenue
    # streams when the project has them, else legacy products).
    all_ids = list(resolved_rev.keys())
    purchased = _purchased_base(project, all_ids, n, start, extra_infl)
    out: dict[str, ResolvedCost] = {}

    for item in project.direct_costs:
        cells = get_cells(project, item, n)
        rc = ResolvedCost(item=item, cells=cells)
        assoc = _assoc(item, all_ids)
        sd = _cost_start(item, project)
        s_idx = max(0, _mb(start, sd)) if sd else 0
        e_idx = _mb(start, item.end_date) if item.end_date else n - 1
        for t in range(n):
            c = cells[t]
            within = item.active and c.active and s_idx <= t <= e_idx
            computed = 0.0
            if within:
                yi = t // 12
                m = item.calculation_method
                pct = (c.percentage_override if c.percentage_override is not None else item.percent)
                amt = _amount_at(
                    (c.amount_override if c.amount_override is not None else item.amount),
                    item.cost_inflation_rate, yi,
                    item.waste_defect_rate_percent if m == CM.FIXED_PER_UNIT else 0.0, extra_infl,
                )
                for pid in assoc:
                    rs = resolved_rev.get(pid)
                    if not rs:
                        continue
                    driver = c.quantity_driver if c.quantity_driver is not None else rs.quantity[t]
                    if m == CM.PERCENT_OF_REVENUE:
                        computed += rs.net[t] * pct / 100.0
                    elif m == CM.PERCENT_OF_SELLING_PRICE:
                        computed += rs.quantity[t] * rs.price[t] * pct / 100.0
                    elif m == CM.PERCENT_OF_PURCHASE_COST:
                        computed += rs.quantity[t] * purchased.get(pid, [0] * n)[t] * pct / 100.0
                    elif m == CM.PER_CUSTOMER:
                        computed += rs.customers[t] * amt
                    elif m in (CM.FIXED_PER_UNIT, CM.PER_ORDER, CM.PER_CONTRACT, CM.PER_SERVICE_DELIVERY):
                        computed += driver * amt
                if m == CM.MONTHLY_ALLOCATED:
                    computed = amt
                elif m == CM.ANNUAL_ALLOCATED:
                    computed = amt / 12.0
                elif m == CM.ONE_TIME:
                    computed = amt if t == s_idx else 0.0
                elif m == CM.MANUAL_BY_PERIOD:
                    computed = 0.0
                computed *= direct_cost_factor
            final = c.manual_cost_amount if c.manual_cost_amount is not None else computed
            rc.computed.append(round(computed, 4))
            rc.final.append(round(final, 4))
        out[item.id] = rc
    return out


def ensure_persisted(project: BusinessPlanProject, n: int) -> bool:
    changed = False
    for item in project.direct_costs:
        if item.id not in project.projections.direct_costs:
            project.projections.direct_costs[item.id] = get_cells(project, item, n)
            changed = True
    return changed


def generate_direct_cost_grid(project: BusinessPlanProject, mode: str) -> ProjectionGrid:
    start, years, n = periods.build_projection_periods(project)
    plist = periods.periods_for(project, mode)
    resolved_rev = rev.resolve_revenue_sources(project, n, start)
    resolved = resolve_items(project, n, start, resolved_rev)
    currency = project.setup.currency if project.setup else "USD"
    rows: list[GridRow] = []
    warnings: list[str] = []
    totals = [0.0] * len(plist)
    rev_total = {pid: sum(rs.net) for pid, rs in resolved_rev.items()}
    covered: set[str] = set()

    for cid, rc in resolved.items():
        _, cat = COGS_CATEGORY_MAP.get(rc.item.category.value, ("other_direct_costs", "Other direct costs"))
        unassigned = not rc.item.apply_to_all and len(rc.item.product_ids) == 0
        for pid in (rc.item.product_ids if not rc.item.apply_to_all else rev_total.keys()):
            covered.add(pid)
        cells: list[GridCell] = []
        if mode == "annual":
            for y in range(years):
                idxs = range(y * 12, min(n, (y + 1) * 12))
                cells.append(GridCell(period_index=y, value=round(sum(rc.final[t] for t in idxs), 2)))
        else:
            for t in range(n):
                c = rc.cells[t]
                cells.append(GridCell(
                    period_index=t, quantity_driver=c.quantity_driver, amount_override=c.amount_override,
                    percentage_override=c.percentage_override, manual_cost_amount=c.manual_cost_amount,
                    active=c.active, notes=c.notes, value=round(rc.final[t], 2),
                ))
        # Only items that flow into the income statement's cost of sales are
        # counted in the grid totals — i.e. active AND assigned. Unassigned or
        # inactive rows still display (and stay editable) but are not summed, so
        # the grid total ties exactly to the statement's cost of sales.
        in_cogs = rc.item.active and (rc.item.apply_to_all or len(rc.item.product_ids) > 0)
        if in_cogs:
            for i, c in enumerate(cells):
                totals[i] += c.value
        row_total = round(sum(c.value for c in cells), 2)
        note = rc.item.calculation_method.value.replace("_", " ")
        if unassigned:
            note += " · unassigned (excluded)"
            warnings.append(f"Direct cost '{rc.item.name}' is unassigned and excluded from cost of sales.")
        elif not rc.item.active:
            note += " · inactive (excluded)"
        elif row_total == 0:
            warnings.append(f"Direct cost '{rc.item.name}' has no projection values.")
        rows.append(GridRow(item_id=cid, label=rc.item.name, group=cat,
                            note=note, cells=cells, total=row_total))

    for pid, rs in resolved_rev.items():
        if pid not in covered and sum(rs.net) > 0:
            warnings.append(f"Revenue stream '{rs.name}' has no direct cost assigned.")

    return ProjectionGrid(
        project_id=project.id, section="direct_costs", mode=mode, currency=currency,
        periods=plist, rows=rows, totals_by_period=[round(x, 2) for x in totals],
        grand_total=round(sum(totals), 2), warnings=warnings,
    )


def _ensure_row(project: BusinessPlanProject, item_id: str, n: int) -> list[DirectCostCell]:
    if item_id not in project.projections.direct_costs:
        item = next((c for c in project.direct_costs if c.id == item_id), None)
        project.projections.direct_costs[item_id] = get_cells(project, item, n) if item else [DirectCostCell() for _ in range(n)]
    cells = project.projections.direct_costs[item_id]
    if len(cells) < n:
        cells += [DirectCostCell() for _ in range(n - len(cells))]
    return cells


def _range(period_index: int, mode: str, n: int) -> list[int]:
    return list(range(period_index * 12, min(n, (period_index + 1) * 12))) if mode == "annual" else [period_index]


def apply_cell_patch(project: BusinessPlanProject, patch, mode: str) -> None:
    _start, _years, n = periods.build_projection_periods(project)
    cells = _ensure_row(project, patch.item_id, n)
    for t in _range(patch.period_index, mode, n):
        if t >= len(cells):
            continue
        c = cells[t]
        if patch.quantity_driver is not None:
            c.quantity_driver = patch.quantity_driver
        if patch.amount_override is not None:
            c.amount_override = patch.amount_override
        if patch.percentage_override is not None:
            c.percentage_override = patch.percentage_override
        if patch.manual_cost_amount is not None:
            c.manual_cost_amount = (patch.manual_cost_amount / len(_range(patch.period_index, mode, n))) if mode == "annual" else patch.manual_cost_amount
        if patch.active is not None:
            c.active = patch.active
        if patch.notes is not None:
            c.notes = patch.notes
        if patch.clear_overrides:
            c.amount_override = c.percentage_override = c.manual_cost_amount = c.quantity_driver = None


def fill_right(project: BusinessPlanProject, item_id: str, from_index: int, mode: str) -> None:
    _start, years, n = periods.build_projection_periods(project)
    cells = _ensure_row(project, item_id, n)
    if mode == "annual":
        src = _range(from_index, "annual", n)
        man = sum((cells[t].manual_cost_amount or 0) for t in src)
        for y in range(from_index + 1, years):
            for t in _range(y, "annual", n):
                cells[t].manual_cost_amount = man / 12 if man else None
    elif from_index < len(cells):
        src = cells[from_index]
        for t in range(from_index + 1, n):
            cells[t].manual_cost_amount = src.manual_cost_amount
            cells[t].amount_override = src.amount_override
            cells[t].percentage_override = src.percentage_override


def apply_inflation(project: BusinessPlanProject, req) -> None:
    """Write inflated manual cost amounts from a base value (override helper)."""
    _start, years, n = periods.build_projection_periods(project)
    ids = [req.item_id] if req.item_id else [c.id for c in project.direct_costs]
    g = req.growth_percent / 100.0
    for item_id in ids:
        cells = _ensure_row(project, item_id, n)
        if req.base_value is None:
            continue
        if req.mode == "annual":
            for y in range(req.start_index, years):
                val = req.base_value * ((1 + g) ** (y - req.start_index))
                for t in _range(y, "annual", n):
                    cells[t].manual_cost_amount = val / 12
        else:
            for t in range(req.start_index, n):
                cells[t].manual_cost_amount = round(req.base_value * ((1 + g) ** (t - req.start_index)), 4)
