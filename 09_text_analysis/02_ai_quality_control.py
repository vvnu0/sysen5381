# 02_ai_quality_control.py
# AI-Assisted Text Quality Control
# Tim Fraser

# This script demonstrates how to use AI (Ollama or OpenAI) to perform quality control
# on AI-generated text reports. It implements quality control criteria including
# boolean accuracy checks and Likert scales for multiple quality dimensions.
# Students learn to design quality control prompts and structure AI outputs as JSON.

# 0. Setup #################################

## 0.1 Load Packages #################################

# If you haven't already, install required packages:
# pip install pandas requests python-dotenv

import pandas as pd  # for data wrangling
import re  # for text processing
import requests  # for HTTP requests
import json  # for JSON operations
import os  # for environment variables
from pathlib import Path  # for portable paths to bundled data
from dotenv import load_dotenv  # for loading .env file

## 0.2 Configuration #################################

# Load .env first so OLLAMA_* and OPENAI_* overrides apply
load_dotenv()

# Choose your AI provider: "ollama" or "openai"
AI_PROVIDER = "ollama"  # Change to "openai" if using OpenAI

# Ollama configuration (OLLAMA_HOST / OLLAMA_MODEL can be set in .env)
PORT = 11434
OLLAMA_HOST = os.getenv("OLLAMA_HOST", f"http://127.0.0.1:{PORT}")
# Default model must be installed locally (`ollama pull <name>`). Override if needed.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"  # Low-cost model

## 0.3 Load Sample Data #################################

# Load sample report text for quality control (next to this script under data/)
_DATA_DIR = Path(__file__).resolve().parent / "data"
with open(_DATA_DIR / "sample_reports.txt", "r", encoding="utf-8") as f:
    sample_text = f.read()

# Split text into individual reports
reports = [r.strip() for r in sample_text.split("\n\n") if r.strip()]
report = reports[0]

# Load source data (if available) for accuracy checking
# In this example, we'll use a simple data structure
source_data = """White County, IL | 2015 | PM10 | Time Driven | hours
|type        |label_value |label_percent |
|:-----------|:-----------|:-------------|
|Light Truck |2.7 M       |51.8%         |
|Car/ Bike   |1.9 M       |36.1%         |
|Combo Truck |381.3 k     |7.3%          |
|Heavy Truck |220.7 k     |4.2%          |
|Bus         |30.6 k      |0.6%          |"""

print("📝 Report for Quality Control:")
print("---")
print(report)
print("---\n")

# 1. AI Quality Control Function #################################

## 1.1 Create Quality Control Prompt #################################

def create_quality_control_prompt(report_text, source_data=None):
    # Base instructions for quality control
    instructions = (
        "You are a quality control validator for AI-generated environmental data reports. "
        "Read the report carefully. If source data is provided, treat it as ground truth: "
        "check every county, year, pollutant, unit, category label, and numeric value "
        "mentioned in the report against that source. Do not invent facts. "
        "Return one JSON object only. Use true or false (lowercase) for booleans. "
        "Use integers 1 through 5 only for Likert fields. No markdown fences, no extra text."
    )

    # Add source data if provided for accuracy checking
    data_context = ""
    if source_data is not None:
        data_context = (
            f"\n\nSource Data (ground truth for accuracy checks):\n{source_data}\n"
            "\nIf the report gives a combined percentage, verify it matches the sum of "
            "the matching source rows (allow small rounding like 12.1 vs 12.0).\n"
        )
    else:
        data_context = (
            "\n\nNo source table was provided. Judge accuracy using only internal "
            "consistency of the report (you cannot mark accurate false for mismatch "
            "with data you do not have).\n"
        )

    # Quality control criteria (from samplevalidation.tex) plus two extra checks
    criteria = """

Quality Control Criteria (use the anchors when you pick a score):

1. accurate (boolean): True only if nothing in the report misstates or misreads the source when source data exists, and there are no internal contradictions. Otherwise false.

2. accuracy (1-5): Fidelity to the data. 1 = major wrong numbers, wrong place/year/pollutant, or wrong category names. 3 = mostly right but a shaky combined total or fuzzy labels. 5 = numbers and labels line up with the source (or the report is internally consistent if no source).

3. formality (1-5): Register and tone. 1 = slang, very chatty, or memo-to-a-friend style. 3 = mixed. 5 = neutral technical or policy memo style suitable for government or agency work.

4. faithfulness (1-5): Sticking to what the data supports. 1 = big claims, drama, or fixes that are not justified by the table. 3 = a little speculative but still tied to the data. 5 = claims and caveats match the strength of the evidence.

5. clarity (1-5): Could a busy analyst follow it. 1 = vague referents, hard to tell what refers to what. 3 = understandable with effort. 5 = crisp sentences and clear structure.

6. succinctness (1-5): Length vs signal. 1 = lots of repetition or filler. 3 = okay length. 5 = tight wording without losing needed numbers.

7. relevance (1-5): Focus on the task. 1 = off-topic padding. 3 = some extra context but still about the data. 5 = stays on the emissions breakdown and implications.

8. completeness (1-5): Coverage of important breakdowns in the source. 1 = omits major categories or the main story of the table. 3 = hits some key rows. 5 = reflects the main categories and shares that a reader would need.

9. internal_consistency (1-5): The report agrees with itself. 1 = math or wording contradicts itself (example: shares that cannot add up, conflicting rankings). 3 = minor awkward phrasing but numbers line up. 5 = no contradictions in the narrative or arithmetic you can check from the text.

Return your response as valid JSON in this exact format (all keys required):
{
  "accurate": true,
  "accuracy": 1,
  "formality": 1,
  "faithfulness": 1,
  "clarity": 1,
  "succinctness": 1,
  "relevance": 1,
  "completeness": 1,
  "internal_consistency": 1,
  "details": "At most 50 words: name the main strength, any numeric mismatch with source if applicable, and the biggest weakness."
}
"""

    # Combine into full prompt
    full_prompt = f"{instructions}{data_context}\n\nReport Text to Validate:\n{report_text}{criteria}"

    return full_prompt

## 1.2 Query AI Function #################################

def _http_error_with_body(response):
    # Ollama often returns 404 with JSON {"error": "model 'x' not found"} — surface that text
    detail = response.text
    try:
        err = response.json().get("error")
        if err:
            detail = err
    except (ValueError, json.JSONDecodeError):
        pass
    return requests.HTTPError(f"{response.status_code} for {response.url}: {detail}", response=response)


def ollama_list_model_names(host=OLLAMA_HOST):
    r = requests.get(f"{host}/api/tags", timeout=30)
    if not r.ok:
        raise _http_error_with_body(r)
    return [m["name"] for m in r.json().get("models", [])]


def ollama_assert_model_installed(model=OLLAMA_MODEL, host=OLLAMA_HOST):
    installed = set(ollama_list_model_names(host))
    if model not in installed:
        avail = ", ".join(sorted(installed)) if installed else "(none — run ollama pull <model>)"
        raise RuntimeError(
            f"Ollama model {model!r} is not installed. Installed: {avail}. "
            f"Fix: ollama pull {model}  OR set OLLAMA_MODEL in .env to an installed name."
        )


# Function to query AI and get quality control results
def query_ai_quality_control(prompt, provider=AI_PROVIDER):
    if provider == "ollama":
        # Fail fast with a clear message if the default model was never pulled
        ollama_assert_model_installed()
        # Query Ollama
        url = f"{OLLAMA_HOST}/api/chat"
        
        body = {
            "model": OLLAMA_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "format": "json",  # Request JSON output
            "stream": False
        }
        
        response = requests.post(url, json=body, timeout=120)
        if not response.ok:
            raise _http_error_with_body(response)
        response_data = response.json()
        output = response_data["message"]["content"]
        
    elif provider == "openai":
        # Query OpenAI
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in .env file. Please set it up first.")
        
        url = "https://api.openai.com/v1/chat/completions"
        
        body = {
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a quality control validator. Always return your responses as valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "response_format": {"type": "json_object"},  # Request JSON output
            "temperature": 0.3  # Lower temperature for more consistent validation
        }
        
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json=body, timeout=120)
        if not response.ok:
            raise _http_error_with_body(response)
        response_data = response.json()
        output = response_data["choices"][0]["message"]["content"]
        
    else:
        raise ValueError("Invalid provider. Use 'ollama' or 'openai'.")
    
    return output

## 1.3 Parse Quality Control Results #################################

# Parse JSON response and convert to DataFrame
def parse_quality_control_results(json_response):
    # Try to parse JSON
    # Sometimes AI returns text with JSON, so we extract JSON if needed
    json_match = re.search(r"\{.*\}", json_response, re.DOTALL)
    if json_match:
        json_response = json_match.group(0)

    # Parse JSON
    quality_data = json.loads(json_response)

    # Newer prompts add completeness and internal_consistency; older runs might omit them
    def likert(val, default=3):
        if val is None:
            return default
        try:
            v = int(val)
            return max(1, min(5, v))
        except (TypeError, ValueError):
            return default

    acc = quality_data.get("accurate")
    if isinstance(acc, str):
        acc = acc.strip().lower() in ("true", "1", "yes")

    # Convert to DataFrame
    results = pd.DataFrame({
        "accurate": [bool(acc) if acc is not None else False],
        "accuracy": [likert(quality_data.get("accuracy"))],
        "formality": [likert(quality_data.get("formality"))],
        "faithfulness": [likert(quality_data.get("faithfulness"))],
        "clarity": [likert(quality_data.get("clarity"))],
        "succinctness": [likert(quality_data.get("succinctness"))],
        "relevance": [likert(quality_data.get("relevance"))],
        "completeness": [likert(quality_data.get("completeness"))],
        "internal_consistency": [likert(quality_data.get("internal_consistency"))],
        "details": [str(quality_data.get("details", "")).strip()],
    })

    return results

# 2. Run Quality Control #################################

## 2.1 Create Quality Control Prompt #################################

quality_prompt = create_quality_control_prompt(report, source_data)

print("🤖 Querying AI for quality control...\n")

## 2.2 Query AI #################################

ai_response = query_ai_quality_control(quality_prompt, provider=AI_PROVIDER)

print("📥 AI Response (raw):")
print(ai_response)
print()

## 2.3 Parse and Display Results #################################

quality_results = parse_quality_control_results(ai_response)

print("✅ Quality Control Results:")
print(quality_results)
print()

## 2.4 Calculate Overall Score #################################

# Calculate average Likert score (excluding boolean accurate)
_likert_cols = [
    "accuracy",
    "formality",
    "faithfulness",
    "clarity",
    "succinctness",
    "relevance",
    "completeness",
    "internal_consistency",
]
likert_scores = quality_results[_likert_cols]
overall_score = likert_scores.mean(axis=1).values[0]

quality_results["overall_score"] = round(overall_score, 2)

print(f"📊 Overall Quality Score (average of Likert scales): {overall_score:.2f} / 5.0")
print(f"📊 Accuracy Check: {'✅ PASS' if quality_results['accurate'].values[0] else '❌ FAIL'}\n")

# 3. Quality Control Multiple Reports #################################

## 3.1 Batch Quality Control Function #################################

# Function to check multiple reports
def check_multiple_reports(reports, source_data=None):
    print(f"🔄 Performing quality control on {len(reports)} reports...\n")
    
    all_results = []
    
    for i, report_text in enumerate(reports, 1):
        print(f"Checking report {i} of {len(reports)}...")
        
        # Create prompt
        prompt = create_quality_control_prompt(report_text, source_data)
        
        # Query AI
        try:
            response = query_ai_quality_control(prompt, provider=AI_PROVIDER)
            results = parse_quality_control_results(response)
            results["report_id"] = i
            all_results.append(results)
        except Exception as e:
            print(f"❌ Error checking report {i}: {e}")
        
        # Small delay to avoid rate limiting
        import time
        time.sleep(1)
    
    # Combine all results
    if all_results:
        combined_results = pd.concat(all_results, ignore_index=True)
        return combined_results
    else:
        return pd.DataFrame()

## 3.2 Run Batch Quality Control (Optional) #################################

# Uncomment to check all reports
# if len(reports) > 1:
#     batch_results = check_multiple_reports(reports, source_data)
#     print("\n📊 Batch Quality Control Results:")
#     print(batch_results)

print("✅ AI quality control complete!")
print("💡 Compare these results with manual quality control (01_manual_quality_control.py) to see how AI performs.")
