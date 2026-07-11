CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS search_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_text TEXT NOT NULL,
    category TEXT,
    triggered_by TEXT,
    request_source TEXT,
    requested_by_user_id TEXT,
    request_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_search_requests_query ON search_requests(query_text);
CREATE INDEX IF NOT EXISTS idx_search_requests_created_at ON search_requests(created_at DESC);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    search_request_id UUID NOT NULL REFERENCES search_requests(id) ON DELETE CASCADE,
    run_status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    current_stage TEXT,
    run_config JSONB,
    error_summary TEXT,
    warning_summary TEXT,
    trigger_type TEXT,
    retry_of_run_id UUID REFERENCES pipeline_runs(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_request ON pipeline_runs(search_request_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(run_status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs(started_at DESC);

CREATE TABLE IF NOT EXISTS agent_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    agent_type TEXT,
    step_name TEXT,
    execution_status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    input_summary JSONB,
    output_summary JSONB,
    error_message TEXT,
    metrics JSONB
);

CREATE INDEX IF NOT EXISTS idx_agent_executions_run ON agent_executions(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_agent ON agent_executions(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_executions_status ON agent_executions(execution_status);

CREATE TABLE IF NOT EXISTS workflow_events (
    id BIGSERIAL PRIMARY KEY,
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    agent_execution_id UUID REFERENCES agent_executions(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    event_stage TEXT NOT NULL,
    event_status TEXT,
    message TEXT,
    event_metadata JSONB,
    records_processed_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workflow_events_run ON workflow_events(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_workflow_events_stage ON workflow_events(event_stage);
CREATE INDEX IF NOT EXISTS idx_workflow_events_created_at ON workflow_events(created_at DESC);

CREATE TABLE IF NOT EXISTS scrape_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    platform_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    search_url TEXT,
    strategy_name TEXT,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    http_status INTEGER,
    error_message TEXT,
    metadata JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_scrape_sources_run ON scrape_sources(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_scrape_sources_platform ON scrape_sources(platform_name);
CREATE INDEX IF NOT EXISTS idx_scrape_sources_source_type ON scrape_sources(source_type);

CREATE TABLE IF NOT EXISTS raw_scrape_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    scrape_source_id UUID REFERENCES scrape_sources(id) ON DELETE SET NULL,
    query_text TEXT NOT NULL,
    category TEXT,
    source_type TEXT NOT NULL,
    platform_name TEXT NOT NULL,
    raw_title TEXT,
    raw_description TEXT,
    raw_price NUMERIC(12,2),
    raw_currency TEXT,
    raw_supplier_seller TEXT,
    raw_moq INTEGER,
    raw_stock_status TEXT,
    raw_delivery_info JSONB,
    source_url TEXT,
    vendor_location TEXT,
    raw_payload JSONB NOT NULL,
    record_hash TEXT,
    scrape_status TEXT NOT NULL DEFAULT 'captured',
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_scrape_records_run ON raw_scrape_records(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_raw_scrape_records_platform ON raw_scrape_records(platform_name);
CREATE INDEX IF NOT EXISTS idx_raw_scrape_records_source_type ON raw_scrape_records(source_type);
CREATE INDEX IF NOT EXISTS idx_raw_scrape_records_hash ON raw_scrape_records(record_hash);
CREATE INDEX IF NOT EXISTS idx_raw_scrape_records_query_category ON raw_scrape_records(query_text, category);

CREATE TABLE IF NOT EXISTS normalized_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    raw_scrape_record_id UUID NOT NULL REFERENCES raw_scrape_records(id) ON DELETE CASCADE,
    validation_status TEXT NOT NULL,
    rejection_reason TEXT,
    is_accessory BOOLEAN NOT NULL DEFAULT FALSE,
    raw_title TEXT,
    cleaned_title TEXT,
    normalized_text TEXT,
    canonical_brand TEXT,
    canonical_model TEXT,
    storage_variant TEXT,
    source_type TEXT NOT NULL,
    platform_name TEXT NOT NULL,
    normalized_price_pkr NUMERIC(12,2),
    price_original NUMERIC(12,2),
    currency_original TEXT,
    normalized_supplier_seller TEXT,
    normalized_moq INTEGER,
    normalized_stock_status TEXT,
    normalized_delivery_info JSONB,
    url TEXT,
    feature_vector JSONB,
    normalization_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (raw_scrape_record_id)
);

CREATE INDEX IF NOT EXISTS idx_normalized_records_run ON normalized_records(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_normalized_records_validation ON normalized_records(validation_status);
CREATE INDEX IF NOT EXISTS idx_normalized_records_brand_model ON normalized_records(canonical_brand, canonical_model);
CREATE INDEX IF NOT EXISTS idx_normalized_records_title ON normalized_records(cleaned_title);
CREATE INDEX IF NOT EXISTS idx_normalized_records_source_type ON normalized_records(source_type);

CREATE TABLE IF NOT EXISTS product_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    cluster_key TEXT NOT NULL,
    query_text TEXT NOT NULL,
    category TEXT,
    canonical_title TEXT,
    canonical_brand TEXT,
    canonical_model TEXT,
    storage_variant TEXT,
    cluster_status TEXT NOT NULL DEFAULT 'active',
    similarity_threshold NUMERIC(5,4),
    cluster_confidence NUMERIC(5,4),
    platform_count INTEGER,
    vendor_count INTEGER,
    cluster_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (pipeline_run_id, cluster_key)
);

CREATE INDEX IF NOT EXISTS idx_product_clusters_run ON product_clusters(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_product_clusters_query_category ON product_clusters(query_text, category);
CREATE INDEX IF NOT EXISTS idx_product_clusters_brand_model ON product_clusters(canonical_brand, canonical_model);
CREATE INDEX IF NOT EXISTS idx_product_clusters_storage ON product_clusters(storage_variant);

CREATE TABLE IF NOT EXISTS cluster_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    product_cluster_id UUID NOT NULL REFERENCES product_clusters(id) ON DELETE CASCADE,
    normalized_record_id UUID NOT NULL REFERENCES normalized_records(id) ON DELETE CASCADE,
    membership_score NUMERIC(5,4),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (product_cluster_id, normalized_record_id)
);

CREATE INDEX IF NOT EXISTS idx_cluster_memberships_cluster ON cluster_memberships(product_cluster_id);
CREATE INDEX IF NOT EXISTS idx_cluster_memberships_record ON cluster_memberships(normalized_record_id);

CREATE TABLE IF NOT EXISTS record_similarity_edges (
    id BIGSERIAL PRIMARY KEY,
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    left_normalized_record_id UUID NOT NULL REFERENCES normalized_records(id) ON DELETE CASCADE,
    right_normalized_record_id UUID NOT NULL REFERENCES normalized_records(id) ON DELETE CASCADE,
    similarity_score NUMERIC(5,4) NOT NULL,
    match_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_similarity_run ON record_similarity_edges(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_similarity_left ON record_similarity_edges(left_normalized_record_id);
CREATE INDEX IF NOT EXISTS idx_similarity_right ON record_similarity_edges(right_normalized_record_id);

CREATE TABLE IF NOT EXISTS analytics_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    product_cluster_id UUID NOT NULL REFERENCES product_clusters(id) ON DELETE CASCADE,
    analysis_status TEXT NOT NULL,
    min_retail_price NUMERIC(12,2),
    max_retail_price NUMERIC(12,2),
    avg_retail_price NUMERIC(12,2),
    avg_wholesale_price NUMERIC(12,2),
    best_wholesale_price NUMERIC(12,2),
    price_spread NUMERIC(12,2),
    wholesale_candidates JSONB,
    retail_candidates JSONB,
    vendor_count INTEGER,
    platform_count INTEGER,
    estimated_optimal_buy_price NUMERIC(12,2),
    estimated_optimal_sell_price NUMERIC(12,2),
    expected_margin_percent NUMERIC(8,2),
    confidence_score NUMERIC(5,4),
    analysis_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_analytics_results_run ON analytics_results(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_analytics_results_cluster ON analytics_results(product_cluster_id);
CREATE INDEX IF NOT EXISTS idx_analytics_results_confidence ON analytics_results(confidence_score);

CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    analytics_result_id UUID NOT NULL REFERENCES analytics_results(id) ON DELETE CASCADE,
    recommendation_type TEXT NOT NULL,
    recommendation_status TEXT NOT NULL,
    recommended_buy_price_pkr NUMERIC(12,2),
    recommended_sell_price_pkr NUMERIC(12,2),
    sourcing_recommendation TEXT,
    marketing_recommendation TEXT,
    strategy_summary TEXT,
    reasoning_trace JSONB,
    confidence_score NUMERIC(5,4),
    approval_status TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_recommendations_run ON recommendations(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_analytics ON recommendations(analytics_result_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_status ON recommendations(recommendation_status);

CREATE TABLE IF NOT EXISTS dead_letter_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID REFERENCES pipeline_runs(id) ON DELETE SET NULL,
    stage_name TEXT NOT NULL,
    source_table TEXT,
    source_record_id UUID,
    failure_type TEXT,
    error_message TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dead_letter_run ON dead_letter_records(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_dead_letter_stage ON dead_letter_records(stage_name);
