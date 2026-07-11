# Phase 1 Pricing, Feedback, and Analytics Design

## Goal
Make the analytics model the primary source of truth in the UI, add visible confidence and reasoning signals, capture user outcome feedback for future retraining, and version analytics artifacts so model rollbacks are possible.

## Scope
This phase covers pricing/analytics only:
- primary pricing figures in Results, Analytics, Reports, and PDF exports
- low-sample confidence warnings and reasoning visibility
- user outcome capture for acted-on recommendations and later actual buy/sell prices
- analytics model artifact versioning and rollback support
- category-specific MCB confidence thresholds
- price-history exposure using existing multi-run scrape data

Out of scope for this phase:
- task queue / Redis / websocket async orchestration
- marketing tiered generation and caching
- legacy code removal beyond any direct dependency cleanup needed to support this phase

## Current State
The live frontend currently shows a naive observed-market calculation as "estimated profit" in the comparison helper. The backend analytics service already computes:
- recommended buy price
- recommended sell price
- expected margin
- confidence score
- model sanity adjustments

The problem is that those figures are not consistently presented as the primary user-facing result. The system also lacks a user workflow for recording actual outcomes after a recommendation is used, which prevents the project from building a retraining dataset.

## Proposed UX

### Results page
Add a compact "Recommendation Outcome" panel next to the analytics summary. The panel should let the user:
- mark the recommendation as acted on, skipped, or still under review
- optionally enter actual buy price
- optionally enter actual sell price
- optionally enter quantity / units
- optionally add a short note

The panel should also show:
- primary recommended buy price
- primary recommended sell price
- expected margin
- confidence score
- a low-sample warning when counts are below threshold
- a short reasoning list from the analytics sanity layer

### Analytics page
Show the same primary recommendation figures, but with the reasoning and sample-quality labels emphasized more strongly than the old min/max market range.

### Reports and PDF
Use the analytics recommendation as the executive summary. Keep the observed market min/max as a secondary "Observed Market Range" section, not as the headline profit number.

### History / follow-up
Users should be able to add an outcome later even if they did not submit it immediately on the Results page. The follow-up form should be able to attach to the same analytics result or pipeline run.

## Data Model

### Outcome capture
Store user feedback as an append-only event stream linked to:
- `pipeline_run_id`
- `analytics_result_id`
- optional `recommendation_id`
- optional `marketing_strategy_id` if the feedback came from a later stage

Each feedback event should support:
- `feedback_type` such as `acted_on_recommendation`, `actual_price_reported`, `dismissed`, `follow_up`
- `action_taken` such as `bought`, `sold`, `skipped`, `waiting`
- `actual_buy_price_pkr`
- `actual_sell_price_pkr`
- `quantity`
- `notes`
- `source_page`
- `created_at`

This gives us one trail for immediate feedback and later outcome reporting without forcing users to know the difference.

### Model registry
Store analytics model artifacts in a registry table so each retrain can be tracked independently.
Minimum fields:
- model family
- artifact filename / path
- version tag
- source training set
- sample count
- evaluation metadata
- active / archived state
- created_at / activated_at
- rollback linkage

### MCB thresholds
Store per-category confidence thresholds so the final decision layer is not a single global constant.
Minimum fields:
- category
- confidence threshold
- optional notes
- updated_at

### Price history
Do not overwrite historical market observations. The current pipeline already stores run-scoped scrape data with timestamps, so phase 1 should expose that history through a read path and UI trend surface rather than introducing a duplicate history store.

## Analytics Behavior
- Primary figures should be the analytics model's recommended buy price, recommended sell price, expected margin, and confidence score.
- The old min/max comparison should become a labeled observed-market reference.
- A low-sample warning should be visible when wholesale or retail counts are below threshold.
- The analytics response should include a short, structured sanity summary that explains clamping, category caps, variance penalties, or fallback behavior.
- The feedback endpoint should accept both immediate and delayed user outcome data.
- Model versioning should allow the backend to load the active artifact and keep older artifacts available for rollback.

## Compatibility
- Existing recommendation rows and marketing strategy rows must keep working.
- Existing `pipeline_run_id` and `analytics_result_id` links remain the primary join keys.
- The new feedback trail should not require auth yet, but the schema should leave room for future `user_id` or tenant scoping.

## Risks
- Adding feedback capture increases UI complexity slightly, so the form should be compact and optional.
- Model registry changes affect how the analytics service loads artifacts, so rollback support must be verified carefully.
- Per-category thresholds can create confusion if the UI does not show which threshold was used.

## Phase 1 Success Criteria
- The analytics recommendation is visibly the primary result everywhere the user sees prices.
- Users can submit or later add outcome feedback tied to the original prediction.
- Analytics model artifacts are versioned and rollback-capable.
- MCB confidence thresholds vary by category.
- Historical price runs remain queryable without overwriting old data.

