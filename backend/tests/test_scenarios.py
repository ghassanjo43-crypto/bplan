"""Named saved scenarios per project — CRUD, default handling, backfill, and
per-scenario financial output (selected by scenario id).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ScenarioAssumption
from app.models.enums import ScenarioType
from app.services import financial_analysis_service as fas
from app.services import income_statement_service as isvc
from app.services import scenario_service as scn
from app.services.demo_builder import build_demo_project

PID = "demo_aquapure"


def _three_scenario_project():
    p = build_demo_project()
    p.scenarios = []
    scn.ensure_default(p)                                   # Base Case default
    opt = ScenarioAssumption(name="Upside", scenario_type=ScenarioType.OPTIMISTIC,
                             sales_volume_adjustment=20)
    con = ScenarioAssumption(name="Downside", scenario_type=ScenarioType.CONSERVATIVE,
                             sales_volume_adjustment=-15)
    p.scenarios += [opt, con]
    return p, p.scenarios[0], opt, con


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/api/demo/load-aquapure")
        yield c


# -- service-level: default handling + per-scenario output -------------------
def test_old_project_with_no_scenarios_gets_a_base_case():
    p = build_demo_project()
    p.scenarios = []
    assert scn.ensure_default(p) is True
    assert len(p.scenarios) == 1
    only = p.scenarios[0]
    assert only.name == "Base Case"
    assert only.scenario_type == ScenarioType.BASE
    assert only.is_default is True
    # idempotent — a second call changes nothing
    assert scn.ensure_default(p) is False


def test_project_can_hold_multiple_scenarios_and_output_is_per_scenario():
    p = build_demo_project()
    p.scenarios = []
    scn.ensure_default(p)                                   # Base Case
    optimistic = ScenarioAssumption(name="Aggressive Growth",
                                    scenario_type=ScenarioType.OPTIMISTIC,
                                    sales_volume_adjustment=20)
    conservative = ScenarioAssumption(name="Downside", scenario_type=ScenarioType.CONSERVATIVE,
                                      sales_volume_adjustment=-15)
    p.scenarios += [optimistic, conservative]
    assert len(p.scenarios) == 3

    base_rev = isvc.generate_income_statement(p, p.scenarios[0].id, "yearly").totals.total_revenue
    opt_rev = isvc.generate_income_statement(p, optimistic.id, "yearly").totals.total_revenue
    con_rev = isvc.generate_income_statement(p, conservative.id, "yearly").totals.total_revenue
    # Financial output is generated per scenario, selected by id.
    assert opt_rev > base_rev > con_rev


def test_set_default_marks_one_and_clears_the_rest():
    p = build_demo_project()
    p.scenarios = []
    scn.ensure_default(p)
    extra = ScenarioAssumption(name="Custom A", scenario_type=ScenarioType.CUSTOM)
    p.scenarios.append(extra)
    assert scn.set_default(p, extra.id) is extra
    assert [s.name for s in p.scenarios if s.is_default] == ["Custom A"]


# -- API-level CRUD ----------------------------------------------------------
def test_create_scenario_with_a_name(client):
    base = f"/api/projects/{PID}/scenarios"
    created = client.post(base, json={
        "name": "Investor Case", "description": "Pitch numbers",
        "scenario_type": "optimistic", "sales_volume_adjustment": 25,
    })
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Investor Case" and body["scenario_type"] == "optimistic"
    sid = body["id"]

    # update
    upd = client.put(f"{base}/{sid}", json={**body, "name": "Investor Case v2", "sales_volume_adjustment": 30})
    assert upd.status_code == 200 and upd.json()["name"] == "Investor Case v2"
    assert upd.json()["sales_volume_adjustment"] == 30

    # The statement routes accept a scenario *id* (the relaxed query validation);
    # per-scenario numeric output by id is asserted at the service level above.
    for stmt in ("income-statement", "balance-sheet", "cash-flow"):
        assert client.get(f"/api/projects/{PID}/{stmt}?scenario={sid}&view=yearly").status_code == 200

    client.delete(f"{base}/{sid}")


def test_duplicate_scenario_is_independent(client):
    base = f"/api/projects/{PID}/scenarios"
    src = client.post(base, json={"name": "Original", "scenario_type": "custom",
                                  "direct_cost_adjustment": 5}).json()
    dup_payload = {k: v for k, v in src.items() if k not in ("id", "created_at", "updated_at")}
    dup_payload["name"] = "Original (copy)"
    dup_payload["is_default"] = False
    dup = client.post(base, json=dup_payload)
    assert dup.status_code == 201
    dup_body = dup.json()
    assert dup_body["id"] != src["id"]                      # a distinct record
    assert dup_body["name"] == "Original (copy)"
    # editing the copy doesn't affect the original
    client.put(f"{base}/{dup_body['id']}", json={**dup_body, "direct_cost_adjustment": 99})
    again = next(s for s in client.get(base).json() if s["id"] == src["id"])
    assert again["direct_cost_adjustment"] == 5

    client.delete(f"{base}/{src['id']}")
    client.delete(f"{base}/{dup_body['id']}")


def test_deleting_one_scenario_keeps_project_and_others(client):
    base = f"/api/projects/{PID}/scenarios"
    a = client.post(base, json={"name": "Keep", "scenario_type": "base"}).json()
    b = client.post(base, json={"name": "Remove", "scenario_type": "custom"}).json()
    assert client.delete(f"{base}/{b['id']}").status_code in (200, 204)
    # project still loads and the other scenario survives
    assert client.get(f"/api/projects/{PID}").status_code == 200
    ids = {s["id"] for s in client.get(base).json()}
    assert a["id"] in ids and b["id"] not in ids
    client.delete(f"{base}/{a['id']}")


def test_ensure_default_endpoint_and_set_default_endpoint(client):
    base = f"/api/projects/{PID}/scenarios"
    ensured = client.post(f"{base}/ensure-default")
    assert ensured.status_code == 200
    scenarios = ensured.json()
    assert sum(1 for s in scenarios if s["is_default"]) == 1   # exactly one default

    new = client.post(base, json={"name": "New Default", "scenario_type": "custom"}).json()
    resp = client.post(f"{base}/{new['id']}/default")
    assert resp.status_code == 200 and resp.json()["is_default"] is True
    after = client.get(base).json()
    assert [s["id"] for s in after if s["is_default"]] == [new["id"]]
    client.delete(f"{base}/{new['id']}")


# -- Pass 2: side-by-side scenario comparison (by id) ------------------------
def _income_revenue(project, sid):
    r = isvc.generate_income_statement(project, sid, "yearly")
    sec = next(s for s in r.sections if s.key == "revenue")
    return [round(x, 2) for x in sec.subtotal.values_by_period]


def test_comparison_accepts_ids_for_two_scenarios():
    p, base, opt, _con = _three_scenario_project()
    cmp = fas.build_scenario_comparison(p, [base.id, opt.id], "yearly")
    keys = {m.key for m in cmp.metrics}
    assert {"revenue", "gross_profit", "gross_margin", "ebitda", "net_profit",
            "cash_balance", "break_even", "funding_requirement"} <= keys
    for m in cmp.metrics:
        assert [s.scenario for s in m.series] == [base.id, opt.id]      # selected by id


def test_comparison_works_for_three_scenarios():
    p, base, opt, con = _three_scenario_project()
    cmp = fas.build_scenario_comparison(p, [base.id, opt.id, con.id], "yearly")
    rev = next(m for m in cmp.metrics if m.key == "revenue")
    assert [s.scenario for s in rev.series] == [base.id, opt.id, con.id]
    # optimistic (+20% volume) tops base tops conservative (-15%)
    tot = {s.scenario: sum(s.values) for s in rev.series}
    assert tot[opt.id] > tot[base.id] > tot[con.id]


def test_comparison_metrics_match_individual_statement_output():
    p, base, opt, _con = _three_scenario_project()
    cmp = fas.build_scenario_comparison(p, [base.id, opt.id], "yearly")
    rev = next(m for m in cmp.metrics if m.key == "revenue")
    for s in rev.series:
        assert s.values == _income_revenue(p, s.scenario)             # same engine, same numbers


def test_comparison_unknown_id_falls_back_to_default_safely():
    p, base, _opt, _con = _three_scenario_project()   # base is the default
    cmp = fas.build_scenario_comparison(p, ["nope-not-real"], "yearly")
    # unknown id resolves to the default scenario (route convention: safe fallback)
    assert [s.scenario for s in cmp.metrics[0].series] == [base.id]


def test_comparison_route_accepts_scenarios_query(client):
    scns = client.get(f"/api/projects/{PID}/scenarios").json()
    ids = ",".join(s["id"] for s in scns[:2]) if len(scns) >= 2 else scns[0]["id"]
    r = client.get(f"/api/projects/{PID}/financial-analysis/scenario-comparison?scenarios={ids}&view=yearly")
    assert r.status_code == 200
    body = r.json()
    assert any(m["key"] == "funding_requirement" for m in body["metrics"])
