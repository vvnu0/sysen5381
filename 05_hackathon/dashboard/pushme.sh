#!/bin/bash
# Push the City Congestion Streamlit dashboard to Posit Connect.
# Run from repo root. Requires CONNECT_SERVER and CONNECT_API_KEY in .env (or environment).
# After deploy, set API_URL in Posit Connect (Settings >> Vars) to your API's Connect URL.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

if [ -f "05_hackathon/.env" ]; then
  set -a
  source 05_hackathon/.env
  set +a
elif [ -f "05_hackathon/dashboard/.env" ]; then
  set -a
  source 05_hackathon/dashboard/.env
  set +a
fi

pip install rsconnect-python
rsconnect deploy streamlit \
  --server "${CONNECT_SERVER:-https://connect.systems-apps.com}" \
  --api-key "$CONNECT_API_KEY" \
  --entrypoint app \
  --title "City Congestion Tracker" \
  05_hackathon/dashboard/
