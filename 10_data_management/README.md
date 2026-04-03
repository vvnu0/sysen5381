![Banner Image](../docs/images/icons.png)

# README Module 10 — Data management

> Use AI for data management: standardizing inputs, addresses, database workflows, and security. This module also includes a **bounded autonomous agent over HTTP**—a **disaster situational brief** service you can run and deploy in **Python** (**FastAPI**) or **R** (**Plumber**), backed by **Ollama Cloud** and optional web search.

---

## Table of Contents

- [README Module 10 — Data management](#readme-module-10--data-management)
  - [Table of Contents](#table-of-contents)
  - [Autonomous agent (HTTP)](#autonomous-agent-http)
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

## Example folders

| Folder | Description |
|--------|-------------|
| **[`agentpy/`](agentpy/)** | **Python / FastAPI** — bounded disaster situational brief agent, Ollama **`/api/chat`**, **`POST /hooks/agent`**, no Slack. |
| **[`agentr/`](agentr/)** | **R / Plumber** — same HTTP contract; **httr2** + **reticulate** for search tools. |

**Environment variables (Slack tracks):** **`SUPABASE_URL`**, **`SUPABASE_KEY`**, **`OLLAMA_API_KEY`**, **`OLLAMA_MODEL`**, **`SLACK_BOT_TOKEN`**, **`SLACK_SIGNING_SECRET`**, **`SLACK_CHANNEL_ID`**, optional **`HEARTBEAT_SECRET`**. **Semantic memory:** optional **`MEMORY_ENABLED`**, **`MEMORY_TOP_K`**, **`MEMORY_EMBED_MODEL`**; on Posit Connect, optional **`SLACKBOT_PLUMBER_DIR`**.

---

## Reading materials

Coming soon!

---

![Footer Image](../docs/images/icons.png)

---

← 🏠 [Back to Top](#Table-of-Contents)
