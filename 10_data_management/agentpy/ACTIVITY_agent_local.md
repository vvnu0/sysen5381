# 📌 ACTIVITY

## Run the Autonomous Agent Locally

🕒 *Estimated Time: 10-15 minutes*

---

## 📋 Overview

You will install dependencies, configure **Ollama Cloud**, and call the autonomous agent’s **FastAPI** app on your machine with **`curl`** or **[Postman](https://www.postman.com/)**. No Slack or extra chat apps—just HTTP JSON.

---

## ✅ Your Task

### 🧱 Stage 1: Environment

- [ ] Copy [`.env.example`](.env.example) to `.env` in this folder and add your **`OLLAMA_API_KEY`** from [ollama.com](https://ollama.com) (keep `.env` gitignored).
- [ ] Confirm `OLLAMA_HOST` and `OLLAMA_MODEL` match the course default (`nemotron-3-nano:30b-cloud`) unless your instructor says otherwise.
- [ ] Run `pip install -r requirements.txt` in a virtual environment you use for this course.

### 🧱 Stage 2: Start the API

- [ ] From this folder, start the server: `python -m uvicorn app.api:app --host 0.0.0.0 --port 8000`, or **`./runme.sh`**
- [ ] Open `http://127.0.0.1:8000/health` in a browser and confirm you see `"ok": true`.
- [ ] Optional: after a brief, open **`logs/agent.log`** and confirm you see turn-by-turn **`agent`** log lines (see [`README.md`](README.md) if logging is disabled).

### 🧱 Stage 3: Send a task

- [ ] `POST` to `http://127.0.0.1:8000/hooks/agent` with JSON `{"task": "Your disaster snapshot or follow-up (incident name, area, time window if relevant)"}` (use **Postman** or **`curl`** in a terminal).
- [ ] Read the JSON response: note `status`, `turns_used`, `turn_cap`, and `session_id`. If `status` is `paused_for_human`, the model hit the turn cap for that request—use `resume_token` in a follow-up request (see [`README.md`](README.md)). Optionally send **`max_turns`** (≤ server max) to use a lower cap per call.

---

# 📤 To Submit

- Screenshot of a successful **`/hooks/agent`** response (or terminal output) showing `status` and `reply`.
- One sentence: what does **`END_BRIEF`** in **[`AGENT.md`](AGENT.md)** (loaded as the system message) signal?

---

![](../../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
