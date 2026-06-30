"""Phase 1 — revenue timing / recurrence projection tests.

Covers the manual scenarios A–F plus backward compatibility and validation:
  A. One-time revenue appears only once.
  B. Monthly recurring revenue repeats monthly.
  C. Annual recurring revenue (spread vs lump recognition).
  D. Contract revenue spreads over the contract duration.
  E. Revenue stops after the end date.
  F. Seasonal revenue follows the seasonality multipliers.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.models.catalog import ProductService, RevenueAssumption, SeasonalityMonth
from app.models.enums import RecognitionMethod, RevenueTiming, RevenueType
from app.services import revenue_projection_service as rps

START = date(2026, 1, 1)
N = 36


def _product(launch=date(2026, 1, 1), rt=RevenueType.UNIT_SALES):
    return ProductService(id="p1", name="X", revenue_type=rt, selling_price=10, launch_date=launch)


def _seed(ra, product=None):
    return rps.seed_quantity(product or _product(), ra, N, START)


# -- A. one-time ------------------------------------------------------------
def test_a_one_time_appears_once():
    ra = RevenueAssumption(product_id="p1", starting_monthly_volume=500,
                           revenue_timing=RevenueTiming.ONE_TIME)
    q = _seed(ra)
    assert q[0] == 500
    assert sum(1 for x in q if x > 0) == 1


# -- B. monthly recurring ---------------------------------------------------
def test_b_monthly_recurring_repeats():
    ra = RevenueAssumption(product_id="p1", starting_monthly_volume=100, annual_growth_rate=0,
                           revenue_timing=RevenueTiming.MONTHLY_RECURRING)
    q = _seed(ra)
    assert all(x == 100 for x in q)


# -- C. annual recurring ----------------------------------------------------
def test_c_annual_spread():
    ra = RevenueAssumption(product_id="p1", starting_monthly_volume=1200,
                           revenue_timing=RevenueTiming.ANNUAL_RECURRING,
                           recognition_method=RecognitionMethod.SPREAD)
    q = _seed(ra)
    assert all(abs(x - 100) < 1e-6 for x in q)            # 1200 / 12 every month


def test_c_annual_lump():
    ra = RevenueAssumption(product_id="p1", starting_monthly_volume=1200,
                           revenue_timing=RevenueTiming.ANNUAL_RECURRING,
                           recognition_method=RecognitionMethod.LUMP)
    q = _seed(ra)
    assert q[0] == 1200 and q[12] == 1200 and q[24] == 1200
    assert sum(1 for x in q if x > 0) == 3                # once per year over 3 years


# -- D. contract / project spread ------------------------------------------
def test_d_contract_spreads_over_duration():
    ra = RevenueAssumption(product_id="p1", starting_monthly_volume=60,
                           revenue_timing=RevenueTiming.CONTRACT_PERIOD, contract_duration_months=6)
    q = _seed(ra)
    assert all(abs(q[t] - 10) < 1e-6 for t in range(6))  # 60 / 6 for six months
    assert all(q[t] == 0 for t in range(6, N))
    assert abs(sum(q) - 60) < 1e-6                        # cohort total preserved


# -- E. end date stops revenue ---------------------------------------------
def test_e_end_date_stops_revenue():
    ra = RevenueAssumption(product_id="p1", starting_monthly_volume=100,
                           revenue_timing=RevenueTiming.MONTHLY_RECURRING,
                           revenue_end_date=date(2026, 6, 30))
    q = _seed(ra)
    assert all(q[t] == 100 for t in range(6))             # Jan–Jun 2026
    assert all(q[t] == 0 for t in range(6, N))


def test_e_start_date_overrides_launch():
    ra = RevenueAssumption(product_id="p1", starting_monthly_volume=100,
                           revenue_timing=RevenueTiming.MONTHLY_RECURRING,
                           revenue_start_date=date(2026, 4, 1))
    q = _seed(ra)
    assert all(q[t] == 0 for t in range(3))               # before Apr
    assert q[3] == 100


# -- F. seasonal ------------------------------------------------------------
def test_f_seasonal_follows_multipliers():
    ra = RevenueAssumption(product_id="p1", starting_monthly_volume=100,
                           revenue_timing=RevenueTiming.SEASONAL,
                           seasonality=[SeasonalityMonth(month=1, adjustment_percent=150),
                                        SeasonalityMonth(month=7, adjustment_percent=50)])
    q = _seed(ra)
    assert q[0] == 150     # Jan multiplier 150%
    assert q[6] == 50      # Jul multiplier 50%
    assert q[1] == 100     # neutral month


# -- backward compatibility -------------------------------------------------
def test_default_timing_is_continuous_and_unchanged():
    ra = RevenueAssumption(product_id="p1", starting_monthly_volume=100, annual_growth_rate=12)
    assert ra.revenue_timing == RevenueTiming.CONTINUOUS
    q = _seed(ra)
    # continuous keeps the legacy compounded-growth series
    assert q[0] == 100
    assert q[1] > 100 and q[2] > q[1]


# -- validation -------------------------------------------------------------
def test_end_before_start_rejected():
    with pytest.raises(ValueError):
        RevenueAssumption(product_id="p1", revenue_start_date=date(2026, 6, 1),
                          revenue_end_date=date(2026, 1, 1))
