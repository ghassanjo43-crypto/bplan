"""Operating expense projection service (setup + monthly schedule).

Final expense per period = manual amount override, else the seeded amount
(default amount × frequency factor × inflation). The income statement reads the
final amounts, grouped by IFRS classification.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..models import BusinessPlanProject
from ..models.projection import OpexCell
from ..schemas.projection import GridCell, GridRow, ProjectionGrid
from . import projection_period_service as periods

FREQ_FACTOR = {"monthly": 1.0, "quarterly": 1 / 3, "yearly": 1 / 12, "one_time": 0.0}

SELLING = {"marketing", "advertising"}
TECH = {"software"}


def ifrs_classification(category: str) -> tuple[str, str]:
    if category in SELLING:
        return "selling_distribution", "Selling and distribution expenses"
    if category in TECH:
        return "technology_platform", "Technology and platform expenses"
    return "administrative", "Administrative expenses"


def _mb(start: date, other: date) -> int:
    return (other.year - start.year) * 12 + (other.month - start.month)


_PERIOD_MONTHS = {"quarterly": 3, "yearly": 12}


def seed_amounts(exp, n: int, start: date, extra_infl: float = 0.0,
                 rent_factor: float = 1.0, marketing_factor: float = 1.0) -> list[float]:
    out = [0.0] * n
    s_idx = max(0, _mb(start, exp.start_date)) if exp.start_date else 0
    e_idx = _mb(start, exp.end_date) if exp.end_date else n - 1
    cat = exp.category.value
    scen = rent_factor if cat == "rent" else (marketing_factor if cat in SELLING else 1.0)
    freq = exp.frequency.value
    recognition = getattr(exp, "recognition_method", None)
    recognition = recognition.value if hasattr(recognition, "value") else (recognition or "spread")
    for t in range(max(0, s_idx), min(n, e_idx + 1)):
        base = exp.amount * ((1 + (exp.inflation_percent + extra_infl) / 100.0) ** (t // 12))
        if freq == "one_time":
            out[t] = (base if t == s_idx else 0.0) * scen
        elif freq in _PERIOD_MONTHS and recognition == "lump":
            # Whole period amount lands in the period's first month (cash timing).
            period = _PERIOD_MONTHS[freq]
            out[t] = (base if (t - s_idx) % period == 0 else 0.0) * scen
        else:
            # Default: smoothed across the period (monthly factor) — legacy behaviour.
            out[t] = base * FREQ_FACTOR[freq] * scen
    return out


@dataclass
class ResolvedExpense:
    item: object
    cells: list[OpexCell]
    final: list[float] = field(default_factory=list)


def get_cells(project: BusinessPlanProject, exp, n: int, start: date) -> list[OpexCell]:
    stored = project.projections.operating_expenses.get(exp.id)
    if stored is not None:
        cells = list(stored)
        if len(cells) < n:
            cells += [OpexCell() for _ in range(n - len(cells))]
        return cells[:n]
    return [OpexCell(amount=a) for a in seed_amounts(exp, n, start)]


def resolve_items(project: BusinessPlanProject, n: int, start: date,
                  extra_infl: float = 0.0, rent_factor: float = 1.0, marketing_factor: float = 1.0) -> dict[str, ResolvedExpense]:
    out: dict[str, ResolvedExpense] = {}
    for exp in project.operating_expenses:
        cells = get_cells(project, exp, n, start)
        # If scenario factors differ from the seed, re-seed for the income statement view.
        seeded = seed_amounts(exp, n, start, extra_infl, rent_factor, marketing_factor)
        re = ResolvedExpense(item=exp, cells=cells)
        for t in range(n):
            c = cells[t]
            stored_amt = c.amount if project.projections.operating_expenses.get(exp.id) is not None else seeded[t]
            base = c.amount_override if c.amount_override is not None else stored_amt
            re.final.append(round(base if c.active else 0.0, 4))
        out[exp.id] = re
    return out


def ensure_persisted(project: BusinessPlanProject, n: int, start: date) -> bool:
    changed = False
    for exp in project.operating_expenses:
        if exp.id not in project.projections.operating_expenses:
            project.projections.operating_expenses[exp.id] = get_cells(project, exp, n, start)
            changed = True
    return changed


def generate_expense_grid(project: BusinessPlanProject, mode: str) -> ProjectionGrid:
    start, years, n = periods.build_projection_periods(project)
    plist = periods.periods_for(project, mode)
    resolved = resolve_items(project, n, start)
    currency = project.setup.currency if project.setup else "USD"
    rows: list[GridRow] = []
    warnings: list[str] = []
    totals = [0.0] * len(plist)

    for eid, re in resolved.items():
        _, cls_label = ifrs_classification(re.item.category.value)
        cells: list[GridCell] = []
        if mode == "annual":
            for y in range(years):
                idxs = range(y * 12, min(n, (y + 1) * 12))
                cells.append(GridCell(period_index=y, amount=round(sum(re.final[t] for t in idxs), 2),
                                      value=round(sum(re.final[t] for t in idxs), 2)))
        else:
            for t in range(n):
                c = re.cells[t]
                cells.append(GridCell(period_index=t, amount=round(re.final[t], 2),
                                      amount_override=c.amount_override, active=c.active, notes=c.notes,
                                      value=round(re.final[t], 2)))
        for i, c in enumerate(cells):
            totals[i] += c.value
        row_total = round(sum(c.value for c in cells), 2)
        if row_total == 0 and re.item:
            warnings.append(f"Expense '{re.item.name}' has no projection values.")
        rows.append(GridRow(item_id=eid, label=re.item.name, group=cls_label, cells=cells, total=row_total))

    return ProjectionGrid(
        project_id=project.id, section="operating_expenses", mode=mode, currency=currency,
        periods=plist, rows=rows, totals_by_period=[round(x, 2) for x in totals],
        grand_total=round(sum(totals), 2), warnings=warnings,
    )


def _ensure_row(project: BusinessPlanProject, item_id: str, n: int, start: date) -> list[OpexCell]:
    if item_id not in project.projections.operating_expenses:
        exp = next((e for e in project.operating_expenses if e.id == item_id), None)
        project.projections.operating_expenses[item_id] = get_cells(project, exp, n, start) if exp else [OpexCell() for _ in range(n)]
    cells = project.projections.operating_expenses[item_id]
    if len(cells) < n:
        cells += [OpexCell() for _ in range(n - len(cells))]
    return cells


def _range(period_index: int, mode: str, n: int) -> list[int]:
    return list(range(period_index * 12, min(n, (period_index + 1) * 12))) if mode == "annual" else [period_index]


def apply_cell_patch(project: BusinessPlanProject, patch, mode: str) -> None:
    start, _years, n = periods.build_projection_periods(project)
    cells = _ensure_row(project, patch.item_id, n, start)
    targets = _range(patch.period_index, mode, n)
    for t in targets:
        if t >= len(cells):
            continue
        c = cells[t]
        if patch.amount is not None:
            c.amount = patch.amount / len(targets) if mode == "annual" else patch.amount
        if patch.amount_override is not None:
            c.amount_override = patch.amount_override / len(targets) if mode == "annual" else patch.amount_override
        if patch.active is not None:
            c.active = patch.active
        if patch.notes is not None:
            c.notes = patch.notes
        if patch.clear_overrides:
            c.amount_override = None


def fill_right(project: BusinessPlanProject, item_id: str, from_index: int, mode: str) -> None:
    start, years, n = periods.build_projection_periods(project)
    cells = _ensure_row(project, item_id, n, start)
    if mode == "annual":
        src = _range(from_index, "annual", n)
        amt = sum(cells[t].amount for t in src)
        for y in range(from_index + 1, years):
            for t in _range(y, "annual", n):
                cells[t].amount = amt / 12
    elif from_index < len(cells):
        val = cells[from_index].amount
        ov = cells[from_index].amount_override
        for t in range(from_index + 1, n):
            cells[t].amount = val
            cells[t].amount_override = ov


def apply_inflation(project: BusinessPlanProject, req) -> None:
    start, years, n = periods.build_projection_periods(project)
    ids = [req.item_id] if req.item_id else [e.id for e in project.operating_expenses]
    g = req.growth_percent / 100.0
    for item_id in ids:
        cells = _ensure_row(project, item_id, n, start)
        base = req.base_value if req.base_value is not None else cells[req.start_index].amount
        if req.mode == "annual":
            for y in range(req.start_index, years):
                val = base * ((1 + g) ** (y - req.start_index))
                for t in _range(y, "annual", n):
                    cells[t].amount = val / 12
        else:
            for t in range(req.start_index, n):
                cells[t].amount = round(base * ((1 + g) ** (t - req.start_index)), 4)
