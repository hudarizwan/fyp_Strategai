import asyncio
import os
import uuid
from asyncio import get_event_loop
from functools import partial
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.services.marketing_agent import MarketingAgent

router = APIRouter()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
MARKETING_REQUEST_TIMEOUT_SECONDS = float(os.getenv("MARKETING_REQUEST_TIMEOUT_SECONDS", "45"))


class AnalyticsResultPayload(BaseModel):
    recommended_buy_price_pkr: float
    recommended_sell_price_pkr: float
    expected_profit_margin: float
    confidence_score: float
    confidence_reason: str = ""
    wholesale_vendors_count: int = 0
    retail_sellers_count: int = 0


class MarketingGenerateRequest(BaseModel):
    product_name: str
    category: str
    analytics_result: AnalyticsResultPayload = Field(validation_alias="analytics_result")
    scraper_result: Dict[str, Any] = Field(default_factory=dict, validation_alias="scraper_result")
    recommendation: Optional[AnalyticsResultPayload] = None
    scraped_data: Optional[Dict[str, Any]] = None
    pipeline_run_id: Optional[str] = None
    analytics_result_id: Optional[str] = None
    product_cluster_id: Optional[str] = None
    parent_strategy_id: Optional[str] = None
    generation_type: str = "initial"

    @model_validator(mode="before")
    @classmethod
    def coerce_legacy_aliases(cls, data: Any):
        if not isinstance(data, dict):
            return data
        if "analytics_result" not in data and "recommendation" in data:
            data["analytics_result"] = data["recommendation"]
        if "scraper_result" not in data and "scraped_data" in data:
            data["scraper_result"] = data["scraped_data"]
        return data


def _build_agent() -> MarketingAgent:
    return MarketingAgent(
        ollama_base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
    )


def _build_fallback_runner(agent: MarketingAgent, request: MarketingGenerateRequest, reason: str):
    return partial(
        agent.run_deterministic,
        product_name=request.product_name,
        category=request.category,
        analytics_result=request.analytics_result.model_dump(),
        scraper_result=request.scraper_result,
        pipeline_run_id=request.pipeline_run_id,
        analytics_result_id=request.analytics_result_id,
        product_cluster_id=request.product_cluster_id,
        parent_strategy_id=request.parent_strategy_id,
        generation_type=request.generation_type,
        fallback_reason=reason,
    )


@router.post("/generate")
async def generate_marketing_strategy(request: MarketingGenerateRequest):
    """
    Run the Marketing Agent pipeline and return a full go-to-market strategy.
    Persists result to Supabase marketing_strategies table.

    The normal path uses Ollama in a thread pool. If it times out or fails,
    we return a deterministic fallback strategy instead of surfacing a 502.
    """
    try:
        agent = _build_agent()

        def _run():
            return agent.run(
                product_name=request.product_name,
                category=request.category,
                analytics_result=request.analytics_result.model_dump(),
                scraper_result=request.scraper_result,
                pipeline_run_id=request.pipeline_run_id,
                analytics_result_id=request.analytics_result_id,
                product_cluster_id=request.product_cluster_id,
                parent_strategy_id=request.parent_strategy_id,
                generation_type=request.generation_type,
            )

        loop = get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, _run),
                timeout=MARKETING_REQUEST_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            result = await loop.run_in_executor(
                None,
                _build_fallback_runner(agent, request, f"llm_timeout_{int(MARKETING_REQUEST_TIMEOUT_SECONDS)}s"),
            )

        if result.get("analysis_status") == "invalid":
            result = await loop.run_in_executor(
                None,
                _build_fallback_runner(agent, request, "invalid_llm_output"),
            )
        return result
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        try:
            agent = _build_agent()
            loop = get_event_loop()
            result = await loop.run_in_executor(
                None,
                _build_fallback_runner(agent, request, f"llm_error:{type(exc).__name__}"),
            )
            return result
        except Exception:
            raise HTTPException(status_code=502, detail=f"Ollama error: {exc}")


@router.get("/history")
def get_marketing_history(limit: int = 20):
    """Return the last N marketing strategy runs (summary only)."""
    try:
        from app.services.ecdb import ECDB

        db = ECDB()
        strategies = db.get_marketing_history(limit=limit)
        return {"strategies": strategies, "count": len(strategies)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/by-analytics/{analytics_result_id}")
def get_latest_strategy_by_analytics(analytics_result_id: str):
    try:
        from app.services.ecdb import ECDB

        db = ECDB()
        strategy = db.get_latest_marketing_strategy_by_analytics(analytics_result_id)
        if not strategy:
            analytics_row = db.get_analytics_result(analytics_result_id)
            pipeline_run_id = analytics_row.get("pipeline_run_id") if analytics_row else None
            if pipeline_run_id:
                strategy = db.get_latest_marketing_strategy_by_pipeline(pipeline_run_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return strategy
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/history/{analytics_result_id}")
def get_strategy_history_by_analytics(analytics_result_id: str, limit: int = 20):
    try:
        from app.services.ecdb import ECDB

        db = ECDB()
        strategies = db.get_marketing_history(limit=limit, analytics_result_id=analytics_result_id)
        if not strategies:
            analytics_row = db.get_analytics_result(analytics_result_id)
            pipeline_run_id = analytics_row.get("pipeline_run_id") if analytics_row else None
            if pipeline_run_id:
                strategies = db.get_marketing_history(limit=limit, pipeline_run_id=pipeline_run_id)
        return {"strategies": strategies, "count": len(strategies)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/by-pipeline/{pipeline_run_id}")
def get_latest_strategy_by_pipeline(pipeline_run_id: str):
    try:
        from app.services.ecdb import ECDB

        db = ECDB()
        strategy = db.get_latest_marketing_strategy_by_pipeline(pipeline_run_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return strategy
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/history-pipeline/{pipeline_run_id}")
def get_strategy_history_by_pipeline(pipeline_run_id: str, limit: int = 20):
    try:
        from app.services.ecdb import ECDB

        db = ECDB()
        strategies = db.get_marketing_history(limit=limit, pipeline_run_id=pipeline_run_id)
        return {"strategies": strategies, "count": len(strategies)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/regenerate")
async def regenerate_marketing_strategy(request: MarketingGenerateRequest):
    request = request.model_copy(update={"generation_type": "regenerate"})
    return await generate_marketing_strategy(request)


@router.get("/{strategy_id}")
def get_marketing_strategy(strategy_id: str):
    """Return a single marketing strategy by ID."""
    try:
        uuid.UUID(strategy_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid strategy_id format")
    try:
        from app.services.ecdb import ECDB

        db = ECDB()
        strategy = db.get_marketing_strategy_by_id(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return strategy
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
