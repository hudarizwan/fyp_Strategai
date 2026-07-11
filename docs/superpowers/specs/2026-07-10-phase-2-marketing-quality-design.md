# Phase 2 Marketing Quality Design
**Date:** 2026-07-10
**Project:** StrategAI
**Status:** Draft

---

## 1. Goal

Make the marketing strategy generation pipeline respond structurally to analytics quality so low-confidence or low-sample products produce narrower, more cautious strategies, while high-confidence products can generate broader and more ambitious strategies.

This phase is not about prettier wording alone. The pipeline must enforce quality-aware limits in code so the final stored strategy and returned response comply even if the LLM is overconfident or generic.

---

## 2. Scope

This phase covers:
- extending the marketing API contract so analytics quality signals reach the marketing pipeline
- building a dedicated marketing quality context separate from MCB approval thresholds
- threading quality context into prompt building and strategy metadata
- adding deterministic post-processing that enforces structural limits by quality band
- adding tests that verify both prompt inputs and final enforced strategy shape

Out of scope:
- task queues, Redis, websocket updates, or async orchestration
- marketing caching / deduplication
- frontend redesign beyond any small metadata display needed to explain the final strategy
- changes to analytics scoring itself

---

## 3. Current State

The live marketing path already:
- accepts `product_name`, `category`, `analytics_result`, and `scraper_result`
- builds a strategy context from analytics and scraped market data
- generates a strategy with local Ollama
- validates the response
- optionally runs a critic pass
- stores the final result in Supabase via `marketing_strategies`

The gap is that the current request model only carries a small analytics subset. The prompt builder and agent can see buy/sell prices, confidence, and supplier/seller counts, but low-sample context is not treated as a first-class quality policy. That means strategy breadth still depends too heavily on prompt compliance and implicit model behavior.

---

## 4. Design Decision

Marketing quality must use its own explicit scale, separate from the MCB threshold system.

- MCB threshold remains the approval gate for product decisions.
- Marketing quality band remains the strategy-shaping gate for tone, scope, and ambition.
- The two systems may both consume analytics confidence and sample context, but they must not share a constant or be named as if they are the same policy.

Recommended constant / naming:
- `MARKETING_QUALITY_BANDS`
- optional helper constants such as `MARKETING_LOW_CONFIDENCE_THRESHOLD` and `MARKETING_LOW_SAMPLE_DEFAULTS`

Recommended band labels:
- `high_confidence`
- `moderate_confidence`
- `low_confidence`

The band should be derived from:
- analytics `confidence_score`
- `low_sample_warning`
- supplier / listing counts
- sample thresholds if present

It should not be derived from the MCB threshold value.

---

## 5. Architecture

### 5.1 Data Flow

```
POST /marketing/generate
    -> Marketing API request model
    -> MarketingAgent._perceive()
    -> quality context builder
    -> MarketingAgent._build_strategy_context()
    -> system prompt + user prompt
    -> Ollama draft strategy
    -> validation
    -> deterministic quality-policy enforcement
    -> optional critic repair
    -> final quality enforcement again
    -> store in marketing_strategies
    -> return strategy JSON
```

The important rule is that quality enforcement happens in code, not only in prompt text. Prompting can influence structure, but the policy layer must be the final authority before storage and response.

### 5.2 Quality Context

Add a marketing-specific quality context object with fields like:
- `confidence_score`
- `low_sample_warning`
- `low_sample_reason`
- `wholesale_vendors_count`
- `retail_sellers_count`
- `sample_thresholds`
- `confidence_band`
- `policy_profile`
- `prompt_directives`

This object should be built once and then reused by:
- the system prompt
- the user prompt
- the deterministic policy enforcer
- the stored `strategy_meta`

### 5.3 Deterministic Enforcement

Slice 2 must include a policy function that normalizes the generated strategy into the approved structural band.

Recommended function shape:
- input: generated strategy dict + quality context
- output: enforced strategy dict

Structural limits should include:
- maximum channel count
- maximum launch phases
- KPI target ceilings or scaling factor
- whether broad-channel growth language is allowed
- whether a cautious or aggressive strategic angle is allowed

This policy should operate after generation and before storage. If the critic pass changes the strategy afterward, the policy should run again so the final result still obeys the same rules.

### 5.4 Storage and Metadata

Store the resolved quality band in `strategy_meta` so the Marketing page and history can explain why the strategy looks cautious or aggressive.

Recommended metadata fields:
- `marketing_quality_band`
- `marketing_quality_reason`
- `marketing_quality_inputs`
- `quality_policy_applied`

This keeps the output explainable without conflating it with MCB decision logic.

---

## 6. API Changes

The marketing request model should preserve the analytics quality fields needed to build quality context.

Minimum request additions:
- `low_sample_warning`
- `low_sample_reason`
- `sample_thresholds`
- `wholesale_vendors_count`
- `retail_sellers_count`
- `confidence_score`

If the API currently receives a richer analytics object, the model should explicitly accept and validate those fields rather than dropping them.

The marketing response does not need a new top-level schema for this phase, but it should preserve the structured `strategy_meta` fields so the frontend can explain the quality band later.

---

## 7. Prompt Design

The prompt builder should receive quality context and convert it into concrete instructions.

Prompt guidance should differ by band:
- `high_confidence`: allow broader channel selection, more assertive launch language, stronger KPI ambition
- `moderate_confidence`: balanced scope with practical guardrails
- `low_confidence`: narrow launch scope, trust-heavy messaging, limited channels, conservative KPIs, validation-first rollout

The prompt should also instruct the LLM to:
- keep the strategy grounded in the supplied analytics quality
- avoid overclaiming when the sample is sparse
- cite evidence in the ledger when caution is warranted

Prompting is still useful, but only as an input to the wider policy system. It is not the enforcement mechanism.

---

## 8. Deterministic Policy Rules

The quality policy should be explicit enough to test without depending on the LLM's prose.

Example policy shape:
- `low_confidence`
  - cap channels to 1-2
  - cap launch phases to 1-2
  - reduce KPI targets
  - prefer trust, validation, and proof-heavy language
- `moderate_confidence`
  - allow a standard launch plan
  - moderate KPI targets
  - 2-3 channels
- `high_confidence`
  - allow broader channel coverage
  - more ambitious KPIs
  - a fuller launch structure

The exact numbers should be encoded in the policy layer, not left to prompt interpretation.

The policy should be applied:
- after initial generation
- after critic repair, if critic is enabled
- before store/return

That gives deterministic compliance even when the LLM returns something too broad or too vague.

---

## 9. Testing Strategy

Slice 3 must verify actual enforcement, not only prompt injection.

Required test groups:

### Prompt-input tests
Assert that the marketing prompt builder receives and serializes quality context fields.
These tests verify the contract between analytics and marketing.

### Enforcement tests
Mock the LLM output and assert that the final strategy is structurally different by quality band.
These tests should verify:
- channel count differences
- launch phase count differences
- KPI target differences
- metadata describing the applied quality band

### Regression tests
Assert that:
- high-confidence strategies are not accidentally clamped down to low-sample behavior
- low-confidence strategies are not allowed to keep an overbroad launch plan
- the critic pass does not override the quality policy

The tests should target deterministic helpers and the final stored output, not just raw prompt text.

---

## 10. Implementation Slices

### Slice 1
Extend the marketing request model and build the marketing quality context helper.

### Slice 2
Thread quality context into the prompt builder and add deterministic quality-policy enforcement before storage and response.

### Slice 3
Add tests that verify prompt input content and structural enforcement across quality bands.

---

## 11. Risks

- If quality policy names are too close to MCB threshold names, future maintainers may confuse approval policy with marketing tone policy.
- If enforcement only happens before the critic pass, the critic could reintroduce overbroad output.
- If tests only inspect prompt text, the pipeline could still fail to comply when the LLM ignores instructions.

---

## 12. Success Criteria

- Marketing can see analytics quality signals explicitly.
- Low-confidence / low-sample products produce narrower and more cautious strategies in code, not just in wording.
- High-confidence products retain broader marketing freedom.
- MCB threshold logic stays separate and unchanged.
- Tests prove the enforcement layer works even when the LLM output is mocked.

