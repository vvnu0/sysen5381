# test_requests.py
# POST request with JSON data (example using requests)
# Pairs with ACTIVITY_add_documentation_to_cursor.md
# Tim Fraser

# Demonstrates how to send a POST request with a JSON body using the requests library.
# The json= parameter encodes the payload and sets Content-Type: application/json automatically.

# 0. Setup #################################

## 0.1 Load Packages ############################

import requests  # for HTTP requests

## 0.2 Make POST request with JSON ###############################

url = "https://httpbin.org/post"
payload = {"name": "test"}

# Use json= so requests encodes the dict and sets Content-Type: application/json
r = requests.post(url, json=payload)

# Optional: check status and parse JSON response
r.raise_for_status()
print(r.json())
