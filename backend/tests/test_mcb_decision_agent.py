from app.services.mcb_decision_agent import CONFIDENCE_THRESHOLD, MCBDecisionAgent
from app.services.mcb_models import (
    AnalyticsOutput,
    CompetitorSignals,
    MarketingOutput,
    MarketStats,
    MCBDecisionInput,
)


def _make_payload() -> MCBDecisionInput:
    return MCBDecisionInput(
        product_name="HyperX Cloud III",
        category="headset",
        wholesale=MarketStats(
            avg_price_pkr=2800,
            min_price_pkr=2600,
            max_price_pkr=3200,
            participant_count=4,
        ),
        retail=MarketStats(
            avg_price_pkr=3900,
            min_price_pkr=3600,
            max_price_pkr=4300,
            participant_count=5,
        ),
        analytics=AnalyticsOutput(
            predicted_price_pkr=3850,
            predicted_margin_percent=27,
            confidence_score=0.82,
        ),
        competitors=CompetitorSignals(
            discount_intensity="medium",
            stock_out_rate=0.08,
            price_aggression="medium",
        ),
        marketing=MarketingOutput(
            segment="value gamers",
            positioning="Trusted gaming headset with proof-led comfort messaging.",
            primary_channel="daraz",
            budget_pkr=18000,
            expected_roi_percent=46,
            confidence_score=0.79,
        ),
    )


def test_mcb_approves_strong_case():
    agent = MCBDecisionAgent()
    decision = agent.decide(_make_payload())

    assert decision.final_status == "approved"
    assert decision.final_confidence >= CONFIDENCE_THRESHOLD
    assert decision.approved_strategy is not None
    assert decision.approved_price_pkr == 3850


def test_mcb_requests_reanalysis_for_low_confidence_case():
    agent = MCBDecisionAgent()
    payload = _make_payload()
    payload.analytics.confidence_score = 0.48
    payload.marketing.confidence_score = 0.44
    payload.retail.participant_count = 1

    decision = agent.decide(payload)

    assert decision.final_status == "needs_reanalysis"
    assert any(flag.code == "insufficient_retail_data" for flag in decision.validation_flags)
    assert decision.approved_strategy is None


def test_mcb_escalates_human_review_for_contradiction():
    agent = MCBDecisionAgent()
    payload = _make_payload()
    payload.analytics.predicted_price_pkr = 2500
    payload.analytics.predicted_margin_percent = -3
    payload.marketing.positioning = "Exclusive premium headset for luxury gamers."

    decision = agent.decide(payload)

    assert decision.final_status == "human_review"
    assert any(flag.severity == "critical" for flag in decision.validation_flags)
    assert decision.approved_price_pkr is None


def test_mcb_missing_data_case_is_not_auto_approved():
    agent = MCBDecisionAgent()
    payload = _make_payload()
    payload.wholesale = MarketStats(participant_count=0)
    payload.retail = MarketStats(participant_count=0)

    decision = agent.decide(payload)

    assert decision.final_status == "human_review"
    assert any(flag.code == "market_data_missing_both_sides" for flag in decision.validation_flags)


def test_mcb_flags_aggressive_market_with_weak_confidence():
    agent = MCBDecisionAgent()
    payload = _make_payload()
    payload.competitors.price_aggression = "high"
    payload.analytics.confidence_score = 0.5
    payload.marketing.confidence_score = 0.49

    decision = agent.decide(payload)

    assert any(flag.code == "aggressive_market_with_weak_confidence" for flag in decision.validation_flags)
    assert decision.final_status in {"needs_reanalysis", "human_review"}


class _ThresholdDB:
    def __init__(self, threshold_map):
        self.threshold_map = threshold_map

    def get_effective_mcb_confidence_threshold(self, category):
        return self.threshold_map.get(category, self.threshold_map.get('general_retail', 0.70))


def test_mcb_uses_category_specific_threshold_when_db_provides_one():
    low_threshold_agent = MCBDecisionAgent(db=_ThresholdDB({'headset': 0.80, 'general_retail': 0.70}))
    high_threshold_agent = MCBDecisionAgent(db=_ThresholdDB({'headset': 0.95, 'general_retail': 0.70}))
    payload = _make_payload()

    low_threshold_decision = low_threshold_agent.decide(payload)
    high_threshold_decision = high_threshold_agent.decide(payload)

    assert low_threshold_decision.final_status == 'approved'
    assert high_threshold_decision.final_status != 'approved'
    assert any('Approval threshold for headset' in line for line in low_threshold_decision.reasoning_trail)


class _TierDB:
    def __init__(self, exact=None, general=None):
        self.exact = exact
        self.general = general

    def resolve_mcb_confidence_threshold(self, category):
        if self.exact is not None:
            return {
                'confidence_threshold': self.exact,
                'threshold_source_tier': 'exact category',
                'threshold_source_category': category,
            }
        if self.general is not None:
            return {
                'confidence_threshold': self.general,
                'threshold_source_tier': 'general_retail',
                'threshold_source_category': 'general_retail',
            }
        return {
            'confidence_threshold': 0.70,
            'threshold_source_tier': 'hardcoded 0.70',
            'threshold_source_category': None,
        }


def test_mcb_exposes_threshold_source_tier_in_reasoning_trail():
    agent = MCBDecisionAgent(db=_TierDB(exact=0.80))
    decision = agent.decide(_make_payload())

    assert decision.confidence_threshold == 0.80
    assert decision.threshold_source_tier == 'exact category'
    assert any('Approval threshold for headset: 0.80 (exact category).' in line for line in decision.reasoning_trail)


def test_mcb_uses_general_retail_fallback_when_exact_category_missing():
    agent = MCBDecisionAgent(db=_TierDB(exact=None, general=0.73))
    decision = agent.decide(_make_payload())

    assert decision.confidence_threshold == 0.73
    assert decision.threshold_source_tier == 'general_retail'
    assert decision.threshold_source_category == 'general_retail'
    assert any('general_retail' in line for line in decision.reasoning_trail)
