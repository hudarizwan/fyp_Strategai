from __future__ import annotations

from typing import Any, Dict, List

from app.services.commercial_intelligence import QUALITY_BANDS, classify_quality_band


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


MARKETING_CATEGORY_PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    "mobile_phones": {
        "positioning": "authenticity-first flagship value",
        "primary_channels": ["daraz", "youtube", "instagram"],
        "secondary_channels": ["facebook", "whatsapp"],
        "buying_factors": ["warranty", "authenticity", "spec clarity", "resale confidence"],
        "promotion_hooks": ["comparison proof", "originality proof", "warranty reassurance"],
        "typical_margin_band": "12-28%",
        "seasonality": ["eid", "back-to-school", "11.11", "12.12"],
        "recommended_content": ["comparison reels", "authenticity explainers", "price-value carousels"],
        "risk_notes": ["counterfeit anxiety", "rapid price changes", "spec confusion"],
        "brand_voice": "clear, proof-led, and confident",
        "brand_personality": "trustworthy, informed, and premium-aware",
        "persona": "comparison-heavy smartphone buyers",
    },
    "audio": {
        "positioning": "comfort and performance-led audio",
        "primary_channels": ["daraz", "instagram", "tiktok"],
        "secondary_channels": ["youtube", "facebook"],
        "buying_factors": ["comfort", "sound quality", "microphone", "authenticity"],
        "promotion_hooks": ["demo clips", "feature comparisons", "use-case proof"],
        "typical_margin_band": "18-35%",
        "seasonality": ["eid", "back-to-school", "gaming peaks"],
        "recommended_content": ["demo-led reels", "comfort closeups", "comparison carousels"],
        "risk_notes": ["counterfeit concerns", "spec confusion", "comfort claims need proof"],
        "brand_voice": "assuring, detailed, and performance-led",
        "brand_personality": "credible, modern, and enthusiast-friendly",
        "persona": "gaming and entertainment buyers",
    },
    "cameras": {
        "positioning": "setup-simple security confidence",
        "primary_channels": ["daraz", "youtube", "facebook"],
        "secondary_channels": ["instagram", "whatsapp"],
        "buying_factors": ["setup ease", "visibility", "reliability", "after-sales support"],
        "promotion_hooks": ["setup walkthroughs", "scenario demos", "night-vision proof"],
        "typical_margin_band": "15-30%",
        "seasonality": ["eid", "house moves", "year-end"],
        "recommended_content": ["setup walkthroughs", "scenario reels", "trust explainers"],
        "risk_notes": ["setup friction", "privacy hesitation", "support expectations"],
        "brand_voice": "calm, reassuring, and practical",
        "brand_personality": "responsible, trustworthy, and professional",
        "persona": "security-conscious buyers",
    },
    "mobile_accessories": {
        "positioning": "compatibility and convenience",
        "primary_channels": ["daraz", "whatsapp", "facebook"],
        "secondary_channels": ["instagram", "tiktok"],
        "buying_factors": ["compatibility", "bundle value", "delivery convenience", "price"],
        "promotion_hooks": ["bundle creatives", "problem-solution reels", "utility demos"],
        "typical_margin_band": "20-40%",
        "seasonality": ["ramadan", "eid", "daily utility demand"],
        "recommended_content": ["bundle posts", "compatibility explainers", "quick utility demos"],
        "risk_notes": ["commodity pressure", "compatibility returns", "margin compression"],
        "brand_voice": "direct, practical, and value-aware",
        "brand_personality": "helpful, efficient, and reliable",
        "persona": "convenience buyers",
    },
    "computer_accessories": {
        "positioning": "productivity and compatibility proof",
        "primary_channels": ["daraz", "youtube", "instagram"],
        "secondary_channels": ["facebook", "whatsapp"],
        "buying_factors": ["compatibility", "reliability", "performance", "desk utility"],
        "promotion_hooks": ["desk demos", "compatibility proof", "speed comparisons"],
        "typical_margin_band": "18-38%",
        "seasonality": ["back-to-school", "office refresh", "exam season"],
        "recommended_content": ["compatibility explainers", "desk-use reels", "feature comparison posts"],
        "risk_notes": ["compatibility doubt", "spec overload", "returns on mismatch"],
        "brand_voice": "precise, practical, and expert-led",
        "brand_personality": "smart, dependable, and efficient",
        "persona": "utility-driven buyers",
    },
    "fashion": {
        "positioning": "style-led value with social proof",
        "primary_channels": ["instagram", "tiktok", "facebook"],
        "secondary_channels": ["daraz", "whatsapp"],
        "buying_factors": ["style", "fit", "social proof", "price"],
        "promotion_hooks": ["try-on clips", "UGC", "seasonal collections"],
        "typical_margin_band": "25-55%",
        "seasonality": ["eid", "wedding season", "summer/winter launches"],
        "recommended_content": ["lookbooks", "try-on videos", "seasonal styling posts"],
        "risk_notes": ["fit uncertainty", "trend changes", "return risk"],
        "brand_voice": "aspirational, modern, and social",
        "brand_personality": "trendy, confident, and expressive",
        "persona": "style-conscious shoppers",
    },
    "beauty": {
        "positioning": "routine improvement with trust and proof",
        "primary_channels": ["instagram", "tiktok", "youtube"],
        "secondary_channels": ["facebook", "whatsapp"],
        "buying_factors": ["results", "ingredients", "safety", "reviews"],
        "promotion_hooks": ["before-after proof", "routine content", "expert tips"],
        "typical_margin_band": "30-60%",
        "seasonality": ["ramadan", "eid", "self-care peaks"],
        "recommended_content": ["before-after reels", "routine guides", "review-led posts"],
        "risk_notes": ["trust sensitivity", "claim compliance", "ingredient concerns"],
        "brand_voice": "expert, reassuring, and aspirational",
        "brand_personality": "careful, polished, and helpful",
        "persona": "result-seeking self-care buyers",
    },
    "home_goods": {
        "positioning": "practical home improvement",
        "primary_channels": ["facebook", "daraz", "instagram"],
        "secondary_channels": ["whatsapp", "youtube"],
        "buying_factors": ["utility", "durability", "price", "ease of use"],
        "promotion_hooks": ["problem-solution demos", "before-after visuals", "household utility"],
        "typical_margin_band": "18-42%",
        "seasonality": ["ramadan", "eid", "moving season"],
        "recommended_content": ["use-case videos", "before-after carousels", "bundle explainers"],
        "risk_notes": ["practical objections", "delivery damage", "price sensitivity"],
        "brand_voice": "practical, clear, and trustworthy",
        "brand_personality": "useful, calm, and reliable",
        "persona": "household convenience buyers",
    },
    "generic_gadgets": {
        "positioning": "easy utility with a simple payoff",
        "primary_channels": ["daraz", "instagram", "tiktok"],
        "secondary_channels": ["facebook", "whatsapp"],
        "buying_factors": ["utility", "novelty", "price", "clarity"],
        "promotion_hooks": ["short demos", "problem-solution hooks", "simple explainer creatives"],
        "typical_margin_band": "20-45%",
        "seasonality": ["gifting peaks", "sale seasons"],
        "recommended_content": ["quick demos", "hook-led reels", "comparison posts"],
        "risk_notes": ["substitute pressure", "low familiarity", "short attention windows"],
        "brand_voice": "simple, clear, and immediate",
        "brand_personality": "friendly, smart, and accessible",
        "persona": "fast-deciding utility buyers",
    },
}


def _playbook_for_family(family: str) -> Dict[str, Any]:
    return MARKETING_CATEGORY_PLAYBOOKS.get(family, MARKETING_CATEGORY_PLAYBOOKS["generic_gadgets"])


def _label_from_score(score: float) -> str:
    if score >= 80:
        return "high"
    if score >= 55:
        return "medium"
    return "low"


def _band_from_quality(quality_band: str) -> str:
    if quality_band in {"limited", "guarded"}:
        return "cautious"
    if quality_band == "strong":
        return "expansive"
    return "balanced"


def _evidence_refs(*refs: str) -> List[str]:
    return list(dict.fromkeys([ref for ref in refs if ref]))


def _pick_channels(playbook: Dict[str, Any], platform_distribution: Dict[str, Any], quality_band: str, angle: str) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []
    for name, count in sorted(platform_distribution.items(), key=lambda item: item[1], reverse=True):
        ranked.append({
            "name": name,
            "priority": len(ranked) + 1,
            "rationale": f"Observed {count} listing(s) on {name} during scraping.",
            "evidence": _evidence_refs("platform_distribution", "competitor_summary"),
        })

    angle_channels = {
        "risk_averse": playbook["primary_channels"][:2],
        "value_focus": playbook["primary_channels"][:3],
        "premium_focus": playbook["primary_channels"][:2] + playbook["secondary_channels"][:1],
        "aggressive_growth": playbook["primary_channels"][:3],
        "market_penetration": playbook["primary_channels"][:3],
        "brand_building": playbook["primary_channels"][:3],
    }.get(angle, playbook["primary_channels"][:3])

    for channel in angle_channels:
        ranked.append({
            "name": channel,
            "priority": len(ranked) + 1,
            "rationale": f"Fits the playbook for {playbook['positioning']} and the current {quality_band} quality band.",
            "evidence": _evidence_refs("category_playbook", "quality_band", "strategy_angle"),
        })

    normalized: List[Dict[str, Any]] = []
    seen = set()
    max_channels = QUALITY_BANDS.get(quality_band, QUALITY_BANDS["balanced"])["max_channels"]
    for item in ranked:
        key = str(item.get("name", "")).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(item)
    return normalized[: int(max_channels)]


def _budget_tier(gross_profit: float, opportunity_score: float, quality_band: str, confidence: float) -> Dict[str, Any]:
    if quality_band in {"limited", "guarded"} or confidence < 0.5:
        tier = "lean"
        base_share = 0.10
    elif opportunity_score >= 75:
        tier = "growth"
        base_share = 0.22
    else:
        tier = "balanced"
        base_share = 0.16

    spend_pkr = max(1500.0, round(gross_profit * base_share, 2))
    if quality_band == "strong" and opportunity_score >= 75:
        spend_pkr = max(spend_pkr, round(gross_profit * 0.25, 2))

    return {
        "tier": tier,
        "monthly_budget_target_pkr": spend_pkr,
        "allocation": {
            "marketplace_ads": 35,
            "social_content": 25,
            "retargeting": 15,
            "creator_or_ugc": 15,
            "testing_reserve": 10,
        },
        "rationale": "Budget is scaled from the observed gross profit, the quality band, and the opportunity score rather than fabricated operating costs.",
    }


def _risk_level(opportunity_score: float, confidence: float, low_sample_warning: bool, competition_score: float) -> str:
    if low_sample_warning or confidence < 0.45 or competition_score >= 70:
        return "high"
    if opportunity_score >= 65:
        return "medium"
    return "low"


def _kpis(enriched: Dict[str, Any], quality_band: str, confidence: float, angle: str) -> List[Dict[str, Any]]:
    limits = QUALITY_BANDS.get(quality_band, QUALITY_BANDS["balanced"])
    base_views = max(200, int(round((confidence * 1600) * float(limits["views_multiplier"]))))
    base_orders = max(3, int(round((confidence * 14) * float(limits["orders_multiplier"]))))
    if angle in {"aggressive_growth", "market_penetration"} and quality_band == "strong":
        base_orders += 3
    if angle == "risk_averse":
        base_orders = max(3, base_orders - 1)
    conversion = round(max(1.0, min(6.0, confidence * 4.0)), 1)
    revenue = int(round(base_orders * _safe_float(enriched.get("sell_price_pkr", 0.0))))
    return [
        {"metric": "Qualified listing views", "target": base_views, "period": "Week 1", "evidence": ["confidence_score", "quality_band"]},
        {"metric": "Orders", "target": base_orders, "period": "Month 1", "evidence": ["confidence_score", "margin_percent"]},
        {"metric": "Conversion rate %", "target": conversion, "period": "Week 2", "evidence": ["channel_recommendation", "content_planning"]},
        {"metric": "Gross revenue (PKR)", "target": revenue, "period": "Month 1", "evidence": ["sell_price_pkr", "orders"]},
    ][: int(limits["max_kpis"])]


def _validation_checks(bundle: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[str] = []
    checks: List[str] = []
    channel_count = len(bundle["channel_recommendation"]["channels"])
    max_channels = bundle["channel_recommendation"]["max_channels"]
    if channel_count <= max_channels:
        checks.append("channel_limit:ok")
    else:
        issues.append("channel_limit:exceeded")

    allocation = bundle["budget_recommendation"]["allocation"]
    if sum(allocation.values()) == 100:
        checks.append("budget_allocation:ok")
    else:
        issues.append("budget_allocation:invalid")

    if bundle["pricing_communication"]["recommendation_alignment"] in {"aligned", "strictly_aligned"}:
        checks.append("pricing_alignment:ok")
    else:
        issues.append("pricing_alignment:weak")

    evidence_coverage = bundle["marketing_decision_summary"]["decision_score_breakdown"].get("evidence_coverage", 0)
    if evidence_coverage >= 0.6:
        checks.append("evidence_coverage:ok")
    else:
        issues.append("evidence_coverage:thin")

    status = "ok" if not issues else "needs_review" if len(issues) <= 2 else "invalid"
    return {"status": status, "checks": checks, "issues": issues}


def build_marketing_intelligence_bundle(enriched: Dict[str, Any], strategy_context: Dict[str, Any]) -> Dict[str, Any]:
    commercial = enriched.get("commercial_intelligence") or {}
    market = commercial.get("market_intelligence") or enriched.get("market_intelligence") or {}
    profitability = commercial.get("profitability_summary") or enriched.get("profitability_summary") or {}
    product_profile = strategy_context["product_profile"]
    category_profile = strategy_context["category_profile"]
    quality_band = str(strategy_context.get("quality_band") or commercial.get("quality_band") or "balanced")
    confidence = _safe_float(enriched.get("confidence_score", 0.0))
    low_sample_warning = bool(enriched.get("low_sample_warning", False))
    opportunity_score = _safe_float(market.get("opportunity_score", 0.0))
    competition_score = _safe_float(market.get("competition_score", 0.0))
    supplier_quality_score = _safe_float(market.get("supplier_quality_score", 0.0))
    market_saturation_score = _safe_float(market.get("market_saturation_score", 0.0))
    data_quality_score = _safe_float(market.get("data_quality_score", 0.0))
    risk_score = _safe_float(market.get("risk_score", 0.0))
    family = str(category_profile.get("family", "generic_gadgets"))
    playbook = _playbook_for_family(family)
    angle = str(strategy_context.get("strategy_angle", "value_focus"))
    platform_distribution = enriched.get("platform_distribution") or {}
    price_band = enriched.get("price_band") or {}
    gross_profit = _safe_float(enriched.get("gross_profit_pkr", profitability.get("gross_profit_pkr", 0.0)))
    gross_margin = _safe_float(enriched.get("gross_margin_percent", profitability.get("gross_margin_percent", 0.0)))
    seller_count = _safe_int(enriched.get("seller_count", 0))
    vendor_count = _safe_int(enriched.get("vendor_count", 0))

    customer_intelligence = {
        "persona": playbook["persona"],
        "purchase_motivation": product_profile["buyer_motivation"],
        "pain_points": playbook["buying_factors"],
        "trust_barriers": playbook["risk_notes"][:3],
        "journey_stage": "comparison" if product_profile["comparison_intensity"] == "high" else "evaluation",
        "preferred_message": playbook["positioning"],
        "brand_voice": playbook["brand_voice"],
        "brand_personality": playbook["brand_personality"],
    }

    market_intelligence = {
        "opportunity_score": round(opportunity_score, 2),
        "competition_score": round(competition_score, 2),
        "supplier_quality_score": round(supplier_quality_score, 2),
        "market_saturation_score": round(market_saturation_score, 2),
        "data_quality_score": round(data_quality_score, 2),
        "risk_score": round(risk_score, 2),
        "confidence_band": classify_quality_band(
            confidence_score=confidence,
            low_sample_warning=low_sample_warning,
            wholesale_vendor_count=vendor_count,
            retail_listing_count=seller_count,
            margin_percent=gross_margin,
        ),
        "market_state": _label_from_score(opportunity_score),
        "competition_state": _label_from_score(competition_score),
        "supplier_state": _label_from_score(supplier_quality_score),
        "pricing_state": _label_from_score(gross_margin),
        "stability_state": _label_from_score(100.0 - market_saturation_score),
    }

    competitor_intelligence = {
        "key_competitors": (strategy_context.get("competitor_summary") or {}).get("competitor_names", [])[:5],
        "top_platforms": (strategy_context.get("competitor_summary") or {}).get("top_platforms", [])[:3],
        "five_forces": {
            "supplier_power": "high" if vendor_count <= 1 else "medium" if vendor_count <= 3 else "low",
            "buyer_power": "high" if competition_score >= 60 else "medium",
            "competitive_rivalry": "high" if competition_score >= 65 else "medium" if competition_score >= 35 else "low",
            "threat_of_substitutes": "high" if product_profile["product_family"] in {"generic_gadgets", "mobile_accessories"} else "medium",
            "threat_of_new_entrants": "medium" if seller_count >= 4 else "low",
        },
        "price_band": {
            "min": round(_safe_float(price_band.get("min", 0.0)), 2),
            "max": round(_safe_float(price_band.get("max", 0.0)), 2),
            "avg": round(_safe_float(price_band.get("avg", 0.0)), 2),
            "currency": "PKR",
        },
    }

    channel_channels = _pick_channels(playbook, platform_distribution, quality_band, angle)
    channel_recommendation = {
        "channels": channel_channels,
        "max_channels": int(QUALITY_BANDS.get(quality_band, QUALITY_BANDS["balanced"])["max_channels"]),
        "primary_channel": channel_channels[0]["name"] if channel_channels else "daraz",
        "channel_mix": {
            "marketplace": 40 if "daraz" in {c["name"] for c in channel_channels} else 30,
            "social": 35 if any(name in {c["name"] for c in channel_channels} for name in ("instagram", "tiktok")) else 25,
            "retargeting": 15 if quality_band in {"balanced", "strong"} else 10,
            "content": 10,
        },
    }
    channel_recommendation["channel_mix"]["content"] = 100 - (
        channel_recommendation["channel_mix"]["marketplace"]
        + channel_recommendation["channel_mix"]["social"]
        + channel_recommendation["channel_mix"]["retargeting"]
    )

    budget_recommendation = _budget_tier(gross_profit=gross_profit, opportunity_score=opportunity_score, quality_band=quality_band, confidence=confidence)

    positioning_statement = (
        f"Position {enriched.get('product_name', 'the product')} as {playbook['positioning']} "
        f"for {customer_intelligence['persona']}."
    )
    brand_positioning = {
        "value_proposition": f"Clearer proof, cleaner positioning, and a better reason to choose this offer around PKR {float(enriched.get('sell_price_pkr', 0.0)):,.0f}.",
        "unique_selling_proposition": f"Anchor the offer around {playbook['promotion_hooks'][0]}.",
        "positioning_statement": positioning_statement,
        "brand_voice": playbook["brand_voice"],
        "brand_personality": playbook["brand_personality"],
        "messaging_pillars": playbook["buying_factors"][:4],
    }

    pricing_communication = {
        "recommended_buy_price_pkr": round(_safe_float(enriched.get("buy_price_pkr", 0.0)), 2),
        "recommended_sell_price_pkr": round(_safe_float(enriched.get("sell_price_pkr", 0.0)), 2),
        "observed_market_band": {
            "min": round(_safe_float(price_band.get("min", 0.0)), 2),
            "max": round(_safe_float(price_band.get("max", 0.0)), 2),
        },
        "message": f"Lead with evidence that the current sell price of PKR {float(enriched.get('sell_price_pkr', 0.0)):,.0f} is still inside the observed market band.",
        "recommendation_alignment": "strictly_aligned" if gross_margin > 0 else "aligned",
    }

    content_planning = {
        "content_pillars": [
            f"{playbook['positioning']}",
            "proof and comparison",
            "trust and reassurance",
            "offer clarity and CTA",
        ],
        "recommended_frequency": QUALITY_BANDS.get(quality_band, QUALITY_BANDS["balanced"])["content_frequency"],
        "best_platforms": [item["name"] for item in channel_channels[:3]],
        "creative_direction": playbook["recommended_content"],
        "cta_recommendations": [
            "Buy now",
            "Compare price and proof",
            "Check warranty and delivery details",
        ],
        "hashtags": ["#StrategAI", "#EcommercePakistan", "#Daraz", "#PakistanBusiness"],
        "video_ideas": [
            f"Show why {enriched.get('product_name', 'the product')} solves a real problem.",
            "Create a quick comparison reel against the market norm.",
            "Demonstrate the trust signal that removes hesitation.",
        ],
        "copy_themes": [
            "benefit-first headline",
            "proof-led subheadline",
            "trust badge or guarantee",
        ],
        "email_sequence_ideas": [
            "Introduce the product and the main problem it solves.",
            "Show proof, comparison, and trust signals.",
            "Close with urgency, offer clarity, and a simple CTA.",
        ],
    }

    risk_level = _risk_level(opportunity_score, confidence, low_sample_warning, competition_score)
    risk_assessment = {
        "risk_level": risk_level,
        "risks": [
            {
                "risk": "Competition may compress price quickly.",
                "mitigation": "Use proof-led creatives and track the first performance window closely.",
                "evidence": _evidence_refs("competition_score", "market_saturation_score"),
            },
            {
                "risk": "Confidence is constrained by sample size or signal quality.",
                "mitigation": "Keep launch scope narrow and avoid overcommitting spend early.",
                "evidence": _evidence_refs("confidence_band", "low_sample_warning", "data_quality_score"),
            },
        ],
    }

    kpi_recommendation = {
        "kpis": _kpis(enriched, quality_band, confidence, angle),
        "primary_success_metric": "Orders",
        "secondary_success_metric": "Qualified listing views",
        "confidence_alignment": _label_from_score(confidence * 100.0),
    }

    campaign_roadmap = {
        "phases": [
            {"name": "Launch setup", "focus": "proof and listing clarity"},
            {"name": "Signal capture", "focus": "track early response"},
            {"name": "Scale decision", "focus": "widen only if signal is healthy"},
        ]
    }

    framework_outputs = {
        "stp": {
            "segmentation": {
                "demographics": f"{customer_intelligence['persona']} in Pakistan looking for {playbook['positioning']}.",
                "psychographics": f"Buyers are driven by {', '.join(playbook['buying_factors'][:3])}.",
            },
            "targeting": {"primary_segment": customer_intelligence["persona"]},
            "positioning": {"statement": positioning_statement},
        },
        "swot": {
            "strengths": [
                f"Observed gross profit is around PKR {gross_profit:,.0f}.",
                f"The product can be framed around {playbook['promotion_hooks'][0]}.",
            ],
            "weaknesses": [
                f"Confidence is only {confidence:.2f}, so the first launch should stay measured.",
                "The market still needs proof-led messaging to reduce hesitation.",
            ],
            "opportunities": [
                f"Opportunity score sits at {opportunity_score:.1f}/100.",
                "There is room to win attention with clearer comparison and trust content.",
            ],
            "threats": [
                "Price compression can happen fast if the category is crowded.",
                playbook["risk_notes"][0],
            ],
        },
        "pestel": {
            "political": "Cross-border sourcing can be affected by duties or import changes.",
            "economic": "Price-sensitive buyers require a clearly justified offer.",
            "social": f"{playbook['persona'].title()} respond to proof and trust cues.",
            "technological": "Short-form content and marketplace UX shape discovery.",
            "environmental": "Packaging should survive courier handling without unnecessary waste.",
            "legal": "Claims must stay aligned with product reality and warranty terms.",
        },
        "four_ps": {
            "product": playbook["positioning"],
            "price": f"Communicate value around PKR {float(enriched.get('sell_price_pkr', 0.0)):,.0f}.",
            "place": channel_recommendation["primary_channel"],
            "promotion": playbook["promotion_hooks"][:3],
        },
        "aarrr": {
            "acquisition": "Marketplace listings and social discovery.",
            "activation": "Quick proof and trust cues on the landing view.",
            "retention": "Review capture and follow-up offers.",
            "revenue": "Clear pricing and low-friction conversion.",
            "referral": "UGC and simple shareable proof assets.",
        },
        "race": {
            "reach": channel_recommendation["primary_channel"],
            "act": "Show proof before asking for commitment.",
            "convert": "Use trust cues and price clarity.",
            "engage": "Retarget with comparison and review-led content.",
        },
        "marketing_funnel": {
            "top": "Awareness through short proof-led content",
            "middle": "Comparison and reassurance",
            "bottom": "Offer clarity and conversion CTA",
        },
        "buyer_persona": {
            "name": customer_intelligence["persona"],
            "triggers": playbook["buying_factors"][:4],
            "barriers": playbook["risk_notes"][:3],
        },
        "customer_journey": {
            "awareness": "Sees a proof-led hook.",
            "consideration": "Compares price and trust evidence.",
            "decision": "Confirms the offer is safe and practical.",
            "post_purchase": "Receives support and review request.",
        },
        "value_proposition": brand_positioning["value_proposition"],
        "usp": brand_positioning["unique_selling_proposition"],
        "go_to_market_strategy": {
            "summary": f"Launch with {channel_recommendation['primary_channel']} as the anchor channel and keep scope {QUALITY_BANDS.get(quality_band, QUALITY_BANDS['balanced'])['launch_scope']}.",
        },
        "digital_marketing_plan": {
            "channel_mix": channel_recommendation["channel_mix"],
            "content": content_planning["content_pillars"],
            "budget": budget_recommendation["monthly_budget_target_pkr"],
        },
        "channel_mix": channel_recommendation,
        "campaign_roadmap": {
            "phases": [
                {"name": "Launch setup", "focus": "proof and listing clarity"},
                {"name": "Signal capture", "focus": "track early response"},
                {"name": "Scale decision", "focus": "widen only if signal is healthy"},
            ],
        },
        "budget_allocation": budget_recommendation,
        "success_metrics": {
            "views": kpi_recommendation["kpis"][0]["target"],
            "orders": kpi_recommendation["kpis"][1]["target"],
            "revenue": kpi_recommendation["kpis"][3]["target"] if len(kpi_recommendation["kpis"]) > 3 else 0,
        },
        "risk_mitigation": risk_assessment,
        "launch_strategy": {
            "scope": QUALITY_BANDS.get(quality_band, QUALITY_BANDS["balanced"])["launch_scope"],
            "primary_channel": channel_recommendation["primary_channel"],
        },
        "growth_strategy": {
            "next_stage": "widen channels only after the first proof window",
        },
        "customer_retention_strategy": {
            "plan": "capture reviews, answer objections fast, and follow up with useful content.",
        },
        "upselling_strategy": {
            "plan": "use bundles and complementary items rather than aggressive discounting.",
        },
        "cross_selling_strategy": {
            "plan": "offer accessories or companion products that solve the next adjacent problem.",
        },
    }

    decision_score_breakdown = {
        "profitability": round(max(gross_margin, 0.0) * 0.30, 2),
        "market_opportunity": round(opportunity_score * 0.25, 2),
        "supplier_quality": round(supplier_quality_score * 0.15, 2),
        "marketing_readiness": round(data_quality_score * 0.15, 2),
        "confidence": round(confidence * 100.0 * 0.15, 2),
        "evidence_coverage": round(min(1.0, len(enriched.get("evidence_ledger") or []) / 5.0), 2),
    }
    decision_score_breakdown["total"] = round(sum(decision_score_breakdown.values()), 2)

    approval_readiness = "READY" if decision_score_breakdown["total"] >= 75 and risk_level != "high" else "CAUTION" if decision_score_breakdown["total"] >= 60 else "REVIEW" if decision_score_breakdown["total"] >= 45 else "DO_NOT_LAUNCH"

    decision_summary = {
        "overall_recommendation": "Launch" if approval_readiness in {"READY", "CAUTION"} else "Hold",
        "overall_score": decision_score_breakdown["total"],
        "executive_summary": f"{playbook['positioning']} with {channel_recommendation['primary_channel']} as the anchor channel, backed by an observed gross margin of {gross_margin:.1f}% and opportunity score of {opportunity_score:.1f}/100.",
        "top_strengths": [
            f"Gross profit around PKR {gross_profit:,.0f}.",
            f"Supplier quality score at {supplier_quality_score:.1f}/100.",
            f"Marketing confidence aligned to the {quality_band} quality band.",
        ],
        "major_risks": [
            f"Competition score at {competition_score:.1f}/100.",
            "Launch scope should stay evidence-led until the market response is clearer.",
        ],
        "recommended_next_action": "Start with a narrow launch and widen only after proof signals improve.",
        "decision_score_breakdown": decision_score_breakdown,
        "threshold_context": {
            "quality_band": quality_band,
            "confidence_band": market_intelligence["confidence_band"],
            "low_sample_warning": low_sample_warning,
            "supplier_threshold": 3,
            "retail_threshold": 5,
        },
        "approval_readiness": approval_readiness,
    }

    bundle = {
        "category_playbook": playbook,
        "customer_intelligence": customer_intelligence,
        "market_intelligence": market_intelligence,
        "competitor_intelligence": competitor_intelligence,
        "brand_positioning": brand_positioning,
        "channel_recommendation": channel_recommendation,
        "campaign_planning": {
            "launch_scope": QUALITY_BANDS.get(quality_band, QUALITY_BANDS["balanced"])["launch_scope"],
            "roadmap": campaign_roadmap["phases"],
            "primary_theme": playbook["promotion_hooks"][0],
        },
        "budget_recommendation": budget_recommendation,
        "pricing_communication": pricing_communication,
        "risk_assessment": risk_assessment,
        "content_planning": content_planning,
        "kpi_recommendation": kpi_recommendation,
        "framework_outputs": framework_outputs,
        "marketing_validation": _validation_checks({
            "channel_recommendation": channel_recommendation,
            "budget_recommendation": budget_recommendation,
            "pricing_communication": pricing_communication,
            "marketing_decision_summary": {"decision_score_breakdown": {"evidence_coverage": min(1.0, len(enriched.get("evidence_ledger") or []) / 5.0)}},
        }),
        "marketing_decision_summary": decision_summary,
    }
    bundle["marketing_validation"]["evidence_coverage_score"] = min(1.0, len(enriched.get("evidence_ledger") or []) / 5.0)
    return bundle


