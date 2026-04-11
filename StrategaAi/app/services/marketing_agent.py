"""
Marketing Agent for StrategAI.

Lifecycle: Perceive → Enrich → Generate → Validate → Critic → Store
Uses local Ollama (llama3.1:8b) for two LLM passes.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from app.services.ecdb import ECDB

logger = logging.getLogger(__name__)

PAKISTAN_CONTEXT = """
Pakistan e-commerce context (apply throughout):
- COD (Cash on Delivery) is the dominant payment method (~70% of orders).
- Daraz is the primary marketplace. TikTok Shop and Instagram are fast-growing.
- Warranty and authenticity are top buyer concerns, especially for electronics.
- Logistics: J&T, Leopards, TCS — standard delivery 2–5 days.
- Price sensitivity is high; bundle offers and free delivery improve conversion.
- Peak seasons: Eid-ul-Fitr, Eid-ul-Adha, Black Friday, Independence Day (14 Aug).
- Trust signals (genuine warranty, seller ratings, return policy) are critical.
"""

REQUIRED_ANALYTICS_FIELDS = [
    "recommended_buy_price_pkr",
    "recommended_sell_price_pkr",
    "expected_profit_margin",
    "confidence_score",
    "wholesale_vendors_count",
    "retail_sellers_count",
]

REQUIRED_OUTPUT_KEYS = [
    "stp", "swot", "pestel", "competitor_analysis", "marketing_mix",
    "branding", "channels", "content_strategy", "launch_plan",
    "growth_funnel", "evidence_ledger", "validation_report",
    "confidence_score", "analysis_status",
]


class MarketingAgent:
    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
    ):
        self.ollama_base_url = ollama_base_url
        self.model = model
        self.db = ECDB()

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------

    def run(
        self,
        product_name: str,
        category: str,
        analytics_result: Dict[str, Any],
        scraper_result: Dict[str, Any],
        pipeline_run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        perceived = self._perceive(product_name, category, analytics_result)
        enriched = self._enrich(perceived, scraper_result)
        raw_strategy = self._generate(enriched)
        validated = self._validate(raw_strategy, perceived)
        final = self._critic(validated, enriched)
        return self._store(final, product_name, category, pipeline_run_id)

    # ------------------------------------------------------------------
    # Step 1 — Perceive
    # ------------------------------------------------------------------

    def _perceive(
        self,
        product_name: str,
        category: str,
        analytics_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        for field in REQUIRED_ANALYTICS_FIELDS:
            if field not in analytics_result:
                raise ValueError(f"Missing required analytics field: {field}")

        buy = float(analytics_result["recommended_buy_price_pkr"])
        sell = float(analytics_result["recommended_sell_price_pkr"])
        margin = float(analytics_result["expected_profit_margin"])
        confidence = float(analytics_result["confidence_score"])

        if buy <= 0 or sell <= 0:
            raise ValueError("recommended_buy_price_pkr and recommended_sell_price_pkr must be positive")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"confidence_score must be between 0 and 1, got {confidence}")
        if not (0.0 <= margin <= 100.0):
            raise ValueError(f"expected_profit_margin must be between 0 and 100, got {margin}")

        return {
            "product_name": product_name,
            "category": category,
            "buy_price_pkr": buy,
            "sell_price_pkr": sell,
            "margin_percent": margin,
            "confidence_score": confidence,
            "confidence_reason": analytics_result.get("confidence_reason", ""),
            "vendor_count": int(analytics_result.get("wholesale_vendors_count", 0)),
            "seller_count": int(analytics_result.get("retail_sellers_count", 0)),
            "price_spread": round(sell - buy, 2),
        }

    # ------------------------------------------------------------------
    # Step 2 — Enrich
    # ------------------------------------------------------------------

    def _enrich(
        self,
        perceived: Dict[str, Any],
        scraper_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        retail_items = scraper_result.get("retail") or []
        wholesale_platforms = scraper_result.get("wholesale") or {}

        competitor_names: List[str] = []
        retail_prices: List[float] = []
        platform_counts: Dict[str, int] = {}
        review_themes: List[str] = []

        for item in retail_items:
            seller = (item.get("seller") or "").strip()
            if seller:
                competitor_names.append(seller)
            price = item.get("list_price") or item.get("price_pkr")
            if price and float(price) > 0:
                retail_prices.append(float(price))
            platform = item.get("platform") or "unknown"
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
            detail = item.get("detail") or {}
            highlights = detail.get("highlights") or detail.get("full_description") or ""
            safe = re.sub(r"(ignore|disregard|forget|system|prompt|instruction)", "", highlights, flags=re.IGNORECASE)
            safe = safe.strip()[:300]
            if safe:
                review_themes.append(safe)

        wholesale_origins: List[str] = []
        moq_values: List[int] = []
        for _platform, items in wholesale_platforms.items():
            for item in (items or []):
                origin = item.get("origin") or item.get("vendor_location") or ""
                if origin:
                    wholesale_origins.append(origin)
                moq = item.get("moq")
                if moq and int(moq) > 0:
                    moq_values.append(int(moq))

        price_band = {
            "min": min(retail_prices) if retail_prices else 0.0,
            "max": max(retail_prices) if retail_prices else 0.0,
            "avg": round(sum(retail_prices) / len(retail_prices), 2) if retail_prices else 0.0,
            "currency": "PKR",
        }

        moq_range = {
            "min": min(moq_values) if moq_values else 1,
            "max": max(moq_values) if moq_values else 1,
        }

        return {
            **perceived,
            "competitor_count": len(retail_items),
            "competitor_names": list(dict.fromkeys(competitor_names)),
            "price_band": price_band,
            "platform_distribution": platform_counts,
            "wholesale_origins": list(set(wholesale_origins)),
            "moq_range": moq_range,
            "review_themes": review_themes[:5],
        }
