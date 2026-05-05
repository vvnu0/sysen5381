#!/bin/bash
# manifestme.sh

# Write a manifest.json file for a Shiny Python app,
# for deploying to Posit Connect.

# Install rsconnect package for Python
pip install rsconnect-python
# Write a manifest.json file for the Shiny Python app, directing it to the folder.
# Include rag_guardian.py, agent_workflow.py, prompt_validation_experiment.py, and
# bundled validation_rubric.md + validation_results/ + validated_reports/ so the
# in-app validation panel works on Connect. Omit local SQLite artifacts.
rsconnect write-manifest shiny 04_deployment/app --overwrite \
  --exclude "*.db" --exclude "old_app.txt" --exclude "__pycache__"