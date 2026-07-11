# UML Deployment Diagram Guide for StrategAI

## Purpose of This Guide

This guide tells you how to draw a **proper UML Deployment Diagram** for your Final Year Project, **StrategAI**, based on the actual project structure in the repository.

It is written as a drawing guide, not as a finished diagram. You should use it while manually creating your own final UML Deployment Diagram for the report.

---

## 1. What a UML Deployment Diagram Should Show for StrategAI

A UML Deployment Diagram should show the **physical deployment view** of the system, not the processing sequence and not the class structure.

For StrategAI, your deployment diagram should show:

- where the system runs
- what hardware or runtime nodes exist
- what software artifacts are deployed on those nodes
- how those nodes communicate
- which parts are local and which parts are external

For this project, the diagram should communicate one important architectural fact very clearly:

> StrategAI is a locally executed AI pipeline in which the backend runs the main business logic, the Marketing Agent calls a **local Ollama runtime**, and persistent data is stored in **Supabase/PostgreSQL**.

Your diagram is not supposed to show detailed business flow like:

`Scraper -> Clustering -> Analytics -> Marketing Agent -> Recommendation`

That belongs more naturally in a component diagram, activity diagram, or operational architecture diagram.

In the deployment diagram, you show **where these modules are deployed** and **how they communicate at runtime**.

---

## 2. What Nodes You Should Include

For StrategAI, the following nodes are the correct ones to consider.

### A. User Device

Use a UML node with stereotype:

- `<<device>> User Device`

This represents the student's laptop, examiner's machine, or end-user machine from which the system is accessed.

### B. Web Browser

Inside `User Device`, add:

- `<<executionEnvironment>> Web Browser`

This represents Chrome, Edge, or any browser used to access the frontend.

### C. Frontend Interface

Inside the browser, place the frontend artifact(s):

- `StrategAI Dashboard UI`
- `StrategAI Landing Page` (optional if you want both frontends shown)

If you want a cleaner academic diagram, you may combine them into one artifact:

- `StrategAI Frontend (React/Vite UI)`

### D. Frontend Hosting Node

Because your project contains Vite-based frontends, you may optionally add a separate node for the frontend host:

- `<<device>> Frontend Host`
- inside it: `<<executionEnvironment>> Vite Dev Server`

Use this if you want the diagram to reflect the **actual development deployment** in your project, where the frontend is started separately.

If you want a simpler report diagram, you may omit the separate frontend host and show only the browser-side UI artifact.

### E. Backend/Application Server

Add a separate node:

- `<<device>> Backend/Application Server`

This is one of the most important nodes in the whole diagram.

### F. Python Runtime / FastAPI Runtime

Inside the backend server, add one execution environment such as:

- `<<executionEnvironment>> Python Runtime`

You may optionally show:

- `<<executionEnvironment>> Uvicorn / FastAPI Runtime`

If you use both, place Uvicorn/FastAPI inside the Python runtime or next to it, depending on how detailed you want the diagram.

### G. Ollama Host / LLM Host

Because your project uses a **local LLM through Ollama**, this must be shown explicitly.

You have two valid ways to draw it:

1. As a separate node:
   - `<<device>> LLM Host`
   - inside it: `<<executionEnvironment>> Ollama Runtime`

2. As a sibling execution environment on the same physical machine as the backend:
   - inside the same local machine context, show `Ollama Runtime`

For an FYP report, the best option is usually:

- draw **Ollama as its own node**
- mention in the caption or note that it runs **locally on the same machine in the current implementation**

This makes the diagram easier to read.

### H. Database Server

Add a node:

- `<<device>> Database Server`

Since your project uses Supabase/PostgreSQL, a better label is:

- `<<device>> Supabase Cloud / Database Server`

Inside it, add:

- `<<executionEnvironment>> PostgreSQL DBMS`

### I. File / Log Storage

Add a node or sub-node for local file/log persistence:

- `<<device>> Local File Storage`

or, if you prefer not to make it a completely separate node:

- show it as a storage artifact attached to the backend node

Use this because your backend writes logs and maintains local project files and runtime data. It is a valid deployment concern.

### J. Optional Scheduler Node

Your project includes a scheduler package using APScheduler. If you want the diagram to reflect the broader system rather than only on-demand use, include:

- `<<executionEnvironment>> APScheduler`

inside the backend server.

If you want, you may also label it:

- `Scheduled Scraper Service`

### K. External E-Commerce Websites

This is the main missing thing students often forget, and in StrategAI it matters.

The scraper does not operate in isolation. It communicates with external retail and wholesale websites. So include:

- `<<device>> External E-Commerce Websites`

or

- `<<external system>> Retail / Wholesale Market Sources`

Even though `<<external system>>` is not a standard UML deployment stereotype, it is commonly used in academic diagrams and is acceptable if you keep the notation consistent.

This node is important because it shows where scraped data actually comes from.

---

## 3. What Execution Environments You Should Include

For StrategAI, the most appropriate execution environments are:

### On User Device

- `<<executionEnvironment>> Web Browser`

### On Frontend Host (optional)

- `<<executionEnvironment>> Vite Dev Server`

### On Backend/Application Server

- `<<executionEnvironment>> Python Runtime`
- `<<executionEnvironment>> FastAPI/Uvicorn`
- `<<executionEnvironment>> APScheduler` (optional but recommended if you want to show scheduled scraping support)

### On LLM Node

- `<<executionEnvironment>> Ollama Runtime`

### On Database Node

- `<<executionEnvironment>> PostgreSQL DBMS`

That is enough for a strong FYP deployment diagram. Do not overload it with unnecessary low-level execution environments such as thread pools, libraries, or package names.

---

## 4. What Artifacts or Components Should Be Deployed on Which Nodes

This is where the diagram becomes specific to StrategAI.

### A. On Web Browser

Deploy:

- `StrategAI Dashboard UI`
- `StrategAI Landing Page UI` (optional)

If you want one artifact only:

- `StrategAI Frontend Bundle`

### B. On Frontend Host (if shown)

Deploy:

- `Dashboard Frontend Bundle (React/Vite)`
- `Landing Page Bundle (React/Vite)`

You may also write:

- `salik-frontend`
- `landing-page`

if you want the labels to match the repository exactly.

### C. On Backend/Application Server

Deploy these artifacts or deployed software units:

- `FastAPI Backend Application`
- `Scraper Module`
- `NLP / Normalization Module`
- `Clustering Support Module`
- `Analytics Engine`
- `Marketing Agent Service`
- `MCB Decision Agent`
- `ECDB Persistence Service`
- `Configuration Files (.env)` (optional artifact)
- `Workflow Logging`

You can either show each of these separately, or group some of them.

A good grouping for an academic report is:

- `StrategAI Backend API`
- `Scraper Service`
- `Analytics Service`
- `Marketing Agent Service`
- `MCB Recommendation Service`
- `ECDB Data Access Layer`

### D. On Ollama Node

Deploy:

- `Ollama Runtime`
- `Local LLM Model (llama3.1:8b)`

This is very important. Do not draw only “AI model” without showing that it is running through **Ollama**.

### E. On Database Node

Deploy:

- `StrategAI Database Schema`

If you want to be more specific, list major stored artifacts:

- raw scrape tables
- normalized records
- product clusters
- analytics results
- marketing strategies
- workflow events
- pipeline runs

Do not list every table unless your diagram becomes too crowded. In most cases, one artifact label like:

- `StrategAI Operational Database`

is enough, and you can mention the important tables in accompanying text.

### F. On File / Log Storage

Deploy:

- `Application Logs`
- `Temporary Runtime Files` (optional)
- `Report / Export Files` only if your system actually produces them

### G. On Scheduler Environment

Deploy:

- `Scheduled Scraper Job`

or

- `Background Scraper Scheduler`

---

## 5. What Communication Links You Should Draw Between Nodes

These are the main communication links you should draw for StrategAI.

### Required Links

1. `User Device / Browser` -> `Frontend Host`
2. `Browser / Frontend` -> `Backend/Application Server`
3. `Backend/Application Server` -> `Ollama Runtime`
4. `Backend/Application Server` -> `Database Server`
5. `Backend/Application Server` -> `File / Log Storage`
6. `Scraper Module / Backend` -> `External E-Commerce Websites`

### Optional Links

7. `Scheduler` -> `Scraper Module`
8. `Frontend` -> `Database Server`

Only show link 8 if you explicitly want to indicate that the frontend has **optional Supabase client capability**.

Based on the repository, the dashboard mainly communicates with the backend API, while Supabase client setup exists in the frontend codebase but is not the main application path you need to emphasize in this diagram.

So for the main FYP diagram:

- **prefer Frontend -> Backend**
- treat **Frontend -> Supabase** as optional or omit it

---

## 6. What Labels You Should Place on Connectors

Connector labels matter because they make the deployment diagram look professional and technically precise.

Use the following labels.

### Browser -> Frontend Host

If you show a separate frontend host:

- `HTTP`
- `HTTPS`
- `Static asset delivery`

If you do not show a separate frontend host, then do not label this internal relationship.

### Frontend -> Backend/Application Server

Use:

- `HTTP/JSON REST API`

This is the best label for your project.

You may also write:

- `Axios HTTP requests`

but that is too implementation-specific for the final UML figure. Prefer `HTTP/JSON REST API`.

### Backend -> Ollama Runtime

Use:

- `Local HTTP API`
- `Ollama API`
- `localhost:11434`

Best academic label:

- `Local HTTP API (Ollama)`

### Backend -> Database Server

This one needs care, because your `ECDB` service can communicate through more than one mechanism.

The current code supports:

- Supabase REST over HTTPS
- direct PostgreSQL driver connection

So your safest connector label is:

- `REST API / PostgreSQL Connection`

If you want a cleaner single label:

- `Supabase REST / SQL`

### Backend -> File / Log Storage

Use:

- `File I/O`
- `Log Write`

Best label:

- `File I/O / Logging`

### Backend Scraper -> External E-Commerce Websites

Use:

- `HTTPS Scraping Requests`
- `HTML Fetch / Page Retrieval`

Best academic label:

- `HTTPS / Web Scraping`

### Scheduler -> Scraper Module

Use:

- `Scheduled Trigger`
- `Background Job Invocation`

Best label:

- `Scheduled Trigger`

---

## 7. Suggested Clean Layout for Drawing the Diagram Manually

For manual drawing, use a **left-to-right** or **top-to-bottom** deployment layout. For this project, left-to-right is usually cleaner.

### Recommended Layout

#### Left side

Place:

- `User Device`
- inside it `Web Browser`
- inside browser `StrategAI Dashboard UI`

If you want, put `Landing Page UI` beside or below it.

#### Center

Place:

- `Backend/Application Server`

Inside it, stack the execution environments and artifacts vertically:

1. `Python Runtime`
2. `FastAPI/Uvicorn`
3. backend artifacts:
   - Scraper Module
   - Clustering/NLP Module
   - Analytics Engine
   - Marketing Agent Service
   - MCB Decision Agent
   - ECDB Persistence Service
   - APScheduler (optional)

#### Right side

Place:

- `Ollama Runtime`
- `Supabase Cloud / PostgreSQL`
- `File / Log Storage`

This creates a clean “application center with supporting infrastructure on the right” view.

#### Top or bottom external side

Place:

- `External E-Commerce Websites`

Connect this to the backend scraper module.

### Why this layout works

- User-facing parts are on one side.
- Core processing is in the middle.
- support services and infrastructure are on the other side.
- external market sources are visually separate from internal system infrastructure.

This makes the diagram easy for an examiner to read in under 30 seconds.

---

## 8. Common Mistakes to Avoid

### Mistake 1: Drawing a process-flow diagram instead of a deployment diagram

Do not make the whole figure look like:

`Scraper -> Clustering -> Analytics -> Marketing Agent -> Recommendation`

That is not deployment; that is workflow.

### Mistake 2: Forgetting Ollama as a separate runtime

Do not simply write “AI Model” or “LLM” in the backend.  
Your project specifically uses:

- local LLM
- via Ollama

That must be visible.

### Mistake 3: Forgetting external scrape sources

The scraper must scrape something. If you omit the external websites, the deployment view hides an important runtime dependency.

### Mistake 4: Mixing class names with deployment nodes

Do not fill the deployment diagram with too many source-code class names. Use deployment-relevant labels such as:

- `Marketing Agent Service`
- `Analytics Engine`
- `ECDB Persistence Service`

not every Python class or function.

### Mistake 5: Overloading the database node with too many table names

You can mention the database schema or a few key stored artifacts, but do not turn the database node into a schema diagram.

### Mistake 6: Showing cloud LLM APIs

Your project does **not** use OpenAI or Anthropic in the current implementation. Do not draw them in the deployment diagram unless you clearly mark them as “future extension”.

### Mistake 7: Using vague connector labels

Do not use unlabeled lines everywhere.  
Write meaningful labels such as:

- `HTTP/JSON REST API`
- `Local HTTP API (Ollama)`
- `REST API / PostgreSQL Connection`
- `HTTPS / Web Scraping`
- `File I/O / Logging`

### Mistake 8: Confusing frontend and browser

The browser is the execution environment.  
The frontend bundle is the deployed artifact.

### Mistake 9: Omitting the scheduler when claiming automated scraping

If your report text mentions scheduled scraping, then include the scheduler in the deployment diagram or mark it as optional.

---

## 9. Final Checklist for Drawing

Use this checklist while making the final diagram.

### Node Checklist

- [ ] I included `User Device`.
- [ ] I included `Web Browser` as an execution environment.
- [ ] I included the frontend UI artifact.
- [ ] I included the backend/application server.
- [ ] I included the Python/FastAPI runtime.
- [ ] I included the local `Ollama Runtime`.
- [ ] I included the database server (`Supabase/PostgreSQL`).
- [ ] I included file/log storage.
- [ ] I included the optional scheduler if I mention scheduled scraping elsewhere.
- [ ] I included external e-commerce websites as scrape targets.

### Artifact Checklist

- [ ] Frontend artifact is placed on the browser or frontend host.
- [ ] Backend artifacts are placed on the backend server.
- [ ] Ollama and the local model are placed on the LLM node.
- [ ] Database schema/data artifacts are placed on the database node.
- [ ] Log artifacts are placed on local storage or the backend host.

### Connector Checklist

- [ ] Frontend to backend link is labeled `HTTP/JSON REST API`.
- [ ] Backend to Ollama link is labeled `Local HTTP API (Ollama)`.
- [ ] Backend to database link is labeled `REST API / PostgreSQL Connection`.
- [ ] Backend to file storage is labeled `File I/O / Logging`.
- [ ] Scraper to external websites is labeled `HTTPS / Web Scraping`.
- [ ] Scheduler link, if shown, is labeled `Scheduled Trigger`.

### Quality Checklist

- [ ] My deployment diagram shows physical/runtime deployment, not workflow sequence.
- [ ] My notation uses proper UML node and execution-environment concepts.
- [ ] My labels are specific to StrategAI, not generic placeholders.
- [ ] The diagram clearly shows that Ollama is local, not cloud-based.
- [ ] The diagram is readable without needing long explanation.

---

## Recommended Final Wording for Figure Caption

If you want a formal caption under your hand-drawn figure, use something like:

**Figure X.X: UML Deployment Diagram of StrategAI showing the client interface, backend processing environment, local Ollama-based LLM runtime, persistent database layer, external scrape targets, and optional scheduler support.**

---

## Project-Specific Additions You Should Not Forget

After reviewing the project repository, the following items are worth adding because they are easy to miss:

1. **External E-Commerce Websites**
   The scraper depends on external retail and wholesale sources, so they should appear as external nodes.

2. **Optional APScheduler-Based Scheduler**
   There is a scheduler package in the backend, so if your report mentions automated scraping, include it.

3. **ECDB as the backend data-access layer**
   The backend does not talk to the database as an abstract idea only; it uses an explicit persistence service (`ECDB`). You do not need to draw the class name prominently, but the backend-to-database relationship should reflect that there is a dedicated data-access layer.

4. **Supabase/PostgreSQL as persistent storage**
   Do not label the database vaguely as just “Database”. Use `Supabase/PostgreSQL` or `Supabase Cloud / PostgreSQL DBMS`.

5. **Local Ollama runtime with local model**
   This is a defining feature of StrategAI and should be visually obvious.

6. **Two frontends exist in the repository**
   The project contains a dashboard frontend and a landing page frontend. If your deployment diagram must stay simple, combine them as one frontend interface artifact. If you want higher fidelity, show both as separate deployed artifacts.

7. **Frontend direct Supabase client exists but is not the main emphasized path**
   Because the dashboard primarily talks to the backend API, your main deployment diagram should emphasize `Frontend -> Backend`. Direct frontend-to-Supabase access may be omitted or shown as optional.
