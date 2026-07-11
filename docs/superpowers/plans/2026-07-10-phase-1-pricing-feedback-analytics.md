# Phase 1 Pricing, Feedback, and Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the analytics model the primary source of truth in the UI, capture user outcome feedback, version analytics artifacts, and add category-aware confidence thresholds.

**Architecture:** We will keep the current service-based FastAPI flow, but make analytics output the canonical pricing surface and add a small feedback loop around it. Schema changes are split into separate migrations so each table can be reviewed independently before the next one lands. The frontend will get one compact outcome-capture form on the Results page plus secondary read-only surfaces on Analytics and Reports.

**Tech Stack:** FastAPI, Supabase/Postgres, React 18, TypeScript, Tailwind CSS, Recharts, Python tests with pytest, existing `ECDB` data layer.

## Global Constraints

- Do not add new scraping targets.
- Keep Made-in-China as the wholesale source and Daraz as the retail source.
- Do not implement proxy rotation, CAPTCHA solving, or other anti-bot workarounds.
- Preserve the current `pipeline_run_id` / `analytics_result_id` lineage.
- Keep phase 1 limited to pricing, analytics, feedback capture, artifact versioning, and category thresholds.

---

### Task 1: Make Analytics the Primary Price Surface

**Files:**
- Modify: `StrategaAi/StrategaAi/backend/app/services/analytics_agent.py`
- Modify: `StrategaAi/StrategaAi/frontend/salik-frontend/src/types/index.ts`
- Modify: `StrategaAi/StrategaAi/frontend/salik-frontend/src/utils/comparison.ts`
- Modify: `StrategaAi/StrategaAi/frontend/salik-frontend/src/pages/Results.tsx`
- Modify: `StrategaAi/StrategaAi/frontend/salik-frontend/src/pages/Analytics.tsx`
- Modify: `StrategaAi/StrategaAi/frontend/salik-frontend/src/pages/Reports.tsx`
- Modify: `StrategaAi/StrategaAi/backend/app/services/report_renderer.py`
- Test: `StrategaAi/StrategaAi/backend/tests/test_analytics_agent.py`
- Test: `StrategaAi/StrategaAi/backend/tests/test_reports.py`

**Interfaces:**
- Consumes: `recommended_buy_price_pkr`, `recommended_sell_price_pkr`, `expected_profit_margin`, `confidence_score`, `confidence_reason`, `analysis_metadata.pricing_sanity`
- Produces: UI copy and report payloads that treat observed min/max only as a secondary market range

- [ ] **Step 1: Add or extend tests for the response contract**

```python
def test_analytics_response_includes_pricing_sanity():
    result = agent.analyze("X", "Y", nlp_output, pipeline_run_id="run-1")
    assert "analysis_details" in result
    assert "pricing_sanity" in result["analysis_details"] or "sanity_adjustments" in result
```

- [ ] **Step 2: Run the failing test**

Run: `cd StrategaAi/StrategaAi/backend && python -m pytest tests/test_analytics_agent.py -k pricing_sanity -v`
Expected: fail until the response contract is exposed consistently.

- [ ] **Step 3: Implement the minimal contract changes**

Keep the analytics response as the canonical payload, then map that payload through the frontend type definitions and report renderer so the analytics recommendation, not the naive comparison helper, drives the headline figures.

- [ ] **Step 4: Verify the UI build and backend tests**

Run:
`cd StrategaAi/StrategaAi/backend && python -m pytest tests/test_analytics_agent.py tests/test_reports.py -v`
`cd StrategaAi/StrategaAi/frontend/salik-frontend && npm run build`

- [ ] **Step 5: Commit**

```bash
git add StrategaAi/StrategaAi/backend/app/services/analytics_agent.py StrategaAi/StrategaAi/backend/tests/test_analytics_agent.py StrategaAi/StrategaAi/backend/tests/test_reports.py StrategaAi/StrategaAi/backend/app/services/report_renderer.py StrategaAi/StrategaAi/frontend/salik-frontend/src/types/index.ts StrategaAi/StrategaAi/frontend/salik-frontend/src/utils/comparison.ts StrategaAi/StrategaAi/frontend/salik-frontend/src/pages/Results.tsx StrategaAi/StrategaAi/frontend/salik-frontend/src/pages/Analytics.tsx StrategaAi/StrategaAi/frontend/salik-frontend/src/pages/Reports.tsx
git commit -m "feat: make analytics recommendation the primary price surface"
```

**Review gate:** stop here and review the analytics-first UI before touching any schema.

---

### Task 2: Add Outcome Feedback Schema

**Files:**
- Create: `StrategaAi/StrategaAi/backend/db/migrations/004_analytics_outcome_events.sql`
- Modify: `StrategaAi/StrategaAi/backend/app/services/ecdb.py`
- Modify: `StrategaAi/StrategaAi/backend/app/api/analytics.py`
- Test: `StrategaAi/StrategaAi/backend/tests/test_feedback_capture.py`

**Interfaces:**
- Consumes: `pipeline_run_id`, `analytics_result_id`, optional `recommendation_id`, `feedback_type`, `actual_buy_price_pkr`, `actual_sell_price_pkr`, `quantity`, `notes`
- Produces: append-only outcome events linked to the original prediction

- [ ] **Step 1: Write the schema migration**

```sql
CREATE TABLE IF NOT EXISTS analytics_outcome_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID REFERENCES pipeline_runs(id) ON DELETE SET NULL,
    analytics_result_id UUID REFERENCES analytics_results(id) ON DELETE SET NULL,
    recommendation_id UUID REFERENCES recommendations(id) ON DELETE SET NULL,
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
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- [ ] **Step 2: Run the migration in Supabase and inspect the created table**

Expected: table exists with indexes and foreign keys, no destructive changes to existing tables.

- [ ] **Step 3: Add a backend feedback endpoint**

Expose a small `POST /analytics/feedback` endpoint that validates the feedback payload, stores one row in `analytics_outcome_events`, and logs a workflow event tied to the same pipeline run.

- [ ] **Step 4: Add a frontend outcome-capture panel**

Add a compact form to `Results.tsx` for:
- acted on / skipped / later updated
- actual buy price
- actual sell price
- quantity
- note

The form should be optional and dismissible, with a second entry point from history/detail views so the user can add outcomes later.

- [ ] **Step 5: Verify**

Run:
`cd StrategaAi/StrategaAi/backend && python -m pytest tests/test_feedback_capture.py -v`
`cd StrategaAi/StrategaAi/frontend/salik-frontend && npm run build`

- [ ] **Step 6: Commit**

```bash
git add StrategaAi/StrategaAi/backend/db/migrations/004_analytics_outcome_events.sql StrategaAi/StrategaAi/backend/app/services/ecdb.py StrategaAi/StrategaAi/backend/app/api/analytics.py StrategaAi/StrategaAi/backend/tests/test_feedback_capture.py StrategaAi/StrategaAi/frontend/salik-frontend/src/pages/Results.tsx StrategaAi/StrategaAi/frontend/salik-frontend/src/components/OutcomeCapturePanel.tsx StrategaAi/StrategaAi/frontend/salik-frontend/src/services/api.ts StrategaAi/StrategaAi/frontend/salik-frontend/src/types/index.ts
git commit -m "feat: add analytics outcome feedback capture"
```

**Review gate:** pause after this migration and UI review before adding any model registry logic.

---

### Task 3: Add Analytics Model Registry and Rollback Support

**Files:**
- Create: `StrategaAi/StrategaAi/backend/db/migrations/005_analytics_model_registry.sql`
- Modify: `StrategaAi/StrategaAi/backend/app/services/analytics_agent.py`
- Modify: `StrategaAi/StrategaAi/backend/app/services/ecdb.py`
- Modify: `StrategaAi/StrategaAi/backend/app/models/__init__.py`
- Test: `StrategaAi/StrategaAi/backend/tests/test_model_registry.py`

**Interfaces:**
- Consumes: training sample count, artifact filename, model hash, metrics
- Produces: an active analytics model record and retrievable historical versions

- [ ] **Step 1: Add the registry schema**

```sql
CREATE TABLE IF NOT EXISTS analytics_model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_family TEXT NOT NULL,
    version_tag TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    artifact_name TEXT NOT NULL,
    model_hash TEXT,
    source_dataset TEXT,
    sample_count INTEGER,
    evaluation_metrics JSONB,
    model_status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_at TIMESTAMPTZ
);
```

- [ ] **Step 2: Run the migration and review the table separately**

Expected: registry exists and does not alter the feedback table or recommendation tables.

- [ ] **Step 3: Make the analytics agent save versioned artifacts**

Write artifacts to a versioned filename and record the active artifact in the registry instead of overwriting `analytics_pricing_model.joblib`.

- [ ] **Step 4: Add rollback lookup**

The analytics service should load the active registry row first, with an explicit fallback to the previous active artifact if the newest one is marked bad.

- [ ] **Step 5: Verify**

Run:
`cd StrategaAi/StrategaAi/backend && python -m pytest tests/test_model_registry.py -v`

- [ ] **Step 6: Commit**

```bash
git add StrategaAi/StrategaAi/backend/db/migrations/005_analytics_model_registry.sql StrategaAi/StrategaAi/backend/app/services/analytics_agent.py StrategaAi/StrategaAi/backend/app/services/ecdb.py StrategaAi/StrategaAi/backend/tests/test_model_registry.py StrategaAi/StrategaAi/backend/app/models/__init__.py
git commit -m "feat: version analytics model artifacts"
```

**Review gate:** stop and verify rollback behavior before moving to category thresholds.

---

### Task 4: Add Category-Aware MCB Thresholds

**Files:**
- Create: `StrategaAi/StrategaAi/backend/db/migrations/006_mcb_category_thresholds.sql`
- Modify: `StrategaAi/StrategaAi/backend/app/services/mcb_decision_agent.py`
- Modify: `StrategaAi/StrategaAi/backend/app/services/ecdb.py`
- Test: `StrategaAi/StrategaAi/backend/tests/test_mcb_decision_agent.py`

**Interfaces:**
- Consumes: product category, category threshold row
- Produces: per-category approval thresholds instead of a single global `0.70`

- [ ] **Step 1: Write the threshold table**

```sql
CREATE TABLE IF NOT EXISTS mcb_category_thresholds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL UNIQUE,
    confidence_threshold NUMERIC(5,4) NOT NULL,
    notes TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- [ ] **Step 2: Run the migration and review only this table**

Expected: the threshold table is created cleanly and no existing decision code is changed yet.

- [ ] **Step 3: Load thresholds in the decision agent**

Read the category threshold row for the current product category, then fall back to the existing hardcoded threshold if no category-specific row exists.

- [ ] **Step 4: Verify**

Run:
`cd StrategaAi/StrategaAi/backend && python -m pytest tests/test_mcb_decision_agent.py -v`

- [ ] **Step 5: Commit**

```bash
git add StrategaAi/StrategaAi/backend/db/migrations/006_mcb_category_thresholds.sql StrategaAi/StrategaAi/backend/app/services/mcb_decision_agent.py StrategaAi/StrategaAi/backend/app/services/ecdb.py StrategaAi/StrategaAi/backend/tests/test_mcb_decision_agent.py
git commit -m "feat: make mcb thresholds category aware"
```

**Review gate:** confirm the per-category threshold behavior before any price-history UI work.

---

### Task 5: Expose Price History Without Overwriting Runs

**Files:**
- Modify: `StrategaAi/StrategaAi/backend/app/api/analytics.py`
- Modify: `StrategaAi/StrategaAi/backend/app/services/ecdb.py`
- Modify: `StrategaAi/StrategaAi/frontend/salik-frontend/src/pages/Analytics.tsx`
- Modify: `StrategaAi/StrategaAi/frontend/salik-frontend/src/pages/Results.tsx`
- Modify: `StrategaAi/StrategaAi/frontend/salik-frontend/src/components/PriceHistorySparkline.tsx`
- Test: `StrategaAi/StrategaAi/backend/tests/test_price_history.py`

**Interfaces:**
- Consumes: existing timestamped scrape / analytics rows
- Produces: a simple historical price series for the same product or cluster

- [ ] **Step 1: Add a read path for historical price points**

Query existing run-scoped rows by product name, category, or cluster key and return an ordered series of observed buy/sell points.

- [ ] **Step 2: Add a small sparkline or trend block to the UI**

Keep the first version minimal. The goal is to show that the system stores repeated runs rather than overwriting them.

- [ ] **Step 3: Verify**

Run:
`cd StrategaAi/StrategaAi/backend && python -m pytest tests/test_price_history.py -v`
`cd StrategaAi/StrategaAi/frontend/salik-frontend && npm run build`

- [ ] **Step 4: Commit**

```bash
git add StrategaAi/StrategaAi/backend/app/api/analytics.py StrategaAi/StrategaAi/backend/app/services/ecdb.py StrategaAi/StrategaAi/backend/tests/test_price_history.py StrategaAi/StrategaAi/frontend/salik-frontend/src/pages/Analytics.tsx StrategaAi/StrategaAi/frontend/salik-frontend/src/pages/Results.tsx StrategaAi/StrategaAi/frontend/salik-frontend/src/components/PriceHistorySparkline.tsx
git commit -m "feat: expose historical price series"
```

---

### Task 6: Final Phase-1 Verification

**Files:**
- Modify: any files touched above for polish or test fixes only

**Interfaces:**
- Consumes: the full analytics result, feedback rows, registry rows, and category thresholds
- Produces: a consistent phase-1 user flow with reviewable history and logging

- [ ] **Step 1: Run the full targeted test suite**

Run:
`cd StrategaAi/StrategaAi/backend && python -m pytest tests/test_analytics_agent.py tests/test_feedback_capture.py tests/test_model_registry.py tests/test_mcb_decision_agent.py tests/test_price_history.py tests/test_reports.py -v`

- [ ] **Step 2: Build the frontend**

Run:
`cd StrategaAi/StrategaAi/frontend/salik-frontend && npm run build`

- [ ] **Step 3: Manual smoke test**

Validate the following flow:
1. search for a product
2. inspect the analytics recommendation
3. confirm the low-sample warning appears when data is thin
4. submit an outcome feedback event
5. open the history or detail view and confirm the feedback is stored
6. confirm the report shows analytics-first figures and only labels the naive range as observed market range

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: complete phase 1 analytics, feedback, and model versioning"
```


