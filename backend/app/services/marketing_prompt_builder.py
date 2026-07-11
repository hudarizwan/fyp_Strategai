from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

CATEGORY_PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    "gaming_headsets": {
        "category_label": "Gaming Headsets",
        "positioning": "Mid-range Premium",
        "primary_channels": ["Daraz", "TikTok", "Instagram"],
        "channel_roles": {
            "Daraz": "conversion",
            "TikTok": "discovery",
            "Instagram": "social proof",
        },
        "audience_profile": {
            "core_need": "Comfortable gaming audio with visible quality cues",
            "purchase_motivation": "Performance, warranty, and creator-led trust",
            "price_sensitivity": "medium",
        },
        "buying_factors": ["Comfort", "Warranty", "Sound quality", "Microphone clarity", "RGB styling"],
        "promotion_hooks": ["Bundles", "Flash sales", "Warranty proof", "Short-form demos"],
        "content_formats": ["video demo", "comparison post", "unboxing clip"],
        "seasonality": ["Back-to-school", "Holiday gifting", "Tournament season"],
        "trust_signals": ["Official warranty", "Seller ratings", "Return policy"],
        "typical_margin_band": {"min": 30, "max": 45},
        "risk_notes": ["Competition increases during promotions", "Feature claims need proof"],
        "merchandising_notes": ["Show microphone clarity and comfort", "Bundle with accessories when margin allows"],
        "tone": "confident",
    },
    "computer_accessories": {
        "category_label": "Computer Accessories",
        "positioning": "Reliable Value",
        "primary_channels": ["Daraz", "Facebook", "WhatsApp"],
        "channel_roles": {
            "Daraz": "conversion",
            "Facebook": "education",
            "WhatsApp": "assisted selling",
        },
        "audience_profile": {
            "core_need": "Compatibility and durability at a fair price",
            "purchase_motivation": "Practical utility and low replacement risk",
            "price_sensitivity": "high",
        },
        "buying_factors": ["Durability", "Compatibility", "Warranty", "Delivery speed"],
        "promotion_hooks": ["Bundles", "Fast delivery", "Warranty proof", "Compatibility guides"],
        "content_formats": ["comparison post", "setup guide", "carousel"],
        "seasonality": ["Back-to-school", "Work-from-home refresh"],
        "trust_signals": ["Compatibility list", "Warranty coverage", "Seller ratings"],
        "typical_margin_band": {"min": 20, "max": 35},
        "risk_notes": ["Many substitutes compete on price", "Returns rise when compatibility is unclear"],
        "merchandising_notes": ["Highlight model compatibility", "Use bundles to increase basket size"],
        "tone": "practical",
    },
    "mobile_phones": {
        "category_label": "Mobile Phones",
        "positioning": "Trust-led Value",
        "primary_channels": ["Daraz", "Instagram", "YouTube"],
        "channel_roles": {
            "Daraz": "conversion",
            "Instagram": "trust building",
            "YouTube": "education",
        },
        "audience_profile": {
            "core_need": "Reliable phone purchase with warranty confidence",
            "purchase_motivation": "Authenticity, battery life, and resale value",
            "price_sensitivity": "medium",
        },
        "buying_factors": ["Warranty", "Battery", "Brand trust", "Storage", "Camera quality"],
        "promotion_hooks": ["Warranty", "Launch offers", "Authenticity", "Trade-in messaging"],
        "content_formats": ["spec comparison", "review summary", "explainer video"],
        "seasonality": ["Ramadan shopping", "Eid gifting", "New model launches"],
        "trust_signals": ["IMEI check", "Official warranty", "Return policy"],
        "typical_margin_band": {"min": 15, "max": 28},
        "risk_notes": ["Authenticity concerns can slow conversion", "High competition from established sellers"],
        "merchandising_notes": ["Surface warranty and authenticity early", "Keep pricing within known market bands"],
        "tone": "reassuring",
    },
    "mobile_accessories": {
        "category_label": "Mobile Accessories",
        "positioning": "Impulse Value",
        "primary_channels": ["Daraz", "TikTok", "Instagram"],
        "channel_roles": {
            "Daraz": "conversion",
            "TikTok": "discovery",
            "Instagram": "impulse capture",
        },
        "audience_profile": {
            "core_need": "Fast, affordable add-ons that fit existing devices",
            "purchase_motivation": "Convenience, price, and immediate utility",
            "price_sensitivity": "high",
        },
        "buying_factors": ["Price", "Compatibility", "Convenience", "Durability"],
        "promotion_hooks": ["Bundles", "Flash sales", "Limited-time offers", "Cross-sells"],
        "content_formats": ["short video", "bundle post", "story ad"],
        "seasonality": ["Holiday gifting", "Back-to-school"],
        "trust_signals": ["Compatibility notes", "Seller ratings", "Delivery estimate"],
        "typical_margin_band": {"min": 18, "max": 32},
        "risk_notes": ["Impulse demand can be noisy", "Low prices can compress margin quickly"],
        "merchandising_notes": ["Bundle complementary accessories", "Keep add-to-cart friction low"],
        "tone": "energetic",
    },
    "laptops": {
        "category_label": "Laptops",
        "positioning": "Performance Value",
        "primary_channels": ["Daraz", "Facebook", "YouTube"],
        "channel_roles": {
            "Daraz": "conversion",
            "Facebook": "consideration",
            "YouTube": "proof and comparison",
        },
        "audience_profile": {
            "core_need": "Performance and longevity for work or study",
            "purchase_motivation": "Specs, warranty, and long-term utility",
            "price_sensitivity": "medium",
        },
        "buying_factors": ["Specs", "Warranty", "Performance", "Battery life", "Upgradeability"],
        "promotion_hooks": ["Warranty proof", "Comparison content", "Value bundles", "Use-case demos"],
        "content_formats": ["comparison video", "spec sheet", "buyer guide"],
        "seasonality": ["Back-to-school", "Corporate procurement", "Year-end promotions"],
        "trust_signals": ["Warranty length", "Service support", "Specification transparency"],
        "typical_margin_band": {"min": 12, "max": 24},
        "risk_notes": ["High ticket price raises scrutiny", "Specification mismatch can trigger returns"],
        "merchandising_notes": ["Use plain-language spec comparisons", "Make warranty and support explicit"],
        "tone": "authoritative",
    },
    "general_retail": {
        "category_label": "General Retail",
        "positioning": "Value-for-Money",
        "primary_channels": ["Daraz", "Facebook"],
        "channel_roles": {
            "Daraz": "conversion",
            "Facebook": "reach",
        },
        "audience_profile": {
            "core_need": "A sensible purchase that feels trustworthy",
            "purchase_motivation": "Price, availability, and reliability",
            "price_sensitivity": "high",
        },
        "buying_factors": ["Price", "Availability", "Trust", "Delivery speed"],
        "promotion_hooks": ["Bundles", "Flash sales", "Trust signals", "Limited-time offers"],
        "content_formats": ["carousel", "simple listing", "value post"],
        "seasonality": ["Eid shopping", "Holiday gifting"],
        "trust_signals": ["Seller ratings", "Return policy", "Stock availability"],
        "typical_margin_band": {"min": 20, "max": 40},
        "risk_notes": ["Broad category fit can hide weak differentiation", "Trust signals matter across most products"],
        "merchandising_notes": ["Keep the offer easy to understand", "Lead with trust and availability"],
        "tone": "practical",
    },
}

MARKETING_STATE_THRESHOLDS = {
    "high": 0.67,
    "medium": 0.34,
}


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _score_to_band(value: float, *, reverse: bool = False) -> str:
    score = max(0.0, min(_safe_float(value), 100.0))
    if reverse:
        score = 100.0 - score
    if score >= 67.0:
        return "HIGH"
    if score >= 34.0:
        return "MEDIUM"
    return "LOW"


def _category_key(category: str) -> str:
    normalized = (category or "").strip().lower()
    if any(token in normalized for token in ("headset", "headphones", "earbud", "earbuds", "gaming")):
        return "gaming_headsets"
    if any(token in normalized for token in ("computer", "keyboard", "mouse", "accessory", "accessories")):
        if any(token in normalized for token in ("mobile", "phone")):
            return "mobile_accessories"
        return "computer_accessories"
    if any(token in normalized for token in ("mobile", "phone", "smartphone", "iphone", "android")):
        return "mobile_phones"
    if any(token in normalized for token in ("laptop", "notebook", "macbook")):
        return "laptops"
    return "general_retail"


def _playbook_for_category(category: str) -> Dict[str, Any]:
    key = _category_key(category)
    playbook = deepcopy(CATEGORY_PLAYBOOKS.get(key, CATEGORY_PLAYBOOKS["general_retail"]))
    playbook["category_key"] = key
    return playbook


def _confidence_label(value: Any) -> str:
    band = str(value or "LOW").strip().upper()
    if band == "HIGH":
        return "High"
    if band == "MEDIUM":
        return "Medium"
    return "Low"


def _card_confidence_from_business_state(business_state: Dict[str, Any]) -> str:
    market_state = business_state.get("market_state") or {}
    return _confidence_label(market_state.get("confidence"))


def _build_recommendation_card(
    *,
    card_type: str,
    recommendation: str,
    reason: str,
    evidence_refs: List[str],
    confidence: str,
) -> Dict[str, Any]:
    return {
        "type": card_type,
        "recommendation": recommendation,
        "confidence": confidence,
        "reason": reason,
        "evidence_refs": evidence_refs,
    }


def _index_refs(base: str, count: int) -> List[str]:
    return [f"{base}[{index}]" for index in range(count)]


def build_recommendation_cards(
    strategy: Dict[str, Any],
    business_state: Dict[str, Any],
) -> List[Dict[str, Any]]:
    market_state = business_state.get("market_state") or {}
    playbook = business_state.get("category_playbook") or {}
    decision_summary = strategy.get("marketing_decision_summary") or {}

    confidence = _card_confidence_from_business_state(business_state)
    cards: List[Dict[str, Any]] = []

    selected_positioning = str(decision_summary.get("selected_positioning") or "").strip()
    stp_positioning = str(strategy.get("stp", {}).get("positioning", {}).get("statement") or "").strip()
    playbook_positioning = str(playbook.get("positioning", "Value-for-Money") or "").strip()
    if selected_positioning:
        positioning = selected_positioning
        positioning_refs = ["marketing_decision_summary.selected_positioning", "market_state.pricing_strategy"]
    elif stp_positioning:
        positioning = stp_positioning
        positioning_refs = ["stp.positioning.statement", "market_state.pricing_strategy"]
    else:
        positioning = playbook_positioning
        positioning_refs = ["category_playbook.positioning", "market_state.pricing_strategy"]
    cards.append(
        _build_recommendation_card(
            card_type="positioning",
            recommendation=positioning,
            reason="Keep the offer aligned with the selected pricing posture and category playbook.",
            evidence_refs=positioning_refs,
            confidence=confidence,
        )
    )

    summary_channels = [
        str(channel).strip()
        for channel in (decision_summary.get("recommended_channels") or [])
        if str(channel).strip()
    ]
    strategy_channels = [
        str(item.get("name") or "").strip()
        for item in (strategy.get("channels") or [])
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]
    playbook_channels = [
        str(channel).strip()
        for channel in (playbook.get("primary_channels") or [])
        if str(channel).strip()
    ]
    if summary_channels:
        channel_names = summary_channels[:3]
        channel_refs = _index_refs("marketing_decision_summary.recommended_channels", len(channel_names))
    elif strategy_channels:
        channel_names = strategy_channels[:3]
        channel_refs = [f"channels[{index}].name" for index in range(len(channel_names))]
    else:
        channel_names = playbook_channels[:3]
        channel_refs = _index_refs("category_playbook.primary_channels", len(channel_names))
    cards.append(
        _build_recommendation_card(
            card_type="channels",
            recommendation=", ".join(channel_names),
            reason="Prioritize channels that already appear in the strategy and category playbook.",
            evidence_refs=channel_refs,
            confidence=confidence,
        )
    )

    hooks = [
        str(hook).strip()
        for hook in (playbook.get("promotion_hooks") or [])
        if str(hook).strip()
    ]
    buying_factors = [
        str(factor).strip()
        for factor in (playbook.get("buying_factors") or [])
        if str(factor).strip()
    ]
    if hooks:
        offer_focus = hooks[0]
        offer_refs = ["category_playbook.promotion_hooks[0]"]
        if buying_factors:
            offer_focus = f"{offer_focus} tied to {buying_factors[0]}"
            offer_refs.append("category_playbook.buying_factors[0]")
    else:
        offer_focus = str(playbook.get("tone", "Value") or "").strip()
        offer_refs = ["category_playbook.tone"]
    cards.append(
        _build_recommendation_card(
            card_type="offer",
            recommendation=offer_focus,
            reason="Use a proof-led offer that matches the main buyer concern in this category.",
            evidence_refs=offer_refs,
            confidence=confidence,
        )
    )

    risk_notes = [
        str(note).strip()
        for note in (playbook.get("risk_notes") or [])
        if str(note).strip()
    ]
    if risk_notes:
        risk_focus = risk_notes[0]
        risk_refs = ["category_playbook.risk_notes[0]"]
    else:
        market_risk = str(market_state.get("risk") or "").strip()
        if market_risk:
            risk_focus = f"Manage for {market_risk.lower()} risk."
            risk_refs = ["market_state.risk"]
        else:
            risk_focus = "Maintain conservative launch scope."
            risk_refs = ["signals.confidence_band"]
    cards.append(
        _build_recommendation_card(
            card_type="risk",
            recommendation=risk_focus,
            reason="Keep the launch plan aligned with the category's main friction point.",
            evidence_refs=risk_refs,
            confidence=confidence,
        )
    )

    return cards

def build_business_state(
    perceived: Dict[str, Any],
    analytics_result: Dict[str, Any],
    enriched: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    enriched = enriched or {}
    market_intelligence = analytics_result.get("market_intelligence") or {}
    pricing_summary = analytics_result.get("pricing_decision_summary") or {}

    primary_mode = str(
        analytics_result.get("primary_pricing_mode")
        or pricing_summary.get("selected_mode")
        or perceived.get("pricing_mode")
        or "balanced"
    ).strip().upper()
    if primary_mode not in {"COMPETITIVE", "BALANCED", "PREMIUM"}:
        primary_mode = "BALANCED"

    confidence_score = _safe_float(perceived.get("confidence_score", analytics_result.get("confidence_score", 0.0)))
    margin_percent = _safe_float(perceived.get("margin_percent", analytics_result.get("expected_profit_margin", 0.0)))
    seller_count = int(perceived.get("seller_count", analytics_result.get("retail_sellers_count", 0)) or 0)
    vendor_count = int(perceived.get("vendor_count", analytics_result.get("wholesale_vendors_count", 0)) or 0)
    price_spread = _safe_float(perceived.get("price_spread", 0.0))
    price_level = "HIGH" if margin_percent >= 35 else "MEDIUM" if margin_percent >= 18 else "LOW"

    competition_score = _safe_float(market_intelligence.get("competition_score"))
    if competition_score <= 0:
        competition_score = min(100.0, seller_count * 7.5 + price_spread * 0.12)

    demand_score = _safe_float(market_intelligence.get("demand_score"))
    if demand_score <= 0:
        demand_score = min(100.0, seller_count * 7.0 + confidence_score * 18.0 + max(margin_percent, 0.0) * 0.6)

    supplier_quality_score = _safe_float(market_intelligence.get("supplier_quality_score"))
    if supplier_quality_score <= 0:
        supplier_quality_score = min(100.0, vendor_count * 10.0 + confidence_score * 15.0)

    profitability_score = _safe_float(market_intelligence.get("profitability_score"))
    if profitability_score <= 0:
        profitability_score = min(100.0, max(margin_percent, 0.0) * 1.8 + confidence_score * 20.0)

    opportunity_score = _safe_float(market_intelligence.get("opportunity_score"))
    if opportunity_score <= 0:
        opportunity_score = min(100.0, (demand_score * 0.45) + (profitability_score * 0.35) - (competition_score * 0.2))

    risk_score = _safe_float(market_intelligence.get("risk_score"))
    if risk_score <= 0:
        risk_score = min(100.0, (100.0 - confidence_score * 100.0) * 0.35 + (100.0 - profitability_score) * 0.35 + competition_score * 0.15)

    category_playbook = _playbook_for_category(perceived.get("category", analytics_result.get("category", "")))
    market_state = {
        "pricing_strategy": primary_mode,
        "competition": _score_to_band(competition_score),
        "demand": _score_to_band(demand_score),
        "supplier_quality": _score_to_band(supplier_quality_score),
        "profitability": price_level,
        "market_opportunity": _score_to_band(opportunity_score),
        "risk": _score_to_band(risk_score),
        "confidence": _score_to_band(confidence_score * 100.0),
    }

    evidence_ledger = [
        f"Pricing strategy selected: {market_state['pricing_strategy']}",
        f"Competition signal: {market_state['competition']}",
        f"Demand signal: {market_state['demand']}",
        f"Profitability signal: {market_state['profitability']}",
        f"Category playbook: {category_playbook['category_key']}",
    ]

    strategy_guardrails = [
        "Keep all messaging aligned with the selected pricing strategy.",
        f"Lean on {', '.join(category_playbook['promotion_hooks'][:3])} for launch hooks.",
    ]
    if market_state["pricing_strategy"] == "COMPETITIVE":
        strategy_guardrails.append("Avoid premium luxury positioning and emphasize value.")
    elif market_state["pricing_strategy"] == "PREMIUM":
        strategy_guardrails.append("Avoid bargain language and emphasize trust, warranty, and quality.")
    else:
        strategy_guardrails.append("Use balanced value messaging that protects margin without sounding discount-led.")

    if market_state["competition"] == "HIGH":
        strategy_guardrails.append("Use bundles, flash sales, and warranty proof to beat rival offers.")
    if market_state["demand"] == "HIGH":
        strategy_guardrails.append("Scale inventory and launch quickly while attention is strong.")
    if market_state["profitability"] == "LOW" or market_state["risk"] == "HIGH":
        strategy_guardrails.append("Keep scope conservative until margin and risk improve.")

    return {
        "market_state": market_state,
        "category_playbook": category_playbook,
        "evidence_ledger": evidence_ledger,
        "strategy_guardrails": strategy_guardrails,
        "signals": {
            "seller_count_band": _score_to_band(min(100.0, seller_count * 8.0)),
            "vendor_count_band": _score_to_band(min(100.0, vendor_count * 10.0)),
            "price_spread_band": _score_to_band(min(100.0, price_spread * 2.0)),
            "confidence_band": market_state["confidence"],
        },
    }


def build_generation_input(
    perceived: Dict[str, Any],
    enriched: Optional[Dict[str, Any]] = None,
    business_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    enriched = enriched or perceived
    if business_state is None:
        business_state = build_business_state(perceived, enriched, enriched)

    return {
        "product_name": perceived.get("product_name") or enriched.get("product_name", ""),
        "category": perceived.get("category") or enriched.get("category", ""),
        "market_state": business_state["market_state"],
        "category_playbook": business_state["category_playbook"],
        "strategy_guardrails": business_state["strategy_guardrails"],
        "evidence_ledger": business_state["evidence_ledger"],
        "signal_summary": business_state["signals"],
    }


def apply_strategy_consistency(strategy: Dict[str, Any], business_state: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(strategy)
    market_state = business_state.get("market_state") or {}
    playbook = business_state.get("category_playbook") or {}
    pricing_strategy = str(market_state.get("pricing_strategy", "BALANCED")).upper()
    target_positioning = playbook.get("positioning", "Value-for-Money")
    recommended_channels = list(playbook.get("primary_channels", []))
    tactics = list(playbook.get("promotion_hooks", []))
    corrections: List[str] = []

    pricing_label = {
        "COMPETITIVE": "Competitive",
        "BALANCED": "Balanced",
        "PREMIUM": "Premium",
    }.get(pricing_strategy, "Balanced")

    marketing_mix = result.setdefault("marketing_mix", {})
    price = marketing_mix.setdefault("price", {})
    if price.get("strategy") != pricing_label:
        price["strategy"] = pricing_label
        corrections.append("aligned price strategy with analytics")

    marketing_mix.setdefault("place", {})
    marketing_mix["place"]["channels"] = recommended_channels
    marketing_mix.setdefault("promotion", {})
    marketing_mix["promotion"]["tactics"] = tactics

    branding = result.setdefault("branding", {})
    tone_map = {
        "COMPETITIVE": "practical",
        "BALANCED": "trustworthy",
        "PREMIUM": "aspirational",
    }
    branding["tone"] = tone_map.get(pricing_strategy, "trustworthy")

    stp = result.setdefault("stp", {})
    positioning = stp.setdefault("positioning", {})
    current_positioning = str(positioning.get("statement") or branding.get("value_proposition") or "")
    if pricing_strategy == "COMPETITIVE" and any(term in current_positioning.lower() for term in ("premium", "luxury", "exclusive")):
        positioning["statement"] = "Value-led offer focused on conversion and trust."
        branding["value_proposition"] = "Practical value with warranty-backed confidence"
        corrections.append("removed premium messaging from competitive strategy")
    elif pricing_strategy == "PREMIUM" and any(term in current_positioning.lower() for term in ("cheap", "lowest", "bargain", "discount")):
        positioning["statement"] = "Premium positioning centered on quality and warranty."
        branding["value_proposition"] = "Premium quality with trusted service"
        corrections.append("removed bargain messaging from premium strategy")
    else:
        positioning["statement"] = target_positioning

    launch_plan = result.setdefault("launch_plan", {})
    phases = launch_plan.get("phases") or []
    if not phases:
        phases = [{"name": "Launch", "duration": "2 weeks", "actions": []}]
    lead_phase = phases[0]
    actions = list(lead_phase.get("actions") or [])

    if market_state.get("demand") == "HIGH":
        for action in ("increase inventory", "launch immediately"):
            if action not in actions:
                actions.append(action)
        corrections.append("scaled launch because demand is high")
    if market_state.get("competition") == "HIGH":
        for action in ("use bundles", "run flash sales", "surface warranty"):
            if action not in actions:
                actions.append(action)
        corrections.append("added competitive launch tactics")
    if market_state.get("profitability") == "LOW" or market_state.get("risk") == "HIGH":
        actions = [action for action in actions if action not in {"launch immediately", "scale ads"}]
        if "pilot launch" not in actions:
            actions.append("pilot launch")
        corrections.append("reduced launch scope for risk control")

    lead_phase["actions"] = actions
    phases[0] = lead_phase
    launch_plan["phases"] = phases

    kpis = launch_plan.get("kpis") or []
    if kpis:
        adjusted_kpis = []
        for kpi in kpis:
            updated = deepcopy(kpi)
            target = updated.get("target")
            if isinstance(target, (int, float)):
                if market_state.get("demand") == "HIGH":
                    updated["target"] = round(target * 1.25, 1)
                elif market_state.get("profitability") == "LOW" or market_state.get("risk") == "HIGH":
                    updated["target"] = round(target * 0.75, 1)
            adjusted_kpis.append(updated)
        launch_plan["kpis"] = adjusted_kpis

    channels = result.get("channels") or []
    if not channels:
        result["channels"] = [
            {"name": channel, "priority": index + 1, "rationale": f"category playbook recommends {channel}"}
            for index, channel in enumerate(recommended_channels[:3])
        ]
        corrections.append("filled channels from category playbook")
    else:
        channel_names = [str(item.get("name", "")).strip() for item in channels if isinstance(item, dict)]
        merged = []
        for channel in recommended_channels + channel_names:
            if channel and channel not in merged:
                merged.append(channel)
        result["channels"] = [
            {"name": channel, "priority": index + 1, "rationale": f"aligned with {pricing_label.lower()} positioning"}
            for index, channel in enumerate(merged[:3])
        ]
        if result["channels"] != channels:
            corrections.append("reconciled channel list with playbook")

    result["marketing_decision_summary"] = build_marketing_decision_summary(result, business_state)
    result["marketing_consistency_report"] = {
        "status": "auto_corrected" if corrections else "pass",
        "checks": [
            f"pricing_strategy:{pricing_label}",
            f"competition:{market_state.get('competition', 'MEDIUM')}",
            f"demand:{market_state.get('demand', 'MEDIUM')}",
        ],
        "corrections": corrections,
    }
    return result


def build_marketing_decision_summary(strategy: Dict[str, Any], business_state: Dict[str, Any]) -> Dict[str, Any]:
    market_state = business_state.get("market_state") or {}
    playbook = business_state.get("category_playbook") or {}
    selection_reason = [
        f"{market_state.get('pricing_strategy', 'BALANCED').title()} pricing strategy selected",
        f"Competition is {market_state.get('competition', 'MEDIUM').lower()}",
        f"Demand is {market_state.get('demand', 'MEDIUM').lower()}",
    ]
    if playbook.get("positioning"):
        selection_reason.append(f"Category playbook favors {playbook['positioning']}")

    channels = []
    for item in strategy.get("channels") or []:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            if name and name not in channels:
                channels.append(name)
    if not channels:
        channels = list(playbook.get("primary_channels", []))

    return {
        "selected_positioning": strategy.get("stp", {}).get("positioning", {}).get("statement")
            or playbook.get("positioning", "Value-for-Money"),
        "selection_reason": selection_reason,
        "recommended_channels": channels[:3],
        "confidence": market_state.get("confidence", "MEDIUM").title(),
    }
