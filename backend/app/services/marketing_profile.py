from __future__ import annotations

from typing import Any, Dict


def build_product_profile(enriched: Dict[str, Any], category_profile: Dict[str, Any]) -> Dict[str, Any]:
    family = category_profile["family"]
    price_tier = category_profile["price_tier"]
    competition_level = category_profile["competition_intensity"]
    confidence = float(enriched.get("confidence_score", 0.0))
    margin = float(enriched.get("margin_percent", 0.0))
    seller_count = int(enriched.get("seller_count", 0))
    vendor_count = int(enriched.get("vendor_count", 0))
    review_themes = " ".join(enriched.get("review_themes") or []).lower()
    has_warranty_language = any(
        token in review_themes for token in ("warranty", "authentic", "original", "guarantee")
    )

    purchase_type_map = {
        "mobile_phones": "considered_purchase",
        "audio": "considered_purchase",
        "cameras": "considered_purchase",
        "mobile_accessories": "utility_restock",
        "computer_accessories": "functional_upgrade",
        "generic_gadgets": "impulse_supported",
    }
    motivation_map = {
        "mobile_phones": "specs_resale_and_authenticity",
        "audio": "performance_and_trust",
        "cameras": "security_and_setup_reassurance",
        "mobile_accessories": "compatibility_and_convenience",
        "computer_accessories": "compatibility_and_productivity",
        "generic_gadgets": "quick_utility_and_novelty",
    }
    behavior_map = {
        "mobile_phones": "comparison_heavy",
        "audio": "demo_and_comparison_heavy",
        "cameras": "trust_and_setup_heavy",
        "mobile_accessories": "value_and_bundle_heavy",
        "computer_accessories": "comparison_heavy",
        "generic_gadgets": "short_evaluation_cycle",
    }
    content_map = {
        "mobile_phones": "comparison_specs_and_authenticity_proof",
        "audio": "demo_comfort_and_feature_proof",
        "cameras": "demo_setup_and_scenario_proof",
        "mobile_accessories": "utility_bundle_and_compatibility_proof",
        "computer_accessories": "compatibility_and_performance_proof",
        "generic_gadgets": "short_problem_solution_demos",
    }

    trust_sensitivity = "high" if family in {"mobile_phones", "audio", "cameras"} or has_warranty_language else "medium"
    if confidence < 0.3 or seller_count < 2:
        trust_sensitivity = "high"

    comparison_intensity = "high" if competition_level == "high" or family in {"mobile_phones", "audio", "computer_accessories"} else "medium"
    if family in {"mobile_accessories", "generic_gadgets"} and price_tier == "value":
        comparison_intensity = "medium"

    buyer_trigger = "trust_and_proof"
    if family in {"mobile_accessories", "generic_gadgets"}:
        buyer_trigger = "quick_utility"
    elif family == "audio":
        buyer_trigger = "performance_demo"
    elif family == "cameras":
        buyer_trigger = "security_reassurance"
    elif price_tier == "premium":
        buyer_trigger = "aspiration_and_confidence"

    if margin >= 35 and price_tier in {"mid_market", "premium"}:
        category_behavior = "higher_margin_storytelling"
    else:
        category_behavior = behavior_map.get(family, "comparison_heavy")

    return {
        "product_family": family,
        "purchase_type": purchase_type_map.get(family, "considered_purchase"),
        "buyer_motivation": motivation_map.get(family, "value_and_reassurance"),
        "category_behavior": category_behavior,
        "trust_sensitivity": trust_sensitivity,
        "comparison_intensity": comparison_intensity,
        "content_style_needed": content_map.get(family, "proof_oriented_content"),
        "price_tier": price_tier,
        "competition_level": competition_level,
        "buyer_trigger": buyer_trigger,
        "market_maturity": "crowded" if seller_count >= 6 else "emerging" if seller_count >= 2 else "thin",
        "supply_flexibility": "strong" if vendor_count >= 3 else "limited",
    }
