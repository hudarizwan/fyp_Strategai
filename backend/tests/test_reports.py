from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.services.report_renderer import build_report_filename, build_report_html


client = TestClient(app)


def _sample_report():
    return {
        "report_title": "Product Report",
        "generated_at": "2026-06-05T10:15:00Z",
        "product_name": "USB C Cable",
        "summary": {
            "total_suppliers": 2,
            "total_retailers": 2,
            "best_wholesale_price": 120.0,
            "best_retail_price": 320.0,
            "estimated_profit": 200.0,
            "gross_profit_pkr": 200.0,
            "gross_margin_percent": 62.5,
            "observed_market_spread": 200.0,
        },
        "wholesale": [
            {
                "supplier": "Shenzhen Tech",
                "platform": "Made-in-China",
                "unit_price_pkr": 120.0,
                "moq": 100,
                "origin": "China",
            }
        ],
        "retail": [
            {
                "platform": "Daraz",
                "seller": "Cable Store",
                "list_price": 320.0,
                "title": "USB C Fast Charging Cable",
                "promo": "10% off",
            }
        ],
        "recommendations": {
            "supplier": {
                "supplier": "Shenzhen Tech",
                "platform": "Made-in-China",
            },
            "retail_platform": {
                "platform": "Daraz",
                "seller": "Cable Store",
            },
        },
        "price_history": [
            {
                "pipeline_run_id": "run-1",
                "captured_at": "2026-06-01T10:15:00Z",
                "wholesale_count": 2,
                "retail_count": 2,
                "wholesale_avg_price_pkr": 120.0,
                "wholesale_min_price_pkr": 110.0,
                "wholesale_max_price_pkr": 130.0,
                "retail_avg_price_pkr": 320.0,
                "retail_min_price_pkr": 300.0,
                "retail_max_price_pkr": 340.0,
            }
        ],
    }


def test_build_report_html_includes_core_sections():
    html = build_report_html(_sample_report())
    assert "USB C Cable" in html
    assert "Executive Summary" in html
    assert "Wholesale Suppliers Analysis" in html
    assert "Retail Market Analysis" in html
    assert "Recommendations" in html
    assert "Data Sources" in html


def test_build_report_html_includes_price_history_section():
    html = build_report_html(_sample_report())
    assert "Price History" in html
    assert "Historical Price Trend" in html
    assert "Wholesale Avg" in html
    assert "Retail Avg" in html


def test_build_report_filename_is_stable():
    filename = build_report_filename(_sample_report())
    assert filename.startswith("strategai-report-usb-c-cable-")
    assert filename.endswith(".pdf")


def test_pdf_download_endpoint_returns_attachment(monkeypatch):
    def fake_render_report_pdf(report):
        assert report["product_name"] == "USB C Cable"
        return b"%PDF-1.4\n%fake-strategai-pdf\n"

    monkeypatch.setattr("app.services.report_renderer.render_report_pdf_via_worker", fake_render_report_pdf)

    response = client.post("/reports/pdf", json=_sample_report())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment;" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-1.4")


def test_build_report_html_uses_gross_labels():
    html = build_report_html(_sample_report())
    assert "Gross Margin" in html
    assert "Gross Profit" in html
    assert "Observed Market Spread" in html
    assert "Net Profit" not in html
    assert "Break-even Sell" not in html
