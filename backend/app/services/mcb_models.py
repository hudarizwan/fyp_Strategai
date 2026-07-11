"""Schemas for the deterministic MCB decision agent."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


DecisionStatus = Literal["approved", "needs_reanalysis", "human_review"]
FlagSeverity = Literal["info", "warning", "critical"]
CompetitionLevel = Literal["low", "medium", "high"]


class MarketStats(BaseModel):
    avg_price_pkr: Optional[float] = None
    min_price_pkr: Optional[float] = None
    max_price_pkr: Optional[float] = None
    participant_count: int = 0


class AnalyticsOutput(BaseModel):
    predicted_price_pkr: float
    predicted_margin_percent: float
    confidence_score: float = Field(ge=0.0, le=1.0)
    gross_profit_pkr: float = 0.0
    net_profit_pkr: float = 0.0
    roi_percent: float = 0.0
    break_even_sell_price_pkr: float = 0.0
    quality_band: str = "limited"
    demand_score: float = 0.0
    competition_score: float = 0.0
    data_quality_score: float = 0.0
    risk_score: float = 0.0
    market_saturation_score: float = 0.0


class CompetitorSignals(BaseModel):
    discount_intensity: CompetitionLevel = "medium"
    stock_out_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    price_aggression: CompetitionLevel = "medium"


class MarketingOutput(BaseModel):
    segment: Optional[str] = None
    positioning: Optional[str] = None
    primary_channel: Optional[str] = None
    budget_pkr: Optional[float] = Field(default=None, ge=0.0)
    expected_roi_percent: Optional[float] = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    channel_count: int = 0
    launch_scope: str = "standard"
    evidence_coverage_score: float = 0.0
    quality_band: str = "limited"


class MCBDecisionInput(BaseModel):
    product_name: str
    category: str
    wholesale: MarketStats
    retail: MarketStats
    analytics: AnalyticsOutput
    competitors: CompetitorSignals = Field(default_factory=CompetitorSignals)
    marketing: MarketingOutput


class ValidationFlag(BaseModel):
    code: str
    severity: FlagSeverity
    message: str
    field: Optional[str] = None


class ScoreBreakdown(BaseModel):
    analytics_component: float
    marketing_component: float
    data_completeness_component: float
    market_coverage_component: float
    penalty_component: float
    pricing_quality_component: float = 0.0
    demand_component: float = 0.0
    competition_component: float = 0.0
    data_quality_component: float = 0.0
    risk_component: float = 0.0
    marketing_readiness_component: float = 0.0


class ApprovedStrategy(BaseModel):
    segment: str
    positioning: str
    primary_channel: str
    budget_pkr: Optional[float] = None
    expected_roi_percent: Optional[float] = None


class MCBDecisionOutput(BaseModel):
    final_status: DecisionStatus
    final_confidence: float = Field(ge=0.0, le=1.0)
    confidence_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    threshold_source_tier: str = "hardcoded 0.70"
    threshold_source_category: Optional[str] = None
    approved_price_pkr: Optional[float] = None
    approved_margin_percent: Optional[float] = None
    approved_strategy: Optional[ApprovedStrategy] = None
    validation_flags: List[ValidationFlag]
    reasoning_trail: List[str]
    next_action: str
    score_breakdown: ScoreBreakdown
