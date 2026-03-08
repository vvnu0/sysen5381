#!/bin/bash
# manifestme.sh — write manifest.json for City Congestion API (FastAPI)
# Same pattern as 04_deployment/positconnect/fastapi (see that folder).
# Run from repo root: ./05_hackathon/api/manifestme.sh
# Or from 05_hackathon: ./api/manifestme.sh

set -e
pip install rsconnect-python
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR" && pwd)"
rsconnect write-manifest api "$APP_DIR"
