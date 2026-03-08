# Deploy City Congestion Tracker to Posit Connect Cloud

Deploy the **FastAPI** backend first, then the **Streamlit** dashboard. The dashboard talks to the API via `API_URL`; set that in Posit Connect after the API is deployed.

---

## Prerequisites

1. **Posit Connect account**  
   Accept the invite to your Connect server (e.g. `https://connect.systems-apps.com`).

2. **Publisher API key**  
   In Connect: **Account** → **Manage Your API Keys** → **+ New API Key** → choose **Publisher**, name it, create, and copy the key (you only see it once).

3. **Secrets for deployment**  
   In a `.env` file (do not commit) in `05_hackathon/` or `05_hackathon/api/` and `05_hackathon/dashboard/`:

   ```env
   CONNECT_SERVER=https://connect.systems-apps.com
   CONNECT_API_KEY=your_publisher_api_key_here
   ```

4. **Backend env vars for the API app**  
   The API needs these in Posit Connect **Settings → Vars** (or in `.env` for local runs). Set them in Connect after the first deploy:

   - `DATABASE_URL` — Supabase Postgres connection string  
   - `OLLAMA_API_KEY` — Ollama Cloud API key  
   - `OLLAMA_URL` — e.g. `https://ollama.com/api/chat`  
   - `OLLAMA_MODEL` — e.g. `gpt-oss:20b-cloud`

---

## 1. Deploy the FastAPI API

From the **repository root** (e.g. `dsai`):

```bash
# Windows (Git Bash or WSL)
bash 05_hackathon/api/pushme.sh
```

**PowerShell (Windows):** set `CONNECT_SERVER` and `CONNECT_API_KEY`, then run:

```powershell
pip install rsconnect-python
$env:CONNECT_SERVER = "https://connect.systems-apps.com"
$env:CONNECT_API_KEY = "your_publisher_api_key"
rsconnect deploy fastapi --server $env:CONNECT_SERVER --api-key $env:CONNECT_API_KEY --entrypoint main:app --title "City Congestion API" 05_hackathon/api/
```

- Note: If you use a virtualenv, activate it first; `pip install rsconnect-python` runs in the current environment.
- After the first deploy, in Posit Connect open the **City Congestion API** app → **Settings** → **Vars** and add:
  - `DATABASE_URL`
  - `OLLAMA_API_KEY`
  - `OLLAMA_URL` (optional, has default)
  - `OLLAMA_MODEL` (optional, has default)
- Copy the app’s **content URL** (e.g. `https://connect.systems-apps.com/content/<guid>/`). You need it for the dashboard.

---

## 2. Deploy the Streamlit dashboard

From the **repository root**:

```bash
bash 05_hackathon/dashboard/pushme.sh
```

**PowerShell (Windows):**

```powershell
rsconnect deploy streamlit --server $env:CONNECT_SERVER --api-key $env:CONNECT_API_KEY --entrypoint app --title "City Congestion Tracker" 05_hackathon/dashboard/
```

Then in Posit Connect, open the **City Congestion Tracker** app → **Settings** → **Vars** and set:

- `API_URL` = the **full URL of your deployed API** (e.g. `https://connect.systems-apps.com/content/39634566-78b0-4f98-a7cd-956a18a7e0fd/`).  
  Use the exact URL (with trailing slash is fine; the app strips it).

---

## 3. Republish after code changes

- **API:** From repo root run `bash 05_hackathon/api/pushme.sh` again.  
- **Dashboard:** From repo root run `bash 05_hackathon/dashboard/pushme.sh` again.  

Or in Connect use **Content** → select the app → **Republish**.

---

## 4. Optional: Regenerate manifest (API)

If you add or change dependencies in `05_hackathon/api/requirements.txt`, regenerate the manifest from repo root:

```bash
pip install rsconnect-python
rsconnect write-manifest api 05_hackathon/api
```

Then commit the updated `05_hackathon/api/manifest.json` and redeploy.

---

## Architecture reminder

- **Supabase** → only the **FastAPI** app connects (via `DATABASE_URL`).
- **Ollama Cloud** → only the **FastAPI** app calls it (via `OLLAMA_API_KEY`, etc.).
- **Streamlit** → only talks to the **FastAPI** app (via `API_URL` set in Connect).

No database or Ollama keys go in the dashboard; only `API_URL` is needed there.
