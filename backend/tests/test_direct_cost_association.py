"""Direct costs associate with revenue streams (primary) or fall back to legacy
products. Regression for retiring the hidden ProductService association UI in
favour of revenue_streams (income statement + projection engine).
"""
from __future__ import annotations

from app.models import DirectCostItem, RevenueStream
from app.models.enums import (
    CostCalculationMethod as CM,
    DirectCostCategory as DC,
    RevenueStreamType,
)
from app.services import direct_cost_projection_service as dcp
from app.services import income_statement_service as isvc
from app.services import revenue_projection_service as rps
from app.services.demo_builder import build_demo_project
from app.services.income_statement_service import build_projection_periods


def _streams_only_project(streams, costs):
    """A valid project with revenue streams and NO products/legacy revenue."""
    p = build_demo_project()
    p.products, p.revenue = [], []
    p.revenue_streams = streams
    p.direct_costs = costs
    return p


def test_cost_linked_to_one_stream_computes_from_that_streams_quantity_and_revenue():
    stream = RevenueStream(name="Widgets", stream_type=RevenueStreamType.UNIT_SALES,
                           quantity_constant=10, price_constant=100)   # 10 units, 1000/mo
    per_unit = DirectCostItem(name="Material", category=DC.RAW_MATERIALS,
                              product_ids=[stream.id],
                              calculation_method=CM.FIXED_PER_UNIT, amount=4)
    p = _streams_only_project([stream], [per_unit])
    start, _years, n = build_projection_periods(p)
    resolved = dcp.resolve_items(p, n, start, rps.resolve_revenue_sources(p, n, start))
    rc = resolved[per_unit.id]
    assert round(rc.final[0]) == 40                     # 10 units × 4 (per-unit → stream quantity)
    assert round(sum(rc.final)) == 40 * n

    # percent-of-revenue on the same stream → 5% of the stream's forecast revenue
    pct = DirectCostItem(name="Fee", category=DC.PAYMENT_GATEWAY, product_ids=[stream.id],
                         calculation_method=CM.PERCENT_OF_REVENUE, percent=5)
    p2 = _streams_only_project([stream], [pct])
    r2 = dcp.resolve_items(p2, n, start, rps.resolve_revenue_sources(p2, n, start))[pct.id]
    assert round(r2.final[0]) == 50                     # 5% of 1000 (% of revenue → stream revenue)


def test_streams_with_zero_products_allow_direct_cost_association():
    stream = RevenueStream(name="S", stream_type=RevenueStreamType.UNIT_SALES,
                           quantity_constant=5, price_constant=200)    # 1000/mo
    cost = DirectCostItem(name="C", category=DC.RAW_MATERIALS, product_ids=[stream.id],
                          calculation_method=CM.PERCENT_OF_REVENUE, percent=10)
    p = _streams_only_project([stream], [cost])
    assert p.products == []
    r = isvc.generate_income_statement(p, "base", "yearly")
    assert r.totals.total_revenue > 0
    assert r.totals.total_cost_of_sales > 0             # the stream-linked cost is counted in COGS
    assert round(r.totals.total_cost_of_sales) == round(0.10 * r.totals.total_revenue)


def test_legacy_product_only_direct_costs_still_calculate_via_fallback():
    p = build_demo_project()                            # products + product-linked costs, no streams
    assert p.revenue_streams == [] and len(p.products) > 0
    start, _years, n = build_projection_periods(p)
    src = rps.resolve_revenue_sources(p, n, start)
    assert set(src.keys()) == {pr.id for pr in p.products}     # falls back to product ids
    r = isvc.generate_income_statement(p, "base", "yearly")
    assert r.totals.total_cost_of_sales > 0             # legacy COGS path unchanged


def test_association_source_is_streams_not_products_when_streams_exist():
    """The association dropdown is built from resolve_revenue_sources; when
    streams exist it exposes stream ids only — never hidden ProductService ids."""
    stream = RevenueStream(name="S", stream_type=RevenueStreamType.REVENUE_ONLY,
                           revenue_constant=1000)
    p = build_demo_project()                            # still has (hidden) products
    p.revenue_streams = [stream]
    start, _years, n = build_projection_periods(p)
    src = rps.resolve_revenue_sources(p, n, start)
    assert set(src.keys()) == {stream.id}               # only the revenue stream
    assert not (set(src.keys()) & {pr.id for pr in p.products})   # no product ids exposed
