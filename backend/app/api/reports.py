from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services import report_renderer

router = APIRouter()


class ReportDownloadRequest(BaseModel):
    report_title: str = Field(default="Product Report")
    generated_at: str
    product_name: str
    category: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)
    wholesale: List[Dict[str, Any]] = Field(default_factory=list)
    retail: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: Dict[str, Any] = Field(default_factory=dict)
    analytics_recommendation: Optional[Dict[str, Any]] = None
    price_history: List[Dict[str, Any]] = Field(default_factory=list)


@router.post("/pdf")
def download_report_pdf(request: ReportDownloadRequest):
    report_payload = request.model_dump()
    try:
        pdf_bytes = report_renderer.render_report_pdf_via_worker(report_payload)
    except report_renderer.ReportRenderError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    filename = report_renderer.build_report_filename(report_payload)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
