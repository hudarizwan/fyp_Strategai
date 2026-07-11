# Marketing Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an on-demand Marketing Agent to StrategAI that converts pricing intelligence into a full go-to-market strategy using a local Ollama llama3.1:8b model, persisted in Supabase and displayed in the dashboard.

**Architecture:** A `MarketingAgent` class runs a 6-step pipeline (Perceive → Enrich → Generate → Validate → Critic → Store). Two Ollama calls are made per run: one to generate the strategy, one critic pass to fix validation flags. Results are stored in a new `marketing_strategies` Supabase table and surfaced via three new API endpoints.

**Tech Stack:** Python 3.10+, FastAPI, ollama>=0.2.0, Supabase REST (via existing ECDB), React 18, TypeScript, Tailwind CSS, React Router, Recharts

---

## File Map

### Created
| File | Responsibility |
|------|---------------|
| `StrategaAi/db/migrations/003_marketing_strategies.sql` | New Supabase table |
| `StrategaAi/app/services/marketing_agent.py` | Full 6-step agent lifecycle |
| `StrategaAi/app/api/marketing.py` | FastAPI router (3 endpoints) |
| `StrategaAi/tests/test_marketing_agent.py` | Backend unit + integration tests |
| `frontend/salik-frontend/src/pages/Marketing.tsx` | Strategy display page |
| `frontend/salik-frontend/src/pages/MarketingHistory.tsx` | History list page |

### Modified
| File | Change |
|------|--------|
| `StrategaAi/app/services/ecdb.py` | Add `insert_marketing_strategy`, `get_marketing_history`, `get_marketing_strategy_by_id` |
| `StrategaAi/app/main.py` | Register marketing router |
| `StrategaAi/requirements.txt` | Add `ollama>=0.2.0` |
| `StrategaAi/.env` | Add `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |
| `StrategaAi/.env.example` | Add same keys |
| `frontend/salik-frontend/src/services/api.ts` | Add `marketingService` |
| `frontend/salik-frontend/src/pages/Results.tsx` | Add "Generate Marketing Strategy" button |
| `frontend/salik-frontend/src/components/Navbar.tsx` | Add Marketing + History links |
| `frontend/salik-frontend/src/App.tsx` | Add `/marketing` and `/marketing/history` routes |

---

## Task 1: Database Migration

**Files:**
- Create: `StrategaAi/db/migrations/003_marketing_strategies.sql`

- [ ] **Step 1: Create the migration file**

```sql
-- StrategaAi/db/migrations/003_marketing_strategies.sql
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
```

- [ ] **Step 2: Run migration in Supabase**

Go to your Supabase project → SQL Editor → paste the file contents → Run.

Or if you have the DB URL available:
```bash
cd StrategaAi
psql "$SUPABASE_DB_URL" -f db/migrations/003_marketing_strategies.sql
```

Expected: `CREATE TABLE`, `CREATE INDEX` × 3 with no errors.

- [ ] **Step 3: Commit**

```bash
git add db/migrations/003_marketing_strategies.sql
git commit -m "feat: add marketing_strategies table migration"
```

---

## Task 2: ECDB Methods

**Files:**
- Modify: `StrategaAi/app/services/ecdb.py`
- Test: `StrategaAi/tests/test_marketing_agent.py`

- [ ] **Step 1: Write failing tests for ECDB methods**

Create `StrategaAi/tests/test_marketing_agent.py`:

```python
"""Tests for Marketing Agent and ECDB marketing methods."""
import json
from unittest.mock import MagicMock, patch
import pytest

from app.services.ecdb import ECDB


# ---------------------------------------------------------------------------
# ECDB helpers
# ---------------------------------------------------------------------------

def _make_ecdb_rest():
    """Return an ECDB wired to REST-only mode (no live DB needed)."""
    with patch("app.services.ecdb.SUPABASE_DB_URL", ""), \
         patch("app.services.ecdb.SUPABASE_URL", "http://fake.supabase"), \
         patch("app.services.ecdb.SUPABASE_KEY", "fake-key"), \
         patch("app.services.ecdb.SUPABASE_SERVICE_KEY", "fake-service-key"), \
         patch.object(ECDB, "_connect", return_value=None), \
         patch.object(ECDB, "_init_database", return_value=None):
        db = ECDB.__new__(ECDB)
        db.driver_name = "supabase_rest"
        db.rest_base_url = "http://fake.supabase"
        db.rest_headers = {"apikey": "fake-key", "Authorization": "Bearer fake-key"}
        return db


def test_insert_marketing_strategy_returns_row():
    db = _make_ecdb_rest()
    fake_row = {
        "id": "aaaa-1111",
        "product_name": "Headphones",
        "category": "headsets",
        "analysis_status": "ok",
        "confidence_score": 0.8,
        "created_at": "2026-04-12T00:00:00Z",
    }
    with patch.object(db, "_rest_post", return_value=[fake_row]) as mock_post:
        result = db.insert_marketing_strategy({
            "product_name": "Headphones",
            "category": "headsets",
            "strategy": {"stp": {}},
            "analysis_status": "ok",
            "confidence_score": 0.8,
        })
    assert result["id"] == "aaaa-1111"
    mock_post.assert_called_once_with("marketing_strategies", {
        "product_name": "Headphones",
        "category": "headsets",
        "strategy": {"stp": {}},
        "analysis_status": "ok",
        "confidence_score": 0.8,
    })


def test_get_marketing_history_returns_list():
    db = _make_ecdb_rest()
    fake_rows = [
        {"id": "aaa", "product_name": "Headphones", "analysis_status": "ok",
         "confidence_score": 0.8, "created_at": "2026-04-12T00:00:00Z"},
    ]
    with patch.object(db, "_rest_get", return_value=fake_rows):
        result = db.get_marketing_history(limit=5)
    assert len(result) == 1
    assert result[0]["id"] == "aaa"


def test_get_marketing_strategy_by_id_returns_row():
    db = _make_ecdb_rest()
    fake_row = {"id": "bbb", "product_name": "Mouse", "strategy": {"stp": {}}}
    with patch.object(db, "_rest_get", return_value=[fake_row]):
        result = db.get_marketing_strategy_by_id("bbb")
    assert result["id"] == "bbb"


def test_get_marketing_strategy_by_id_not_found():
    db = _make_ecdb_rest()
    with patch.object(db, "_rest_get", return_value=[]):
        result = db.get_marketing_strategy_by_id("missing-id")
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd StrategaAi
venv/Scripts/python -m pytest tests/test_marketing_agent.py::test_insert_marketing_strategy_returns_row -v
```

Expected: `FAILED` — `AttributeError: 'ECDB' object has no attribute 'insert_marketing_strategy'`

- [ ] **Step 3: Add the three ECDB methods**

Open `StrategaAi/app/services/ecdb.py`. Find the last method in the class (near the bottom). Add after it:

```python
    # ------------------------------------------------------------------
    # Marketing strategies
    # ------------------------------------------------------------------

    def insert_marketing_strategy(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        rows = self._rest_post("marketing_strategies", payload)
        return rows[0] if rows else {}

    def get_marketing_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._rest_get(
            "marketing_strategies",
            {
                "select": "id,product_name,category,analysis_status,confidence_score,created_at",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )

    def get_marketing_strategy_by_id(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        rows = self._rest_get(
            "marketing_strategies",
            {"select": "*", "id": f"eq.{strategy_id}", "limit": "1"},
        )
        return rows[0] if rows else None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd StrategaAi
venv/Scripts/python -m pytest tests/test_marketing_agent.py::test_insert_marketing_strategy_returns_row tests/test_marketing_agent.py::test_get_marketing_history_returns_list tests/test_marketing_agent.py::test_get_marketing_strategy_by_id_returns_row tests/test_marketing_agent.py::test_get_marketing_strategy_by_id_not_found -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/ecdb.py tests/test_marketing_agent.py
git commit -m "feat: add marketing_strategy ECDB methods"
```

---

## Task 3: MarketingAgent — Perceive and Enrich

**Files:**
- Create: `StrategaAi/app/services/marketing_agent.py`
- Modify: `StrategaAi/tests/test_marketing_agent.py`

- [ ] **Step 1: Add failing tests for Perceive and Enrich**

Append to `StrategaAi/tests/test_marketing_agent.py`:

```python
# ---------------------------------------------------------------------------
# Perceive
# ---------------------------------------------------------------------------

from app.services.marketing_agent import MarketingAgent

VALID_ANALYTICS = {
    "recommended_buy_price_pkr": 28000.0,
    "recommended_sell_price_pkr": 38000.0,
    "expected_profit_margin": 26.3,
    "confidence_score": 0.81,
    "confidence_reason": "sufficient data",
    "wholesale_vendors_count": 6,
    "retail_sellers_count": 12,
}

VALID_SCRAPER = {
    "wholesale": {
        "made_in_china": [
            {"supplier": "Shenzhen Co", "unit_price": 100.0, "unit_price_pkr": 28000.0,
             "currency": "USD", "moq": 10, "origin": "China"},
        ]
    },
    "retail": [
        {"seller": "TechStore", "platform": "daraz", "list_price": 39000.0,
         "title": "Sony WH-1000XM5", "url": "https://daraz.pk/1",
         "detail": {"highlights": "Great noise cancelling, fast delivery"}},
        {"seller": "GadgetHub", "platform": "daraz", "list_price": 40000.0,
         "title": "Sony Headphones", "url": "https://daraz.pk/2", "detail": {}},
    ],
}


def _make_agent():
    with patch("app.services.marketing_agent.ECDB"):
        agent = MarketingAgent(ollama_base_url="http://localhost:11434", model="llama3.1:8b")
    return agent


def test_perceive_valid_input():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    assert perceived["product_name"] == "Sony WH-1000XM5"
    assert perceived["buy_price_pkr"] == 28000.0
    assert perceived["sell_price_pkr"] == 38000.0
    assert perceived["margin_percent"] == 26.3
    assert perceived["confidence_score"] == 0.81
    assert perceived["vendor_count"] == 6
    assert perceived["seller_count"] == 12


def test_perceive_missing_required_field_raises():
    agent = _make_agent()
    bad = {k: v for k, v in VALID_ANALYTICS.items() if k != "recommended_buy_price_pkr"}
    with pytest.raises(ValueError, match="recommended_buy_price_pkr"):
        agent._perceive("Product", "category", bad)


def test_perceive_negative_price_raises():
    agent = _make_agent()
    bad = {**VALID_ANALYTICS, "recommended_buy_price_pkr": -100.0}
    with pytest.raises(ValueError, match="positive"):
        agent._perceive("Product", "category", bad)


def test_perceive_confidence_out_of_range_raises():
    agent = _make_agent()
    bad = {**VALID_ANALYTICS, "confidence_score": 1.5}
    with pytest.raises(ValueError, match="confidence_score"):
        agent._perceive("Product", "category", bad)


# ---------------------------------------------------------------------------
# Enrich
# ---------------------------------------------------------------------------

def test_enrich_extracts_competitors():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    assert enriched["competitor_count"] == 2
    assert enriched["price_band"]["min"] == 39000.0
    assert enriched["price_band"]["max"] == 40000.0
    assert "TechStore" in enriched["competitor_names"]


def test_enrich_extracts_wholesale_origins():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    assert "China" in enriched["wholesale_origins"]
    assert enriched["moq_range"]["min"] == 10


def test_enrich_extracts_review_themes():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    assert len(enriched["review_themes"]) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd StrategaAi
venv/Scripts/python -m pytest tests/test_marketing_agent.py::test_perceive_valid_input -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'app.services.marketing_agent'`

- [ ] **Step 3: Create marketing_agent.py with Perceive and Enrich**

Create `StrategaAi/app/services/marketing_agent.py`:

```python
"""
Marketing Agent for StrategAI.

Lifecycle: Perceive → Enrich → Generate → Validate → Critic → Store
Uses local Ollama (llama3.1:8b) for two LLM passes.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from app.services.ecdb import ECDB

logger = logging.getLogger(__name__)

PAKISTAN_CONTEXT = """
Pakistan e-commerce context (apply throughout):
- COD (Cash on Delivery) is the dominant payment method (~70% of orders).
- Daraz is the primary marketplace. TikTok Shop and Instagram are fast-growing.
- Warranty and authenticity are top buyer concerns, especially for electronics.
- Logistics: J&T, Leopards, TCS — standard delivery 2–5 days.
- Price sensitivity is high; bundle offers and free delivery improve conversion.
- Peak seasons: Eid-ul-Fitr, Eid-ul-Adha, Black Friday, Independence Day (14 Aug).
- Trust signals (genuine warranty, seller ratings, return policy) are critical.
"""

REQUIRED_ANALYTICS_FIELDS = [
    "recommended_buy_price_pkr",
    "recommended_sell_price_pkr",
    "expected_profit_margin",
    "confidence_score",
    "wholesale_vendors_count",
    "retail_sellers_count",
]

REQUIRED_OUTPUT_KEYS = [
    "stp", "swot", "pestel", "competitor_analysis", "marketing_mix",
    "branding", "channels", "content_strategy", "launch_plan",
    "growth_funnel", "evidence_ledger", "validation_report",
    "confidence_score", "analysis_status",
]


class MarketingAgent:
    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
    ):
        self.ollama_base_url = ollama_base_url
        self.model = model
        self.db = ECDB()

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------

    def run(
        self,
        product_name: str,
        category: str,
        analytics_result: Dict[str, Any],
        scraper_result: Dict[str, Any],
        pipeline_run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        perceived = self._perceive(product_name, category, analytics_result)
        enriched = self._enrich(perceived, scraper_result)
        raw_strategy = self._generate(enriched)
        validated = self._validate(raw_strategy, perceived)
        final = self._critic(validated, enriched)
        return self._store(final, product_name, category, pipeline_run_id)

    # ------------------------------------------------------------------
    # Step 1 — Perceive
    # ------------------------------------------------------------------

    def _perceive(
        self,
        product_name: str,
        category: str,
        analytics_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        for field in REQUIRED_ANALYTICS_FIELDS:
            if field not in analytics_result:
                raise ValueError(f"Missing required analytics field: {field}")

        buy = float(analytics_result["recommended_buy_price_pkr"])
        sell = float(analytics_result["recommended_sell_price_pkr"])
        margin = float(analytics_result["expected_profit_margin"])
        confidence = float(analytics_result["confidence_score"])

        if buy <= 0 or sell <= 0:
            raise ValueError("recommended_buy_price_pkr and recommended_sell_price_pkr must be positive")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"confidence_score must be between 0 and 1, got {confidence}")
        if not (0.0 <= margin <= 100.0):
            raise ValueError(f"expected_profit_margin must be between 0 and 100, got {margin}")

        return {
            "product_name": product_name,
            "category": category,
            "buy_price_pkr": buy,
            "sell_price_pkr": sell,
            "margin_percent": margin,
            "confidence_score": confidence,
            "confidence_reason": analytics_result.get("confidence_reason", ""),
            "vendor_count": int(analytics_result.get("wholesale_vendors_count", 0)),
            "seller_count": int(analytics_result.get("retail_sellers_count", 0)),
            "price_spread": round(sell - buy, 2),
        }

    # ------------------------------------------------------------------
    # Step 2 — Enrich
    # ------------------------------------------------------------------

    def _enrich(
        self,
        perceived: Dict[str, Any],
        scraper_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        retail_items = scraper_result.get("retail") or []
        wholesale_platforms = scraper_result.get("wholesale") or {}

        # Competitors from retail
        competitor_names: List[str] = []
        retail_prices: List[float] = []
        platform_counts: Dict[str, int] = {}
        review_themes: List[str] = []

        for item in retail_items:
            seller = (item.get("seller") or "").strip()
            if seller:
                competitor_names.append(seller)
            price = item.get("list_price") or item.get("price_pkr")
            if price and float(price) > 0:
                retail_prices.append(float(price))
            platform = item.get("platform") or "unknown"
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
            detail = item.get("detail") or {}
            highlights = detail.get("highlights") or detail.get("full_description") or ""
            # Sanitize: strip anything that looks like an instruction injection
            safe = re.sub(r"(ignore|disregard|forget|system|prompt|instruction)", "", highlights, flags=re.IGNORECASE)
            safe = safe.strip()[:300]
            if safe:
                review_themes.append(safe)

        # Wholesale origins + MOQ
        wholesale_origins: List[str] = []
        moq_values: List[int] = []
        for _platform, items in wholesale_platforms.items():
            for item in (items or []):
                origin = item.get("origin") or item.get("vendor_location") or ""
                if origin:
                    wholesale_origins.append(origin)
                moq = item.get("moq")
                if moq and int(moq) > 0:
                    moq_values.append(int(moq))

        price_band = {
            "min": min(retail_prices) if retail_prices else 0.0,
            "max": max(retail_prices) if retail_prices else 0.0,
            "avg": round(sum(retail_prices) / len(retail_prices), 2) if retail_prices else 0.0,
            "currency": "PKR",
        }

        moq_range = {
            "min": min(moq_values) if moq_values else 1,
            "max": max(moq_values) if moq_values else 1,
        }

        return {
            **perceived,
            "competitor_count": len(retail_items),
            "competitor_names": list(dict.fromkeys(competitor_names)),  # deduplicated, order-preserved
            "price_band": price_band,
            "platform_distribution": platform_counts,
            "wholesale_origins": list(set(wholesale_origins)),
            "moq_range": moq_range,
            "review_themes": review_themes[:5],  # cap at 5 to keep prompt size reasonable
        }
```

- [ ] **Step 4: Run Perceive + Enrich tests**

```bash
cd StrategaAi
venv/Scripts/python -m pytest tests/test_marketing_agent.py -k "perceive or enrich" -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/marketing_agent.py tests/test_marketing_agent.py
git commit -m "feat: marketing agent perceive and enrich steps"
```

---

## Task 4: MarketingAgent — Generate (Ollama call #1)

**Files:**
- Modify: `StrategaAi/app/services/marketing_agent.py`
- Modify: `StrategaAi/requirements.txt`
- Modify: `StrategaAi/tests/test_marketing_agent.py`

- [ ] **Step 1: Add ollama to requirements.txt**

Open `StrategaAi/requirements.txt` and add at the end:
```
ollama>=0.2.0
```

Install it:
```bash
cd StrategaAi
venv/Scripts/pip install ollama>=0.2.0
```

Expected: `Successfully installed ollama-x.x.x`

- [ ] **Step 2: Write failing test for Generate**

Append to `StrategaAi/tests/test_marketing_agent.py`:

```python
# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

MINIMAL_VALID_STRATEGY = {
    "stp": {"segmentation": {}, "targeting": {}, "positioning": {}},
    "swot": {"strengths": ["low cost"], "weaknesses": [], "opportunities": [], "threats": []},
    "pestel": {"political": "stable", "economic": "growing", "social": "online shift",
               "technological": "4G coverage", "environmental": "N/A", "legal": "import duties"},
    "competitor_analysis": {
        "five_forces": {"supplier_power": "medium", "buyer_power": "high",
                        "competitive_rivalry": "high", "threat_of_substitutes": "medium",
                        "threat_of_new_entrants": "low"},
        "key_competitors": ["TechStore"],
        "price_band": {"min": 39000, "max": 40000, "currency": "PKR"},
    },
    "marketing_mix": {
        "product": {"description": "noise cancelling headphones"},
        "price": {"strategy": "competitive", "recommended_sell_pkr": 38000},
        "place": {"channels": ["Daraz"]},
        "promotion": {"tactics": ["social media"]},
    },
    "branding": {"value_proposition": "best sound", "tone": "premium", "tagline": "Hear More"},
    "channels": [{"name": "Daraz", "priority": 1, "rationale": "largest marketplace"}],
    "content_strategy": {"formats": ["video"], "frequency": "3x per week"},
    "launch_plan": {
        "phases": [{"name": "Soft Launch", "duration": "2 weeks", "actions": ["list on Daraz"]}],
        "kpis": [{"metric": "units sold", "target": 50, "period": "month 1"}],
        "measurement_plan": {"tools": ["Daraz analytics"], "cadence": "weekly"},
    },
    "growth_funnel": {
        "model": "AARRR",
        "stages": [{"stage": "Acquisition", "metric": "listing views", "target": 1000}],
    },
    "evidence_ledger": [{"recommendation": "price at 38000", "evidence": ["retail price band 39k-40k"]}],
    "validation_report": {"status": "ok", "checks": [], "flags": []},
    "confidence_score": 0.78,
    "analysis_status": "ok",
}


def test_generate_parses_valid_json_response():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)

    mock_response = {"message": {"content": json.dumps(MINIMAL_VALID_STRATEGY)}}
    with patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = mock_response
        result = agent._generate(enriched)

    assert result["analysis_status"] == "ok"
    assert "stp" in result


def test_generate_extracts_json_from_prose():
    """Handles model responses that wrap JSON in prose or code fences."""
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)

    wrapped = f"Here is the strategy:\n```json\n{json.dumps(MINIMAL_VALID_STRATEGY)}\n```"
    mock_response = {"message": {"content": wrapped}}
    with patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = mock_response
        result = agent._generate(enriched)

    assert "stp" in result


def test_generate_returns_error_dict_on_unparseable_response():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)

    mock_response = {"message": {"content": "I cannot generate a strategy."}}
    with patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = mock_response
        result = agent._generate(enriched)

    assert result["analysis_status"] == "invalid"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd StrategaAi
venv/Scripts/python -m pytest tests/test_marketing_agent.py::test_generate_parses_valid_json_response -v
```

Expected: `FAILED` — `AttributeError: '_generate'`

- [ ] **Step 4: Add _generate method and imports to marketing_agent.py**

At the top of `StrategaAi/app/services/marketing_agent.py`, after the existing imports, add:

```python
import ollama
```

Then add `_generate` and `_build_system_prompt` to the `MarketingAgent` class, after `_enrich`:

```python
    # ------------------------------------------------------------------
    # Step 3 — Generate (Ollama call #1)
    # ------------------------------------------------------------------

    def _generate(self, enriched: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = self._build_system_prompt()
        user_content = (
            "Generate a complete marketing strategy for this product. "
            "Return ONLY valid JSON matching the schema. No prose, no markdown fences.\n\n"
            f"INPUT DATA:\n{json.dumps(enriched, indent=2)}"
        )
        try:
            client = ollama.Client(host=self.ollama_base_url)
            response = client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                options={"temperature": 0.3},
            )
            raw_text = response["message"]["content"]
            return self._extract_json(raw_text)
        except Exception as exc:
            logger.error("Ollama generate call failed: %s", exc)
            return self._empty_strategy(str(exc))

    def _build_system_prompt(self) -> str:
        return f"""You are a senior marketing strategist specialising in Pakistan e-commerce.
Follow this lifecycle: Perceive → Enrich → Reason → Plan → Generate → Validate → Store.

{PAKISTAN_CONTEXT}

Required frameworks to include:
- STP (Segmentation, Targeting, Positioning)
- SWOT (Strengths, Weaknesses, Opportunities, Threats)
- PESTEL
- 4Ps Marketing Mix (Product, Price, Place, Promotion)
- Porter's Five Forces (inside competitor_analysis.five_forces)
- AARRR Growth Funnel (inside growth_funnel)

Evidence grounding: Every major recommendation MUST include an "evidence" field citing
specific input data fields (e.g., "price_band", "vendor_count", "review_themes").

Pricing consistency: recommended prices in marketing_mix.price MUST align with
buy_price_pkr and sell_price_pkr in the input. Do not contradict them.

Output ONLY this JSON object, fully populated, no extra text:
{{
  "stp": {{"segmentation": {{}}, "targeting": {{}}, "positioning": {{}}}},
  "swot": {{"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}},
  "pestel": {{"political": "", "economic": "", "social": "", "technological": "", "environmental": "", "legal": ""}},
  "competitor_analysis": {{
    "five_forces": {{"supplier_power": "", "buyer_power": "", "competitive_rivalry": "", "threat_of_substitutes": "", "threat_of_new_entrants": ""}},
    "key_competitors": [],
    "price_band": {{"min": 0, "max": 0, "currency": "PKR"}}
  }},
  "marketing_mix": {{"product": {{}}, "price": {{}}, "place": {{}}, "promotion": {{}}}},
  "branding": {{"value_proposition": "", "tone": "", "tagline": ""}},
  "channels": [],
  "content_strategy": {{}},
  "launch_plan": {{"phases": [], "kpis": [], "measurement_plan": {{}}}},
  "growth_funnel": {{"model": "AARRR", "stages": []}},
  "evidence_ledger": [],
  "validation_report": {{"status": "ok", "checks": [], "flags": []}},
  "confidence_score": 0.0,
  "analysis_status": "ok"
}}"""

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from model output, handling code fences and prose wrapping."""
        # Try raw parse first
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        # Try extracting from code fence
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence_match:
            try:
                return json.loads(fence_match.group(1))
            except json.JSONDecodeError:
                pass
        # Try finding first { ... } block
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
        logger.warning("Could not parse JSON from model output")
        return self._empty_strategy("unparseable model output")

    def _empty_strategy(self, reason: str = "") -> Dict[str, Any]:
        return {
            "stp": {}, "swot": {}, "pestel": {}, "competitor_analysis": {},
            "marketing_mix": {}, "branding": {}, "channels": [],
            "content_strategy": {}, "launch_plan": {},
            "growth_funnel": {"model": "AARRR", "stages": []},
            "evidence_ledger": [],
            "validation_report": {"status": "invalid", "checks": [], "flags": [reason]},
            "confidence_score": 0.0,
            "analysis_status": "invalid",
        }
```

- [ ] **Step 5: Run generate tests**

```bash
cd StrategaAi
venv/Scripts/python -m pytest tests/test_marketing_agent.py -k "generate" -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/services/marketing_agent.py requirements.txt tests/test_marketing_agent.py
git commit -m "feat: marketing agent generate step with ollama"
```

---

## Task 5: MarketingAgent — Validate

**Files:**
- Modify: `StrategaAi/app/services/marketing_agent.py`
- Modify: `StrategaAi/tests/test_marketing_agent.py`

- [ ] **Step 1: Write failing tests for Validate**

Append to `StrategaAi/tests/test_marketing_agent.py`:

```python
# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

def test_validate_ok_strategy_passes():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    result = agent._validate(MINIMAL_VALID_STRATEGY.copy(), perceived)
    assert result["validation_report"]["status"] == "ok"
    assert result["analysis_status"] == "ok"


def test_validate_missing_key_flags_needs_review():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    bad = {k: v for k, v in MINIMAL_VALID_STRATEGY.items() if k != "swot"}
    result = agent._validate(bad, perceived)
    assert result["validation_report"]["status"] == "needs_review"
    assert any("swot" in flag for flag in result["validation_report"]["flags"])


def test_validate_empty_evidence_ledger_flags():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    bad = {**MINIMAL_VALID_STRATEGY, "evidence_ledger": []}
    result = agent._validate(bad, perceived)
    assert result["validation_report"]["status"] in ("needs_review", "invalid")
    assert any("evidence_ledger" in flag for flag in result["validation_report"]["flags"])


def test_validate_confidence_out_of_range_flags():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    bad = {**MINIMAL_VALID_STRATEGY, "confidence_score": 1.8}
    result = agent._validate(bad, perceived)
    assert any("confidence_score" in flag for flag in result["validation_report"]["flags"])


def test_validate_invalid_analysis_status():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    bad = {**MINIMAL_VALID_STRATEGY, "analysis_status": "invalid"}
    result = agent._validate(bad, perceived)
    assert result["validation_report"]["status"] in ("needs_review", "invalid")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd StrategaAi
venv/Scripts/python -m pytest tests/test_marketing_agent.py -k "validate" -v
```

Expected: `FAILED` — `AttributeError: '_validate'`

- [ ] **Step 3: Add _validate method to marketing_agent.py**

Add after `_empty_strategy` in the `MarketingAgent` class:

```python
    # ------------------------------------------------------------------
    # Step 4 — Validate (Python)
    # ------------------------------------------------------------------

    def _validate(
        self,
        strategy: Dict[str, Any],
        perceived: Dict[str, Any],
    ) -> Dict[str, Any]:
        strategy = dict(strategy)
        flags: List[str] = []
        checks: List[str] = []

        # Required keys
        for key in REQUIRED_OUTPUT_KEYS:
            if key not in strategy:
                flags.append(f"missing_key:{key}")
            else:
                checks.append(f"present:{key}")

        # confidence_score range
        cs = strategy.get("confidence_score")
        if cs is not None:
            try:
                cs = float(cs)
                if not (0.0 <= cs <= 1.0):
                    flags.append(f"confidence_score out of range: {cs}")
                else:
                    checks.append("confidence_score_range:ok")
            except (TypeError, ValueError):
                flags.append("confidence_score not numeric")

        # analysis_status not already invalid (from generate step)
        if strategy.get("analysis_status") == "invalid":
            flags.append("analysis_status:invalid from generate step")

        # evidence_ledger not empty
        if not strategy.get("evidence_ledger"):
            flags.append("evidence_ledger:empty")
        else:
            checks.append("evidence_ledger:populated")

        # launch_plan.kpis not empty
        kpis = (strategy.get("launch_plan") or {}).get("kpis")
        if not kpis:
            flags.append("launch_plan.kpis:empty")
        else:
            checks.append("launch_plan.kpis:populated")

        # Determine status
        if len(flags) == 0:
            status = "ok"
        elif len(flags) <= 2:
            status = "needs_review"
        else:
            status = "invalid"

        strategy["validation_report"] = {
            "status": status,
            "checks": checks,
            "flags": flags,
        }
        if status != "ok":
            strategy["analysis_status"] = status

        return strategy
```

- [ ] **Step 4: Run validate tests**

```bash
cd StrategaAi
venv/Scripts/python -m pytest tests/test_marketing_agent.py -k "validate" -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/marketing_agent.py tests/test_marketing_agent.py
git commit -m "feat: marketing agent validate step"
```

---

## Task 6: MarketingAgent — Critic, Store, and run()

**Files:**
- Modify: `StrategaAi/app/services/marketing_agent.py`
- Modify: `StrategaAi/tests/test_marketing_agent.py`

- [ ] **Step 1: Write failing tests for Critic and run()**

Append to `StrategaAi/tests/test_marketing_agent.py`:

```python
# ---------------------------------------------------------------------------
# Critic + run()
# ---------------------------------------------------------------------------

def test_critic_returns_improved_strategy():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    strategy_with_flags = {
        **MINIMAL_VALID_STRATEGY,
        "validation_report": {
            "status": "needs_review",
            "checks": [],
            "flags": ["evidence_ledger:empty"],
        },
        "evidence_ledger": [],
    }
    improved = {**MINIMAL_VALID_STRATEGY, "evidence_ledger": [{"recommendation": "fixed", "evidence": ["price_band"]}]}
    mock_response = {"message": {"content": json.dumps(improved)}}
    with patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = mock_response
        result = agent._critic(strategy_with_flags, enriched)
    assert result["evidence_ledger"][0]["recommendation"] == "fixed"


def test_critic_keeps_original_if_parse_fails():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    strategy_ok = {**MINIMAL_VALID_STRATEGY}
    mock_response = {"message": {"content": "not json"}}
    with patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = mock_response
        result = agent._critic(strategy_ok, enriched)
    assert result["analysis_status"] == "ok"


def test_run_returns_strategy_with_id():
    agent = _make_agent()
    stored_row = {"id": "xyz-123", **MINIMAL_VALID_STRATEGY,
                  "product_name": "Sony WH-1000XM5", "category": "headsets",
                  "created_at": "2026-04-12T00:00:00Z"}

    with patch("app.services.marketing_agent.ollama") as mock_ollama, \
         patch.object(agent.db, "insert_marketing_strategy", return_value=stored_row):
        mock_ollama.Client.return_value.chat.return_value = {
            "message": {"content": json.dumps(MINIMAL_VALID_STRATEGY)}
        }
        result = agent.run(
            "Sony WH-1000XM5", "headsets",
            VALID_ANALYTICS, VALID_SCRAPER,
        )
    assert result["id"] == "xyz-123"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd StrategaAi
venv/Scripts/python -m pytest tests/test_marketing_agent.py -k "critic or run" -v
```

Expected: `FAILED` — `AttributeError: '_critic'`

- [ ] **Step 3: Add _critic, _store methods to marketing_agent.py**

Add after `_validate` in the `MarketingAgent` class:

```python
    # ------------------------------------------------------------------
    # Step 5 — Critic (Ollama call #2)
    # ------------------------------------------------------------------

    def _critic(
        self,
        strategy: Dict[str, Any],
        enriched: Dict[str, Any],
    ) -> Dict[str, Any]:
        flags = (strategy.get("validation_report") or {}).get("flags") or []
        if not flags:
            return strategy  # nothing to fix

        critic_prompt = (
            "You are a critical reviewer. The marketing strategy below has validation issues. "
            "Fix ONLY the flagged problems. Return the corrected strategy as valid JSON only. "
            "Do not change sections that are not flagged.\n\n"
            f"FLAGS:\n{json.dumps(flags)}\n\n"
            f"STRATEGY:\n{json.dumps(strategy)}"
        )
        try:
            client = ollama.Client(host=self.ollama_base_url)
            response = client.chat(
                model=self.model,
                messages=[{"role": "user", "content": critic_prompt}],
                options={"temperature": 0.1},
            )
            raw_text = response["message"]["content"]
            improved = self._extract_json(raw_text)
            if improved.get("analysis_status") != "invalid" and improved.get("stp"):
                return improved
        except Exception as exc:
            logger.warning("Critic pass failed: %s — keeping validated strategy", exc)
        return strategy

    # ------------------------------------------------------------------
    # Step 6 — Store
    # ------------------------------------------------------------------

    def _store(
        self,
        strategy: Dict[str, Any],
        product_name: str,
        category: str,
        pipeline_run_id: Optional[str],
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "product_name": product_name,
            "category": category,
            "strategy": strategy,
            "analysis_status": strategy.get("analysis_status", "ok"),
            "confidence_score": strategy.get("confidence_score"),
        }
        if pipeline_run_id:
            payload["pipeline_run_id"] = pipeline_run_id
        stored = self.db.insert_marketing_strategy(payload)
        return {**stored, **strategy}
```

- [ ] **Step 4: Run all marketing agent tests**

```bash
cd StrategaAi
venv/Scripts/python -m pytest tests/test_marketing_agent.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/services/marketing_agent.py tests/test_marketing_agent.py
git commit -m "feat: marketing agent critic, store, and run() orchestrator"
```

---

## Task 7: FastAPI Router

**Files:**
- Create: `StrategaAi/app/api/marketing.py`
- Modify: `StrategaAi/app/main.py`

- [ ] **Step 1: Create the router**

Create `StrategaAi/app/api/marketing.py`:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
import os

from app.services.marketing_agent import MarketingAgent

router = APIRouter()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


class AnalyticsResultPayload(BaseModel):
    recommended_buy_price_pkr: float
    recommended_sell_price_pkr: float
    expected_profit_margin: float
    confidence_score: float
    confidence_reason: str = ""
    wholesale_vendors_count: int = 0
    retail_sellers_count: int = 0


class MarketingGenerateRequest(BaseModel):
    product_name: str
    category: str
    analytics_result: AnalyticsResultPayload
    scraper_result: Dict[str, Any] = {}
    pipeline_run_id: Optional[str] = None


@router.post("/generate")
async def generate_marketing_strategy(request: MarketingGenerateRequest):
    """
    Run the Marketing Agent pipeline and return a full go-to-market strategy.
    Persists result to Supabase marketing_strategies table.
    """
    try:
        agent = MarketingAgent(
            ollama_base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
        )
        result = agent.run(
            product_name=request.product_name,
            category=request.category,
            analytics_result=request.analytics_result.model_dump(),
            scraper_result=request.scraper_result,
            pipeline_run_id=request.pipeline_run_id,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/history")
async def get_marketing_history(limit: int = 20):
    """Return the last N marketing strategy runs (summary only)."""
    try:
        from app.services.ecdb import ECDB
        db = ECDB()
        strategies = db.get_marketing_history(limit=limit)
        return {"strategies": strategies, "count": len(strategies)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{strategy_id}")
async def get_marketing_strategy(strategy_id: str):
    """Return a single marketing strategy by ID."""
    try:
        from app.services.ecdb import ECDB
        db = ECDB()
        strategy = db.get_marketing_strategy_by_id(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return strategy
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

- [ ] **Step 2: Register the router in main.py**

Open `StrategaAi/app/main.py`. After the existing router imports, add:

```python
from app.api.marketing import router as marketing_router
```

After the existing `app.include_router(analytics_router, ...)` line, add:

```python
app.include_router(marketing_router, prefix="/marketing", tags=["Marketing Agent"])
```

- [ ] **Step 3: Add env vars to .env and .env.example**

In `StrategaAi/.env`, add at the end:
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

In `StrategaAi/.env.example`, add at the end:
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

- [ ] **Step 4: Verify the server starts**

```bash
cd StrategaAi
venv/Scripts/uvicorn app.main:app --port 8001 --reload
```

Expected: server starts, visit `http://127.0.0.1:8001/docs` — you should see `Marketing Agent` section with 3 endpoints: `POST /marketing/generate`, `GET /marketing/history`, `GET /marketing/{strategy_id}`.

Stop the server with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add app/api/marketing.py app/main.py .env.example
git commit -m "feat: marketing API router with generate, history, and get-by-id endpoints"
```

---

## Task 8: Frontend — API Service + Results Page Button

**Files:**
- Modify: `frontend/salik-frontend/src/services/api.ts`
- Modify: `frontend/salik-frontend/src/pages/Results.tsx`

- [ ] **Step 1: Add marketingService to api.ts**

Open `frontend/salik-frontend/src/services/api.ts`. After the existing `scraperService` object, add:

```typescript
export const marketingService = {
  generate: async (payload: {
    product_name: string;
    category: string;
    analytics_result: Record<string, any>;
    scraper_result: Record<string, any>;
    pipeline_run_id?: string;
  }): Promise<any> => {
    const response = await api.post('/marketing/generate', payload);
    return response.data;
  },

  getHistory: async (limit = 20): Promise<{ strategies: any[]; count: number }> => {
    const response = await api.get(`/marketing/history?limit=${limit}`);
    return response.data;
  },

  getById: async (id: string): Promise<any> => {
    const response = await api.get(`/marketing/${id}`);
    return response.data;
  },
};
```

- [ ] **Step 2: Add the button to Results.tsx**

Open `frontend/salik-frontend/src/pages/Results.tsx`.

After the existing imports, add:
```typescript
import { marketingService } from '@/services/api';
import { Sparkles } from 'lucide-react';
```

After the existing state declarations (`const [error, setError] = useState...`), add:
```typescript
const [marketingLoading, setMarketingLoading] = useState(false);
const [marketingError, setMarketingError] = useState<string | null>(null);
```

After the `useEffect` closing brace, add:
```typescript
const handleGenerateMarketing = async () => {
  const storedAnalytics = sessionStorage.getItem('analyticsRecommendation');
  if (!storedAnalytics || !data) return;
  setMarketingLoading(true);
  setMarketingError(null);
  try {
    const analyticsResult = JSON.parse(storedAnalytics);
    const scraperResult = JSON.parse(sessionStorage.getItem('scraperResult') || '{}');
    const strategy = await marketingService.generate({
      product_name: data.product_name,
      category: analyticsResult.category || '',
      analytics_result: analyticsResult,
      scraper_result: scraperResult,
    });
    sessionStorage.setItem('marketingStrategy', JSON.stringify(strategy));
    navigate('/marketing');
  } catch (err) {
    setMarketingError(err instanceof Error ? err.message : 'Failed to generate marketing strategy');
  } finally {
    setMarketingLoading(false);
  }
};
```

In the JSX, after the `{comparisonData.estimatedProfit > 0 && <ComparisonSummary ... />}` block, add:

```tsx
{/* Marketing Strategy CTA */}
{analyticsRecommendation && (
  <div className="flex flex-col items-center gap-3 py-6 border border-white/10 rounded-lg bg-white/5">
    <p className="text-gray-400 text-sm">
      Analytics complete — generate a full go-to-market strategy
    </p>
    {marketingError && (
      <ErrorAlert message={marketingError} onClose={() => setMarketingError(null)} />
    )}
    <Button
      onClick={handleGenerateMarketing}
      disabled={marketingLoading}
      className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2"
    >
      {marketingLoading ? (
        <>
          <span className="animate-spin mr-2 inline-block h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
          Generating strategy...
        </>
      ) : (
        <>
          <Sparkles className="mr-2 h-4 w-4" />
          Generate Marketing Strategy
        </>
      )}
    </Button>
  </div>
)}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/salik-frontend/src/services/api.ts frontend/salik-frontend/src/pages/Results.tsx
git commit -m "feat: marketing service and generate button on Results page"
```

---

## Task 9: Frontend — Marketing.tsx Display Page

**Files:**
- Create: `frontend/salik-frontend/src/pages/Marketing.tsx`

- [ ] **Step 1: Create Marketing.tsx**

Create `frontend/salik-frontend/src/pages/Marketing.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, AlertTriangle, XCircle, ChevronDown, ChevronUp } from 'lucide-react';
import Button from '@/components/ui/Button';

function StatusBadge({ status }: { status: string }) {
  if (status === 'ok') return (
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
      <CheckCircle className="h-3 w-3" /> OK
    </span>
  );
  if (status === 'needs_review') return (
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
      <AlertTriangle className="h-3 w-3" /> Needs Review
    </span>
  );
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30">
      <XCircle className="h-3 w-3" /> Invalid
    </span>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="border border-white/10 rounded-lg overflow-hidden">
      <button
        className="w-full flex items-center justify-between p-4 bg-white/5 hover:bg-white/10 transition-colors text-left"
        onClick={() => setOpen(o => !o)}
      >
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        {open ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
      </button>
      {open && <div className="p-4 space-y-2">{children}</div>}
    </div>
  );
}

function KVRow({ label, value }: { label: string; value?: string | number }) {
  if (value === undefined || value === null || value === '') return null;
  return (
    <div className="flex gap-2">
      <span className="text-gray-400 min-w-[140px] text-sm">{label}:</span>
      <span className="text-white text-sm">{String(value)}</span>
    </div>
  );
}

export default function Marketing() {
  const navigate = useNavigate();
  const [strategy, setStrategy] = useState<any>(null);

  useEffect(() => {
    const stored = sessionStorage.getItem('marketingStrategy');
    if (stored) {
      try { setStrategy(JSON.parse(stored)); } catch { /* ignore */ }
    }
  }, []);

  if (!strategy) {
    return (
      <div className="container mx-auto px-4 py-8 bg-black min-h-screen">
        <p className="text-gray-400">No strategy found. Please generate one from the Results page.</p>
        <Button onClick={() => navigate('/')} className="mt-4">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Dashboard
        </Button>
      </div>
    );
  }

  const stp = strategy.stp || {};
  const swot = strategy.swot || {};
  const pestel = strategy.pestel || {};
  const ca = strategy.competitor_analysis || {};
  const mix = strategy.marketing_mix || {};
  const branding = strategy.branding || {};
  const channels: any[] = strategy.channels || [];
  const content = strategy.content_strategy || {};
  const launch = strategy.launch_plan || {};
  const funnel = strategy.growth_funnel || {};
  const evidence: any[] = strategy.evidence_ledger || [];
  const validation = strategy.validation_report || {};

  return (
    <div className="container mx-auto px-4 py-8 space-y-6 bg-black min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Marketing Strategy</h1>
          <p className="text-gray-400 text-sm mt-1">{strategy.product_name} · {strategy.category}</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={strategy.analysis_status || 'ok'} />
          <span className="text-gray-400 text-sm">
            Confidence: {strategy.confidence_score !== undefined
              ? `${(strategy.confidence_score * 100).toFixed(0)}%`
              : 'N/A'}
          </span>
          <Button variant="outline" onClick={() => navigate('/results')}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Results
          </Button>
        </div>
      </div>

      {/* STP */}
      <Section title="STP Analysis">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {['segmentation', 'targeting', 'positioning'].map(k => (
            <div key={k} className="p-3 bg-white/5 rounded border border-white/10">
              <h3 className="text-cyan-400 font-medium capitalize mb-2">{k}</h3>
              <pre className="text-gray-300 text-xs whitespace-pre-wrap">
                {typeof stp[k] === 'object' ? JSON.stringify(stp[k], null, 2) : stp[k] || '-'}
              </pre>
            </div>
          ))}
        </div>
      </Section>

      {/* SWOT */}
      <Section title="SWOT Analysis">
        <div className="grid grid-cols-2 gap-4">
          {[
            { key: 'strengths', color: 'green' },
            { key: 'weaknesses', color: 'red' },
            { key: 'opportunities', color: 'cyan' },
            { key: 'threats', color: 'yellow' },
          ].map(({ key, color }) => (
            <div key={key} className={`p-3 bg-${color}-500/10 border border-${color}-500/20 rounded`}>
              <h3 className={`text-${color}-400 font-medium capitalize mb-2`}>{key}</h3>
              <ul className="list-disc list-inside space-y-1">
                {(swot[key] || []).map((item: string, i: number) => (
                  <li key={i} className="text-gray-300 text-sm">{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>

      {/* PESTEL */}
      <Section title="PESTEL Analysis">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {Object.entries(pestel).map(([k, v]) => (
            <div key={k} className="p-3 bg-white/5 rounded border border-white/10">
              <h4 className="text-indigo-400 font-medium capitalize text-sm mb-1">{k}</h4>
              <p className="text-gray-300 text-xs">{String(v)}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Competitor Analysis */}
      <Section title="Competitor Analysis">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h3 className="text-white font-medium mb-2 text-sm">Porter's Five Forces</h3>
            <div className="space-y-2">
              {Object.entries(ca.five_forces || {}).map(([k, v]) => (
                <div key={k} className="flex justify-between items-center py-1 border-b border-white/10">
                  <span className="text-gray-400 text-sm capitalize">{k.replace(/_/g, ' ')}</span>
                  <span className="text-white text-sm">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 className="text-white font-medium mb-2 text-sm">Key Competitors</h3>
            <ul className="list-disc list-inside space-y-1">
              {(ca.key_competitors || []).map((c: string, i: number) => (
                <li key={i} className="text-gray-300 text-sm">{c}</li>
              ))}
            </ul>
            {ca.price_band && (
              <div className="mt-3 p-2 bg-white/5 rounded text-sm">
                <span className="text-gray-400">Price band: </span>
                <span className="text-white">
                  {ca.price_band.min?.toLocaleString()} – {ca.price_band.max?.toLocaleString()} {ca.price_band.currency}
                </span>
              </div>
            )}
          </div>
        </div>
      </Section>

      {/* 4Ps */}
      <Section title="Marketing Mix (4Ps)">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {['product', 'price', 'place', 'promotion'].map(p => (
            <div key={p} className="p-3 bg-white/5 rounded border border-white/10">
              <h3 className="text-purple-400 font-medium capitalize mb-2">{p}</h3>
              <pre className="text-gray-300 text-xs whitespace-pre-wrap">
                {typeof mix[p] === 'object' ? JSON.stringify(mix[p], null, 2) : mix[p] || '-'}
              </pre>
            </div>
          ))}
        </div>
      </Section>

      {/* Branding */}
      <Section title="Branding">
        <KVRow label="Value Proposition" value={branding.value_proposition} />
        <KVRow label="Tone" value={branding.tone} />
        <KVRow label="Tagline" value={branding.tagline} />
      </Section>

      {/* Channels */}
      <Section title="Channel Plan">
        <div className="space-y-2">
          {channels.map((ch: any, i: number) => (
            <div key={i} className="flex items-start gap-3 p-3 bg-white/5 rounded border border-white/10">
              <span className="text-cyan-400 font-bold text-sm w-6">{ch.priority || i + 1}</span>
              <div>
                <p className="text-white font-medium text-sm">{ch.name}</p>
                <p className="text-gray-400 text-xs">{ch.rationale}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Growth Funnel */}
      <Section title={`Growth Funnel (${funnel.model || 'AARRR'})`}>
        <div className="flex gap-2 flex-wrap">
          {(funnel.stages || []).map((s: any, i: number) => (
            <div key={i} className="flex-1 min-w-[120px] p-3 bg-white/5 rounded border border-white/10 text-center">
              <p className="text-cyan-400 font-medium text-sm">{s.stage}</p>
              <p className="text-gray-300 text-xs mt-1">{s.metric}</p>
              {s.target && <p className="text-white text-xs mt-1">Target: {s.target}</p>}
            </div>
          ))}
        </div>
      </Section>

      {/* Launch Plan */}
      <Section title="Launch Plan">
        <div className="space-y-3">
          {(launch.phases || []).map((ph: any, i: number) => (
            <div key={i} className="p-3 bg-white/5 rounded border border-white/10">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-purple-400 font-medium text-sm">{ph.name}</span>
                <span className="text-gray-500 text-xs">· {ph.duration}</span>
              </div>
              <ul className="list-disc list-inside space-y-1">
                {(ph.actions || []).map((a: string, j: number) => (
                  <li key={j} className="text-gray-300 text-xs">{a}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        {(launch.kpis || []).length > 0 && (
          <div className="mt-4">
            <h3 className="text-white font-medium text-sm mb-2">KPIs</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {(launch.kpis || []).map((k: any, i: number) => (
                <div key={i} className="p-2 bg-white/5 rounded text-xs">
                  <span className="text-cyan-400">{k.metric}: </span>
                  <span className="text-white">{k.target} ({k.period})</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Section>

      {/* Evidence Ledger */}
      <Section title="Evidence Ledger">
        <div className="space-y-2">
          {evidence.map((e: any, i: number) => (
            <div key={i} className="p-2 bg-white/5 rounded border border-white/10 text-xs">
              <p className="text-white">{e.recommendation}</p>
              <p className="text-gray-400 mt-1">Evidence: {(e.evidence || []).join(', ')}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Validation Report */}
      <Section title="Validation Report">
        <div className="flex items-center gap-2 mb-3">
          <StatusBadge status={validation.status || 'ok'} />
        </div>
        {(validation.flags || []).length > 0 && (
          <div>
            <p className="text-yellow-400 text-sm font-medium mb-1">Flags:</p>
            <ul className="list-disc list-inside space-y-1">
              {(validation.flags || []).map((f: string, i: number) => (
                <li key={i} className="text-gray-300 text-sm">{f}</li>
              ))}
            </ul>
          </div>
        )}
      </Section>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/salik-frontend/src/pages/Marketing.tsx
git commit -m "feat: Marketing strategy display page"
```

---

## Task 10: Frontend — History Page, Navbar, App Routes

**Files:**
- Create: `frontend/salik-frontend/src/pages/MarketingHistory.tsx`
- Modify: `frontend/salik-frontend/src/components/Navbar.tsx`
- Modify: `frontend/salik-frontend/src/App.tsx`

- [ ] **Step 1: Create MarketingHistory.tsx**

Create `frontend/salik-frontend/src/pages/MarketingHistory.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, History } from 'lucide-react';
import Button from '@/components/ui/Button';
import { marketingService } from '@/services/api';

function StatusDot({ status }: { status: string }) {
  const color = status === 'ok' ? 'bg-green-400' : status === 'needs_review' ? 'bg-yellow-400' : 'bg-red-400';
  return <span className={`inline-block w-2 h-2 rounded-full ${color}`} />;
}

export default function MarketingHistory() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    marketingService.getHistory(20)
      .then(data => setRows(data.strategies))
      .catch(err => setError(err.message || 'Failed to load history'))
      .finally(() => setLoading(false));
  }, []);

  const handleRowClick = async (id: string) => {
    try {
      const strategy = await marketingService.getById(id);
      sessionStorage.setItem('marketingStrategy', JSON.stringify(strategy));
      navigate('/marketing');
    } catch {
      setError('Failed to load strategy');
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 bg-black min-h-screen space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <History className="h-6 w-6 text-purple-400" />
          <h1 className="text-3xl font-bold text-white">Marketing History</h1>
        </div>
        <Button variant="outline" onClick={() => navigate('/')}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Dashboard
        </Button>
      </div>

      {loading && <p className="text-gray-400">Loading...</p>}
      {error && <p className="text-red-400">{error}</p>}

      {!loading && rows.length === 0 && (
        <p className="text-gray-400">No strategies generated yet. Run one from the Results page.</p>
      )}

      {rows.length > 0 && (
        <div className="border border-white/10 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-white/5 text-gray-400 text-left">
              <tr>
                <th className="px-4 py-3">Product</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Confidence</th>
                <th className="px-4 py-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row: any) => (
                <tr
                  key={row.id}
                  className="border-t border-white/5 hover:bg-white/5 cursor-pointer transition-colors"
                  onClick={() => handleRowClick(row.id)}
                >
                  <td className="px-4 py-3 text-white font-medium">{row.product_name}</td>
                  <td className="px-4 py-3 text-gray-400">{row.category}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-2">
                      <StatusDot status={row.analysis_status} />
                      <span className="text-gray-300 capitalize">{row.analysis_status?.replace('_', ' ')}</span>
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    {row.confidence_score !== null
                      ? `${(row.confidence_score * 100).toFixed(0)}%`
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(row.created_at).toLocaleDateString('en-PK', {
                      day: 'numeric', month: 'short', year: 'numeric',
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add Marketing links to Navbar**

Open `frontend/salik-frontend/src/components/Navbar.tsx`. Read it first to find where nav links are listed. Add two new entries alongside the existing links:

```tsx
{ to: '/marketing/history', label: 'History', icon: <History className="h-4 w-4" /> },
```

Also add the import at the top if not already present:
```tsx
import { History } from 'lucide-react';
```

- [ ] **Step 3: Add routes to App.tsx**

Open `frontend/salik-frontend/src/App.tsx`. Add the two new imports at the top:

```tsx
import Marketing from '@/pages/Marketing';
import MarketingHistory from '@/pages/MarketingHistory';
```

Inside the `<Routes>` block, add:

```tsx
<Route path="/marketing" element={<Marketing />} />
<Route path="/marketing/history" element={<MarketingHistory />} />
```

- [ ] **Step 4: Verify frontend builds without errors**

```bash
cd frontend/salik-frontend
npm run build
```

Expected: build succeeds with no TypeScript errors. Fix any type errors before proceeding.

- [ ] **Step 5: Commit**

```bash
git add frontend/salik-frontend/src/pages/MarketingHistory.tsx \
        frontend/salik-frontend/src/components/Navbar.tsx \
        frontend/salik-frontend/src/App.tsx
git commit -m "feat: marketing history page, navbar links, and app routes"
```

---

## Task 11: End-to-End Smoke Test

- [ ] **Step 1: Make sure Ollama is running with the right model**

```bash
ollama pull llama3.1:8b
ollama serve
```

In a second terminal, verify:
```bash
ollama list
```

Expected: `llama3.1:8b` appears in the list.

- [ ] **Step 2: Start the backend**

```bash
cd StrategaAi
venv/Scripts/uvicorn app.main:app --port 8001 --reload
```

- [ ] **Step 3: Start the dashboard frontend**

```bash
cd frontend/salik-frontend
npm run dev
```

- [ ] **Step 4: Run a full flow**

1. Open `http://localhost:5173`
2. Search for a product (e.g., "Sony WH-1000XM5", category "headsets")
3. Wait for scrape + analytics to complete → you land on Results page
4. Click **"Generate Marketing Strategy"** — spinner appears
5. After 15–60 seconds, you are redirected to `/marketing`
6. Verify: STP, SWOT, PESTEL, 4Ps, Channels, Growth Funnel, Launch Plan, Evidence Ledger, Validation Report all have content
7. Open `http://localhost:5173/marketing/history` — row for this run should appear

- [ ] **Step 5: Run the full backend test suite**

```bash
cd StrategaAi
venv/Scripts/python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete marketing agent integration — end-to-end working"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Perceive → Enrich → Generate → Validate → Critic → Store lifecycle (Tasks 3–6)
- ✅ STP, SWOT, PESTEL, 4Ps, Five Forces, AARRR in system prompt (Task 4)
- ✅ Evidence grounding required in prompt (Task 4)
- ✅ Validation layer: schema check, confidence range, evidence_ledger, kpis (Task 5)
- ✅ Critic (second-pass) pass with flags (Task 6)
- ✅ DB persistence to marketing_strategies (Tasks 1, 2, 6)
- ✅ On-demand from Results page button (Task 8)
- ✅ Strategy display page with all sections (Task 9)
- ✅ History page with table and row-click (Task 10)
- ✅ OLLAMA_BASE_URL and OLLAMA_MODEL env vars (Task 7)
- ✅ Pakistan e-commerce context injected into prompt (Task 4)
- ✅ Sanitization of scraped review text in Enrich (Task 3)

**Type consistency:** `_perceive` returns `perceived` dict → passed to `_enrich` → `enriched` dict → passed to `_generate`. `_validate(strategy, perceived)` matches call in `run()`. `_critic(validated, enriched)` matches. `_store(final, product_name, category, pipeline_run_id)` matches. All consistent.

**Placeholder scan:** No TBDs or incomplete steps found.
