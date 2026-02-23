# 04_openai.py
# Query OpenAI Models with API Key
# This script demonstrates how to query OpenAI's models
# using your API key stored in the .env file

# If you haven't already, install these packages...
# pip install requests python-dotenv

# Load libraries
import requests # for HTTP requests
import os # for environment variables
from dotenv import load_dotenv # for loading .env file
import time # for optional async queries

# Starting message
print("\n🚀 Querying OpenAI in Python...\n")

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Check if API key is set
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file. Please set it up first.")

# OpenAI API endpoint
url = "https://api.openai.com/v1/responses"

# Construct the request body
body = {
    "model": "gpt-4o-mini",  # Low-cost model
    "input": "Hello! Please respond with: Model is working."
}

# Set headers with API key
headers = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json"
}

# Send POST request to OpenAI API (with retry for rate limits)
max_retries = 3
for attempt in range(max_retries):
    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 429:
        error_info = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        error_msg = error_info.get("error", {}).get("message", "Rate limited by OpenAI.")
        print(f"  Rate limited (attempt {attempt + 1}/{max_retries}): {error_msg}")
        if attempt < max_retries - 1:
            wait = 2 ** (attempt + 1)
            print(f"  Retrying in {wait}s...")
            time.sleep(wait)
        else:
            print("\n  All retries exhausted. Check your OpenAI account quota/billing at:")
            print("  https://platform.openai.com/settings/organization/billing/overview")
            exit(1)
    else:
        response.raise_for_status()
        break

# Parse the response JSON
result = response.json()

# Optional - for longer queries...
# Wait for the response to finish (OpenAI returns right away, then we poll until done)
# while result.get("status") in ("created", "in_progress"):
#     time.sleep(0.5)
#     r = requests.get(f"https://api.openai.com/v1/responses/{result['id']}", headers=headers)
#     r.raise_for_status()
#     result = r.json()

# Gross, but straightforward version of extracting the model's reply
output = result['output'][0]['content'][0]['text']


# Print the model's reply
print("📝 Model Response:")
print(output)
print()

# Closing message
print("✅ OpenAI query complete.\n")
