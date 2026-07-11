"""Validation rules for the deterministic MCB decision agent."""

from __future__ import annotations

from typing import List

from app.services.mcb_models import MCBDecisionInput, ValidationFlag


def validate_business_rules(payload: MCBDecisionInput) -> List[ValidationFlag]:
    """Return validation flags describing pricing, data, and strategy contradictions."""
    flags: List[ValidationFlag] = []

    wholesale = payload.wholesale
    retail = payload.retail
    analytics = payload.analytics
    marketing = payload.marketing
    competitors = payload.competitors

    if wholesale.participant_count < 1 and retail.participant_count < 1:
        flags.append(
            ValidationFlag(
                code="market_data_missing_both_sides",
                severity="critical",
                field="wholesale,retail",
                message="Both wholesale and retail market evidence are missing.",
            )
        )
    else:
        if wholesale.participant_count < 2 or wholesale.avg_price_pkr is None:
            flags.append(
                ValidationFlag(
                    code="insufficient_wholesale_data",
                    severity="warning",
                    field="wholesale",
                    message="Wholesale evidence is thin; supplier coverage should improve before approval.",
                )
            )
        if retail.participant_count < 2 or retail.avg_price_pkr is None:
            flags.append(
                ValidationFlag(
                    code="insufficient_retail_data",
                    severity="warning",
                    field="retail",
                    message="Retail evidence is thin; the price band may not be stable enough yet.",
                )
            )

    if wholesale.avg_price_pkr is not None and analytics.predicted_price_pkr <= wholesale.avg_price_pkr:
        flags.append(
            ValidationFlag(
                code="predicted_price_below_wholesale_average",
                severity="critical",
                field="analytics.predicted_price_pkr",
                message="Predicted sell price is not above the wholesale average.",
            )
        )

    if retail.min_price_pkr is not None and retail.max_price_pkr is not None:
        lower_bound = retail.min_price_pkr * 0.8
        upper_bound = retail.max_price_pkr * 1.2
        if analytics.predicted_price_pkr < lower_bound or analytics.predicted_price_pkr > upper_bound:
            severity = "critical" if analytics.predicted_price_pkr < retail.min_price_pkr * 0.7 or analytics.predicted_price_pkr > retail.max_price_pkr * 1.3 else "warning"
            flags.append(
                ValidationFlag(
                    code="predicted_price_outside_market_band",
                    severity=severity,
                    field="analytics.predicted_price_pkr",
                    message="Predicted sell price sits outside the observed retail band tolerance.",
                )
            )

    if analytics.predicted_margin_percent <= 0:
        flags.append(
            ValidationFlag(
                code="negative_or_zero_margin",
                severity="critical",
                field="analytics.predicted_margin_percent",
                message="Predicted margin is not commercially viable.",
            )
        )
    elif analytics.predicted_margin_percent > 90:
        flags.append(
            ValidationFlag(
                code="unrealistic_margin",
                severity="critical",
                field="analytics.predicted_margin_percent",
                message="Predicted margin is unrealistically high for a defendable go-to-market decision.",
            )
        )
    elif analytics.predicted_margin_percent > 70:
        flags.append(
            ValidationFlag(
                code="aggressive_margin_assumption",
                severity="warning",
                field="analytics.predicted_margin_percent",
                message="Predicted margin is unusually high and should be rechecked.",
            )
        )

    if marketing.budget_pkr is not None and marketing.expected_roi_percent is not None:
        if analytics.predicted_margin_percent < 10 and marketing.expected_roi_percent < 20 and marketing.budget_pkr > analytics.predicted_price_pkr * 0.3:
            flags.append(
                ValidationFlag(
                    code="budget_roi_inconsistent_with_margin",
                    severity="warning",
                    field="marketing.budget_pkr",
                    message="Marketing budget and ROI assumptions are too optimistic for the available unit margin.",
                )
            )

    positioning_text = (marketing.positioning or "").lower()
    if any(word in positioning_text for word in ("premium", "exclusive", "luxury")):
        low_price_signal = retail.avg_price_pkr is not None and retail.avg_price_pkr < 5000
        low_margin_signal = analytics.predicted_margin_percent < 12
        if low_price_signal or low_margin_signal:
            flags.append(
                ValidationFlag(
                    code="premium_positioning_contradiction",
                    severity="warning",
                    field="marketing.positioning",
                    message="Premium positioning conflicts with the observed price or margin signals.",
                )
            )

    if competitors.price_aggression == "high" and (
        analytics.confidence_score < 0.55 or marketing.confidence_score < 0.55
    ):
        flags.append(
            ValidationFlag(
                code="aggressive_market_with_weak_confidence",
                severity="warning",
                field="competitors.price_aggression",
                message="Competitive pricing pressure is high while confidence is still weak.",
            )
        )

    missing_marketing_fields = [
        field_name
        for field_name, value in {
            "segment": marketing.segment,
            "positioning": marketing.positioning,
            "primary_channel": marketing.primary_channel,
        }.items()
        if not value
    ]
    if missing_marketing_fields:
        flags.append(
            ValidationFlag(
                code="marketing_strategy_incomplete",
                severity="warning",
                field="marketing",
                message=f"Marketing output is incomplete: missing {', '.join(missing_marketing_fields)}.",
            )
        )

    return flags
