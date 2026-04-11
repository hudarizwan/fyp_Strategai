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
import ollama

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

    # ------------------------------------------------------------------
    # Step 3 — Generate (Ollama call #1)
    # ------------------------------------------------------------------

    def _generate(self, enriched: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = self._build_system_prompt()
        user_content = (
            "Generate a complete marketing strategy for this product. "
            "Return ONLY valid JSON matching the schema. No prose, no markdown fences.\n\n"
            f"INPUT DATA:\n{json.dumps(enriched, indent=2)}"
        )
        try:
            client = ollama.Client(host=self.ollama_base_url)
            response = client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                options={"temperature": 0.3},
            )
            raw_text = response["message"]["content"]
            return self._extract_json(raw_text)
        except Exception as exc:
            logger.error("Ollama generate call failed: %s", exc)
            return self._empty_strategy(str(exc))

    def _build_system_prompt(self) -> str:
        return f"""You are a senior marketing strategist specialising in Pakistan e-commerce.
Follow this lifecycle: Perceive → Enrich → Reason → Plan → Generate → Validate → Store.

{PAKISTAN_CONTEXT}

Required frameworks to include:
- STP (Segmentation, Targeting, Positioning)
- SWOT (Strengths, Weaknesses, Opportunities, Threats)
- PESTEL
- 4Ps Marketing Mix (Product, Price, Place, Promotion)
- Porter's Five Forces (inside competitor_analysis.five_forces)
- AARRR Growth Funnel (inside growth_funnel)

Evidence grounding: Every major recommendation MUST include an "evidence" field citing
specific input data fields (e.g., "price_band", "vendor_count", "review_themes").

Pricing consistency: recommended prices in marketing_mix.price MUST align with
buy_price_pkr and sell_price_pkr in the input. Do not contradict them.

Output ONLY this JSON object, fully populated, no extra text:
{{
  "stp": {{"segmentation": {{}}, "targeting": {{}}, "positioning": {{}}}},
  "swot": {{"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}},
  "pestel": {{"political": "", "economic": "", "social": "", "technological": "", "environmental": "", "legal": ""}},
  "competitor_analysis": {{
    "five_forces": {{"supplier_power": "", "buyer_power": "", "competitive_rivalry": "", "threat_of_substitutes": "", "threat_of_new_entrants": ""}},
    "key_competitors": [],
    "price_band": {{"min": 0, "max": 0, "currency": "PKR"}}
  }},
  "marketing_mix": {{"product": {{}}, "price": {{}}, "place": {{}}, "promotion": {{}}}},
  "branding": {{"value_proposition": "", "tone": "", "tagline": ""}},
  "channels": [],
  "content_strategy": {{}},
  "launch_plan": {{"phases": [], "kpis": [], "measurement_plan": {{}}}},
  "growth_funnel": {{"model": "AARRR", "stages": []}},
  "evidence_ledger": [],
  "validation_report": {{"status": "ok", "checks": [], "flags": []}},
  "confidence_score": 0.0,
  "analysis_status": "ok"
}}"""

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from model output, handling code fences and prose wrapping."""
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence_match:
            try:
                return json.loads(fence_match.group(1))
            except json.JSONDecodeError:
                pass
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
        logger.warning("Could not parse JSON from model output")
        return self._empty_strategy("unparseable model output")

    def _empty_strategy(self, reason: str = "") -> Dict[str, Any]:
        return {
            "stp": {}, "swot": {}, "pestel": {}, "competitor_analysis": {},
            "marketing_mix": {}, "branding": {}, "channels": [],
            "content_strategy": {}, "launch_plan": {},
            "growth_funnel": {"model": "AARRR", "stages": []},
            "evidence_ledger": [],
            "validation_report": {"status": "invalid", "checks": [], "flags": [reason]},
            "confidence_score": 0.0,
            "analysis_status": "invalid",
        }

    # ------------------------------------------------------------------
    # Step 4 — Validate (Python)
    # ------------------------------------------------------------------

    def _validate(
        self,
        strategy: Dict[str, Any],
        perceived: Dict[str, Any],
    ) -> Dict[str, Any]:
        strategy = dict(strategy)
        flags: List[str] = []
        checks: List[str] = []

        # Required keys
        for key in REQUIRED_OUTPUT_KEYS:
            if key not in strategy:
                flags.append(f"missing_key:{key}")
            else:
                checks.append(f"present:{key}")

        # confidence_score range
        cs = strategy.get("confidence_score")
        if cs is not None:
            try:
                cs = float(cs)
                if not (0.0 <= cs <= 1.0):
                    flags.append(f"confidence_score out of range: {cs}")
                else:
                    checks.append("confidence_score_range:ok")
            except (TypeError, ValueError):
                flags.append("confidence_score not numeric")

        # analysis_status not already invalid
        if strategy.get("analysis_status") == "invalid":
            flags.append("analysis_status:invalid from generate step")

        # evidence_ledger not empty
        if not strategy.get("evidence_ledger"):
            flags.append("evidence_ledger:empty")
        else:
            checks.append("evidence_ledger:populated")

        # launch_plan.kpis not empty
        kpis = (strategy.get("launch_plan") or {}).get("kpis")
        if not kpis:
            flags.append("launch_plan.kpis:empty")
        else:
            checks.append("launch_plan.kpis:populated")

        # Determine status
        if len(flags) == 0:
            status = "ok"
        elif len(flags) <= 2:
            status = "needs_review"
        else:
            status = "invalid"

        strategy["validation_report"] = {
            "status": status,
            "checks": checks,
            "flags": flags,
        }
        if status != "ok":
            strategy["analysis_status"] = status

        return strategy
