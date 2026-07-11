from __future__ import annotations

import html
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

REPORT_PAGE_TITLE = "StrategAI Report"
REPORT_MAX_TABLE_ROWS = int(os.getenv("REPORT_MAX_TABLE_ROWS", "20"))
REPORT_PDF_FORMAT = os.getenv("REPORT_PDF_FORMAT", "A4")
REPORT_BROWSER_PATH = os.getenv("REPORT_BROWSER_PATH") or os.getenv("PLAYWRIGHT_CHROMIUM_PATH")


class ReportRenderError(RuntimeError):
    """Raised when the PDF renderer cannot complete a report export."""


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}"
    return str(value)


def _format_datetime(value: Any) -> str:
    if not value:
        return "N/A"
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%b %d, %Y %I:%M %p UTC")


def _format_number(value: Any, decimals: int = 0) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "0"
    if decimals > 0:
        return f"{numeric:,.{decimals}f}"
    if numeric.is_integer():
        return f"{int(numeric):,}"
    return f"{numeric:,.2f}"


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "report"


def _find_browser_path() -> Optional[str]:
    if REPORT_BROWSER_PATH:
        candidate = Path(REPORT_BROWSER_PATH)
        if candidate.exists():
            return str(candidate)

    candidates = [
        Path(os.environ.get("ProgramFiles", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe",
    ]
    for candidate in candidates:
        if str(candidate) and candidate.exists():
            return str(candidate)
    return None


def _render_kv_card(label: str, value: Any, accent: str = "") -> str:
    safe_label = html.escape(label)
    safe_value = html.escape(_safe_text(value) or "N/A")
    return f"""
        <div class="metric-card {accent}">
            <div class="metric-label">{safe_label}</div>
            <div class="metric-value">{safe_value}</div>
        </div>
    """


def _render_table_rows(rows: List[Dict[str, Any]], row_type: str) -> str:
    rendered: List[str] = []
    for row in rows[:REPORT_MAX_TABLE_ROWS]:
        if row_type == "wholesale":
            rendered.append(
                f"""
                <tr>
                    <td>{html.escape(_safe_text(row.get("supplier") or row.get("vendor_name") or "N/A"))}</td>
                    <td>{html.escape(_safe_text(row.get("platform") or row.get("platform_name") or "N/A"))}</td>
                    <td>{html.escape(_safe_text(row.get("unit_price_pkr") or row.get("unit_price") or row.get("price_pkr") or 0))}</td>
                    <td>{html.escape(_safe_text(row.get("moq") or row.get("moq_listing") or 0))}</td>
                    <td>{html.escape(_safe_text(row.get("origin") or row.get("vendor_location") or ""))}</td>
                </tr>
                """
            )
        else:
            rendered.append(
                f"""
                <tr>
                    <td>{html.escape(_safe_text(row.get("platform") or "N/A"))}</td>
                    <td>{html.escape(_safe_text(row.get("seller") or row.get("seller_name") or "N/A"))}</td>
                    <td>{html.escape(_safe_text(row.get("list_price") or row.get("price_pkr") or 0))}</td>
                    <td>{html.escape(_safe_text(row.get("title") or row.get("raw_title") or ""))}</td>
                    <td>{html.escape(_safe_text(row.get("promo") or row.get("stock_status") or ""))}</td>
                </tr>
                """
            )
    return "\n".join(rendered)


def _render_price_history_rows(rows: List[Dict[str, Any]]) -> str:
    rendered: List[str] = []
    for row in rows[:REPORT_MAX_TABLE_ROWS]:
        wholesale_avg = _coerce_float(row.get("wholesale_avg_price_pkr"))
        retail_avg = _coerce_float(row.get("retail_avg_price_pkr"))
        spread = max(0.0, retail_avg - wholesale_avg)
        rendered.append(
            f"""
                <tr>
                    <td>{html.escape(_safe_text(row.get("pipeline_run_id") or "N/A"))}</td>
                    <td>{html.escape(_format_datetime(row.get("captured_at")))}</td>
                    <td>{html.escape(_format_number(wholesale_avg))} PKR</td>
                    <td>{html.escape(_format_number(retail_avg))} PKR</td>
                    <td>{html.escape(_format_number(spread))} PKR</td>
                </tr>
            """
        )
    return "\n".join(rendered)


def build_report_html(report: Dict[str, Any]) -> str:
    title = html.escape(_safe_text(report.get("report_title") or "Product Report"))
    product_name = html.escape(_safe_text(report.get("product_name") or "Unknown product"))
    category_raw = _safe_text(report.get("category") or "")
    category = html.escape(category_raw)
    generated_at = html.escape(_format_datetime(report.get("generated_at")))
    summary = report.get("summary") or {}
    wholesale = report.get("wholesale") or []
    retail = report.get("retail") or []
    recommendations = report.get("recommendations") or {}
    analytics = report.get("analytics_recommendation") or {}
    price_history = report.get("price_history") or []
    supplier_rec = recommendations.get("supplier") or {}
    retail_rec = recommendations.get("retail_platform") or recommendations.get("retailPlatform") or {}

    recommended_buy = summary.get("recommended_buy_price", summary.get("best_wholesale_price", 0))
    recommended_sell = summary.get("recommended_sell_price", summary.get("best_retail_price", 0))
    gross_margin = summary.get("gross_margin_percent", summary.get("expected_profit_margin", summary.get("estimated_profit", 0)))
    gross_profit = summary.get("gross_profit_pkr", summary.get("observed_market_spread", summary.get("expected_profit_pkr", 0)))
    confidence_band = summary.get("confidence_band", analytics.get("confidence_band", "limited"))
    confidence_score = summary.get("confidence_score", analytics.get("confidence_score", 0))
    low_sample_warning = bool(summary.get("low_sample_warning", analytics.get("low_sample_warning", False)))
    low_sample_reason = summary.get("low_sample_reason") or analytics.get("low_sample_reason") or ""
    reasoning_bullets = analytics.get("reasoning_bullets") or []

    observed_wholesale_min = summary.get("observed_wholesale_min", summary.get("best_wholesale_price", 0))
    observed_wholesale_max = summary.get("observed_wholesale_max", summary.get("best_wholesale_price", 0))
    observed_retail_min = summary.get("observed_retail_min", summary.get("best_retail_price", 0))
    observed_retail_max = summary.get("observed_retail_max", summary.get("best_retail_price", 0))
    observed_market_spread = summary.get(
        "observed_market_spread",
        max(0, float(summary.get("best_retail_price", 0) or 0) - float(summary.get("best_wholesale_price", 0) or 0)),
    )

    reasoning_html = "".join(f"<li>{html.escape(str(bullet))}</li>" for bullet in reasoning_bullets)
    low_sample_html = ""
    if low_sample_warning:
        low_sample_html = f"""
            <div class="card" style="margin-top: 12px; border-color: rgba(217, 119, 6, 0.2); background: rgba(217, 119, 6, 0.05);">
                <div class="card-head">
                    <h3>Low Confidence - Based on Limited Data</h3>
                </div>
                <div class="report-info">
                    <p><strong>Reason:</strong> {html.escape(low_sample_reason or 'The current sample is small and should be treated conservatively.')}</p>
                </div>
            </div>
        """
    reasoning_section = ""
    if reasoning_html:
        reasoning_section = f"""
            <div class="card" style="margin-top: 12px;">
                <div class="card-head">
                    <h3>Recommendation Reasoning</h3>
                </div>
                <ul class="bullet-list">
                    {reasoning_html}
                </ul>
            </div>
        """

    wholesale_rows = _render_table_rows(wholesale, "wholesale")
    retail_rows = _render_table_rows(retail, "retail")
    history_rows = _render_price_history_rows(price_history)

    wholesale_more = ""
    if len(wholesale) > REPORT_MAX_TABLE_ROWS:
        wholesale_more = f"<p class=\"table-note\">Showing first {REPORT_MAX_TABLE_ROWS} of {len(wholesale)} wholesale rows.</p>"
    retail_more = ""
    if len(retail) > REPORT_MAX_TABLE_ROWS:
        retail_more = f"<p class=\"table-note\">Showing first {REPORT_MAX_TABLE_ROWS} of {len(retail)} retail rows.</p>"

    category_phrase = f" in {category}" if category_raw else ""

    recommendations_section = ""
    if supplier_rec or retail_rec:
        recommendation_cards = []
        if supplier_rec:
            recommendation_cards.append(
                f"""
                <div class="callout callout-cyan">
                    <h4>Recommended Supplier</h4>
                    <p><strong>Supplier:</strong> {html.escape(_safe_text(supplier_rec.get("supplier") or supplier_rec.get("vendor_name") or "N/A"))}</p>
                    <p><strong>Platform:</strong> {html.escape(_safe_text(supplier_rec.get("platform") or supplier_rec.get("platform_name") or "N/A"))}</p>
                    <p><strong>Unit Price:</strong> {html.escape(_safe_text(supplier_rec.get("unit_price_pkr") or supplier_rec.get("unit_price") or 0))} PKR</p>
                    <p><strong>MOQ:</strong> {html.escape(_safe_text(supplier_rec.get("moq") or supplier_rec.get("moq_listing") or 0))} units</p>
                </div>
                """
            )
        if retail_rec:
            recommendation_cards.append(
                f"""
                <div class="callout callout-indigo">
                    <h4>Recommended Retail Platform</h4>
                    <p><strong>Platform:</strong> {html.escape(_safe_text(retail_rec.get("platform") or "N/A"))}</p>
                    <p><strong>Seller:</strong> {html.escape(_safe_text(retail_rec.get("seller") or retail_rec.get("seller_name") or "N/A"))}</p>
                    <p><strong>List Price:</strong> {html.escape(_safe_text(retail_rec.get("list_price") or retail_rec.get("price_pkr") or 0))} PKR</p>
                </div>
                """
            )
        recommendations_section = f"""
        <section class="section">
            <div class="card">
                <div class="card-head">
                    <h3>Recommendations</h3>
                </div>
                <div class="two-col">
                    {''.join(recommendation_cards)}
                </div>
            </div>
        </section>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <style>
        :root {{
            color-scheme: light;
            --ink: #0f172a;
            --muted: #64748b;
            --line: #e2e8f0;
            --bg: #f8fafc;
            --panel: #ffffff;
            --accent: #0891b2;
            --accent-2: #4f46e5;
            --success: #059669;
            --danger: #dc2626;
        }}
        * {{ box-sizing: border-box; }}
        @page {{
            size: {REPORT_PDF_FORMAT};
            margin: 18mm 14mm 18mm 14mm;
        }}
        html, body {{
            margin: 0;
            padding: 0;
            background: var(--bg);
            color: var(--ink);
            font-family: Arial, Helvetica, sans-serif;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        body {{
            padding: 18px;
        }}
        .sheet {{
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 24px;
            overflow: hidden;
            box-shadow: 0 18px 60px rgba(15, 23, 42, 0.08);
        }}
        .hero {{
            padding: 28px 30px;
            background: linear-gradient(135deg, rgba(8, 145, 178, 0.10), rgba(79, 70, 229, 0.10));
            border-bottom: 1px solid var(--line);
        }}
        .eyebrow {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            color: var(--muted);
            margin-bottom: 10px;
        }}
        h1 {{
            margin: 0;
            font-size: 30px;
            line-height: 1.1;
        }}
        .subhead {{
            margin-top: 8px;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.6;
        }}
        .meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 14px;
            margin-top: 16px;
            font-size: 12px;
            color: var(--muted);
        }}
        .meta strong {{
            color: var(--ink);
        }}
        .section {{
            padding: 24px 30px 0 30px;
            break-inside: avoid;
        }}
        .section-title {{
            margin: 0 0 12px 0;
            font-size: 18px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
        }}
        .metric-card {{
            min-height: 88px;
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 14px;
        }}
        .metric-card.accent {{
            border-color: rgba(8, 145, 178, 0.18);
            background: linear-gradient(180deg, rgba(8, 145, 178, 0.05), rgba(8, 145, 178, 0.02));
        }}
        .metric-card.accent-2 {{
            border-color: rgba(79, 70, 229, 0.18);
            background: linear-gradient(180deg, rgba(79, 70, 229, 0.05), rgba(79, 70, 229, 0.02));
        }}
        .metric-card.success {{
            border-color: rgba(5, 150, 105, 0.18);
            background: linear-gradient(180deg, rgba(5, 150, 105, 0.05), rgba(5, 150, 105, 0.02));
        }}
        .metric-card.danger {{
            border-color: rgba(220, 38, 38, 0.18);
            background: linear-gradient(180deg, rgba(220, 38, 38, 0.05), rgba(220, 38, 38, 0.02));
        }}
        .metric-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--muted);
            margin-bottom: 10px;
        }}
        .metric-value {{
            font-size: 18px;
            font-weight: 700;
            line-height: 1.25;
            word-break: break-word;
        }}
        .profit-positive {{
            color: var(--success);
        }}
        .profit-negative {{
            color: var(--danger);
        }}
        .card {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 18px;
        }}
        .callout {{
            border-radius: 16px;
            border: 1px solid var(--line);
            padding: 16px;
            background: #fff;
        }}
        .callout h4 {{
            margin: 0 0 10px 0;
            font-size: 14px;
        }}
        .callout p {{
            margin: 0 0 6px 0;
            font-size: 12px;
            color: var(--ink);
            line-height: 1.5;
        }}
        .callout-cyan {{
            border-color: rgba(8, 145, 178, 0.18);
            background: rgba(8, 145, 178, 0.05);
        }}
        .callout-indigo {{
            border-color: rgba(79, 70, 229, 0.18);
            background: rgba(79, 70, 229, 0.05);
        }}
        .report-info p {{
            margin: 0 0 6px 0;
            font-size: 12px;
            line-height: 1.5;
        }}
        .card + .card {{
            margin-top: 12px;
        }}
        .card-head {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: baseline;
            margin-bottom: 12px;
        }}
        .card-head h3 {{
            margin: 0;
            font-size: 15px;
        }}
        .table-note {{
            margin: 10px 0 0 0;
            font-size: 11px;
            color: var(--muted);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
            font-size: 11px;
        }}
        thead {{
            display: table-header-group;
        }}
        th, td {{
            border-bottom: 1px solid var(--line);
            padding: 9px 8px;
            text-align: left;
            vertical-align: top;
            word-wrap: break-word;
        }}
        th {{
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--muted);
        }}
        .two-col {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
        }}
        .bullet-list {{
            margin: 0;
            padding-left: 18px;
        }}
        .bullet-list li {{
            margin: 0 0 6px 0;
            color: var(--ink);
            line-height: 1.5;
        }}
        .footer-space {{
            height: 12px;
        }}
    </style>
</head>
<body>
    <div class="sheet">
        <section class="hero">
            <div class="eyebrow">StrategAI Report</div>
            <h1>{title}</h1>
            <div class="subhead">
                Professional market analysis for <strong>{product_name}</strong>{category_phrase}.
                This PDF mirrors the on-screen report and includes the same summary, supplier, and retail data.
            </div>
            <div class="meta">
                <span><strong>Generated:</strong> {generated_at}</span>
                <span><strong>Wholesale rows:</strong> {len(wholesale)}</span>
                <span><strong>Retail rows:</strong> {len(retail)}</span>
            </div>
        </section>

        <section class="section">
            <h2 class="section-title">Executive Summary</h2>
            <div class="grid">
                {_render_kv_card("Total Suppliers", summary.get("total_suppliers", 0), "accent")}
                {_render_kv_card("Retail Listings", summary.get("total_retailers", 0), "accent-2")}
                {_render_kv_card("Recommended Buy", f"PKR {_format_number(recommended_buy)}", "accent")}
                {_render_kv_card("Recommended Sell", f"PKR {_format_number(recommended_sell)}", "accent-2")}
            </div>
            <div class="grid" style="margin-top: 12px;">
                <div class="metric-card {'success' if float(recommended_sell or 0) > float(recommended_buy or 0) else 'danger'}">
                    <div class="metric-label">Gross Margin</div>
                    <div class="metric-value profit-{('positive' if float(recommended_sell or 0) > float(recommended_buy or 0) else 'negative')}">{_format_number(gross_margin, 1)}%</div>
                </div>
                {_render_kv_card("Gross Profit", f"PKR {_format_number(gross_profit)}", "accent")}
                {_render_kv_card("Confidence", f"{_format_number(float(confidence_score or 0) * 100, 0)}%", "accent")}
                {_render_kv_card("Observed Market Spread", f"PKR {_format_number(observed_market_spread)}", "accent-2")}
            </div>
            <div class="grid" style="margin-top: 12px;">
                {_render_kv_card("Evidence Basis", "Observed market spread only", "accent")}
                {_render_kv_card("Confidence Band", confidence_band.title(), "accent-2")}
                {_render_kv_card("Analysis Focus", product_name, "accent")}
                {_render_kv_card("Report Format", "PDF Export", "accent-2")}
            </div>
            {low_sample_html}
            {reasoning_section}
            <div class="grid" style="margin-top: 12px;">
                {_render_kv_card("Generation Time", generated_at, "accent")}
                {_render_kv_card("Observed Wholesale Band", f"PKR {_format_number(observed_wholesale_min)} - {_format_number(observed_wholesale_max)}", "accent")}
                {_render_kv_card("Observed Retail Band", f"PKR {_format_number(observed_retail_min)} - {_format_number(observed_retail_max)}", "accent-2")}
                {_render_kv_card("Observed Market Spread", f"PKR {_format_number(observed_market_spread)}", "accent-2")}
            </div>
        </section>

        <section class="section">
            <div class="card">
                <div class="card-head">
                    <h3>Wholesale Suppliers Analysis</h3>
                    <span class="table-note">{len(wholesale)} total records</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Supplier</th>
                            <th>Platform</th>
                            <th>Unit Price</th>
                            <th>MOQ</th>
                            <th>Origin</th>
                        </tr>
                    </thead>
                    <tbody>
                        {wholesale_rows or '<tr><td colspan="5">No wholesale records available.</td></tr>'}
                    </tbody>
                </table>
                {wholesale_more}
            </div>
        </section>

        <section class="section">
            <div class="card">
                <div class="card-head">
                    <h3>Retail Market Analysis</h3>
                    <span class="table-note">{len(retail)} total records</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Platform</th>
                            <th>Seller</th>
                            <th>List Price</th>
                            <th>Product Title</th>
                            <th>Promo / Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {retail_rows or '<tr><td colspan="5">No retail records available.</td></tr>'}
                    </tbody>
                </table>
                {retail_more}
            </div>
        </section>

        {recommendations_section}

        {f'''
        <section class="section">
            <div class="card">
                <div class="card-head">
                    <h2 class="section-title">Price History</h2>
                    <h3>Historical Price Trend</h3>
                    <span class="table-note">{len(price_history)} tracked runs</span>
                </div>
                <div class="grid" style="margin-bottom: 12px;">
                    {_render_kv_card("Latest Wholesale Avg", f"PKR {_format_number((price_history or [{}])[-1].get('wholesale_avg_price_pkr', 0))}", "accent")}
                    {_render_kv_card("Latest Retail Avg", f"PKR {_format_number((price_history or [{}])[-1].get('retail_avg_price_pkr', 0))}", "accent-2")}
                    {_render_kv_card("Trend Summary", ("Single snapshot - trend unavailable" if len(price_history) < 2 else f"{_safe_text((price_history or [{}])[-1].get('retail_avg_price_pkr', 0) - (price_history or [{}])[0].get('retail_avg_price_pkr', 0))} PKR retail change"), "success")}
                    {_render_kv_card("Runs Tracked", len(price_history), "accent")}
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Run ID</th>
                            <th>Captured</th>
                            <th>Wholesale Avg</th>
                            <th>Retail Avg</th>
                            <th>Spread</th>
                        </tr>
                    </thead>
                    <tbody>
                        {history_rows or '<tr><td colspan="5">No historical price runs available.</td></tr>'}
                    </tbody>
                </table>
            </div>
        </section>
        ''' if price_history else ''}

        <section class="section">
            <h2 class="section-title">Report Information</h2>
            <div class="card">
                <div class="card-head">
                    <h3>Report Information</h3>
                </div>
                <div class="report-info">
                    <p><strong>Generated:</strong> {generated_at}</p>
                    <p><strong>Product:</strong> {product_name}</p>
                    <p><strong>Data Sources:</strong> Made-in-China, Daraz, Mega.pk, Homeshopping.pk, Telemart.pk</p>
                </div>
            </div>
        </section>
        <div class="footer-space"></div>
    </div>
</body>
</html>"""


async def render_report_pdf(report: Dict[str, Any]) -> bytes:
    html_content = build_report_html(report)
    browser_path = _find_browser_path()

    browser = None
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                executable_path=browser_path,
                args=["--disable-dev-shm-usage"],
            )
            page = await browser.new_page(viewport={"width": 1440, "height": 1600})
            await page.set_content(html_content, wait_until="networkidle")
            await page.emulate_media(media="print")
            pdf_bytes = await page.pdf(
                format=REPORT_PDF_FORMAT,
                print_background=True,
                display_header_footer=True,
                margin={"top": "16mm", "right": "14mm", "bottom": "18mm", "left": "14mm"},
                header_template="<div></div>",
                footer_template="""
                    <div style="font-size:8px; width:100%; color:#64748b; padding:0 14mm;">
                        <span style="float:left;">StrategAI</span>
                        <span style="float:right;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
                    </div>
                """,
            )
            return pdf_bytes
    except Exception as exc:
        logger.exception("PDF rendering failed")
        raise ReportRenderError(f"Unable to render PDF report: {exc}") from exc
    finally:
        if browser is not None:
            await browser.close()


def build_report_filename(report: Dict[str, Any]) -> str:
    product_name = _safe_text(report.get("product_name") or "report")
    title_slug = _slugify(product_name)
    generated_at = report.get("generated_at")
    stamp = "unknown-time"
    if generated_at:
        try:
            stamp = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00")).strftime("%Y%m%d-%H%M%S")
        except ValueError:
            stamp = _slugify(str(generated_at))
    return f"strategai-report-{title_slug}-{stamp}.pdf"


def render_report_pdf_via_worker(report: Dict[str, Any]) -> bytes:
    """
    Render the PDF in a separate Python process.

    This avoids Windows event-loop limitations inside the FastAPI/Uvicorn worker,
    while still reusing the same HTML-to-PDF renderer code.
    """
    backend_root = Path(__file__).resolve().parents[2]
    input_handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    output_handle = tempfile.NamedTemporaryFile("wb", suffix=".pdf", delete=False)
    input_path = Path(input_handle.name)
    output_path = Path(output_handle.name)
    input_handle.close()
    output_handle.close()

    try:
        input_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.services.report_renderer",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
            ],
            cwd=str(backend_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "worker process failed"
            raise ReportRenderError(f"Unable to render PDF report: {detail}")
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ReportRenderError("Unable to render PDF report: output file was not created")
        return output_path.read_bytes()
    except ReportRenderError:
        raise
    except Exception as exc:
        raise ReportRenderError(f"Unable to render PDF report: {exc}") from exc
    finally:
        for path in (input_path, output_path):
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Render a StrategAI PDF report from JSON input.")
    parser.add_argument("--input", required=True, help="Path to a JSON file containing the report payload.")
    parser.add_argument("--output", required=True, help="Path to write the generated PDF.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    report = json.loads(input_path.read_text(encoding="utf-8"))
    pdf_bytes = __import__("asyncio").run(render_report_pdf(report))
    output_path.write_bytes(pdf_bytes)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
