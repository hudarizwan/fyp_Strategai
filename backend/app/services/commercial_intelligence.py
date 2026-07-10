from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence


@dataclass(frozen=True)
class CostProfile:
    commission_rate: float
    shipping_base_pkr: float
    shipping_variable_rate: float
    packaging_pkr: float
    advertising_rate: float
    tax_rate: float
    overhead_rate: float
    contingency_rate: float


DEFAULT_COST_PROFILE = CostProfile(
    commission_rate=0.08,
    shipping_base_pkr=180.0,
    shipping_variable_rate=0.01,
    packaging_pkr=45.0,
    advertising_rate=0.04,
    tax_rate=0.15,
    overhead_rate=0.03,
    contingency_rate=0.03,
)

CATEGORY_COST_PROFILES: Dict[str, CostProfile] = {
    "mobile_phones": CostProfile(0.06, 260.0, 0.008, 90.0, 0.05, 0.15, 0.02, 0.03),
    "laptops": CostProfile(0.05, 320.0, 0.006, 120.0, 0.05, 0.15, 0.025, 0.03),
    "headsets": CostProfile(0.08, 180.0, 0.010, 55.0, 0.045, 0.15, 0.03, 0.03),
    "audio": CostProfile(0.08, 180.0, 0.010, 55.0, 0.045, 0.15, 0.03, 0.03),
    "computer_accessories": CostProfile(0.08, 150.0, 0.010, 50.0, 0.04, 0.15, 0.025, 0.03),
    "mobile_accessories": CostProfile(0.10, 120.0, 0.012, 40.0, 0.035, 0.15, 0.03, 0.035),
    "cameras": CostProfile(0.07, 220.0, 0.009, 70.0, 0.05, 0.15, 0.03, 0.03),
    "home_goods": CostProfile(0.09, 200.0, 0.012, 60.0, 0.035, 0.15, 0.03, 0.035),
    "fashion": CostProfile(0.12, 160.0, 0.014, 35.0, 0.045, 0.15, 0.035, 0.04),
    "beauty": CostProfile(0.11, 140.0, 0.012, 30.0, 0.05, 0.15, 0.035, 0.04),
    "general_retail": CostProfile(0.09, 180.0, 0.010, 45.0, 0.04, 0.15, 0.03, 0.035),
    "generic_gadgets": CostProfile(0.09, 170.0, 0.011, 45.0, 0.04, 0.15, 0.03, 0.035),
    "unknown": DEFAULT_COST_PROFILE,
}

QUALITY_BANDS: Dict[str, Dict[str, Any]] = {
    "limited": {
        "max_channels": 2,
        "max_kpis": 3,
        "orders_multiplier": 0.55,
        "views_multiplier": 0.60,
        "content_frequency": "2 focused posts per week",
        "channel_scope": "narrow",
        "launch_scope": "narrow",
    },
    "guarded": {
        "max_channels": 3,
        "max_kpis": 4,
        "orders_multiplier": 0.75,
        "views_multiplier": 0.80,
        "content_frequency": "3 focused posts per week",
        "channel_scope": "focused",
        "launch_scope": "focused",
    },
    "balanced": {
        "max_channels": 4,
        "max_kpis": 4,
        "orders_multiplier": 0.95,
        "views_multiplier": 0.95,
        "content_frequency": "3 focused posts per week",
        "channel_scope": "balanced",
        "launch_scope": "balanced",
    },
    "strong": {
        "max_channels": 4,
        "max_kpis": 5,
        "orders_multiplier": 1.10,
        "views_multiplier": 1.10,
        "content_frequency": "4 focused posts per week",
        "channel_scope": "broad",
        "launch_scope": "broad",
    },
}


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


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


def infer_market_family(product_name: str = "", category: str = "") -> str:
    combined = f"{product_name} {category}".lower()
    if any(token in combined for token in ("iphone", "samsung", "redmi", "infinix", "mobile", "phone")):
        return "mobile_phones"
    if any(token in combined for token in ("laptop", "macbook", "notebook", "chromebook", "thinkpad")):
        return "laptops"
    if any(token in combined for token in ("headset", "headphone", "earbud", "earphone", "audio", "speaker")):
        return "headsets"
    if any(token in combined for token in ("camera", "cctv", "webcam", "surveillance")):
        return "cameras"
    if any(token in combined for token in ("charger", "cable", "adapter", "power bank", "case", "cover")):
        return "mobile_accessories"
    if any(token in combined for token in ("mouse", "keyboard", "ssd", "router", "monitor", "accessor")):
        return "computer_accessories"
    if any(token in combined for token in ("makeup", "cream", "serum", "beauty", "skincare")):
        return "beauty"
    if any(token in combined for token in ("shirt", "dress", "shoe", "bag", "fashion")):
        return "fashion"
    if any(token in combined for token in ("home", "kitchen", "furniture", "organizer", "pillow")):
        return "home_goods"
    if "retail" in combined or "general" in combined:
        return "general_retail"
    return "generic_gadgets"


def resolve_cost_profile(product_name: str, category: str) -> CostProfile:
    family = infer_market_family(product_name, category)
    return CATEGORY_COST_PROFILES.get(family, CATEGORY_COST_PROFILES["unknown"])


def classify_quality_band(
    confidence_score: float,
    low_sample_warning: bool,
    wholesale_vendor_count: int,
    retail_listing_count: int,
    net_margin_percent: Optional[float] = None,
) -> str:
    confidence = _safe_float(confidence_score)
    if low_sample_warning or wholesale_vendor_count < 3 or retail_listing_count < 5:
        return "limited"
    if confidence < 0.55 or (net_margin_percent is not None and net_margin_percent < 8.0):
        return "guarded"
    if confidence < 0.75 or (net_margin_percent is not None and net_margin_percent < 15.0):
        return "balanced"
    return "strong"


def _build_adjusted_contingency(
    gross_profit_pkr: float,
    confidence_score: float,
    low_sample_warning: bool,
    price_cv: float,
    cost_profile: CostProfile,
) -> float:
    uncertainty_factor = 1.0
    if low_sample_warning:
        uncertainty_factor += 0.35
    uncertainty_factor += max(0.0, 0.5 - _safe_float(confidence_score)) * 0.6
    uncertainty_factor += min(max(price_cv, 0.0), 1.0) * 0.35
    return max(gross_profit_pkr * cost_profile.contingency_rate * uncertainty_factor, 0.0)


def compute_profitability_snapshot(
    *,
    product_name: str,
    category: str,
    buy_price_pkr: float,
    sell_price_pkr: float,
    confidence_score: float,
    low_sample_warning: bool,
    wholesale_metrics: Dict[str, Any],
    retail_metrics: Dict[str, Any],
    combined_metrics: Dict[str, Any],
    price_band: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    buy = max(_safe_float(buy_price_pkr), 0.0)
    sell = max(_safe_float(sell_price_pkr), 0.0)
    price_band = price_band or {}
    cost_profile = resolve_cost_profile(product_name, category)
    gross_profit = max(sell - buy, 0.0)

    commission = sell * cost_profile.commission_rate
    shipping = cost_profile.shipping_base_pkr + (sell * cost_profile.shipping_variable_rate)
    packaging = cost_profile.packaging_pkr
    advertising = sell * cost_profile.advertising_rate
    taxes = sell * cost_profile.tax_rate
    overhead = sell * cost_profile.overhead_rate
    contingency = _build_adjusted_contingency(
        gross_profit,
        confidence_score=confidence_score,
        low_sample_warning=low_sample_warning,
        price_cv=_safe_float(retail_metrics.get("price_cv", 0.0)),
        cost_profile=cost_profile,
    )

    total_costs = commission + shipping + packaging + advertising + taxes + overhead + contingency
    net_profit = gross_profit - total_costs
    gross_margin_percent = round((gross_profit / sell) * 100.0, 2) if sell > 0 else 0.0
    net_margin_percent = round((net_profit / sell) * 100.0, 2) if sell > 0 else 0.0
    roi_percent = round((net_profit / max(buy + total_costs, 1.0)) * 100.0, 2) if (buy + total_costs) > 0 else 0.0

    variable_rate = cost_profile.commission_rate + cost_profile.shipping_variable_rate + cost_profile.advertising_rate + cost_profile.tax_rate + cost_profile.overhead_rate
    break_even_denominator = max(1.0 - variable_rate, 0.05)
    break_even_numerator = buy + cost_profile.shipping_base_pkr + packaging + contingency
    break_even_sell = break_even_numerator / break_even_denominator

    quality_band = classify_quality_band(
        confidence_score=confidence_score,
        low_sample_warning=low_sample_warning,
        wholesale_vendor_count=_safe_int(wholesale_metrics.get("vendor_count", 0)),
        retail_listing_count=_safe_int(retail_metrics.get("vendor_count", 0)),
        net_margin_percent=net_margin_percent,
    )

    profitability_confidence = _clamp(
        _safe_float(confidence_score)
        - (0.08 if low_sample_warning else 0.0)
        - min(_safe_float(retail_metrics.get("price_cv", 0.0)) * 0.10, 0.12)
        - (0.05 if net_margin_percent < 10 else 0.0)
    )

    risk_notes: List[str] = []
    if low_sample_warning:
        risk_notes.append("limited data sample raises forecast uncertainty")
    if net_margin_percent < 10:
        risk_notes.append("net margin is thin after operating costs")
    if _safe_float(retail_metrics.get("price_cv", 0.0)) > 0.35:
        risk_notes.append("retail pricing variance is high")
    if _safe_float(wholesale_metrics.get("price_cv", 0.0)) > 0.35:
        risk_notes.append("wholesale pricing variance is high")
    if not risk_notes:
        risk_notes.append("cost structure remains commercially manageable")

    return {
        "product_name": product_name,
        "category": category,
        "buy_price_pkr": round(buy, 2),
        "sell_price_pkr": round(sell, 2),
        "quality_band": quality_band,
        "cost_profile": {
            "commission_rate": round(cost_profile.commission_rate, 4),
            "shipping_base_pkr": round(cost_profile.shipping_base_pkr, 2),
            "shipping_variable_rate": round(cost_profile.shipping_variable_rate, 4),
            "packaging_pkr": round(cost_profile.packaging_pkr, 2),
            "advertising_rate": round(cost_profile.advertising_rate, 4),
            "tax_rate": round(cost_profile.tax_rate, 4),
            "overhead_rate": round(cost_profile.overhead_rate, 4),
            "contingency_rate": round(cost_profile.contingency_rate, 4),
        },
        "cost_breakdown": {
            "gross_profit_pkr": round(gross_profit, 2),
            "commission_pkr": round(commission, 2),
            "shipping_pkr": round(shipping, 2),
            "packaging_pkr": round(packaging, 2),
            "advertising_pkr": round(advertising, 2),
            "taxes_pkr": round(taxes, 2),
            "overhead_pkr": round(overhead, 2),
            "contingency_pkr": round(contingency, 2),
            "total_operating_cost_pkr": round(total_costs, 2),
        },
        "profitability_summary": {
            "gross_profit_pkr": round(gross_profit, 2),
            "net_profit_pkr": round(net_profit, 2),
            "gross_margin_percent": gross_margin_percent,
            "net_margin_percent": net_margin_percent,
            "roi_percent": roi_percent,
            "break_even_sell_price_pkr": round(break_even_sell, 2),
            "profitability_confidence": round(profitability_confidence, 4),
            "risk_notes": risk_notes,
            "price_band": {
                "min": round(_safe_float(price_band.get("min", 0.0)), 2),
                "max": round(_safe_float(price_band.get("max", 0.0)), 2),
                "avg": round(_safe_float(price_band.get("avg", 0.0)), 2),
                "currency": price_band.get("currency", "PKR"),
            },
        },
    }


def _normalise_count(value: Any) -> int:
    return max(_safe_int(value), 0)


def build_market_intelligence_snapshot(
    *,
    wholesale_metrics: Dict[str, Any],
    retail_metrics: Dict[str, Any],
    combined_metrics: Dict[str, Any],
    profitability_snapshot: Dict[str, Any],
    confidence_score: float,
    low_sample_warning: bool,
) -> Dict[str, Any]:
    wholesale_count = _normalise_count(wholesale_metrics.get("vendor_count", 0))
    retail_count = _normalise_count(retail_metrics.get("vendor_count", 0))
    wholesale_cv = _safe_float(wholesale_metrics.get("price_cv", 0.0))
    retail_cv = _safe_float(retail_metrics.get("price_cv", 0.0))
    retail_price_band = profitability_snapshot.get("profitability_summary", {}).get("price_band", {}) or {}
    net_margin = _safe_float(profitability_snapshot.get("profitability_summary", {}).get("net_margin_percent", 0.0))
    gross_margin = _safe_float(profitability_snapshot.get("profitability_summary", {}).get("gross_margin_percent", 0.0))
    profitability_confidence = _safe_float(profitability_snapshot.get("profitability_summary", {}).get("profitability_confidence", confidence_score))

    demand_score = _clamp(
        (retail_count / 10.0) * 0.45
        + (1.0 - min(retail_cv, 1.0)) * 0.25
        + (1.0 if combined_metrics.get("has_both_sources") else 0.5) * 0.20
        + _safe_float(confidence_score) * 0.10
    ) * 100.0
    competition_pressure = _clamp(
        (retail_count / 12.0) * 0.40
        + min(retail_cv, 1.0) * 0.25
        + (0.20 if combined_metrics.get("has_both_sources") else 0.10)
        + (0.15 if low_sample_warning else 0.0)
    ) * 100.0
    supplier_quality = _clamp(
        (wholesale_count / 8.0) * 0.45
        + (1.0 - min(wholesale_cv, 1.0)) * 0.35
        + (0.20 if combined_metrics.get("has_both_sources") else 0.0)
    ) * 100.0
    market_saturation = _clamp(
        (retail_count / 14.0) * 0.55
        + min(retail_cv, 1.0) * 0.30
        + (0.15 if not combined_metrics.get("has_both_sources") else 0.0)
    ) * 100.0
    data_quality = _clamp(
        _safe_float(confidence_score) * 0.45
        + (0.25 if not low_sample_warning else 0.10)
        + (0.15 if wholesale_count >= 3 else 0.05)
        + (0.15 if retail_count >= 5 else 0.05)
    ) * 100.0
    risk_score = _clamp(
        (100.0 - net_margin * 0.85) / 100.0
        + (0.20 if low_sample_warning else 0.0)
        + min(retail_cv * 0.25, 0.20)
        + (0.15 if market_saturation > 60 else 0.0)
    ) * 100.0
    opportunity_score = _clamp(
        (demand_score / 100.0) * 0.40
        + (supplier_quality / 100.0) * 0.15
        + max(net_margin, 0.0) / 100.0 * 0.30
        + (1.0 - risk_score / 100.0) * 0.15
    ) * 100.0

    confidence_band = classify_quality_band(
        confidence_score=confidence_score,
        low_sample_warning=low_sample_warning,
        wholesale_vendor_count=wholesale_count,
        retail_listing_count=retail_count,
        net_margin_percent=net_margin,
    )

    return {
        "confidence_band": confidence_band,
        "confidence_score": round(profitability_confidence * 100.0, 2),
        "demand_score": round(demand_score, 2),
        "competition_score": round(competition_pressure, 2),
        "supplier_quality_score": round(supplier_quality, 2),
        "market_saturation_score": round(market_saturation, 2),
        "data_quality_score": round(data_quality, 2),
        "risk_score": round(risk_score, 2),
        "opportunity_score": round(opportunity_score, 2),
        "reasoning": {
            "demand": [
                f"{retail_count} retail seller signal(s) support visible market interest." if retail_count else "No retail seller evidence is present yet.",
                f"Retail band remains at PKR {retail_price_band.get('min', 0):,.0f}-{retail_price_band.get('max', 0):,.0f}." if retail_price_band else "Retail band is still incomplete.",
            ],
            "competition": [
                f"Retail price variance is {retail_cv:.2f}, which indicates {('strong' if retail_cv > 0.35 else 'moderate' if retail_cv > 0.18 else 'tight')} pricing pressure.",
                "Low sample size keeps competition estimates conservative." if low_sample_warning else "Sample size is broad enough for a more stable competition read.",
            ],
            "supplier": [
                f"{wholesale_count} wholesale supplier signal(s) are available for sourcing review.",
                f"Wholesale variance is {wholesale_cv:.2f}, which suggests {('active negotiation room' if wholesale_cv < 0.18 else 'some price spread' if wholesale_cv < 0.35 else 'volatile supplier pricing')}."
            ],
            "risk": [
                f"Net margin sits at {net_margin:.2f}% after operating costs.",
                "Risk is elevated because the market sample is limited." if low_sample_warning else "Risk stays more manageable because the sample is reasonably broad.",
            ],
            "opportunity": [
                f"Profitability leaves a net margin of {net_margin:.2f}% and gross margin of {gross_margin:.2f}%.",
                f"Break-even sell price is PKR {profitability_snapshot.get('profitability_summary', {}).get('break_even_sell_price_pkr', 0):,.0f}.",
            ],
        },
    }



def _round_psychological_price(value: float) -> float:
    value = max(_safe_float(value), 0.0)
    if value < 100.0:
        return round(max(value, 9.0), 2)
    floored = int(value)
    candidate = (floored // 10) * 10 - 1
    if candidate <= 0:
        candidate = 9
    if candidate < value * 0.94:
        candidate = ((floored // 10) * 10) + 9
    return round(float(candidate), 2)


def _clamp_price_candidate(mode: str, candidate: float, buy_price_pkr: float, price_band: Dict[str, Any]) -> float:
    retail_min = _safe_float(price_band.get("min", 0.0))
    retail_max = _safe_float(price_band.get("max", 0.0))
    retail_avg = _safe_float(price_band.get("avg", 0.0))
    lower_bound = max(_safe_float(buy_price_pkr) * 1.05, 0.0)
    upper_bound = max(candidate, lower_bound)

    if retail_min > 0.0:
        if mode == "competitive":
            lower_bound = max(lower_bound, retail_min * 0.94)
            upper_bound = max(lower_bound, retail_min * 1.01)
        elif mode == "balanced":
            lower_bound = max(lower_bound, retail_min * 0.97)
            upper_bound = max(lower_bound, (retail_avg or retail_max or retail_min) * 1.01)
        elif mode == "premium":
            lower_bound = max(lower_bound, (retail_avg or retail_min) * 1.01)
            upper_bound = max(lower_bound, (retail_max or retail_avg or retail_min) * 1.04)
        else:
            lower_bound = max(lower_bound, retail_min * 0.96)
            upper_bound = max(lower_bound, (retail_avg or retail_max or retail_min) * 1.02)
    elif retail_avg > 0.0:
        lower_bound = max(lower_bound, retail_avg * 0.9)
        upper_bound = max(lower_bound, retail_avg * 1.08)

    return round(min(max(candidate, lower_bound), upper_bound), 2)


def build_pricing_mode_snapshot(
    *,
    product_name: str,
    category: str,
    wholesale_metrics: Dict[str, Any],
    retail_metrics: Dict[str, Any],
    combined_metrics: Dict[str, Any],
    profitability_snapshot: Dict[str, Any],
    confidence_score: float,
    low_sample_warning: bool,
    price_band: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    price_band = price_band or profitability_snapshot.get("profitability_summary", {}).get("price_band") or {}
    buy_price = _safe_float(profitability_snapshot.get("buy_price_pkr", 0.0))
    base_sell = _safe_float(profitability_snapshot.get("sell_price_pkr", 0.0))
    retail_min = _safe_float(price_band.get("min", 0.0))
    retail_max = _safe_float(price_band.get("max", 0.0))
    retail_avg = _safe_float(price_band.get("avg", 0.0))
    retail_cv = _safe_float(retail_metrics.get("price_cv", 0.0))
    wholesale_count = _normalise_count(wholesale_metrics.get("vendor_count", 0))
    retail_count = _normalise_count(retail_metrics.get("vendor_count", 0))
    family = infer_market_family(product_name, category)
    confidence = _clamp(_safe_float(confidence_score))
    price_spread = max(retail_max - retail_min, 0.0)
    retail_anchor = retail_avg or retail_min or retail_max or base_sell or (buy_price * 1.25)
    competition_pressure = _clamp((retail_count / 8.0) * 0.55 + min(retail_cv, 1.0) * 0.45)
    data_strength = _clamp(
        confidence
        + (0.08 if combined_metrics.get("has_both_sources") else -0.06)
        + (0.05 if wholesale_count >= 3 else -0.04)
        + (0.05 if retail_count >= 5 else -0.08)
        - (0.16 if low_sample_warning else 0.0)
    )
    premium_affinity = 0.12 if family in {"mobile_phones", "laptops", "headsets", "cameras", "beauty", "fashion"} else 0.04
    psychological_affinity = 0.12 if family in {"headsets", "computer_accessories", "mobile_accessories", "beauty", "fashion", "general_retail"} else 0.05

    raw_candidates = {
        "competitive": min(base_sell, retail_anchor) - (price_spread * 0.08 if price_spread else retail_anchor * 0.02),
        "balanced": base_sell or retail_anchor,
        "premium": max(base_sell, retail_anchor) + (price_spread * (0.12 + premium_affinity)),
        "psychological": _round_psychological_price((base_sell or retail_anchor) - max(price_spread * 0.02, 1.0)),
    }

    pricing_modes: Dict[str, Dict[str, Any]] = {}
    mode_scores: Dict[str, float] = {}
    for mode, raw_candidate in raw_candidates.items():
        candidate_price = _clamp_price_candidate(mode, raw_candidate, buy_price, price_band)
        variant_profitability = compute_profitability_snapshot(
            product_name=product_name,
            category=category,
            buy_price_pkr=buy_price,
            sell_price_pkr=candidate_price,
            confidence_score=confidence,
            low_sample_warning=low_sample_warning,
            wholesale_metrics=wholesale_metrics,
            retail_metrics=retail_metrics,
            combined_metrics=combined_metrics,
            price_band=price_band,
        )
        profitability_summary = variant_profitability.get("profitability_summary") or {}
        net_margin = _safe_float(profitability_summary.get("net_margin_percent", 0.0))
        break_even = _safe_float(profitability_summary.get("break_even_sell_price_pkr", 0.0))
        margin_safety = _clamp((candidate_price - break_even) / max(candidate_price, 1.0))

        if mode == "competitive":
            market_fit = _clamp(
                0.46
                + competition_pressure * 0.24
                + (0.16 if low_sample_warning else 0.0)
                + max(0.0, 0.62 - confidence) * 0.30
                + min(retail_cv, 1.0) * 0.10
            )
        elif mode == "balanced":
            market_fit = _clamp(
                0.56
                + data_strength * 0.18
                + (0.08 if combined_metrics.get("has_both_sources") else 0.0)
                - competition_pressure * 0.06
            )
        elif mode == "premium":
            market_fit = _clamp(
                0.30
                + data_strength * 0.22
                + premium_affinity * 0.70
                + max(0.0, 0.22 - min(retail_cv, 1.0)) * 0.45
                + max(0.0, confidence - 0.7) * 0.25
                - (0.22 if low_sample_warning else 0.0)
            )
        else:
            market_fit = _clamp(
                0.38
                + data_strength * 0.16
                + psychological_affinity * 0.65
                + competition_pressure * 0.08
                + max(0.0, 0.3 - min(retail_cv, 1.0)) * 0.15
            )

        fit_score = _clamp(
            margin_safety * 0.42
            + market_fit * 0.38
            + data_strength * 0.20
            - (0.14 if net_margin < 8.0 else 0.0)
            - (0.08 if candidate_price <= break_even else 0.0)
        )

        reasoning: List[str] = [
            f"candidate price set at PKR {candidate_price:,.0f} for the {mode} mode.",
            f"expected net margin is {net_margin:.2f}% against break-even at PKR {break_even:,.0f}.",
        ]
        if mode == "competitive":
            reasoning.append("Mode leans toward faster conversion when price pressure or uncertainty is elevated.")
        elif mode == "balanced":
            reasoning.append("Mode keeps pricing near the current recommendation while preserving commercial discipline.")
        elif mode == "premium":
            reasoning.append("Mode stretches upward only when category fit, confidence, and retail stability can support it.")
        else:
            reasoning.append("Mode uses charm pricing to stay close to the retail anchor with a conversion-friendly ending.")
        if low_sample_warning:
            reasoning.append("Low sample warning reduces confidence in aggressive price expansion.")

        pricing_modes[mode] = {
            "candidate_price_pkr": round(candidate_price, 2),
            "expected_net_margin_percent": round(net_margin, 2),
            "fit_score": round(fit_score, 4),
            "market_fit_score": round(market_fit, 4),
            "margin_safety_score": round(margin_safety, 4),
            "confidence_weight": round(data_strength, 4),
            "reasoning": reasoning,
        }
        mode_scores[mode] = fit_score

    ordered_modes = sorted(
        pricing_modes.keys(),
        key=lambda mode: (mode_scores[mode], pricing_modes[mode]["expected_net_margin_percent"], -pricing_modes[mode]["candidate_price_pkr"]),
        reverse=True,
    )
    primary_mode = ordered_modes[0] if ordered_modes else "balanced"
    alternate_modes = [mode for mode in ordered_modes if mode != primary_mode]
    return {
        "pricing_modes": pricing_modes,
        "primary_pricing_mode": primary_mode,
        "alternate_pricing_modes": alternate_modes,
    }

def build_evidence_ledger(
    *,
    product_name: str,
    category: str,
    wholesale_metrics: Dict[str, Any],
    retail_metrics: Dict[str, Any],
    combined_metrics: Dict[str, Any],
    profitability_snapshot: Dict[str, Any],
    market_intelligence: Dict[str, Any],
    price_band: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    price_band = price_band or {}
    ledger: List[Dict[str, Any]] = []
    gross = profitability_snapshot.get("profitability_summary", {})
    cost_breakdown = profitability_snapshot.get("cost_breakdown", {})
    cost_profile = profitability_snapshot.get("cost_profile", {})

    ledger.append(
        {
            "section": "pricing",
            "recommendation": (
                f"Use a net profit target around PKR {gross.get('net_profit_pkr', 0):,.0f} "
                f"with a net margin of {gross.get('net_margin_percent', 0):.1f}%."
            ),
            "evidence": [
                f"recommended_buy_price_pkr={profitability_snapshot.get('buy_price_pkr', 0)}",
                f"recommended_sell_price_pkr={profitability_snapshot.get('sell_price_pkr', 0)}",
                f"gross_profit_pkr={cost_breakdown.get('gross_profit_pkr', 0)}",
                f"commission_rate={cost_profile.get('commission_rate', 0)}",
                f"shipping_base_pkr={cost_profile.get('shipping_base_pkr', 0)}",
                f"advertising_rate={cost_profile.get('advertising_rate', 0)}",
                f"tax_rate={cost_profile.get('tax_rate', 0)}",
            ],
        }
    )
    ledger.append(
        {
            "section": "demand",
            "recommendation": (
                f"Treat demand as {market_intelligence.get('confidence_band', 'balanced')} because retail coverage is "
                f"{_normalise_count(retail_metrics.get('vendor_count', 0))} listings and the observed band is PKR "
                f"{price_band.get('min', 0):,.0f}-{price_band.get('max', 0):,.0f}."
            ),
            "evidence": [
                f"retail_sellers_count={retail_metrics.get('vendor_count', 0)}",
                f"retail_price_cv={retail_metrics.get('price_cv', 0)}",
                f"market_saturation_score={market_intelligence.get('market_saturation_score', 0)}",
            ],
        }
    )
    ledger.append(
        {
            "section": "competition",
            "recommendation": (
                f"Pricing pressure is {market_intelligence.get('competition_score', 0):.0f}/100, so the strategy should "
                f"stay aligned to the observed retail band and not rely on aggressive widening."
            ),
            "evidence": [
                f"retail_sellers_count={retail_metrics.get('vendor_count', 0)}",
                f"retail_price_band_min={price_band.get('min', 0)}",
                f"retail_price_band_max={price_band.get('max', 0)}",
                f"retail_price_cv={retail_metrics.get('price_cv', 0)}",
            ],
        }
    )
    ledger.append(
        {
            "section": "supplier",
            "recommendation": (
                f"Supplier quality is {market_intelligence.get('supplier_quality_score', 0):.0f}/100, so sourcing should "
                f"prefer the strongest vendors while preserving MOQ discipline."
            ),
            "evidence": [
                f"wholesale_vendors_count={wholesale_metrics.get('vendor_count', 0)}",
                f"wholesale_price_cv={wholesale_metrics.get('price_cv', 0)}",
                f"moq_min={combined_metrics.get('moq_min', 'n/a')}",
            ],
        }
    )
    ledger.append(
        {
            "section": "risk",
            "recommendation": (
                f"Risk is {market_intelligence.get('risk_score', 0):.0f}/100 because the profit cushion and sample size "
                f"need to be treated carefully."
            ),
            "evidence": [
                f"net_margin_percent={gross.get('net_margin_percent', 0)}",
                f"profitability_confidence={gross.get('profitability_confidence', 0)}",
                f"quality_band={profitability_snapshot.get('quality_band', 'balanced')}",
            ],
        }
    )

    if combined_metrics.get("has_both_sources"):
        ledger.append(
            {
                "section": "validation",
                "recommendation": "Use both wholesale and retail evidence because the comparison is grounded on both sides of the market.",
                "evidence": [
                    "has_both_sources=True",
                    f"platform_count={combined_metrics.get('platform_count', 0)}",
                    f"vendor_count={combined_metrics.get('vendor_count', 0)}",
                ],
            }
        )
    return ledger
