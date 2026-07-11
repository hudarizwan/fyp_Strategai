from __future__ import annotations

from typing import Any, Dict, List


ARCHETYPES: Dict[str, Dict[str, str]] = {
    "budget_commodity": {
        "focus": "value clarity, bundles, and easy conversion",
        "messaging_style": "practical and price-aware",
        "channel_bias": "marketplace-first",
    },
    "premium_brand": {
        "focus": "quality cues, tone, and aspiration",
        "messaging_style": "polished and confident",
        "channel_bias": "brand-led and creator-assisted",
    },
    "technical_comparison": {
        "focus": "specs, demos, side-by-side proof, and objections",
        "messaging_style": "clear and comparison-heavy",
        "channel_bias": "marketplace plus comparison content",
    },
    "trend_social_first": {
        "focus": "short-form hooks, creators, and shareability",
        "messaging_style": "visual and fast-moving",
        "channel_bias": "social-first",
    },
    "trust_and_warranty": {
        "focus": "authenticity, COD reassurance, warranty, and returns",
        "messaging_style": "reassuring and grounded",
        "channel_bias": "marketplace trust surfaces",
    },
    "gift_lifestyle": {
        "focus": "emotion, gifting, and lifestyle framing",
        "messaging_style": "aspirational and visual",
        "channel_bias": "social and creator content",
    },
    "low_competition_fast_launch": {
        "focus": "speed, early capture, and simple validation",
        "messaging_style": "practical and direct",
        "channel_bias": "single-channel launch",
    },
    "high_competition_differentiation": {
        "focus": "differentiation, comparison hooks, and trust proof",
        "messaging_style": "sharp and objection-aware",
        "channel_bias": "marketplace plus retargeting",
    },
}


def route_strategy_archetype(
    product_profile: Dict[str, Any],
    enriched: Dict[str, Any],
) -> Dict[str, Any]:
    family = product_profile["product_family"]
    trust = product_profile["trust_sensitivity"]
    comparison = product_profile["comparison_intensity"]
    competition = product_profile["competition_level"]
    purchase_type = product_profile["purchase_type"]
    price_tier = product_profile["price_tier"]

    primary = "budget_commodity"
    reasons: List[str] = []

    if price_tier == "premium":
        primary = "premium_brand"
        reasons.append("price tier is premium enough to reward stronger tone and perceived quality.")
    elif comparison == "high":
        primary = "technical_comparison"
        reasons.append("buyers are likely to compare alternatives before buying.")
    elif family in {"mobile_accessories", "generic_gadgets"}:
        primary = "budget_commodity"
        reasons.append("the category converts better on simple value and utility proof.")

    secondary = "trust_and_warranty" if trust == "high" else "low_competition_fast_launch"
    if competition == "high":
        secondary = "high_competition_differentiation"
        reasons.append("competition is crowded, so differentiation is required.")
    elif purchase_type == "impulse_supported":
        secondary = "trend_social_first"
        reasons.append("the product benefits from short-form social discovery.")
    elif trust == "high":
        reasons.append("trust and reassurance are material conversion levers here.")
    else:
        reasons.append("the market is thin enough to launch narrowly and learn quickly.")

    available = [primary]
    if secondary != primary:
        available.append(secondary)

    return {
        "primary": primary,
        "secondary": secondary,
        "available": available,
        "reason": reasons,
        "archetype_details": {name: ARCHETYPES[name] for name in available},
    }
