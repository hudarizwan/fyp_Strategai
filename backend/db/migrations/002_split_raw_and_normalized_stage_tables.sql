CREATE TABLE IF NOT EXISTS raw_wholesale_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    scrape_source_id UUID REFERENCES scrape_sources(id) ON DELETE SET NULL,
    query_text TEXT NOT NULL,
    category TEXT,
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

CREATE INDEX IF NOT EXISTS idx_raw_wholesale_records_run ON raw_wholesale_records(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_raw_wholesale_records_platform ON raw_wholesale_records(platform_name);
CREATE INDEX IF NOT EXISTS idx_raw_wholesale_records_hash ON raw_wholesale_records(record_hash);
CREATE INDEX IF NOT EXISTS idx_raw_wholesale_records_query_category ON raw_wholesale_records(query_text, category);

CREATE TABLE IF NOT EXISTS raw_retail_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    scrape_source_id UUID REFERENCES scrape_sources(id) ON DELETE SET NULL,
    query_text TEXT NOT NULL,
    category TEXT,
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

CREATE INDEX IF NOT EXISTS idx_raw_retail_records_run ON raw_retail_records(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_raw_retail_records_platform ON raw_retail_records(platform_name);
CREATE INDEX IF NOT EXISTS idx_raw_retail_records_hash ON raw_retail_records(record_hash);
CREATE INDEX IF NOT EXISTS idx_raw_retail_records_query_category ON raw_retail_records(query_text, category);

CREATE TABLE IF NOT EXISTS normalized_wholesale_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    raw_wholesale_record_id UUID NOT NULL REFERENCES raw_wholesale_records(id) ON DELETE CASCADE,
    validation_status TEXT NOT NULL,
    rejection_reason TEXT,
    is_accessory BOOLEAN NOT NULL DEFAULT FALSE,
    raw_title TEXT,
    cleaned_title TEXT,
    normalized_text TEXT,
    canonical_brand TEXT,
    canonical_model TEXT,
    storage_variant TEXT,
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
    UNIQUE (raw_wholesale_record_id)
);

CREATE INDEX IF NOT EXISTS idx_normalized_wholesale_records_run ON normalized_wholesale_records(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_normalized_wholesale_records_validation ON normalized_wholesale_records(validation_status);
CREATE INDEX IF NOT EXISTS idx_normalized_wholesale_records_brand_model ON normalized_wholesale_records(canonical_brand, canonical_model);
CREATE INDEX IF NOT EXISTS idx_normalized_wholesale_records_title ON normalized_wholesale_records(cleaned_title);

CREATE TABLE IF NOT EXISTS normalized_retail_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    raw_retail_record_id UUID NOT NULL REFERENCES raw_retail_records(id) ON DELETE CASCADE,
    validation_status TEXT NOT NULL,
    rejection_reason TEXT,
    is_accessory BOOLEAN NOT NULL DEFAULT FALSE,
    raw_title TEXT,
    cleaned_title TEXT,
    normalized_text TEXT,
    canonical_brand TEXT,
    canonical_model TEXT,
    storage_variant TEXT,
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
    UNIQUE (raw_retail_record_id)
);

CREATE INDEX IF NOT EXISTS idx_normalized_retail_records_run ON normalized_retail_records(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_normalized_retail_records_validation ON normalized_retail_records(validation_status);
CREATE INDEX IF NOT EXISTS idx_normalized_retail_records_brand_model ON normalized_retail_records(canonical_brand, canonical_model);
CREATE INDEX IF NOT EXISTS idx_normalized_retail_records_title ON normalized_retail_records(cleaned_title);

ALTER TABLE cluster_memberships
    ADD COLUMN IF NOT EXISTS normalized_wholesale_record_id UUID REFERENCES normalized_wholesale_records(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS normalized_retail_record_id UUID REFERENCES normalized_retail_records(id) ON DELETE CASCADE;

ALTER TABLE cluster_memberships
    ALTER COLUMN normalized_record_id DROP NOT NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'cluster_memberships'
          AND column_name = 'normalized_record_id'
    ) THEN
        UPDATE cluster_memberships cm
        SET normalized_wholesale_record_id = nr.id
        FROM normalized_records nr
        WHERE cm.normalized_record_id = nr.id
          AND nr.source_type = 'wholesale'
          AND cm.normalized_wholesale_record_id IS NULL;

        UPDATE cluster_memberships cm
        SET normalized_retail_record_id = nr.id
        FROM normalized_records nr
        WHERE cm.normalized_record_id = nr.id
          AND nr.source_type = 'retail'
          AND cm.normalized_retail_record_id IS NULL;
    END IF;
END $$;

ALTER TABLE cluster_memberships
    DROP CONSTRAINT IF EXISTS cluster_memberships_record_ref_check;

ALTER TABLE cluster_memberships
    ADD CONSTRAINT cluster_memberships_record_ref_check
    CHECK (
        ((normalized_wholesale_record_id IS NOT NULL)::int +
         (normalized_retail_record_id IS NOT NULL)::int +
         (normalized_record_id IS NOT NULL)::int) = 1
    );

CREATE UNIQUE INDEX IF NOT EXISTS idx_cluster_memberships_wholesale_unique
    ON cluster_memberships(product_cluster_id, normalized_wholesale_record_id)
    WHERE normalized_wholesale_record_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_cluster_memberships_retail_unique
    ON cluster_memberships(product_cluster_id, normalized_retail_record_id)
    WHERE normalized_retail_record_id IS NOT NULL;

ALTER TABLE record_similarity_edges
    ADD COLUMN IF NOT EXISTS left_normalized_wholesale_record_id UUID REFERENCES normalized_wholesale_records(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS left_normalized_retail_record_id UUID REFERENCES normalized_retail_records(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS right_normalized_wholesale_record_id UUID REFERENCES normalized_wholesale_records(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS right_normalized_retail_record_id UUID REFERENCES normalized_retail_records(id) ON DELETE CASCADE;

ALTER TABLE record_similarity_edges
    ALTER COLUMN left_normalized_record_id DROP NOT NULL,
    ALTER COLUMN right_normalized_record_id DROP NOT NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'record_similarity_edges'
          AND column_name = 'left_normalized_record_id'
    ) THEN
        UPDATE record_similarity_edges rse
        SET left_normalized_wholesale_record_id = nr.id
        FROM normalized_records nr
        WHERE rse.left_normalized_record_id = nr.id
          AND nr.source_type = 'wholesale'
          AND rse.left_normalized_wholesale_record_id IS NULL;

        UPDATE record_similarity_edges rse
        SET left_normalized_retail_record_id = nr.id
        FROM normalized_records nr
        WHERE rse.left_normalized_record_id = nr.id
          AND nr.source_type = 'retail'
          AND rse.left_normalized_retail_record_id IS NULL;

        UPDATE record_similarity_edges rse
        SET right_normalized_wholesale_record_id = nr.id
        FROM normalized_records nr
        WHERE rse.right_normalized_record_id = nr.id
          AND nr.source_type = 'wholesale'
          AND rse.right_normalized_wholesale_record_id IS NULL;

        UPDATE record_similarity_edges rse
        SET right_normalized_retail_record_id = nr.id
        FROM normalized_records nr
        WHERE rse.right_normalized_record_id = nr.id
          AND nr.source_type = 'retail'
          AND rse.right_normalized_retail_record_id IS NULL;
    END IF;
END $$;

INSERT INTO raw_wholesale_records (
    id, pipeline_run_id, scrape_source_id, query_text, category, platform_name,
    raw_title, raw_description, raw_price, raw_currency, raw_supplier_seller,
    raw_moq, raw_stock_status, raw_delivery_info, source_url, vendor_location,
    raw_payload, record_hash, scrape_status, captured_at
)
SELECT
    id, pipeline_run_id, scrape_source_id, query_text, category, platform_name,
    raw_title, raw_description, raw_price, raw_currency, raw_supplier_seller,
    raw_moq, raw_stock_status, raw_delivery_info, source_url, vendor_location,
    raw_payload, record_hash, scrape_status, captured_at
FROM raw_scrape_records
WHERE source_type = 'wholesale'
ON CONFLICT (id) DO NOTHING;

INSERT INTO raw_retail_records (
    id, pipeline_run_id, scrape_source_id, query_text, category, platform_name,
    raw_title, raw_description, raw_price, raw_currency, raw_supplier_seller,
    raw_moq, raw_stock_status, raw_delivery_info, source_url, vendor_location,
    raw_payload, record_hash, scrape_status, captured_at
)
SELECT
    id, pipeline_run_id, scrape_source_id, query_text, category, platform_name,
    raw_title, raw_description, raw_price, raw_currency, raw_supplier_seller,
    raw_moq, raw_stock_status, raw_delivery_info, source_url, vendor_location,
    raw_payload, record_hash, scrape_status, captured_at
FROM raw_scrape_records
WHERE source_type = 'retail'
ON CONFLICT (id) DO NOTHING;

INSERT INTO normalized_wholesale_records (
    id, pipeline_run_id, raw_wholesale_record_id, validation_status, rejection_reason,
    is_accessory, raw_title, cleaned_title, normalized_text, canonical_brand,
    canonical_model, storage_variant, platform_name, normalized_price_pkr,
    price_original, currency_original, normalized_supplier_seller, normalized_moq,
    normalized_stock_status, normalized_delivery_info, url, feature_vector,
    normalization_metadata, created_at
)
SELECT
    nr.id, nr.pipeline_run_id, nr.raw_scrape_record_id, nr.validation_status, nr.rejection_reason,
    nr.is_accessory, nr.raw_title, nr.cleaned_title, nr.normalized_text, nr.canonical_brand,
    nr.canonical_model, nr.storage_variant, nr.platform_name, nr.normalized_price_pkr,
    nr.price_original, nr.currency_original, nr.normalized_supplier_seller, nr.normalized_moq,
    nr.normalized_stock_status, nr.normalized_delivery_info, nr.url, nr.feature_vector,
    nr.normalization_metadata, nr.created_at
FROM normalized_records nr
JOIN raw_scrape_records rsr ON rsr.id = nr.raw_scrape_record_id
WHERE rsr.source_type = 'wholesale'
ON CONFLICT (id) DO NOTHING;

INSERT INTO normalized_retail_records (
    id, pipeline_run_id, raw_retail_record_id, validation_status, rejection_reason,
    is_accessory, raw_title, cleaned_title, normalized_text, canonical_brand,
    canonical_model, storage_variant, platform_name, normalized_price_pkr,
    price_original, currency_original, normalized_supplier_seller, normalized_moq,
    normalized_stock_status, normalized_delivery_info, url, feature_vector,
    normalization_metadata, created_at
)
SELECT
    nr.id, nr.pipeline_run_id, nr.raw_scrape_record_id, nr.validation_status, nr.rejection_reason,
    nr.is_accessory, nr.raw_title, nr.cleaned_title, nr.normalized_text, nr.canonical_brand,
    nr.canonical_model, nr.storage_variant, nr.platform_name, nr.normalized_price_pkr,
    nr.price_original, nr.currency_original, nr.normalized_supplier_seller, nr.normalized_moq,
    nr.normalized_stock_status, nr.normalized_delivery_info, nr.url, nr.feature_vector,
    nr.normalization_metadata, nr.created_at
FROM normalized_records nr
JOIN raw_scrape_records rsr ON rsr.id = nr.raw_scrape_record_id
WHERE rsr.source_type = 'retail'
ON CONFLICT (id) DO NOTHING;
