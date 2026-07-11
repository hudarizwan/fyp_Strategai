# UML Deployment Diagram for StrategAI - 10 Minute Version

## Goal

This guide is for drawing a **UML Deployment Diagram** using notation style similar to the reference image:

- **3D node boxes** for devices and execution environments
- **nested boxes** to show what runs inside what
- **artifact rectangles** for deployed software units
- **communication paths** as labeled lines between nodes

This is **not** a workflow diagram.  
Do **not** draw only:

`Scraper -> Clustering -> Analytics -> Marketing -> Recommendation`

Instead, show:

- where StrategAI runs
- what runtime nodes exist
- what software is deployed on each node
- how those nodes communicate

---

## 1. UML Notation to Use

Use the following **shapes exactly** while drawing.

### 1.1 Deployment Frame

Use a large **outer rectangular frame with a small tab/header** at the top-left.

Write inside the header:

`deployment StrategAI Decision Support System`

This frame represents the whole deployed system.

---

### 1.2 Device Node Shape

Use a **3D box / node box** for each hardware or hosted runtime node.

Write the stereotype at the top:

`<<device>>`

Then write the node name below it.

Example format:

`<<device>> Backend/Application Server`

Use this shape for:

- User Device
- Frontend Host
- Backend/Application Server
- Ollama Host
- Supabase Cloud Server
- External E-Commerce Platforms

---

### 1.3 Execution Environment Shape

Inside a device, draw another **nested 3D box**.

Write the stereotype:

`<<executionEnvironment>>`

Then write the runtime name.

Example:

`<<executionEnvironment>> FastAPI/Uvicorn Runtime`

Use this shape for:

- Web Browser
- Vite Dev Server
- Python Runtime
- FastAPI/Uvicorn Runtime
- Ollama Runtime
- PostgreSQL DBMS
- APScheduler Runtime (optional)

---

### 1.4 Artifact Shape

Use a **rectangle with a folded top-right corner**.

Write the stereotype:

`<<artifact>>`

Then write the deployed software or logical software package name.

Example:

`<<artifact>> StrategAI Backend API`

Use this shape for:

- Dashboard UI
- Landing Page UI
- FastAPI Backend API
- Scraper Module
- NLP / Clustering Module
- Analytics Engine
- Marketing Agent Service
- MCB Decision Agent
- ECDB Persistence Layer
- llama3.1:8b Model
- Database schemas or logical data stores if you want detailed DB view

---

### 1.5 Communication Path

Use a **solid line** between nodes.

Write a small label above the line in this style:

`<<protocol>> HTTP/JSON`

Use this for:

- Browser to Backend
- Backend to Ollama
- Backend to Supabase
- Backend to External Websites
- Frontend Host to Browser

---

## 2. Correct StrategAI Deployment View

Based on the actual project, your deployment diagram should show these main runtime nodes:

1. `<<device>> User Device`
2. `<<device>> Frontend Host`
3. `<<device>> Backend/Application Server`
4. `<<device>> Ollama Host`
5. `<<device>> Supabase Cloud Server`
6. `<<device>> External E-Commerce Platforms`

Optional:

7. `<<executionEnvironment>> APScheduler Runtime`

Important accuracy note:

- `APScheduler` exists in the project, but it is **not started by default** from `main.py` or the startup scripts.
- Therefore, show it as **optional** or **future/auxiliary deployment detail**, not as the core always-running path.

---

## 3. Step-by-Step Drawing Instructions

Follow this order exactly.

---

## Step 1: Draw the Outer Deployment Frame

Draw one large rectangle around the whole diagram with a small header tab.

Write:

`deployment StrategAI Decision Support System`

This matches the notation style of the reference image.

---

## Step 2: Draw the Left-Side User Node

Draw a **3D device box** on the far left.

Label:

`<<device>> User Device`

Inside it, draw one nested **execution environment** box.

Label:

`<<executionEnvironment>> Web Browser`

Inside the browser box, draw two **artifact** rectangles:

1. `<<artifact>> StrategAI Dashboard UI`
2. `<<artifact>> StrategAI Landing Page UI`

If space is limited, you may keep only:

`<<artifact>> StrategAI Dashboard UI`

But if you want full project accuracy, include both.

---

## Step 3: Draw the Frontend Host Node

Place this above the User Device or slightly upper-left/center.

Draw a **3D device box**.

Label:

`<<device>> Frontend Host`

Inside it, draw one or two nested execution environments.

Recommended labels:

1. `<<executionEnvironment>> Vite Dev Server - Dashboard`
2. `<<executionEnvironment>> Vite Dev Server - Landing Page`

Inside them, place artifacts:

1. `<<artifact>> Dashboard Frontend Build`
2. `<<artifact>> Landing Page Frontend Build`

This is correct because your project contains two separate frontend applications.

---

## Step 4: Draw the Main Backend Node in the Center

This should be the largest and most important node in the diagram.

Draw a large **3D device box** in the center.

Label:

`<<device>> Backend/Application Server`

Inside it, draw a nested execution environment:

1. `<<executionEnvironment>> Python Runtime`

Inside that, draw another nested execution environment:

2. `<<executionEnvironment>> FastAPI/Uvicorn Runtime`

Inside the FastAPI/Uvicorn runtime, place these artifacts:

1. `<<artifact>> StrategAI Backend API`
2. `<<artifact>> Scraper Module`
3. `<<artifact>> NLP / Clustering Module`
4. `<<artifact>> Analytics Engine`
5. `<<artifact>> Marketing Agent Service`
6. `<<artifact>> MCB Decision Agent`
7. `<<artifact>> ECDB Persistence Layer`

These are the most correct names for your project-level deployment view.

---

## Step 5: Add APScheduler Correctly

If you want to show scheduling support, draw a smaller nested execution environment near the Python runtime.

Label:

`<<executionEnvironment>> APScheduler Runtime`

Inside it, place:

`<<artifact>> Scheduled Scraper Job`

Important:

- Draw this as an **optional nested runtime** inside the backend node.
- Do **not** make it look like the whole system depends on it.
- If your teacher prefers only active deployment pieces, you may omit it.

---

## Step 6: Draw the Ollama Node on the Right

Draw a **3D device box** on the right side.

Label:

`<<device>> Ollama Host`

Inside it, draw one nested execution environment.

Label:

`<<executionEnvironment>> Ollama Runtime`

Inside it, place artifacts:

1. `<<artifact>> Ollama Service`
2. `<<artifact>> llama3.1:8b Model`

This is a very important part of your diagram because the marketing agent uses the local model through Ollama.

---

## Step 7: Draw the Database Node

Place another **3D device box** to the right side, near the Ollama node.

Label:

`<<device>> Supabase Cloud Server`

Inside it, draw one nested execution environment.

Label:

`<<executionEnvironment>> PostgreSQL DBMS`

Inside it, draw artifacts. Use either the **simple version** or the **detailed version** below.

### Simple Version

1. `<<artifact>> StrategAI Operational Database`

### Detailed Version

1. `<<artifact>> Pipeline and Workflow Tables`
2. `<<artifact>> Raw Scrape Data Tables`
3. `<<artifact>> Analytics and Recommendation Tables`
4. `<<artifact>> Marketing Strategy Tables`

If your diagram space is small, use the simple version.

---

## Step 8: Draw the External Source Node

Draw another **3D device box** at the top or bottom.

Label:

`<<device>> External E-Commerce Platforms`

Inside it, you may place one artifact:

`<<artifact>> Wholesale and Retail Product Listings`

If you want more detail, write small text inside the node such as:

- Alibaba / 1688 / GlobalSources
- Daraz / retail marketplace pages

Do not overcrowd this node.

---

## Step 9: Draw the Communication Paths

Now connect the nodes using **solid lines**.

Label each line with a protocol-style tag.

### 9.1 Frontend Host to User Device

Connect:

`Frontend Host -> User Device`

Label:

`<<protocol>> HTTP`

---

### 9.2 User Device / Browser to Backend

Connect:

`Web Browser -> Backend/Application Server`

Label:

`<<protocol>> HTTP/JSON REST API`

This is correct because the dashboard calls backend endpoints for scraping, analytics, and marketing.

---

### 9.3 Backend to Ollama

Connect:

`Backend/Application Server -> Ollama Host`

Label:

`<<protocol>> Local HTTP API`

You may also write:

`<<protocol>> Ollama HTTP API`

---

### 9.4 Backend to Supabase

Connect:

`Backend/Application Server -> Supabase Cloud Server`

Label:

`<<protocol>> PostgreSQL / Supabase REST`

This is more accurate than writing only “database connection”.

---

### 9.5 Backend to External Platforms

Connect:

`Backend/Application Server -> External E-Commerce Platforms`

Label:

`<<protocol>> HTTPS / Web Scraping`

---

### 9.6 APScheduler to Scraper Module

Only if you include APScheduler:

Connect:

`APScheduler Runtime -> Scraper Module`

Label:

`<<trigger>> Scheduled Trigger`

This should be a short internal connector inside the backend area.

---

## 4. Best Layout for Fast Hand Drawing

Use this arrangement for a clean 10-minute exam drawing.

### Left

- `<<device>> User Device`
- inside it `<<executionEnvironment>> Web Browser`
- inside it UI artifacts

### Upper Left or Upper Center

- `<<device>> Frontend Host`
- inside it Vite runtime artifacts

### Center

- `<<device>> Backend/Application Server`
- inside it Python Runtime
- inside Python Runtime, FastAPI/Uvicorn Runtime
- inside FastAPI/Uvicorn Runtime, backend artifacts
- optional APScheduler inside backend

### Right

- `<<device>> Ollama Host`
- `<<device>> Supabase Cloud Server`

### Top or Bottom

- `<<device>> External E-Commerce Platforms`

This gives a balanced deployment view and matches the style of the sample diagram.

---

## 5. Exact Names You Should Write

Use these exact labels in the diagram.

### Deployment Frame

`deployment StrategAI Decision Support System`

### Device Nodes

`<<device>> User Device`

`<<device>> Frontend Host`

`<<device>> Backend/Application Server`

`<<device>> Ollama Host`

`<<device>> Supabase Cloud Server`

`<<device>> External E-Commerce Platforms`

### Execution Environments

`<<executionEnvironment>> Web Browser`

`<<executionEnvironment>> Vite Dev Server - Dashboard`

`<<executionEnvironment>> Vite Dev Server - Landing Page`

`<<executionEnvironment>> Python Runtime`

`<<executionEnvironment>> FastAPI/Uvicorn Runtime`

`<<executionEnvironment>> APScheduler Runtime`

`<<executionEnvironment>> Ollama Runtime`

`<<executionEnvironment>> PostgreSQL DBMS`

### Artifacts

`<<artifact>> StrategAI Dashboard UI`

`<<artifact>> StrategAI Landing Page UI`

`<<artifact>> Dashboard Frontend Build`

`<<artifact>> Landing Page Frontend Build`

`<<artifact>> StrategAI Backend API`

`<<artifact>> Scraper Module`

`<<artifact>> NLP / Clustering Module`

`<<artifact>> Analytics Engine`

`<<artifact>> Marketing Agent Service`

`<<artifact>> MCB Decision Agent`

`<<artifact>> ECDB Persistence Layer`

`<<artifact>> Scheduled Scraper Job`

`<<artifact>> Ollama Service`

`<<artifact>> llama3.1:8b Model`

`<<artifact>> StrategAI Operational Database`

`<<artifact>> Wholesale and Retail Product Listings`

---

## 6. What Not to Write

Avoid these weaker or less accurate labels:

- `Database` only
- `Server` only
- `AI Module` only
- `Marketing` only
- `Frontend` only
- `AP Scheduler` as a top-level main system node

Also avoid putting every table name, every class name, or every API route in the deployment diagram.

---

## 7. Examiner-Safe Final Version

If you want the cleanest final drawing, use this reduced version:

1. `<<device>> User Device`
   inside: `<<executionEnvironment>> Web Browser`
   inside: `<<artifact>> StrategAI Dashboard UI`, `<<artifact>> StrategAI Landing Page UI`

2. `<<device>> Frontend Host`
   inside: `<<executionEnvironment>> Vite Dev Server`
   inside: `<<artifact>> Dashboard Frontend Build`, `<<artifact>> Landing Page Frontend Build`

3. `<<device>> Backend/Application Server`
   inside: `<<executionEnvironment>> Python Runtime`
   inside: `<<executionEnvironment>> FastAPI/Uvicorn Runtime`
   inside: backend artifacts

4. `<<device>> Ollama Host`
   inside: `<<executionEnvironment>> Ollama Runtime`
   inside: `<<artifact>> llama3.1:8b Model`

5. `<<device>> Supabase Cloud Server`
   inside: `<<executionEnvironment>> PostgreSQL DBMS`
   inside: `<<artifact>> StrategAI Operational Database`

6. `<<device>> External E-Commerce Platforms`

Optional:

7. `<<executionEnvironment>> APScheduler Runtime`
   inside backend only

---

## 8. Final Checklist

- [ ] I used a deployment frame with a title tab.
- [ ] I used 3D node boxes for devices.
- [ ] I used nested 3D boxes for execution environments.
- [ ] I used artifact rectangles with folded corners.
- [ ] I placed the browser inside the user device.
- [ ] I placed FastAPI/Uvicorn inside the backend server.
- [ ] I placed Ollama in its own host node.
- [ ] I placed PostgreSQL inside the Supabase cloud node.
- [ ] I labeled communication lines with protocols.
- [ ] I kept APScheduler optional.
- [ ] I drew a deployment view, not a workflow pipeline.

---

## When You Want Me To Review Your Hand-Drawn Diagram

Send me one of these:

1. a photo of the hand-drawn diagram
2. a screenshot of the digital diagram
3. a typed list of the nodes and links you drew

Then I can check:

- UML notation correctness
- naming accuracy
- missing nodes
- wrong stereotypes
- whether the layout is examiner-ready
