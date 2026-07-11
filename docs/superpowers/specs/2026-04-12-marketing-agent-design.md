# Marketing Agent — Design Specification
**Date:** 2026-04-12
**Project:** StrategAI
**Status:** Approved

---

## 1. Overview

The Marketing Agent is a new pipeline stage in StrategAI that converts structured pricing intelligence (from the existing analytics pipeline) into a fully reasoned, evidence-backed go-to-market strategy for Pakistan e-commerce.

It is triggered on-demand from the Results page after the user has already seen their scrape + analytics results. The generated strategy is persisted in Supabase and viewable both immediately and in a history page.

---

## 2. Trigger & Integration Point

- **Trigger:** "Generate Marketing Strategy" button on `Results.tsx`
- **Input source:** `sessionStorage.scraperResult` + `sessionStorage.analyticsRecommendation`
- **Not** part of the auto-run pipeline — user explicitly initiates
- **Output destination:** Supabase `marketing_strategies` table + `sessionStorage.marketingStrategy` + `/marketing` page

---

## 3. Architecture

```
Results page
    │
    └─ "Generate Marketing Strategy" button
            │
            POST /marketing/generate
            { product_name, category, analytics_result, scraper_result, pipeline_run_id? }
            │
            MarketingAgent (app/services/marketing_agent.py)
            │
            ├─ 1. Perceive       — validate + structure input (Python only)
            ├─ 2. Enrich         — extract competitors/context from scraper_result (Python only)
            ├─ 3. Generate       — Ollama llama3.1:8b call #1 → raw strategy JSON
            ├─ 4. Validate       — Python: schema check, price/margin sanity, evidence check
            ├─ 5. Critic         — Ollama llama3.1:8b call #2 → refined strategy
            └─ 6. Store          — insert to marketing_strategies (Supabase via ECDB)
                    │
                    return full strategy JSON
```

---

## 4. New Files

| File | Purpose |
|------|---------|
| `app/services/marketing_agent.py` | MarketingAgent class with full lifecycle |
| `app/api/marketing.py` | FastAPI router: POST /marketing/generate, GET /marketing/history |
| `db/migrations/003_marketing_strategies.sql` | New Supabase table |
| `frontend/salik-frontend/src/pages/Marketing.tsx` | Strategy display page |
| `frontend/salik-frontend/src/pages/MarketingHistory.tsx` | History list page |

## 5. Modified Files

| File | Change |
|------|--------|
| `app/main.py` | Register marketing router at `/marketing` |
| `frontend/salik-frontend/src/App.tsx` | Add routes `/marketing` and `/marketing/history` |
| `frontend/salik-frontend/src/pages/Results.tsx` | Add "Generate Marketing Strategy" button |
| `frontend/salik-frontend/src/components/Navbar.tsx` | Add Marketing + History nav links |
| `frontend/salik-frontend/src/services/api.ts` | Add `marketingService.generate()` and `marketingService.getHistory()` |

---

## 6. Agent Lifecycle (Detailed)

### Step 1 — Perceive (Python)
- Validate all required fields: `product_name`, `category`, `analytics_result`
- Check: prices > 0, `confidence_score` in [0,1], `expected_profit_margin` in [0,100], vendor/seller counts are integers ≥ 0
- Raise `ValueError` early if input is unusable
- Output: clean `perceived` dict

### Step 2 — Enrich (Python, no LLM)
Extract from `scraper_result` without any model call:
- **Competitor names + price band** from retail listings (platform, seller, list_price)
- **Platform distribution** (count per platform)
- **MOQ range + origin countries** from wholesale listings
- **Review themes** from `detail.highlights` in retail items (sanitised — strip any embedded instructions)
- Output: `enriched_context` dict

### Step 3 — Generate (Ollama call #1)
- Uses `ollama` Python library hitting `http://localhost:11434`
- Model: `llama3.1:8b`
- System prompt: Senior marketing strategist role + lifecycle instructions + Pakistan e-commerce context (COD preference, Daraz + TikTok + Instagram priority, warranty expectations for electronics)
- User prompt: injects `perceived` + `enriched_context` as JSON
- Required frameworks in output: STP, SWOT, PESTEL, 4Ps, Porter's Five Forces, AARRR growth funnel
- Response format: strict JSON only (no prose wrapping)
- Timeout: 120s

### Step 4 — Validate (Python)
Check the parsed JSON:
- All required top-level keys present (`stp`, `swot`, `pestel`, `competitor_analysis`, `marketing_mix`, `branding`, `channels`, `content_strategy`, `launch_plan`, `growth_funnel`, `evidence_ledger`, `validation_report`, `confidence_score`, `analysis_status`)
- `confidence_score` in [0, 1]
- Prices in `marketing_mix.price` do not contradict `analytics_result` (recommended sell price must be ≥ recommended buy price)
- `evidence_ledger` is not empty
- `launch_plan.kpis` is not empty
- Set `validation_report.status`: `ok` / `needs_review` / `invalid`
- Append specific flags for any failed check

### Step 5 — Critic (Ollama call #2)
- Sends: generated strategy JSON + `validation_report.flags`
- Prompt: "You are a critical reviewer. Fix all flagged issues in this marketing strategy. Return corrected JSON only, same schema."
- Replaces strategy with critic output if parseable; otherwise keeps validated output with `needs_review` status
- Timeout: 120s

### Step 6 — Store (Python + Supabase)
- Insert into `marketing_strategies` via new `ECDB.insert_marketing_strategy()` method
- Returns full strategy dict to the API endpoint

---

## 7. API Endpoints

### `POST /marketing/generate`

**Request:**
```json
{
  "product_name": "string",
  "category": "string",
  "analytics_result": {
    "recommended_buy_price_pkr": 0.0,
    "recommended_sell_price_pkr": 0.0,
    "expected_profit_margin": 0.0,
    "confidence_score": 0.0,
    "confidence_reason": "string",
    "wholesale_vendors_count": 0,
    "retail_sellers_count": 0
  },
  "scraper_result": {},
  "pipeline_run_id": "uuid (optional)"
}
```

**Response:** Full strategy JSON (schema in Section 9)

### `GET /marketing/{id}`

**Response:** Full strategy JSON for a single past run (same schema as `/generate` response). Used by `MarketingHistory.tsx` when a row is clicked.

---

### `GET /marketing/history?limit=20`

**Response:**
```json
{
  "strategies": [
    {
      "id": "uuid",
      "product_name": "string",
      "category": "string",
      "analysis_status": "ok",
      "confidence_score": 0.81,
      "created_at": "ISO timestamp"
    }
  ],
  "count": 20
}
```

---

## 8. Database Migration

```sql
-- 003_marketing_strategies.sql
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

CREATE INDEX IF NOT EXISTS idx_marketing_strategies_product ON marketing_strategies(product_name);
CREATE INDEX IF NOT EXISTS idx_marketing_strategies_created_at ON marketing_strategies(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_marketing_strategies_status ON marketing_strategies(analysis_status);
```

---

## 9. Output JSON Schema

```json
{
  "product_overview": {
    "name": "",
    "category": "",
    "buy_price_pkr": 0,
    "sell_price_pkr": 0,
    "margin_percent": 0,
    "vendor_count": 0,
    "seller_count": 0
  },
  "stp": {
    "segmentation": {},
    "targeting": {},
    "positioning": {}
  },
  "swot": {
    "strengths": [],
    "weaknesses": [],
    "opportunities": [],
    "threats": []
  },
  "pestel": {
    "political": "",
    "economic": "",
    "social": "",
    "technological": "",
    "environmental": "",
    "legal": ""
  },
  "competitor_analysis": {
    "five_forces": {
      "supplier_power": "",
      "buyer_power": "",
      "competitive_rivalry": "",
      "threat_of_substitutes": "",
      "threat_of_new_entrants": ""
    },
    "key_competitors": [],
    "price_band": { "min": 0, "max": 0, "currency": "PKR" }
  },
  "marketing_mix": {
    "product": {},
    "price": {},
    "place": {},
    "promotion": {}
  },
  "branding": {
    "value_proposition": "",
    "tone": "",
    "tagline": ""
  },
  "channels": [],
  "content_strategy": {},
  "launch_plan": {
    "phases": [],
    "kpis": [],
    "measurement_plan": {}
  },
  "growth_funnel": {
    "model": "AARRR",
    "stages": []
  },
  "evidence_ledger": [],
  "validation_report": {
    "status": "ok",
    "checks": [],
    "flags": []
  },
  "confidence_score": 0.0,
  "analysis_status": "ok"
}
```

---

## 10. Frontend Pages

### Results.tsx changes
- Add "Generate Marketing Strategy" button below `ComparisonSummary`
- Loading state: spinner + "Generating strategy with AI..." text (Ollama takes 10–30s)
- On success: save to `sessionStorage.marketingStrategy`, navigate to `/marketing`
- On error: show `ErrorAlert`

### Marketing.tsx (new, route `/marketing`)
Reads from `sessionStorage.marketingStrategy`. Collapsible sections:
1. Product Overview + confidence badge + analysis_status badge
2. STP Analysis (3 cards)
3. SWOT (2×2 grid)
4. PESTEL (6-cell table)
5. Competitor Analysis — Five Forces + key competitors + price band
6. Marketing Mix — 4Ps cards
7. Channel Plan — prioritized list with rationale
8. Growth Funnel — AARRR stages with metrics
9. Launch Plan — phased timeline + KPIs
10. Evidence Ledger — collapsible table
11. Validation Report — status badge + flags list

### MarketingHistory.tsx (new, route `/marketing/history`)
- Fetches `GET /marketing/history`
- Table: product name, category, status badge, confidence %, date
- Row click: fetches full strategy from Supabase, saves to sessionStorage, navigates to `/marketing`

---

## 11. Environment Variables

Add to `StrategaAi/.env`:
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

Add to `StrategaAi/.env.example`:
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

---

## 12. Dependencies

Add to `requirements.txt`:
```
ollama>=0.2.0
```

---

## 13. Pakistan E-Commerce Context (injected into LLM prompt)

- COD (Cash on Delivery) is dominant payment method
- Daraz is primary marketplace; TikTok Shop and Instagram are fast-growing
- Warranty and authenticity are top buyer concerns for electronics
- Logistics: J&T, Leopards, TCS — 2–5 day delivery standard
- Price sensitivity is high; bundle offers and free delivery convert well
- Peak seasons: Eid, Black Friday, Independence Day (14 Aug)

---

## 14. Out of Scope

- Real-time competitor scraping during marketing generation (uses existing scraper_result only)
- Authentication / user accounts
- Multi-language output (Urdu)
- Scheduled/automated marketing generation
