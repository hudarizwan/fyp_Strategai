from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
import os

from app.services.marketing_agent import MarketingAgent

router = APIRouter()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


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
    analytics_result: AnalyticsResultPayload
    scraper_result: Dict[str, Any] = {}
    pipeline_run_id: Optional[str] = None


@router.post("/generate")
async def generate_marketing_strategy(request: MarketingGenerateRequest):
    """
    Run the Marketing Agent pipeline and return a full go-to-market strategy.
    Persists result to Supabase marketing_strategies table.
    """
    try:
        agent = MarketingAgent(
            ollama_base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
        )
        result = agent.run(
            product_name=request.product_name,
            category=request.category,
            analytics_result=request.analytics_result.model_dump(),
            scraper_result=request.scraper_result,
            pipeline_run_id=request.pipeline_run_id,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/history")
async def get_marketing_history(limit: int = 20):
    """Return the last N marketing strategy runs (summary only)."""
    try:
        from app.services.ecdb import ECDB
        db = ECDB()
        strategies = db.get_marketing_history(limit=limit)
        return {"strategies": strategies, "count": len(strategies)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{strategy_id}")
async def get_marketing_strategy(strategy_id: str):
    """Return a single marketing strategy by ID."""
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
