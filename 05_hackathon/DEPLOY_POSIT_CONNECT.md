# Deploy City Congestion Tracker to Posit Connect Cloud

This guide deploys the **Streamlit dashboard** to [Posit Connect Cloud](https://connect.posit.cloud/). The dashboard talks only to your **FastAPI** backend; it does not connect to Supabase or Ollama directly.

**Architecture:** Supabase → FastAPI → **Streamlit (on Connect Cloud)**

Reference: [Deploy a Streamlit Application to Connect Cloud](https://docs.posit.co/connect-cloud/how-to/python/streamlit.html).

---

## Prerequisites

1. **FastAPI backend deployed and reachable**  
   The dashboard needs a public `API_URL`. Deploy the `api/` (FastAPI) app to a host such as:
   - [Render](https://render.com/) (Web Service)
   - [Railway](https://railway.app/)
   - [Fly.io](https://fly.io/)
   - Another cloud that gives you a public HTTPS URL

   On that host, set:
   - `DATABASE_URL` (Supabase Postgres)
   - `OLLAMA_API_KEY`, `OLLAMA_URL`, `OLLAMA_MODEL` (if you use AI summaries)

2. **GitHub account** and a **public** repository containing this project (or at least the Streamlit app and `requirements.txt`).

3. **Posit Connect Cloud** account: [Sign in](https://connect.posit.cloud/).

---

## 1. Prepare the repo

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
| **What runs on Connect** | Streamlit dashboard only |
| **Primary file**  | `dashboard/app.py` (or `05_hackathon/dashboard/app.py`) |
| **Required env**  | `API_URL` = public FastAPI base URL |
| **Requirements**  | `requirements.txt` in repo root or next to `app.py` |

The dashboard will call `API_URL` for `/health`, `/locations`, `/congestion/*`, and `/summary`. Ensure the FastAPI app is deployed and has access to Supabase and (optionally) Ollama. The dashboard uses server-side requests, so CORS is not required unless you add browser-based API calls later.
