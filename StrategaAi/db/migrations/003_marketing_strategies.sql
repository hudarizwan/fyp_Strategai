CREATE TABLE IF NOT EXISTS marketing_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID REFERENCES pipeline_runs(id) ON DELETE SET NULL,
    product_name TEXT NOT NULL,
    category TEXT,
    strategy JSONB NOT NULL,
    analysis_status TEXT NOT NULL DEFAULT 'ok',
    confidence_score FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_marketing_strategies_product
    ON marketing_strategies(product_name);
CREATE INDEX IF NOT EXISTS idx_marketing_strategies_created_at
    ON marketing_strategies(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_marketing_strategies_status
    ON marketing_strategies(analysis_status);
