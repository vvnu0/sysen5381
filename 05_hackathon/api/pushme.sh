#!/bin/bash
# pushme.sh — deploy City Congestion API (FastAPI) to Posit Connect
# Same pattern as 04_deployment/positconnect/fastapi.
# Requires api/.env with CONNECT_SERVER and CONNECT_API_KEY.
# Run from repo root: ./05_hackathon/api/pushme.sh
# Or from 05_hackathon: ./api/pushme.sh

set -e
pip install rsconnect-python
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo "Missing api/.env. Copy api/.example.env to api/.env and set CONNECT_SERVER and CONNECT_API_KEY."
  exit 1
fi
if [ -z "$CONNECT_SERVER" ] || [ -z "$CONNECT_API_KEY" ]; then
  echo "Set CONNECT_SERVER and CONNECT_API_KEY in api/.env"
  exit 1
fi
rsconnect deploy fastapi \
  --server "$CONNECT_SERVER" \
  --api-key "$CONNECT_API_KEY" \
  --entrypoint main:app \
  ./
