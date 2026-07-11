CREATE TABLE IF NOT EXISTS marketing_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID REFERENCES pipeline_runs(id) ON DELETE SET NULL,
    analytics_result_id UUID REFERENCES analytics_results(id) ON DELETE SET NULL,
    product_cluster_id UUID REFERENCES product_clusters(id) ON DELETE SET NULL,
    product_name TEXT NOT NULL,
    category TEXT,
    strategy JSONB NOT NULL,
    analysis_status TEXT NOT NULL DEFAULT 'ok',
    strategy_status TEXT NOT NULL DEFAULT 'generated',
    version_number INTEGER NOT NULL DEFAULT 1,
    is_latest BOOLEAN NOT NULL DEFAULT TRUE,
    generation_type TEXT NOT NULL DEFAULT 'initial',
    parent_strategy_id UUID REFERENCES marketing_strategies(id) ON DELETE SET NULL,
    confidence_score FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE marketing_strategies ADD COLUMN IF NOT EXISTS analytics_result_id UUID REFERENCES analytics_results(id) ON DELETE SET NULL;
ALTER TABLE marketing_strategies ADD COLUMN IF NOT EXISTS product_cluster_id UUID REFERENCES product_clusters(id) ON DELETE SET NULL;
ALTER TABLE marketing_strategies ADD COLUMN IF NOT EXISTS strategy_status TEXT NOT NULL DEFAULT 'generated';
ALTER TABLE marketing_strategies ADD COLUMN IF NOT EXISTS version_number INTEGER NOT NULL DEFAULT 1;
ALTER TABLE marketing_strategies ADD COLUMN IF NOT EXISTS is_latest BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE marketing_strategies ADD COLUMN IF NOT EXISTS generation_type TEXT NOT NULL DEFAULT 'initial';
ALTER TABLE marketing_strategies ADD COLUMN IF NOT EXISTS parent_strategy_id UUID REFERENCES marketing_strategies(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_marketing_strategies_product
    ON marketing_strategies(product_name);
CREATE INDEX IF NOT EXISTS idx_marketing_strategies_created_at
    ON marketing_strategies(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_marketing_strategies_status
    ON marketing_strategies(analysis_status);
CREATE INDEX IF NOT EXISTS idx_marketing_strategies_pipeline_run
    ON marketing_strategies(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_marketing_strategies_analytics
    ON marketing_strategies(analytics_result_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_marketing_strategies_latest
    ON marketing_strategies(analytics_result_id, is_latest);
