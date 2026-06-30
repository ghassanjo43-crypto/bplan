"""Generate the business plan report as a PDF (HTML + CSS via WeasyPrint).

If WeasyPrint's native libraries are unavailable, this falls back to saving a
styled, print-ready HTML report (the browser can 'Print to PDF'). Word
generation is never affected by PDF availability.
"""
from __future__ import annotations

import base64
import html
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..models import BusinessPlanProject
from ..schemas.reports import ReportFile
from . import chart_render_service as chartsvc
from . import report_data_service as rd

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "reports"


def _e(v) -> str:
    return html.escape(str(v))


def _chart_img(rendered) -> str:
    b64 = base64.b64encode(rendered["png"]).decode("ascii")
    cap = f'<div class="chart__insight">{_e(rendered["insight"])}</div>' if rendered.get("insight") else ""
    return f'<figure class="chart"><img src="data:image/png;base64,{b64}" alt="{_e(rendered["title"])}" />{cap}</figure>'


def _img_attrs(tag: str) -> dict:
    return {m.group(1).lower(): m.group(3) for m in re.finditer(r'([\w:-]+)\s*=\s*(["\'])(.*?)\2', tag)}


def _data_uri(file_path: str, mime: str) -> str | None:
    from pathlib import Path
    try:
        data = Path(file_path).read_bytes()
    except Exception:
        return None
    return f"data:{mime or 'image/png'};base64,{base64.b64encode(data).decode('ascii')}"


def _inline_images(content_html: str, image_index: dict) -> str:
    """Rewrite each inline TipTap <img data-image-id> into a print-ready
    <figure class="topic-image align-..."> with a base64 data URI, embedded at
    its exact position. Missing files become a visible (non-fatal) placeholder."""
    def repl(match: re.Match) -> str:
        attrs = _img_attrs(match.group(0))
        image_id = attrs.get("data-image-id")
        meta = image_index.get(image_id) if image_id else None
        align = (attrs.get("data-alignment") or (meta or {}).get("alignment") or "center").lower()
        caption = attrs.get("data-caption") or (meta or {}).get("caption") or ""
        try:
            pct = int(float(attrs.get("data-width") or (meta or {}).get("width_pct") or 80))
        except (TypeError, ValueError):
            pct = 80
        if align == "full_width":
            pct = 100
        pct = min(max(pct, 10), 100)
        uri = _data_uri((meta or {}).get("file_path", ""), (meta or {}).get("mime_type", "image/png")) if meta else None
        if not uri:
            return '<div class="topic-image-missing">[Image unavailable]</div>'
        cap = f'<figcaption>{_e(caption)}</figcaption>' if caption else ""
        alt = _e(attrs.get("alt") or (meta or {}).get("alt_text") or "")
        return (f'<figure class="topic-image align-{_e(align)}" style="width:{pct}%">'
                f'<img src="{uri}" alt="{alt}" />{cap}</figure>')

    return re.sub(r"<img\b[^>]*>", repl, content_html or "")


def _sanitize_richtext(html_str: str) -> str:
    return re.sub(r"<script.*?</script>", "", html_str or "", flags=re.S | re.I)


def _text_plan_html(ctx) -> str:
    tp = ctx.get("text_plan") or {}
    if not tp.get("has_content"):
        return ""
    image_index = tp.get("image_index") or {}
    out = []
    for sec in tp["sections"]:
        out.append(f'<h1 class="section">{_e(sec["title"])}</h1>')
        if sec.get("description"):
            out.append(f'<p class="note">{_e(sec["description"])}</p>')
        for topic in sec["topics"]:
            out.append(f'<h2>{_e(topic["title"])}</h2>')
            if topic.get("guidance"):
                out.append(f'<div class="warn warn--info"><b>Guidance</b> &nbsp;{_e(topic["guidance"])}</div>')
            content = (topic.get("content_html") or "").strip()
            if content:
                body = _inline_images(_sanitize_richtext(content), image_index)
            else:
                body = f'<p>{_e(topic.get("plain_text") or "")}</p>'
            out.append(f'<div class="richtext">{body}</div>')
    return "".join(out)


# --------------------------------------------------------------------------
# HTML builders
# --------------------------------------------------------------------------
def _fin_table(periods, rows, currency, total_col=False):
    head = '<thead><tr><th class="left">Line item</th>'
    head += "".join(f"<th>{_e(p)}</th>" for p in periods)
    if total_col:
        head += "<th>Total</th>"
    head += "</tr></thead>"
    body = "<tbody>"
    for r in rows:
        kind = r.get("kind", "line")
        cls = {"subtotal": "subtotal", "grand": "grand", "section": "section", "group": "group", "check": "check"}.get(kind, "")
        label_cls = "indent" if kind == "line" else ""
        body += f'<tr class="{cls}"><td class="{label_cls}">{_e(r["label"])}</td>'
        vals = r.get("values", [])
        for i in range(len(periods)):
            v = vals[i] if i < len(vals) else None
            body += f'<td class="num">{_e(rd.fmt_num(v)) if (kind != "section" and vals) else ""}</td>'
        if total_col:
            body += f'<td class="num">{_e(rd.fmt_num(sum(vals))) if (vals and kind != "section") else ""}</td>'
        body += "</tr>"
    body += "</tbody>"
    return f"<table>{head}{body}</table>"


def _kv(items):
    pairs = items if isinstance(items, list) else [{"label": k, "value": v} for k, v in items.items()]
    rows = "".join(
        f'<tr><td class="k">{_e(it["label"])}</td><td class="v">'
        f'{_e(rd.fmt_num(it["value"]) if isinstance(it["value"], (int, float)) else it["value"])}</td></tr>'
        for it in pairs
    )
    return f'<table class="kv">{rows}</table>'


def _generic(headers, rows, numeric_cols=()):
    head = "<thead><tr>" + "".join(
        f'<th class="{"" if i in numeric_cols else "left"}">{_e(h)}</th>' for i, h in enumerate(headers)
    ) + "</tr></thead>"
    body = "<tbody>"
    for row in rows:
        body += "<tr>"
        for i, val in enumerate(row):
            if i in numeric_cols:
                body += f'<td class="num">{_e(rd.fmt_num(val) if isinstance(val, (int, float)) else val)}</td>'
            else:
                body += f"<td>{_e(val)}</td>"
        body += "</tr>"
    body += "</tbody>"
    return f"<table>{head}{body}</table>"


def _kpi_cards(items):
    cards = "".join(
        f'<div class="kpi"><div class="kpi__label">{_e(it["label"])}</div>'
        f'<div class="kpi__value">{_e(it["value"])}</div></div>'
        for it in items
    )
    return f'<div class="kpi-grid">{cards}</div>'


def _warn(message, severity):
    return f'<div class="warn warn--{severity}"><b>{_e(severity)}</b> &nbsp;{_e(message)}</div>'


def _cat_rows(cat_table, total_label):
    rows = [{"label": r["label"], "values": r["values"], "kind": "line"} for r in cat_table]
    if cat_table:
        n = len(cat_table[0]["values"])
        rows.append({"label": total_label, "values": [sum(r["values"][i] for r in cat_table) for i in range(n)], "kind": "subtotal"})
    return rows


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------
def render_report_html(ctx) -> str:
    m = ctx["meta"]
    P = ctx["periods"]
    cur = ctx["currency"]
    parts = []

    # cover
    proj = f'<div class="cover__project">{_e(m["project_name"])}</div>' if m["project_name"] and m["project_name"] != "–" else ""
    parts.append(f"""
    <section class="cover">
      <div class="cover__company">{_e(m["company"])}</div>{proj}
      <div class="cover__rule"></div>
      <div class="cover__title">{_e(m["title"])}</div>
      <div class="cover__subtitle">{_e(m["subtitle"])}</div>
      <div class="cover__meta">
        <div>Currency: <b>{_e(cur)}</b></div>
        <div>Scenario: <b>{_e(m["scenario_label"])}</b></div>
        <div>Projection period: <b>{_e(m["period_range"])}</b></div>
        <div>Prepared for: <b>{_e(m["prepared_for"])}</b></div>
        <div>Prepared: {_e(m["prepared_date"])}</div>
      </div>
      <div class="cover__confidential">CONFIDENTIAL</div>
    </section>""")

    # toc
    toc = "".join(f"<li>{_e(t)}</li>" for _k, t in rd.SECTIONS)
    parts.append(f'<section class="toc"><h1 class="section">Table of Contents</h1><ol>{toc}</ol></section>')

    # 1 executive summary
    ov = ctx["overview"]
    insights = "".join(f"<li>{_e(s)}</li>" for s in ctx["insights"])
    parts.append(f"""
    <h1 class="section">1. Executive Summary</h1>
    <p>{_e(ov.get("Description", ""))}</p>
    <p>This report presents a {_e(m["period_range"])} projected financial study for {_e(m["company"])}
       under the {_e(ctx["scenario_label"])}, prepared in {_e(cur)}.</p>
    <h2>Key projected highlights</h2>{_kpi_cards(ctx["highlights"])}
    {f'<h2>Analytical commentary</h2><ul>{insights}</ul>' if insights else ''}""")

    # textual business plan (written narrative) — before the financial study
    parts.append(_text_plan_html(ctx))

    # 2 business overview
    parts.append(f'<h1 class="section">2. Business Overview</h1>{_kv(ctx["overview"])}')

    # 3 products & revenue
    prod_rows = [[p["name"], p["category"], p["revenue_type"], p["unit"], p["price"], p["launch"], p["active"]] for p in ctx["products"]]
    timing_html = ""
    if ctx.get("revenue_timing"):
        tr = [[r["name"], r["timing"], r["unit"], r["start"], r["end"], r["duration"], r["recognition"], r["payment_terms"]]
              for r in ctx["revenue_timing"]]
        timing_html = (f'<h2>Revenue timing &amp; recurrence</h2>'
                       f'<p class="note"><em>{ctx["timing_notes"][0]}</em></p>'
                       + _generic(["Stream", "Timing / recurrence", "Selling unit", "Start", "End",
                                   "Contract mo.", "Recognition", "Payment terms"], tr))
    parts.append(f"""
    <h1 class="section">3. Products and Revenue Model</h1>
    <h2>Products and services</h2>
    {_generic(["Product / Service", "Category", "Revenue type", "Unit", "Price", "Launch", "Status"], prod_rows, numeric_cols=(4,))}
    {timing_html}
    <h2>Revenue by stream</h2>
    {_fin_table(P, _cat_rows(ctx["revenue_table"], "Total revenue"), cur, total_col=True)}""")

    # 4-7 assumptions
    if ctx["options"].include_assumptions:
        staff_rows = [[s["department"], s["title"], s["employees"], s["salary"], s["start"]] for s in ctx["staffing"]]
        asset_rows = [[a["name"], a["category"], a["purchase_amount"], a["useful_life"], a["method"], a["nbv"]] for a in ctx["fixed_assets"]]
        loans = ctx["financing"]["loans"]
        loan_html = ""
        if loans:
            lr = [[l["name"], l["amount"], rd.fmt_pct(l["rate"]), l["term"], l["grace"], l["type"]] for l in loans]
            loan_html = "<h3>Loans</h3>" + _generic(["Loan", "Amount", "Rate", "Term (m)", "Grace (m)", "Repayment"], lr, numeric_cols=(1,))
        dc_detail_html = ""
        if ctx.get("direct_costs_detail"):
            dr = [[c["name"], c["method"], c["association"], c["linked"], c["supplier_terms"], c["start"], c["end"], c["value"]]
                  for c in ctx["direct_costs_detail"]]
            dc_detail_html = (f'<p class="note"><em>{ctx["timing_notes"][2]}</em></p>'
                              + _generic(["Cost item", "Method", "Linked product(s)", "Link", "Supplier terms",
                                          "Start", "End", "Amount / %"], dr))
        opex_detail_html = ""
        if ctx.get("operating_expenses_detail"):
            orw = [[e["name"], e["category"], e["timing"], e["recognition"], e["start"], e["end"], e["inflation"]]
                   for e in ctx["operating_expenses_detail"]]
            opex_detail_html = (f'<p class="note"><em>{ctx["timing_notes"][1]}</em></p>'
                                + _generic(["Expense", "Category", "Timing / recurrence", "Recognition", "Start", "End", "Escalation"], orw))
        parts.append(f"""
        <h1 class="section">4. Projection Assumptions</h1>
        <h2>Direct cost of sales</h2>{_fin_table(P, _cat_rows(ctx["direct_cost_table"], "Total cost of sales"), cur, total_col=True)}
        {dc_detail_html}
        <h2>Operating expenses</h2>{_fin_table(P, _cat_rows(ctx["opex_table"], "Total operating expenses"), cur, total_col=True)}
        {opex_detail_html}
        <h1 class="section">5. Operating Model</h1>
        <h2>Staffing plan</h2>{_generic(["Department", "Role", "Employees", "Monthly salary", "Start date"], staff_rows, numeric_cols=(2, 3))}
        {f'<h2>Total staff cost by year</h2>{_fin_table(P, _cat_rows(ctx["staff_by_dept"], "Total staff cost"), cur, total_col=True)}' if ctx["staff_by_dept"] else ''}
        <h1 class="section">6. Capital Expenditure and Assets</h1>
        {_generic(["Asset", "Category", "Cost", "Life (yrs)", "Method", "NBV (final year)"], asset_rows, numeric_cols=(2, 3, 5))}
        <h1 class="section">7. Working Capital and Financing</h1>
        <h2>Working capital assumptions</h2>{_kv(ctx["working_capital"])}
        <h2>Equity funding</h2>{_kv(ctx["financing"]["equity"])}
        {loan_html}
        <h2>Tax and VAT</h2>{_kv(ctx["tax"])}
        <h2>KPI targets</h2>{_kv(ctx["kpis"])}""")

    # 8 statements — printed on landscape pages (they are wide)
    period = m["period_range"]

    def _stmt_head(title, when):
        proj = f'<div class="stmt-head__project">{_e(m["project_name"])}</div>' if m.get("project_name") else ""
        return (f'<div class="stmt-head"><div class="stmt-head__company">{_e(m["company"])}</div>'
                f'<div class="stmt-head__title">{_e(title)}</div>{proj}'
                f'<div class="stmt-head__when">{_e(when)}</div></div>')

    parts.append(f"""
    <section class="landscape-section">
    <h1 class="section">8. Financial Statements</h1>
    <p class="note">All figures in {_e(cur)}. Negative amounts are shown in parentheses; a dash indicates a nil balance.</p>
    {_stmt_head("Statement of Profit or Loss", f"For the projected period {period}")}{_fin_table(P, ctx["income_statement"]["rows"], cur)}
    {_stmt_head("Statement of Financial Position", f"As at the end of the projected period ({period})")}{_fin_table(P, ctx["balance_sheet"]["rows"], cur)}
    {_stmt_head("Statement of Cash Flows (indirect method)", f"For the projected period {period}")}{_fin_table(P, ctx["cash_flow"]["rows"], cur)}
    </section>""")

    # 9 analysis
    analysis = f'<h1 class="section">9. Financial Analysis</h1><h2>Key performance indicators</h2>' + \
               _kpi_cards([{"label": k["label"], "value": k["value"]} for k in ctx["fa_kpis"]])
    if ctx["options"].include_charts and ctx.get("chart_sections"):
        analysis += ('<p class="note">The charts below are generated from the projected financial statements and '
                     'mirror the application\'s Financial Analysis dashboard.</p>')
        for sec in ctx["chart_sections"]:
            analysis += f'<h2>{_e(sec["title"])}</h2>'
            if sec.get("description"):
                analysis += f'<p class="note">{_e(sec["description"])}</p>'
            for rendered in chartsvc.render_report_charts(sec["charts"], cur):
                analysis += _chart_img(rendered)
    parts.append(analysis)

    # 10 scenario comparison
    sc = ctx["scenario_comparison"]
    sc_rows = "".join(
        f'<tr><td>{_e(r["label"])}</td>' + "".join(
            f'<td class="num">{_e(rd.fmt_pct(r["values"].get(s)) if r["format"]=="percent" else rd.fmt_num(r["values"].get(s)))}</td>'
            for s in ("base", "conservative", "optimistic")) + "</tr>"
        for r in sc["rows"])
    scenario_imgs = ""
    if ctx["options"].include_charts and ctx.get("scenario_metrics"):
        for rendered in chartsvc.render_scenario_charts(ctx["scenario_metrics"], ctx["scenario_periods"], cur):
            scenario_imgs += _chart_img(rendered)
    parts.append(f"""
    <h1 class="section">10. Scenario Comparison</h1>
    {scenario_imgs}
    <h2>Scenario summary</h2>
    <table><thead><tr><th class="left">Metric</th><th>Base Case</th><th>Conservative Case</th><th>Optimistic Case</th></tr></thead>
    <tbody>{sc_rows}</tbody></table>""")

    # 11 risks
    if ctx["options"].include_warnings:
        rec = "".join(_warn(f'{r["label"]}: {"PASS" if r["status"] else "REVIEW REQUIRED"}', "info" if r["status"] else "critical")
                      for r in ctx["reconciliations"])
        warns = "".join(_warn(w["message"], w["severity"]) for w in ctx["warnings"]) or '<p class="note">No warnings — the projection is internally consistent.</p>'
        parts.append(f'<h1 class="section">11. Risks, Warnings and Reconciliations</h1><h2>Reconciliation checks</h2>{rec}<h2>Warnings</h2>{warns}')

    # 12 appendices
    if ctx["options"].include_appendices:
        ar = [[a["name"], a["category"], a["purchase_amount"], a["useful_life"], a["residual"], a["nbv"]] for a in ctx["fixed_assets"]]
        parts.append(f"""
        <h1 class="section">12. Appendices</h1>
        <h2>Appendix A — Revenue by stream</h2>{_fin_table(P, _cat_rows(ctx["revenue_table"], "Total revenue"), cur, total_col=True)}
        <h2>Appendix E — Fixed asset register</h2>{_generic(["Asset", "Category", "Cost", "Life", "Residual", "NBV"], ar, numeric_cols=(2, 4, 5))}""")

    css = (TEMPLATE_DIR / "business_plan_report.css").read_text(encoding="utf-8")
    shell = (TEMPLATE_DIR / "business_plan_report.html").read_text(encoding="utf-8")
    return shell.replace("{css}", css).replace("{title}", _e(m["title"])).replace("{company}", _e(m["company"])).replace("{content}", "".join(parts))


def render_pdf_from_html(html_str: str) -> bytes:
    import weasyprint
    return weasyprint.HTML(string=html_str).write_pdf()


def generate_business_plan_pdf(project: BusinessPlanProject, request) -> ReportFile:
    ctx = rd.build_report_context(project, request.scenario, request.view, request)
    html_str = render_report_html(ctx)
    report_id = uuid.uuid4().hex
    base = rd.sanitize_filename(f"business_plan_report_{ctx['meta']['company']}_{request.scenario}_{datetime.now():%Y%m%d}")

    fmt, message = "pdf", None
    try:
        content = render_pdf_from_html(html_str)
        file_name = f"{base}_{report_id[:6]}.pdf"
    except Exception as exc:  # WeasyPrint native libs unavailable -> HTML fallback
        fmt = "html"
        message = (f"PDF engine unavailable ({type(exc).__name__}); a print-ready HTML report was generated instead "
                   f"(open it and use the browser 'Print to PDF').")
        content = html_str.encode("utf-8")
        file_name = f"{base}_{report_id[:6]}.html"

    path = rd.report_path(project.id, file_name)
    path.write_bytes(content)
    entry = ReportFile(report_id=report_id, file_name=file_name, format=fmt, scenario=request.scenario,
                       view=request.view, report_style=request.report_style, status="ready",
                       size_bytes=path.stat().st_size, created_at=datetime.now(timezone.utc), message=message)
    rd.add_index_entry(project.id, entry.model_dump(mode="json"))
    return entry
