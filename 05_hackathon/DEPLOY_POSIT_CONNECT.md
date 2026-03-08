# Deploy City Congestion Tracker to Posit Connect Cloud

This guide deploys the **Streamlit dashboard** to [Posit Connect Cloud](https://connect.posit.cloud/). The dashboard talks only to your **FastAPI** backend; it does not connect to Supabase or Ollama directly.

**Architecture:** Supabase → FastAPI → **Streamlit (on Connect Cloud)**

Reference: [Deploy a Streamlit Application to Connect Cloud](https://docs.posit.co/connect-cloud/how-to/python/streamlit.html).

---

## Why do I need FastAPI?

Your app is designed so that:

- **Only the API** talks to Supabase (database) and to Ollama (AI).  
- **The dashboard** only calls the API over HTTP.

So the dashboard cannot work without a running API: it needs an `API_URL` to fetch locations, congestion data, and AI summaries. Deploying the FastAPI app gives you that URL. You can deploy the API to **Posit Connect** (self-hosted, same as the course example in `04_deployment/positconnect/fastapi`) or to another host (Render, Railway, etc.); then point the Streamlit app’s `API_URL` at it.

---

## A. Deploy the FastAPI API (so the dashboard has something to call)

You can deploy the API to **Posit Connect** (self-hosted) using the same pattern as the course example in `04_deployment/positconnect/fastapi`.

### A.1 One-time setup

1. **Install rsconnect-python:**  
   `pip install rsconnect-python`

2. **Create `api/.env`** (do not commit it). Copy from `api/.example.env` and set:
   - `CONNECT_SERVER` — your Posit Connect URL (e.g. `https://connect.systems-apps.com`)
   - `CONNECT_API_KEY` — API key from Connect (Account → API Keys)
   - Optionally for local runs: `DATABASE_URL`, `OLLAMA_API_KEY`, etc.

3. **Set environment variables for the API on Posit Connect** (after first deploy):  
   In Connect, open the deployed API → **Settings** / **Environment** and add:
   - `DATABASE_URL` — Supabase Postgres connection string  
   - `OLLAMA_API_KEY`, `OLLAMA_URL`, `OLLAMA_MODEL` (if you use AI summaries)

### A.2 Generate manifest and deploy

From the **repository root** (e.g. `dsai` or `05_hackathon`):

```bash
# Generate manifest (run once, or when you add/remove files)
./api/manifestme.sh

# Deploy the API to Posit Connect
./api/pushme.sh
```

Or from the `api/` directory (if your shell supports it):

```bash
cd 05_hackathon/api
./manifestme.sh
./pushme.sh
```

**Important:** `pushme.sh` sources `api/.env` for `CONNECT_SERVER` and `CONNECT_API_KEY`. On Windows you can run the same commands via Git Bash, or run the equivalent `rsconnect` commands in PowerShell (see [rsconnect-python deploy](https://docs.posit.co/rsconnect-python/commands/deploy/)).

### A.3 Get the API URL

After a successful deploy, Posit Connect shows the content URL, e.g.  
`https://connect.systems-apps.com/content/39634566-78b0-4f98-a7cd-956a18a7e0fd/`

Use that as **`API_URL`** (no trailing slash) when deploying the Streamlit app or in the dashboard’s environment.

---

## B. Deploy the Streamlit dashboard (Connect Cloud)

---

## Prerequisites (for the dashboard)

1. **FastAPI backend deployed and reachable**  
   Complete **Section A** above to deploy the API to Posit Connect, or deploy `api/` to another host (Render, Railway, Fly.io). You need a public **`API_URL`** for the dashboard. On the host, set `DATABASE_URL`, and if you use AI summaries: `OLLAMA_API_KEY`, `OLLAMA_URL`, `OLLAMA_MODEL`.

2. **GitHub account** and a **public** repository containing this project (or at least the Streamlit app and `requirements.txt`).

3. **Posit Connect Cloud** account: [Sign in](https://connect.posit.cloud/).

---

## 1. Prepare the repo (for Streamlit)

- Ensure the dashboard and its dependencies are in the repo:
  - **Primary file:** `dashboard/app.py` (or `05_hackathon/dashboard/app.py` if the repo root is the whole course repo).
  - **Requirements:** A `requirements.txt` with dashboard dependencies must be in the **repo root** or in the **same directory as the primary file** (e.g. `dashboard/` or `05_hackathon/`).  
  - This project includes:
    - `05_hackathon/requirements.txt`
    - `05_hackathon/dashboard/requirements.txt`
- Add to `.gitignore` (if not already):
  - `venv/`, `.venv/`
  - `.env` (do **not** commit secrets; set `API_URL` in Connect Cloud instead)

---

## 2. Push to GitHub

From your project root (e.g. `05_hackathon` or `dsai`):

```bash
git add .
git commit -m "Add Streamlit app and requirements for Posit Connect"
git push origin main
```

Use the branch you intend to use for deployment (e.g. `main`).

---

## 3. Deploy to Posit Connect Cloud

1. **Sign in** to [Connect Cloud](https://connect.posit.cloud/).
2. Click the **Publish** (publish) button on the Home page.
3. Choose **Streamlit**.
4. Select the **public GitHub repository** that contains the dashboard.
5. Confirm the **branch** (e.g. `main`).
6. Set the **primary file**:
   - If the repo root is `05_hackathon`: select **`dashboard/app.py`**.
   - If the repo root is the full course repo: select **`05_hackathon/dashboard/app.py`**.
7. **Environment variable (required):**
   - Add **`API_URL`** = your deployed FastAPI base URL (e.g. `https://your-api.onrender.com`), with no trailing slash.
   - Connect Cloud will inject this when the app runs; the dashboard reads it via `os.getenv("API_URL", "http://127.0.0.1:8000")`.
8. Click **Publish**.

Build logs will stream at the bottom. When the build succeeds, the app will be available at the URL shown.

---

## 4. Republish after changes

After you change the dashboard or `requirements.txt`:

1. Commit and push to the same branch.
2. In Connect Cloud, open the content and use **Republish** (republish icon).

---

## Summary

| Item              | Value / action |
|-------------------|----------------|
| **Why FastAPI?**  | Dashboard only talks to the API; the API talks to Supabase and Ollama. You need the API running to get a working dashboard. |
| **API deploy**    | Section A: use `api/manifestme.sh` and `api/pushme.sh` (same pattern as `04_deployment/positconnect/fastapi`). |
| **Dashboard (Connect Cloud)** | Streamlit only; primary file `dashboard/app.py`; set `API_URL` to your deployed API URL. |
| **Requirements**  | `requirements.txt` in repo root or next to `app.py` (dashboard); `api/requirements.txt` for the API. |

The dashboard will call `API_URL` for `/health`, `/locations`, `/congestion/*`, and `/summary`. Ensure the FastAPI app is deployed and has access to Supabase and (optionally) Ollama. The dashboard uses server-side requests, so CORS is not required unless you add browser-based API calls later.
