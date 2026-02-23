# 06_ai_reporter.py
# AI-Powered Geographic Attention Reporter
# Combines Guardian API data with Ollama for news coverage analysis
# Tim Fraser

# This script queries the Guardian API for global news coverage data,
# processes it into structured statistics, and uses a local Ollama LLM
# to generate an analytical report with deep insights.

# 0. Setup #################################

## 0.1 Load Packages ############################

import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta

## 0.2 Load Environment Variables ################

# Load API key from .env file in project root
load_dotenv(".env")
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")

# Check if API key was loaded
if not GUARDIAN_API_KEY:
    print("ERROR: GUARDIAN_API_KEY not found in .env file")
    print("Please add: GUARDIAN_API_KEY=your_key_here")
    exit(1)

## 0.3 Configure Ollama Connection ###############

# Ollama runs locally on port 11434
OLLAMA_PORT = 11434
OLLAMA_URL = f"http://localhost:{OLLAMA_PORT}/api/generate"
OLLAMA_MODEL = "gemma3:latest"

## 0.4 Define Constants ##########################

# Countries to analyze for geographic coverage
COUNTRIES = [
    "United States", "United Kingdom", "China", "India", "Russia",
    "Brazil", "Germany", "France", "Australia", "Japan"
]

# Population data in millions (for per-capita calculations)
POPULATIONS = {
    "United States": 334, "United Kingdom": 68, "China": 1425,
    "India": 1438, "Russia": 144, "Brazil": 216,
    "Germany": 84, "France": 68, "Australia": 26, "Japan": 124
}

# 1. Query Guardian API #################################

## 1.1 Define Date Range ############################

# Query the last 30 days of coverage
end_date = datetime.now()
start_date = end_date - timedelta(days=30)
from_date_str = start_date.strftime("%Y-%m-%d")
to_date_str = end_date.strftime("%Y-%m-%d")

print(f"Querying Guardian API: {from_date_str} to {to_date_str}")
print(f"Analyzing {len(COUNTRIES)} countries...\n")

## 1.2 Fetch Article Data per Country ###############

# Store all article data and country summaries
all_articles = []
country_totals = {}

for country in COUNTRIES:
    # Make API request with enhanced fields
    response = requests.get(
        "https://content.guardianapis.com/search",
        params={
            "q": country,
            "from-date": from_date_str,
            "to-date": to_date_str,
            "page-size": 50,  # Get up to 50 sample articles per country
            "show-fields": "wordcount",  # Request wordcount field
            "api-key": GUARDIAN_API_KEY
        }
    )
    
    # Handle errors gracefully
    if response.status_code != 200:
        print(f"  WARNING: {country} - Status {response.status_code}")
        continue
    
    data = response.json()
    if data.get("response", {}).get("status") != "ok":
        print(f"  WARNING: {country} - API error")
        continue
    
    # Extract total count and article details
    total = data["response"]["total"]
    country_totals[country] = total
    
    # Process each article for detailed analysis
    for article in data["response"]["results"]:
        fields = article.get("fields", {})
        wordcount = fields.get("wordcount", "0")
        
        all_articles.append({
            "country": country,
            "title": article.get("webTitle", "N/A"),
            "section": article.get("sectionName", "N/A"),
            "pillar": article.get("pillarName", "Other"),
            "wordcount": int(wordcount) if wordcount else 0,
            "date": article.get("webPublicationDate", "")[:10]
        })
    
    print(f"  {country}: {total} articles")

print(f"\nCollected {len(all_articles)} sample articles")

## 1.3 Build DataFrames ##############################

# Create articles DataFrame
df_articles = pd.DataFrame(all_articles)

# Create country summary DataFrame
df_summary = (pd.DataFrame([
        {"country": c, "total_articles": country_totals.get(c, 0)}
        for c in COUNTRIES if c in country_totals
    ])
    .assign(
        population_m = lambda x: x["country"].map(POPULATIONS),
        articles_per_1m = lambda x: (x["total_articles"] / x["population_m"]).round(1)
    )
    .sort_values("total_articles", ascending=False)
)

# 2. Process Data for AI #################################

## 2.1 Calculate Summary Statistics ##################

total_articles = df_summary["total_articles"].sum()
avg_articles = df_summary["total_articles"].mean()
top_country = df_summary.iloc[0]["country"]
bottom_country = df_summary.iloc[-1]["country"]

# Calculate average wordcount per country
wordcount_by_country = (df_articles
    .groupby("country")["wordcount"]
    .mean()
    .round(0)
    .to_dict()
)

# Calculate pillar distribution per country (% News, Opinion, etc.)
pillar_counts = (df_articles
    .groupby(["country", "pillar"])
    .size()
    .unstack(fill_value=0)
)

# Calculate percentages
pillar_pct = pillar_counts.div(pillar_counts.sum(axis=1), axis=0) * 100
pillar_pct = pillar_pct.round(1)

## 2.2 Format Data as Structured Text ################

# Build the data block for the AI prompt
data_text = f"""DATA SUMMARY:
- Date range: {from_date_str} to {to_date_str}
- Countries analyzed: {len(df_summary)}
- Total articles: {total_articles:,}
- Average per country: {avg_articles:,.0f}

COVERAGE BY COUNTRY (sorted by volume):
"""

# Add country rows with all metrics
for _, row in df_summary.iterrows():
    country = row["country"]
    avg_wc = wordcount_by_country.get(country, 0)
    
    # Get pillar percentages for this country
    news_pct = pillar_pct.loc[country, "News"] if country in pillar_pct.index and "News" in pillar_pct.columns else 0
    opinion_pct = pillar_pct.loc[country, "Opinion"] if country in pillar_pct.index and "Opinion" in pillar_pct.columns else 0
    
    data_text += f"- {country}: {row['total_articles']:,} articles, "
    data_text += f"{row['articles_per_1m']:.1f} per 1M pop, "
    data_text += f"avg {avg_wc:.0f} words, "
    data_text += f"{news_pct:.0f}% News, {opinion_pct:.0f}% Opinion\n"

# Add top/bottom highlights
data_text += f"""
KEY OBSERVATIONS:
- Highest coverage: {top_country} ({df_summary.iloc[0]['total_articles']:,} articles)
- Lowest coverage: {bottom_country} ({df_summary.iloc[-1]['total_articles']:,} articles)
- Coverage ratio (top/bottom): {df_summary.iloc[0]['total_articles'] / df_summary.iloc[-1]['total_articles']:.1f}x
"""

print("\n" + "=" * 60)
print("DATA PREPARED FOR AI ANALYSIS")
print("=" * 60)
print(data_text)

# 3. Design AI Prompt #################################

## 3.1 Build Prompt with Role, Task, Instructions ####

prompt = f"""ROLE: You are a media analyst specializing in global news coverage patterns.

TASK: Analyze the following Guardian newspaper coverage data and produce a concise analytical report.

INSTRUCTIONS:
- USE FORMAL LANGUAGE ONLY. No hyperbole or superlatives.
- REPORT SPECIFIC NUMBERS AND PERCENTAGES from the data.
- DO NOT use phrases like "it is clear that", "obviously", or "interestingly".
- PROVIDE EXACTLY 2 DEEP INSIGHTS that go beyond restating the data.
- EXTEND EACH INSIGHT with your own analysis, implications, or tangential observations.
- FORMAT: Use markdown headers and bullet points. Keep response under 300 words.

CHAIN OF THOUGHT:
1. First, identify the top and bottom countries by raw coverage volume.
2. Compare raw coverage vs per-capita coverage to find discrepancies.
3. Analyze coverage DEPTH: Which countries get longer articles (higher avg wordcount)?
4. Analyze coverage TONE: Which countries appear more in News vs Opinion pillars?
5. Consider explanatory factors (Guardian's UK base, geopolitical relevance, crisis events).
6. Draw conclusions about media attention patterns and potential biases.

{data_text}

OUTPUT FORMAT:

## Key Statistics
- [3-4 bullet points with specific numbers from the data]

## Insight 1: [Descriptive Title]
[2-3 sentences providing deep analysis, not just restating numbers]

## Insight 2: [Descriptive Title]
[2-3 sentences providing deep analysis with implications or tangents]

## Implications
[1-2 sentences on what this means for journalists, researchers, or readers]
"""

# 4. Query Ollama #################################

## 4.1 Send Request to Local LLM ####################

print("\n" + "=" * 60)
print("SENDING TO OLLAMA...")
print("=" * 60)

try:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        },
        timeout=120  # Allow up to 2 minutes for response
    )
    
    ## 4.2 Parse Response ################################
    
    if response.status_code != 200:
        print(f"ERROR: Ollama returned status {response.status_code}")
        print("Make sure Ollama is running: ollama serve")
        exit(1)
    
    result = response.json()
    
    if "response" not in result:
        print("ERROR: Unexpected response format")
        print(json.dumps(result, indent=2))
        exit(1)
    
    ai_report = result["response"]

except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect to Ollama")
    print("Make sure Ollama is running: ollama serve")
    exit(1)

# 5. Display Report #################################

## 5.1 Print AI-Generated Analysis ###################

print("\n" + "=" * 60)
print("AI-GENERATED COVERAGE ANALYSIS REPORT")
print("=" * 60)
print(ai_report)
print("\n" + "=" * 60)
print("Report generation complete.")
print("=" * 60)
