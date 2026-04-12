#!/bin/bash
# manifestme.sh

# Write a manifest.json file for a Shiny Python app,
# for deploying to Posit Connect.

# Install rsconnect package for Python
pip install rsconnect-python
# Write a manifest.json file for the Shiny Python app, directing it to the folder
# Include rag_guardian.py and agent_workflow.py; omit local SQLite artifacts.
rsconnect write-manifest shiny 04_deployment/app --overwrite \
  --exclude "*.db" --exclude "old_app.txt"