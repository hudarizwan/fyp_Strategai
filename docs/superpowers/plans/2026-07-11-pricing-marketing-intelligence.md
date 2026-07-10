# Pricing and Marketing Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make StrategAI behave like an AI business consultant by adding multi-strategy pricing, evidence-based explainability, market opportunity scoring, supplier ranking, and analytics-driven marketing without changing the scraper, frontend architecture, or API contracts.

**Architecture:** Keep the live request flow intact: analytics produces a richer commercial intelligence payload, marketing consumes that payload, and the decision layer uses the same response contract with deeper internal reasoning. The new logic is deterministic-first, with the LLM used only for narrative expression and not as the source of business truth.

**Tech Stack:** FastAPI, Pydantic, Python services under `backend/app/services`, existing Supabase/Postgres persistence, existing Ollama marketing generation, existing pytest suite.

## Global Constraints

- Do not modify scraper logic or add new scraping targets.
- Do not change frontend architecture or API response contracts.
- Preserve existing endpoints and workflows.
- Keep all new intelligence inside backend service layers and existing response metadata.
- Use deterministic business rules to enforce structural limits before or after LLM generation.
- Keep marketing output grounded in analytics and market evidence rather than generic LLM prose.
- Maintain compatibility with existing tests and live storage paths.

---

### Task 1: Pricing mode engine and commercial intelligence schema

**Files:**
- Modify: `backend/app/services/commercial_intelligence.py`
- Modify: `backend/app/services/analytics_agent.py`
- Modify: `backend/app/services/mcb_models.py`
- Test: `backend/tests/test_analytics_agent.py`
- Test: `backend/tests/test_mcb_decision_agent.py`

**Interfaces:**
- Consumes: current wholesale/retail metrics, `confidence_score`, `low_sample_warning`, `price_band`, category family detection.
- Produces: structured pricing mode snapshot with `competitive`, `balanced`, `premium`, and `psychological` variants, plus one primary mode and supporting alternates.

- [ ] **Step 1: Write the failing pricing-mode tests**

```python
def test_commercial_intelligence_returns_four_pricing_modes():
    snapshot = build_commercial_intelligence_snapshot(...)
    assert set(snapshot["pricing_modes"]) == {"competitive", "balanced", "premium", "psychological"}
    assert snapshot["primary_pricing_mode"] in snapshot["pricing_modes"]

def test_primary_mode_changes_with_market_shape():
    weak_market = build_commercial_intelligence_snapshot(...)
    strong_market = build_commercial_intelligence_snapshot(...)
    assert weak_market["primary_pricing_mode"] != strong_market["primary_pricing_mode"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
PYTHONPATH=backend python -m pytest backend/tests/test_analytics_agent.py -k pricing_mode -q
```
Expected: fail because the pricing-mode fields do not exist yet.

- [ ] **Step 3: Implement the pricing-mode engine**

```python
def build_pricing_mode_snapshot(...):
    # Build deterministic candidate prices for competitive, balanced, premium, psychological
    # Rank modes by margin safety, market fit, and confidence
    # Return primary_pricing_mode, alternate_pricing_modes, and evidence reasons
```

- [ ] **Step 4: Wire the snapshot into analytics output**

```python
def _build_commercial_intelligence(...):
    pricing_modes = build_pricing_mode_snapshot(...)
    return {
        "pricing_modes": pricing_modes,
        "primary_pricing_mode": pricing_modes["primary_pricing_mode"],
        "alternate_pricing_modes": pricing_modes["alternate_pricing_modes"],
        ...
    }
```

- [ ] **Step 5: Run the targeted tests**

Run:
```bash
PYTHONPATH=backend python -m pytest backend/tests/test_analytics_agent.py backend/tests/test_mcb_decision_agent.py -q
```
Expected: pass for pricing-mode coverage.

---

### Task 2: Explainable market intelligence, supplier ranking, and opportunity scoring

**Files:**
- Modify: `backend/app/services/commercial_intelligence.py`
- Modify: `backend/app/services/analytics_agent.py`
- Modify: `backend/app/services/report_renderer.py`
- Test: `backend/tests/test_reports.py`
- Test: `backend/tests/test_analytics_agent.py`

**Interfaces:**
- Consumes: pricing-mode snapshot, wholesale/retail metrics, category family.
- Produces: `market_opportunity`, `supplier_rankings`, category-aware business notes, and evidence-led rationale lists.

- [ ] **Step 1: Write tests for evidence-led outputs**

```python
def test_market_intelligence_includes_supplier_rankings():
    snapshot = build_commercial_intelligence_snapshot(...)
    assert snapshot["supplier_rankings"]
    assert snapshot["market_opportunity"]["score"] >= 0

def test_report_renders_primary_mode_and_alternates():
    html = build_report_html(report)
    assert "Primary Pricing Mode" in html
    assert "Alternative Modes" in html
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run:
```bash
PYTHONPATH=backend python -m pytest backend/tests/test_analytics_agent.py backend/tests/test_reports.py -q
```
Expected: fail because the new evidence fields are not yet rendered everywhere.

- [ ] **Step 3: Add supplier ranking and opportunity scoring**

```python
def build_supplier_rankings(wholesale_metrics, combined_metrics):
    # Score suppliers by price, MOQ burden, variance stability, and source diversity
    # Return ranked suppliers and a short explanation per entry
```

```python
def build_market_opportunity_snapshot(...):
    # Compute demand, competition, supplier strength, risk, and opportunity
    # Return explanation bullets tied to source metrics
```

- [ ] **Step 4: Surface the new fields in analytics and report rendering**

```python
recommendation["market_opportunity"] = ...
recommendation["supplier_rankings"] = ...
recommendation["business_insights"] = ...
```

- [ ] **Step 5: Run the tests again**

Run:
```bash
PYTHONPATH=backend python -m pytest backend/tests/test_analytics_agent.py backend/tests/test_reports.py -q
```
Expected: pass.

---

### Task 3: Marketing strategies driven by analytics outputs

**Files:**
- Modify: `backend/app/services/marketing_prompt_builder.py`
- Modify: `backend/app/services/marketing_agent.py`
- Modify: `backend/app/services/mcb_models.py`
- Test: `backend/tests/test_marketing_agent.py`

**Interfaces:**
- Consumes: pricing mode, confidence band, low-sample warning, opportunity score, supplier rankings, evidence ledger, category playbook.
- Produces: structurally constrained marketing output that scales launch scope, channel breadth, and KPI ambition from analytics quality.

- [ ] **Step 1: Write tests that assert structural marketing differences**

```python
def test_low_confidence_strategies_are_narrower():
    limited = agent._build_fast_path_strategy(enriched_limited, context_limited)
    strong = agent._build_fast_path_strategy(enriched_strong, context_strong)
    assert len(limited["channels"]) < len(strong["channels"])
    assert len(limited["launch_plan"]["kpis"]) <= len(strong["launch_plan"]["kpis"])
```

- [ ] **Step 2: Run the tests and confirm they fail first**

Run:
```bash
PYTHONPATH=backend python -m pytest backend/tests/test_marketing_agent.py -q
```
Expected: fail until the prompt builder and deterministic post-processing are updated.

- [ ] **Step 3: Feed the analytics intelligence into the prompt builder**

```python
def build_compact_analytics_summary(enriched):
    # Include pricing_modes, primary_pricing_mode, market_opportunity, supplier_rankings, and evidence_ledger
```

```python
def build_marketing_system_prompt(strategy_context, pakistan_context):
    # Tell the model to obey the selected pricing mode and quality band
```

- [ ] **Step 4: Enforce structural limits in the marketing agent**

```python
def _apply_quality_band_limits(strategy, strategy_context):
    # Clamp channel count, KPI count, launch scope, and content cadence deterministically
```

- [ ] **Step 5: Run the tests**

Run:
```bash
PYTHONPATH=backend python -m pytest backend/tests/test_marketing_agent.py -q
```
Expected: pass with the new quality-band structural enforcement.

---

### Task 4: Decision-layer alignment and traceability polish

**Files:**
- Modify: `backend/app/services/mcb_scoring.py`
- Modify: `backend/app/services/mcb_decision_agent.py`
- Modify: `backend/app/api/analytics.py`
- Test: `backend/tests/test_mcb_decision_agent.py`

**Interfaces:**
- Consumes: analytics commercial intelligence and marketing strategy metadata.
- Produces: a richer confidence breakdown and a reasoning trail that names the pricing mode and business-quality drivers.

- [ ] **Step 1: Write tests for reasoning-trail coverage**

```python
def test_reasoning_trail_mentions_pricing_mode():
    decision = agent.decide(payload)
    assert any("pricing mode" in item.lower() for item in decision.reasoning_trail)
```

- [ ] **Step 2: Run the tests to see the current gap**

Run:
```bash
PYTHONPATH=backend python -m pytest backend/tests/test_mcb_decision_agent.py -q
```
Expected: fail until the reasoning trail includes the new business-intelligence language.

- [ ] **Step 3: Update the score breakdown and decision explanation**

```python
def compute_final_confidence(payload, flags):
    # Add pricing quality, demand, competition, data quality, risk, and marketing readiness
```

```python
def _build_reasoning_trail(...):
    # Mention the resolved pricing mode, opportunity score, supplier quality, and threshold source
```

- [ ] **Step 4: Run the decision tests**

Run:
```bash
PYTHONPATH=backend python -m pytest backend/tests/test_mcb_decision_agent.py -q
```
Expected: pass.

---

## Spec Coverage Check

- Multi-strategy pricing: Task 1
- Evidence-based explainability: Tasks 1 and 2
- Marketing driven by analytics outputs: Task 3
- Market opportunity assessment: Task 2
- Supplier ranking: Task 2
- Category-aware business knowledge: Tasks 1 and 3
- No scraper changes: Global Constraints
- No frontend or API contract changes: Global Constraints and Tasks 2-4

## Self-Review Notes

- No placeholders remain.
- File boundaries stay focused on backend service layers.
- The plan preserves live workflows and keeps the scraper untouched.
- The pricing and marketing behaviors are split into reviewable slices, with tests before implementation in each task.
