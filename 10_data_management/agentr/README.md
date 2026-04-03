# README `10_data_management/agentr`

> **R / Plumber** edition of the disaster situational brief agent: same HTTP JSON contract as [`agentpy/`](../agentpy/README.md) (**`GET /health`**, **`POST /hooks/control`**, **`POST /hooks/agent`**). Uses **httr2** for Ollama **`/api/chat`**, **reticulate** + **CrewAI** **`SerperDevTool`** for **`web_search`**, and plain R for **`read_skill`** and guardrails.

---

## Quick start (local)

1. Install R packages: `plumber`, `jsonlite`, `httr2`, `reticulate`, `rsconnect` (optional, for deploy).
2. Create a Python environment with **`requirements.txt`** (same stack as agentpy for `crewai_tools`), then either:
   - `reticulate::install_python()` / `reticulate::py_install(c("crewai[tools]"), pip = TRUE)`, or  
   - Point **`RETICULATE_PYTHON`** in `.env` at that interpreter.
3. Copy **`.env.example`** → **`.env`** and set at least **`OLLAMA_API_KEY`**, **`OLLAMA_HOST`**, **`OLLAMA_MODEL`**.
4. From this folder:

```r
Rscript runme.R
```

5. **`GET http://127.0.0.1:8000/health`** and **`POST http://127.0.0.1:8000/hooks/agent`** with JSON `{"task":"…"}` (same as agentpy).

Optional: **`logs/agent.log`** when **`AGENT_LOG_FILE`** is unset (see agentpy README for disable flags).

---

## Layout

| Path | Role |
|------|------|
| **`plumber.R`** | Plumber app: routes + session store + sources **`R/`** |
| **`R/guardrails.R`** | Turn caps, skill paths, **`AGENTR_ROOT`** / **`getwd()`** |
| **`R/context.R`** | **`AGENT.md`** + skill listing in system prompt |
| **`R/tools_reticulate.R`** | **`ollama_tool_definitions`**, **`run_web_search`** (Serper via reticulate), **`run_read_skill`** |
| **`R/ollama_chat.R`** | One **`httr2`** round-trip to Ollama |
| **`R/loop.R`** | **`run_research_loop`** (parity with agentpy **`loop.py`**) |
| **`R/logging.R`** | Optional file log |
| **`AGENT.md`**, **`skills/`** | Same instructional content as agentpy |
| **`requirements.txt`** | Python deps for reticulate on Connect |

---

## Posit Connect

- Deploy as an **R API** (Plumber), not the Python **`rsconnect deploy api`** flow.
- From **`agentr/`**: **`Rscript manifestme.R`** then **`Rscript deployme.R`** (after **`rsconnect::addServer`** / **`.env`** with **`CONNECT_SERVER`** and **`CONNECT_API_KEY`**), mirroring [`08_function_calling/mcp_plumber/deployme.R`](../../08_function_calling/mcp_plumber/deployme.R).
- Ensure Connect installs **`requirements.txt`** so **`reticulate`** can import **`crewai_tools`**.
- Set server env vars: **`OLLAMA_API_KEY`**, **`OLLAMA_HOST`**, **`OLLAMA_MODEL`**, optional **`SERPER_API_KEY`**.

Smoke test after deploy: set **`AGENT_PUBLIC_URL`** and run **`Rscript testme.R`**.

---

## Parity with agentpy

Same paths and JSON fields as FastAPI **`app.api`**: session **`session_id`** / **`resume_token`**, **`turn_cap`**, **`prefetch_search_used`**, **`forced_tool_round`**, **`min_completion_turns`**, HTTP **503** when stopped, **403** / **404** for bad resume, **500** on Ollama errors.

**Note:** Plumber’s default JSON serializer may represent R **`NULL`** scalar fields (e.g. **`session_id`** on some error responses) as **`{}`** instead of JSON **`null`**. Treat **`{}`** as “no session id” when parsing; successful runs still return a string **`session_id`** as in Python.

---

← See [`../README.md`](../README.md) for the Module 10 activity index.
