# Slice 3 Design: Business Knowledge Layer and Executive Recommendation

## Goal
Turn StrategAI from a pricing-and-marketing pipeline into a compact AI business recommendation system without changing scraper behavior, API contracts, or the existing workflow.

This slice builds three additive capabilities:
1. A richer category playbook / business knowledge layer.
2. Evidence-backed marketing recommendation cards with confidence labels.
3. A concise `business_decision_summary` returned at the end of the marketing response path.

## Decision
Use Option A: keep `business_decision_summary` in the marketing response only.

That keeps the summary at the end of the pipeline, avoids contract changes in analytics, and preserves the current workflow:

`Scrape -> NLP -> Analytics -> Marketing -> MCB Decision -> Report`

## Existing Shape
The current backend already provides most of the raw ingredients:

1. `analytics_agent.py` produces pricing, profitability, risk, confidence, and `pricing_decision_summary`.
2. `commercial_intelligence.py` already contains pricing-mode reasoning, evidence ledgers, and confidence-band logic.
3. `marketing_agent.py` already consumes structured business state, applies consistency checks, and returns `marketing_decision_summary`.
4. `ecdb.py` already resolves MCB thresholds with an exact-category -> `general_retail` -> hardcoded `0.70` fallback chain.

This slice should extend those structures instead of replacing them.

## Design Overview

### 1. Rich Category Playbook
Expand the existing category playbook concept into a lightweight business knowledge layer.

The playbook should remain deterministic and category-specific. Each category entry should include:
- `positioning`
- `primary_channels`
- `buying_factors`
- `promotion_hooks`
- `typical_margin_band`
- `seasonality`
- `recommended_content`
- optional `risk_notes`

The playbook stays as local application knowledge, not a separate ML system or external knowledge base.
It must remain data only, not embedded decision logic.

### 2. Evidence-Backed Recommendation Cards
Marketing should produce structured recommendation cards for the major business decisions it makes.

Each card should include:
- the recommendation text
- a confidence label
- a short reason
- references to existing evidence fields already available in the business state

Examples of card types:
- positioning
- channel selection
- launch scope
- message tone
- risk handling

The card output should be deterministic and post-processed, not left to the LLM to invent from scratch.
The cards should reference evidence using field paths or IDs rather than copying large blobs of source data.

### 3. Executive Summary
Add `business_decision_summary` as a concise executive object in the final marketing response.

It should not duplicate the full pricing summary or marketing summary. Instead it should reference them and present:
- `overall_recommendation`
- `overall_score`
- `executive_summary`
- `top_strengths`
- `major_risks`
- `recommended_next_action`
- `decision_score_breakdown`
- `approval_readiness`
- `threshold_context`

The score should be explainable, with a breakdown showing how pricing, marketing readiness, market opportunity, supplier quality, and confidence contributed to the final score.
The overall score must be calculated by a documented deterministic weighting formula, not an arbitrary or learned value.
The summary must stay compact and fit on one screen.

## Data Flow

1. Analytics produces the primary commercial signal:
   - pricing recommendation
   - profitability
   - market intelligence
   - low-sample warning
   - `pricing_decision_summary`

2. Marketing receives the structured analytics output and transforms it into:
   - `market_state`
   - category playbook context
   - evidence ledger
   - strategy guardrails
   - marketing recommendation cards
   - `marketing_decision_summary`

3. The marketing layer resolves MCB threshold metadata through `ECDB.resolve_mcb_confidence_threshold(category)` when assembling the final executive summary.

4. The final marketing response returns an additive `business_decision_summary` object that combines:
   - analytics confidence and profitability signals
   - marketing readiness
   - resolved threshold tier and value
   - major risks and next action
   - approval readiness derived from the existing decision logic

## Threshold Handling
The executive summary should surface threshold context explicitly so users can see where the approval bar came from.

Resolution order remains:
1. exact category
2. `general_retail`
3. hardcoded `0.70`

The summary should include:
- `confidence_threshold`
- `threshold_source_tier`
- `threshold_source_category`

No new MCB API route is required for this slice.
The executive summary must remain deterministic and must not invoke the LLM.

## API / Contract Rules
Keep all existing request and response contracts compatible.

Allowed:
- additive response fields
- additive helper functions
- additive internal data structures

Avoid:
- renaming existing public response keys
- changing scraper inputs or outputs
- changing the current workflow order
- making analytics or marketing dependent on a new external service

## Error Handling
If category metadata is missing, fall back to the existing general playbook and threshold resolution chain.

If evidence data is incomplete, the system should still return a summary, but with lower confidence and explicit risk notes.

If the LLM output is incomplete or contradictory, the deterministic post-processing layer should enforce alignment with:
- the pricing mode
- the category playbook
- the resolved market state
- the confidence and threshold context

## Testing Plan
Add or extend tests to verify:

1. Category playbook entries are structured and category-aware.
2. Recommendation cards include evidence and confidence labels.
3. The executive summary is concise and additive, not duplicative.
4. The executive summary includes the resolved threshold source tier.
5. The executive score uses the documented weighting formula.
6. The executive summary includes `approval_readiness`.
7. Existing marketing and analytics tests still pass unchanged.

## Success Criteria
This slice is complete when:
- the marketing response includes `business_decision_summary`
- the summary is concise and executive-facing
- the category playbook is richer and deterministic
- recommendation cards are evidence-backed and confidence-labeled
- the resolved threshold source is visible in the final summary
- no scraper, frontend, or existing API contract is broken

## Notes
- The `business_decision_summary` name is kept for compatibility, but it should be presented in the UI as an AI executive recommendation where appropriate.
- The summary should reference the existing pricing and marketing summaries rather than duplicating them.
