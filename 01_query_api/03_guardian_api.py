# 03_guardian_api.py
# Example: Fetching an Article from The Guardian API
# Pairs with 02_example.py
# Tim Fraser

# This script shows how to:
# - Load an API key from a .env file
# - Make a GET request to The Guardian's search endpoint
# - Retrieve and display one article

# 0. Setup #################################

## 0.1 Load Packages ############################

import os  # for reading environment variables
import requests  # for making HTTP requests
from dotenv import load_dotenv  # for loading variables from .env

## 0.2 Load Environment Variables ################

# Load environment variables from the .env file
load_dotenv(".env")

# Get the Guardian API key from the environment
# You'll need to add GUARDIAN_API_KEY=your_key_here to your .env file
# Register for a free key at: https://open-platform.theguardian.com/access/
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")

# 1. Make API Request ###########################

# The Guardian API uses the api-key as a query parameter (not a header)
# We'll search for one article about "technology"
response = requests.get(
    "https://content.guardianapis.com/search",
    params={
        "q": "technology",        # search query
        "page-size": 1,           # limit to 1 result
        "api-key": GUARDIAN_API_KEY
    }
)

# 2. Inspect Response ###########################

# View response status code (200 = success)
print("Status Code:", response.status_code)

# Extract the response as JSON
data = response.json()

# Check if the request was successful
if response.status_code == 200 and data.get("response", {}).get("status") == "ok":
    # Get the first article from the results
    results = data["response"]["results"]
    if results:
        article = results[0]
        print("\n--- Article Found ---")
        print("Title:", article.get("webTitle"))
        print("Section:", article.get("sectionName"))
        print("Date:", article.get("webPublicationDate"))
        print("URL:", article.get("webUrl"))
    else:
        print("No articles found.")
else:
    # Print error message if request failed
    print("Error:", data.get("message", "Unknown error"))
