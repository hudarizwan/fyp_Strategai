import asyncio
import logging
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import sys
sys.path.append('..')

from app.services.nlp_agent import NLPAgent
from app.services.analytics_agent import AnalyticsAgent
from app.services.ecdb import ECDB
from app.services.marketing_agent import MarketingAgent
from app.services.mcb_decision_agent import MCBDecisionAgent
from app.services.mcb_models import (
    AnalyticsOutput as MCBAnalyticsOutput,
    CompetitorSignals,
    MarketingOutput,
    MarketStats,
    MCBDecisionInput,
    MCBDecisionOutput,
)
from app.services.scraper_service import scrape_product_platforms

router = APIRouter()
logger = logging.getLogger(__name__)
MARKETING_INLINE_TIMEOUT_SECONDS = float(os.getenv("MARKETING_INLINE_TIMEOUT_SECONDS", "20"))
RUN_INLINE_MARKETING = os.getenv("RUN_INLINE_MARKETING", "false").strip().lower() in {"1", "true", "yes", "on"}


# Request Models
class AnalyzeRequest(BaseModel):
    product_name: str
    category: str


class QueryRequest(BaseModel):
    product_name: str
    category: str


def _build_raw_stage_rows(raw_capture: Dict[str, Any], pipeline_run_id: str, product_name: str, category: str):
    scrape_sources = []
    wholesale_rows = []
    retail_rows = []

    for platform, items in (raw_capture.get("wholesale") or {}).items():
        search_url = raw_capture.get("links_used", {}).get(f"{platform}_search", "")
        scrape_sources.append({
            "pipeline_run_id": pipeline_run_id,
            "platform_name": platform,
            "source_type": "wholesale",
            "search_url": search_url,
            "strategy_name": "source_specific",
            "attempt_number": 1,
            "success": bool(items),
            "metadata": {"item_count": len(items)},
            "started_at": None,
            "completed_at": None,
        })
        for item in items:
            wholesale_rows.append({
                "pipeline_run_id": pipeline_run_id,
                "scrape_source_id": f"wholesale::{platform}",
                "query_text": product_name,
                "category": category,
                "source_type": "wholesale",
                "platform_name": platform,
                "raw_title": item.get("title"),
                "raw_description": " ".join(str(v) for v in (item.get("attributes_listing") or {}).values()),
                "raw_price": item.get("unit_price"),
                "raw_currency": item.get("currency"),
                "raw_supplier_seller": item.get("supplier") or item.get("vendor_name"),
                "raw_moq": item.get("moq"),
                "raw_stock_status": item.get("stock_status") or item.get("stock"),
                "raw_delivery_info": item.get("delivery_info") or item.get("shipping_terms"),
                "source_url": item.get("source_url") or item.get("url"),
                "vendor_location": item.get("origin") or item.get("vendor_location"),
                "raw_payload": item,
                "record_hash": f"wholesale::{platform}::{item.get('title','')}::{item.get('source_url') or item.get('url') or ''}",
                "scrape_status": "captured",
            })

    for platform in {"daraz"}:
        search_url = raw_capture.get("links_used", {}).get(f"{platform}_search", "")
        items = [item for item in (raw_capture.get("retail") or []) if item.get("platform") == platform]
        scrape_sources.append({
            "pipeline_run_id": pipeline_run_id,
            "platform_name": platform,
            "source_type": "retail",
            "search_url": search_url,
            "strategy_name": "source_specific",
            "attempt_number": 1,
            "success": bool(items),
            "metadata": {"item_count": len(items)},
            "started_at": None,
            "completed_at": None,
        })
    for item in raw_capture.get("retail") or []:
        retail_rows.append({
            "pipeline_run_id": pipeline_run_id,
            "scrape_source_id": f"retail::{item.get('platform')}",
            "query_text": product_name,
            "category": category,
            "source_type": "retail",
            "platform_name": item.get("platform"),
            "raw_title": item.get("title"),
            "raw_description": ((item.get("detail") or {}).get("full_description") or (item.get("detail") or {}).get("highlights") or ""),
            "raw_price": item.get("list_price") or item.get("price_pkr"),
            "raw_currency": item.get("currency") or "PKR",
            "raw_supplier_seller": item.get("seller") or (item.get("detail") or {}).get("seller_name"),
            "raw_moq": item.get("moq"),
            "raw_stock_status": (item.get("detail") or {}).get("stock_status"),
            "raw_delivery_info": (item.get("detail") or {}).get("delivery_options"),
            "source_url": item.get("url"),
            "vendor_location": (item.get("detail") or {}).get("delivery_location"),
            "raw_payload": item,
            "record_hash": f"retail::{item.get('platform')}::{item.get('title','')}::{item.get('url') or ''}",
            "scrape_status": "captured",
        })

    return scrape_sources, wholesale_rows, retail_rows


def _attach_raw_record_ids(
    filtered_data: Dict[str, Any],
    inserted_wholesale_rows: list[Dict[str, Any]],
    inserted_retail_rows: list[Dict[str, Any]],
):
    wholesale_lookup = {
        (
            row.get("platform_name"),
            row.get("raw_title"),
            row.get("source_url"),
        ): row.get("id")
        for row in inserted_wholesale_rows
    }
    retail_lookup = {
        (
            row.get("platform_name"),
            row.get("raw_title"),
            row.get("source_url"),
        ): row.get("id")
        for row in inserted_retail_rows
    }
    for platform, items in (filtered_data.get("wholesale") or {}).items():
        for item in items:
            item["_raw_scrape_record_id"] = wholesale_lookup.get((platform, item.get("title"), item.get("source_url") or item.get("url")))
            item["_raw_source_type"] = "wholesale"
    for item in filtered_data.get("retail") or []:
        item["_raw_scrape_record_id"] = retail_lookup.get((item.get("platform"), item.get("title"), item.get("url")))
        item["_raw_source_type"] = "retail"


# Response Models
class RecommendationResponse(BaseModel):
    product: str
    category: str
    pipeline_run_id: Optional[str] = None
    analytics_result_id: Optional[str] = None
    product_cluster_id: Optional[str] = None
    recommended_buy_price_pkr: float
    recommended_sell_price_pkr: float
    expected_profit_margin: float
    confidence_score: float
    confidence_reason: str
    wholesale_vendors_count: int
    retail_sellers_count: int
    low_sample_warning: bool = False
    low_sample_reason: str = ""
    sample_thresholds: Dict[str, int] = Field(default_factory=dict)
    reasoning_bullets: List[str] = Field(default_factory=list)
    gross_profit_pkr: float = 0.0
    net_profit_pkr: float = 0.0
    gross_margin_percent: float = 0.0
    roi_percent: float = 0.0
    break_even_sell_price_pkr: float = 0.0
    profitability_confidence: float = 0.0
    confidence_band: str = "limited"
    cost_breakdown: Dict[str, Any] = Field(default_factory=dict)
    cost_profile: Dict[str, Any] = Field(default_factory=dict)
    market_intelligence: Dict[str, Any] = Field(default_factory=dict)
    commercial_intelligence: Dict[str, Any] = Field(default_factory=dict)
    profitability_summary: Dict[str, Any] = Field(default_factory=dict)
    evidence_ledger: List[Dict[str, Any]] = Field(default_factory=list)
    analysis_details: Dict[str, Any] = Field(default_factory=dict)
    marketing_strategy_id: Optional[str] = None
    marketing_analysis_status: Optional[str] = None
    mcb_decision: Optional[MCBDecisionOutput] = None


class AnalyticsFeedbackRequest(BaseModel):
    pipeline_run_id: Optional[str] = None
    analytics_result_id: Optional[str] = None
    recommendation_id: Optional[str] = None
    marketing_strategy_id: Optional[str] = None
    submitted_by_user_id: Optional[str] = None
    product_name: str
    category: Optional[str] = None
    feedback_type: str = Field(default="follow_up")
    action_taken: Optional[str] = None
    actual_buy_price_pkr: Optional[float] = None
    actual_sell_price_pkr: Optional[float] = None
    quantity: Optional[int] = None
    notes: Optional[str] = None
    source_page: Optional[str] = None


class AnalyticsFeedbackResponse(BaseModel):
    id: str
    pipeline_run_id: Optional[str] = None
    analytics_result_id: Optional[str] = None
    recommendation_id: Optional[str] = None
    feedback_type: str
    action_taken: Optional[str] = None
    created_at: Optional[str] = None
    status: str = "stored"


class PriceHistoryPoint(BaseModel):
    pipeline_run_id: Optional[str] = None
    captured_at: Optional[str] = None
    wholesale_count: int = 0
    retail_count: int = 0
    wholesale_avg_price_pkr: float = 0.0
    wholesale_min_price_pkr: float = 0.0
    wholesale_max_price_pkr: float = 0.0
    retail_avg_price_pkr: float = 0.0
    retail_min_price_pkr: float = 0.0
    retail_max_price_pkr: float = 0.0


class PriceHistoryResponse(BaseModel):
    product_name: str
    category: str
    total_points: int
    points: List[PriceHistoryPoint] = Field(default_factory=list)


def _build_mcb_workflow_metadata(mcb_decision: MCBDecisionOutput) -> Dict[str, Any]:
    return {
        "final_confidence": mcb_decision.final_confidence,
        "confidence_threshold": mcb_decision.confidence_threshold,
        "threshold_source_tier": mcb_decision.threshold_source_tier,
        "threshold_source_category": mcb_decision.threshold_source_category,
        "final_status": mcb_decision.final_status,
    }

def _extract_prices(items: list[Dict[str, Any]], keys: tuple[str, ...]) -> list[float]:
    prices: list[float] = []
    for item in items:
        for key in keys:
            value = item.get(key)
            if value is None:
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if numeric > 0:
                prices.append(numeric)
                break
    return prices


def _build_market_stats(raw_data: Dict[str, Any]) -> tuple[MarketStats, MarketStats]:
    wholesale_items: list[Dict[str, Any]] = []
    for items in (raw_data.get("wholesale") or {}).values():
        wholesale_items.extend(items or [])
    retail_items = raw_data.get("retail") or []

    wholesale_prices = _extract_prices(wholesale_items, ("unit_price_pkr", "price_pkr", "unit_price"))
    retail_prices = _extract_prices(retail_items, ("list_price", "price_pkr"))

    wholesale_stats = MarketStats(
        avg_price_pkr=(sum(wholesale_prices) / len(wholesale_prices)) if wholesale_prices else None,
        min_price_pkr=min(wholesale_prices) if wholesale_prices else None,
        max_price_pkr=max(wholesale_prices) if wholesale_prices else None,
        participant_count=len({(item.get("supplier") or item.get("vendor_name") or "").strip() for item in wholesale_items if (item.get("supplier") or item.get("vendor_name"))}) or len(wholesale_items),
    )
    retail_stats = MarketStats(
        avg_price_pkr=(sum(retail_prices) / len(retail_prices)) if retail_prices else None,
        min_price_pkr=min(retail_prices) if retail_prices else None,
        max_price_pkr=max(retail_prices) if retail_prices else None,
        participant_count=len({(item.get("seller") or "").strip() for item in retail_items if item.get("seller")}) or len(retail_items),
    )
    return wholesale_stats, retail_stats


def _build_competitor_signals(raw_data: Dict[str, Any], retail_stats: MarketStats) -> CompetitorSignals:
    retail_items = raw_data.get("retail") or []
    discount_hits = 0
    stock_out_hits = 0

    for item in retail_items:
        promo_text = str(item.get("promo") or "").lower()
        if promo_text and any(token in promo_text for token in ("off", "%", "sale", "discount")):
            discount_hits += 1
        detail = item.get("detail") or {}
        stock_text = str(detail.get("stock_status") or item.get("stock_status") or "").lower()
        if stock_text and any(token in stock_text for token in ("out", "unavailable", "sold")):
            stock_out_hits += 1

    retail_count = max(len(retail_items), 1)
    discount_ratio = discount_hits / retail_count
    stock_out_rate = stock_out_hits / retail_count

    discount_intensity = "high" if discount_ratio >= 0.5 else "medium" if discount_ratio >= 0.2 else "low"
    spread_ratio = 1.0
    if retail_stats.avg_price_pkr and retail_stats.max_price_pkr is not None and retail_stats.min_price_pkr is not None and retail_stats.avg_price_pkr > 0:
        spread_ratio = (retail_stats.max_price_pkr - retail_stats.min_price_pkr) / retail_stats.avg_price_pkr
    price_aggression = "high" if spread_ratio <= 0.08 else "medium" if spread_ratio <= 0.2 else "low"

    return CompetitorSignals(
        discount_intensity=discount_intensity,
        stock_out_rate=round(stock_out_rate, 4),
        price_aggression=price_aggression,
    )


def _extract_marketing_output(marketing_result: Dict[str, Any]) -> MarketingOutput:
    strategy = marketing_result.get("strategy") if isinstance(marketing_result.get("strategy"), dict) else marketing_result
    stp = strategy.get("stp") or {}
    channels = strategy.get("channels") or []
    primary_channel = channels[0].get("name") if channels and isinstance(channels[0], dict) else None
    strategy_meta = strategy.get("strategy_meta") or {}
    return MarketingOutput(
        segment=((stp.get("targeting") or {}).get("primary_segment") if isinstance(stp.get("targeting"), dict) else None),
        positioning=((stp.get("positioning") or {}).get("statement") if isinstance(stp.get("positioning"), dict) else None),
        primary_channel=primary_channel,
        budget_pkr=None,
        expected_roi_percent=None,
        confidence_score=float(marketing_result.get("confidence_score") or strategy.get("confidence_score") or 0.0),
        channel_count=len(channels),
        launch_scope=str(strategy_meta.get("launch_scope") or strategy_meta.get("quality_band") or "standard"),
        evidence_coverage_score=float(strategy_meta.get("evidence_coverage_score") or 0.0),
        quality_band=str(strategy_meta.get("quality_band") or "limited"),
    )


def _fallback_marketing_output(reason: str) -> tuple[MarketingOutput, Dict[str, Any]]:
    return (
        MarketingOutput(
            segment=None,
            positioning=None,
            primary_channel=None,
            budget_pkr=None,
            expected_roi_percent=None,
            confidence_score=0.0,
        ),
        {
            "id": None,
            "analysis_status": "invalid",
            "storage_status": "failed",
            "storage_error": reason,
        },
    )


def _deferred_marketing_output() -> tuple[MarketingOutput, Dict[str, Any]]:
    return (
        MarketingOutput(
            segment=None,
            positioning=None,
            primary_channel=None,
            budget_pkr=None,
            expected_roi_percent=None,
            confidence_score=0.0,
        ),
        {
            "id": None,
            "analysis_status": "pending",
            "storage_status": "deferred",
        },
    )


async def _run_marketing_with_timeout(
    product_name: str,
    category: str,
    recommendation: Dict[str, Any],
    raw_data: Dict[str, Any],
    pipeline_run_id: str,
) -> Dict[str, Any]:
    marketing_agent = MarketingAgent()
    return await asyncio.wait_for(
        asyncio.to_thread(
            marketing_agent.run,
            product_name=product_name,
            category=category,
            analytics_result=recommendation,
            scraper_result=raw_data,
            pipeline_run_id=pipeline_run_id,
            analytics_result_id=recommendation.get("analytics_result_id"),
            product_cluster_id=recommendation.get("product_cluster_id"),
            generation_type="initial",
        ),
        timeout=MARKETING_INLINE_TIMEOUT_SECONDS,
    )


@router.post("/analyze", response_model=RecommendationResponse)
async def analyze_product(request: AnalyzeRequest):
    """
    Complete end-to-end analysis: Scrape → NLP → Analytics
    """
    try:
        db = ECDB()
        search_request = db.create_search_request(request.product_name, request.category, triggered_by="user", request_source="api")
        pipeline_run = db.create_pipeline_run(search_request["id"], current_stage="scraper", run_config={"product_name": request.product_name, "category": request.category})
        db.log_workflow_event(pipeline_run["id"], "run_started", "pipeline", "running", "Pipeline run created")

        scraper_exec = db.create_agent_execution(pipeline_run["id"], "scraper_service", "scraper", "scrape_product_platforms")
        db.log_workflow_event(pipeline_run["id"], "scraper_started", "scraper", "running", "Starting scraper", scraper_exec["id"])
        # Step 1: Scrape
        raw_data = scrape_product_platforms(request.product_name, request.category)
        raw_capture = raw_data.get("raw_capture", raw_data)
        scrape_sources, raw_wholesale_rows, raw_retail_rows = _build_raw_stage_rows(raw_capture, pipeline_run["id"], request.product_name, request.category)
        source_id_map = {}
        for source in scrape_sources:
            created_source = db.create_scrape_source(
                pipeline_run["id"],
                source["platform_name"],
                source["source_type"],
                search_url=source["search_url"],
                strategy_name=source["strategy_name"],
                metadata=source["metadata"],
            )
            source_id_map[f"{source['source_type']}::{source['platform_name']}"] = created_source["id"]
        for row in raw_wholesale_rows + raw_retail_rows:
            row["scrape_source_id"] = source_id_map.get(row["scrape_source_id"])
        inserted_wholesale_raw = db.insert_raw_wholesale_records_bulk(raw_wholesale_rows) if raw_wholesale_rows else []
        inserted_retail_raw = db.insert_raw_retail_records_bulk(raw_retail_rows) if raw_retail_rows else []
        inserted_raw = inserted_wholesale_raw + inserted_retail_raw
        _attach_raw_record_ids(raw_data, inserted_wholesale_raw, inserted_retail_raw)
        db.finalize_agent_execution(scraper_exec["id"], "completed", output_summary={"raw_records": len(inserted_raw)})
        db.log_workflow_event(pipeline_run["id"], "scraper_completed", "scraper", "completed", "Scraper completed", scraper_exec["id"], records_processed_count=len(inserted_raw))
        db.update_pipeline_run_status(pipeline_run["id"], "running", current_stage="nlp")
        
        # Step 2: NLP Processing
        nlp_agent = NLPAgent()
        nlp_exec = db.create_agent_execution(pipeline_run["id"], "nlp_agent", "nlp", "process")
        db.log_workflow_event(pipeline_run["id"], "nlp_started", "nlp", "running", "Starting NLP", nlp_exec["id"])
        nlp_output = nlp_agent.process(raw_data, request.product_name, request.category, pipeline_run_id=pipeline_run["id"])
        db.finalize_agent_execution(nlp_exec["id"], "completed", output_summary=nlp_output.get("stats"))
        db.log_workflow_event(pipeline_run["id"], "nlp_completed", "nlp", "completed", "NLP completed", nlp_exec["id"], records_processed_count=nlp_output.get("stats", {}).get("after_validation"))
        db.update_pipeline_run_status(pipeline_run["id"], "running", current_stage="analytics")
        
        # Step 3: Analytics
        analytics_agent = AnalyticsAgent()
        analytics_exec = db.create_agent_execution(pipeline_run["id"], "analytics_agent", "analytics", "analyze")
        db.log_workflow_event(pipeline_run["id"], "analytics_started", "analytics", "running", "Starting analytics", analytics_exec["id"])
        db.log_workflow_event(pipeline_run["id"], "recommendation_started", "recommendation", "running", "Starting recommendation generation")
        recommendation = analytics_agent.analyze(request.product_name, request.category, nlp_output, pipeline_run_id=pipeline_run["id"])
        db.finalize_agent_execution(analytics_exec["id"], "completed", output_summary={"confidence": recommendation.get("confidence_score")})
        db.log_workflow_event(pipeline_run["id"], "analytics_completed", "analytics", "completed", "Analytics completed", analytics_exec["id"], records_processed_count=1)
        db.log_workflow_event(pipeline_run["id"], "recommendation_completed", "recommendation", "completed", "Recommendation stored", records_processed_count=1)

        marketing_output, marketing_result = _deferred_marketing_output()
        marketing_exec = db.create_agent_execution(pipeline_run["id"], "marketing_agent", "marketing", "run")
        if RUN_INLINE_MARKETING:
            db.log_workflow_event(pipeline_run["id"], "marketing_started", "marketing", "running", "Starting marketing generation", marketing_exec["id"])
            try:
                marketing_result = await _run_marketing_with_timeout(
                    product_name=request.product_name,
                    category=request.category,
                    recommendation=recommendation,
                    raw_data=raw_data,
                    pipeline_run_id=pipeline_run["id"],
                )
                marketing_output = _extract_marketing_output(marketing_result)
                db.finalize_agent_execution(marketing_exec["id"], "completed", output_summary={"strategy_id": marketing_result.get("id")})
                db.log_workflow_event(
                    pipeline_run["id"],
                    "marketing_completed",
                    "marketing",
                    "completed",
                    "Marketing strategy generated",
                    marketing_exec["id"],
                    records_processed_count=1,
                )
            except asyncio.TimeoutError:
                timeout_message = f"Marketing generation timed out after {MARKETING_INLINE_TIMEOUT_SECONDS:.0f}s"
                logger.warning(timeout_message)
                marketing_output, marketing_result = _fallback_marketing_output(timeout_message)
                db.finalize_agent_execution(marketing_exec["id"], "failed", error_message=timeout_message)
                db.log_workflow_event(
                    pipeline_run["id"],
                    "marketing_timed_out",
                    "marketing",
                    "failed",
                    timeout_message,
                    marketing_exec["id"],
                )
            except Exception as marketing_exc:
                marketing_output, marketing_result = _fallback_marketing_output(str(marketing_exc))
                db.finalize_agent_execution(marketing_exec["id"], "failed", error_message=str(marketing_exc))
                db.log_workflow_event(
                    pipeline_run["id"],
                    "marketing_failed",
                    "marketing",
                    "failed",
                    str(marketing_exc),
                    marketing_exec["id"],
                )
        else:
            db.finalize_agent_execution(marketing_exec["id"], "completed", output_summary={"deferred": True})
            db.log_workflow_event(
                pipeline_run["id"],
                "marketing_deferred",
                "marketing",
                "completed",
                "Marketing generation deferred to frontend background flow",
                marketing_exec["id"],
            )

        mcb_exec = db.create_agent_execution(pipeline_run["id"], "mcb_decision_agent", "decision", "decide")
        db.log_workflow_event(pipeline_run["id"], "mcb_started", "decision", "running", "Starting MCB decision", mcb_exec["id"])
        wholesale_stats, retail_stats = _build_market_stats(raw_data)
        competitor_signals = _build_competitor_signals(raw_data, retail_stats)
        mcb_input = MCBDecisionInput(
            product_name=request.product_name,
            category=request.category,
            wholesale=wholesale_stats,
            retail=retail_stats,
            analytics=MCBAnalyticsOutput(
                predicted_price_pkr=recommendation.get("recommended_sell_price_pkr", 0.0),
                predicted_margin_percent=recommendation.get("expected_profit_margin", 0.0),
                confidence_score=recommendation.get("confidence_score", 0.0),
                gross_profit_pkr=recommendation.get("gross_profit_pkr", 0.0),
                net_profit_pkr=recommendation.get("net_profit_pkr", 0.0),
                roi_percent=recommendation.get("roi_percent", 0.0),
                break_even_sell_price_pkr=recommendation.get("break_even_sell_price_pkr", 0.0),
                quality_band=str(recommendation.get("confidence_band") or "limited"),
                demand_score=float((recommendation.get("market_intelligence") or {}).get("demand_score", 0.0)),
                competition_score=float((recommendation.get("market_intelligence") or {}).get("competition_score", 0.0)),
                data_quality_score=float((recommendation.get("market_intelligence") or {}).get("data_quality_score", 0.0)),
                risk_score=float((recommendation.get("market_intelligence") or {}).get("risk_score", 0.0)),
                market_saturation_score=float((recommendation.get("market_intelligence") or {}).get("market_saturation_score", 0.0)),
            ),
            competitors=competitor_signals,
            marketing=MarketingOutput(
                segment=marketing_output.segment,
                positioning=marketing_output.positioning,
                primary_channel=marketing_output.primary_channel,
                budget_pkr=marketing_output.budget_pkr,
                expected_roi_percent=marketing_output.expected_roi_percent,
                confidence_score=marketing_output.confidence_score,
                channel_count=marketing_output.channel_count,
                launch_scope=marketing_output.launch_scope,
                evidence_coverage_score=marketing_output.evidence_coverage_score,
                quality_band=marketing_output.quality_band,
            ),
        )
        mcb_agent = MCBDecisionAgent(db)
        mcb_decision = mcb_agent.decide(mcb_input)
        db.finalize_agent_execution(mcb_exec["id"], "completed", output_summary={"final_status": mcb_decision.final_status})
        db.log_workflow_event(
            pipeline_run["id"],
            "mcb_completed",
            "decision",
            "completed",
            f"MCB final status: {mcb_decision.final_status} (threshold: {mcb_decision.threshold_source_tier})",
            mcb_exec["id"],
            event_metadata=_build_mcb_workflow_metadata(mcb_decision),
            records_processed_count=1,
        )

        db.finalize_pipeline_run(pipeline_run["id"], "completed", current_stage="completed")
        recommendation["pipeline_run_id"] = pipeline_run["id"]
        recommendation["marketing_strategy_id"] = marketing_result.get("id")
        recommendation["marketing_analysis_status"] = marketing_result.get("analysis_status")
        recommendation["mcb_decision"] = mcb_decision.model_dump()
        return RecommendationResponse(**recommendation)
        
    except Exception as e:
        try:
            if 'db' in locals() and 'pipeline_run' in locals():
                db.log_dead_letter_record("pipeline", str(e), {"product_name": request.product_name, "category": request.category}, pipeline_run["id"])
                db.log_workflow_event(pipeline_run["id"], "run_failed", "pipeline", "failed", str(e))
                db.finalize_pipeline_run(pipeline_run["id"], "failed", current_stage="failed", error_summary=str(e))
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback", response_model=AnalyticsFeedbackResponse)
async def submit_feedback(request: AnalyticsFeedbackRequest):
    """Capture user outcome feedback for an analytics recommendation."""
    try:
        db = ECDB()
        pipeline_run_id = request.pipeline_run_id
        analytics_result_id = request.analytics_result_id
        recommendation_id = request.recommendation_id

        if not pipeline_run_id and not analytics_result_id and not recommendation_id:
            raise HTTPException(status_code=400, detail="At least one of pipeline_run_id, analytics_result_id, or recommendation_id is required")

        analytics_row = None
        if analytics_result_id:
            analytics_row = db.get_analytics_result(analytics_result_id)
            if not analytics_row:
                raise HTTPException(status_code=404, detail="Analytics result not found")
            pipeline_run_id = pipeline_run_id or analytics_row.get("pipeline_run_id")

        if not recommendation_id and pipeline_run_id and analytics_result_id:
            for row in db.get_run_recommendations(pipeline_run_id):
                if row.get("analytics_result_id") == analytics_result_id:
                    recommendation_id = row.get("id")
                    break

        payload = {
            "pipeline_run_id": pipeline_run_id,
            "analytics_result_id": analytics_result_id,
            "recommendation_id": recommendation_id,
            "marketing_strategy_id": request.marketing_strategy_id,
            "submitted_by_user_id": request.submitted_by_user_id,
            "product_name": request.product_name,
            "category": request.category,
            "feedback_type": request.feedback_type,
            "action_taken": request.action_taken or request.feedback_type,
            "actual_buy_price_pkr": request.actual_buy_price_pkr if request.actual_buy_price_pkr and request.actual_buy_price_pkr > 0 else None,
            "actual_sell_price_pkr": request.actual_sell_price_pkr if request.actual_sell_price_pkr and request.actual_sell_price_pkr > 0 else None,
            "quantity": request.quantity if request.quantity and request.quantity > 0 else None,
            "notes": request.notes,
            "source_page": request.source_page or "results",
            "feedback_payload": request.model_dump(),
        }
        stored = db.insert_analytics_outcome_event(payload)
        if pipeline_run_id:
            db.log_workflow_event(
                pipeline_run_id,
                "analytics_feedback_submitted",
                "feedback",
                "completed",
                "Outcome feedback recorded",
                event_metadata={
                    "feedback_type": request.feedback_type,
                    "source_page": request.source_page or "results",
                    "analytics_result_id": analytics_result_id,
                    "recommendation_id": recommendation_id,
                },
                records_processed_count=1,
            )
        return AnalyticsFeedbackResponse(
            id=str(stored.get("id") or ""),
            pipeline_run_id=stored.get("pipeline_run_id") or pipeline_run_id,
            analytics_result_id=stored.get("analytics_result_id") or analytics_result_id,
            recommendation_id=stored.get("recommendation_id") or recommendation_id,
            feedback_type=stored.get("feedback_type") or request.feedback_type,
            action_taken=stored.get("action_taken") or request.action_taken or request.feedback_type,
            created_at=stored.get("created_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_product(request: QueryRequest):
    """
    Query existing product data from database
    """
    try:
        nlp_agent = NLPAgent()
        products = nlp_agent.db.get_products_by_query(request.product_name, request.category)
        
        if not products:
            raise HTTPException(status_code=404, detail="No products found")
        
        # Separate wholesale and retail
        wholesale = [p for p in products if p.get('source_type') == 'wholesale']
        retail = [p for p in products if p.get('source_type') == 'retail']
        clusters = nlp_agent.db.get_clusters_by_query(request.product_name, request.category)
        
        return {
            "product_name": request.product_name,
            "category": request.category,
            "wholesale_products": wholesale,
            "retail_products": retail,
            "clusters": clusters,
            "total_products": len(products)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/{category}")
async def get_category_patterns(category: str):
    """
    Get learned patterns for a category
    """
    try:
        nlp_agent = NLPAgent()
        
        # Get product patterns
        product_patterns = nlp_agent.db.get_all_product_patterns(category)
        
        # Get category pattern
        category_pattern = nlp_agent.db.get_category_pattern(category)
        
        return {
            "category": category,
            "product_patterns": product_patterns,
            "category_pattern": category_pattern
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_database_stats():
    """
    Get database statistics
    """
    try:
        nlp_agent = NLPAgent()
        stats = nlp_agent.db.get_stats()
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_recent_recommendations(limit: int = 10):
    """
    Get recent recommendations
    """
    try:
        nlp_agent = NLPAgent()
        recommendations = nlp_agent.db.get_recent_recommendations(limit)
        
        return {
            "recommendations": recommendations,
            "count": len(recommendations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price-history", response_model=PriceHistoryResponse)
async def get_price_history(product_name: str, category: str, limit: int = 12):
    try:
        db = ECDB()
        points = db.get_price_history(product_name, category, limit=limit)
        return PriceHistoryResponse(
            product_name=product_name,
            category=category,
            total_points=len(points),
            points=[PriceHistoryPoint(**point) for point in points],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trace/{pipeline_run_id}")
async def trace_pipeline_run(pipeline_run_id: str):
    try:
        db = ECDB()
        return db.trace_pipeline_run(pipeline_run_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
