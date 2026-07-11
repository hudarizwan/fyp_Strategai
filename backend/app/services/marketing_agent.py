"""
Marketing Agent for StrategAI.

Lifecycle: Perceive Ã¢â€ â€™ Enrich Ã¢â€ â€™ Generate Ã¢â€ â€™ Validate Ã¢â€ â€™ Critic Ã¢â€ â€™ Store
Uses local Ollama (llama3.1:8b) for two LLM passes.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from app.services.business_decision_summary import build_business_decision_summary
from app.services.ecdb import ECDB
from app.services import marketing_prompt_builder
import ollama

logger = logging.getLogger(__name__)

PAKISTAN_CONTEXT = """
Pakistan e-commerce context (apply throughout):
- COD (Cash on Delivery) is the dominant payment method (~70% of orders).
- Daraz is the primary marketplace. TikTok Shop and Instagram are fast-growing.
- Warranty and authenticity are top buyer concerns, especially for electronics.
- Logistics: J&T, Leopards, TCS Ã¢â‚¬â€ standard delivery 2-5 days.
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
        business_state = self._build_business_state(perceived, analytics_result, enriched)
        generation_input = self._build_generation_input(perceived, enriched, business_state)
        # _generate raises on Ollama connection errors ? propagates to API as 502
        raw_strategy = self._generate(generation_input)
        # Populate evidence_ledger from enriched data if model left it empty
        # (avoids a full second Ollama critic call for this soft flag alone)
        raw_strategy = self._ensure_evidence_ledger(raw_strategy, enriched, business_state)
        raw_strategy = self._ensure_kpis(raw_strategy, perceived)
        validated = self._validate(raw_strategy, perceived)
        final = self._critic(validated, enriched)
        final = self._apply_strategy_consistency(final, business_state)
        final = self._ensure_marketing_decision_summary(final, business_state)
        final["marketing_readiness_score"] = marketing_prompt_builder.build_marketing_readiness_score(final, business_state)
        threshold_context = self.db.resolve_mcb_confidence_threshold(category)
        final["business_decision_summary"] = build_business_decision_summary(
            analytics_result,
            final,
            threshold_context,
        )
        final = self._validate(final, perceived)
        return self._store(final, product_name, category, pipeline_run_id)

    # ------------------------------------------------------------------
    # Step 1 Ã¢â‚¬â€ Perceive
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
    # Step 2 Ã¢â‚¬â€ Enrich
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

    def _build_business_state(
        self,
        perceived: Dict[str, Any],
        analytics_result: Dict[str, Any],
        enriched: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return marketing_prompt_builder.build_business_state(perceived, analytics_result, enriched)

    def _build_generation_input(
        self,
        perceived: Dict[str, Any],
        enriched: Optional[Dict[str, Any]] = None,
        business_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return marketing_prompt_builder.build_generation_input(perceived, enriched, business_state)

    def _apply_strategy_consistency(
        self,
        strategy: Dict[str, Any],
        business_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        return marketing_prompt_builder.apply_strategy_consistency(strategy, business_state)

    def _ensure_marketing_decision_summary(
        self,
        strategy: Dict[str, Any],
        business_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        if "marketing_decision_summary" in strategy:
            return strategy
        strategy = dict(strategy)
        strategy["marketing_decision_summary"] = marketing_prompt_builder.build_marketing_decision_summary(
            strategy,
            business_state,
        )
        return strategy
    # Step 3 Ã¢â‚¬â€ Generate (Ollama call #1)
    # ------------------------------------------------------------------

    def _generate(self, enriched: Dict[str, Any]) -> Dict[str, Any]:
        if "market_state" not in enriched:
            legacy_perceived = {
                "product_name": enriched.get("product_name", ""),
                "category": enriched.get("category", ""),
                "buy_price_pkr": enriched.get("buy_price_pkr", enriched.get("recommended_buy_price_pkr", 0.0)),
                "sell_price_pkr": enriched.get("sell_price_pkr", enriched.get("recommended_sell_price_pkr", 0.0)),
                "margin_percent": enriched.get("margin_percent", enriched.get("expected_profit_margin", 0.0)),
                "confidence_score": enriched.get("confidence_score", 0.0),
                "confidence_reason": enriched.get("confidence_reason", ""),
                "vendor_count": enriched.get("vendor_count", enriched.get("wholesale_vendors_count", 0)),
                "seller_count": enriched.get("seller_count", enriched.get("retail_sellers_count", 0)),
                "price_spread": enriched.get("price_spread", 0.0),
            }
            business_state = self._build_business_state(legacy_perceived, enriched, enriched)
            enriched = self._build_generation_input(legacy_perceived, enriched, business_state)
        system_prompt = self._build_system_prompt()
        user_content = (
            "Generate a complete marketing strategy for this product. "
            "Your entire response must be a single JSON object matching the schema. "
            "No prose, no markdown fences, no explanation - JSON only.\n\n"
            f"INPUT DATA:\n{json.dumps(enriched, indent=2)}"
        )
        # Connection/timeout errors propagate ??? caller (API) maps them to 502
        client = ollama.Client(host=self.ollama_base_url)
        response = client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            format="json",  # Constrains model to valid JSON output
            options={"temperature": 0.3, "num_ctx": 4096},
        )
        # response is a ChatResponse Pydantic object ??? use attribute access, not []
        raw_text = response.message.content
        result = self._extract_json(raw_text)
        if result.get("analysis_status") == "invalid":
            logger.warning(
                "Model returned unparseable JSON for product=%r; validation will flag",
                enriched.get("product_name"),
            )
        return result

    def _build_system_prompt(self) -> str:
        return f"""You are a senior marketing strategist for Pakistan e-commerce. Respond with ONE JSON object only Ã¢â‚¬â€ no prose, no markdown.

{PAKISTAN_CONTEXT}

Rules:
- Keep ALL string values SHORT (1-2 sentences max).
- Use arrays of strings for lists (strengths, weaknesses, etc.).
- Follow the structured market_state, category_playbook, strategy_guardrails, evidence_ledger, and signal_summary in the input.
- Prices in marketing_mix.price must match the structured input's sell price.
- confidence_score must be between 0.0 and 1.0.
- Set analysis_status to "ok".

Required JSON structure (fill every field Ã¢â‚¬â€ no nulls, no empty strings):
{{"stp":{{"segmentation":{{"demographics":"","psychographics":""}},"targeting":{{"primary_segment":""}},"positioning":{{"statement":""}}}},"swot":{{"strengths":[""],"weaknesses":[""],"opportunities":[""],"threats":[""]}},"pestel":{{"political":"","economic":"","social":"","technological":"","environmental":"","legal":""}},"competitor_analysis":{{"five_forces":{{"supplier_power":"","buyer_power":"","competitive_rivalry":"","threat_of_substitutes":"","threat_of_new_entrants":""}},"key_competitors":[""],"price_band":{{"min":0,"max":0,"currency":"PKR"}}}},"marketing_mix":{{"product":{{"description":"","usp":""}},"price":{{"strategy":"","recommended_sell_pkr":0}},"place":{{"channels":[""]}},"promotion":{{"tactics":[""]}}}},"branding":{{"value_proposition":"","tone":"","tagline":""}},"channels":[{{"name":"","priority":1,"rationale":""}}],"content_strategy":{{"formats":[""],"frequency":""}},"launch_plan":{{"phases":[{{"name":"","duration":"","actions":[""]}}],"kpis":[{{"metric":"","target":0,"period":""}}],"measurement_plan":{{"tools":[""],"cadence":""}}}},"growth_funnel":{{"model":"AARRR","stages":[{{"stage":"","metric":"","target":0}}]}},"evidence_ledger":[{{"recommendation":"","evidence":[""]}}],"validation_report":{{"status":"ok","checks":[],"flags":[]}},"confidence_score":0.75,"analysis_status":"ok"}}"""

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from model output. Handles code fences and leading/trailing prose."""
        text = text.strip()

        # 1. Direct parse (works when format="json" is respected)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Strip markdown code fence and parse the inner content
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. Find outermost {...} by position (reliable for nested JSON)
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        logger.warning("Could not parse JSON from model output: %.200s", text)
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
    # Post-generate enrichment (no LLM) Ã¢â‚¬â€ prevents unnecessary critic pass
    # ------------------------------------------------------------------

    def _ensure_evidence_ledger(
        self,
        strategy: Dict[str, Any],
        enriched: Dict[str, Any],
        business_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """If model returned empty evidence_ledger, build it from structured context."""
        def _normalize_entry(entry: Any) -> Optional[Dict[str, Any]]:
            if isinstance(entry, dict):
                recommendation = str(entry.get("recommendation") or "").strip()
                if not recommendation:
                    return None
                normalized = dict(entry)
                normalized["recommendation"] = recommendation
                evidence = normalized.get("evidence")
                if isinstance(evidence, list):
                    normalized["evidence"] = [str(item) for item in evidence if str(item).strip()]
                else:
                    normalized["evidence"] = []
                return normalized
            recommendation = str(entry or "").strip()
            if not recommendation:
                return None
            return {"recommendation": recommendation, "evidence": []}

        existing_ledger = strategy.get("evidence_ledger") or []
        if existing_ledger:
            normalized_ledger = []
            seen = set()
            for entry in existing_ledger:
                normalized = _normalize_entry(entry)
                if not normalized:
                    continue
                key = normalized["recommendation"].lower()
                if key in seen:
                    continue
                seen.add(key)
                normalized_ledger.append(normalized)
            strategy = dict(strategy)
            strategy["evidence_ledger"] = normalized_ledger
            return strategy

        built_ledger = list((business_state or {}).get("evidence_ledger") or [])
        if not built_ledger:
            price_band = enriched.get("price_band") or {}
            if price_band.get("min") or price_band.get("max"):
                built_ledger.append({
                    "recommendation": f"Price between PKR {price_band.get('min',0):,.0f} and PKR {price_band.get('max',0):,.0f} based on retail market",
                    "evidence": ["price_band", "retail_sellers_count"],
                })
            origins = enriched.get("wholesale_origins") or []
            if origins:
                built_ledger.append({
                    "recommendation": f"Source from {', '.join(origins[:3])} wholesale channels",
                    "evidence": ["wholesale_origins", "moq_range"],
                })
            platforms = enriched.get("platform_distribution") or {}
            if platforms:
                top = max(platforms, key=platforms.get)
                built_ledger.append({
                    "recommendation": f"Prioritise {top} for primary sales channel",
                    "evidence": ["platform_distribution", "competitor_names"],
                })
            if not built_ledger:
                built_ledger.append({
                    "recommendation": f"Buy at PKR {enriched.get('buy_price_pkr',0):,.0f}, sell at PKR {enriched.get('sell_price_pkr',0):,.0f} for {enriched.get('margin_percent',0):.1f}% margin",
                    "evidence": ["buy_price_pkr", "sell_price_pkr", "margin_percent"],
                })
        normalized_ledger = []
        seen = set()
        for entry in built_ledger:
            normalized = _normalize_entry(entry)
            if not normalized:
                continue
            key = normalized["recommendation"].lower()
            if key in seen:
                continue
            seen.add(key)
            normalized_ledger.append(normalized)
        strategy = dict(strategy)
        strategy["evidence_ledger"] = normalized_ledger
        return strategy

    def _ensure_kpis(
        self, strategy: Dict[str, Any], perceived: Dict[str, Any]
    ) -> Dict[str, Any]:
        """If model returned empty launch_plan.kpis, add sensible defaults."""
        launch_plan = strategy.get("launch_plan") or {}
        if launch_plan.get("kpis"):
            return strategy
        strategy = dict(strategy)
        strategy["launch_plan"] = {
            **launch_plan,
            "kpis": [
                {"metric": "Units sold", "target": 10, "period": "Month 1"},
                {"metric": "Daraz listing views", "target": 500, "period": "Week 1"},
                {"metric": "Profit margin %", "target": round(perceived.get("margin_percent", 20), 1), "period": "Monthly"},
            ],
        }
        return strategy

    # ------------------------------------------------------------------
    # Step 4 Ã¢â‚¬â€ Validate (Python)
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

    # ------------------------------------------------------------------
    # Step 5 Ã¢â‚¬â€ Critic (Ollama call #2)
    # ------------------------------------------------------------------

    def _critic(
        self,
        strategy: Dict[str, Any],
        enriched: Dict[str, Any],
    ) -> Dict[str, Any]:
        flags = (strategy.get("validation_report") or {}).get("flags") or []
        if not flags:
            return strategy  # nothing to fix

        # Soft flags are already handled by _ensure_evidence_ledger / _ensure_kpis.
        # Only run a second (slow) Ollama call for structural missing-key issues.
        SOFT_FLAG_PREFIXES = ("evidence_ledger", "launch_plan.kpis", "confidence_score out of range")
        hard_flags = [f for f in flags if not any(f.startswith(p) for p in SOFT_FLAG_PREFIXES)]
        if not hard_flags:
            logger.info("Critic skipped Ã¢â‚¬â€ all flags are soft (handled by Python post-processing)")
            return strategy

        critic_prompt = (
            "You are a critical reviewer. The marketing strategy below has validation issues. "
            "Fix ONLY the flagged problems. Return the corrected strategy as a single JSON object. "
            "No prose, no markdown, no explanation Ã¢â‚¬â€ JSON only.\n\n"
            f"FLAGS:\n{json.dumps(flags)}\n\n"
            f"STRATEGY:\n{json.dumps(strategy)}"
        )
        try:
            client = ollama.Client(host=self.ollama_base_url)
            response = client.chat(
                model=self.model,
                messages=[{"role": "user", "content": critic_prompt}],
                format="json",
                options={"temperature": 0.1, "num_ctx": 4096},
            )
            # response is a ChatResponse Pydantic object Ã¢â‚¬â€ use attribute access, not []
            raw_text = response.message.content
            improved = self._extract_json(raw_text)
            if improved.get("analysis_status") != "invalid" and improved.get("stp"):
                return improved
        except Exception as exc:
            logger.warning("Critic pass failed: %s Ã¢â‚¬â€ keeping validated strategy", exc)
        return strategy

    # ------------------------------------------------------------------
    # Step 6 Ã¢â‚¬â€ Store
    # ------------------------------------------------------------------

    def _store(
        self,
        strategy: Dict[str, Any],
        product_name: str,
        category: str,
        pipeline_run_id: Optional[str],
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "product_name": product_name,
            "category": category,
            "strategy": strategy,
            "analysis_status": strategy.get("analysis_status", "ok"),
            "confidence_score": strategy.get("confidence_score"),
        }
        if pipeline_run_id:
            payload["pipeline_run_id"] = pipeline_run_id
        stored = self.db.insert_marketing_strategy(payload)
        if not stored.get("id"):
            logger.error(
                "DB insert returned no id for product=%r Ã¢â‚¬â€ Supabase insert may have failed silently (RLS?)",
                product_name,
            )
        return {**stored, **strategy}

