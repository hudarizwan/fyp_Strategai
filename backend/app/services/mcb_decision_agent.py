"""Deterministic MCB decision agent for final strategy governance.

Example:
    from app.services.mcb_decision_agent import MCBDecisionAgent
    from app.services.mcb_models import (
        AnalyticsOutput,
        CompetitorSignals,
        MarketingOutput,
        MarketStats,
        MCBDecisionInput,
    )

    agent = MCBDecisionAgent()
    decision = agent.decide(
        MCBDecisionInput(
            product_name="HyperX Cloud III",
            category="headset",
            wholesale=MarketStats(avg_price_pkr=2800, min_price_pkr=2600, max_price_pkr=3200, participant_count=4),
            retail=MarketStats(avg_price_pkr=3900, min_price_pkr=3600, max_price_pkr=4300, participant_count=3),
            analytics=AnalyticsOutput(predicted_price_pkr=3850, predicted_margin_percent=27, confidence_score=0.78),
            competitors=CompetitorSignals(discount_intensity="medium", stock_out_rate=0.1, price_aggression="medium"),
            marketing=MarketingOutput(
                segment="value gamers",
                positioning="Trusted gaming headset with clear comfort and proof-led messaging.",
                primary_channel="daraz",
                budget_pkr=18000,
                expected_roi_percent=42,
                confidence_score=0.76,
            ),
        )
    )
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.services.ecdb import ECDB
from app.services.mcb_models import (
    ApprovedStrategy,
    MCBDecisionInput,
    MCBDecisionOutput,
    ValidationFlag,
)
from app.services.mcb_rules import validate_business_rules
from app.services.mcb_scoring import compute_final_confidence


DEFAULT_CONFIDENCE_THRESHOLD = 0.70
CONFIDENCE_THRESHOLD = DEFAULT_CONFIDENCE_THRESHOLD


class MCBDecisionAgent:
    """Final deterministic decision module that governs approval readiness."""

    def __init__(self, db: Optional[ECDB] = None):
        self.db = db

    def _resolve_confidence_threshold(self, category: str) -> Tuple[float, str, Optional[str]]:
        if self.db:
            resolver = getattr(self.db, "resolve_mcb_confidence_threshold", None)
            if callable(resolver):
                try:
                    resolved = resolver(category) or {}
                    return (
                        float(resolved.get("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD)),
                        str(resolved.get("threshold_source_tier", "hardcoded 0.70")),
                        resolved.get("threshold_source_category"),
                    )
                except Exception:
                    pass
            legacy_resolver = getattr(self.db, "get_effective_mcb_confidence_threshold", None)
            if callable(legacy_resolver):
                try:
                    return float(legacy_resolver(category)), "legacy fallback", None
                except Exception:
                    pass
        return DEFAULT_CONFIDENCE_THRESHOLD, "hardcoded 0.70", None

    def decide(self, payload: MCBDecisionInput) -> MCBDecisionOutput:
        flags = validate_business_rules(payload)
        final_confidence, breakdown = compute_final_confidence(payload, flags)

        critical_flags = [flag for flag in flags if flag.severity == "critical"]
        warning_flags = [flag for flag in flags if flag.severity == "warning"]
        confidence_threshold, threshold_source_tier, threshold_source_category = self._resolve_confidence_threshold(payload.category)
        reasoning_trail = self._build_reasoning_trail(payload, final_confidence, flags, confidence_threshold, threshold_source_tier, breakdown)

        if critical_flags:
            status = "human_review"
            next_action = "Escalate to human review and inspect flagged pricing/data contradictions."
        elif final_confidence >= confidence_threshold and not critical_flags:
            status = "approved"
            next_action = "Approve the strategy for dashboard delivery and downstream execution."
        elif warning_flags:
            status = "needs_reanalysis"
            next_action = "Re-run upstream analysis with better market coverage or revised assumptions."
        else:
            status = "human_review"
            next_action = "Escalate to human review because confidence is too weak without a clear automated recovery path."

        approved_strategy = None
        approved_price_pkr = None
        approved_margin_percent = None
        if status == "approved":
            approved_strategy = ApprovedStrategy(
                segment=payload.marketing.segment or "",
                positioning=payload.marketing.positioning or "",
                primary_channel=payload.marketing.primary_channel or "",
                budget_pkr=payload.marketing.budget_pkr,
                expected_roi_percent=payload.marketing.expected_roi_percent,
            )
            approved_price_pkr = payload.analytics.predicted_price_pkr
            approved_margin_percent = payload.analytics.predicted_margin_percent

        return MCBDecisionOutput(
            final_status=status,
            final_confidence=final_confidence,
            confidence_threshold=confidence_threshold,
            threshold_source_tier=threshold_source_tier,
            threshold_source_category=threshold_source_category,
            approved_price_pkr=approved_price_pkr,
            approved_margin_percent=approved_margin_percent,
            approved_strategy=approved_strategy,
            validation_flags=flags,
            reasoning_trail=reasoning_trail,
            next_action=next_action,
            score_breakdown=breakdown,
        )

    def _build_reasoning_trail(
        self,
        payload: MCBDecisionInput,
        final_confidence: float,
        flags: List[ValidationFlag],
        confidence_threshold: float,
        threshold_source_tier: str,
        breakdown,
    ) -> List[str]:
        trail = [
            f"Analytics confidence contributed from {payload.analytics.confidence_score:.2f}.",
            f"Marketing confidence contributed from {payload.marketing.confidence_score:.2f}.",
            f"Wholesale participants: {payload.wholesale.participant_count}; retail participants: {payload.retail.participant_count}.",
            f"Predicted price {payload.analytics.predicted_price_pkr:.2f} PKR with margin {payload.analytics.predicted_margin_percent:.2f}%.",
            f"Pricing quality component: {breakdown.pricing_quality_component:.2f}.",
            f"Demand component: {breakdown.demand_component:.2f}; competition component: {breakdown.competition_component:.2f}.",
            f"Data quality component: {breakdown.data_quality_component:.2f}; risk control component: {breakdown.risk_component:.2f}.",
            f"Marketing readiness component: {breakdown.marketing_readiness_component:.2f}.",
            f"Final confidence after penalties: {final_confidence:.2f}.",
            f"Approval threshold for {payload.category}: {confidence_threshold:.2f} ({threshold_source_tier}).",
        ]
        if flags:
            trail.append(f"Validation produced {len(flags)} flag(s): {', '.join(flag.code for flag in flags)}.")
        else:
            trail.append("No validation contradictions were detected.")
        return trail
