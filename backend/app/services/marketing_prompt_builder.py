from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


RESPONSE_SCHEMA = {
    "stp": {"segmentation": {"demographics": "", "psychographics": ""}, "targeting": {"primary_segment": ""}, "positioning": {"statement": ""}},
    "swot": {"strengths": [""], "weaknesses": [""], "opportunities": [""], "threats": [""]},
    "pestel": {"political": "", "economic": "", "social": "", "technological": "", "environmental": "", "legal": ""},
    "competitor_analysis": {"five_forces": {"supplier_power": "", "buyer_power": "", "competitive_rivalry": "", "threat_of_substitutes": "", "threat_of_new_entrants": ""}, "key_competitors": [""], "price_band": {"min": 0, "max": 0, "currency": "PKR"}},
    "marketing_mix": {"product": {"description": "", "usp": ""}, "price": {"strategy": "", "recommended_sell_pkr": 0}, "place": {"channels": [""]}, "promotion": {"tactics": [""]}},
    "branding": {"value_proposition": "", "tone": "", "tagline": ""},
    "channels": [{"name": "", "priority": 1, "rationale": ""}],
    "content_strategy": {"formats": [""], "frequency": ""},
    "launch_plan": {"phases": [{"name": "", "duration": "", "actions": [""]}], "kpis": [{"metric": "", "target": 0, "period": ""}], "measurement_plan": {"tools": [""], "cadence": ""}},
    "growth_funnel": {"model": "AARRR", "stages": [{"stage": "", "metric": "", "target": 0}]},
    "evidence_ledger": [{"recommendation": "", "evidence": [""]}],
    "validation_report": {"status": "ok", "checks": [], "flags": []},
    "confidence_score": 0.75,
    "analysis_status": "ok",
    "marketing_intelligence": {},
    "marketing_decision_summary": {},
    "framework_outputs": {},
}


def build_compact_analytics_summary(enriched: Dict[str, Any]) -> Dict[str, Any]:
    price_band = enriched.get("price_band") or {}
    profitability_summary = enriched.get("profitability_summary") or {}
    market_intelligence = enriched.get("market_intelligence") or {}
    commercial_intelligence = enriched.get("commercial_intelligence") or {}
    return {
        "buy_price_pkr": round(float(enriched.get("buy_price_pkr", 0.0)), 2),
        "sell_price_pkr": round(float(enriched.get("sell_price_pkr", 0.0)), 2),
        "margin_percent": round(float(enriched.get("gross_margin_percent", enriched.get("margin_percent", 0.0))), 2),
        "gross_margin_percent": round(float(enriched.get("gross_margin_percent", enriched.get("margin_percent", 0.0))), 2),
        "confidence_score": round(float(enriched.get("confidence_score", 0.0)), 3),
        "confidence_band": enriched.get("confidence_band") or commercial_intelligence.get("quality_band") or "limited",
        "vendor_count": int(enriched.get("vendor_count", 0)),
        "seller_count": int(enriched.get("seller_count", 0)),
        "low_sample_warning": bool(enriched.get("low_sample_warning", False)),
        "sample_thresholds": enriched.get("sample_thresholds") or {},
        "gross_profit_pkr": round(float(enriched.get("gross_profit_pkr", profitability_summary.get("gross_profit_pkr", 0.0))), 2),
        "observed_market_spread_pkr": round(float(enriched.get("observed_market_spread_pkr", profitability_summary.get("observed_market_spread_pkr", enriched.get("gross_profit_pkr", 0.0)))), 2),
        "gross_margin_percent": round(float(enriched.get("gross_margin_percent", profitability_summary.get("gross_margin_percent", 0.0))), 2),
        "roi_percent": round(float(enriched.get("roi_percent", profitability_summary.get("roi_percent", 0.0))), 2),
        "profitability_confidence": round(float(enriched.get("profitability_confidence", profitability_summary.get("profitability_confidence", 0.0))), 3),
        "retail_price_band": {
            "min": round(float(price_band.get("min", 0.0)), 2),
            "max": round(float(price_band.get("max", 0.0)), 2),
            "avg": round(float(price_band.get("avg", 0.0)), 2),
        },
        "platform_count": len(enriched.get("platform_distribution") or {}),
        "moq_range": enriched.get("moq_range") or {"min": 1, "max": 1},
        "market_intelligence": {
            "demand_score": round(float(market_intelligence.get("demand_score", 0.0)), 2),
            "competition_score": round(float(market_intelligence.get("competition_score", 0.0)), 2),
            "supplier_quality_score": round(float(market_intelligence.get("supplier_quality_score", 0.0)), 2),
            "market_saturation_score": round(float(market_intelligence.get("market_saturation_score", 0.0)), 2),
            "data_quality_score": round(float(market_intelligence.get("data_quality_score", 0.0)), 2),
            "risk_score": round(float(market_intelligence.get("risk_score", 0.0)), 2),
            "opportunity_score": round(float(market_intelligence.get("opportunity_score", 0.0)), 2),
        },
        "evidence_ledger": commercial_intelligence.get("evidence_ledger") or [],
    }


def build_competitor_summary(enriched: Dict[str, Any]) -> Dict[str, Any]:
    platforms = enriched.get("platform_distribution") or {}
    sorted_platforms = sorted(platforms.items(), key=lambda item: item[1], reverse=True)
    return {
        "competitor_count": int(enriched.get("competitor_count", 0)),
        "competitor_names": (enriched.get("competitor_names") or [])[:5],
        "top_platforms": [{"name": name, "count": count} for name, count in sorted_platforms[:3]],
        "review_themes": (enriched.get("review_themes") or [])[:3],
        "wholesale_origins": (enriched.get("wholesale_origins") or [])[:3],
    }


def build_marketing_system_prompt(strategy_context: Dict[str, Any], pakistan_context: str) -> str:
    profile = strategy_context["product_profile"]
    archetype = strategy_context["strategy_archetype"]
    return f"""You are a senior Pakistan e-commerce marketing strategist. Return one JSON object only.

{pakistan_context}

Working mode:
- Use the deterministic marketing intelligence bundle as the source of truth and synthesize the final narrative from it.
- Write a full, rich, LLM-generated go-to-market strategy in the original StrategAI style.
- Use the product profile, gross-profit snapshot, strategy archetype, category playbook, and marketing intelligence bundle to make the strategy specific.
- Keep the strategy grounded in the supplied analytics, observed market spread, competitor signals, and evidence-led marketing intelligence.
- Use the evidence to justify the strategy, but do not flatten the narrative into a terse summary.
- Do not assume platform commissions, shipping, taxes, or other operating costs.
- Prefer detailed, product-specific prose in SWOT, PESTEL, launch plan, KPI plan, and growth funnel sections.
- If the quality band is limited or guarded, keep launch scope narrow, KPI ambition modest, and channel breadth conservative.
- If the product is technical or trust-sensitive, emphasize demos, proof, warranty, COD reassurance, authenticity, or comparison language where relevant.
- If the product is commodity-like, emphasize value, convenience, bundle logic, and channel efficiency.
- If the product is premium, emphasize tone, aspiration, and selective channels.

Current routing:
- primary_archetype: {archetype['primary']}
- secondary_archetype: {archetype['secondary']}
- product_family: {profile['product_family']}
- buyer_trigger: {profile['buyer_trigger']}
- content_style_needed: {profile['content_style_needed']}
"""


def build_marketing_user_prompt(
    product_name: str,
    category: str,
    strategy_context: Dict[str, Any],
    sections: Optional[List[str]] = None,
    existing_strategy: Optional[Dict[str, Any]] = None,
    previous_strategy: Optional[Dict[str, Any]] = None,
) -> str:
    payload = {
        "product_name": product_name,
        "category": category,
        "analytics_summary": strategy_context["compact_analytics"],
        "product_profile": strategy_context["product_profile"],
        "strategy_archetype": strategy_context["strategy_archetype"],
        "competitor_summary": strategy_context["competitor_summary"],
        "commercial_intelligence": strategy_context.get("commercial_intelligence", {}),
        "marketing_intelligence": strategy_context.get("marketing_intelligence", {}),
        "category_playbook": strategy_context.get("category_playbook", {}),
        "marketing_decision_summary": strategy_context.get("marketing_decision_summary", {}),
        "framework_outputs": strategy_context.get("framework_outputs", {}),
        "evidence_ledger": strategy_context.get("evidence_ledger", []),
        "strategy_angle": strategy_context["strategy_angle"],
    }
    instructions = [
        "Generate a product-specific marketing strategy that follows the structured intelligence bundle.",
        "Use the supplied profile, category playbook, and intelligence bundle before generic category assumptions.",
        "Keep channel choices and messaging consistent with the buyer trigger, content style, and validation checks provided.",
        "Write in a richer, more detailed style rather than a short executive summary.",
        "Use evidence references for every major recommendation.",
        "Do not contradict the deterministic marketing decision summary or quality band.",
        "Return JSON only.",
    ]
    if sections:
        payload["sections_to_regenerate"] = sections
        payload["existing_strategy"] = existing_strategy or {}
        payload["previous_strategy"] = previous_strategy or {}
        instructions.extend([
            "Only regenerate the requested sections.",
            "Make the regenerated sections materially different from the previous strategy while staying realistic.",
            "Do not rewrite untouched sections.",
        ])

    return (
        "\n".join(instructions)
        + "\n\nINPUT:\n"
        + json.dumps(payload, ensure_ascii=True)
        + "\n\nSCHEMA:\n"
        + json.dumps(RESPONSE_SCHEMA if not sections else {key: RESPONSE_SCHEMA[key] for key in sections}, ensure_ascii=True)
    )




