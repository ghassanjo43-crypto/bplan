"""Phase 2 — operating-expense cost timing / recognition method tests.

Covers manual scenarios E (rent monthly), G (annual insurance recognition),
I (one-time marketing) and the spread-vs-lump recognition for quarterly/annual,
plus backward compatibility (spread is the default).
"""
from __future__ import annotations

from datetime import date

from app.models.costs import OperatingExpense
from app.models.enums import ExpenseCategory, ExpenseFrequency, RecognitionMethod
from app.services import operating_expense_projection_service as oep

START = date(2026, 1, 1)
N = 24


def _seed(exp):
    return oep.seed_amounts(exp, N, START)


def _exp(**kw):
    kw.setdefault("name", "X")
    return OperatingExpense(**kw)


# -- E / G(rent): monthly recurring repeats every month --------------------
def test_rent_monthly_repeats():
    q = _seed(_exp(category=ExpenseCategory.RENT, amount=10000, frequency=ExpenseFrequency.MONTHLY))
    assert all(x == 10000 for x in q)


# -- I: one-time appears only once -----------------------------------------
def test_one_time_appears_once():
    q = _seed(_exp(category=ExpenseCategory.MARKETING, amount=5000, frequency=ExpenseFrequency.ONE_TIME))
    assert q[0] == 5000
    assert sum(1 for x in q if x > 0) == 1


# -- G: annual default is smoothed (legacy/backward compatible) ------------
def test_annual_default_spread_is_smoothed():
    exp = _exp(category=ExpenseCategory.INSURANCE, amount=12000, frequency=ExpenseFrequency.YEARLY)
    assert exp.recognition_method == RecognitionMethod.SPREAD          # default
    q = _seed(exp)
    assert all(abs(x - 1000) < 1e-6 for x in q)                        # 12000 / 12 each month


# -- G: annual lump recognises the whole amount once per year --------------
def test_annual_lump_once_per_year():
    q = _seed(_exp(category=ExpenseCategory.INSURANCE, amount=12000,
                   frequency=ExpenseFrequency.YEARLY, recognition_method=RecognitionMethod.LUMP))
    assert q[0] == 12000 and q[12] == 12000
    assert sum(1 for x in q if x > 0) == 2                             # 2 years in the horizon


# -- quarterly spread vs lump ----------------------------------------------
def test_quarterly_spread_vs_lump():
    spread = _seed(_exp(category=ExpenseCategory.OTHER, amount=3000, frequency=ExpenseFrequency.QUARTERLY))
    assert all(abs(x - 1000) < 1e-6 for x in spread)                  # 3000 / 3 each month

    lump = _seed(_exp(category=ExpenseCategory.OTHER, amount=3000, frequency=ExpenseFrequency.QUARTERLY,
                      recognition_method=RecognitionMethod.LUMP))
    assert lump[0] == 3000 and lump[3] == 3000 and lump[1] == 0       # every 3 months


# -- annual totals are identical regardless of recognition -----------------
def test_annual_total_invariant_to_recognition():
    spread = _seed(_exp(category=ExpenseCategory.INSURANCE, amount=12000, frequency=ExpenseFrequency.YEARLY))
    lump = _seed(_exp(category=ExpenseCategory.INSURANCE, amount=12000, frequency=ExpenseFrequency.YEARLY,
                      recognition_method=RecognitionMethod.LUMP))
    assert abs(sum(spread) - sum(lump)) < 1e-6                         # same yearly cost, different shape


# -- backward compatibility -------------------------------------------------
def test_legacy_expense_loads_with_spread_default():
    # A legacy stored record has no recognition_method.
    exp = OperatingExpense.model_validate({"name": "X", "amount": 12000, "frequency": "yearly"})
    assert exp.recognition_method == RecognitionMethod.SPREAD
    q = oep.seed_amounts(exp, N, START)
    assert all(abs(x - 1000) < 1e-6 for x in q)           # unchanged smoothed behaviour


# -- temporary (start/end) still respected ---------------------------------
def test_temporary_start_end_window():
    q = _seed(_exp(category=ExpenseCategory.RENT, amount=1000, frequency=ExpenseFrequency.MONTHLY,
                   start_date=date(2026, 3, 1), end_date=date(2026, 6, 30)))
    assert q[0] == 0 and q[1] == 0
    assert all(q[t] == 1000 for t in range(2, 6))                     # Mar–Jun
    assert q[6] == 0
