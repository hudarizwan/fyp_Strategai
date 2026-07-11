# Chapter 7: Implementation

## 7.1 INTRODUCTION

StrategAI is implemented as a modular AI-assisted decision-support system for e-commerce product evaluation. The repository shows that the current active runtime architecture is centered on a FastAPI backend, a React frontend, a Supabase/PostgreSQL-backed storage layer, and a local large language model interface through Ollama for marketing strategy generation. The implemented flow is broader than a single marketing component; it is a staged pipeline that begins with market data acquisition and ends with a governed recommendation and strategy output.

The actual end-to-end operational flow implemented in the backend can be summarized as follows:

1. A user submits a product name and category through the frontend.
2. The frontend invokes the backend scraper and analytics services.
3. The scraper collects wholesale and retail listings from verified sources.
4. A sieve-style filtering layer removes irrelevant, duplicate, or accessory listings.
5. The NLP processing layer normalizes titles, extracts product structure, converts prices to PKR, and groups similar items into clusters.
6. The analytics layer computes market statistics, performs pricing inference using a hybrid machine learning and rule-based sanity model, and persists a recommendation.
7. The marketing agent enriches the analytics result with market context, routes the product into an appropriate strategy archetype, assembles prompts, generates a structured strategy through Ollama, validates the response, and stores versioned strategy records.
8. A deterministic decision-governance layer evaluates the analytics and marketing outputs together and assigns a final decision state such as `approved`, `needs_reanalysis`, or `human_review`.

The most important implementation detail is that the active production path is service-driven through FastAPI routes, especially `/analytics/analyze`, rather than through the older LangGraph-based BDI wrappers. The repository still contains BDI-style agent modules and workflow definitions, but these act primarily as auxiliary or experimental orchestration artifacts rather than the primary deployment path.

## 7.2 IMPLEMENTATION OVERVIEW AND ARCHITECTURE

### 7.2.1 Backend Application Layer

The backend entry point is `backend/app/main.py`. It defines a FastAPI application and mounts three major routers:

- `scraper` router for raw market collection
- `analytics` router for full pipeline execution and recommendation generation
- `marketing` router for standalone marketing generation, regeneration, and history retrieval

This is important because it reveals that StrategAI is not implemented as one monolithic script. Instead, it exposes distinct service interfaces that allow the scraper, analytics engine, and marketing strategy generator to be run independently or as part of the complete pipeline.

### 7.2.2 Active Runtime Flow

The active end-to-end flow is implemented inside `backend/app/api/analytics.py`, specifically in the `/analytics/analyze` endpoint. This route performs the following sequence:

1. Creates a search request record and a pipeline run record.
2. Logs workflow events and per-agent execution entries.
3. Runs the scraper service.
4. Persists raw wholesale and retail rows into stage-specific raw tables.
5. Runs the NLP pipeline to normalize and cluster products.
6. Runs the analytics agent to compute pricing recommendations.
7. Runs the marketing agent to produce a structured go-to-market strategy.
8. Runs the MCB decision agent to validate approval readiness.
9. Finalizes the pipeline run and returns a combined response to the client.

This architecture gives the project strong traceability. Each stage is represented not only in memory but also in persistent workflow records, making the system more suitable for an FYP focused on implementation quality and auditability.

### 7.2.3 Auxiliary Agent Architecture

The `backend/app/agents/` directory contains additional agent abstractions:

- `base_agent.py` implements a BDI-style agent base class
- `enhanced_scraper_agent.py` wraps tiered scraping with fallback logic
- `nlp_cleaning_agent.py` wraps the NLP service for LangGraph
- `analytics_agent_ensemble.py` implements an older ensemble-learning analytics agent
- `analysis_agent.py` implements an older neural-network-oriented analysis path
- `workflow.py` and `complete_workflow.py` define LangGraph workflows

These files are significant because they show the evolution of the system from an explicitly agent-oriented architecture toward a service-oriented execution path. For reporting purposes, the correct interpretation is that StrategAI includes both:

- a current service-first production implementation
- an experimental or earlier multi-agent orchestration layer retained in the repository

## 7.3 DETAILED IMPLEMENTATION OF MAJOR MODULES

### 7.3.1 Scraper Engine

The scraper subsystem is implemented in `backend/app/services/scraper_service.py`. Its purpose is to collect market evidence from wholesale and retail sources while minimizing irrelevant and noisy records.

#### Purpose

The scraper provides the raw evidence required by all downstream modules. Without it, clustering, analytics, and marketing would operate on assumptions rather than observed market listings.

#### Inputs

- `product_name`
- `category`
- optional `moq`
- control flags such as `normalize`, `persist`, and `use_parallel`

#### Outputs

- a structured payload containing `wholesale`, `retail`, `links_used`
- a `raw_capture` snapshot
- optional `normalized_output`
- diagnostics for wholesale scraping

#### Core Logic

The scraper does not simply fetch arbitrary HTML. It uses source-specific logic and layered fallback:

- Made-in-China listings are parsed through targeted HTML extraction functions.
- Daraz listings prefer Playwright-based extraction, then fall back to ScraperAPI or generic HTML parsing.
- Jobs can run in parallel using `ThreadPoolExecutor`.
- A modular sieve filter then normalizes, deduplicates, and constrains the results before they are passed onward.

The implemented source set in the active pipeline is focused and realistic:

- wholesale: `made_in_china`
- retail: `daraz`

This narrow source scope is a deliberate engineering choice. It improves reliability and reduces schema inconsistency compared to scraping many unstable sites.

#### Interesting Choices

The most notable implementation choice is the use of strict acceptance rules before downstream processing:

- `strict_name_match()` enforces ordered token coverage.
- `is_accessory()` rejects compatible accessories such as covers, chargers, cases, or replacement parts.
- `passes_all_constraints()` combines title presence, name matching, and accessory rejection.
- `_dedupe_dict_items()` removes duplicates using stable composite keys.

This means the scraper stage is already partially semantic, rather than acting as a dumb network fetcher.

#### Trade-offs

- Strong filtering improves quality but may reduce recall for unusually phrased listings.
- Playwright offers better Daraz extraction quality but adds runtime complexity.
- ScraperAPI fallback improves robustness but introduces dependence on external credentials.

### 7.3.2 Data Preprocessing and Cleaning

The preprocessing layer is implemented in `backend/app/services/nlp_agent.py` through the `NLPAgent` class.

#### Purpose

This module converts heterogeneous raw platform listings into analytics-ready structured records.

#### Inputs

- filtered scraper output
- `product_name`
- `category`
- `pipeline_run_id` when persistence is required

#### Outputs

- normalized records
- valid records
- similarity matrix
- product clusters
- persistence counts and statistics

#### Core Logic

The NLP layer performs the following operations:

1. Flattens platform-specific retail and wholesale records into a common schema.
2. Cleans noisy text through punctuation removal, lowercasing, and marketing-noise filtering.
3. Extracts product structure:
   - brand
   - model
   - storage variant
4. Converts original currencies into PKR.
5. Detects accessories and rejects them.
6. Builds normalized text for similarity comparison.
7. Persists normalized records into stage-specific normalized tables.

The implementation is intentionally lightweight. It does not depend on heavy transformer-based NLP; instead, it uses robust deterministic normalization suitable for a constrained FYP environment.

#### Interesting Choices

Several choices are especially important:

- The code handles both `sklearn` TF-IDF and a custom fallback vectorizer, which improves resilience in restricted environments.
- Brand and model extraction is rule-based and query-aware rather than fully generic.
- Storage variants such as `64GB`, `128GB`, and `256GB` are treated as cluster boundaries, preventing wrong merges across device variants.

#### Trade-offs

- Deterministic extraction is transparent and fast, but less flexible than full neural entity extraction.
- The normalization layer is easier to test and debug, but requires careful rule maintenance for new categories.

### 7.3.3 Cluster Generation and Product Grouping

The clustering logic is also implemented within `NLPAgent`.

#### Purpose

The system must compare like with like. Clustering prevents the analytics engine from mixing unrelated products or mismatched variants.

#### Inputs

- validated normalized records
- similarity matrix

#### Outputs

- connected product clusters
- cluster entities containing canonical titles, vendor summaries, price candidates, and traceability information

#### Core Logic

The clustering algorithm works as a graph-based connected-component process:

- TF-IDF vectors are generated from normalized product text.
- cosine similarity is computed between all records.
- `_records_should_cluster()` allows clustering if:
  - similarity exceeds a threshold, or
  - brand and model match exactly.
- storage mismatch blocks clustering even when text is similar.

This combination of numeric similarity and business logic is one of the strongest implementation decisions in the codebase. It reduces false merges without requiring a complex third-party clustering framework.

#### Why It Exists

Without clustering, the analytics engine would average prices across incompatible products. The cluster abstraction is therefore the project’s main product identity mechanism.

### 7.3.4 Analytics Engine

The analytics engine is implemented in `backend/app/services/analytics_agent.py`.

#### Purpose

This module transforms clustered market evidence into pricing recommendations and margin guidance.

#### Inputs

- clustered NLP output
- `product_name`
- `category`
- optional `pipeline_run_id`

#### Outputs

- recommended buy price
- recommended sell price
- expected profit margin
- confidence score and reason
- recommendation status
- detailed analysis metadata

#### Core Logic

The analytics engine is not a plain machine learning predictor. It is a hybrid design that combines:

- descriptive statistics over cluster data
- outlier removal
- product-category-specific margin policies
- an ensemble regression model
- post-prediction sanity clamping

The embedded `HybridPricingModel` loads a persisted model bundle when available. If no trained model is present, it generates synthetic cold-start training data and fits:

- Random Forest for buy price
- Random Forest for sell price
- XGBoost buy model when available
- XGBoost sell model when available

Predictions are averaged across available estimators. The module then applies a deterministic safety layer. This safety layer is one of the most technically mature parts of the project. It clamps model outputs against:

- observed retail bands
- category-specific minimum and maximum margin policies
- sparse-data restrictions
- buy-to-retail floor safety ratios

#### Recommendation Engine

The repository does not contain a separate class named `RecommendationEngine`; instead, recommendation generation is implemented directly inside the analytics service. The method `_build_recommendation_response()` packages the final output and stores it in the `recommendations` table. Therefore, in the actual implementation, the analytics engine and recommendation engine are fused into one service.

#### Interesting Choices

- `DEFAULT_CATEGORY_POLICIES` provides domain-specific pricing guardrails.
- `_detect_pricing_category()` infers the most appropriate business policy from product and cluster text.
- `_remove_price_outliers()` improves robustness when scraped data contains extreme anomalies.
- low-confidence clusters are still persisted with explicit statuses such as `low_confidence` or `insufficient_data`.

#### Trade-offs

- A purely ML approach would be more flexible but risk unrealistic pricing.
- A purely rule-based approach would be easier to explain but less adaptive.
- The implemented hybrid model is a good compromise for an academic prototype with real market noise.

### 7.3.5 Context Builder and Product Differentiation Layer

The context-building and differentiation logic is distributed mainly across:

- `marketing_agent.py`
- `marketing_profile.py`
- `marketing_archetypes.py`
- `marketing_prompt_builder.py`

#### Purpose

These modules prevent the marketing agent from generating generic, repetitive output. They convert raw analytics and scraper evidence into a product-aware context packet.

#### Inputs

- analytics recommendation
- retail competitor summary
- wholesale origin and MOQ summary
- inferred category behavior

#### Outputs

- category profile
- product profile
- strategy archetype
- compact analytics summary
- competitor summary
- selected strategy angle

#### Core Logic

The context builder operates in layers:

1. `_infer_category_profile()` infers family, price tier, competition intensity, audience style, trust driver, and content formats.
2. `build_product_profile()` converts this into purchase-type, buyer-motivation, trust-sensitivity, comparison-intensity, content-style, and supply-flexibility descriptors.
3. `route_strategy_archetype()` maps the product into one or two marketing archetypes such as:
   - `technical_comparison`
   - `premium_brand`
   - `budget_commodity`
   - `high_competition_differentiation`
4. `_select_strategy_angle()` chooses the angle used for generation and rotates it when regeneration is requested.

This is effectively the project’s product differentiation layer. It ensures that a camera, a premium headphone, and a low-cost mobile accessory do not receive the same launch logic.

### 7.3.6 Prompt Builder and LLM Interface

The prompt assembly logic is implemented in `marketing_prompt_builder.py`, while model execution is handled in `marketing_agent.py`.

#### Purpose

The LLM interface produces a structured marketing strategy with sections such as STP, SWOT, PESTEL, channels, launch plan, and evidence ledger.

#### Inputs

- strategy context
- compact analytics summary
- competitor summary
- Pakistan-specific e-commerce context

#### Outputs

- a JSON-only marketing strategy

#### Core Logic

The prompt builder deliberately compresses numerical and market evidence into structured summaries instead of sending raw scraper output directly. This reduces prompt size and increases consistency.

The generator then calls Ollama with:

- model: `llama3.1:8b` by default
- format: JSON
- controlled temperature
- structured schema expectations

The model output is parsed by `_extract_json()`, which handles:

- clean JSON
- fenced JSON
- prose-wrapped JSON

If parsing fails, the agent returns an intentionally invalid empty strategy rather than silently accepting malformed text. This is a strong implementation choice because it makes generation failure visible.

#### Fast Path

The marketing agent includes a deterministic fast path for low-confidence or sparse-data cases. In these cases, it skips Ollama entirely and constructs a structured strategy in Python. This reduces latency and avoids wasting LLM calls when the market evidence is too weak to justify expensive generation.

#### Trade-offs

- Local Ollama provides privacy, cost control, and offline capability.
- A local 8B model is cheaper than a cloud API but may require stricter post-processing and validation.
- JSON-only prompting improves parseability but can constrain expressive richness.

### 7.3.7 Validation Layer and Anti-Genericity Logic

Validation is implemented at two levels.

#### Marketing Validation

Within `MarketingAgent`, `_validate()` checks:

- presence of required output keys
- confidence score numeric range
- presence of evidence ledger
- presence of KPIs
- invalid analysis status from generation

If only soft issues remain, the result is marked `needs_review`. If harder issues appear, the agent may invoke `_critic()` to repair the output through a second low-temperature model pass.

#### Similarity Guard

`marketing_similarity.py` implements anti-genericity logic using textual signatures across strategic sections. The generated strategy is compared with prior stored strategies using `SequenceMatcher`. If similarity exceeds the threshold, selected sections are regenerated. This mechanism is particularly important in an academic project because it demonstrates awareness of a known weakness of LLM systems: repetitive generic output.

### 7.3.8 Final Decision and Governance Layer

The final governance module is `MCBDecisionAgent`, supported by `mcb_rules.py`, `mcb_scoring.py`, and `mcb_models.py`.

#### Purpose

This module determines whether the combined analytics and marketing output is safe enough to approve automatically.

#### Inputs

- wholesale market statistics
- retail market statistics
- analytics prediction
- competitor signals
- marketing summary output

#### Outputs

- final status
- final confidence
- validation flags
- approved strategy summary when appropriate
- next action

#### Core Logic

The governance layer uses:

- business-rule validation for contradictions
- weighted confidence scoring
- severity-aware penalty accumulation

The final statuses are:

- `approved`
- `needs_reanalysis`
- `human_review`

This is an excellent architectural addition because it separates generation from approval. The project therefore avoids treating an LLM output as automatically trustworthy.

### 7.3.9 Database and Storage Layer

The storage subsystem is implemented through `backend/app/services/ecdb.py` and the SQL migrations under `backend/db/migrations/`.

#### Purpose

The database layer provides:

- historical persistence
- workflow auditability
- stage-by-stage traceability
- recommendation and strategy retrieval

#### Actual Storage Design

The repository shows a hybrid storage architecture:

1. A newer pipeline-oriented schema created through migrations:
   - `search_requests`
   - `pipeline_runs`
   - `agent_executions`
   - `workflow_events`
   - `scrape_sources`
   - raw and normalized stage tables
   - `product_clusters`
   - `record_similarity_edges`
   - `analytics_results`
   - `recommendations`
   - `marketing_strategies`
   - `dead_letter_records`

2. Older or compatibility-oriented product tables still managed by `ECDB`:
   - `wholesale_products`
   - `retail_products`
   - `category_patterns`
   - `product_patterns`

This reveals that the project evolved over time. Instead of deleting the earlier tables, the implementation preserves backward compatibility while adding a richer stage-aware pipeline schema.

#### Connectivity Model

`ECDB` supports multiple access modes:

- direct PostgreSQL through `psycopg2`
- pure-Python PostgreSQL through `pg8000`
- Supabase REST fallback

This is a pragmatic engineering decision because it reduces deployment fragility across different environments.

#### Marketing Strategy Versioning

The `marketing_strategies` table supports:

- `version_number`
- `is_latest`
- `generation_type`
- `parent_strategy_id`

This means the system implements explicit strategy history rather than overwriting prior outputs. That is academically valuable because it supports comparison between generation attempts.

### 7.3.10 Scheduler and Auxiliary Controllers

The repository includes `backend/app/scheduler/scraper_scheduler.py`, which defines a scheduled scraper for a fixed set of proof-of-concept products. It is designed to:

- run daily at 2 AM
- scrape predefined electronics products
- process them through the NLP pipeline
- populate the database for future learning

Although this scheduler is not wired into the FastAPI startup path in the inspected code, its existence demonstrates that the project considered recurring data collection rather than only ad hoc user-triggered scraping.

### 7.3.11 Frontend and User Interface Layer

The active frontend is `frontend/salik-frontend`, a React + Vite application.

#### Key Pages

- `Dashboard.tsx` accepts product input and triggers scraping and analytics
- `Results.tsx` displays scraped market results and triggers marketing generation/regeneration
- `Analytics.tsx` presents price comparison charts and analytics summary
- `Marketing.tsx` renders the generated strategy, version history, evidence ledger, and validation report

#### UI-to-Backend Coupling

The frontend uses `frontend/salik-frontend/src/services/api.ts` to call:

- `/scraper/start`
- `/analytics/analyze`
- `/marketing/generate`
- `/marketing/regenerate`
- marketing history and retrieval routes

The frontend stores intermediate results in `sessionStorage`, which is a simple but effective mechanism for preserving pipeline state across page transitions.

The second frontend, `frontend/landing-page`, appears to be a separate landing or presentation site rather than the main operational dashboard.

## 7.4 REPRESENTATIVE CODE EXCERPTS AND EXPLANATION

The following excerpts are intentionally selective. It is neither necessary nor desirable to reproduce full source files in the report. The chosen excerpts represent the parts that best demonstrate the project’s technical originality and engineering decisions.

### Excerpt 7.1: End-to-End Pipeline Orchestration

```python
search_request = db.create_search_request(product_name, category)
pipeline_run = db.create_pipeline_run(search_request["id"], current_stage="scraper")

raw_data = scrape_product_platforms(product_name, category)
nlp_output = NLPAgent().process(raw_data, product_name, category, pipeline_run_id=pipeline_run["id"])
recommendation = AnalyticsAgent().analyze(product_name, category, nlp_output, pipeline_run_id=pipeline_run["id"])
marketing_result = MarketingAgent().run(product_name, category, recommendation, raw_data, pipeline_run_id=pipeline_run["id"])
mcb_decision = MCBDecisionAgent().decide(mcb_input)
```

This excerpt shows that the project is implemented as a true staged pipeline rather than isolated scripts.

It matters because it demonstrates traceability, modularity, and stage-aware persistence.

It was selected because `/analytics/analyze` is the single most important runtime path in the system.

### Excerpt 7.2: Sieve-Based Scraper Filtering

```python
normalized = _normalize_wholesale_item(item)
if not normalized:
    reject("missing_required")
if not passes_all_constraints(normalized, product_name, category):
    reject("constraint_rejected")
deduped = _dedupe_dict_items(
    normalized_items,
    ["title", "supplier", "unit_price", "source_url"],
)
```

This excerpt shows that the scraper does not forward raw HTML results blindly.

It matters because the quality of every later stage depends on early rejection of noise, accessories, and duplicates.

It was selected because the sieve filter is the practical foundation of data quality in StrategAI.

### Excerpt 7.3: Rule-Assisted Clustering

```python
if left_storage and right_storage and left_storage != right_storage:
    return False
if similarity >= self.similarity_threshold:
    return True
if left["brand"] == right["brand"] and left["model"] == right["model"]:
    return True
return False
```

This excerpt shows that clustering uses both similarity scores and business rules.

It matters because clustering errors would corrupt analytics by mixing incompatible products.

It was selected because it captures the project’s central identity-resolution strategy in only a few lines.

### Excerpt 7.4: Hybrid Pricing with Sanity Control

```python
predicted_buy, predicted_sell = self.model.predict(feature_row)
adjusted_buy = max(predicted_buy, heuristic_buy)
adjusted_sell = clamp_to_retail_band(predicted_sell, retail_bounds)
adjusted_sell = apply_margin_caps(adjusted_sell, adjusted_buy, category_policy)
if confidence_after_adjustment < threshold:
    adjusted_buy = heuristic_buy
    adjusted_sell = heuristic_sell
```

This excerpt shows that analytics is not naive regression.

It matters because the project explicitly prevents unrealistic outputs from leaving the analytics stage.

It was selected because it captures the strongest technical contribution of the analytics layer: combining ML with deterministic safety.

### Excerpt 7.5: Anti-Generic Marketing Guard

```python
similarity = compare_with_history(strategy, previous_rows)
if similarity["too_similar"]:
    regenerated = self._regenerate_sections(strategy, enriched, context, previous_strategy)
    regenerated["strategy_meta"]["similarity_check"] = {
        **similarity,
        "regenerated_due_to_similarity": True,
    }
```

This excerpt shows that the marketing agent actively resists repetitive outputs.

It matters because generic responses are a common weakness in local LLM deployments.

It was selected because it directly demonstrates product-specific differentiation in implementation rather than only in claims.

## 7.5 RATIONALE AND TRADE-OFFS

### 7.5.1 Local Model vs External API

The project uses Ollama with a local model by default. This decision offers:

- better privacy
- lower marginal cost
- easier offline experimentation
- independence from cloud API quotas

The trade-off is reduced raw reasoning quality compared with some larger hosted models, which is why the implementation compensates through deterministic routing, schema constraints, validation, and regeneration logic.

### 7.5.2 Deterministic Logic vs LLM Flexibility

StrategAI does not delegate everything to the model. Product filtering, normalization, clustering, pricing sanity checks, and approval governance are all deterministic. The LLM is used where generative synthesis is valuable, namely in marketing strategy composition.

This is a strong design choice. It limits hallucination in numerical or structural tasks while still using AI where it adds value.

### 7.5.3 Modular Pipeline vs Monolithic Flow

The codebase separates scraping, NLP, analytics, marketing, and governance into their own modules. This increases clarity, testability, and replaceability. The trade-off is more plumbing code and more schemas to manage, but the result is more appropriate for a serious FYP than a monolithic script.

### 7.5.4 Rich Traceability vs Storage Complexity

The newer schema stores pipeline runs, agent executions, stage outputs, and dead-letter records. This makes debugging and audit easier, but it also introduces additional schema complexity. For an academic system, this trade-off is justified because traceability is an important part of demonstrating engineering maturity.

### 7.5.5 Broad Source Coverage vs Data Quality

The active scraper targets a limited number of marketplaces. This sacrifices breadth but improves the consistency and quality of parsed results. Given the downstream dependence on clustering and analytics accuracy, this is a sensible prioritization.

## 7.6 TEXTUAL DIAGRAM GUIDANCE

### 7.6.1 Operational Diagram

Purpose: to show the runtime flow of a single user-triggered analysis.

Elements to include:

- User
- React Dashboard
- FastAPI Backend
- Scraper Service
- NLP Agent
- Analytics Agent
- Marketing Agent
- MCB Decision Agent
- Supabase/PostgreSQL
- Ollama Local Model

Suggested drawing sequence:

`User -> Dashboard -> /analytics/analyze -> Scraper Service -> Database (raw stage)`

`Scraper Service -> NLP Agent -> Database (normalized records, clusters)`

`NLP Agent -> Analytics Agent -> Database (analytics_results, recommendations)`

`Analytics Agent -> Marketing Agent -> Ollama -> Database (marketing_strategies)`

`Marketing Agent + Analytics Output -> MCB Decision Agent -> Final API response -> Dashboard`

### 7.6.2 Component Diagram

Purpose: to show the static modules of StrategAI and the dependencies between them.

This diagram should be drawn as an architectural view, not as a process flow. It should answer the following questions clearly:

- which major components exist in StrategAI
- which components provide or require services
- how the Marketing Agent is decomposed internally
- which systems are internal to StrategAI and which are external dependencies

Components to include:

- React Frontend
- FastAPI App
- Scraper Router
- Analytics Router
- Marketing Router
- Scraper Service
- NLP Service
- Analytics Service
- Marketing Service
- Recommendation Module
- Prompt Builder
- Context Builder
- Product Differentiation Layer
- Archetype Router
- Validation Layer
- Similarity Guard
- MCB Decision Agent
- ECDB
- PostgreSQL/Supabase
- Ollama

Suggested structure:

- place the React Frontend on the left
- place the FastAPI App in the center as the main orchestrator
- place the core backend services beneath the FastAPI layer
- place PostgreSQL/Supabase and Ollama on the right as supporting external systems
- treat the Marketing Service as a subsystem with internal components instead of a single black box

Internal Marketing Agent structure:

- Context Builder prepares product, market, and analytics context
- Product Differentiation Layer extracts unique selling points and positioning signals
- Archetype Router selects the most suitable marketing strategy pattern
- Prompt Builder composes the final prompt sent to the LLM
- Ollama performs local language-model generation
- Validation Layer checks whether the generated strategy is usable
- Similarity Guard compares the generated output against stored strategies
- ECDB stores approved strategies for reuse and versioning

Interface relationships to show:

- `React Frontend` requires the `FastAPI API`
- `Scraper Router` requires `Scraper Service`
- `Analytics Router` requires `Analytics Service`
- `Marketing Router` requires `Marketing Service`
- `Marketing Service` requires `Ollama`
- `Marketing Service` requires `ECDB`
- `Validation Layer` and `Similarity Guard` depend on the stored strategy history
- `MCB Decision Agent` receives the combined analytics and marketing output

Recommended connection order:

1. `React Frontend` -> `FastAPI App`
2. `FastAPI App` -> `Scraper Router`
3. `FastAPI App` -> `Analytics Router`
4. `FastAPI App` -> `Marketing Router`
5. `Scraper Router` -> `Scraper Service`
6. `Analytics Router` -> `Analytics Service`
7. `Marketing Router` -> `Marketing Service`
8. `Marketing Service` -> `Context Builder`
9. `Marketing Service` -> `Product Differentiation Layer`
10. `Marketing Service` -> `Archetype Router`
11. `Marketing Service` -> `Prompt Builder`
12. `Prompt Builder` -> `Ollama`
13. `Marketing Service` -> `Validation Layer`
14. `Marketing Service` -> `Similarity Guard`
15. `Marketing Service` -> `ECDB`
16. `Analytics Service` -> `MCB Decision Agent`
17. `Marketing Service` -> `MCB Decision Agent`

Drawing guidance:

- use provided interfaces for services that are offered to other components
- use required interfaces for services that a component consumes
- use assembly connectors where a required interface matches a provided interface
- use delegation connectors inside the Marketing Agent subsystem
- keep external systems such as Ollama and PostgreSQL/Supabase visually separate from internal modules

What to avoid:

- do not draw class-level details
- do not include SQL tables or column names
- do not show the diagram as a left-to-right workflow only
- do not place every module directly on the database
- do not merge the Marketing Agent into a single unlabeled box

### 7.6.3 Deployment Diagram

Purpose: to show where the system executes physically or logically.

Nodes to include:

- Client Browser
- Frontend Host for `salik-frontend`
- Frontend Host for landing page
- Backend API Host running FastAPI/Uvicorn
- Local or network-accessible Ollama host
- Supabase cloud database
- External web sources:
  - Daraz
  - Made-in-China
  - optional ScraperAPI

Suggested drawing structure:

- top node: user device/browser
- middle nodes: frontend and backend application servers
- right-side service nodes: Ollama, Supabase
- bottom external-source nodes: scraped marketplaces

## 7.7 CORE TECHNICAL INTERFACES

### 7.7.1 Interface 1: `POST /analytics/analyze`

Purpose: triggers the full evidence-to-recommendation pipeline.

Input:

```json
{
  "product_name": "HyperX Cloud III",
  "category": "headset"
}
```

Output:

```json
{
  "product": "HyperX Cloud III",
  "category": "headset",
  "pipeline_run_id": "uuid",
  "analytics_result_id": "uuid",
  "product_cluster_id": "uuid",
  "recommended_buy_price_pkr": 2800.0,
  "recommended_sell_price_pkr": 3850.0,
  "expected_profit_margin": 27.0,
  "confidence_score": 0.78,
  "confidence_reason": "moderate confidence - usable market coverage with some variance",
  "marketing_strategy_id": "uuid",
  "marketing_analysis_status": "ok",
  "mcb_decision": {
    "final_status": "approved"
  }
}
```

Request/response flow:

1. request enters FastAPI
2. pipeline run is created
3. scraper, NLP, analytics, marketing, and MCB decision execute
4. final combined recommendation is returned

Why this interface is core:

It is the primary business interface of StrategAI because it executes the full decision-support pipeline in one call.

### 7.7.2 Interface 2: `POST /marketing/generate`

Purpose: generates a marketing strategy from existing analytics and scraper results.

Input:

```json
{
  "product_name": "HyperX Cloud III",
  "category": "headset",
  "analytics_result": {
    "recommended_buy_price_pkr": 2800.0,
    "recommended_sell_price_pkr": 3850.0,
    "expected_profit_margin": 27.0,
    "confidence_score": 0.78,
    "wholesale_vendors_count": 4,
    "retail_sellers_count": 5
  },
  "scraper_result": {
    "wholesale": {},
    "retail": []
  },
  "pipeline_run_id": "uuid",
  "analytics_result_id": "uuid",
  "product_cluster_id": "uuid"
}
```

Output:

```json
{
  "id": "uuid",
  "product_name": "HyperX Cloud III",
  "category": "headset",
  "analysis_status": "ok",
  "confidence_score": 0.76,
  "version_number": 1,
  "is_latest": true,
  "strategy": {
    "stp": {},
    "swot": {},
    "channels": [],
    "launch_plan": {},
    "validation_report": {}
  }
}
```

Why this interface is core:

It isolates the LLM-assisted marketing subsystem and supports regeneration, versioning, and comparison independently of the analytics route.

### 7.7.3 Interface 3: `POST /scraper/start`

Purpose: retrieves current wholesale and retail market listings without executing the full analytics stack.

Input:

```json
{
  "product_name": "Logitech K380",
  "category": "keyboard",
  "normalize": false,
  "persist": false,
  "use_parallel": true
}
```

Output:

```json
{
  "product_name": "Logitech K380",
  "links_used": {
    "made_in_china_search": "https://...",
    "daraz_search": "https://..."
  },
  "wholesale": {
    "made_in_china": []
  },
  "retail": []
}
```

Why this interface is core:

It is the evidence collection entry point and is also used directly by the frontend search workflow.

## 7.8 STATE TRANSITION DIAGRAM

The main processing state flow can be drawn in textual form as follows:

`Idle -> Input Received -> Search Request Created -> Pipeline Run Created -> Scraping -> Raw Data Stored -> NLP Normalization -> Record Validation -> Clustering -> Analytics Prediction -> Pricing Sanity Check -> Recommendation Stored -> Marketing Generation -> Marketing Validation -> Similarity Check -> Strategy Stored -> MCB Decision -> Completed`

Alternative paths:

- `Scraping -> No Valid Listings -> NLP returns sparse data -> Analytics marks low_confidence -> Recommendation Stored -> Marketing fast path or failure path -> MCB needs_reanalysis`
- `Marketing Generation -> Invalid JSON -> Validation failed -> Critic retry or invalid result -> Stored with review status`
- `Any Stage -> Exception -> Dead Letter Record -> Pipeline Failed`

# Chapter 8: Testing

## 8.1 INTRODUCTION

This chapter is written from executed verification, not from assumption. The repository was inspected for automated tests and executable checks before drafting this chapter.

The following checks were run during inspection:

1. Backend automated tests:
   - command used: `PYTHONPATH=backend pytest -q backend/tests -p no:cacheprovider`
   - observed result: `77 passed, 2 warnings in approximately 21.4 seconds`
2. `salik-frontend` production build:
   - observed result: successful production build after rerunning outside sandbox
3. `salik-frontend` lint:
   - observed result: passed
4. `landing-page` production build:
   - observed result: failed with TypeScript errors
5. `landing-page` lint:
   - observed result: failed with 5 errors and 1 warning

An important observation is that running `pytest` from the repository root initially failed during test collection because the suite assumes `backend` is present on `PYTHONPATH`. This is a project setup issue, not a logic failure in the tests themselves.

## 8.2 TEST PLAN AND AUTOMATED TEST INVENTORY

The backend test suite consists of 77 tests distributed as follows:

| Test file | Focus area | Test count |
| --- | --- | ---: |
| `test_scraper_subsystem.py` | scraper filtering, parsing, orchestration, compatibility wrappers | 13 |
| `test_nlp_agent.py` | text cleaning, normalization, clustering, persistence wrappers | 9 |
| `test_analytics_agent.py` | category detection, outlier handling, confidence, pricing sanity, persistence | 14 |
| `test_marketing_agent.py` | perceive/enrich/generate/validate/critic/run/versioning/similarity | 36 |
| `test_mcb_decision_agent.py` | approval, reanalysis, contradiction handling, missing-data cases | 5 |

This distribution shows that the strongest automated coverage is concentrated on the most logic-heavy components: marketing, analytics, and scraping.

## 8.3 WHITE BOX TESTING

White box testing focused on internal decision logic rather than only surface responses.

### 8.3.1 Scraper Logic

Internal logic under test:

- accessory rejection
- duplicate rejection
- price parsing
- platform-job fault tolerance
- diagnostics retention
- search query expansion for wholesale scraping

Representative cases:

| Test case | Expected result | Actual result |
| --- | --- | --- |
| Accessory listing mixed with real product | accessory removed | Passed |
| Duplicate Daraz listing | duplicate removed | Passed |
| Made-in-China card parsing | supplier, MOQ, unit price extracted correctly | Passed |
| Parallel job group with one failing job | successful job retained, failed job returned empty list | Passed |

Interpretation:

The scraper subsystem behaves deterministically and is strongly protected against common scraping noise. This is a significant strength because later stages rely on high-quality inputs.

### 8.3.2 NLP and Clustering Logic

Internal logic under test:

- text cleaning
- currency normalization
- brand/model extraction
- cluster assignment
- cluster aggregate calculation
- wrapper export behavior

Representative cases:

| Test case | Expected result | Actual result |
| --- | --- | --- |
| `USD` to `PKR` conversion | `10 USD -> 2800 PKR` | Passed |
| Roman numeral model extraction | `HyperX Cloud III -> model = cloud iii` | Passed |
| Cross-platform title similarity | same product clustered together | Passed |
| Cluster aggregate computation | min retail and platform count computed correctly | Passed |

Interpretation:

The clustering layer is internally consistent and business-aware. The tests especially confirm that product identity resolution is not arbitrary.

### 8.3.3 Analytics Logic

Internal logic under test:

- category policy detection
- outlier removal
- low-confidence identification
- pricing clamp logic
- sparse-data fallback
- recommendation persistence

Representative cases:

| Test case | Expected result | Actual result |
| --- | --- | --- |
| Phone cluster detection | `mobile_phones` policy selected | Passed |
| Headset cluster detection | `headsets` policy selected | Passed |
| Extreme outlier in wholesale prices | outlier excluded from metrics | Passed |
| Extreme ML sell prediction | clamped into retail band | Passed |
| Sparse one-record market | confidence reduced and conservative pricing applied | Passed |
| Analytics persistence | one analytics row and one recommendation created | Passed |

Interpretation:

These tests confirm that the analytics engine is not merely predicting numbers but actively constraining them into commercially defensible ranges.

### 8.3.4 Marketing Logic

Internal logic under test:

- analytics input validation
- enrichment from scraper evidence
- JSON extraction from model responses
- validation and critic behavior
- fast-path generation
- product-specific differentiation
- regeneration angle rotation
- similarity guard
- marketing strategy versioning

Representative cases:

| Test case | Expected result | Actual result |
| --- | --- | --- |
| Missing analytics field | raise `ValueError` | Passed |
| JSON in markdown fences | parsed successfully | Passed |
| Non-JSON model response | invalid strategy returned | Passed |
| Soft validation flags only | critic not called | Passed |
| Low-confidence input | fast path used, Ollama skipped | Passed |
| Regeneration request | strategy angle rotated | Passed |
| Similarity with previous strategy | selected sections regenerated | Passed |

Interpretation:

The marketing subsystem is the most thoroughly tested module in the repository. This is appropriate because it is also the least deterministic component and therefore requires stronger guardrails.

### 8.3.5 Final Decision Governance

Internal logic under test:

- automatic approval for strong cases
- reanalysis for low-confidence cases
- escalation for contradictions
- refusal to auto-approve missing-data cases

Representative cases:

| Test case | Expected result | Actual result |
| --- | --- | --- |
| Strong market and marketing evidence | `approved` | Passed |
| Weak retail coverage and low confidence | `needs_reanalysis` | Passed |
| Contradictory negative-margin case | `human_review` | Passed |
| Missing both wholesale and retail evidence | not auto-approved | Passed |

Interpretation:

The governance layer behaves correctly as a final checkpoint rather than a superficial wrapper.

## 8.4 BLACK BOX TESTING

Black box testing was performed through executable service-level checks and frontend build validations rather than live internet-dependent pipeline calls.

### 8.4.1 Backend API Surface

Because the automated tests heavily mock external dependencies, the backend logic could be black-box evaluated at module boundaries without requiring live Daraz, Supabase, or Ollama services.

Representative black box cases:

| Interface or behavior | Test input | Expected behavior | Actual result | Status |
| --- | --- | --- | --- | --- |
| scraper subsystem orchestration | product + category | returns structured wholesale/retail payload and source links | observed in automated test suite | Pass |
| marketing generation parser | valid JSON, fenced JSON, malformed text | parse valid JSON, reject malformed output | observed in automated test suite | Pass |
| marketing storage | generated strategy | returns stored record with ID or graceful storage failure | observed in automated test suite | Pass |
| MCB decision | strong case payload | returns `approved` | observed in automated test suite | Pass |

### 8.4.2 Frontend Build-Level Black Box Checks

The React frontends were treated as deployable black-box artifacts.

| Frontend check | Expected behavior | Actual result | Status |
| --- | --- | --- | --- |
| `salik-frontend` build | production bundle generated | passed | Pass |
| `salik-frontend` lint | no lint errors | passed | Pass |
| `landing-page` build | production bundle generated | failed in `dotted-glow-background.tsx` due TypeScript errors | Fail |
| `landing-page` lint | clean lint output | failed with 5 errors and 1 warning | Fail |

The `landing-page` failures are genuine project issues, not hypothetical concerns.

## 8.5 SYSTEM TESTING

### 8.5.1 End-to-End Pipeline Status

The repository clearly supports the full conceptual pipeline:

`Scraper -> Clustering/NLP -> Analytics -> Marketing Agent -> Recommendation -> Decision Governance`

However, a full live end-to-end run against external services was not executed in this session because it depends on:

- live web scraping access
- database credentials and reachable Supabase infrastructure
- a running local Ollama service and pulled model

Therefore, the system testing result should be stated accurately as follows:

- internal logic of each stage was verified through automated tests
- API-layer orchestration was inspected directly in code
- frontend integration paths were verified statically and partially through build/lint checks
- live external-system integration remains only partially verified in the current evidence set

### 8.5.2 Practical System-Level Conclusion

From the inspected code and executed tests, the backend pipeline is implementation-complete at the logic level. The strongest evidence supports:

- scraper filtering and orchestration
- clustering and normalization
- analytics recommendation generation
- marketing generation and validation
- final approval governance

The weakest evidence concerns live deployment dependencies rather than internal logic:

- real marketplace access at runtime
- real Supabase writes during a full pipeline run
- real Ollama inference during a live user session

## 8.6 TOOLS USED

The following tools were actually present or used:

- `pytest` for backend automated testing
- `unittest` and `pytest` together in the backend test suite
- mock objects and monkeypatching for external dependency isolation
- `npm run build` for frontend build verification
- `npm run lint` for frontend static analysis
- logging and workflow tables in the backend for traceability
- JSON schema-style validation through structured key checks in the marketing agent
- database persistence abstractions through `ECDB`

## 8.7 EXPERIMENTS AND SIMULATIONS

The repository itself encodes several meaningful experiments, even when they are implemented as automated tests rather than separate benchmark notebooks.

### 8.7.1 Generic Strategy vs Product-Specific Strategy

Why conducted:

To avoid repetitive generic outputs from the local marketing model.

Setup:

- product profiling
- archetype routing
- strategy angle selection
- similarity comparison against history

Variables changed:

- product family
- competition level
- regeneration angle
- similarity threshold

Observed impact:

- different products produced different tagline, PESTEL, launch-plan, and messaging structures in tested fast-path cases
- regenerated strategies rotated the strategy angle instead of repeating the same version

Interpretation:

The differentiation layer materially improves specificity and reduces genericity.

### 8.7.2 With vs Without Similarity Guard

Why conducted:

To detect whether repeated generations collapse into near-duplicate strategies.

Setup:

- compare generated strategy text signature to prior saved strategy
- regenerate selected sections if similarity exceeds threshold

Observed impact:

- near-duplicate outputs were flagged
- selected sections were regenerated instead of blindly accepted

Interpretation:

This acts as an anti-genericity experiment embedded in the implementation itself.

### 8.7.3 With vs Without Validation

Why conducted:

To ensure malformed LLM outputs do not silently enter the database.

Setup:

- pass valid JSON, fenced JSON, prose-wrapped JSON, and invalid non-JSON responses

Observed impact:

- valid structured output was accepted
- malformed output was downgraded to `invalid`
- critic repair was attempted only when appropriate

Interpretation:

Validation and repair meaningfully increase robustness of the marketing module.

### 8.7.4 Extreme Prediction vs Sanity Layer

Why conducted:

To determine whether the analytics engine can resist unrealistic machine-learning outputs.

Setup:

- patch model predictions to extreme sell values
- compare final price after sanity layer

Observed impact:

- sell price was clamped back into retail-aware bounds
- margin caps were enforced
- low-confidence fallback applied under sparse evidence

Interpretation:

The sanity layer is not decorative; it materially changes unsafe predictions into defensible recommendations.

## 8.8 GRAPHS AND TABLES RECOMMENDED FOR THE FINAL REPORT

The following tables and figures are recommended in a directly insertable academic format so that the final report can include evidence with minimal rewriting.

### 8.8.1 Table: Backend Test Suite Summary

Table 8.1: Backend Test Suite Summary

| Module under test | Test file | Number of test cases | Observed result | Remarks |
| --- | --- | ---: | --- | --- |
| Scraper subsystem | `test_scraper_subsystem.py` | 13 | Pass | Verified parsing, filtering, deduplication, and orchestration |
| NLP and clustering | `test_nlp_agent.py` | 9 | Pass | Verified normalization, clustering, and wrapper persistence behavior |
| Analytics engine | `test_analytics_agent.py` | 14 | Pass | Verified category detection, pricing sanity, and recommendation persistence |
| Marketing agent | `test_marketing_agent.py` | 36 | Pass | Verified enrichment, generation handling, validation, versioning, and similarity guard |
| Decision governance | `test_mcb_decision_agent.py` | 5 | Pass | Verified approval, reanalysis, and human-review routing |
| Overall backend suite | `backend/tests` | 77 | Pass | `77 passed, 2 warnings` |

### 8.8.2 Table: Stage-Wise Verification Matrix

Table 8.2: Stage-Wise Verification Matrix

| Pipeline stage | Verification method | Evidence source | Result | Notes |
| --- | --- | --- | --- | --- |
| Scraping | Automated unit and subsystem tests | `test_scraper_subsystem.py` | Verified | Live website execution not performed in this session |
| Preprocessing and NLP | Automated unit tests | `test_nlp_agent.py` | Verified | Includes cleaning, normalization, and clustering |
| Analytics and recommendation | Automated unit tests | `test_analytics_agent.py` | Verified | Includes sanity clamping and persistence |
| Marketing strategy generation | Automated unit tests | `test_marketing_agent.py` | Verified | Model responses mocked for reproducibility |
| Decision governance | Automated unit tests | `test_mcb_decision_agent.py` | Verified | Deterministic approval logic confirmed |
| Full live pipeline | Manual external integration | Not executed | Partially verified | Depends on live scraping, database, and Ollama runtime |

### 8.8.3 Table: Frontend Verification Summary

Table 8.3: Frontend Verification Summary

| Frontend module | Command | Observed result | Status | Remarks |
| --- | --- | --- | --- | --- |
| `salik-frontend` | `npm run build` | Production build completed successfully | Pass | Deployment-ready bundle generated |
| `salik-frontend` | `npm run lint` | No lint errors | Pass | Static analysis passed |
| `landing-page` | `npm run build` | TypeScript build failed | Fail | Failure observed in `dotted-glow-background.tsx` |
| `landing-page` | `npm run lint` | 5 errors and 1 warning | Fail | UI code cleanup still required |

### 8.8.4 Table: Suggested Comparison Experiments

Table 8.4: Suggested Comparison Experiments

| Experiment | Baseline condition | Improved condition | Suggested metric | Reporting note |
| --- | --- | --- | --- | --- |
| Marketing specificity | Generic generation without routing | Product-profile and archetype routing | reviewer-rated specificity | Use two representative strategy outputs |
| Strategy repetition | No similarity guard | Similarity guard enabled | textual overlap score | Compare initial and regenerated strategies |
| Pricing realism | Raw ML prediction | Sanity-clamped recommendation | margin realism and band compliance | Use analytics test evidence |
| Sparse-data resilience | Direct free generation | Fast path plus governance | stability under low data | Use low-confidence scenario |

### 8.8.5 Suggested Figures

1. Figure 8.1: Distribution of backend test cases by subsystem.
2. Figure 8.2: Pipeline-stage verification status matrix.
3. Figure 8.3: Raw sell-price prediction versus sanity-adjusted sell-price recommendation.
4. Figure 8.4: Initial strategy versus regenerated strategy comparison.
5. Figure 8.5: Frontend verification summary showing pass and fail outcomes.

## 8.9 TESTING GAPS AND LIMITATIONS

The following gaps remain and should be acknowledged professionally:

1. No fully automated live end-to-end test currently runs the full pipeline against real marketplaces, real database storage, and a real Ollama model in one command.
2. No dedicated API contract tests were found for FastAPI routes using `TestClient`.
3. No performance benchmark suite was found for scraper latency, analytics latency, or marketing generation latency.
4. No frontend component tests or browser-based end-to-end tests were found.
5. The landing-page frontend currently fails build and lint checks, indicating unresolved UI-layer quality issues.
6. Some configuration files store third-party tokens directly in source code rather than relying exclusively on environment variables; this should be corrected before real deployment.

## 8.10 ANNEXURE NOTE

Detailed raw test outputs, screenshots, terminal logs, lint outputs, and full result tables should be moved to the Annexure so that the main chapter remains readable while the evidence remains auditable.

## 8.11 CHAPTER SUMMARY

The testing evidence indicates that StrategAI is strongest in backend logic quality. The automated suite verified the core reasoning modules, including scraping filters, clustering, analytics, marketing validation, and governance, with all 77 backend tests passing during verification. The principal remaining gaps lie in live third-party integration coverage and in unresolved quality issues in the separate landing-page frontend.

# Chapter 12: Achievements

## 12.1 INTRODUCTION

StrategAI demonstrates several substantial technical achievements for a Final Year Project.

First, the project is implemented as a complete multi-stage system rather than a conceptual prototype. It includes:

- evidence collection from real e-commerce sources
- deterministic cleaning and normalization
- product clustering and identity resolution
- hybrid analytics-based pricing recommendation
- LLM-assisted marketing strategy generation
- validation, anti-genericity, and governance layers
- frontend visualization and strategy presentation

Second, the system demonstrates architectural maturity by maintaining traceability throughout pipeline execution. The use of pipeline runs, workflow events, agent execution logs, stage tables, and versioned marketing strategies elevates the project beyond a simple AI demo.

Third, the project meaningfully combines classical software engineering with AI methods. The implementation does not rely only on prompts. Instead, it integrates:

- rule-based filtering
- clustering
- supervised learning
- structured prompt engineering
- JSON validation
- deterministic business-rule approval

This hybrid design is one of the project’s most defensible academic strengths.

## 12.2 LEARNING OUTCOMES AND PROFESSIONAL DEVELOPMENT

The implementation shows evidence of strong learning outcomes in the following areas:

- backend API engineering with FastAPI
- frontend dashboard development with React and Vite
- database design and staged schema evolution
- web scraping with Requests, BeautifulSoup, Playwright, and fallbacks
- machine learning integration using Random Forest and XGBoost
- local LLM integration through Ollama
- prompt design for structured JSON generation
- software testing through unit and scenario-based automation
- workflow logging and observability

These outcomes indicate that the project helped the student team move beyond isolated coding tasks into full-stack AI system engineering.

## 12.3 RESEARCH AND DESIGN ACHIEVEMENTS

The project also demonstrates notable design achievements:

- the transition from raw scraped evidence to clustered product identities
- separation of generation from governance through the MCB decision layer
- anti-genericity logic for marketing strategy diversification
- support for strategy regeneration with version history
- support for both active API flow and experimental agent-oriented orchestration

These choices suggest that the project was not developed as a one-pass implementation, but rather evolved through iterative refinement.

## 12.4 DEPLOYMENT AND DEMONSTRATION ACHIEVEMENTS

Based on the codebase, the project is capable of being demonstrated in a meaningful academic environment because it supports:

- live product search and evidence retrieval
- visual comparison of wholesale and retail prices
- backend recommendation generation
- marketing strategy generation and history review
- persistent strategy versioning

This makes StrategAI suitable for project demonstrations, departmental evaluations, and industrial presentations where an end-to-end workflow is expected.

## 12.5 COMPETITIONS, EXHIBITIONS, AND RECOGNITION

The repository does not contain formal evidence of competitions, certificates, exhibition participation, or incubator documentation. Therefore, the following subsection should be treated as a structured placeholder to be customized from actual project records.

### Example Text to Customize

StrategAI was presented during departmental project reviews and received feedback on its integration of market intelligence, pricing analytics, and AI-assisted marketing generation. The project is also suitable for showcasing in university exhibitions, entrepreneurship showcases, software expos, or incubation screenings because it demonstrates an applied AI pipeline rather than a narrow theoretical prototype.

If applicable, the following items may be inserted after verification:

- participation in university FYP exhibition
- presentation before external examiners
- showcase in departmental open house
- incubation or startup evaluation session
- competition entry in AI, data science, or entrepreneurship categories
- certificates of participation or appreciation

All such items should be supported with documentary evidence in the appendices.

## 12.6 REALISTIC SUMMARY OF ACHIEVEMENT

The principal achievement of StrategAI is that it successfully implements an evidence-driven AI pipeline that connects scraped market data, structured preprocessing, analytical pricing, controlled generative marketing, and approval governance into one coherent system. This is a meaningful and technically credible outcome for a major FYP.

## 12.7 CHAPTER SUMMARY

In academic terms, the most important achievement of StrategAI is not merely the use of artificial intelligence, but the successful integration of multiple AI and software-engineering techniques into a coherent, testable, and demonstrable product. This gives the project the character of a substantial applied Final Year Project rather than a narrow proof-of-concept.

# Chapter 13: Appendices

## 13.1 INTRODUCTION

The appendices should be organized as annexures so that the main body remains concise while detailed evidence stays available for verification.

## 13.2 RECOMMENDED ANNEXURES

Table 13.1: Recommended Annexures for StrategAI Report Evidence

| Annex | Title | What it contains | Why it is included | Where referenced |
| --- | --- | --- | --- | --- |
| Annex A | Project Evidence and Acknowledgement Support | supervisor feedback, internal review notes, acknowledgment support documents | supports Chapter 12 recognition and formal documentation | Chapter 12 |
| Annex B | Organization or Domain Context | short description of Pakistan e-commerce context, marketplaces used, deployment assumptions | grounds the project context | Chapters 1, 7 |
| Annex C | Research Papers and Literature Sources | key papers, articles, and technical references used in design | shows academic grounding | literature review and Chapter 7 |
| Annex D | Similar Systems Comparison | comparison with existing price-analysis or marketing-assistance systems | establishes novelty | problem statement and discussion |
| Annex E | Detailed Functional and Non-Functional Requirements | expanded requirement tables and acceptance criteria | supports formal software engineering process | requirements chapter |
| Annex F | Use Case Narrations | complete textual use cases for search, analysis, strategy generation, and history review | supports UML and design explanation | design chapter |
| Annex G | Additional UML Diagrams | activity, sequence, class, component, deployment, and state diagrams | provides full diagram set | Chapters 6 and 7 |
| Annex H | Algorithms and Pseudocode | scraper filtering, clustering, pricing sanity, marketing validation, MCB decision logic | supports implementation explanation without dumping full code | Chapter 7 |
| Annex I | Full Testing Tables | all backend test cases, frontend verification logs, pass/fail details | provides auditable testing evidence | Chapter 8 |
| Annex J | Logs, Screenshots, and Raw Outputs | terminal screenshots, API outputs, UI screenshots, generated strategies | strengthens implementation credibility | Chapters 7 and 8 |
| Annex K | Achievement Proofs | certificates, event photos, participation letters, evaluation sheets | supports claims in Chapter 12 | Chapter 12 |

## 13.3 DRAFT CONTENT GUIDANCE FOR EACH ANNEX

### Annex A: Project Evidence and Acknowledgement Support

Contains:

- signed review sheets
- meeting logs
- milestone approval notes
- supervisor comments

Why included:

To support formal project progression and acknowledgements.

Referenced in:

- Chapter 12

### Annex B: Organization or Domain Context

Contains:

- short write-up on Pakistan e-commerce environment
- rationale for selecting Daraz and Made-in-China
- expected buyer behavior assumptions

Why included:

To explain why the marketing and pricing logic is localized rather than generic.

Referenced in:

- Chapter 7

### Annex C: Research Papers and Literature Sources

Contains:

- papers on recommender systems
- papers on price prediction
- papers on product matching and clustering
- papers on prompt engineering and structured generation

Why included:

To show that the implementation is informed by prior research.

Referenced in:

- literature review
- Chapter 7 rationale

### Annex D: Similar Systems Comparison

Contains:

- comparison table of StrategAI with existing systems
- columns for scraping, clustering, analytics, marketing generation, governance, and localization

Why included:

To demonstrate novelty and integration depth.

Referenced in:

- introduction and discussion

### Annex E: Detailed Requirements

Contains:

- expanded requirement lists
- user stories
- acceptance criteria
- traceability mapping to modules

Why included:

To provide full requirement evidence without crowding the main chapters.

Referenced in:

- requirements chapter

### Annex F: Use Case Narrations

Contains:

- detailed textual use cases:
  - search product
  - run analytics
  - generate marketing strategy
  - regenerate strategy
  - view history

Why included:

To complement UML use case diagrams with narrative detail.

Referenced in:

- design chapter

### Annex G: Additional UML Diagrams

Contains:

- sequence diagram for `/analytics/analyze`
- component diagram
- deployment diagram
- state diagram
- optional class and activity diagrams

Why included:

To support the architectural explanation in Chapter 7.

Referenced in:

- Chapters 6 and 7

### Annex H: Algorithms and Pseudocode

Contains:

- scraper sieve filter pseudocode
- clustering pseudocode
- pricing sanity pseudocode
- marketing validation pseudocode
- decision-governance pseudocode

Why included:

To preserve technical depth without reproducing full source files.

Referenced in:

- Chapter 7

### Annex I: Full Testing Tables

Contains:

- backend test file summary
- detailed pass/fail matrix
- frontend build/lint results
- manual verification notes
- testing gap analysis

Why included:

To provide full evidence for Chapter 8.

Referenced in:

- Chapter 8

#### Annex I Draft Table 1: Raw Verification Log Summary

Table I.1: Raw Verification Log Summary

| Evidence ID | Command or check | Observed result | Status | To be attached as |
| --- | --- | --- | --- | --- |
| I-1 | `pytest -q backend/tests -p no:cacheprovider` with `PYTHONPATH=backend` | `77 passed, 2 warnings` | Pass | terminal screenshot or copied log |
| I-2 | `npm run build` in `frontend/salik-frontend` | build completed successfully | Pass | terminal screenshot |
| I-3 | `npm run lint` in `frontend/salik-frontend` | no lint errors | Pass | terminal screenshot |
| I-4 | `npm run build` in `frontend/landing-page` | TypeScript build failed | Fail | terminal screenshot |
| I-5 | `npm run lint` in `frontend/landing-page` | 5 errors and 1 warning | Fail | terminal screenshot |

#### Annex I Draft Table 2: Test Case Attachment Template

Table I.2: Test Case Attachment Template

| Test case ID | Module | Input scenario | Expected result | Actual result | Evidence reference |
| --- | --- | --- | --- | --- | --- |
| TC-SCR-01 | Scraper | Product plus accessory listing | Accessory removed | Passed | Annex I screenshot/log ref |
| TC-NLP-01 | NLP | USD price normalization | Converted to PKR | Passed | Annex I screenshot/log ref |
| TC-ANL-01 | Analytics | Extreme sell prediction | Clamped to realistic range | Passed | Annex I screenshot/log ref |
| TC-MKT-01 | Marketing | Malformed model response | Invalid strategy returned | Passed | Annex I screenshot/log ref |
| TC-MCB-01 | Governance | Contradictory low-margin case | Human review required | Passed | Annex I screenshot/log ref |

### Annex J: Logs, Screenshots, and Raw Outputs

Contains:

- backend test command outputs
- frontend build output
- frontend lint output
- screenshots of dashboard, results page, analytics page, and marketing page
- example generated strategy output

Why included:

To make the implementation observable and defensible to examiners.

Referenced in:

- Chapters 7 and 8

#### Annex J.1 Screenshot Placement Table

Table J.1: Screenshot Placement Table

| Figure ID | Screenshot title | Recommended source | Purpose in report | Chapter reference | Placeholder |
| --- | --- | --- | --- | --- | --- |
| Fig J-1 | Dashboard search interface | `salik-frontend` dashboard | Show user input entry point | Chapters 7, 13 | `[Insert Screenshot: Dashboard Search Screen]` |
| Fig J-2 | Results page with wholesale and retail cards | `salik-frontend` results page | Show scraper output presentation | Chapters 7, 13 | `[Insert Screenshot: Results Page]` |
| Fig J-3 | Analytics page with charts | `salik-frontend` analytics page | Show comparative analytics visualization | Chapters 7, 13 | `[Insert Screenshot: Analytics Charts]` |
| Fig J-4 | Marketing strategy page | `salik-frontend` marketing page | Show generated STP, SWOT, channels, and validation report | Chapters 7, 13 | `[Insert Screenshot: Marketing Strategy Page]` |
| Fig J-5 | Strategy history or regeneration flow | `salik-frontend` history/results page | Demonstrate versioning and regeneration | Chapters 7, 12, 13 | `[Insert Screenshot: Strategy History or Regeneration]` |
| Fig J-6 | Backend health or API response | browser, Postman, or terminal | Show backend service accessibility | Chapters 7, 8 | `[Insert Screenshot: Backend API Response]` |
| Fig J-7 | Backend test suite pass output | terminal | Support testing evidence | Chapters 8, 13 | `[Insert Screenshot: Backend Tests Passed]` |
| Fig J-8 | Salik frontend build success output | terminal | Support deployment readiness claim | Chapters 8, 13 | `[Insert Screenshot: Salik Frontend Build Success]` |
| Fig J-9 | Landing-page build failure output | terminal | Support testing gap analysis | Chapters 8, 13 | `[Insert Screenshot: Landing Page Build Failure]` |
| Fig J-10 | Landing-page lint failure output | terminal | Support testing gap analysis | Chapters 8, 13 | `[Insert Screenshot: Landing Page Lint Failure]` |

#### Annex J.2 Figure Caption Template

Use the following caption style under each inserted screenshot:

`Figure J-x: <brief descriptive title>.`

`Source: Captured during project verification and testing.`

`Purpose: <one-sentence explanation of the relevance of the screenshot>.`

#### Annex J.3 Individual Screenshot Placeholders

Figure J-1: Dashboard Search Screen  
Source: `salik-frontend` dashboard interface.  
Purpose: To show the primary user entry point where a product name and category are submitted for analysis.  
Placeholder:  
`[Insert Screenshot Here: Dashboard Search Screen]`

Figure J-2: Results Page Showing Wholesale and Retail Listings  
Source: `salik-frontend` results page.  
Purpose: To demonstrate how StrategAI presents filtered wholesale and retail market evidence after scraping.  
Placeholder:  
`[Insert Screenshot Here: Results Page with Wholesale and Retail Listings]`

Figure J-3: Analytics Page with Comparative Charts  
Source: `salik-frontend` analytics page.  
Purpose: To show the comparative visualization of wholesale prices, retail prices, and summary analytics.  
Placeholder:  
`[Insert Screenshot Here: Analytics Page with Charts]`

Figure J-4: Marketing Strategy Page  
Source: `salik-frontend` marketing page.  
Purpose: To demonstrate the generated marketing strategy including STP, SWOT, channel plan, and validation report.  
Placeholder:  
`[Insert Screenshot Here: Marketing Strategy Page]`

Figure J-5: Strategy History or Regeneration View  
Source: `salik-frontend` history or regeneration flow.  
Purpose: To provide evidence of version control, regeneration support, and strategy history tracking.  
Placeholder:  
`[Insert Screenshot Here: Strategy History or Regeneration Screen]`

Figure J-6: Backend API Health or Response Output  
Source: browser, Postman, curl, or terminal API call.  
Purpose: To demonstrate that the backend service is reachable and returning structured responses.  
Placeholder:  
`[Insert Screenshot Here: Backend API Health or Response]`

Figure J-7: Backend Test Suite Pass Output  
Source: terminal execution of backend tests.  
Purpose: To provide direct evidence that the automated backend test suite executed successfully.  
Placeholder:  
`[Insert Screenshot Here: Backend Test Suite Pass Output]`

Figure J-8: Salik Frontend Build Success Output  
Source: terminal execution of `npm run build` in `frontend/salik-frontend`.  
Purpose: To support the claim that the main operational frontend is buildable for deployment.  
Placeholder:  
`[Insert Screenshot Here: Salik Frontend Build Success Output]`

Figure J-9: Landing Page Build Failure Output  
Source: terminal execution of `npm run build` in `frontend/landing-page`.  
Purpose: To provide transparent evidence of the current frontend quality gap discussed in the testing chapter.  
Placeholder:  
`[Insert Screenshot Here: Landing Page Build Failure Output]`

Figure J-10: Landing Page Lint Failure Output  
Source: terminal execution of `npm run lint` in `frontend/landing-page`.  
Purpose: To provide transparent evidence of the unresolved linting issues referenced in Chapter 8.  
Placeholder:  
`[Insert Screenshot Here: Landing Page Lint Failure Output]`

### Annex K: Achievement Proofs

Contains:

- certificates
- event participation letters
- presentation photographs
- exhibition or competition screenshots
- incubation or evaluation records

Why included:

To support Chapter 12 achievement claims.

Referenced in:

- Chapter 12

## 13.4 FINAL NOTE ON APPENDIX USE

The appendices should not be treated as optional padding. In a project such as StrategAI, they are essential because they hold the evidence that converts an implementation narrative into an examiner-verifiable academic submission.

## 13.5 ASSUMPTIONS DECLARED IN THIS REPORT

The following assumptions were made transparently while preparing these chapters:

1. The current production path is the FastAPI service flow, because it is the most complete and directly wired execution path in the repository.
2. The BDI/LangGraph agents are implemented but auxiliary or legacy relative to the active API path.
3. The recommendation engine is implemented inside the analytics service rather than as a standalone class.
4. Live end-to-end external integration was not claimed as completed in this chapter because it was not executed during verification.
5. Competition and recognition items were not inferred beyond the repository evidence and are clearly marked for customization.
