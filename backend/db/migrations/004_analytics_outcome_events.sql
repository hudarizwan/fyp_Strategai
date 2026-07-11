CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS analytics_outcome_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID REFERENCES pipeline_runs(id) ON DELETE SET NULL,
    analytics_result_id UUID REFERENCES analytics_results(id) ON DELETE SET NULL,
    recommendation_id UUID REFERENCES recommendations(id) ON DELETE SET NULL,
    marketing_strategy_id UUID REFERENCES marketing_strategies(id) ON DELETE SET NULL,
    submitted_by_user_id TEXT,
    product_name TEXT NOT NULL,
    category TEXT,
    feedback_type TEXT NOT NULL,
    action_taken TEXT,
    actual_buy_price_pkr NUMERIC(12,2),
    actual_sell_price_pkr NUMERIC(12,2),
    quantity INTEGER,
    notes TEXT,
    source_page TEXT,
    feedback_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT analytics_outcome_events_origin_check CHECK (
        pipeline_run_id IS NOT NULL
        OR analytics_result_id IS NOT NULL
        OR recommendation_id IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS idx_analytics_outcome_events_pipeline_run
    ON analytics_outcome_events(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_analytics_outcome_events_analytics_result
    ON analytics_outcome_events(analytics_result_id);
CREATE INDEX IF NOT EXISTS idx_analytics_outcome_events_recommendation
    ON analytics_outcome_events(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_analytics_outcome_events_feedback_type
    ON analytics_outcome_events(feedback_type);
CREATE INDEX IF NOT EXISTS idx_analytics_outcome_events_created_at
    ON analytics_outcome_events(created_at DESC);
