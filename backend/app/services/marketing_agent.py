"""
Marketing Agent for StrategAI.

Lifecycle: Perceive -> Enrich -> Generate -> Validate -> Critic -> Store
Uses local Ollama (llama3.1:8b) for LLM-assisted strategy generation.
"""
from __future__ import annotations

import hashlib
import math
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

import ollama
from app.services.marketing_archetypes import route_strategy_archetype
from app.services.marketing_profile import build_product_profile
from app.services.commercial_intelligence import QUALITY_BANDS, classify_quality_band
from app.services.marketing_prompt_builder import (
    build_compact_analytics_summary,
    build_competitor_summary,
    build_marketing_system_prompt,
    build_marketing_user_prompt,
)
from app.services.marketing_intelligence import build_marketing_intelligence_bundle
from app.services.marketing_similarity import compare_with_history

logger = logging.getLogger(__name__)

LOW_CONFIDENCE_FAST_PATH_THRESHOLD = 0.25
MARKETING_LLM_NUM_CTX = int(os.getenv("MARKETING_LLM_NUM_CTX", "2048"))
MARKETING_LLM_TIMEOUT_SECONDS = float(os.getenv("MARKETING_LLM_TIMEOUT_SECONDS", "90"))
ENABLE_MARKETING_CRITIC = os.getenv("ENABLE_MARKETING_CRITIC", "false").strip().lower() in {"1", "true", "yes", "on"}
ENABLE_SIMILARITY_REGEN = os.getenv("ENABLE_SIMILARITY_REGEN", "false").strip().lower() in {"1", "true", "yes", "on"}
STRATEGY_ANGLES = [
    "value_focus",
    "premium_focus",
    "aggressive_growth",
    "risk_averse",
    "market_penetration",
    "brand_building",
]

PAKISTAN_CONTEXT = """
Pakistan e-commerce context (apply throughout):
- COD (Cash on Delivery) is the dominant payment method (~70% of orders).
- Daraz is the primary marketplace. TikTok Shop and Instagram are fast-growing.
- Warranty and authenticity are top buyer concerns, especially for electronics.
- Logistics: J&T, Leopards, TCS - standard delivery 2-5 days.
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
    "stp",
    "swot",
    "pestel",
    "competitor_analysis",
    "marketing_mix",
    "branding",
    "channels",
    "content_strategy",
    "launch_plan",
    "growth_funnel",
    "evidence_ledger",
    "validation_report",
    "confidence_score",
    "analysis_status",
]


class MarketingAgent:
    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
    ):
        self.ollama_base_url = ollama_base_url
        self.model = model
        self.db = None
        self._context_cache: Dict[str, Dict[str, Any]] = {}

    def run(
        self,
        product_name: str,
        category: str,
        analytics_result: Dict[str, Any],
        scraper_result: Dict[str, Any],
        pipeline_run_id: Optional[str] = None,
        analytics_result_id: Optional[str] = None,
        product_cluster_id: Optional[str] = None,
        parent_strategy_id: Optional[str] = None,
        generation_type: str = "initial",
    ) -> Dict[str, Any]:
        perceived = self._perceive(product_name, category, analytics_result)
        enriched = self._enrich(perceived, scraper_result)
        strategy_context = self._build_strategy_context(
            perceived,
            enriched,
            generation_type=generation_type,
            parent_strategy_id=parent_strategy_id,
        )

        if self._should_use_fast_path(perceived, enriched):
            fast_strategy = self._build_fast_path_strategy(enriched, strategy_context)
            validated = self._validate(fast_strategy, perceived)
            final = self._apply_strategy_metadata(validated, strategy_context)
            final = self._apply_similarity_guard(
                final,
                enriched,
                strategy_context,
                product_name,
                category,
                analytics_result_id,
                pipeline_run_id,
            )
            final = self._apply_strategy_angle_overrides(final, enriched, strategy_context)
            final = self._ensure_evidence_ledger(final, enriched, strategy_context)
            final = self._apply_strategy_metadata(final, strategy_context)
            return self._store(
                final,
                product_name,
                category,
                pipeline_run_id,
                analytics_result_id,
                product_cluster_id,
                parent_strategy_id,
                generation_type,
            )

        raw_strategy = self._generate(enriched, strategy_context)
        if raw_strategy.get("analysis_status") == "invalid" or not raw_strategy.get("stp"):
            logger.warning(
                "Marketing LLM output invalid for %r; using deterministic fallback strategy",
                product_name,
            )
            raw_strategy = self._build_fast_path_strategy(enriched, strategy_context)
        raw_strategy = self._apply_strategy_angle_overrides(raw_strategy, enriched, strategy_context)
        raw_strategy = self._ensure_evidence_ledger(raw_strategy, enriched, strategy_context)
        raw_strategy = self._ensure_kpis(raw_strategy, perceived, enriched, strategy_context)
        validated = self._validate(raw_strategy, perceived)
        final = self._critic(validated, enriched, strategy_context)
        final = self._apply_strategy_angle_overrides(final, enriched, strategy_context)
        final = self._apply_strategy_metadata(final, strategy_context)
        final = self._apply_similarity_guard(
            final,
            enriched,
            strategy_context,
            product_name,
            category,
            analytics_result_id,
            pipeline_run_id,
        )
        final = self._apply_strategy_angle_overrides(final, enriched, strategy_context)
        final = self._ensure_evidence_ledger(final, enriched, strategy_context)
        final = self._apply_strategy_metadata(final, strategy_context)
        return self._store(
            final,
            product_name,
            category,
            pipeline_run_id,
            analytics_result_id,
            product_cluster_id,
            parent_strategy_id,
            generation_type,
        )

    def run_deterministic(
        self,
        product_name: str,
        category: str,
        analytics_result: Dict[str, Any],
        scraper_result: Dict[str, Any],
        pipeline_run_id: Optional[str] = None,
        analytics_result_id: Optional[str] = None,
        product_cluster_id: Optional[str] = None,
        parent_strategy_id: Optional[str] = None,
        generation_type: str = "initial",
        fallback_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        perceived = self._perceive(product_name, category, analytics_result)
        enriched = self._enrich(perceived, scraper_result)
        strategy_context = self._build_strategy_context(
            perceived,
            enriched,
            generation_type=generation_type,
            parent_strategy_id=parent_strategy_id,
        )
        strategy = self._build_fast_path_strategy(enriched, strategy_context)
        validated = self._validate(strategy, perceived)
        final = self._apply_strategy_metadata(validated, strategy_context)
        if fallback_reason:
            final.setdefault("validation_report", {}).setdefault("flags", [])
            final["validation_report"]["flags"].append(f"deterministic_fallback:{fallback_reason}")
            final.setdefault("strategy_meta", {})
            final["strategy_meta"]["fallback_reason"] = fallback_reason
        return self._store(
            final,
            product_name,
            category,
            pipeline_run_id,
            analytics_result_id,
            product_cluster_id,
            parent_strategy_id,
            generation_type,
        )

    def _should_use_fast_path(self, perceived: Dict[str, Any], enriched: Dict[str, Any]) -> bool:
        confidence = float(perceived.get("confidence_score", 0.0))
        seller_count = int(perceived.get("seller_count", 0))
        competitor_count = int(enriched.get("competitor_count", 0))
        vendor_count = int(perceived.get("vendor_count", 0))
        has_retail_price_band = bool((enriched.get("price_band") or {}).get("max"))
        return (
            confidence < LOW_CONFIDENCE_FAST_PATH_THRESHOLD
            and (
                seller_count == 0
                or competitor_count == 0
                or vendor_count == 0
                or not has_retail_price_band
            )
        )

    def _build_strategy_context(
        self,
        perceived: Dict[str, Any],
        enriched: Dict[str, Any],
        generation_type: str,
        parent_strategy_id: Optional[str],
    ) -> Dict[str, Any]:
        cache_key = self._make_context_cache_key(perceived, enriched, generation_type, parent_strategy_id)
        if cache_key in self._context_cache:
            cached = dict(self._context_cache[cache_key])
            if generation_type == "regenerate" and parent_strategy_id:
                cached["previous_strategy_angle"] = self._get_previous_strategy_angle(parent_strategy_id)
            return cached

        category_profile = self._infer_category_profile(enriched)
        product_profile = build_product_profile(enriched, category_profile)
        strategy_archetype = route_strategy_archetype(product_profile, enriched)
        previous_angle = self._get_previous_strategy_angle(parent_strategy_id)
        strategy_angle = self._select_strategy_angle(
            enriched,
            category_profile,
            generation_type=generation_type,
            previous_angle=previous_angle,
        )
        generation_mode = "fast_path" if self._should_use_fast_path(perceived, enriched) else "llm_hybrid"
        quality_band = self._resolve_quality_band(perceived)
        commercial_intelligence = perceived.get("commercial_intelligence") or {}
        compact_analytics = build_compact_analytics_summary(enriched)
        compact_analytics.setdefault("confidence_band", quality_band)
        compact_analytics.setdefault("low_sample_warning", bool(perceived.get("low_sample_warning", False)))
        compact_analytics.setdefault("sample_thresholds", perceived.get("sample_thresholds") or {})
        compact_analytics.setdefault("market_intelligence", perceived.get("market_intelligence") or {})
        compact_analytics.setdefault("evidence_ledger", perceived.get("evidence_ledger") or [])
        context = {
            "strategy_angle": strategy_angle,
            "generation_mode": generation_mode,
            "generation_type": generation_type,
            "variation_type": "baseline" if generation_type == "initial" else "angle_rotation",
            "category_profile": category_profile,
            "product_profile": product_profile,
            "strategy_archetype": strategy_archetype,
            "compact_analytics": compact_analytics,
            "competitor_summary": build_competitor_summary(enriched),
            "commercial_intelligence": commercial_intelligence,
            "quality_band": quality_band,
            "launch_scope": self._quality_band_limits(quality_band)["launch_scope"],
            "evidence_ledger": perceived.get("evidence_ledger") or [],
            "previous_strategy_angle": previous_angle,
        }
        marketing_intelligence = build_marketing_intelligence_bundle(enriched, context)
        context = {
            **context,
            "marketing_intelligence": marketing_intelligence,
            "marketing_decision_summary": marketing_intelligence["marketing_decision_summary"],
            "marketing_validation": marketing_intelligence["marketing_validation"],
            "category_playbook": marketing_intelligence["category_playbook"],
            "channel_recommendation": marketing_intelligence["channel_recommendation"],
            "budget_recommendation": marketing_intelligence["budget_recommendation"],
            "pricing_communication": marketing_intelligence["pricing_communication"],
            "risk_assessment": marketing_intelligence["risk_assessment"],
            "content_planning": marketing_intelligence["content_planning"],
            "kpi_recommendation": marketing_intelligence["kpi_recommendation"],
            "framework_outputs": marketing_intelligence["framework_outputs"],
        }
        self._context_cache[cache_key] = context
        return context

    def _build_fallback_context(self, enriched: Dict[str, Any]) -> Dict[str, Any]:
        profile = self._infer_category_profile(enriched)
        product_profile = build_product_profile(enriched, profile)
        quality_band = str(enriched.get("confidence_band") or (enriched.get("commercial_intelligence") or {}).get("quality_band") or "limited")
        compact_analytics = build_compact_analytics_summary(enriched)
        compact_analytics.setdefault("confidence_band", quality_band)
        compact_analytics.setdefault("low_sample_warning", bool(enriched.get("low_sample_warning", False)))
        compact_analytics.setdefault("sample_thresholds", enriched.get("sample_thresholds") or {})
        compact_analytics.setdefault("market_intelligence", enriched.get("market_intelligence") or {})
        compact_analytics.setdefault("evidence_ledger", enriched.get("evidence_ledger") or [])
        return {
            "strategy_angle": self._select_strategy_angle(enriched, profile, "initial", None),
            "generation_mode": "llm_hybrid",
            "generation_type": "initial",
            "variation_type": "baseline",
            "category_profile": profile,
            "product_profile": product_profile,
            "strategy_archetype": route_strategy_archetype(product_profile, enriched),
            "compact_analytics": compact_analytics,
            "competitor_summary": build_competitor_summary(enriched),
            "commercial_intelligence": enriched.get("commercial_intelligence") or {},
            "quality_band": quality_band,
            "launch_scope": self._launch_scope_for_quality_band(quality_band),
            "evidence_ledger": enriched.get("evidence_ledger") or [],
            "previous_strategy_angle": None,
        }

    def _resolve_quality_band(self, perceived: Dict[str, Any]) -> str:
        confidence = float(perceived.get("confidence_score", 0.0))
        low_sample_warning = bool(perceived.get("low_sample_warning", False))
        wholesale_count = int(perceived.get("vendor_count", 0))
        retail_count = int(perceived.get("seller_count", 0))
        margin_percent = float(perceived.get("margin_percent", 0.0))
        return classify_quality_band(
            confidence_score=confidence,
            low_sample_warning=low_sample_warning,
            wholesale_vendor_count=wholesale_count,
            retail_listing_count=retail_count,
            margin_percent=margin_percent if margin_percent else None,
        )

    def _quality_band_limits(self, quality_band: str) -> Dict[str, Any]:
        return QUALITY_BANDS.get(quality_band, QUALITY_BANDS["balanced"])

    def _launch_scope_for_quality_band(self, quality_band: str) -> str:
        return self._quality_band_limits(quality_band)["launch_scope"]

    def _build_evidence_ledger(self, enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        commercial = enriched.get("commercial_intelligence") or {}
        market_intelligence = commercial.get("market_intelligence") or {}
        profitability = commercial.get("profitability_summary") or {}
        price_band = profitability.get("price_band") or enriched.get("price_band") or {}
        ledger = list(commercial.get("evidence_ledger") or [])
        if ledger:
            return ledger
        ledger = []
        ledger.append({
            "recommendation": f"Price around PKR {float(enriched.get('sell_price_pkr', 0.0)):,.0f} because the observed retail band is PKR {float(price_band.get('min', 0.0)):,.0f}-{float(price_band.get('max', 0.0)):,.0f}.",
            "evidence": ["sell_price_pkr", "price_band", "expected_profit_margin"],
        })
        ledger.append({
            "recommendation": f"Keep the launch narrow because the quality band is {strategy_context.get('quality_band', 'limited')} and gross margin is {float(profitability.get('gross_margin_percent', 0.0)):.1f}%.",
            "evidence": ["confidence_band", "gross_margin_percent", "low_sample_warning"],
        })
        ledger.append({
            "recommendation": f"Use {market_intelligence.get('competition_score', 0.0):.0f}/100 competition pressure to justify channel and pricing discipline.",
            "evidence": ["competition_score", "market_saturation_score", "retail_price_band"],
        })
        ledger.append({
            "recommendation": f"Source from the current wholesale set and keep MOQ close to {enriched.get('moq_range', {}).get('min', 1)}-{enriched.get('moq_range', {}).get('max', 1)}.",
            "evidence": ["wholesale_vendors_count", "moq_range", "wholesale_origins"],
        })
        ledger.append({
            "recommendation": "Treat the profit engine as evidence-only: gross profit and observed spread are derived from market prices, not assumed operating costs.",
            "evidence": ["gross_profit_pkr", "gross_margin_percent", "observed_market_spread_pkr"],
        })
        return ledger

    def _make_context_cache_key(
        self,
        perceived: Dict[str, Any],
        enriched: Dict[str, Any],
        generation_type: str,
        parent_strategy_id: Optional[str],
    ) -> str:
        return "|".join(
            [
                str(perceived.get("product_name", "")),
                str(perceived.get("category", "")),
                str(perceived.get("buy_price_pkr", "")),
                str(perceived.get("sell_price_pkr", "")),
                str(perceived.get("confidence_score", "")),
                str(perceived.get("confidence_band", "")),
                str(perceived.get("low_sample_warning", "")),
                str(generation_type),
                str(parent_strategy_id or ""),
                str((enriched.get("price_band") or {}).get("avg", "")),
                str(enriched.get("competitor_count", "")),
            ]
        )

    def _infer_category_profile(self, enriched: Dict[str, Any]) -> Dict[str, Any]:
        combined = f"{enriched.get('product_name', '')} {enriched.get('category', '')}".lower()
        family = "generic_gadgets"
        if any(token in combined for token in ("iphone", "samsung", "redmi", "infinix", "phone", "mobile")):
            family = "mobile_phones"
        elif any(token in combined for token in ("hyperx", "headset", "headphone", "earbud", "earphone", "speaker")):
            family = "audio"
        elif any(token in combined for token in ("camera", "cctv", "webcam", "surveillance")):
            family = "cameras"
        elif any(token in combined for token in ("charger", "cable", "adapter", "power bank", "case")):
            family = "mobile_accessories"
        elif any(token in combined for token in ("mouse", "keyboard", "router", "ssd", "laptop")):
            family = "computer_accessories"

        avg_price = float((enriched.get("price_band") or {}).get("avg") or enriched.get("sell_price_pkr") or 0.0)
        if avg_price >= 120000:
            price_tier = "premium"
        elif avg_price >= 25000:
            price_tier = "mid_market"
        else:
            price_tier = "value"

        competitor_count = int(enriched.get("competitor_count", 0))
        seller_count = int(enriched.get("seller_count", 0))
        vendor_count = int(enriched.get("vendor_count", 0))
        competition_score = competitor_count + seller_count + max(vendor_count - 1, 0)
        if competition_score >= 10:
            competition_intensity = "high"
        elif competition_score >= 4:
            competition_intensity = "medium"
        else:
            competition_intensity = "low"

        audience_map = {
            "mobile_phones": "price-aware smartphone buyers who compare specs, authenticity, and resale confidence",
            "audio": "gaming and entertainment buyers who care about comfort, sound quality, and whether the listing feels genuine",
            "cameras": "security-conscious buyers who want clear setup confidence and reliable support",
            "mobile_accessories": "convenience buyers who convert on compatibility, bundles, and quick utility proof",
            "computer_accessories": "utility-driven buyers who want compatibility, reliability, and everyday performance proof",
            "generic_gadgets": "experimenting buyers who need a simple reason to believe the product is useful right now",
        }
        trust_map = {
            "mobile_phones": "warranty clarity and authentic device assurance",
            "audio": "authenticity, comfort, and credible feature proof",
            "cameras": "setup reassurance and after-sales clarity",
            "mobile_accessories": "compatibility proof and hassle-free delivery",
            "computer_accessories": "compatibility proof and durable quality control",
            "generic_gadgets": "simple demos and practical value proof",
        }
        format_map = {
            "mobile_phones": ["spec explainers", "comparison reels", "price-value carousels"],
            "audio": ["demo clips", "comfort-focused creatives", "feature comparisons"],
            "cameras": ["setup walkthroughs", "security use-case clips", "night-vision demos"],
            "mobile_accessories": ["bundle creatives", "problem-solution reels", "quick utility demos"],
            "computer_accessories": ["compatibility explainers", "desk setup reels", "speed demos"],
            "generic_gadgets": ["short demos", "before-after clips", "problem-solution posts"],
        }
        return {
            "family": family,
            "price_tier": price_tier,
            "competition_intensity": competition_intensity,
            "audience_archetype": audience_map[family],
            "trust_driver": trust_map[family],
            "content_formats": format_map[family],
        }

    def _ollama_chat(
        self,
        *,
        messages: List[Dict[str, str]],
        format: str = "json",
        temperature: float = 0.6,
        num_ctx: Optional[int] = None,
    ):
        started = time.perf_counter()
        client = ollama.Client(
            host=self.ollama_base_url,
            timeout=MARKETING_LLM_TIMEOUT_SECONDS,
        )
        response = client.chat(
            model=self.model,
            messages=messages,
            format=format,
            options={"temperature": temperature, "num_ctx": num_ctx or MARKETING_LLM_NUM_CTX},
        )
        elapsed = time.perf_counter() - started
        logger.info("Marketing Ollama call completed in %.2fs for model=%s", elapsed, self.model)
        return response

    def _get_previous_strategy_angle(self, parent_strategy_id: Optional[str]) -> Optional[str]:
        if not parent_strategy_id:
            return None
        try:
            if self.db is None:
                from app.services.ecdb import ECDB

                self.db = ECDB()
            previous = self.db.get_marketing_strategy_by_id(parent_strategy_id)
        except Exception:
            return None
        if not previous:
            return None
        strategy = previous.get("strategy") or {}
        meta = strategy.get("strategy_meta") or {}
        return meta.get("strategy_angle")

    def _select_strategy_angle(
        self,
        enriched: Dict[str, Any],
        category_profile: Dict[str, Any],
        generation_type: str,
        previous_angle: Optional[str],
    ) -> str:
        family = category_profile["family"]
        margin = float(enriched.get("margin_percent", 0.0))
        confidence = float(enriched.get("confidence_score", 0.0))
        quality_band = str(enriched.get("confidence_band") or (enriched.get("commercial_intelligence") or {}).get("quality_band") or "limited")
        low_sample_warning = bool(enriched.get("low_sample_warning", False))
        competition = category_profile["competition_intensity"]

        family_candidates = {
            "mobile_phones": ["risk_averse", "value_focus", "market_penetration", "premium_focus"],
            "audio": ["value_focus", "brand_building", "aggressive_growth", "risk_averse"],
            "cameras": ["risk_averse", "brand_building", "value_focus", "aggressive_growth"],
            "mobile_accessories": ["market_penetration", "aggressive_growth", "value_focus", "brand_building"],
            "computer_accessories": ["value_focus", "market_penetration", "risk_averse", "brand_building"],
            "generic_gadgets": ["risk_averse", "value_focus", "brand_building", "aggressive_growth"],
        }
        candidates = family_candidates.get(family, STRATEGY_ANGLES)

        if generation_type == "regenerate":
            if previous_angle in candidates:
                return candidates[(candidates.index(previous_angle) + 1) % len(candidates)]
            seed = hashlib.sha256(f"{enriched.get('product_name')}|regen".encode("utf-8")).hexdigest()
            return candidates[int(seed[:2], 16) % len(candidates)]

        if quality_band in {"limited", "guarded"} or low_sample_warning:
            if competition == "high" and quality_band == "guarded":
                return "market_penetration"
            return "risk_averse"
        if confidence < 0.25:
            return "risk_averse"
        if competition == "high":
            return "market_penetration"
        if margin >= 35:
            return "premium_focus"
        if margin >= 20:
            return "value_focus"
        return candidates[0]

    def _build_fast_path_strategy(self, enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> Dict[str, Any]:
        confidence = max(0.1, min(1.0, float(enriched.get("confidence_score", 0.0))))
        channels = self._build_dynamic_channels(enriched, strategy_context)
        launch_plan = self._build_dynamic_launch_plan(enriched, strategy_context)
        kpis = self._build_dynamic_kpis(enriched, strategy_context)
        launch_plan["kpis"] = kpis
        return {
            "stp": self._build_dynamic_stp(enriched, strategy_context),
            "swot": self._build_dynamic_swot(enriched, strategy_context),
            "pestel": self._build_dynamic_pestel(enriched, strategy_context),
            "competitor_analysis": self._build_dynamic_competitor_analysis(enriched, strategy_context),
            "marketing_mix": self._build_dynamic_marketing_mix(enriched, strategy_context, channels),
            "branding": self._build_dynamic_branding(enriched, strategy_context),
            "channels": channels,
            "content_strategy": self._build_dynamic_content_strategy(enriched, strategy_context),
            "launch_plan": launch_plan,
            "growth_funnel": self._build_dynamic_growth_funnel(enriched, strategy_context, kpis),
            "evidence_ledger": self._build_evidence_ledger(enriched, strategy_context),
            "validation_report": {
                "status": "ok",
                "checks": ["fast_path_strategy_generated"],
                "flags": ["used_fast_path_due_to_sparse_or_low_confidence_market_data"],
            },
            "confidence_score": confidence,
            "analysis_status": "ok",
        }

    def _build_dynamic_stp(self, enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> Dict[str, Any]:
        profile = strategy_context["category_profile"]
        angle = strategy_context["strategy_angle"]
        margin = float(enriched.get("margin_percent", 0.0))
        return {
            "segmentation": {
                "demographics": (
                    f"{profile['price_tier'].replace('_', ' ').title()} Pakistan buyers shopping for "
                    f"{profile['family'].replace('_', ' ')} around PKR {self._price_band_text(enriched)}."
                ),
                "psychographics": (
                    f"They want {profile['trust_driver']} and respond better to a {angle.replace('_', ' ')} message than to generic hype."
                ),
            },
            "targeting": {
                "primary_segment": self._targeting_text(profile, angle),
            },
            "positioning": {
                "statement": (
                    f"Position {enriched.get('product_name')} as the {angle.replace('_', ' ')} option: "
                    f"clearer to trust, easier to compare, and still aligned with a {margin:.1f}% target margin."
                ),
            },
        }

    def _targeting_text(self, profile: Dict[str, Any], angle: str) -> str:
        angle_map = {
            "value_focus": "buyers who want the safest value-for-money option without feeling they are sacrificing trust",
            "premium_focus": "buyers willing to pay more for stronger quality cues and a more polished experience",
            "aggressive_growth": "high-intent marketplace shoppers who can convert quickly when the offer is visible and easy to compare",
            "risk_averse": "careful first-wave buyers who need reassurance before they commit",
            "market_penetration": "comparison-heavy shoppers who can be won with sharper pricing and faster proof",
            "brand_building": "repeat-minded buyers who respond to consistency, memorability, and review capture",
        }
        return f"{angle_map[angle]}, especially within {profile['audience_archetype']}."

    def _build_dynamic_swot(self, enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> Dict[str, Any]:
        profile = strategy_context["category_profile"]
        competition = profile["competition_intensity"]
        confidence = float(enriched.get("confidence_score", 0.0))
        margin = float(enriched.get("margin_percent", 0.0))
        buy_price = float(enriched.get("buy_price_pkr", 0.0))
        sell_price = float(enriched.get("sell_price_pkr", 0.0))
        seller_count = int(enriched.get("seller_count", 0))
        vendor_count = int(enriched.get("vendor_count", 0))
        moq_min = int((enriched.get("moq_range") or {}).get("min") or 1)
        commercial = enriched.get("commercial_intelligence") or {}
        profitability = commercial.get("profitability_summary") or {}
        market_intelligence = commercial.get("market_intelligence") or {}

        strengths = [
            f"The current economics support buying around PKR {buy_price:,.0f} and selling near PKR {sell_price:,.0f}.",
            f"Target margin is roughly {margin:.1f}%, which is enough to support a focused launch message.",
        ]
        if profitability:
            strengths.append(
                f"Gross profit stays around PKR {profitability.get('gross_profit_pkr', 0.0):,.0f} based on the observed buy/sell spread."
            )
        if vendor_count > 1:
            strengths.append(f"{vendor_count} wholesale source signals reduce single-supplier concentration risk.")
        if seller_count > 0:
            strengths.append(f"Live retail presence across {seller_count} seller signal(s) gives the offer at least some visible demand context.")

        weaknesses = []
        if confidence < 0.35:
            weaknesses.append("Confidence is still low, so the first launch wave should validate demand before inventory or ad spend expands.")
        if seller_count < 2:
            weaknesses.append("Retail depth is thin, which makes forecasting and creative prioritization less certain.")
        if moq_min > 5:
            weaknesses.append(f"MOQ starts around {moq_min} units, so working capital can get trapped before product-market fit is proven.")
        if vendor_count <= 1:
            weaknesses.append("Supplier choice is still narrow, which limits negotiation leverage early on.")
        if profitability.get("gross_margin_percent", 0.0) < 10:
            weaknesses.append(f"Gross margin is only {profitability.get('gross_margin_percent', 0.0):.1f}%, so price spread matters more than headline volume.")

        opportunities = [
            f"The current retail band of PKR {self._price_band_text(enriched)} leaves room to test differentiated messaging without immediate race-to-the-bottom discounting.",
        ]
        if competition != "high":
            opportunities.append("A focused listing can still stand out with trust proof and clearer value communication.")
        else:
            opportunities.append("Better comparison copy and trust cues can steal attention from crowded but weakly differentiated listings.")
        if market_intelligence.get("opportunity_score", 0.0) > 60:
            opportunities.append("The evidence stack still supports a measured growth push if inventory stays disciplined.")

        family_threats = {
            "mobile_phones": "Rapid handset price resets and authenticity anxiety can erode trust and margin quickly.",
            "audio": "Lookalike audio gear and counterfeit concerns can flatten differentiation if proof is weak.",
            "cameras": "Privacy hesitation and setup complexity can slow conversion if reassurance is not immediate.",
            "mobile_accessories": "Commodity-style listings can erase differentiation fast when compatibility is not explicit.",
            "computer_accessories": "Compatibility doubt can block purchase even when headline pricing looks attractive.",
            "generic_gadgets": "Substitute gadgets can steal attention unless the use case is obvious in seconds.",
        }
        threats = [
            family_threats.get(profile["family"], "Competition can compress margins quickly when listings feel interchangeable."),
            f"{competition.title()} competition means price compression can happen quickly once multiple sellers chase the same traffic.",
        ]

        return {
            "strengths": strengths,
            "weaknesses": weaknesses or ["The launch should stay disciplined until stronger sell-through evidence appears."],
            "opportunities": opportunities,
            "threats": threats,
        }

    def _build_dynamic_pestel(self, enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> Dict[str, Any]:
        profile = strategy_context["category_profile"]
        family = profile["family"]
        angle = strategy_context["strategy_angle"].replace("_", " ")
        family_overrides = {
            "mobile_phones": (
                "Smartphone buyers compare specs, resale confidence, and authenticity before purchase.",
                "Comparison creatives and benchmark-style proof outperform generic branding in this category.",
                "Warranty wording, originality claims, and compliance messaging must stay precise.",
            ),
            "audio": (
                "Gaming and entertainment buyers care about comfort, mic clarity, and whether the offer feels genuine.",
                "Demo-led creatives and feature comparisons convert better than broad lifestyle messaging.",
                "Claims about comfort, compatibility, and battery should stay tightly grounded.",
            ),
            "cameras": (
                "Security-focused buyers need reassurance around setup, visibility, and day-to-day reliability.",
                "Installation demos and scenario-led content reduce hesitation more effectively than broad claims.",
                "Claims around storage, surveillance use, and performance need to stay exact.",
            ),
            "mobile_accessories": (
                "Accessory buyers are convenience-driven and often decide quickly once compatibility is clear.",
                "Problem-solution reels and bundle creatives improve understanding faster than generic visuals.",
                "Charging speed and compatibility claims should be exact to avoid returns.",
            ),
            "computer_accessories": (
                "Utility buyers respond to compatibility, reliability, and practical improvement claims.",
                "Desk-use demos and compatibility proof build confidence faster than broad branding.",
                "Performance and compatibility claims need to stay specific and supportable.",
            ),
            "generic_gadgets": (
                "Generic gadget buyers need a quick answer to why the item is useful right now.",
                "Short practical demos do more work here than abstract positioning language.",
                "Use-case claims should stay realistic so expectations do not outrun the offer.",
            ),
        }
        social, technological, legal = family_overrides.get(family, family_overrides["generic_gadgets"])
        return {
            "political": "Imported product economics can shift with duties and FX changes, so replenishment should stay disciplined.",
            "economic": f"Pakistan buyers remain price-sensitive, so a {angle} strategy must stay visibly grounded in market reality.",
            "social": social,
            "technological": technological,
            "environmental": "Packaging should protect the product in courier networks without making fulfillment inefficient.",
            "legal": legal,
        }

    def _build_dynamic_competitor_analysis(self, enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> Dict[str, Any]:
        competition = strategy_context["category_profile"]["competition_intensity"]
        vendor_count = int(enriched.get("vendor_count", 0))
        competitor_names = enriched.get("competitor_names") or ["Marketplace competitors"]
        return {
            "five_forces": {
                "supplier_power": "high" if vendor_count <= 1 else "medium",
                "buyer_power": "high" if competition != "low" else "medium",
                "competitive_rivalry": "high" if competition == "high" else "medium" if competition == "medium" else "low",
                "threat_of_substitutes": "high" if strategy_context["category_profile"]["family"] in {"mobile_accessories", "generic_gadgets"} else "medium",
                "threat_of_new_entrants": "medium",
            },
            "key_competitors": competitor_names[:5],
            "price_band": {
                "min": (enriched.get("price_band") or {}).get("min", enriched.get("sell_price_pkr", 0.0)),
                "max": (enriched.get("price_band") or {}).get("max", enriched.get("sell_price_pkr", 0.0)),
                "currency": "PKR",
            },
        }

    def _build_dynamic_marketing_mix(
        self,
        enriched: Dict[str, Any],
        strategy_context: Dict[str, Any],
        channels: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        angle = strategy_context["strategy_angle"]
        profile = strategy_context["category_profile"]
        sell_price = float(enriched.get("sell_price_pkr", 0.0))
        profitability = (enriched.get("commercial_intelligence") or {}).get("profitability_summary") or {}
        quality_band = strategy_context.get("quality_band", "limited")
        promotion_map = {
            "value_focus": [
                "Lead with price-value comparisons and visible trust badges.",
                "Use bundles or delivery incentives instead of deep discounting.",
            ],
            "premium_focus": [
                "Emphasize authenticity, quality cues, and better presentation in every creative.",
                "Use comparison creatives that justify why the offer deserves a stronger ticket.",
            ],
            "aggressive_growth": [
                "Push velocity with short-form video, retargeting, and stronger first-week marketplace visibility.",
                "Test multiple hooks quickly and scale only the top-converting angle.",
            ],
            "risk_averse": [
                "Keep claims conservative and focus on trust, returns, and practical proof before scaling spend.",
                "Use a narrow first-channel rollout to protect cash while learning.",
            ],
            "market_penetration": [
                "Open with sharper entry pricing and urgency-led offers to win initial share.",
                "Use marketplace promos and ads to dominate early clicks.",
            ],
            "brand_building": [
                "Build repeatable visual language, consistent proof points, and stronger review capture loops.",
                "Prioritize memorability and trust-building over short-lived discount noise.",
            ],
        }
        return {
            "product": {
                "description": f"{enriched.get('product_name')} positioned for {profile['audience_archetype']}.",
                "usp": f"Anchor the offer around {profile['trust_driver']} and a clearly explained use case.",
            },
            "price": {
                "strategy": f"{angle.replace('_', ' ').title()} pricing around PKR {sell_price:,.0f}, aligned to the observed retail band of PKR {self._price_band_text(enriched)} and a gross margin of {float(profitability.get('gross_margin_percent', 0.0)):.1f}%.",
                "recommended_sell_pkr": sell_price,
            },
            "place": {
                "channels": [channel["name"] for channel in channels],
            },
            "promotion": {
                "tactics": promotion_map[angle] if quality_band in {"balanced", "strong"} else promotion_map["risk_averse"],
            },
        }

    def _build_dynamic_branding(self, enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> Dict[str, Any]:
        angle = strategy_context["strategy_angle"]
        profile = strategy_context["category_profile"]
        tone_map = {
            "value_focus": "clear and reassuring",
            "premium_focus": "confident and elevated",
            "aggressive_growth": "direct and energetic",
            "risk_averse": "calm and trustworthy",
            "market_penetration": "urgent and practical",
            "brand_building": "memorable and credible",
        }
        tagline_map = {
            "value_focus": f"More proof, better value in {enriched.get('product_name')}.",
            "premium_focus": f"{enriched.get('product_name')} with a stronger reason to choose it.",
            "aggressive_growth": f"Move faster with the right {enriched.get('product_name')}.",
            "risk_averse": f"{enriched.get('product_name')} you can buy with more confidence.",
            "market_penetration": f"Switch to smarter value with {enriched.get('product_name')}.",
            "brand_building": f"Make {enriched.get('product_name')} the name buyers remember.",
        }
        return {
            "value_proposition": (
                f"Offer {enriched.get('product_name')} with a {angle.replace('_', ' ')} promise built around {profile['trust_driver']}."
            ),
            "tone": tone_map[angle],
            "tagline": tagline_map[angle],
        }

    def _build_dynamic_channels(self, enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        platform_distribution = enriched.get("platform_distribution") or {}
        angle = strategy_context["strategy_angle"]
        quality_band = strategy_context.get("quality_band", "limited")
        limits = self._quality_band_limits(quality_band)
        channel_priority: List[tuple[str, str]] = []

        for name, count in sorted(platform_distribution.items(), key=lambda item: item[1], reverse=True):
            channel_priority.append((name, f"Observed {count} relevant listing(s) on this platform during scraping."))

        if angle in {"aggressive_growth", "brand_building"} and quality_band in {"balanced", "strong"}:
            channel_priority.append(("instagram", "Useful for visual proof, creator-style content, and retargeting audiences."))
        if angle in {"market_penetration", "aggressive_growth"} and quality_band in {"balanced", "strong"}:
            channel_priority.append(("tiktok_shop", "Good fit for fast experimentation and higher-velocity offer testing in Pakistan."))
        if strategy_context["category_profile"]["family"] in {"mobile_phones", "audio", "cameras"}:
            channel_priority.append(("daraz", "Marketplace trust and search intent make this a dependable primary conversion surface."))

        normalized: List[Dict[str, Any]] = []
        seen = set()
        for name, rationale in channel_priority:
            key = (name or "").lower()
            if not key or key in seen:
                continue
            seen.add(key)
            normalized.append({
                "name": name,
                "priority": len(normalized) + 1,
                "rationale": rationale,
            })
        if not normalized:
            normalized.append({
                "name": "daraz",
                "priority": 1,
                "rationale": "Default first channel because marketplace demand proof is easiest to validate there.",
            })
        return normalized[: int(limits["max_channels"])]

    def _build_dynamic_content_strategy(self, enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> Dict[str, Any]:
        quality_band = strategy_context.get("quality_band", "limited")
        cadence = self._quality_band_limits(quality_band)["content_frequency"]
        if strategy_context["strategy_angle"] in {"aggressive_growth", "brand_building"} and quality_band in {"balanced", "strong"}:
            cadence = "4 focused posts per week"
        return {
            "formats": strategy_context["category_profile"]["content_formats"],
            "frequency": cadence,
        }

    def _build_dynamic_kpis(self, enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        confidence = float(enriched.get("confidence_score", 0.0))
        angle = strategy_context["strategy_angle"]
        competition = strategy_context["category_profile"]["competition_intensity"]
        sell_price = float(enriched.get("sell_price_pkr", 0.0))
        quality_band = strategy_context.get("quality_band", "limited")
        limits = self._quality_band_limits(quality_band)
        scope_multiplier = float(limits["orders_multiplier"])

        base_orders = max(3, int(round(((confidence * 16) + 6) * scope_multiplier)))
        if angle == "aggressive_growth":
            base_orders += 4 if quality_band in {"balanced", "strong"} else 1
        elif angle == "market_penetration":
            base_orders += 2 if quality_band in {"balanced", "strong"} else 0
        elif angle == "risk_averse":
            base_orders = max(3, base_orders - 2)
        elif angle == "premium_focus":
            base_orders = max(3, base_orders - 1)
        elif angle == "brand_building":
            base_orders = max(3, base_orders - 1)

        if competition == "high":
            base_orders = max(3, base_orders - 2)

        view_multiplier = {
            "value_focus": 75,
            "premium_focus": 60,
            "aggressive_growth": 95,
            "risk_averse": 50,
            "market_penetration": 85,
            "brand_building": 100,
        }[angle]
        views_target = max(200, int(base_orders * view_multiplier * float(limits["views_multiplier"])))
        conversion_target = round(max(1.0, min(4.0, confidence * 3.2 + (0.4 if angle == "market_penetration" else 0.0))), 1)
        revenue_target = int(base_orders * sell_price)
        kpis = [
            {"metric": "Qualified listing views", "target": views_target, "period": "Week 1"},
            {"metric": "Orders", "target": base_orders, "period": "Month 1"},
            {"metric": "Gross revenue (PKR)", "target": revenue_target, "period": "Month 1"},
            {"metric": "Conversion rate %", "target": conversion_target, "period": "Week 2"},
        ]
        return kpis[: int(limits["max_kpis"])]

    def _build_dynamic_launch_plan(self, enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> Dict[str, Any]:
        angle = strategy_context["strategy_angle"]
        family = strategy_context["category_profile"]["family"]
        quality_band = strategy_context.get("quality_band", "limited")
        limits = self._quality_band_limits(quality_band)
        channels = self._build_dynamic_channels(enriched, strategy_context)
        primary_channel = channels[0]["name"]
        moq_min = int((enriched.get("moq_range") or {}).get("min") or 1)
        angle_actions = {
            "value_focus": "lead with price-proof creatives and bundle messaging",
            "premium_focus": "lead with quality proof, trust badges, and stronger presentation",
            "aggressive_growth": "test more creatives quickly and scale only the winners",
            "risk_averse": "launch narrowly, monitor returns, and validate demand before widening inventory",
            "market_penetration": "enter with sharper pricing and first-order conversion offers",
            "brand_building": "build repeatable visual language and capture reviews early",
        }
        family_setup = {
            "mobile_phones": "Show authenticity, warranty proof, and comparison hooks in the first screen.",
            "audio": "Lead with comfort, authenticity, and use-case proof instead of vague lifestyle claims.",
            "cameras": "Show setup simplicity, app clarity, and real surveillance use cases above the fold.",
            "mobile_accessories": "Highlight compatibility, bundle utility, and delivery convenience immediately.",
            "computer_accessories": "Lead with compatibility proof and practical use-case clarity.",
            "generic_gadgets": "Show the problem-solution payoff in the first creative and listing module.",
        }
        phases = [
            {
                "name": "Launch Setup",
                "duration": "5-7 days",
                "actions": [
                    f"Prepare the first {primary_channel} listing with {angle_actions[angle]}.",
                    family_setup.get(family, "Make trust signals and delivery expectations visible above the fold."),
                ],
            },
            {
                "name": "Signal Capture",
                "duration": "7-10 days",
                "actions": [
                    "Track CTR, conversion, and the top customer objections before widening spend.",
                    f"Keep replenishment close to the lower MOQ band around {moq_min} units until sell-through is clearer.",
                ],
            },
            {
                "name": "Scale Decision",
                "duration": "2 weeks",
                "actions": [
                    "Reallocate budget toward the best-performing creative hook and channel.",
                    "Decide whether to widen channels, renegotiate supply, or hold the launch if unit economics soften.",
                ],
            },
        ]
        if quality_band in {"limited", "guarded"}:
            phases = phases[:2]
            phases[-1]["name"] = "Validation Gate"
            phases[-1]["duration"] = "7-10 days"
            phases[-1]["actions"] = [
                "Hold spend tight and validate whether the offer is earning traction before expansion.",
                "Use only the narrowest set of channels and avoid inventory widening until evidence improves.",
            ]
        return {
            "phases": phases,
            "measurement_plan": {
                "tools": ["Marketplace analytics", "Manual competitor checks", "Ad manager reports"],
                "cadence": "Twice weekly" if quality_band in {"balanced", "strong"} else "Weekly",
            },
        }

    def _build_dynamic_growth_funnel(
        self,
        enriched: Dict[str, Any],
        strategy_context: Dict[str, Any],
        kpis: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        confidence = float(enriched.get("confidence_score", 0.0))
        quality_band = strategy_context.get("quality_band", "limited")
        limits = self._quality_band_limits(quality_band)
        orders_target = next((item["target"] for item in kpis if item["metric"] == "Orders"), 8)
        views_target = next((item["target"] for item in kpis if item["metric"] == "Qualified listing views"), 400)
        add_to_cart_target = max(10, int(round(views_target * max(0.02, confidence * 0.06))))
        repeat_target = max(1, int(round(orders_target * (0.2 if quality_band in {"limited", "guarded"} else 0.25))))
        stages = [
            {"stage": "Acquisition", "metric": "Qualified listing views", "target": views_target},
            {"stage": "Activation", "metric": "Add to cart actions", "target": add_to_cart_target},
            {"stage": "Revenue", "metric": "Orders", "target": orders_target},
            {"stage": "Retention", "metric": "Repeat buyers / referral conversions", "target": repeat_target},
        ]
        return {
            "model": "AARRR",
            "stages": stages[: int(limits["max_kpis"])],
        }

    def _build_price_recommendation_text(self, enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> str:
        angle = strategy_context["strategy_angle"].replace("_", " ")
        return (
            f"Use a {angle} sell story around PKR {float(enriched.get('sell_price_pkr', 0.0)):,.0f}, "
            f"because the observed retail band sits around PKR {self._price_band_text(enriched)}."
        )

    def _build_supply_recommendation_text(self, enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> str:
        origins = ", ".join((enriched.get("wholesale_origins") or ["available suppliers"])[:3])
        return (
            f"Source carefully from {origins} near PKR {float(enriched.get('buy_price_pkr', 0.0)):,.0f} "
            "and keep early orders close to the minimum practical MOQ."
        )

    def _price_band_text(self, enriched: Dict[str, Any]) -> str:
        price_band = enriched.get("price_band") or {}
        return f"{price_band.get('min', 0):,.0f}-{price_band.get('max', 0):,.0f}"

    def _apply_strategy_angle_overrides(
        self,
        strategy: Dict[str, Any],
        enriched: Dict[str, Any],
        strategy_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        strategy = dict(strategy)
        dynamic_stp = self._build_dynamic_stp(enriched, strategy_context)
        dynamic_branding = self._build_dynamic_branding(enriched, strategy_context)
        dynamic_channels = self._build_dynamic_channels(enriched, strategy_context)
        dynamic_content = self._build_dynamic_content_strategy(enriched, strategy_context)
        dynamic_kpis = self._build_dynamic_kpis(enriched, strategy_context)
        dynamic_launch = self._build_dynamic_launch_plan(enriched, strategy_context)
        dynamic_growth = self._build_dynamic_growth_funnel(enriched, strategy_context, dynamic_kpis)
        dynamic_mix = self._build_dynamic_marketing_mix(enriched, strategy_context, dynamic_channels)
        limits = self._quality_band_limits(strategy_context.get("quality_band", "limited"))

        existing_stp = strategy.get("stp") or {}
        strategy["stp"] = {
            "segmentation": existing_stp.get("segmentation") or dynamic_stp["segmentation"],
            "targeting": existing_stp.get("targeting") or dynamic_stp["targeting"],
            "positioning": existing_stp.get("positioning") or dynamic_stp["positioning"],
        }
        strategy["swot"] = strategy.get("swot") or self._build_dynamic_swot(enriched, strategy_context)
        strategy["pestel"] = strategy.get("pestel") or self._build_dynamic_pestel(enriched, strategy_context)
        strategy["competitor_analysis"] = strategy.get("competitor_analysis") or self._build_dynamic_competitor_analysis(enriched, strategy_context)

        existing_branding = strategy.get("branding") or {}
        strategy["branding"] = {
            "value_proposition": existing_branding.get("value_proposition") or dynamic_branding["value_proposition"],
            "tone": existing_branding.get("tone") or dynamic_branding["tone"],
            "tagline": existing_branding.get("tagline") or dynamic_branding["tagline"],
        }

        existing_channels = list(strategy.get("channels") or [])
        strategy["channels"] = (existing_channels[: int(limits["max_channels"])] if existing_channels else dynamic_channels)

        existing_content = strategy.get("content_strategy") or {}
        strategy["content_strategy"] = {
            **dynamic_content,
            **existing_content,
        }
        if not strategy["content_strategy"].get("frequency"):
            strategy["content_strategy"]["frequency"] = dynamic_content["frequency"]

        existing_launch = strategy.get("launch_plan") or {}
        merged_launch = {**dynamic_launch, **existing_launch}
        existing_kpis = list(existing_launch.get("kpis") or [])
        merged_launch["kpis"] = existing_kpis[: int(limits["max_kpis"])] if existing_kpis else dynamic_kpis
        strategy["launch_plan"] = merged_launch
        strategy["growth_funnel"] = strategy.get("growth_funnel") or dynamic_growth
        strategy["marketing_mix"] = {
            "product": {**dynamic_mix["product"], **((strategy.get("marketing_mix") or {}).get("product") or {})},
            "price": {**dynamic_mix["price"], **((strategy.get("marketing_mix") or {}).get("price") or {})},
            "place": {**dynamic_mix["place"], **((strategy.get("marketing_mix") or {}).get("place") or {})},
            "promotion": {**dynamic_mix["promotion"], **((strategy.get("marketing_mix") or {}).get("promotion") or {})},
        }
        strategy["evidence_ledger"] = self._build_evidence_ledger(enriched, strategy_context)
        return strategy

    def _apply_strategy_metadata(self, strategy: Dict[str, Any], strategy_context: Dict[str, Any]) -> Dict[str, Any]:
        strategy = dict(strategy)
        compact_analytics = strategy_context.get("compact_analytics") or {}
        strategy["strategy_meta"] = {
            "strategy_angle": strategy_context["strategy_angle"],
            "generation_mode": strategy_context["generation_mode"],
            "variation_type": strategy_context["variation_type"],
            "category_family": strategy_context["category_profile"]["family"],
            "price_tier": strategy_context["category_profile"]["price_tier"],
            "competition_intensity": strategy_context["category_profile"]["competition_intensity"],
            "quality_band": strategy_context.get("quality_band", compact_analytics.get("confidence_band", "limited")),
            "launch_scope": strategy_context.get("launch_scope", "standard"),
            "channel_count": len(strategy.get("channels") or []),
            "evidence_coverage_score": min(1.0, len(strategy.get("evidence_ledger") or []) / 5.0),
            "product_profile": strategy_context.get("product_profile"),
            "strategy_archetype": strategy_context.get("strategy_archetype"),
            "competitor_summary": strategy_context.get("competitor_summary"),
            "compact_analytics": compact_analytics,
            "commercial_intelligence": strategy_context.get("commercial_intelligence") or {},
        }
        marketing_intelligence = strategy_context.get("marketing_intelligence") or {}
        strategy["marketing_intelligence"] = marketing_intelligence
        strategy["marketing_decision_summary"] = strategy_context.get("marketing_decision_summary") or marketing_intelligence.get("marketing_decision_summary") or {}
        strategy["marketing_validation"] = strategy_context.get("marketing_validation") or marketing_intelligence.get("marketing_validation") or {}
        strategy["category_playbook"] = strategy_context.get("category_playbook") or marketing_intelligence.get("category_playbook") or {}
        strategy["customer_intelligence"] = marketing_intelligence.get("customer_intelligence") or {}
        strategy["market_intelligence"] = marketing_intelligence.get("market_intelligence") or {}
        strategy["competitor_intelligence"] = marketing_intelligence.get("competitor_intelligence") or {}
        strategy["brand_positioning"] = marketing_intelligence.get("brand_positioning") or {}
        strategy["channel_recommendation"] = strategy_context.get("channel_recommendation") or marketing_intelligence.get("channel_recommendation") or {}
        strategy["budget_recommendation"] = strategy_context.get("budget_recommendation") or marketing_intelligence.get("budget_recommendation") or {}
        strategy["pricing_communication"] = strategy_context.get("pricing_communication") or marketing_intelligence.get("pricing_communication") or {}
        strategy["risk_assessment"] = strategy_context.get("risk_assessment") or marketing_intelligence.get("risk_assessment") or {}
        strategy["content_planning"] = strategy_context.get("content_planning") or marketing_intelligence.get("content_planning") or {}
        strategy["kpi_recommendation"] = strategy_context.get("kpi_recommendation") or marketing_intelligence.get("kpi_recommendation") or {}
        strategy["framework_outputs"] = strategy_context.get("framework_outputs") or marketing_intelligence.get("framework_outputs") or {}
        return strategy

    def _load_previous_strategies(
        self,
        analytics_result_id: Optional[str],
        pipeline_run_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        try:
            if self.db is None:
                from app.services.ecdb import ECDB

                self.db = ECDB()
        except Exception:
            return []

        rows: List[Dict[str, Any]] = []
        try:
            if analytics_result_id:
                latest = self.db.get_latest_marketing_strategy_by_analytics(analytics_result_id)
                if latest:
                    rows.append(latest)
            elif pipeline_run_id:
                latest = self.db.get_latest_marketing_strategy_by_pipeline(pipeline_run_id)
                if latest:
                    rows.append(latest)
        except Exception:
            return []
        return rows

    def _regenerate_sections(
        self,
        strategy: Dict[str, Any],
        enriched: Dict[str, Any],
        strategy_context: Dict[str, Any],
        previous_strategy: Dict[str, Any],
    ) -> Dict[str, Any]:
        sections = ["stp", "branding", "channels", "content_strategy", "marketing_mix"]
        try:
            response = self._ollama_chat(
                messages=[
                    {"role": "system", "content": self._build_system_prompt(strategy_context)},
                    {
                        "role": "user",
                        "content": self._build_user_prompt(
                            enriched,
                            strategy_context,
                            sections=sections,
                            existing_strategy=strategy,
                            previous_strategy=previous_strategy,
                        ),
                    },
                ],
                format="json",
                temperature=0.75,
            )
            patch = self._extract_json(response.message.content)
        except Exception as exc:
            logger.warning("Similarity regeneration failed: %s", exc)
            return strategy

        if patch.get("analysis_status") == "invalid":
            return strategy

        merged = dict(strategy)
        for section in sections:
            if patch.get(section):
                merged[section] = patch[section]
        return merged

    def _apply_similarity_guard(
        self,
        strategy: Dict[str, Any],
        enriched: Dict[str, Any],
        strategy_context: Dict[str, Any],
        product_name: str,
        category: str,
        analytics_result_id: Optional[str],
        pipeline_run_id: Optional[str],
    ) -> Dict[str, Any]:
        previous_rows = self._load_previous_strategies(analytics_result_id, pipeline_run_id)
        if not previous_rows:
            strategy.setdefault("strategy_meta", {})
            strategy["strategy_meta"]["similarity_check"] = {"compared_count": 0, "too_similar": False, "score": 0.0}
            return strategy

        similarity = compare_with_history(strategy, previous_rows)
        strategy.setdefault("strategy_meta", {})
        strategy["strategy_meta"]["similarity_check"] = similarity

        if not similarity["too_similar"]:
            return strategy

        if strategy_context.get("generation_type") != "regenerate" or not ENABLE_SIMILARITY_REGEN:
            strategy["strategy_meta"]["similarity_check"] = {
                **similarity,
                "regenerated_due_to_similarity": False,
                "skipped_reason": "disabled_for_default_runtime",
            }
            return strategy

        prior = previous_rows[0].get("strategy") if isinstance(previous_rows[0].get("strategy"), dict) else previous_rows[0]
        secondary = (strategy_context.get("strategy_archetype") or {}).get("secondary")
        if secondary:
            strategy_context = {
                **strategy_context,
                "variation_type": "similarity_regeneration",
            }
        regenerated = self._regenerate_sections(strategy, enriched, strategy_context, prior or {})
        regenerated = self._apply_strategy_metadata(regenerated, strategy_context)
        regenerated.setdefault("strategy_meta", {})
        regenerated["strategy_meta"]["similarity_check"] = {
            **similarity,
            "regenerated_due_to_similarity": True,
            "product_name": product_name,
            "category": category,
        }
        return regenerated

    # ------------------------------------------------------------------
    # Step 1 - Perceive
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
        margin = float(analytics_result.get("gross_margin_percent", analytics_result["expected_profit_margin"]))
        confidence = float(analytics_result["confidence_score"])

        if buy <= 0 or sell <= 0:
            raise ValueError("recommended_buy_price_pkr and recommended_sell_price_pkr must be positive")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"confidence_score must be between 0 and 1, got {confidence}")
        if not math.isfinite(margin):
            raise ValueError(f"expected_profit_margin must be a finite number, got {margin}")

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
            "gross_profit_pkr": float(analytics_result.get("gross_profit_pkr", 0.0)),
            "observed_market_spread_pkr": round(sell - buy, 2),
            "observed_market_spread": round(sell - buy, 2),
            "net_profit_pkr": float(analytics_result.get("gross_profit_pkr", analytics_result.get("net_profit_pkr", 0.0))),
            "gross_margin_percent": float(analytics_result.get("gross_margin_percent", margin)),
            "roi_percent": float(analytics_result.get("roi_percent", 0.0)),
            "break_even_sell_price_pkr": float(analytics_result.get("break_even_sell_price_pkr", 0.0)),
            "profitability_confidence": float(analytics_result.get("profitability_confidence", confidence)),
            "confidence_band": analytics_result.get("confidence_band", "limited"),
            "low_sample_warning": bool(analytics_result.get("low_sample_warning", False)),
            "sample_thresholds": analytics_result.get("sample_thresholds") or {},
            "profitability_summary": analytics_result.get("profitability_summary") or {},
            "market_intelligence": analytics_result.get("market_intelligence") or {},
            "commercial_intelligence": analytics_result.get("commercial_intelligence") or {},
            "evidence_ledger": analytics_result.get("evidence_ledger") or [],
        }

    # ------------------------------------------------------------------
    # Step 2 - Enrich
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
    # Step 3 - Generate
    # ------------------------------------------------------------------

    def _generate(self, enriched: Dict[str, Any], strategy_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        strategy_context = strategy_context or self._build_fallback_context(enriched)
        system_prompt = self._build_system_prompt(strategy_context)
        user_content = self._build_user_prompt(enriched, strategy_context)
        response = self._ollama_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            format="json",
            temperature=0.55,
        )
        result = self._extract_json(response.message.content)
        if result.get("analysis_status") == "invalid":
            logger.warning(
                "Model returned unparseable JSON for product=%r; validation will flag",
                enriched.get("product_name"),
            )
        return result

    def _build_system_prompt(self, strategy_context: Dict[str, Any]) -> str:
        return build_marketing_system_prompt(strategy_context, PAKISTAN_CONTEXT)

    def _build_user_prompt(
        self,
        enriched: Dict[str, Any],
        strategy_context: Dict[str, Any],
        sections: Optional[List[str]] = None,
        existing_strategy: Optional[Dict[str, Any]] = None,
        previous_strategy: Optional[Dict[str, Any]] = None,
    ) -> str:
        return build_marketing_user_prompt(
            enriched.get("product_name", ""),
            enriched.get("category", ""),
            strategy_context,
            sections=sections,
            existing_strategy=existing_strategy,
            previous_strategy=previous_strategy,
        )

    def _extract_json(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

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
            "stp": {},
            "swot": {},
            "pestel": {},
            "competitor_analysis": {},
            "marketing_mix": {},
            "branding": {},
            "channels": [],
            "content_strategy": {},
            "launch_plan": {},
            "growth_funnel": {"model": "AARRR", "stages": []},
            "evidence_ledger": [],
            "validation_report": {"status": "invalid", "checks": [], "flags": [reason]},
            "confidence_score": 0.0,
            "analysis_status": "invalid",
        }

    def _ensure_evidence_ledger(self, strategy: Dict[str, Any], enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> Dict[str, Any]:
        strategy = dict(strategy)
        built_ledger = self._build_evidence_ledger(enriched, strategy_context)
        existing_ledger = strategy.get("evidence_ledger") or []
        combined: List[Dict[str, Any]] = []
        seen = set()
        for entry in built_ledger + list(existing_ledger):
            recommendation = str(entry.get("recommendation") or "").strip()
            key = recommendation.lower()
            if not key or key in seen:
                continue
            seen.add(key)
            combined.append(entry)
        strategy["evidence_ledger"] = combined or built_ledger
        return strategy

    def _ensure_kpis(
        self,
        strategy: Dict[str, Any],
        perceived: Dict[str, Any],
        enriched: Dict[str, Any],
        strategy_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        launch_plan = strategy.get("launch_plan") or {}
        if launch_plan.get("kpis"):
            return strategy
        strategy = dict(strategy)
        strategy["launch_plan"] = {
            **launch_plan,
            "kpis": self._build_dynamic_kpis(enriched, strategy_context),
        }
        return strategy

    # ------------------------------------------------------------------
    # Step 4 - Validate
    # ------------------------------------------------------------------

    def _validate(self, strategy: Dict[str, Any], perceived: Dict[str, Any]) -> Dict[str, Any]:
        strategy = dict(strategy)
        flags: List[str] = []
        checks: List[str] = []

        for key in REQUIRED_OUTPUT_KEYS:
            if key not in strategy:
                flags.append(f"missing_key:{key}")
            else:
                checks.append(f"present:{key}")

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

        if strategy.get("analysis_status") == "invalid":
            flags.append("analysis_status:invalid from generate step")

        evidence_ledger = strategy.get("evidence_ledger") or []
        if not evidence_ledger:
            flags.append("evidence_ledger:empty")
        else:
            checks.append("evidence_ledger:populated")
            if len(evidence_ledger) < 3:
                flags.append("evidence_ledger:thin")

        kpis = (strategy.get("launch_plan") or {}).get("kpis")
        if not kpis:
            flags.append("launch_plan.kpis:empty")
        else:
            checks.append("launch_plan.kpis:populated")

        soft_prefixes = ("evidence_ledger:thin", "launch_plan.kpis")
        hard_flags = [flag for flag in flags if not any(flag.startswith(prefix) for prefix in soft_prefixes)]
        status = "ok" if not hard_flags else "needs_review" if len(hard_flags) <= 2 else "invalid"
        strategy["validation_report"] = {
            "status": status,
            "checks": checks,
            "flags": flags,
        }
        if status != "ok":
            strategy["analysis_status"] = status
        return strategy

    # ------------------------------------------------------------------
    # Step 5 - Critic
    # ------------------------------------------------------------------

    def _critic(
        self,
        strategy: Dict[str, Any],
        enriched: Dict[str, Any],
        strategy_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        strategy_context = strategy_context or self._build_fallback_context(enriched)
        if not ENABLE_MARKETING_CRITIC:
            logger.info("Critic skipped - disabled for default runtime")
            return strategy
        flags = (strategy.get("validation_report") or {}).get("flags") or []
        if not flags:
            return strategy

        soft_prefixes = ("evidence_ledger", "launch_plan.kpis", "confidence_score out of range")
        hard_flags = [flag for flag in flags if not any(flag.startswith(prefix) for prefix in soft_prefixes)]
        if not hard_flags:
            logger.info("Critic skipped - all flags are soft and handled by Python post-processing")
            return strategy

        critic_prompt = (
            "You are a critical reviewer. The marketing strategy below has validation issues. "
            "Fix ONLY the flagged problems. Keep the current strategy angle and category behavior intact. "
            "Return a single JSON object only.\n\n"
            f"STRATEGY CONTEXT:\n{json.dumps(strategy_context)}\n\n"
            f"FLAGS:\n{json.dumps(flags)}\n\n"
            f"STRATEGY:\n{json.dumps(strategy)}"
        )
        try:
            response = self._ollama_chat(
                messages=[{"role": "user", "content": critic_prompt}],
                format="json",
                temperature=0.2,
            )
            improved = self._extract_json(response.message.content)
            if improved.get("analysis_status") != "invalid" and improved.get("stp"):
                return improved
        except Exception as exc:
            logger.warning("Critic pass failed: %s - keeping validated strategy", exc)
        return strategy

    # ------------------------------------------------------------------
    # Step 6 - Store
    # ------------------------------------------------------------------

    def _store(
        self,
        strategy: Dict[str, Any],
        product_name: str,
        category: str,
        pipeline_run_id: Optional[str],
        analytics_result_id: Optional[str],
        product_cluster_id: Optional[str],
        parent_strategy_id: Optional[str],
        generation_type: str,
    ) -> Dict[str, Any]:
        strategy = dict(strategy)
        payload: Dict[str, Any] = {
            "product_name": product_name,
            "category": category,
            "strategy": strategy,
            "analysis_status": strategy.get("analysis_status", "ok"),
            "strategy_status": "generated",
            "confidence_score": strategy.get("confidence_score"),
            "analytics_result_id": analytics_result_id,
            "product_cluster_id": product_cluster_id,
            "generation_type": generation_type or "initial",
        }
        if pipeline_run_id:
            payload["pipeline_run_id"] = pipeline_run_id
        if parent_strategy_id:
            payload["parent_strategy_id"] = parent_strategy_id
        try:
            if self.db is None:
                from app.services.ecdb import ECDB

                self.db = ECDB()
            stored = self.db.insert_marketing_strategy(payload)
            if not stored.get("id"):
                logger.error(
                    "DB insert returned no id for product=%r - marketing strategy insert may have failed silently",
                    product_name,
                )
                strategy["storage_status"] = "failed"
                strategy["storage_error"] = "marketing strategy insert returned no id"
                return strategy
            return {**stored, **strategy, "storage_status": "stored"}
        except Exception as exc:
            logger.warning("Marketing strategy persistence failed for %r: %s", product_name, exc)
            strategy["storage_status"] = "failed"
            strategy["storage_error"] = str(exc)
            return strategy





