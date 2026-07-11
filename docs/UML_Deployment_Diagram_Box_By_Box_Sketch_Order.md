# UML Deployment Diagram for StrategAI - Box-by-Box Sketch Order

## Purpose

This document tells you the **exact drawing order** for manually sketching the **Specification-Level UML Deployment Diagram** of StrategAI.

Use it like a practical drawing sequence:

- draw box 1 first
- then box 2
- then box 3
- then add inner boxes
- then add artifacts
- then connect everything

This is meant to help you draw neatly and avoid getting confused halfway through.

---

## Before You Start

At the top of the page, write the title:

**UML Specification-Level Deployment Diagram of StrategAI**

Leave enough space between the left, center, and right parts of the page, because the deployment diagram will be easiest to read in a wide layout.

Best page layout:

- left side = user side
- center = backend
- right side = support infrastructure
- top or bottom = external data sources

---

## Drawing Order

## Box 1: Draw the Main Backend Node First

Draw the largest and most important box in the **center** of the page:

- `<<device>> Backend/Application Server`

Why first:

- it is the central deployment node
- almost every other node connects to it
- building the diagram around it keeps the drawing balanced

Make this box large enough to contain several inner boxes and labels.

---

## Box 2: Draw the User Device on the Left

Now draw a second large node on the **left side** of the page:

- `<<device>> User Device`

Leave enough space between this box and the backend box so that you can later draw a labeled connector between them.

---

## Box 3: Draw the LLM Node on the Right

On the **right side** of the backend, draw:

- `<<device>> LLM Host`

This box is specifically for the local Ollama deployment.

Do not merge this into the backend box if you want a clean academic diagram. Even if both run locally in practice, separating them makes the deployment architecture easier to understand.

---

## Box 4: Draw the Database Node on the Right

Still on the right side, below or beside the LLM Host, draw:

- `<<device>> Supabase Cloud / Database Server`

This should be visually separate from the Ollama node.

It is better to keep the LLM runtime and persistent storage as different deployment targets.

---

## Box 5: Draw the File / Log Storage Node

Near the backend, usually to the **lower right**, draw:

- `<<device>> File / Log Storage`

This can be a smaller node than the others.

You include this because your backend performs logging and uses file-based project/runtime storage.

---

## Box 6: Draw the External Websites Node

Now draw a node either at the **top** or **bottom** of the page:

- `<<device>> External E-Commerce Websites`

If you want a more academic label, you can write:

- `<<device>> External Retail / Wholesale Websites`

This node represents the sources the scraper communicates with.

This is important because many students forget to show where scraped data comes from.

---

## Box 7: Optional Frontend Host

Only draw this if you want to reflect the development setup more closely.

Place it above the user device or slightly above-left:

- `<<device>> Frontend Host`

If you want a simpler final diagram, you may skip this node completely.

For most FYP reports, the browser plus frontend artifact is enough.

---

## Box 8: Add the Browser Execution Environment Inside User Device

Inside `User Device`, draw a smaller inner box:

- `<<executionEnvironment>> Web Browser`

This should sit comfortably inside the user device node.

Do not label the browser as a `<<device>>`. In UML deployment notation, the browser is better represented as an execution environment.

---

## Box 9: Add Frontend Artifact Inside the Browser

Inside the browser box, write one or two artifacts:

- `StrategAI Dashboard UI`
- optional `StrategAI Landing Page UI`

If you want a simpler diagram, combine them into:

- `StrategAI Frontend UI`

If your diagram starts getting crowded, use only:

- `Dashboard UI`

because that is the main operational frontend.

---

## Box 10: Add Python Runtime Inside Backend Node

Inside `Backend/Application Server`, draw an inner box:

- `<<executionEnvironment>> Python Runtime`

This is your first backend execution environment.

Keep some space inside this backend node for one more execution environment and several artifacts.

---

## Box 11: Add FastAPI/Uvicorn Execution Environment

Inside the backend node, usually below the Python runtime or inside it conceptually, draw:

- `<<executionEnvironment>> FastAPI/Uvicorn`

This shows how the backend application is served at runtime.

If you want a neat layout:

- Python Runtime at upper half
- FastAPI/Uvicorn under it
- deployed backend artifacts beneath or beside them

---

## Box 12: Optional APScheduler Environment

If you want to include the scheduler, draw another small inner box in the backend node:

- `<<executionEnvironment>> APScheduler`

This is optional but useful if your report text mentions scheduled scraping or background execution.

If you do not mention scheduling in your final report, you may omit it.

---

## Box 13: Add Backend Artifacts

Now write the backend deployed artifacts inside the backend node.

Use a simple vertical list or small artifact labels:

- `FastAPI Backend Application`
- `Scraper Module`
- `NLP / Clustering Support Module`
- `Analytics Engine`
- `Marketing Agent Service`
- `MCB Decision Agent`
- `ECDB Persistence Service`

You do not need to draw every artifact as a separate tiny UML artifact box if it becomes messy. A clean grouped list inside the backend node is acceptable in an academic deployment diagram.

If you prefer a grouped view, you can separate them into three logical blocks:

1. Data acquisition:
   - Scraper Module
   - NLP / Clustering Support

2. Intelligence:
   - Analytics Engine
   - Marketing Agent Service
   - MCB Decision Agent

3. Infrastructure:
   - FastAPI Backend Application
   - ECDB Persistence Service

---

## Box 14: Add Ollama Runtime Inside LLM Host

Inside `LLM Host`, draw:

- `<<executionEnvironment>> Ollama Runtime`

Then inside or under it, write:

- `Local LLM Model: llama3.1:8b`

This is one of the most important parts of the diagram because your project specifically uses **local Ollama**, not a cloud LLM API.

---

## Box 15: Add PostgreSQL Execution Environment Inside Database Node

Inside `Supabase Cloud / Database Server`, draw:

- `<<executionEnvironment>> PostgreSQL DBMS`

Then add the database artifact:

- `StrategAI Operational Database`

If there is space, you may add in smaller text:

- pipeline runs
- analytics results
- marketing strategies
- workflow events

But do not overload this box with too many table names.

---

## Box 16: Add File Storage Artifact

Inside `File / Log Storage`, write:

- `Application Logs`

Optional:

- `Runtime Files`

Keep this node simple.

---

## Box 17: Add External Source Label Details

Inside `External E-Commerce Websites`, write one short descriptor like:

- `Retail and Wholesale Market Sources`

or

- `Daraz / Supplier Sources / Other E-Commerce Pages`

Do not list too many brand names. Keep it generic and professional.

---

## Box 18: Optional Frontend Host Details

If you included `Frontend Host`, add:

- `<<executionEnvironment>> Vite Dev Server`

Then inside it write:

- `Dashboard Frontend Bundle`
- optional `Landing Page Bundle`

Again, this is optional. For many FYP deployment diagrams, the browser-side frontend artifact alone is enough.

---

## Now Draw the Connectors

Once all major boxes are complete, do **not** add arrows randomly. Follow this exact order.

## Connector 1: User Device to Backend

Draw a line from `User Device` to `Backend/Application Server`.

Label it:

- `HTTP/JSON REST API`

This is the main user-system communication path.

---

## Connector 2: Backend to LLM Host

Draw a line from `Backend/Application Server` to `LLM Host`.

Label it:

- `Local HTTP API (Ollama)`

This is essential because it makes the local-AI architecture visible.

---

## Connector 3: Backend to Database

Draw a line from `Backend/Application Server` to `Supabase Cloud / Database Server`.

Label it:

- `REST API / PostgreSQL Connection`

This is the safest label because your backend can reach the database through either Supabase REST or direct PostgreSQL drivers.

---

## Connector 4: Backend to File / Log Storage

Draw a line from `Backend/Application Server` to `File / Log Storage`.

Label it:

- `File I/O / Logging`

---

## Connector 5: Backend to External Websites

Draw a line from `Backend/Application Server` to `External E-Commerce Websites`.

Label it:

- `HTTPS / Web Scraping`

This shows that the scraper gathers data from external market sources.

---

## Connector 6: Optional Frontend Host to User Device

If you drew a `Frontend Host`, connect it to `User Device`.

Label it:

- `HTTP`

or

- `Static Asset Delivery`

---

## Connector 7: Optional Scheduler to Scraper Logic

If you included APScheduler, either:

- draw a small internal connector from `APScheduler` to `Scraper Module`

or

- draw a note saying:
  `Scheduled Trigger`

If you do draw the connector, label it:

- `Scheduled Trigger`

---

## Final Cleaning Step

After all boxes and lines are drawn, do a neatness pass.

Check these in order:

1. All major nodes are visible.
2. The backend is visually central.
3. The browser is inside the user device.
4. Ollama is clearly separate and local.
5. The database is clearly separate from the backend.
6. External websites are shown.
7. Connector labels are readable.
8. The figure looks like deployment, not process flow.

---

## Fastest Clean Version If You Are Short on Time

If you are in a hurry, draw only these boxes in this order:

1. `Backend/Application Server`
2. `User Device`
3. `LLM Host`
4. `Supabase Cloud / Database Server`
5. `External E-Commerce Websites`

Then add:

- browser in user device
- FastAPI + backend modules in backend
- Ollama + local model in LLM host
- PostgreSQL + operational database in DB node
- links and connector labels

That gives you a strong and academically acceptable deployment diagram even in minimal form.

---

## One-Line Reminder While Drawing

If you get confused, remember:

**Draw machines first, runtimes second, deployed software third, and communication links last.**
