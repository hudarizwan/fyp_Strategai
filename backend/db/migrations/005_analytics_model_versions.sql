CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS analytics_model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name TEXT NOT NULL DEFAULT 'analytics_pricing_model',
    version_tag TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    source TEXT,
    sample_count INTEGER NOT NULL DEFAULT 0,
    training_metadata JSONB,
    metrics JSONB,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT false,
    activated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_model_versions_version_tag
    ON analytics_model_versions(version_tag);
CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_model_versions_single_active
    ON analytics_model_versions (is_active)
    WHERE is_active IS TRUE;
CREATE INDEX IF NOT EXISTS idx_analytics_model_versions_created_at
    ON analytics_model_versions(created_at DESC);
