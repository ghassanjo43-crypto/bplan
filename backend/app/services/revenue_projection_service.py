"""Revenue projection service (two-layer: setup + monthly schedule).

Each product/service acts as a revenue stream (setup). Its monthly quantity
schedule is the source of truth for the income statement. Schedules are seeded
deterministically from the growth/seasonality helpers, then user-editable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from dateutil.relativedelta import relativedelta

from ..models import BusinessPlanProject
from ..models.projection import RevenueCell
from ..schemas.projection import GridCell, GridRow, ProjectionGrid
from . import projection_period_service as periods

# IFRS revenue category per revenue type (reused by the income statement).
REVENUE_TYPE_TO_CATEGORY = {
    "unit_sales": ("product_revenue", "Product revenue"),
    "service_contract": ("service_revenue", "Service revenue"),
    "subscription": ("subscription_revenue", "Subscription revenue"),
    "project_based": ("contract_revenue", "Contract revenue"),
    "commission": ("commission_revenue", "Commission revenue"),
    "licensing": ("licensing_revenue", "Licensing revenue"),
    "other": ("other_revenue", "Other revenue"),
}


def _mb(start: date, other: date) -> int:
    return (other.year - start.year) * 12 + (other.month - start.month)


def _annual_billed(product) -> bool:
    unit = (product.unit_of_sale or "").lower()
    return any(k in unit for k in ("annual", "year", "yr", "p.a"))


def default_price(product, ra) -> float:
    rt = product.revenue_type.value
    if rt == "subscription":
        p = (ra.subscription_price if ra else None) or product.selling_price
        return p / 12 if _annual_billed(product) else p
    if rt in ("service_contract", "project_based"):
        return (ra.contract_value if ra else None) or product.selling_price
    if rt == "licensing":
        return (ra.licensing_fee if ra else None) or product.selling_price
    if rt == "commission":
        aov = (ra.average_order_value if ra else None) or product.selling_price
        return aov * ((ra.commission_rate if ra else 0) or 0) / 100.0
    return (ra.average_order_value if ra else None) or product.selling_price


def _growth_monthly(ra) -> float:
    # Annual Sales Growth is the primary input; the UI disables the monthly
    # field whenever an annual rate is set. Annual therefore takes precedence,
    # and the optional monthly rate is only used when annual is left blank.
    if ra is None:
        return 0.0
    if ra.annual_growth_rate is not None:
        return (1 + ra.annual_growth_rate / 100.0) ** (1 / 12) - 1
    if ra.monthly_growth_rate is not None:
        return ra.monthly_growth_rate / 100.0
    return 0.0


def _season(ra, month: int, force: bool = False) -> float:
    if ra is None or (not ra.seasonality_enabled and not force):
        return 1.0
    for s in ra.seasonality:
        if s.month == month:
            return s.adjustment_percent / 100.0
    return 1.0


def _enum_value(v, default: str) -> str:
    """Tolerant accessor for an enum-or-str field (handles legacy/raw data)."""
    if v is None:
        return default
    return v.value if hasattr(v, "value") else v


def stream_start_idx(product, ra, start: date) -> int:
    """Month index a stream begins: per-stream start date, else product launch."""
    sd = (getattr(ra, "revenue_start_date", None) if ra else None) or (
        product.launch_date if product else None
    )
    return max(0, _mb(start, sd)) if sd else 0


def stream_end_idx(ra, start: date, n: int) -> int:
    """Last active month index: per-stream end date, else the horizon end."""
    ed = getattr(ra, "revenue_end_date", None) if ra else None
    if not ed:
        return n - 1
    return min(n - 1, _mb(start, ed))


def stream_window(product, ra, start: date, n: int) -> tuple[int, int]:
    """Active [start, end] month window for a stream — the single source of truth.

    For CONTRACT_PERIOD the end is derived from start + contract_duration_months
    (the manual revenue_end_date is intentionally ignored so the two can never
    contradict). All other modes use revenue_end_date (else the horizon).
    """
    s_idx = stream_start_idx(product, ra, start)
    timing = _enum_value(getattr(ra, "revenue_timing", None), "continuous")
    if timing == "contract_period":
        duration = int(getattr(ra, "contract_duration_months", None) or 12)
        e_idx = min(n - 1, s_idx + duration - 1)
    else:
        e_idx = stream_end_idx(ra, start, n)
    return s_idx, e_idx


def seed_quantity(product, ra, n: int, start: date) -> list[float]:
    """Seed a monthly quantity series, shaped by the stream's revenue timing.

    CONTINUOUS (the default) reproduces the legacy growth/seasonality series, so
    projects without a timing value are unchanged. Other modes shape recurrence:
    one-time (single month), annual (spread or lump), contract (spread a cohort
    over its duration), seasonal (force seasonality multipliers). CUSTOM seeds
    the continuous baseline as a starting point for month-by-month grid edits.
    """
    units = [0.0] * n
    if ra is None or not product.active:
        return units

    s_idx, e_idx = stream_window(product, ra, start, n)
    if s_idx >= n or e_idx < s_idx:
        return units

    rt = product.revenue_type.value
    timing = _enum_value(getattr(ra, "revenue_timing", None), "continuous")
    recognition = _enum_value(getattr(ra, "recognition_method", None), "spread")
    g = _growth_monthly(ra)
    start_vol = ra.starting_monthly_volume or 0

    if timing == "one_time":
        units[s_idx] = round(start_vol, 4)
        return units

    if timing == "annual_recurring":
        annual_g = (ra.annual_growth_rate or 0) / 100.0
        for t in range(s_idx, e_idx + 1):
            year = (t - s_idx) // 12
            yearly_qty = start_vol * ((1 + annual_g) ** year)
            if recognition == "lump":
                if (t - s_idx) % 12 == 0:
                    units[t] = round(yearly_qty, 4)
            else:
                units[t] = round(yearly_qty / 12.0, 4)
        return units

    if timing == "contract_period":
        duration = int(getattr(ra, "contract_duration_months", None) or 12)
        if recognition == "lump":
            units[s_idx] = round(start_vol, 4)
        else:
            last = min(e_idx, s_idx + duration - 1)
            for t in range(s_idx, last + 1):
                units[t] = round(start_vol / duration, 4)
        return units

    # continuous / monthly_recurring / seasonal / custom -> growth + seasonality
    force_season = timing == "seasonal"
    if rt == "subscription":
        churn = (ra.churn_rate or 0) / 100.0
        churn_m = (1 - (1 - churn) ** (1 / 12)) if _annual_billed(product) else churn
        subs = 0.0
        for t in range(s_idx, e_idx + 1):
            subs = start_vol if t == s_idx else subs * (1 + g) * (1 - churn_m)
            units[t] = round(subs, 4)
    else:
        for t in range(s_idx, e_idx + 1):
            base = start_vol * ((1 + g) ** (t - s_idx))
            month = (start + relativedelta(months=t)).month
            units[t] = round(base * _season(ra, month, force_season), 4)
    return units


@dataclass
class ResolvedStream:
    product: object
    ra: object
    cells: list[RevenueCell]
    quantity: list[float] = field(default_factory=list)
    price: list[float] = field(default_factory=list)
    discount: list[float] = field(default_factory=list)
    refund: list[float] = field(default_factory=list)
    active: list[bool] = field(default_factory=list)
    gross: list[float] = field(default_factory=list)
    net: list[float] = field(default_factory=list)
    customers: list[float] = field(default_factory=list)


def get_cells(project: BusinessPlanProject, product, ra, n: int, start: date) -> list[RevenueCell]:
    """Stored cells if present (resized to n), else freshly seeded (in-memory)."""
    stored = project.projections.revenue.get(product.id)
    if stored is not None:
        cells = list(stored)
        if len(cells) < n:
            cells += [RevenueCell() for _ in range(n - len(cells))]
        return cells[:n]
    qty = seed_quantity(product, ra, n, start)
    return [RevenueCell(quantity=q) for q in qty]


def resolve_streams(
    project: BusinessPlanProject, n: int, start: date,
    vol_factor: float = 1.0, price_factor: float = 1.0,
) -> dict[str, ResolvedStream]:
    out: dict[str, ResolvedStream] = {}
    for product in project.products:
        ra = next((r for r in project.revenue if r.product_id == product.id), None)
        cells = get_cells(project, product, ra, n, start)
        d_price = default_price(product, ra)
        d_disc = (ra.discount_percent if ra else 0) or 0
        d_ref = (ra.refund_percent if ra else 0) or 0
        # Active window — the single source of truth. Contract/project uses
        # start + duration; other modes use revenue_end_date (else horizon).
        # Enforced here so the window applies even to stored/seeded grids.
        start_idx, end_idx = stream_window(product, ra, start, n)
        rs = ResolvedStream(product=product, ra=ra, cells=cells)
        for t in range(n):
            c = cells[t]
            active = c.active and product.active and start_idx <= t <= end_idx
            price = (c.price_override if c.price_override is not None else d_price) * price_factor
            disc = c.discount_override if c.discount_override is not None else d_disc
            ref = c.refund_override if c.refund_override is not None else d_ref
            qty = (c.quantity or 0) * vol_factor
            gross = qty * price if active else 0.0
            net = gross * (1 - disc / 100.0) * (1 - ref / 100.0)
            rs.quantity.append(qty)
            rs.price.append(price)
            rs.discount.append(disc)
            rs.refund.append(ref)
            rs.active.append(active)
            rs.gross.append(gross)
            rs.net.append(round(net, 4))
            rs.customers.append(qty)
        out[product.id] = rs
    return out


# -- Unified revenue source (streams primary, products fallback) ------------
@dataclass
class RevSource:
    """A revenue source direct costs can associate with — either a Revenue
    Stream (primary) or, for legacy projects, a product/service."""
    id: str
    name: str
    quantity: list[float]
    price: list[float]
    net: list[float]
    customers: list[float]


def resolve_revenue_sources(
    project: BusinessPlanProject, n: int, start: date,
    vol_factor: float = 1.0, price_factor: float = 1.0,
) -> dict[str, RevSource]:
    """Revenue sources keyed by id, used for direct-cost association + drivers.

    When the project has any active revenue stream, the sources ARE the streams
    (the primary workflow). Otherwise it falls back to the legacy per-product
    resolution so existing product-only projects are unchanged.
    """
    from . import revenue_stream_service as rss

    active_streams = [s for s in getattr(project, "revenue_streams", [])
                      if getattr(s, "active", True)]
    if active_streams:
        out: dict[str, RevSource] = {}
        for s in active_streams:
            net = [round(v * vol_factor, 4) for v in rss.compute_monthly(s, n)]
            qty, price, customers = rss.driver_series(s, n)
            qty = [q * vol_factor for q in qty]
            price = [p * price_factor for p in price]
            out[s.id] = RevSource(id=s.id, name=s.name, quantity=qty, price=price,
                                  net=net, customers=customers)
        return out

    return {
        pid: RevSource(id=pid, name=rs.product.name, quantity=rs.quantity,
                       price=rs.price, net=rs.net, customers=rs.customers)
        for pid, rs in resolve_streams(project, n, start, vol_factor, price_factor).items()
    }


# -- Persistence + grid -----------------------------------------------------
def ensure_persisted(project: BusinessPlanProject, n: int, start: date) -> bool:
    """Persist seeded schedules for any stream lacking one. Returns True if changed."""
    changed = False
    for product in project.products:
        if product.id not in project.projections.revenue:
            ra = next((r for r in project.revenue if r.product_id == product.id), None)
            project.projections.revenue[product.id] = get_cells(project, product, ra, n, start)
            changed = True
    return changed


def generate_revenue_grid(project: BusinessPlanProject, mode: str) -> ProjectionGrid:
    start, years, n = periods.build_projection_periods(project)
    plist = periods.periods_for(project, mode)
    resolved = resolve_streams(project, n, start)
    currency = project.setup.currency if project.setup else "USD"
    rows: list[GridRow] = []
    warnings: list[str] = []
    totals = [0.0] * len(plist)

    for pid, rs in resolved.items():
        _, cat_label = REVENUE_TYPE_TO_CATEGORY.get(rs.product.revenue_type.value, ("other_revenue", "Other revenue"))
        cells: list[GridCell] = []
        if mode == "annual":
            for y in range(years):
                idxs = range(y * 12, min(n, (y + 1) * 12))
                qty = sum(rs.quantity[t] for t in idxs)
                net = sum(rs.net[t] for t in idxs)
                gross = sum(rs.gross[t] for t in idxs)
                cells.append(GridCell(period_index=y, quantity=round(qty, 2), value=round(net, 2),
                                      gross=round(gross, 2), active=any(rs.active[t] for t in idxs)))
        else:
            for t in range(n):
                c = rs.cells[t]
                cells.append(GridCell(
                    period_index=t, quantity=round(rs.quantity[t], 2),
                    price_override=c.price_override, discount_override=c.discount_override,
                    refund_override=c.refund_override, active=rs.active[t], notes=c.notes,
                    value=round(rs.net[t], 2), gross=round(rs.gross[t], 2),
                    discount_amount=round(rs.gross[t] * rs.discount[t] / 100.0, 2),
                    refund_amount=round(rs.gross[t] * rs.refund[t] / 100.0, 2),
                ))
        for i, c in enumerate(cells):
            totals[i] += c.value
        row_total = round(sum(c.value for c in cells), 2)
        if row_total == 0:
            warnings.append(f"Revenue stream '{rs.product.name}' has no projection values.")
        rows.append(GridRow(item_id=pid, label=rs.product.name, group=cat_label, cells=cells, total=row_total))

    return ProjectionGrid(
        project_id=project.id, section="revenue", mode=mode, currency=currency,
        periods=plist, rows=rows, totals_by_period=[round(x, 2) for x in totals],
        grand_total=round(sum(totals), 2), warnings=warnings,
    )


# -- Mutations (operate on stored monthly cells) ----------------------------
def _ensure_row(project: BusinessPlanProject, item_id: str, n: int, start: date) -> list[RevenueCell]:
    if item_id not in project.projections.revenue:
        product = next((p for p in project.products if p.id == item_id), None)
        ra = next((r for r in project.revenue if r.product_id == item_id), None) if product else None
        project.projections.revenue[item_id] = get_cells(project, product, ra, n, start) if product else [RevenueCell() for _ in range(n)]
    cells = project.projections.revenue[item_id]
    if len(cells) < n:
        cells += [RevenueCell() for _ in range(n - len(cells))]
    return cells


def _monthly_index_range(period_index: int, mode: str, n: int) -> list[int]:
    if mode == "annual":
        return [t for t in range(period_index * 12, min(n, (period_index + 1) * 12))]
    return [period_index]


def apply_cell_patch(project: BusinessPlanProject, patch, mode: str) -> None:
    start, _years, n = periods.build_projection_periods(project)
    cells = _ensure_row(project, patch.item_id, n, start)
    targets = _monthly_index_range(patch.period_index, mode, n)
    for ti, t in enumerate(targets):
        if t >= len(cells):
            continue
        c = cells[t]
        if patch.quantity is not None:
            # annual quantity is spread evenly across the year's months
            c.quantity = patch.quantity / len(targets) if mode == "annual" else patch.quantity
        if patch.price_override is not None:
            c.price_override = patch.price_override
        if patch.discount_override is not None:
            c.discount_override = patch.discount_override
        if patch.refund_override is not None:
            c.refund_override = patch.refund_override
        if patch.active is not None:
            c.active = patch.active
        if patch.notes is not None:
            c.notes = patch.notes
        if patch.clear_overrides:
            c.price_override = c.discount_override = c.refund_override = None


def fill_right(project: BusinessPlanProject, item_id: str, from_index: int, mode: str) -> None:
    start, years, n = periods.build_projection_periods(project)
    cells = _ensure_row(project, item_id, n, start)
    if mode == "annual":
        src_idxs = _monthly_index_range(from_index, "annual", n)
        src_qty = sum(cells[t].quantity for t in src_idxs) if src_idxs else 0
        for y in range(from_index + 1, years):
            for ti, t in enumerate(_monthly_index_range(y, "annual", n)):
                cells[t].quantity = src_qty / 12
    else:
        if from_index < len(cells):
            val = cells[from_index].quantity
            for t in range(from_index + 1, n):
                cells[t].quantity = val


def apply_growth(project: BusinessPlanProject, req) -> None:
    start, years, n = periods.build_projection_periods(project)
    ids = [req.item_id] if req.item_id else [p.id for p in project.products]
    g = req.growth_percent / 100.0
    for item_id in ids:
        cells = _ensure_row(project, item_id, n, start)
        if req.mode == "annual":
            base = req.base_value
            if base is None:
                base = sum(cells[t].quantity for t in _monthly_index_range(req.start_index, "annual", n))
            for y in range(req.start_index, years):
                year_val = base * ((1 + g) ** (y - req.start_index))
                for t in _monthly_index_range(y, "annual", n):
                    cells[t].quantity = year_val / 12
        else:
            base = req.base_value if req.base_value is not None else cells[req.start_index].quantity
            for t in range(req.start_index, n):
                cells[t].quantity = round(base * ((1 + g) ** (t - req.start_index)), 4)
