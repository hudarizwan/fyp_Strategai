"""
ECDB (E-Commerce Database) - Supabase PostgreSQL version
Stores cleaned product data and learned category patterns.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import json
import logging
from urllib.parse import urlparse
import requests
from uuid import uuid4

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:  # pragma: no cover - depends on local PostgreSQL driver build
    psycopg2 = None
    RealDictCursor = None

try:
    import pg8000.native as pg8000_native
except Exception:  # pragma: no cover - optional pure-python fallback driver
    pg8000_native = None

from app.config.supabase_config import SUPABASE_DB_URL, SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY


logger = logging.getLogger(__name__)

REST_TIMEOUT = 15
DB_CONNECT_TIMEOUT = 5


class _PG8000CursorWrapper:
    def __init__(self, conn_wrapper: "_PG8000ConnectionWrapper"):
        self.conn_wrapper = conn_wrapper
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query: str, params: tuple = None):
        prepared = query.replace("%s", "{}")
        self.rows = self.conn_wrapper.raw.run(prepared, *(params or ())) or []
        return self

    def fetchone(self):
        if not self.rows:
            return None
        row = self.rows[0]
        return row if isinstance(row, dict) else dict(row)

    def fetchall(self):
        return [row if isinstance(row, dict) else dict(row) for row in self.rows]


class _PG8000ConnectionWrapper:
    def __init__(self, raw_conn):
        self.raw = raw_conn
        self.autocommit = False

    def cursor(self):
        return _PG8000CursorWrapper(self)

    def commit(self):
        self.raw.run("commit")

    def close(self):
        self.raw.close()


class ECDB:
    """E-Commerce Database Manager - Supabase PostgreSQL"""
    
    def __init__(self, db_url: str = None, prefer_rest: bool = True):
        self.db_url = db_url or SUPABASE_DB_URL
        self.prefer_rest = prefer_rest
        self.conn = None
        self.driver_name = None
        self.rest_base_url = SUPABASE_URL.rstrip("/") if SUPABASE_URL else ""
        rest_token = SUPABASE_SERVICE_KEY or SUPABASE_KEY
        self.rest_headers = {
            "apikey": rest_token,
            "Authorization": f"Bearer {rest_token}",
        } if rest_token else {}
        self.rest_session = requests.Session()
        self.rest_session.trust_env = False
        self._connect()
        self._init_database()
    
    def _connect(self):
        """Connect to Supabase PostgreSQL"""
        if self.prefer_rest and self.rest_base_url and self.rest_headers.get("apikey"):
            try:
                response = self.rest_session.get(
                    f"{self.rest_base_url}/rest/v1/",
                    headers=self.rest_headers,
                    timeout=REST_TIMEOUT,
                )
                response.raise_for_status()
                self.driver_name = "supabase_rest"
                logger.info("[ECDB] Connected to Supabase via REST API fallback")
                return
            except Exception as exc:
                logger.warning("[ECDB] REST fallback connection failed: %s", exc)

        if psycopg2 is not None and RealDictCursor is not None:
            try:
                self.conn = psycopg2.connect(
                    self.db_url,
                    cursor_factory=RealDictCursor,
                    connect_timeout=DB_CONNECT_TIMEOUT,
                )
                self.conn.autocommit = False
                self.driver_name = "psycopg2"
                logger.info("[ECDB] Connected to Supabase PostgreSQL via psycopg2")
                return
            except Exception as exc:
                logger.warning("[ECDB] psycopg2 connection failed: %s", exc)

        if pg8000_native is not None:
            try:
                parsed = urlparse(self.db_url)
                self.conn = _PG8000ConnectionWrapper(
                    pg8000_native.Connection(
                        user=parsed.username,
                        password=parsed.password,
                        host=parsed.hostname,
                        port=parsed.port or 5432,
                        database=(parsed.path or "/postgres").lstrip("/"),
                        ssl_context=True,
                        timeout=DB_CONNECT_TIMEOUT,
                    )
                )
                self.driver_name = "pg8000"
                logger.info("[ECDB] Connected to Supabase PostgreSQL via pg8000")
                return
            except Exception as exc:
                logger.warning("[ECDB] pg8000 connection failed: %s", exc)

        raise RuntimeError("No working PostgreSQL driver is available in the current environment")
    
    def _init_database(self):
        """Initialize database and create tables if they don't exist"""
        if self.driver_name == "supabase_rest":
            logger.info("[ECDB] REST mode active; skipping DDL initialization")
            return
        self._create_products_table()
        self._create_category_patterns_table()
        self._create_product_patterns_table()  # NEW: Brand/Model patterns
        self._create_cluster_summaries_table()
        self._ensure_product_columns()
        self._create_analytics_model_versions_table()
        self._create_mcb_category_thresholds_table()
        self._create_mcb_threshold_audit_events_table()
        self._create_analytics_outcome_events_table()
        self._create_recommendations_table()
    
    
    def _create_products_table(self):
        """Create wholesale and retail products tables (separate)"""
        self._create_wholesale_products_table()
        self._create_retail_products_table()

    def _rest_get(self, table: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        response = self.rest_session.get(
            f"{self.rest_base_url}/rest/v1/{table}",
            headers=self.rest_headers,
            params=params,
            timeout=REST_TIMEOUT,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return response.json()

    def _rest_post(self, table: str, payload: Any, upsert: bool = False) -> List[Dict[str, Any]]:
        headers = {
            **self.rest_headers,
            "Content-Type": "application/json",
            "Prefer": "return=representation" + (",resolution=merge-duplicates" if upsert else ""),
        }
        response = self.rest_session.post(
            f"{self.rest_base_url}/rest/v1/{table}",
            headers=headers,
            json=payload,
            timeout=REST_TIMEOUT,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return response.json() if response.text else []

    def _rest_patch(self, table: str, payload: Dict[str, Any], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        headers = {
            **self.rest_headers,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        response = self.rest_session.patch(
            f"{self.rest_base_url}/rest/v1/{table}",
            headers=headers,
            params=params,
            json=payload,
            timeout=REST_TIMEOUT,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return response.json() if response.text else []

    def _rest_count(self, table: str) -> int:
        response = self.rest_session.get(
            f"{self.rest_base_url}/rest/v1/{table}",
            headers={**self.rest_headers, "Prefer": "count=exact"},
            params={"select": "id", "limit": 1},
            timeout=REST_TIMEOUT,
        )
        if response.status_code == 404:
            return 0
        response.raise_for_status()
        content_range = response.headers.get("Content-Range", "0-0/0")
        total = content_range.split("/")[-1]
        return int(total) if total.isdigit() else 0

    def _new_uuid(self) -> str:
        return str(uuid4())
    
    def _create_wholesale_products_table(self):
        """Create wholesale_products table"""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS wholesale_products (
                    id SERIAL PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    
                    -- Normalized fields
                    clean_title TEXT,
                    brand TEXT,
                    model TEXT,
                    
                    -- Pricing (wholesale specific)
                    price_pkr REAL,
                    currency TEXT DEFAULT 'PKR',
                    moq INTEGER,  -- Minimum Order Quantity
                    
                    -- Vendor info
                    vendor_name TEXT,
                    vendor_location TEXT,
                    
                    -- Metadata
                    url TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_accessory BOOLEAN DEFAULT FALSE,
                    
                    -- Feature vector (JSONB)
                    feature_vector JSONB
                )
            """)
            
            # Create indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_wholesale_category ON wholesale_products(category)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_wholesale_brand ON wholesale_products(brand)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_wholesale_platform ON wholesale_products(platform)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_wholesale_scraped_at ON wholesale_products(scraped_at)")
            
            self.conn.commit()
    
    def _create_retail_products_table(self):
        """Create retail_products table"""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS retail_products (
                    id SERIAL PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    
                    -- Normalized fields
                    clean_title TEXT,
                    brand TEXT,
                    model TEXT,
                    
                    -- Pricing (retail specific)
                    price_pkr REAL,
                    currency TEXT DEFAULT 'PKR',
                    original_price_pkr REAL,  -- Before discount
                    discount_percent REAL,
                    
                    -- Seller info
                    seller_name TEXT,
                    seller_rating REAL,
                    seller_reviews_count INTEGER,
                    
                    -- Metadata
                    url TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_accessory BOOLEAN DEFAULT FALSE,
                    
                    -- Feature vector (JSONB)
                    feature_vector JSONB
                )
            """)
            
            # Create indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_retail_category ON retail_products(category)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_retail_brand ON retail_products(brand)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_retail_platform ON retail_products(platform)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_retail_scraped_at ON retail_products(scraped_at)")
            
            self.conn.commit()

    def _ensure_product_columns(self):
        """Add NLP-related columns to product tables when missing."""
        statements = [
            "ALTER TABLE wholesale_products ADD COLUMN IF NOT EXISTS cluster_id TEXT",
            "ALTER TABLE wholesale_products ADD COLUMN IF NOT EXISTS raw_title TEXT",
            "ALTER TABLE wholesale_products ADD COLUMN IF NOT EXISTS delivery_info JSONB",
            "ALTER TABLE wholesale_products ADD COLUMN IF NOT EXISTS stock_status TEXT",
            "ALTER TABLE wholesale_products ADD COLUMN IF NOT EXISTS raw_payload JSONB",
            "ALTER TABLE retail_products ADD COLUMN IF NOT EXISTS cluster_id TEXT",
            "ALTER TABLE retail_products ADD COLUMN IF NOT EXISTS raw_title TEXT",
            "ALTER TABLE retail_products ADD COLUMN IF NOT EXISTS delivery_info JSONB",
            "ALTER TABLE retail_products ADD COLUMN IF NOT EXISTS stock_status TEXT",
            "ALTER TABLE retail_products ADD COLUMN IF NOT EXISTS raw_payload JSONB",
        ]

        with self.conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)
            self.conn.commit()
    
    def _create_category_patterns_table(self):
        """Create category_patterns table"""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS category_patterns (
                    id SERIAL PRIMARY KEY,
                    category TEXT NOT NULL UNIQUE,
                    
                    -- Wholesale statistics
                    avg_wholesale_price_pkr REAL,
                    min_wholesale_price_pkr REAL,
                    max_wholesale_price_pkr REAL,
                    std_wholesale_price_pkr REAL,
                    
                    -- Retail statistics
                    avg_retail_price_pkr REAL,
                    min_retail_price_pkr REAL,
                    max_retail_price_pkr REAL,
                    std_retail_price_pkr REAL,
                    
                    -- Margin statistics
                    avg_margin_percent REAL,
                    min_margin_percent REAL,
                    max_margin_percent REAL,
                    
                    -- Competition metrics
                    avg_wholesale_vendors INTEGER,
                    avg_retail_sellers INTEGER,
                    competition_intensity REAL,
                    
                    -- Learning metadata
                    sample_count INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
    
    def _create_product_patterns_table(self):
        """Create product_patterns table for brand/model-specific patterns"""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS product_patterns (
                    id SERIAL PRIMARY KEY,
                    category TEXT NOT NULL,
                    brand TEXT,
                    model TEXT,
                    
                    -- Wholesale statistics
                    avg_wholesale_price_pkr REAL,
                    min_wholesale_price_pkr REAL,
                    max_wholesale_price_pkr REAL,
                    std_wholesale_price_pkr REAL,
                    
                    -- Retail statistics
                    avg_retail_price_pkr REAL,
                    min_retail_price_pkr REAL,
                    max_retail_price_pkr REAL,
                    std_retail_price_pkr REAL,
                    
                    -- Margin statistics
                    avg_margin_percent REAL,
                    min_margin_percent REAL,
                    max_margin_percent REAL,
                    
                    -- Learning metadata
                    sample_count INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Unique constraint on category + brand + model
                    UNIQUE(category, brand, model)
                )
            """)
            
            # Create indexes for faster lookups
            cur.execute("CREATE INDEX IF NOT EXISTS idx_product_category ON product_patterns(category)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_product_brand ON product_patterns(brand)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_product_model ON product_patterns(model)")
            
            self.conn.commit()

    def _create_cluster_summaries_table(self):
        """Create cluster summaries table for NLP output."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS product_clusters (
                    cluster_id TEXT PRIMARY KEY,
                    query_product TEXT NOT NULL,
                    category TEXT NOT NULL,
                    canonical_title TEXT,
                    brand TEXT,
                    model TEXT,
                    platform_count INTEGER,
                    vendor_count INTEGER,
                    min_retail_price REAL,
                    max_retail_price REAL,
                    avg_price REAL,
                    price_spread REAL,
                    wholesale_price_candidates JSONB,
                    retail_price_candidates JSONB,
                    traceability JSONB,
                    cluster_payload JSONB,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
    
    def _create_analytics_model_versions_table(self):
        """Create analytics_model_versions table"""
        with self.conn.cursor() as cur:
            cur.execute("""
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
                )
            """)
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_model_versions_version_tag ON analytics_model_versions(version_tag)")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_model_versions_single_active ON analytics_model_versions (is_active) WHERE is_active IS TRUE")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_analytics_model_versions_created_at ON analytics_model_versions(created_at DESC)")
            self.conn.commit()

    def _create_mcb_category_thresholds_table(self):
        """Create mcb_category_thresholds table"""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mcb_category_thresholds (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    category TEXT NOT NULL UNIQUE,
                    approval_confidence_threshold NUMERIC(4,3) NOT NULL CHECK (
                        approval_confidence_threshold >= 0
                        AND approval_confidence_threshold <= 1
                    ),
                    changed_by TEXT NOT NULL DEFAULT 'system:threshold-script',
                    change_reason TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_mcb_category_thresholds_created_at ON mcb_category_thresholds(created_at DESC)")
            self.conn.commit()

    def _create_mcb_threshold_audit_events_table(self):
        """Create mcb_threshold_audit_events table"""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mcb_threshold_audit_events (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    threshold_id UUID REFERENCES mcb_category_thresholds(id) ON DELETE SET NULL,
                    category TEXT NOT NULL,
                    old_approval_confidence_threshold NUMERIC(4,3),
                    new_approval_confidence_threshold NUMERIC(4,3) NOT NULL CHECK (
                        new_approval_confidence_threshold >= 0
                        AND new_approval_confidence_threshold <= 1
                    ),
                    changed_by TEXT NOT NULL,
                    change_reason TEXT,
                    source_script TEXT NOT NULL DEFAULT 'set_mcb_category_threshold.py',
                    action_type TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_mcb_threshold_audit_events_category ON mcb_threshold_audit_events(category)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_mcb_threshold_audit_events_created_at ON mcb_threshold_audit_events(created_at DESC)")
            self.conn.commit()

    def _create_analytics_outcome_events_table(self):
        """Create analytics_outcome_events table"""
        with self.conn.cursor() as cur:
            cur.execute("""
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
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_analytics_outcome_events_pipeline_run ON analytics_outcome_events(pipeline_run_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_analytics_outcome_events_analytics_result ON analytics_outcome_events(analytics_result_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_analytics_outcome_events_recommendation ON analytics_outcome_events(recommendation_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_analytics_outcome_events_feedback_type ON analytics_outcome_events(feedback_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_analytics_outcome_events_created_at ON analytics_outcome_events(created_at DESC)")
            self.conn.commit()

    def _create_recommendations_table(self):
        """Create recommendations table"""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id SERIAL PRIMARY KEY,
                    query_product TEXT NOT NULL,
                    category TEXT NOT NULL,
                    
                    -- Pricing decisions
                    recommended_buy_price_pkr REAL,
                    recommended_sell_price_pkr REAL,
                    expected_profit_margin REAL,
                    
                    -- Confidence
                    confidence_score REAL,
                    confidence_reason TEXT,
                    
                    -- Supporting data
                    wholesale_vendors_count INTEGER,
                    retail_sellers_count INTEGER,
                    price_spread_wholesale REAL,
                    price_spread_retail REAL,
                    
                    -- Metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Full analysis (JSONB)
                    analysis_details JSONB
                )
            """)
            self.conn.commit()
    
    # ==================== PRODUCT OPERATIONS ====================
    
    def insert_product(self, product: Dict[str, Any]) -> int:
        """Insert a product record (routes to wholesale or retail table)"""
        source_type = product.get('source_type')
        
        if source_type == 'wholesale':
            return self.insert_wholesale_product(product)
        elif source_type == 'retail':
            return self.insert_retail_product(product)
        else:
            raise ValueError(f"Invalid source_type: {source_type}. Must be 'wholesale' or 'retail'")
    
    def insert_wholesale_product(self, product: Dict[str, Any]) -> int:
        """Insert a wholesale product"""
        logger.info(
            "[ECDB] Insert wholesale start: product=%s platform=%s cluster=%s",
            product.get('product_name'),
            product.get('platform'),
            product.get('cluster_id'),
        )
        if self.driver_name == "supabase_rest":
            try:
                rows = self._rest_post("wholesale_products", {
                    "product_name": product.get('product_name'),
                    "category": product.get('category'),
                    "platform": product.get('platform'),
                    "clean_title": product.get('clean_title'),
                    "brand": product.get('brand'),
                    "model": product.get('model'),
                    "price_pkr": product.get('price_pkr'),
                    "currency": product.get('currency', 'PKR'),
                    "moq": product.get('moq'),
                    "vendor_name": product.get('vendor_name'),
                    "vendor_location": product.get('vendor_location'),
                    "url": product.get('url'),
                    "is_accessory": product.get('is_accessory', False),
                    "feature_vector": product.get('feature_vector'),
                })
                product_id = rows[0]["id"] if rows else 0
                logger.info("[ECDB] Insert wholesale success via REST: id=%s", product_id)
                return product_id
            except Exception:
                logger.exception("[ECDB] Insert wholesale failed via REST")
                raise
        with self.conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO wholesale_products (
                        product_name, category, platform,
                        clean_title, brand, model,
                        price_pkr, currency, moq,
                        vendor_name, vendor_location,
                        url, is_accessory, feature_vector,
                        cluster_id, raw_title, delivery_info, stock_status, raw_payload
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    product.get('product_name'),
                    product.get('category'),
                    product.get('platform'),
                    product.get('clean_title'),
                    product.get('brand'),
                    product.get('model'),
                    product.get('price_pkr'),
                    product.get('currency', 'PKR'),
                    product.get('moq'),
                    product.get('vendor_name'),
                    product.get('vendor_location'),
                    product.get('url'),
                    product.get('is_accessory', False),
                    json.dumps(product.get('feature_vector')) if product.get('feature_vector') else None,
                    product.get('cluster_id'),
                    product.get('raw_title'),
                    json.dumps(product.get('delivery_info')) if product.get('delivery_info') is not None else None,
                    product.get('stock_status'),
                    json.dumps(product.get('raw_payload')) if product.get('raw_payload') is not None else None,
                ))
                product_id = cur.fetchone()['id']
                self.conn.commit()
                logger.info("[ECDB] Insert wholesale success: id=%s", product_id)
                return product_id
            except Exception:
                logger.exception("[ECDB] Insert wholesale failed")
                raise
    
    def insert_retail_product(self, product: Dict[str, Any]) -> int:
        """Insert a retail product"""
        logger.info(
            "[ECDB] Insert retail start: product=%s platform=%s cluster=%s",
            product.get('product_name'),
            product.get('platform'),
            product.get('cluster_id'),
        )
        if self.driver_name == "supabase_rest":
            try:
                rows = self._rest_post("retail_products", {
                    "product_name": product.get('product_name'),
                    "category": product.get('category'),
                    "platform": product.get('platform'),
                    "clean_title": product.get('clean_title'),
                    "brand": product.get('brand'),
                    "model": product.get('model'),
                    "price_pkr": product.get('price_pkr'),
                    "currency": product.get('currency', 'PKR'),
                    "original_price_pkr": product.get('original_price_pkr'),
                    "discount_percent": product.get('discount_percent'),
                    "seller_name": product.get('seller_name') or product.get('vendor_name'),
                    "seller_rating": product.get('seller_rating'),
                    "seller_reviews_count": product.get('seller_reviews_count'),
                    "url": product.get('url'),
                    "is_accessory": product.get('is_accessory', False),
                    "feature_vector": product.get('feature_vector'),
                })
                product_id = rows[0]["id"] if rows else 0
                logger.info("[ECDB] Insert retail success via REST: id=%s", product_id)
                return product_id
            except Exception:
                logger.exception("[ECDB] Insert retail failed via REST")
                raise
        with self.conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO retail_products (
                        product_name, category, platform,
                        clean_title, brand, model,
                        price_pkr, currency, original_price_pkr, discount_percent,
                        seller_name, seller_rating, seller_reviews_count,
                        url, is_accessory, feature_vector,
                        cluster_id, raw_title, delivery_info, stock_status, raw_payload
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    product.get('product_name'),
                    product.get('category'),
                    product.get('platform'),
                    product.get('clean_title'),
                    product.get('brand'),
                    product.get('model'),
                    product.get('price_pkr'),
                    product.get('currency', 'PKR'),
                    product.get('original_price_pkr'),
                    product.get('discount_percent'),
                    product.get('seller_name') or product.get('vendor_name'),
                    product.get('seller_rating'),
                    product.get('seller_reviews_count'),
                    product.get('url'),
                    product.get('is_accessory', False),
                    json.dumps(product.get('feature_vector')) if product.get('feature_vector') else None,
                    product.get('cluster_id'),
                    product.get('raw_title'),
                    json.dumps(product.get('delivery_info')) if product.get('delivery_info') is not None else None,
                    product.get('stock_status'),
                    json.dumps(product.get('raw_payload')) if product.get('raw_payload') is not None else None,
                ))
                product_id = cur.fetchone()['id']
                self.conn.commit()
                logger.info("[ECDB] Insert retail success: id=%s", product_id)
                return product_id
            except Exception:
                logger.exception("[ECDB] Insert retail failed")
                raise

    def upsert_cluster_summary(self, cluster: Dict[str, Any]) -> str:
        """Insert or update NLP cluster summary."""
        logger.info("[ECDB] Upsert cluster start: cluster_id=%s", cluster.get("cluster_id"))
        if self.driver_name == "supabase_rest":
            try:
                rows = self._rest_post("product_clusters", {
                    "cluster_id": cluster.get("cluster_id"),
                    "query_product": cluster.get("query"),
                    "category": cluster.get("category"),
                    "canonical_title": cluster.get("canonical_title"),
                    "brand": cluster.get("brand"),
                    "model": cluster.get("model"),
                    "platform_count": cluster.get("platform_count"),
                    "vendor_count": cluster.get("vendor_count"),
                    "min_retail_price": cluster.get("min_retail_price"),
                    "max_retail_price": cluster.get("max_retail_price"),
                    "avg_price": cluster.get("avg_price"),
                    "price_spread": cluster.get("price_spread"),
                    "wholesale_price_candidates": cluster.get("wholesale_price_candidates") or [],
                    "retail_price_candidates": cluster.get("retail_price_candidates") or [],
                    "traceability": cluster.get("traceability") or [],
                    "cluster_payload": cluster,
                    "updated_at": datetime.now().isoformat(),
                }, upsert=True)
                logger.info("[ECDB] Upsert cluster success via REST: cluster_id=%s", cluster.get("cluster_id"))
                return (rows[0].get("cluster_id") if rows else cluster.get("cluster_id"))
            except Exception:
                logger.warning("[ECDB] Cluster summary persistence unavailable via REST")
                return cluster.get("cluster_id")
        with self.conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO product_clusters (
                        cluster_id, query_product, category, canonical_title,
                        brand, model, platform_count, vendor_count,
                        min_retail_price, max_retail_price, avg_price, price_spread,
                        wholesale_price_candidates, retail_price_candidates,
                        traceability, cluster_payload, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cluster_id)
                    DO UPDATE SET
                        canonical_title = EXCLUDED.canonical_title,
                        brand = EXCLUDED.brand,
                        model = EXCLUDED.model,
                        platform_count = EXCLUDED.platform_count,
                        vendor_count = EXCLUDED.vendor_count,
                        min_retail_price = EXCLUDED.min_retail_price,
                        max_retail_price = EXCLUDED.max_retail_price,
                        avg_price = EXCLUDED.avg_price,
                        price_spread = EXCLUDED.price_spread,
                        wholesale_price_candidates = EXCLUDED.wholesale_price_candidates,
                        retail_price_candidates = EXCLUDED.retail_price_candidates,
                        traceability = EXCLUDED.traceability,
                        cluster_payload = EXCLUDED.cluster_payload,
                        updated_at = EXCLUDED.updated_at
                """, (
                    cluster.get("cluster_id"),
                    cluster.get("query"),
                    cluster.get("category"),
                    cluster.get("canonical_title"),
                    cluster.get("brand"),
                    cluster.get("model"),
                    cluster.get("platform_count"),
                    cluster.get("vendor_count"),
                    cluster.get("min_retail_price"),
                    cluster.get("max_retail_price"),
                    cluster.get("avg_price"),
                    cluster.get("price_spread"),
                    json.dumps(cluster.get("wholesale_price_candidates") or []),
                    json.dumps(cluster.get("retail_price_candidates") or []),
                    json.dumps(cluster.get("traceability") or []),
                    json.dumps(cluster),
                    datetime.now(),
                ))
                self.conn.commit()
                logger.info("[ECDB] Upsert cluster success: cluster_id=%s", cluster.get("cluster_id"))
                return cluster.get("cluster_id")
            except Exception:
                logger.exception("[ECDB] Upsert cluster failed")
                raise

    def get_clusters_by_query(self, product_name: str, category: str) -> List[Dict[str, Any]]:
        """Retrieve NLP clusters for a query/category pair."""
        if self.driver_name == "supabase_rest":
            return self._rest_get("product_clusters", {
                "select": "*",
                "query_product": f"eq.{product_name}",
                "category": f"eq.{category}",
                "order": "updated_at.desc",
            })
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM product_clusters
                WHERE query_product = %s AND category = %s
                ORDER BY updated_at DESC
            """, (product_name, category))
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    
    
    def get_products_by_category(self, category: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all products in a category (from both wholesale and retail)"""
        wholesale = self.get_wholesale_products_by_category(category, limit // 2)
        retail = self.get_retail_products_by_category(category, limit // 2)
        
        # Add source_type for backward compatibility
        for p in wholesale:
            p['source_type'] = 'wholesale'
        for p in retail:
            p['source_type'] = 'retail'
        
        return wholesale + retail
    
    def get_wholesale_products_by_category(self, category: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Get wholesale products in a category"""
        if self.driver_name == "supabase_rest":
            return self._rest_get("wholesale_products", {
                "select": "*",
                "category": f"eq.{category}",
                "is_accessory": "eq.false",
                "order": "scraped_at.desc",
                "limit": limit,
            })
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM wholesale_products 
                WHERE category = %s AND is_accessory = FALSE
                ORDER BY scraped_at DESC
                LIMIT %s
            """, (category, limit))
            
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    
    def get_retail_products_by_category(self, category: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Get retail products in a category"""
        if self.driver_name == "supabase_rest":
            return self._rest_get("retail_products", {
                "select": "*",
                "category": f"eq.{category}",
                "is_accessory": "eq.false",
                "order": "scraped_at.desc",
                "limit": limit,
            })
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM retail_products 
                WHERE category = %s AND is_accessory = FALSE
                ORDER BY scraped_at DESC
                LIMIT %s
            """, (category, limit))
            
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    
    def get_products_by_query(self, product_name: str, category: str) -> List[Dict[str, Any]]:
        """Get products matching a query (from both wholesale and retail)"""
        wholesale = self.get_wholesale_products_by_query(product_name, category)
        retail = self.get_retail_products_by_query(product_name, category)
        
        # Add source_type for backward compatibility
        for p in wholesale:
            p['source_type'] = 'wholesale'
        for p in retail:
            p['source_type'] = 'retail'
        
        return wholesale + retail
    
    def get_wholesale_products_by_query(self, product_name: str, category: str) -> List[Dict[str, Any]]:
        """Get wholesale products matching a query"""
        if self.driver_name == "supabase_rest":
            return self._rest_get("wholesale_products", {
                "select": "*",
                "product_name": f"eq.{product_name}",
                "category": f"eq.{category}",
                "is_accessory": "eq.false",
                "order": "scraped_at.desc",
            })
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM wholesale_products 
                WHERE product_name = %s AND category = %s AND is_accessory = FALSE
                ORDER BY scraped_at DESC
            """, (product_name, category))
            
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    def get_retail_products_by_query(self, product_name: str, category: str) -> List[Dict[str, Any]]:
        """Get retail products matching a query"""
        if self.driver_name == "supabase_rest":
            return self._rest_get("retail_products", {
                "select": "*",
                "product_name": f"eq.{product_name}",
                "category": f"eq.{category}",
                "is_accessory": "eq.false",
                "order": "scraped_at.desc",
            })
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM retail_products 
                WHERE product_name = %s AND category = %s AND is_accessory = FALSE
                ORDER BY scraped_at DESC
            """, (product_name, category))
            
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    # Compatibility wrappers for older agent/service code.
    def get_wholesale_by_query(self, product_name: str, category: str) -> List[Dict[str, Any]]:
        """Backward-compatible alias for wholesale query lookups."""
        return self.get_wholesale_products_by_query(product_name, category)

    def get_retail_by_query(self, product_name: str, category: str) -> List[Dict[str, Any]]:
        """Backward-compatible alias for retail query lookups."""
        return self.get_retail_products_by_query(product_name, category)

    def get_wholesale_by_category(self, category: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Backward-compatible alias for wholesale category lookups."""
        return self.get_wholesale_products_by_category(category, limit)

    def get_retail_by_category(self, category: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Backward-compatible alias for retail category lookups."""
        return self.get_retail_products_by_category(category, limit)

    # ==================== PIPELINE LIFECYCLE OPERATIONS ====================

    def create_search_request(
        self,
        query_text: str,
        category: str,
        triggered_by: str = "system",
        request_source: str = "api",
        requested_by_user_id: Optional[str] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "id": self._new_uuid(),
            "query_text": query_text,
            "category": category,
            "triggered_by": triggered_by,
            "request_source": request_source,
            "requested_by_user_id": requested_by_user_id,
            "request_metadata": request_metadata or {},
        }
        rows = self._rest_post("search_requests", payload)
        return rows[0] if rows else payload

    def create_pipeline_run(
        self,
        search_request_id: str,
        run_status: str = "running",
        current_stage: str = "created",
        run_config: Optional[Dict[str, Any]] = None,
        trigger_type: str = "manual",
        retry_of_run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "id": self._new_uuid(),
            "search_request_id": search_request_id,
            "run_status": run_status,
            "current_stage": current_stage,
            "run_config": run_config or {},
            "trigger_type": trigger_type,
            "retry_of_run_id": retry_of_run_id,
        }
        rows = self._rest_post("pipeline_runs", payload)
        return rows[0] if rows else payload

    def update_pipeline_run_status(
        self,
        pipeline_run_id: str,
        run_status: str,
        current_stage: Optional[str] = None,
        error_summary: Optional[str] = None,
        warning_summary: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {"run_status": run_status}
        if current_stage is not None:
            payload["current_stage"] = current_stage
        if error_summary is not None:
            payload["error_summary"] = error_summary
        if warning_summary is not None:
            payload["warning_summary"] = warning_summary
        rows = self._rest_patch("pipeline_runs", payload, {"id": f"eq.{pipeline_run_id}"})
        return rows[0] if rows else None

    def finalize_pipeline_run(
        self,
        pipeline_run_id: str,
        run_status: str = "completed",
        current_stage: str = "completed",
        error_summary: Optional[str] = None,
        warning_summary: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        payload = {
            "run_status": run_status,
            "current_stage": current_stage,
            "completed_at": datetime.utcnow().isoformat(),
            "error_summary": error_summary,
            "warning_summary": warning_summary,
        }
        rows = self._rest_patch("pipeline_runs", payload, {"id": f"eq.{pipeline_run_id}"})
        return rows[0] if rows else None

    def create_agent_execution(
        self,
        pipeline_run_id: str,
        agent_name: str,
        agent_type: str,
        step_name: str,
        execution_status: str = "running",
        input_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "id": self._new_uuid(),
            "pipeline_run_id": pipeline_run_id,
            "agent_name": agent_name,
            "agent_type": agent_type,
            "step_name": step_name,
            "execution_status": execution_status,
            "input_summary": input_summary or {},
        }
        rows = self._rest_post("agent_executions", payload)
        return rows[0] if rows else payload

    def finalize_agent_execution(
        self,
        agent_execution_id: str,
        execution_status: str,
        output_summary: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        payload = {
            "execution_status": execution_status,
            "completed_at": datetime.utcnow().isoformat(),
            "output_summary": output_summary or {},
            "error_message": error_message,
            "metrics": metrics or {},
        }
        rows = self._rest_patch("agent_executions", payload, {"id": f"eq.{agent_execution_id}"})
        return rows[0] if rows else None

    def log_workflow_event(
        self,
        pipeline_run_id: str,
        event_type: str,
        event_stage: str,
        event_status: str,
        message: str = "",
        agent_execution_id: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
        records_processed_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload = {
            "pipeline_run_id": pipeline_run_id,
            "agent_execution_id": agent_execution_id,
            "event_type": event_type,
            "event_stage": event_stage,
            "event_status": event_status,
            "message": message,
            "event_metadata": event_metadata or {},
            "records_processed_count": records_processed_count,
        }
        rows = self._rest_post("workflow_events", payload)
        return rows[0] if rows else payload

    def log_dead_letter_record(
        self,
        stage_name: str,
        error_message: str,
        payload: Optional[Dict[str, Any]] = None,
        pipeline_run_id: Optional[str] = None,
        source_table: Optional[str] = None,
        source_record_id: Optional[str] = None,
        failure_type: str = "processing_error",
    ) -> Dict[str, Any]:
        row = {
            "id": self._new_uuid(),
            "pipeline_run_id": pipeline_run_id,
            "stage_name": stage_name,
            "source_table": source_table,
            "source_record_id": source_record_id,
            "failure_type": failure_type,
            "error_message": error_message,
            "payload": payload or {},
        }
        rows = self._rest_post("dead_letter_records", row)
        return rows[0] if rows else row

    def create_scrape_source(
        self,
        pipeline_run_id: str,
        platform_name: str,
        source_type: str,
        search_url: str = "",
        strategy_name: str = "",
        attempt_number: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "id": self._new_uuid(),
            "pipeline_run_id": pipeline_run_id,
            "platform_name": platform_name,
            "source_type": source_type,
            "search_url": search_url,
            "strategy_name": strategy_name,
            "attempt_number": attempt_number,
            "success": False,
            "metadata": metadata or {},
            "started_at": datetime.utcnow().isoformat(),
        }
        rows = self._rest_post("scrape_sources", payload)
        return rows[0] if rows else payload

    def update_scrape_source_status(
        self,
        scrape_source_id: str,
        success: bool,
        http_status: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        payload = {
            "success": success,
            "http_status": http_status,
            "error_message": error_message,
            "metadata": metadata or {},
            "completed_at": datetime.utcnow().isoformat(),
        }
        rows = self._rest_patch("scrape_sources", payload, {"id": f"eq.{scrape_source_id}"})
        return rows[0] if rows else None

    def insert_raw_scrape_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        source_type = (record.get("source_type") or "").lower()
        if source_type == "wholesale":
            return self.insert_raw_wholesale_record(record)
        if source_type == "retail":
            return self.insert_raw_retail_record(record)
        payload = {"id": self._new_uuid(), **record}
        rows = self._rest_post("raw_scrape_records", payload)
        return rows[0] if rows else payload

    def insert_raw_scrape_records_bulk(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        wholesale = [record for record in records if (record.get("source_type") or "").lower() == "wholesale"]
        retail = [record for record in records if (record.get("source_type") or "").lower() == "retail"]
        other = [record for record in records if (record.get("source_type") or "").lower() not in {"wholesale", "retail"}]

        inserted: List[Dict[str, Any]] = []
        if wholesale:
            inserted.extend(self.insert_raw_wholesale_records_bulk(wholesale))
        if retail:
            inserted.extend(self.insert_raw_retail_records_bulk(retail))
        if other:
            payload = [{"id": self._new_uuid(), **record} for record in other]
            inserted.extend(self._rest_post("raw_scrape_records", payload) or payload)
        return inserted

    def insert_normalized_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        source_type = (record.get("source_type") or "").lower()
        if source_type == "wholesale":
            return self.insert_normalized_wholesale_record(record)
        if source_type == "retail":
            return self.insert_normalized_retail_record(record)
        payload = {"id": self._new_uuid(), **record}
        rows = self._rest_post("normalized_records", payload)
        return rows[0] if rows else payload

    def insert_normalized_records_bulk(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        wholesale = [record for record in records if (record.get("source_type") or "").lower() == "wholesale"]
        retail = [record for record in records if (record.get("source_type") or "").lower() == "retail"]
        other = [record for record in records if (record.get("source_type") or "").lower() not in {"wholesale", "retail"}]

        inserted: List[Dict[str, Any]] = []
        if wholesale:
            inserted.extend(self.insert_normalized_wholesale_records_bulk(wholesale))
        if retail:
            inserted.extend(self.insert_normalized_retail_records_bulk(retail))
        if other:
            payload = [{"id": self._new_uuid(), **record} for record in other]
            inserted.extend(self._rest_post("normalized_records", payload) or payload)
        return inserted

    def insert_raw_wholesale_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"id": self._new_uuid(), **{k: v for k, v in record.items() if k != "source_type"}}
        rows = self._rest_post("raw_wholesale_records", payload)
        self._insert_legacy_raw_scrape_record({**payload, "source_type": "wholesale"})
        row = rows[0] if rows else payload
        row["source_type"] = "wholesale"
        return row

    def insert_raw_retail_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"id": self._new_uuid(), **{k: v for k, v in record.items() if k != "source_type"}}
        rows = self._rest_post("raw_retail_records", payload)
        self._insert_legacy_raw_scrape_record({**payload, "source_type": "retail"})
        row = rows[0] if rows else payload
        row["source_type"] = "retail"
        return row

    def insert_raw_wholesale_records_bulk(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        payload = [{"id": self._new_uuid(), **{k: v for k, v in record.items() if k != "source_type"}} for record in records]
        rows = self._rest_post("raw_wholesale_records", payload) or payload
        self._insert_legacy_raw_scrape_records_bulk([{**row, "source_type": "wholesale"} for row in payload])
        for row in rows:
            row["source_type"] = "wholesale"
        return rows

    def insert_raw_retail_records_bulk(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        payload = [{"id": self._new_uuid(), **{k: v for k, v in record.items() if k != "source_type"}} for record in records]
        rows = self._rest_post("raw_retail_records", payload) or payload
        self._insert_legacy_raw_scrape_records_bulk([{**row, "source_type": "retail"} for row in payload])
        for row in rows:
            row["source_type"] = "retail"
        return rows

    def insert_normalized_wholesale_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "id": self._new_uuid(),
            **{k: v for k, v in record.items() if k not in {"source_type", "raw_scrape_record_id"}},
            "raw_wholesale_record_id": record.get("raw_wholesale_record_id") or record.get("raw_scrape_record_id"),
        }
        rows = self._rest_post("normalized_wholesale_records", payload)
        self._insert_legacy_normalized_record({**payload, "source_type": "wholesale"})
        row = rows[0] if rows else payload
        row["source_type"] = "wholesale"
        return row

    def insert_normalized_retail_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "id": self._new_uuid(),
            **{k: v for k, v in record.items() if k not in {"source_type", "raw_scrape_record_id"}},
            "raw_retail_record_id": record.get("raw_retail_record_id") or record.get("raw_scrape_record_id"),
        }
        rows = self._rest_post("normalized_retail_records", payload)
        self._insert_legacy_normalized_record({**payload, "source_type": "retail"})
        row = rows[0] if rows else payload
        row["source_type"] = "retail"
        return row

    def insert_normalized_wholesale_records_bulk(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        payload = [{
            "id": self._new_uuid(),
            **{k: v for k, v in record.items() if k not in {"source_type", "raw_scrape_record_id"}},
            "raw_wholesale_record_id": record.get("raw_wholesale_record_id") or record.get("raw_scrape_record_id"),
        } for record in records]
        rows = self._rest_post("normalized_wholesale_records", payload) or payload
        self._insert_legacy_normalized_records_bulk([{**row, "source_type": "wholesale"} for row in payload])
        for row in rows:
            row["source_type"] = "wholesale"
        return rows

    def insert_normalized_retail_records_bulk(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        payload = [{
            "id": self._new_uuid(),
            **{k: v for k, v in record.items() if k not in {"source_type", "raw_scrape_record_id"}},
            "raw_retail_record_id": record.get("raw_retail_record_id") or record.get("raw_scrape_record_id"),
        } for record in records]
        rows = self._rest_post("normalized_retail_records", payload) or payload
        self._insert_legacy_normalized_records_bulk([{**row, "source_type": "retail"} for row in payload])
        for row in rows:
            row["source_type"] = "retail"
        return rows

    def _insert_legacy_raw_scrape_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        rows = self._rest_post("raw_scrape_records", record)
        return rows[0] if rows else record

    def _insert_legacy_raw_scrape_records_bulk(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not records:
            return []
        return self._rest_post("raw_scrape_records", records) or records

    def _legacy_normalized_payload(self, record: Dict[str, Any]) -> Dict[str, Any]:
        source_type = (record.get("source_type") or "").lower()
        payload = {
            "id": record.get("id") or self._new_uuid(),
            "pipeline_run_id": record.get("pipeline_run_id"),
            "raw_scrape_record_id": record.get("raw_wholesale_record_id") or record.get("raw_retail_record_id") or record.get("raw_scrape_record_id"),
            "validation_status": record.get("validation_status"),
            "rejection_reason": record.get("rejection_reason"),
            "is_accessory": record.get("is_accessory", False),
            "raw_title": record.get("raw_title"),
            "cleaned_title": record.get("cleaned_title"),
            "normalized_text": record.get("normalized_text"),
            "canonical_brand": record.get("canonical_brand"),
            "canonical_model": record.get("canonical_model"),
            "storage_variant": record.get("storage_variant"),
            "source_type": source_type,
            "platform_name": record.get("platform_name"),
            "normalized_price_pkr": record.get("normalized_price_pkr"),
            "price_original": record.get("price_original"),
            "currency_original": record.get("currency_original"),
            "normalized_supplier_seller": record.get("normalized_supplier_seller"),
            "normalized_moq": record.get("normalized_moq"),
            "normalized_stock_status": record.get("normalized_stock_status"),
            "normalized_delivery_info": record.get("normalized_delivery_info"),
            "url": record.get("url"),
            "feature_vector": record.get("feature_vector"),
            "normalization_metadata": record.get("normalization_metadata"),
        }
        return payload

    def _insert_legacy_normalized_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._legacy_normalized_payload(record)
        rows = self._rest_post("normalized_records", payload)
        return rows[0] if rows else payload

    def _insert_legacy_normalized_records_bulk(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not records:
            return []
        payload = [self._legacy_normalized_payload(record) for record in records]
        return self._rest_post("normalized_records", payload) or payload

    def insert_product_cluster(self, cluster: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"id": self._new_uuid(), **cluster}
        rows = self._rest_post("product_clusters", payload)
        return rows[0] if rows else payload

    def insert_cluster_membership(self, membership: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"id": self._new_uuid(), **membership}
        source_type = (payload.pop("source_type", "") or "").lower()
        normalized_record_id = payload.pop("normalized_record_id", None)
        if normalized_record_id:
            payload["normalized_record_id"] = normalized_record_id
        if normalized_record_id and source_type == "wholesale":
            payload["normalized_wholesale_record_id"] = normalized_record_id
        elif normalized_record_id and source_type == "retail":
            payload["normalized_retail_record_id"] = normalized_record_id
        rows = self._rest_post("cluster_memberships", payload)
        return rows[0] if rows else payload

    def insert_similarity_edge(self, edge: Dict[str, Any]) -> Dict[str, Any]:
        payload = {**edge}
        left_source_type = (payload.pop("left_source_type", "") or "").lower()
        right_source_type = (payload.pop("right_source_type", "") or "").lower()
        left_record_id = payload.pop("left_normalized_record_id", None)
        right_record_id = payload.pop("right_normalized_record_id", None)
        payload["left_normalized_record_id"] = left_record_id
        payload["right_normalized_record_id"] = right_record_id
        if left_record_id and left_source_type == "wholesale":
            payload["left_normalized_wholesale_record_id"] = left_record_id
        elif left_record_id and left_source_type == "retail":
            payload["left_normalized_retail_record_id"] = left_record_id
        if right_record_id and right_source_type == "wholesale":
            payload["right_normalized_wholesale_record_id"] = right_record_id
        elif right_record_id and right_source_type == "retail":
            payload["right_normalized_retail_record_id"] = right_record_id
        rows = self._rest_post("record_similarity_edges", payload)
        return rows[0] if rows else payload

    def insert_analytics_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"id": self._new_uuid(), **result}
        rows = self._rest_post("analytics_results", payload)
        return rows[0] if rows else payload

    def _coerce_price_history_value(self, value: Any) -> Optional[float]:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return numeric if numeric > 0 else None

    def _build_price_history_points(
        self,
        wholesale_rows: List[Dict[str, Any]],
        retail_rows: List[Dict[str, Any]],
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}

        def ingest(rows: List[Dict[str, Any]], source_type: str) -> None:
            price_key = f"{source_type}_prices"
            count_key = f"{source_type}_count"
            for index, row in enumerate(rows):
                run_key = str(row.get("pipeline_run_id") or row.get("captured_at") or f"{source_type}-{index}")
                bucket = grouped.setdefault(
                    run_key,
                    {
                        "pipeline_run_id": row.get("pipeline_run_id"),
                        "captured_at": "",
                        "wholesale_prices": [],
                        "retail_prices": [],
                        "wholesale_count": 0,
                        "retail_count": 0,
                    },
                )
                captured_at = row.get("captured_at")
                if captured_at is not None:
                    captured_text = str(captured_at)
                    if not bucket["captured_at"] or captured_text > bucket["captured_at"]:
                        bucket["captured_at"] = captured_text
                if not bucket.get("pipeline_run_id") and row.get("pipeline_run_id"):
                    bucket["pipeline_run_id"] = row.get("pipeline_run_id")
                price = self._coerce_price_history_value(
                    row.get("raw_price")
                    if row.get("raw_price") is not None
                    else row.get("price_pkr")
                    if row.get("price_pkr") is not None
                    else row.get("unit_price")
                    if row.get("unit_price") is not None
                    else row.get("price")
                )
                if price is not None:
                    bucket[price_key].append(price)
                bucket[count_key] += 1

        ingest(wholesale_rows, "wholesale")
        ingest(retail_rows, "retail")

        points: List[Dict[str, Any]] = []
        for bucket in grouped.values():
            wholesale_prices = bucket["wholesale_prices"]
            retail_prices = bucket["retail_prices"]
            points.append(
                {
                    "pipeline_run_id": bucket.get("pipeline_run_id"),
                    "captured_at": bucket.get("captured_at") or None,
                    "wholesale_count": bucket["wholesale_count"],
                    "retail_count": bucket["retail_count"],
                    "wholesale_avg_price_pkr": (sum(wholesale_prices) / len(wholesale_prices)) if wholesale_prices else 0.0,
                    "wholesale_min_price_pkr": min(wholesale_prices) if wholesale_prices else 0.0,
                    "wholesale_max_price_pkr": max(wholesale_prices) if wholesale_prices else 0.0,
                    "retail_avg_price_pkr": (sum(retail_prices) / len(retail_prices)) if retail_prices else 0.0,
                    "retail_min_price_pkr": min(retail_prices) if retail_prices else 0.0,
                    "retail_max_price_pkr": max(retail_prices) if retail_prices else 0.0,
                }
            )

        points.sort(key=lambda point: point.get("captured_at") or "")
        if limit and limit > 0:
            points = points[-limit:]
        return points

    def get_price_history(self, product_name: str, category: str, limit: int = 12) -> List[Dict[str, Any]]:
        if not product_name or not category:
            return []

        if self.driver_name == "supabase_rest":
            wholesale_rows = self._rest_get(
                "raw_wholesale_records",
                {
                    "select": "*",
                    "query_text": f"eq.{product_name}",
                    "category": f"eq.{category}",
                    "order": "captured_at.asc",
                },
            )
            retail_rows = self._rest_get(
                "raw_retail_records",
                {
                    "select": "*",
                    "query_text": f"eq.{product_name}",
                    "category": f"eq.{category}",
                    "order": "captured_at.asc",
                },
            )
            return self._build_price_history_points(wholesale_rows, retail_rows, limit=limit)

        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM raw_wholesale_records WHERE query_text = %s AND category = %s ORDER BY captured_at ASC",
                (product_name, category),
            )
            wholesale_rows = [dict(row) for row in cur.fetchall()]
            cur.execute(
                "SELECT * FROM raw_retail_records WHERE query_text = %s AND category = %s ORDER BY captured_at ASC",
                (product_name, category),
            )
            retail_rows = [dict(row) for row in cur.fetchall()]
        return self._build_price_history_points(wholesale_rows, retail_rows, limit=limit)

    def get_pipeline_run(self, pipeline_run_id: str) -> Optional[Dict[str, Any]]:
        rows = self._rest_get("pipeline_runs", {"select": "*", "id": f"eq.{pipeline_run_id}", "limit": 1})
        return rows[0] if rows else None

    def get_run_raw_records(self, pipeline_run_id: str) -> List[Dict[str, Any]]:
        wholesale = self.get_run_raw_wholesale_records(pipeline_run_id)
        retail = self.get_run_raw_retail_records(pipeline_run_id)
        return sorted(wholesale + retail, key=lambda row: row.get("captured_at") or "")

    def get_run_normalized_records(self, pipeline_run_id: str) -> List[Dict[str, Any]]:
        wholesale = self.get_run_normalized_wholesale_records(pipeline_run_id)
        retail = self.get_run_normalized_retail_records(pipeline_run_id)
        return sorted(wholesale + retail, key=lambda row: row.get("created_at") or "")

    def get_run_raw_wholesale_records(self, pipeline_run_id: str) -> List[Dict[str, Any]]:
        rows = self._rest_get("raw_wholesale_records", {"select": "*", "pipeline_run_id": f"eq.{pipeline_run_id}", "order": "captured_at.asc"})
        for row in rows:
            row["source_type"] = "wholesale"
        return rows

    def get_run_raw_retail_records(self, pipeline_run_id: str) -> List[Dict[str, Any]]:
        rows = self._rest_get("raw_retail_records", {"select": "*", "pipeline_run_id": f"eq.{pipeline_run_id}", "order": "captured_at.asc"})
        for row in rows:
            row["source_type"] = "retail"
        return rows

    def get_run_normalized_wholesale_records(self, pipeline_run_id: str) -> List[Dict[str, Any]]:
        rows = self._rest_get("normalized_wholesale_records", {"select": "*", "pipeline_run_id": f"eq.{pipeline_run_id}", "order": "created_at.asc"})
        for row in rows:
            row["source_type"] = "wholesale"
            row["raw_scrape_record_id"] = row.get("raw_wholesale_record_id")
        return rows

    def get_run_normalized_retail_records(self, pipeline_run_id: str) -> List[Dict[str, Any]]:
        rows = self._rest_get("normalized_retail_records", {"select": "*", "pipeline_run_id": f"eq.{pipeline_run_id}", "order": "created_at.asc"})
        for row in rows:
            row["source_type"] = "retail"
            row["raw_scrape_record_id"] = row.get("raw_retail_record_id")
        return rows

    def get_run_clusters(self, pipeline_run_id: str) -> List[Dict[str, Any]]:
        return self._rest_get("product_clusters", {"select": "*", "pipeline_run_id": f"eq.{pipeline_run_id}", "order": "created_at.asc"})

    def get_run_analytics(self, pipeline_run_id: str) -> List[Dict[str, Any]]:
        return self._rest_get("analytics_results", {"select": "*", "pipeline_run_id": f"eq.{pipeline_run_id}", "order": "created_at.asc"})

    def get_analytics_result(self, analytics_result_id: str) -> Optional[Dict[str, Any]]:
        rows = self._rest_get(
            "analytics_results",
            {"select": "*", "id": f"eq.{analytics_result_id}", "limit": "1"},
        )
        return rows[0] if rows else None

    def get_run_recommendations(self, pipeline_run_id: str) -> List[Dict[str, Any]]:
        return self._rest_get("recommendations", {"select": "*", "pipeline_run_id": f"eq.{pipeline_run_id}", "order": "created_at.asc"})

    def trace_pipeline_run(self, pipeline_run_id: str) -> Dict[str, Any]:
        run = self.get_pipeline_run(pipeline_run_id)
        request = None
        if run and run.get("search_request_id"):
            rows = self._rest_get("search_requests", {"select": "*", "id": f"eq.{run['search_request_id']}", "limit": 1})
            request = rows[0] if rows else None
        raw_wholesale = self.get_run_raw_wholesale_records(pipeline_run_id)
        raw_retail = self.get_run_raw_retail_records(pipeline_run_id)
        normalized_wholesale = self.get_run_normalized_wholesale_records(pipeline_run_id)
        normalized_retail = self.get_run_normalized_retail_records(pipeline_run_id)
        return {
            "request": request,
            "run": run,
            "scrape_sources": self._rest_get("scrape_sources", {"select": "*", "pipeline_run_id": f"eq.{pipeline_run_id}", "order": "started_at.asc"}),
            "raw_wholesale_records": raw_wholesale,
            "raw_retail_records": raw_retail,
            "raw_records": sorted(raw_wholesale + raw_retail, key=lambda row: row.get("captured_at") or ""),
            "normalized_wholesale_records": normalized_wholesale,
            "normalized_retail_records": normalized_retail,
            "normalized_records": sorted(normalized_wholesale + normalized_retail, key=lambda row: row.get("created_at") or ""),
            "clusters": self.get_run_clusters(pipeline_run_id),
            "cluster_memberships": self._rest_get("cluster_memberships", {"select": "*", "pipeline_run_id": f"eq.{pipeline_run_id}"}),
            "similarity_edges": self._rest_get("record_similarity_edges", {"select": "*", "pipeline_run_id": f"eq.{pipeline_run_id}"}),
            "analytics": self.get_run_analytics(pipeline_run_id),
            "recommendations": self.get_run_recommendations(pipeline_run_id),
            "workflow_events": self._rest_get("workflow_events", {"select": "*", "pipeline_run_id": f"eq.{pipeline_run_id}", "order": "created_at.asc"}),
            "agent_executions": self._rest_get("agent_executions", {"select": "*", "pipeline_run_id": f"eq.{pipeline_run_id}", "order": "started_at.asc"}),
        }
    
    # ==================== CATEGORY PATTERN OPERATIONS ====================
    
    def update_category_pattern(self, pattern: Dict[str, Any]):
        """Update or insert category pattern"""
        if self.driver_name == "supabase_rest":
            logger.info("[ECDB] category_patterns table is optional in REST mode; skipping pattern update")
            return None
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO category_patterns (
                    category,
                    avg_wholesale_price_pkr, min_wholesale_price_pkr, 
                    max_wholesale_price_pkr, std_wholesale_price_pkr,
                    avg_retail_price_pkr, min_retail_price_pkr,
                    max_retail_price_pkr, std_retail_price_pkr,
                    avg_margin_percent, min_margin_percent, max_margin_percent,
                    avg_wholesale_vendors, avg_retail_sellers,
                    competition_intensity, sample_count,
                    last_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (category) 
                DO UPDATE SET
                    avg_wholesale_price_pkr = EXCLUDED.avg_wholesale_price_pkr,
                    min_wholesale_price_pkr = EXCLUDED.min_wholesale_price_pkr,
                    max_wholesale_price_pkr = EXCLUDED.max_wholesale_price_pkr,
                    std_wholesale_price_pkr = EXCLUDED.std_wholesale_price_pkr,
                    avg_retail_price_pkr = EXCLUDED.avg_retail_price_pkr,
                    min_retail_price_pkr = EXCLUDED.min_retail_price_pkr,
                    max_retail_price_pkr = EXCLUDED.max_retail_price_pkr,
                    std_retail_price_pkr = EXCLUDED.std_retail_price_pkr,
                    avg_margin_percent = EXCLUDED.avg_margin_percent,
                    min_margin_percent = EXCLUDED.min_margin_percent,
                    max_margin_percent = EXCLUDED.max_margin_percent,
                    avg_wholesale_vendors = EXCLUDED.avg_wholesale_vendors,
                    avg_retail_sellers = EXCLUDED.avg_retail_sellers,
                    competition_intensity = EXCLUDED.competition_intensity,
                    sample_count = EXCLUDED.sample_count,
                    last_updated = EXCLUDED.last_updated
            """, (
                pattern['category'],
                pattern.get('avg_wholesale_price_pkr'),
                pattern.get('min_wholesale_price_pkr'),
                pattern.get('max_wholesale_price_pkr'),
                pattern.get('std_wholesale_price_pkr'),
                pattern.get('avg_retail_price_pkr'),
                pattern.get('min_retail_price_pkr'),
                pattern.get('max_retail_price_pkr'),
                pattern.get('std_retail_price_pkr'),
                pattern.get('avg_margin_percent'),
                pattern.get('min_margin_percent'),
                pattern.get('max_margin_percent'),
                pattern.get('avg_wholesale_vendors'),
                pattern.get('avg_retail_sellers'),
                pattern.get('competition_intensity'),
                pattern.get('sample_count'),
                datetime.now()
            ))
            self.conn.commit()
    
    def get_category_pattern(self, category: str) -> Optional[Dict[str, Any]]:
        """Get category pattern"""
        if self.driver_name == "supabase_rest":
            try:
                rows = self._rest_get("category_patterns", {
                    "select": "*",
                    "category": f"eq.{category}",
                    "limit": 1,
                })
                return rows[0] if rows else None
            except Exception as exc:
                logger.info("[ECDB] category pattern lookup unavailable in REST mode: %s", exc)
                return None
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM category_patterns WHERE category = %s
            """, (category,))
            
            row = cur.fetchone()
            return dict(row) if row else None
    
    # ==================== PRODUCT PATTERN OPERATIONS ====================
    
    def update_product_pattern(self, pattern: Dict[str, Any]):
        """Update or insert product pattern (brand/model specific)"""
        if self.driver_name == "supabase_rest":
            logger.info("[ECDB] product_patterns table is optional in REST mode; skipping product pattern update")
            return None
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO product_patterns (
                    category, brand, model,
                    avg_wholesale_price_pkr, min_wholesale_price_pkr,
                    max_wholesale_price_pkr, std_wholesale_price_pkr,
                    avg_retail_price_pkr, min_retail_price_pkr,
                    max_retail_price_pkr, std_retail_price_pkr,
                    avg_margin_percent, min_margin_percent, max_margin_percent,
                    sample_count, last_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (category, brand, model)
                DO UPDATE SET
                    avg_wholesale_price_pkr = EXCLUDED.avg_wholesale_price_pkr,
                    min_wholesale_price_pkr = EXCLUDED.min_wholesale_price_pkr,
                    max_wholesale_price_pkr = EXCLUDED.max_wholesale_price_pkr,
                    std_wholesale_price_pkr = EXCLUDED.std_wholesale_price_pkr,
                    avg_retail_price_pkr = EXCLUDED.avg_retail_price_pkr,
                    min_retail_price_pkr = EXCLUDED.min_retail_price_pkr,
                    max_retail_price_pkr = EXCLUDED.max_retail_price_pkr,
                    std_retail_price_pkr = EXCLUDED.std_retail_price_pkr,
                    avg_margin_percent = EXCLUDED.avg_margin_percent,
                    min_margin_percent = EXCLUDED.min_margin_percent,
                    max_margin_percent = EXCLUDED.max_margin_percent,
                    sample_count = EXCLUDED.sample_count,
                    last_updated = EXCLUDED.last_updated
            """, (
                pattern['category'],
                pattern.get('brand'),
                pattern.get('model'),
                pattern.get('avg_wholesale_price_pkr'),
                pattern.get('min_wholesale_price_pkr'),
                pattern.get('max_wholesale_price_pkr'),
                pattern.get('std_wholesale_price_pkr'),
                pattern.get('avg_retail_price_pkr'),
                pattern.get('min_retail_price_pkr'),
                pattern.get('max_retail_price_pkr'),
                pattern.get('std_retail_price_pkr'),
                pattern.get('avg_margin_percent'),
                pattern.get('min_margin_percent'),
                pattern.get('max_margin_percent'),
                pattern.get('sample_count'),
                datetime.now()
            ))
            self.conn.commit()
    
    def get_product_pattern(self, category: str, brand: str = None, model: str = None) -> Optional[Dict[str, Any]]:
        """
        Get product pattern with hierarchical fallback.
        
        Priority:
        1. Exact match (category + brand + model)
        2. Brand match (category + brand, model=NULL)
        3. Category match (fallback to category_patterns)
        """
        if self.driver_name == "supabase_rest":
            try:
                if brand and model:
                    rows = self._rest_get("product_patterns", {
                        "select": "*",
                        "category": f"eq.{category}",
                        "brand": f"eq.{brand}",
                        "model": f"eq.{model}",
                        "limit": 1,
                    })
                    if rows:
                        return rows[0]
                if brand:
                    rows = self._rest_get("product_patterns", {
                        "select": "*",
                        "category": f"eq.{category}",
                        "brand": f"eq.{brand}",
                        "model": "is.null",
                        "limit": 1,
                    })
                    if rows:
                        return rows[0]
            except Exception as exc:
                logger.info("[ECDB] product pattern lookup unavailable in REST mode: %s", exc)
            return self.get_category_pattern(category)
        with self.conn.cursor() as cur:
            # Try exact match first
            if brand and model:
                cur.execute("""
                    SELECT * FROM product_patterns 
                    WHERE category = %s AND brand = %s AND model = %s
                """, (category, brand, model))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
            
            # Try brand-level match
            if brand:
                cur.execute("""
                    SELECT * FROM product_patterns 
                    WHERE category = %s AND brand = %s AND model IS NULL
                """, (category, brand))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
            
            # Fallback to category pattern
            return self.get_category_pattern(category)
    
    def get_all_product_patterns(self, category: str = None) -> List[Dict[str, Any]]:
        """Get all product patterns, optionally filtered by category"""
        if self.driver_name == "supabase_rest":
            try:
                params = {"select": "*", "order": "brand.asc,model.asc"}
                if category:
                    params["category"] = f"eq.{category}"
                return self._rest_get("product_patterns", params)
            except Exception as exc:
                logger.info("[ECDB] product pattern listing unavailable in REST mode: %s", exc)
                return []
        with self.conn.cursor() as cur:
            if category:
                cur.execute("""
                    SELECT * FROM product_patterns WHERE category = %s
                    ORDER BY brand, model
                """, (category,))
            else:
                cur.execute("""
                    SELECT * FROM product_patterns
                    ORDER BY category, brand, model
                """)
            
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    
    # ==================== RECOMMENDATION OPERATIONS ====================
    
    def insert_recommendation(self, recommendation: Dict[str, Any]) -> int:
        """Insert a recommendation"""
        if recommendation.get("pipeline_run_id") and recommendation.get("analytics_result_id"):
            payload = {
                "id": recommendation.get("id") or self._new_uuid(),
                "pipeline_run_id": recommendation["pipeline_run_id"],
                "analytics_result_id": recommendation["analytics_result_id"],
                "recommendation_type": recommendation.get("recommendation_type", "pricing"),
                "recommendation_status": recommendation.get("recommendation_status", "generated"),
                "recommended_buy_price_pkr": recommendation.get("recommended_buy_price_pkr"),
                "recommended_sell_price_pkr": recommendation.get("recommended_sell_price_pkr"),
                "sourcing_recommendation": recommendation.get("sourcing_recommendation"),
                "marketing_recommendation": recommendation.get("marketing_recommendation"),
                "strategy_summary": recommendation.get("strategy_summary"),
                "reasoning_trace": recommendation.get("reasoning_trace") or recommendation.get("analysis_details"),
                "confidence_score": recommendation.get("confidence_score"),
                "approval_status": recommendation.get("approval_status", "pending"),
            }
            rows = self._rest_post("recommendations", payload)
            row = rows[0] if rows else payload
            return row.get("id", 0)
        if self.driver_name == "supabase_rest":
            rows = self._rest_post("recommendations", {
                "query_product": recommendation['query_product'],
                "category": recommendation['category'],
                "recommended_buy_price_pkr": recommendation['recommended_buy_price_pkr'],
                "recommended_sell_price_pkr": recommendation['recommended_sell_price_pkr'],
                "expected_profit_margin": recommendation['expected_profit_margin'],
                "confidence_score": recommendation['confidence_score'],
                "confidence_reason": recommendation['confidence_reason'],
                "wholesale_vendors_count": recommendation.get('wholesale_vendors_count'),
                "retail_sellers_count": recommendation.get('retail_sellers_count'),
                "price_spread_wholesale": recommendation.get('price_spread_wholesale'),
                "price_spread_retail": recommendation.get('price_spread_retail'),
                "analysis_details": recommendation.get('analysis_details'),
            })
            return rows[0]["id"] if rows else 0
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO recommendations (
                    query_product, category,
                    recommended_buy_price_pkr, recommended_sell_price_pkr,
                    expected_profit_margin,
                    confidence_score, confidence_reason,
                    wholesale_vendors_count, retail_sellers_count,
                    price_spread_wholesale, price_spread_retail,
                    analysis_details
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                recommendation['query_product'],
                recommendation['category'],
                recommendation['recommended_buy_price_pkr'],
                recommendation['recommended_sell_price_pkr'],
                recommendation['expected_profit_margin'],
                recommendation['confidence_score'],
                recommendation['confidence_reason'],
                recommendation.get('wholesale_vendors_count'),
                recommendation.get('retail_sellers_count'),
                recommendation.get('price_spread_wholesale'),
                recommendation.get('price_spread_retail'),
                json.dumps(recommendation.get('analysis_details'))
            ))
            
            rec_id = cur.fetchone()['id']
            self.conn.commit()
            return rec_id
    
    def insert_analytics_outcome_event(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "id": feedback.get("id") or self._new_uuid(),
            "pipeline_run_id": feedback.get("pipeline_run_id"),
            "analytics_result_id": feedback.get("analytics_result_id"),
            "recommendation_id": feedback.get("recommendation_id"),
            "marketing_strategy_id": feedback.get("marketing_strategy_id"),
            "submitted_by_user_id": feedback.get("submitted_by_user_id"),
            "product_name": feedback.get("product_name"),
            "category": feedback.get("category"),
            "feedback_type": feedback.get("feedback_type", "follow_up"),
            "action_taken": feedback.get("action_taken"),
            "actual_buy_price_pkr": feedback.get("actual_buy_price_pkr"),
            "actual_sell_price_pkr": feedback.get("actual_sell_price_pkr"),
            "quantity": feedback.get("quantity"),
            "notes": feedback.get("notes"),
            "source_page": feedback.get("source_page"),
            "feedback_payload": feedback.get("feedback_payload") or feedback,
        }
        if self.driver_name == "supabase_rest":
            rows = self._rest_post("analytics_outcome_events", payload)
            return rows[0] if rows else payload
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO analytics_outcome_events (
                    id, pipeline_run_id, analytics_result_id, recommendation_id,
                    marketing_strategy_id, submitted_by_user_id, product_name, category,
                    feedback_type, action_taken, actual_buy_price_pkr, actual_sell_price_pkr,
                    quantity, notes, source_page, feedback_payload
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                payload["id"],
                payload["pipeline_run_id"],
                payload["analytics_result_id"],
                payload["recommendation_id"],
                payload["marketing_strategy_id"],
                payload["submitted_by_user_id"],
                payload["product_name"],
                payload["category"],
                payload["feedback_type"],
                payload["action_taken"],
                payload["actual_buy_price_pkr"],
                payload["actual_sell_price_pkr"],
                payload["quantity"],
                payload["notes"],
                payload["source_page"],
                json.dumps(payload["feedback_payload"]),
            ))
            row = cur.fetchone()
            self.conn.commit()
            return dict(row) if row else payload

    def _analytics_model_version_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        version_payload = {
            "id": payload.get("id") or self._new_uuid(),
            "model_name": payload.get("model_name") or "analytics_pricing_model",
            "version_tag": payload.get("version_tag"),
            "artifact_path": payload.get("artifact_path"),
            "source": payload.get("source"),
            "sample_count": int(payload.get("sample_count") or 0),
            "training_metadata": payload.get("training_metadata") or {},
            "metrics": payload.get("metrics") or {},
            "notes": payload.get("notes"),
            "is_active": bool(payload.get("is_active")),
            "activated_at": payload.get("activated_at"),
        }
        return version_payload

    def _clear_active_analytics_model_versions(self, model_name: Optional[str] = None, commit: bool = True) -> None:
        if self.driver_name == "supabase_rest":
            params = {"is_active": "eq.true"}
            if model_name:
                params["model_name"] = f"eq.{model_name}"
            self._rest_patch("analytics_model_versions", {"is_active": False, "activated_at": None}, params)
            return
        with self.conn.cursor() as cur:
            if model_name:
                cur.execute("UPDATE analytics_model_versions SET is_active = false, activated_at = NULL WHERE is_active = true AND model_name = %s", (model_name,))
            else:
                cur.execute("UPDATE analytics_model_versions SET is_active = false, activated_at = NULL WHERE is_active = true")
            if commit:
                self.conn.commit()

    def insert_analytics_model_version(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        version_payload = self._analytics_model_version_payload(payload)
        if not version_payload["version_tag"]:
            raise ValueError("version_tag is required")
        if version_payload["is_active"]:
            version_payload["activated_at"] = version_payload["activated_at"] or datetime.now(timezone.utc).isoformat()
        if self.driver_name == "supabase_rest":
            if version_payload["is_active"]:
                self._clear_active_analytics_model_versions(version_payload["model_name"])
            rows = self._rest_post("analytics_model_versions", version_payload)
            return rows[0] if rows else version_payload
        with self.conn.cursor() as cur:
            if version_payload["is_active"]:
                if version_payload["model_name"]:
                    cur.execute(
                        "UPDATE analytics_model_versions SET is_active = false, activated_at = NULL WHERE is_active = true AND model_name = %s",
                        (version_payload["model_name"],),
                    )
                else:
                    cur.execute("UPDATE analytics_model_versions SET is_active = false, activated_at = NULL WHERE is_active = true")
            cur.execute("""
                INSERT INTO analytics_model_versions (
                    id, model_name, version_tag, artifact_path, source, sample_count,
                    training_metadata, metrics, notes, is_active, activated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                version_payload["id"],
                version_payload["model_name"],
                version_payload["version_tag"],
                version_payload["artifact_path"],
                version_payload["source"],
                version_payload["sample_count"],
                json.dumps(version_payload["training_metadata"]),
                json.dumps(version_payload["metrics"]),
                version_payload["notes"],
                version_payload["is_active"],
                version_payload["activated_at"],
            ))
            row = cur.fetchone()
            self.conn.commit()
            return dict(row) if row else version_payload

    def get_analytics_model_version_by_id(self, version_id: str) -> Optional[Dict[str, Any]]:
        if self.driver_name == "supabase_rest":
            rows = self._rest_get("analytics_model_versions", {"select": "*", "id": f"eq.{version_id}", "limit": "1"})
            return rows[0] if rows else None
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM analytics_model_versions WHERE id = %s LIMIT 1", (version_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_analytics_model_version_by_tag(self, version_tag: str) -> Optional[Dict[str, Any]]:
        if self.driver_name == "supabase_rest":
            rows = self._rest_get("analytics_model_versions", {"select": "*", "version_tag": f"eq.{version_tag}", "limit": "1"})
            return rows[0] if rows else None
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM analytics_model_versions WHERE version_tag = %s LIMIT 1", (version_tag,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_active_analytics_model_version(self) -> Optional[Dict[str, Any]]:
        if self.driver_name == "supabase_rest":
            rows = self._rest_get(
                "analytics_model_versions",
                {"select": "*", "is_active": "eq.true", "order": "created_at.desc", "limit": "1"},
            )
            if rows:
                return rows[0]
            fallback = self._rest_get(
                "analytics_model_versions",
                {"select": "*", "order": "created_at.desc", "limit": "1"},
            )
            return fallback[0] if fallback else None
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM analytics_model_versions WHERE is_active = true ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                return dict(row)
            cur.execute("SELECT * FROM analytics_model_versions ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None

    def get_latest_analytics_model_version(self) -> Optional[Dict[str, Any]]:
        if self.driver_name == "supabase_rest":
            rows = self._rest_get("analytics_model_versions", {"select": "*", "order": "created_at.desc", "limit": "1"})
            return rows[0] if rows else None
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM analytics_model_versions ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None

    def set_active_analytics_model_version(self, version_id: str) -> Dict[str, Any]:
        target = self.get_analytics_model_version_by_id(version_id)
        if not target:
            raise ValueError(f"Analytics model version not found: {version_id}")
        model_name = target.get("model_name") or "analytics_pricing_model"
        activated_at = datetime.now(timezone.utc).isoformat()
        if self.driver_name == "supabase_rest":
            self._clear_active_analytics_model_versions(model_name)
            rows = self._rest_patch(
                "analytics_model_versions",
                {"is_active": True, "activated_at": activated_at},
                {"id": f"eq.{version_id}"},
            )
            return rows[0] if rows else {**target, "is_active": True, "activated_at": activated_at}
        with self.conn.cursor() as cur:
            if model_name:
                cur.execute(
                    "UPDATE analytics_model_versions SET is_active = false, activated_at = NULL WHERE is_active = true AND model_name = %s",
                    (model_name,),
                )
            else:
                cur.execute("UPDATE analytics_model_versions SET is_active = false, activated_at = NULL WHERE is_active = true")
            cur.execute(
                "UPDATE analytics_model_versions SET is_active = true, activated_at = %s WHERE id = %s RETURNING *",
                (activated_at, version_id),
            )
            row = cur.fetchone()
            self.conn.commit()
            return dict(row) if row else {**target, "is_active": True, "activated_at": activated_at}

    def _normalize_mcb_threshold_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(row)
        threshold = normalized.get("approval_confidence_threshold")
        if threshold is not None:
            normalized["approval_confidence_threshold"] = float(threshold)
        return normalized

    def get_mcb_category_threshold(self, category: str) -> Optional[Dict[str, Any]]:
        if not category:
            return None
        if self.driver_name == "supabase_rest":
            rows = self._rest_get(
                "mcb_category_thresholds",
                {"select": "*", "category": f"eq.{category}", "limit": "1"},
            )
            return self._normalize_mcb_threshold_row(rows[0]) if rows else None
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM mcb_category_thresholds WHERE category = %s LIMIT 1",
                (category,),
            )
            row = cur.fetchone()
            return self._normalize_mcb_threshold_row(dict(row)) if row else None

    def get_effective_mcb_confidence_threshold(self, category: str) -> float:
        for candidate in (category, "general_retail"):
            row = self.get_mcb_category_threshold(candidate)
            if row and row.get("approval_confidence_threshold") is not None:
                return float(row["approval_confidence_threshold"])
        return 0.70

    def resolve_mcb_confidence_threshold(self, category: str) -> Dict[str, Any]:
        exact_row = self.get_mcb_category_threshold(category)
        if exact_row and exact_row.get("approval_confidence_threshold") is not None:
            return {
                "confidence_threshold": float(exact_row["approval_confidence_threshold"]),
                "threshold_source_tier": "exact category",
                "threshold_source_category": category,
            }

        fallback_row = self.get_mcb_category_threshold("general_retail")
        if fallback_row and fallback_row.get("approval_confidence_threshold") is not None:
            return {
                "confidence_threshold": float(fallback_row["approval_confidence_threshold"]),
                "threshold_source_tier": "general_retail",
                "threshold_source_category": "general_retail",
            }

        return {
            "confidence_threshold": 0.70,
            "threshold_source_tier": "hardcoded 0.70",
            "threshold_source_category": None,
        }

    def set_mcb_category_threshold(
        self,
        category: str,
        approval_confidence_threshold: float,
        changed_by: str = "system:threshold-script",
        change_reason: Optional[str] = None,
        source_script: str = "set_mcb_category_threshold.py",
    ) -> Dict[str, Any]:
        if self.driver_name == "supabase_rest":
            raise RuntimeError("MCB threshold updates require a direct PostgreSQL transaction; REST updates are not supported.")
        if not category:
            raise ValueError("category is required")
        if changed_by is None or not str(changed_by).strip():
            raise ValueError("changed_by is required")
        if approval_confidence_threshold < 0 or approval_confidence_threshold > 1:
            raise ValueError("approval_confidence_threshold must be between 0 and 1")

        threshold_value = round(float(approval_confidence_threshold), 3)
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, approval_confidence_threshold FROM mcb_category_thresholds WHERE category = %s LIMIT 1 FOR UPDATE",
                (category,),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """
                    UPDATE mcb_category_thresholds
                    SET approval_confidence_threshold = %s,
                        changed_by = %s,
                        change_reason = %s,
                        updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (
                        threshold_value,
                        changed_by,
                        change_reason,
                        existing["id"],
                    ),
                )
                row = cur.fetchone()
                old_threshold = existing.get("approval_confidence_threshold")
                action_type = "updated"
            else:
                cur.execute(
                    """
                    INSERT INTO mcb_category_thresholds (
                        category,
                        approval_confidence_threshold,
                        changed_by,
                        change_reason
                    ) VALUES (%s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        category,
                        threshold_value,
                        changed_by,
                        change_reason,
                    ),
                )
                row = cur.fetchone()
                old_threshold = None
                action_type = "inserted"

            cur.execute(
                """
                INSERT INTO mcb_threshold_audit_events (
                    threshold_id,
                    category,
                    old_approval_confidence_threshold,
                    new_approval_confidence_threshold,
                    changed_by,
                    change_reason,
                    source_script,
                    action_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    row["id"],
                    category,
                    old_threshold,
                    threshold_value,
                    changed_by,
                    change_reason,
                    source_script,
                    action_type,
                ),
            )
            self.conn.commit()
            return self._normalize_mcb_threshold_row(dict(row)) if row else {
                "id": None,
                "category": category,
                "approval_confidence_threshold": threshold_value,
                "changed_by": changed_by,
                "change_reason": change_reason,
            }

    def get_recent_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent recommendations"""
        if self.driver_name == "supabase_rest":
            return self._rest_get("recommendations", {
                "select": "*",
                "order": "created_at.desc",
                "limit": limit,
            })
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM recommendations 
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    
    # ==================== UTILITY ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if self.driver_name == "supabase_rest":
            wholesale_count = self._rest_count("wholesale_products")
            retail_count = self._rest_count("retail_products")
            category_count = self._rest_count("category_patterns")
            product_pattern_count = self._rest_count("product_patterns")
            recommendation_count = self._rest_count("recommendations")
            return {
                'total_products': wholesale_count + retail_count,
                'wholesale_products': wholesale_count,
                'retail_products': retail_count,
                'total_categories': category_count,
                'total_product_patterns': product_pattern_count,
                'total_recommendations': recommendation_count
            }
        with self.conn.cursor() as cur:
            # Count wholesale products
            cur.execute("SELECT COUNT(*) as count FROM wholesale_products")
            wholesale_count = cur.fetchone()['count']
            
            # Count retail products
            cur.execute("SELECT COUNT(*) as count FROM retail_products")
            retail_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM category_patterns")
            category_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM product_patterns")
            product_pattern_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM recommendations")
            recommendation_count = cur.fetchone()['count']
        
        return {
            'total_products': wholesale_count + retail_count,
            'wholesale_products': wholesale_count,
            'retail_products': retail_count,
            'total_categories': category_count,
            'total_product_patterns': product_pattern_count,
            'total_recommendations': recommendation_count
        }
    
    def close(self):
        """Close database connection"""
        if hasattr(self, "conn") and self.conn:
            self.conn.close()
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()

    # ------------------------------------------------------------------
    # Marketing strategies
    # ------------------------------------------------------------------

    def _normalize_marketing_strategy_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(row)
        strategy_payload = normalized.get("strategy") or {}
        meta = strategy_payload.get("_meta") if isinstance(strategy_payload, dict) else {}
        if isinstance(meta, dict):
            for key in (
                "analytics_result_id",
                "product_cluster_id",
                "version_number",
                "is_latest",
                "generation_type",
                "parent_strategy_id",
                "strategy_status",
            ):
                normalized.setdefault(key, meta.get(key))
        return normalized

    def insert_marketing_strategy(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(payload)
        analytics_result_id = payload.get("analytics_result_id")
        pipeline_run_id = payload.get("pipeline_run_id")

        latest_existing = None
        if analytics_result_id:
            try:
                latest_existing = self.get_latest_marketing_strategy_by_analytics(analytics_result_id)
            except Exception:
                latest_existing = None
        if latest_existing is None and pipeline_run_id:
            latest_existing = self.get_latest_marketing_strategy_by_pipeline(pipeline_run_id)

        if latest_existing:
            payload.setdefault("version_number", int(latest_existing.get("version_number") or 1) + 1)
            payload.setdefault("parent_strategy_id", latest_existing.get("id"))
            payload.setdefault("generation_type", "regenerate")
            if latest_existing.get("id"):
                try:
                    self._rest_patch(
                        "marketing_strategies",
                        {"is_latest": False},
                        {"id": f"eq.{latest_existing['id']}"},
                    )
                except Exception:
                    logger.info("[ECDB] marketing_strategies legacy schema detected; skipping is_latest patch")
        else:
            payload.setdefault("version_number", 1)
            payload.setdefault("generation_type", payload.get("generation_type") or "initial")

        payload.setdefault("is_latest", True)
        payload.setdefault("strategy_status", payload.get("strategy_status") or "generated")

        try:
            rows = self._rest_post("marketing_strategies", payload)
            return self._normalize_marketing_strategy_row(rows[0]) if rows else {}
        except Exception:
            strategy_payload = dict(payload.get("strategy") or {})
            strategy_payload["_meta"] = {
                "analytics_result_id": payload.get("analytics_result_id"),
                "product_cluster_id": payload.get("product_cluster_id"),
                "version_number": payload.get("version_number"),
                "is_latest": payload.get("is_latest"),
                "generation_type": payload.get("generation_type"),
                "parent_strategy_id": payload.get("parent_strategy_id"),
                "strategy_status": payload.get("strategy_status"),
            }
            fallback_payload = {
                "pipeline_run_id": payload.get("pipeline_run_id"),
                "product_name": payload.get("product_name"),
                "category": payload.get("category"),
                "strategy": strategy_payload,
                "analysis_status": payload.get("analysis_status"),
                "confidence_score": payload.get("confidence_score"),
            }
            rows = self._rest_post("marketing_strategies", fallback_payload)
            return self._normalize_marketing_strategy_row(rows[0]) if rows else {}

    def get_marketing_history(
        self,
        limit: int = 20,
        analytics_result_id: Optional[str] = None,
        pipeline_run_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params = {
            "select": "id,product_name,category,analysis_status,confidence_score,created_at,version_number,is_latest,pipeline_run_id,analytics_result_id,generation_type",
            "order": "created_at.desc",
            "limit": str(limit),
        }
        if analytics_result_id:
            params["analytics_result_id"] = f"eq.{analytics_result_id}"
        if pipeline_run_id:
            params["pipeline_run_id"] = f"eq.{pipeline_run_id}"
        try:
            rows = self._rest_get(
                "marketing_strategies",
                params,
            )
        except Exception:
            fallback_params = {
                "select": "id,product_name,category,analysis_status,confidence_score,created_at,pipeline_run_id,strategy",
                "order": "created_at.desc",
                "limit": str(limit),
            }
            if analytics_result_id and not pipeline_run_id:
                return []
            if pipeline_run_id:
                fallback_params["pipeline_run_id"] = f"eq.{pipeline_run_id}"
            rows = self._rest_get("marketing_strategies", fallback_params)
        normalized_rows = [self._normalize_marketing_strategy_row(row) for row in rows]
        if normalized_rows and (analytics_result_id or pipeline_run_id):
            for index, row in enumerate(normalized_rows):
                row["is_latest"] = index == 0
        return normalized_rows

    def get_marketing_strategy_by_id(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        rows = self._rest_get(
            "marketing_strategies",
            {"select": "*", "id": f"eq.{strategy_id}", "limit": "1"},
        )
        return self._normalize_marketing_strategy_row(rows[0]) if rows else None

    def get_latest_marketing_strategy_by_analytics(self, analytics_result_id: str) -> Optional[Dict[str, Any]]:
        try:
            rows = self._rest_get(
                "marketing_strategies",
                {
                    "select": "*",
                    "analytics_result_id": f"eq.{analytics_result_id}",
                    "is_latest": "eq.true",
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
        except Exception:
            rows = []
        if not rows:
            try:
                rows = self._rest_get(
                    "marketing_strategies",
                    {
                        "select": "*",
                        "analytics_result_id": f"eq.{analytics_result_id}",
                        "order": "created_at.desc",
                        "limit": "1",
                    },
                )
            except Exception:
                return None
        return self._normalize_marketing_strategy_row(rows[0]) if rows else None

    def get_latest_marketing_strategy_by_pipeline(self, pipeline_run_id: str) -> Optional[Dict[str, Any]]:
        try:
            rows = self._rest_get(
                "marketing_strategies",
                {
                    "select": "*",
                    "pipeline_run_id": f"eq.{pipeline_run_id}",
                    "is_latest": "eq.true",
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
        except Exception:
            rows = self._rest_get(
                "marketing_strategies",
                {
                    "select": "*",
                    "pipeline_run_id": f"eq.{pipeline_run_id}",
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
        return self._normalize_marketing_strategy_row(rows[0]) if rows else None


