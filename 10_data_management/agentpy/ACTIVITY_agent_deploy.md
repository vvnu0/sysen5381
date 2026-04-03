# 📌 ACTIVITY

## Deploy the Autonomous Agent (FastAPI)

🕒 *Estimated Time: 10-15 minutes*

---

## 📋 Overview

You will deploy the same FastAPI app you ran locally to **Posit Connect** (or your class hosting environment), set environment variables on the server, and verify **`/health`** and **`/hooks/agent`** on the **public** URL.

---

## ✅ Your Task

### 🧱 Stage 1: Manifest and deploy

- [ ] Create a manifest and deploy: either run [`manifestme.sh`](manifestme.sh) then [`deployme.sh`](deployme.sh) from this folder, **or** follow the comments at the top of [`testme.py`](testme.py) (`rsconnect write-manifest api --entrypoint app.api:app`, then `rsconnect deploy api` with **`app.api:app`**).
- [ ] In the Connect (or host) UI, set **`OLLAMA_API_KEY`**, **`OLLAMA_HOST`**, and **`OLLAMA_MODEL`**. Optionally set **`SERPER_API_KEY`** so preflight and **`web_search`** hit live results (omit if you accept “search disabled” behavior). Ensure **`AGENT.md`** and **`skills/`** deploy with the bundle—they drive the system message and **`read_skill`**.

### 🧱 Stage 2: Smoke test

- [ ] Copy your deployed **base URL** (no trailing slash) into `.env` as **`AGENT_PUBLIC_URL`** and run `python testme.py` **or** call **`GET …/health`** manually.
- [ ] `POST` to **`…/hooks/agent`** on the **live** URL with the same JSON body you used locally; confirm you get a `200` and a `reply`.

### 🧱 Stage 3: Start / stop (optional)

- [ ] `POST` to **`/hooks/control`** with `{"action":"stop"}` and confirm **`/health`** shows `"run_enabled": false`.
- [ ] `POST` with `{"action":"start"}` to turn the agent back on.

---

# 📤 To Submit

- Screenshot of **`GET /health`** from the **deployed** base URL showing `"ok": true`.
- Screenshot of a successful **`POST /hooks/agent`** against the **deployed** URL (trim long `reply` text if needed).

---

![](../../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
