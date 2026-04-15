# 📌 LAB

## Deploy an Autonomous Agent (Python or R)

🕒 *Estimated Time: 10–15 minutes*

---

## 📋 Lab Overview

You will deploy the same agent you ran locally to **Posit Connect** (or your class hosting environment), set environment variables on the server, and verify **`/health`** and **`/hooks/agent`** on the **public** URL. Pick the track that matches your local work:

| Track | Folder | Connect content type |
|--------|--------|----------------------|
| **Python** | [`agentpy/`](agentpy/) | **FastAPI** — **`rsconnect deploy api`** with **`app.api:app`** |
| **R** | [`agentr/`](agentr/) | **Plumber** — **`rsconnect::deployAPI`** with **`plumber.R`** |

---

## ✅ Your Task

### 🧱 Stage 1: Manifest and deploy

- [ ] **Python:** From **`agentpy/`**, run **[`manifestme.sh`](agentpy/manifestme.sh)** then **[`deployme.sh`](agentpy/deployme.sh)**, **or** follow the comments at the top of **[`agentpy/testme.py`](agentpy/testme.py)** (`rsconnect write-manifest api --entrypoint app.api:app`, then `rsconnect deploy api`).
- [ ] **R:** From the **repository root**, run **`Rscript 10_data_management/agentr/manifestme.R`** (optional, if you need a fresh manifest) then **`Rscript 10_data_management/agentr/deployme.R`** — see **[`agentr/deployme.R`](agentr/deployme.R)** and **[`agentr/README.md`](agentr/README.md)** (**`readRenviron(".env")`**, **`CONNECT_SERVER`**, **`CONNECT_API_KEY`** at repo root).
- [ ] In the Connect (or host) UI, set **`OLLAMA_API_KEY`**, **`OLLAMA_HOST`**, and **`OLLAMA_MODEL`**. Optionally set **`SERPER_API_KEY`** so preflight and **`web_search`** hit live results (omit if you accept “search disabled” behavior).
- [ ] Ensure **`AGENT.md`** and **`skills/`** deploy with the bundle (they drive the system message and **`read_skill`**). **R** track also needs **`requirements.txt`** so **reticulate** can load **crewai_tools**.

### 🧱 Stage 2: Smoke test

- [ ] Copy your deployed **base URL** (no trailing slash) into **`.env`** as **`AGENT_PUBLIC_URL`**.
- [ ] **Python:** From **`agentpy/`**, run **`python testme.py`** **or** call **`GET …/health`** manually.
- [ ] **R:** From the **repository root**, run **`Rscript 10_data_management/agentr/testme.R`** **or** call **`GET …/health`** manually.
- [ ] **`POST`** to **`…/hooks/agent`** on the **live** URL with the same JSON body you used locally; confirm you get **`200`** and a **`reply`**.

### 🧱 Stage 3: Start / stop (optional)

- [ ] **`POST`** to **`/hooks/control`** with **`{"action":"stop"}`** and confirm **`/health`** shows **`"run_enabled": false`**.
- [ ] **`POST`** with **`{"action":"start"}`** to turn the agent back on.

---

# 📤 To Submit

- Screenshot of **`GET /health`** from the **deployed** base URL showing **`"ok": true`**.
- Screenshot of a successful **`POST /hooks/agent`** against the **deployed** URL (trim long **`reply`** text if needed).

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
