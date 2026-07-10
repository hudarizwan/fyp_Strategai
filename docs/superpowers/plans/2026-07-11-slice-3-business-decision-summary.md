# Slice 3 Business Decision Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact, deterministic `business_decision_summary` to StrategAI's marketing response path, backed by a richer category playbook and evidence-referenced recommendation cards, without changing scraper behavior, API contracts, or the existing workflow.

**Architecture:** The marketing layer remains the final aggregation point. It will transform analytics output into structured business state, enrich it with category playbook data, produce recommendation cards that reference existing evidence by field path or ID, and then build a deterministic executive summary from analytics, marketing, and resolved MCB threshold metadata. The summary stays small and additive so the frontend and report flow can consume it without any contract churn.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, PostgreSQL/Supabase via `ECDB`, Ollama only for existing marketing generation, Pytest.

## Global Constraints

- Preserve scraper behavior.
- Preserve existing API contracts.
- Preserve frontend compatibility.
- Preserve the workflow: `Scrape -> NLP -> Analytics -> Marketing -> MCB Decision -> Report`.
- Keep `business_decision_summary` compact and executive-facing.
- Keep the Category Playbook as structured data only, not embedded decision logic.
- Recommendation cards must reference existing evidence by field path or ID instead of duplicating source blobs.
- The executive summary must remain deterministic and must not invoke the LLM.
- No new MCB API route is required for this slice.
- Threshold resolution order remains exact category, then `general_retail`, then hardcoded `0.70`.
- The overall score must use a documented deterministic weighting formula.

---

### Task 1: Expand Category Playbook and Recommendation Card Helpers

**Files:**
- Modify: `backend/app/services/marketing_prompt_builder.py`
- Modify: `backend/tests/test_marketing_agent.py`

**Interfaces:**
- Consumes: `perceived`, `analytics_result`, `enriched`, and the existing marketing strategy structure.
- Produces: richer `category_playbook` entries, plus recommendation card structures with `confidence`, `reason`, and `evidence_refs`.

- [ ] **Step 1: Write the failing test**

```python
from app.services.marketing_prompt_builder import build_business_state, build_recommendation_cards


def test_recommendation_cards_reference_evidence_paths():
    perceived = {"product_name": "Gaming Headset", "category": "headsets", "confidence_score": 0.84, "margin_percent": 28.0, "vendor_count": 5, "seller_count": 9}
    analytics_result = {"primary_pricing_mode": "balanced", "pricing_decision_summary": {"selection_reason": ["Balanced pricing strategy selected"]}, "market_intelligence": {"market_opportunity_score": 78.0}}
    enriched = {"competitor_count": 9, "price_band": {"min": 3800, "max": 5100, "avg": 4400, "currency": "PKR"}}
    strategy = {"marketing_decision_summary": {"selected_positioning": "Mid-range Premium"}, "channels": [{"name": "TikTok"}]}
    business_state = build_business_state(perceived, analytics_result, enriched)
    cards = build_recommendation_cards(strategy, business_state)
    assert cards[0]["evidence_refs"]
    assert cards[0]["confidence"] in {"High", "Medium", "Low"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_marketing_agent.py -k recommendation_cards_reference_evidence_paths -v`
Expected: FAIL because `build_recommendation_cards` does not exist yet or does not emit `evidence_refs`.

- [ ] **Step 3: Write minimal implementation**

```python
CATEGORY_PLAYBOOKS = {
    "gaming_headsets": {
        "positioning": "Mid-range Premium",
        "primary_channels": ["Daraz", "TikTok", "Instagram"],
        "buying_factors": ["Comfort", "Microphone", "Warranty", "RGB"],
        "promotion_hooks": ["Video demonstrations", "Bundles", "Warranty proof"],
        "typical_margin_band": {"min": 30, "max": 45},
        "seasonality": "Back-to-school",
        "recommended_content": "Short-form video demos",
        "risk_notes": ["Competition can be intense during promotions"],
    },
}


def build_recommendation_cards(strategy, business_state):
    return [
        {
            "type": "positioning",
            "recommendation": strategy["marketing_decision_summary"]["selected_positioning"],
            "confidence": business_state["market_state"]["confidence"].title(),
            "reason": "Aligned with current pricing strategy and category playbook.",
            "evidence_refs": ["pricing_decision_summary.selection_reason", "market_state.pricing_strategy"],
        }
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_marketing_agent.py -k recommendation_cards_reference_evidence_paths -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/marketing_prompt_builder.py backend/tests/test_marketing_agent.py
git commit -m "feat: add structured category playbook cards"
```

### Task 2: Add Deterministic Business Summary Builder

**Files:**
- Create: `backend/app/services/business_decision_summary.py`
- Create: `backend/tests/test_business_decision_summary.py`

**Interfaces:**
- Consumes: analytics result, marketing result, resolved threshold context.
- Produces: `business_decision_summary` with `overall_recommendation`, `overall_score`, `executive_summary`, `top_strengths`, `major_risks`, `recommended_next_action`, `decision_score_breakdown`, `threshold_context`, and `approval_readiness`.

- [ ] **Step 1: Write the failing test**

```python
from app.services.business_decision_summary import build_business_decision_summary


def test_build_business_decision_summary_uses_documented_weights():
    analytics_result = {
        "expected_profit_margin": 40.0,
        "confidence_score": 0.91,
        "market_intelligence": {
            "opportunity_score": 88.0,
            "supplier_quality_score": 80.0,
        },
    }
    marketing_result = {"marketing_readiness_score": 88}
    threshold_context = {
        "confidence_threshold": 0.70,
        "threshold_source_tier": "exact category",
        "threshold_source_category": "headsets",
    }
    summary = build_business_decision_summary(analytics_result, marketing_result, threshold_context)
    assert summary["overall_score"] == 91
    assert summary["decision_score_breakdown"]["profitability"] == 27
    assert summary["approval_readiness"] == "READY"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_business_decision_summary.py -v`
Expected: FAIL because the module and helper do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
WEIGHTS = {
    "profitability": 0.30,
    "market_opportunity": 0.25,
    "supplier_quality": 0.15,
    "marketing_readiness": 0.15,
    "confidence": 0.15,
}


def build_business_decision_summary(analytics_result, marketing_result, threshold_context):
    profitability = round((analytics_result["expected_profit_margin"] / 40.0) * 100.0)
    market_opportunity = round(analytics_result["market_intelligence"]["opportunity_score"])
    supplier_quality = round(analytics_result["market_intelligence"]["supplier_quality_score"])
    marketing_readiness = round(marketing_result["marketing_readiness_score"])
    confidence = round(analytics_result["confidence_score"] * 100.0)

    decision_score_breakdown = {
        "profitability": round(profitability * WEIGHTS["profitability"]),
        "market_opportunity": round(market_opportunity * WEIGHTS["market_opportunity"]),
        "supplier_quality": round(supplier_quality * WEIGHTS["supplier_quality"]),
        "marketing_readiness": round(marketing_readiness * WEIGHTS["marketing_readiness"]),
        "confidence": round(confidence * WEIGHTS["confidence"]),
    }
    overall_score = sum(decision_score_breakdown.values())
    if overall_score >= 85 and analytics_result["confidence_score"] >= threshold_context["confidence_threshold"]:
        approval_readiness = "READY"
    elif overall_score >= 70:
        approval_readiness = "CAUTION"
    elif overall_score >= 55:
        approval_readiness = "REVIEW"
    else:
        approval_readiness = "DO_NOT_LAUNCH"

    return {
        "overall_recommendation": "Launch" if approval_readiness in {"READY", "CAUTION"} else "Hold",
        "overall_score": overall_score,
        "executive_summary": "Balanced pricing, strong supplier quality, and market demand support launch readiness.",
        "top_strengths": ["Healthy margin", "Strong supplier", "Clear positioning"],
        "major_risks": ["Competition is moderate"],
        "recommended_next_action": "Launch within two weeks.",
        "decision_score_breakdown": decision_score_breakdown,
        "approval_readiness": approval_readiness,
        "threshold_context": threshold_context,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_business_decision_summary.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/business_decision_summary.py backend/tests/test_business_decision_summary.py
git commit -m "feat: add deterministic business summary builder"
```

### Task 3: Wire Marketing Response to the Executive Summary

**Files:**
- Modify: `backend/app/services/marketing_agent.py`
- Modify: `backend/app/services/marketing_prompt_builder.py`
- Modify: `backend/tests/test_marketing_agent.py`

**Interfaces:**
- Consumes: `ECDB.resolve_mcb_confidence_threshold(category)`, existing analytics result, structured marketing output, and the new business summary builder.
- Produces: final marketing response that includes `business_decision_summary` and keeps `marketing_decision_summary` intact.

- [ ] **Step 1: Write the failing test**

```python
import json as _json
from unittest.mock import patch


def test_run_attaches_business_decision_summary():
    agent = _make_agent()
    stored_row = {"id": "abc-123", **MINIMAL_VALID_STRATEGY, "product_name": "Sony WH-1000XM5", "category": "headsets"}
    with patch.object(agent.db, "resolve_mcb_confidence_threshold", return_value={
        "confidence_threshold": 0.70,
        "threshold_source_tier": "exact category",
        "threshold_source_category": "headsets",
    }), patch.object(agent.db, "insert_marketing_strategy", return_value=stored_row), patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response(_json.dumps(MINIMAL_VALID_STRATEGY))
        result = agent.run("Sony WH-1000XM5", "headsets", VALID_ANALYTICS, VALID_SCRAPER)
    assert result["business_decision_summary"]["threshold_context"]["threshold_source_tier"] in {
        "exact category", "general_retail", "hardcoded 0.70"
    }
    assert result["business_decision_summary"]["approval_readiness"] in {
        "READY", "CAUTION", "REVIEW", "DO_NOT_LAUNCH"
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_marketing_agent.py -k business_decision_summary -v`
Expected: FAIL because the response does not yet include `business_decision_summary`.

- [ ] **Step 3: Write minimal implementation**

```python
threshold_context = self.db.resolve_mcb_confidence_threshold(category)
marketing_result = self._ensure_marketing_decision_summary(final, business_state)
final["business_decision_summary"] = build_business_decision_summary(
    analytics_result=analytics_result,
    marketing_result=marketing_result,
    threshold_context=threshold_context,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_marketing_agent.py -k business_decision_summary -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/marketing_agent.py backend/app/services/marketing_prompt_builder.py backend/tests/test_marketing_agent.py
git commit -m "feat: attach business decision summary to marketing response"
```

### Task 4: Full Backend Verification and Cleanup

**Files:**
- Modify: `backend/tests/test_marketing_agent.py`
- Modify: `backend/tests/test_business_decision_summary.py`
- Modify: any touched service files from the previous tasks if test failures require cleanup

**Interfaces:**
- Consumes: final marketing response, deterministic summary builder, category playbook helpers.
- Produces: a clean backend test suite proving the new executive summary flow is additive and deterministic.

- [ ] **Step 1: Run the focused test set**

Run:
`python -m pytest backend/tests/test_business_decision_summary.py backend/tests/test_marketing_agent.py -q -p no:cacheprovider`
Expected: all tests pass.

- [ ] **Step 2: Run the broader backend checks**

Run:
`python -m pytest backend/tests -q -p no:cacheprovider`
Expected: backend test suite stays green, with only unrelated pre-existing issues called out if any remain.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/*.py backend/tests/*.py
git commit -m "test: verify slice 3 business recommendation flow"
```

## Self-Review Coverage Check

- Category playbook structure: Task 1
- Evidence-backed recommendation cards: Task 1 and Task 3
- Deterministic executive summary: Task 2
- Deterministic weighted score formula: Task 2
- Threshold context and source tier: Task 3
- Approval readiness mapping: Task 2 and Task 3
- No LLM call for the executive summary: Task 2 and Task 3
- Additive contract compatibility: Task 3 and Task 4
