![Banner Image](../docs/images/icons.png)

# README Module 10 — Data management

> Use AI for data management: standardizing inputs, addresses, database workflows, and security. This module also includes a **bounded autonomous agent over HTTP**—a **disaster situational brief** service you can run and deploy in **Python** (**FastAPI**) or **R** (**Plumber**), backed by **Ollama Cloud** and optional web search.

---

## Table of Contents

- [README Module 10 — Data management](#readme-module-10--data-management)
  - [Table of Contents](#table-of-contents)
  - [Autonomous agent (HTTP)](#autonomous-agent-http)
  - [LLM-assisted data repair (R)](#llm-assisted-data-repair-r)
  - [Example folders](#example-folders)
  - [Reading materials](#reading-materials)

---

## Autonomous agent (HTTP)

Two parallel implementations share the same JSON API (**`GET /health`**, **`POST /hooks/agent`**, **`POST /hooks/control`**):

| Folder | Language | Notes |
|--------|----------|--------|
| **[`agentpy/`](agentpy/)** | Python / **FastAPI** | Default class path; **`rsconnect deploy api`**, **`app.api:app`**. |
| **[`agentr/`](agentr/)** | R / **Plumber** | Same contract; **`web_search`** via **reticulate** + CrewAI **SerperDevTool**; **`rsconnect::deployAPI`**. |

**Activities (either language — follow the track you chose):**

1. **[ACTIVITY: Run the Autonomous Agent Locally](ACTIVITY_agent_local.md)** — install deps, **`.env`**, local server on port **8000**, first **`POST /hooks/agent`**.
2. **[ACTIVITY: Deploy the Autonomous Agent](ACTIVITY_agent_deploy.md)** — Posit Connect manifest + deploy, env vars, smoke test, optional **`/hooks/control`**.

Deep dives: **[`agentpy/README.md`](agentpy/README.md)** and **[`agentr/README.md`](agentr/README.md)**.

**Typical env vars:** **`OLLAMA_API_KEY`**, **`OLLAMA_HOST`**, **`OLLAMA_MODEL`**, optional **`SERPER_API_KEY`**, optional **`AGENT_PUBLIC_URL`** for **[`agentpy/testme.py`](agentpy/testme.py)** or **[`agentr/testme.R`](agentr/testme.R)** after deploy.

---

## LLM-assisted data repair (R)

Scripts in **[`fixer/`](fixer/)** use **Ollama Cloud** from R (**`httr2`**) to **repair tabular data** (batched tool calls) and to **enrich small geospatial examples** (batched tool calls + **sf** / **ggplot2** maps). Shared HTTP + tool-parsing helpers live in **`fixer/functions.R`**; synthetic inputs under **`fixer/data/`**; run outputs under **`fixer/output/`** (gitignored).

**Activities:**

1. **[ACTIVITY: Run the CSV Fixer Agent](ACTIVITY_fixer_csv.md)** — **`.env`**, run **[`fixer/fixer_csv.R`](fixer/fixer_csv.R)**, inspect **`messy_inventory_working.csv`** and **`fix_audit.jsonl`**.
2. **[ACTIVITY: Enrich Zoning and POI Data with an LLM](ACTIVITY_fixer_spatial.md)** — run **[`fixer/fixer_parcels.R`](fixer/fixer_parcels.R)** and **[`fixer/fixer_pois.R`](fixer/fixer_pois.R)**, inspect enriched CSVs and **before/after** map PNGs. Optional: **[`fixer/fixer_spatial_context.R`](fixer/fixer_spatial_context.R)** (LLM **routes** **`nearest_poi`** / **`count_pois_within`** from parcel context; **sf** does geometry).

Course notes: **[`fixer/README.md`](fixer/README.md)**.

---

## Example folders

| Folder | Description |
|--------|-------------|
| **[`agentpy/`](agentpy/)** | **Python / FastAPI** — bounded disaster situational brief agent, Ollama **`/api/chat`**, **`POST /hooks/agent`**, no Slack. |
| **[`agentr/`](agentr/)** | **R / Plumber** — same HTTP contract; **httr2** + **reticulate** for search tools. |
| **[`fixer/`](fixer/)** | **R** — **[`fixer_csv.R`](fixer/fixer_csv.R)** (batched CSV repair), **[`fixer_parcels.R`](fixer/fixer_parcels.R)** (zoning polygons), **[`fixer_pois.R`](fixer/fixer_pois.R)** (POI points), **[`fixer_spatial_context.R`](fixer/fixer_spatial_context.R)** (contextual spatial tool routing); **sf** / **ggplot2** maps. |

**Environment variables (Slack tracks):** **`SUPABASE_URL`**, **`SUPABASE_KEY`**, **`OLLAMA_API_KEY`**, **`OLLAMA_MODEL`**, **`SLACK_BOT_TOKEN`**, **`SLACK_SIGNING_SECRET`**, **`SLACK_CHANNEL_ID`**, optional **`HEARTBEAT_SECRET`**. **Semantic memory:** optional **`MEMORY_ENABLED`**, **`MEMORY_TOP_K`**, **`MEMORY_EMBED_MODEL`**; on Posit Connect, optional **`SLACKBOT_PLUMBER_DIR`**.

---

## Reading materials

Coming soon!

---

![Footer Image](../docs/images/icons.png)

---

← 🏠 [Back to Top](#Table-of-Contents)
