"""Tests for the business plan report generator (Word + PDF)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ScenarioAssumption
from app.models.enums import ScenarioType
from app.schemas.reports import ReportRequest
from app.services import income_statement_service as isvc
from app.services import pdf_report_service as pdfsvc
from app.services import report_data_service as rd
from app.services import scenario_service as scn
from app.services.demo_builder import build_demo_project
from app.services import word_report_service as wordsvc

PID = "demo_aquapure"
BASE = f"/api/projects/{PID}/reports"


@pytest.fixture(scope="module")
def project():
    return build_demo_project()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/api/demo/load-aquapure")
        yield c


@pytest.fixture
def req():
    return ReportRequest(scenario="base", view="yearly", report_style="investor")


# 1. Preview returns 200 with sections
def test_preview_200(client):
    r = client.get(f"{BASE}/business-plan/preview?scenario=base&view=yearly")
    assert r.status_code == 200
    body = r.json()
    assert body["company"]
    assert len(body["sections"]) == 12
    assert body["can_generate"] is True


# 2. Word generation returns 200 with download url
def test_generate_word_200(client):
    r = client.post(f"{BASE}/business-plan/generate-word",
                    json={"scenario": "base", "view": "yearly", "report_style": "investor"})
    assert r.status_code == 200
    body = r.json()
    assert body["format"] == "docx"
    assert body["status"] == "ready"
    assert body["size_bytes"] > 5000
    assert body["download_url"].endswith("/download")


# 3. Word file actually exists on disk and is a real .docx (zip magic)
def test_word_file_exists(project, req):
    f = wordsvc.generate_business_plan_docx(project, req)
    path = rd.report_path(project.id, f.file_name)
    assert path.exists()
    assert path.read_bytes()[:2] == b"PK"  # docx is a zip


# 4. PDF generation returns ready (pdf or html fallback)
def test_generate_pdf_200(client):
    r = client.post(f"{BASE}/business-plan/generate-pdf",
                    json={"scenario": "base", "view": "yearly", "report_style": "investor"})
    assert r.status_code == 200
    body = r.json()
    assert body["format"] in ("pdf", "html")
    assert body["status"] == "ready"
    assert body["size_bytes"] > 1000


# 5. PDF service produces a file on disk (pdf or html fallback) with content
def test_pdf_file_exists(project, req):
    f = pdfsvc.generate_business_plan_pdf(project, req)
    path = rd.report_path(project.id, f.file_name)
    assert path.exists()
    if f.format == "pdf":
        assert path.read_bytes()[:4] == b"%PDF"
    else:
        assert b"<html" in path.read_bytes()[:200].lower()


# 6. Report context carries income statement rows
def test_context_includes_income_statement(project, req):
    ctx = rd.build_report_context(project, "base", "yearly", req)
    rows = ctx["income_statement"]["rows"]
    assert any("Revenue" in r["label"] for r in rows)
    assert any(r["kind"] == "grand" for r in rows)


# 7. Report context carries balance sheet rows incl. a balance check
def test_context_includes_balance_sheet(project, req):
    ctx = rd.build_report_context(project, "base", "yearly", req)
    rows = ctx["balance_sheet"]["rows"]
    assert rows
    assert any(r["kind"] == "check" for r in rows)


# 8. Report context carries cash flow rows
def test_context_includes_cash_flow(project, req):
    ctx = rd.build_report_context(project, "base", "yearly", req)
    assert ctx["cash_flow"]["rows"]


# 9. Report context carries analysis KPIs + scenario comparison
def test_context_includes_analysis_and_scenarios(project, req):
    ctx = rd.build_report_context(project, "base", "yearly", req)
    assert ctx["fa_kpis"]
    assert ctx["scenario_comparison"]["rows"]
    vals = ctx["scenario_comparison"]["rows"][0]["values"]
    assert {"base", "conservative", "optimistic"} <= set(vals.keys())


# 10. Reconciliations are reported (balance + cash)
def test_context_includes_reconciliations(project, req):
    ctx = rd.build_report_context(project, "base", "yearly", req)
    labels = [r["label"] for r in ctx["reconciliations"]]
    assert any("Balance sheet balances" in l for l in labels)
    assert any("Cash flow reconciles" in l for l in labels)


# 11. List shows generated reports
def test_list_reports(client):
    client.post(f"{BASE}/business-plan/generate-word",
                json={"scenario": "base", "view": "yearly", "report_style": "investor"})
    r = client.get(BASE)
    assert r.status_code == 200
    assert len(r.json()) >= 1


# 12. Download returns the file bytes with a content type
def test_download(client):
    gen = client.post(f"{BASE}/business-plan/generate-word",
                      json={"scenario": "base", "view": "yearly", "report_style": "investor"}).json()
    r = client.get(gen["download_url"])
    assert r.status_code == 200
    assert r.content[:2] == b"PK"


# 13. Delete removes the report
def test_delete(client):
    gen = client.post(f"{BASE}/business-plan/generate-word",
                      json={"scenario": "base", "view": "yearly", "report_style": "investor"}).json()
    rid = gen["report_id"]
    assert client.delete(f"{BASE}/{rid}").status_code == 204
    assert client.get(f"{BASE}/{rid}/download").status_code == 404


# 14. Filenames are sanitized (no spaces / unsafe chars)
def test_filename_sanitized(project, req):
    f = wordsvc.generate_business_plan_docx(project, req)
    assert " " not in f.file_name
    assert all(c.isalnum() or c in "._-" for c in f.file_name)


# 15. Full investor report (all sections on) generates without error
def test_full_investor_report(project):
    req = ReportRequest(scenario="base", view="yearly", report_style="full",
                        include_charts=True, include_appendices=True,
                        include_assumptions=True, include_warnings=True)
    wf = wordsvc.generate_business_plan_docx(project, req)
    pf = pdfsvc.generate_business_plan_pdf(project, req)
    assert wf.size_bytes > 5000
    assert pf.size_bytes > 1000


# 16. Context exposes the app's chart sections for image rendering
def test_context_includes_chart_sections(project, req):
    ctx = rd.build_report_context(project, "base", "yearly", req)
    assert ctx["chart_sections"]
    total = sum(len(s["charts"]) for s in ctx["chart_sections"])
    assert total >= 10  # all dashboard charts, not just a subset
    assert ctx["scenario_metrics"]


# 17. Charts render to PNG images for every chart type used in the dashboard
def test_chart_rendering(project, req):
    from app.services import chart_render_service as cr
    ctx = rd.build_report_context(project, "base", "yearly", req)
    specs = [c for s in ctx["chart_sections"] for c in s["charts"]]
    rendered = cr.render_report_charts(specs, ctx["currency"])
    assert len(rendered) == len(specs)  # nothing failed to render
    for r in rendered:
        assert r["png"][:8] == b"\x89PNG\r\n\x1a\n"  # valid PNG signature


# 18. Generated Word document actually embeds the chart images
def test_word_embeds_chart_images(project, req):
    import zipfile
    f = wordsvc.generate_business_plan_docx(project, req)
    path = rd.report_path(project.id, f.file_name)
    with zipfile.ZipFile(path) as z:
        media = [n for n in z.namelist() if n.startswith("word/media/")]
    assert len(media) >= 10  # one file per embedded chart


# 19b. Financial statements print on a landscape Word section; the rest is portrait
def test_word_statements_landscape(project, req):
    from docx import Document
    from docx.enum.section import WD_ORIENT
    f = wordsvc.generate_business_plan_docx(project, req)
    doc = Document(str(rd.report_path(project.id, f.file_name)))
    orients = [s.orientation for s in doc.sections]
    assert WD_ORIENT.LANDSCAPE in orients          # statements section is landscape
    assert orients[0] == WD_ORIENT.PORTRAIT         # report starts portrait
    assert orients[-1] == WD_ORIENT.PORTRAIT        # and ends portrait
    # the landscape section's page is wider than tall
    land = next(s for s in doc.sections if s.orientation == WD_ORIENT.LANDSCAPE)
    assert land.page_width > land.page_height


# 19c. PDF renders the statements section on landscape pages
def test_pdf_statements_landscape(project, req):
    pypdf = pytest.importorskip("pypdf")
    f = pdfsvc.generate_business_plan_pdf(project, req)
    if f.format != "pdf":
        pytest.skip("PDF engine unavailable")
    reader = pypdf.PdfReader(str(rd.report_path(project.id, f.file_name)))
    landscape = [i for i, pg in enumerate(reader.pages)
                 if float(pg.mediabox.width) > float(pg.mediabox.height)]
    portrait = [i for i in range(len(reader.pages)) if i not in landscape]
    assert landscape                                # at least one landscape page
    assert portrait                                 # and the rest portrait
    # landscape pages are contiguous (the financial statements block)
    assert landscape == list(range(landscape[0], landscape[0] + len(landscape)))


# 19. When charts are disabled, no images are embedded
def test_charts_disabled_no_images(project):
    import zipfile
    req = ReportRequest(scenario="base", view="yearly", report_style="investor", include_charts=False)
    f = wordsvc.generate_business_plan_docx(project, req)
    path = rd.report_path(project.id, f.file_name)
    with zipfile.ZipFile(path) as z:
        media = [n for n in z.namelist() if n.startswith("word/media/")]
    assert media == []


# -- report scenario selection uses saved scenario ids ----------------------
def _custom_project(**kw):
    p = build_demo_project()
    scn.ensure_default(p)                                   # guarantee a default
    custom = ScenarioAssumption(name="Base Case Left", scenario_type=ScenarioType.CUSTOM,
                                sales_volume_adjustment=20, **kw)
    p.scenarios.append(custom)
    return p, custom


def test_custom_scenario_available_for_report_selection(client):
    """A scenario created via the API is available to the report dropdown
    (which reads the same /scenarios list)."""
    base = f"/api/projects/{PID}/scenarios"
    created = client.post(base, json={"name": "Base Case Left", "scenario_type": "custom",
                                      "sales_volume_adjustment": 20}).json()
    names = {s["name"]: s["id"] for s in client.get(base).json()}
    assert "Base Case Left" in names and names["Base Case Left"] == created["id"]
    client.delete(f"{base}/{created['id']}")


def test_report_generates_for_custom_scenario_id():
    p, custom = _custom_project()
    opts = ReportRequest(scenario=custom.id, view="yearly", report_style="investor")
    ctx = rd.build_report_context(p, custom.id, "yearly", opts)
    assert ctx["scenario"] == custom.id
    assert ctx["scenario_label"] == "Base Case Left"       # shows the name, not the raw id


def test_report_revenue_matches_income_statement_for_scenario():
    p, custom = _custom_project()
    opts = ReportRequest(scenario=custom.id, view="yearly", report_style="investor")
    ctx = rd.build_report_context(p, custom.id, "yearly", opts)
    is_total = isvc.generate_income_statement(p, custom.id, "yearly").totals.total_revenue
    rev_hi = next(h for h in ctx["highlights"] if "revenue" in h["label"].lower())
    assert rev_hi["value"] == rd.fmt_num(is_total)         # same scenario, same numbers
    # and the +20% volume scenario really differs from base
    base_total = isvc.generate_income_statement(p, "base", "yearly").totals.total_revenue
    assert is_total > base_total


def test_report_default_base_case_for_old_project_without_scenarios():
    p = build_demo_project()
    p.scenarios = []                                        # legacy project, no scenarios
    opts = ReportRequest(scenario="base", view="yearly", report_style="investor")
    ctx = rd.build_report_context(p, "base", "yearly", opts)
    assert ctx["scenario_label"] == "Base Case"            # safe default fallback
