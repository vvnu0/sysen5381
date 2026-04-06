# agent_workflow.py
# Multi-Agent Guardian Coverage Analyzer (Ollama Cloud + function calling)
# Pairs with app.py (Guardian News Coverage Analyzer)
# Tim Fraser

# This module provides cloud_agent / cloud_agent_run for Ollama Cloud with
# tool execution, plus Guardian API tools used by the dashboard chatbot.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

## 0.2 Load Environment Variables ####################

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_URL = "https://ollama.com/api/chat"
OLLAMA_MODEL = "gpt-oss:20b-cloud"

## 0.3 Import RAG / Guardian helpers ################

from rag_guardian import COUNTRIES as RAG_COUNTRIES, query_guardian

# Same topic classification map used in app.py
TOPIC_MAP = {
    "politics": "Politics", "world": "Politics", "us-news": "Politics",
    "uk-news": "Politics", "australia-news": "Politics", "law": "Politics",
    "global": "Politics",
    "culture": "Culture", "music": "Culture", "film": "Culture",
    "books": "Culture", "artanddesign": "Culture", "stage": "Culture",
    "tv-and-radio": "Culture", "games": "Culture", "food": "Culture",
    "environment": "Crisis", "global-development": "Crisis",
    "society": "Crisis", "inequality": "Crisis",
    "sport": "Sport", "football": "Sport", "cricket": "Sport",
    "rugby-union": "Sport", "tennis": "Sport", "cycling": "Sport",
    "formulaone": "Sport",
    "business": "Business", "technology": "Business",
    "money": "Business", "media": "Business",
    "science": "Science", "lifeandstyle": "Science", "education": "Science",
}

POPULATIONS = {
    "United States": 334, "United Kingdom": 68, "China": 1425,
    "India": 1438, "Russia": 144, "Brazil": 216,
    "Germany": 84, "France": 68, "Australia": 26, "Japan": 124,
}

COUNTRIES = list(POPULATIONS.keys())


# 1. OLLAMA CLOUD AGENT WITH TOOLS #############################

def _resolve_tool_function(func_name):
    """Find a tool function in this module or the caller's globals."""
    func = globals().get(func_name)
    if func is not None:
        return func
    for depth in range(1, 8):
        try:
            frame = sys._getframe(depth)
            func = frame.f_globals.get(func_name)
            if func is not None:
                return func
        except ValueError:
            break
    return None


def cloud_agent(messages, model=OLLAMA_MODEL, output="text", tools=None, all=False):
    """
    Single turn to Ollama Cloud. With tools, executes tool calls locally and
    attaches outputs to each tool_call dict (same pattern as 08_function_calling/functions.py).
    """
    if not OLLAMA_API_KEY:
        raise ValueError("OLLAMA_API_KEY not found in .env file.")

    body = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if tools is not None:
        body["tools"] = tools

    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(OLLAMA_URL, headers=headers, json=body, timeout=180)
    response.raise_for_status()
    result = response.json()

    if tools is not None and "tool_calls" in result.get("message", {}):
        tool_calls = result["message"]["tool_calls"]
        for tool_call in tool_calls:
            func_name = tool_call["function"]["name"]
            raw_args = tool_call["function"].get("arguments", {})
            func_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            func = _resolve_tool_function(func_name)
            if func:
                tool_output = func(**func_args)
                tool_call["output"] = tool_output

    if all:
        return result

    if "tool_calls" in result.get("message", {}):
        tool_calls = result["message"]["tool_calls"]
        if output == "tools":
            return tool_calls
        if tool_calls:
            return tool_calls[-1].get("output", result["message"].get("content", ""))
    return result["message"].get("content", "")


def cloud_agent_run(role, task, tools=None, output="text", model=OLLAMA_MODEL):
    """Run one agent turn with optional system role (mirrors functions.agent_run)."""
    messages = [
        {"role": "system", "content": role},
        {"role": "user", "content": task},
    ]
    return cloud_agent(messages=messages, model=model, output=output, tools=tools)


# 2. TOOL: FETCH ARTICLES FOR RAG / CHATBOT ##################

def search_guardian_articles(country, from_date, to_date):
    """
    Fetch Guardian articles mentioning a country in a date range.
    Returns a list of dicts with headline, trail_text, short_url, section, date, country.
    Used by Agent 1 (query parser) via function calling.
    """
    if not GUARDIAN_API_KEY:
        return [{"error": "GUARDIAN_API_KEY not configured"}]
    articles, _total, error = query_guardian(country, from_date, to_date, GUARDIAN_API_KEY)
    if error:
        return [{"error": error}]
    if not articles:
        return [{"error": f"No articles found for {country} in range {from_date} to {to_date}"}]
    return articles


tool_search_guardian_articles = {
    "type": "function",
    "function": {
        "name": "search_guardian_articles",
        "description": (
            "Fetch Guardian newspaper article records for semantic search and analysis. "
            "Use the country and date range implied by the user's question "
            "(e.g. 'United States', 'last week' as concrete YYYY-MM-DD bounds). "
            f"Country must be one of: {', '.join(RAG_COUNTRIES)}."
        ),
        "parameters": {
            "type": "object",
            "required": ["country", "from_date", "to_date"],
            "properties": {
                "country": {
                    "type": "string",
                    "description": f"Country name. Options: {', '.join(RAG_COUNTRIES)}.",
                },
                "from_date": {
                    "type": "string",
                    "description": "Start date YYYY-MM-DD (inclusive).",
                },
                "to_date": {
                    "type": "string",
                    "description": "End date YYYY-MM-DD (inclusive).",
                },
            },
        },
    },
}


# 3. TOOL: TOPIC BREAKDOWN (STANDALONE DEMO) ##################

def get_guardian_coverage(country, from_date, to_date):
    """
    Query the Guardian API for articles mentioning a country and return
    a topic breakdown summary as a pandas DataFrame.
    """
    if not GUARDIAN_API_KEY:
        return pd.DataFrame({"error": ["GUARDIAN_API_KEY not configured"]})

    response = requests.get(
        "https://content.guardianapis.com/search",
        params={
            "q": country,
            "from-date": from_date,
            "to-date": to_date,
            "page-size": 50,
            "show-fields": "wordcount",
            "api-key": GUARDIAN_API_KEY,
        },
        timeout=15,
    )

    if response.status_code != 200:
        return pd.DataFrame({"error": [f"API returned status {response.status_code}"]})

    data = response.json()
    resp = data.get("response", {})
    total = resp.get("total", 0)

    topics = []
    for article in resp.get("results", []):
        section_id = article.get("sectionId", "").lower()
        topic = TOPIC_MAP.get(section_id, "Other")
        topics.append(topic)

    if not topics:
        return pd.DataFrame({"error": [f"No articles found for {country}"]})

    topic_series = pd.Series(topics)
    topic_counts = topic_series.value_counts().reset_index()
    topic_counts.columns = ["topic", "count"]
    topic_counts["percentage"] = (topic_counts["count"] / topic_counts["count"].sum() * 100).round(1)
    topic_counts = topic_counts.sort_values("count", ascending=False)

    pop = POPULATIONS.get(country, None)
    per_1m = round(total / pop, 1) if pop else None

    topic_counts["country"] = country
    topic_counts["total_articles"] = total
    topic_counts["articles_per_1m"] = per_1m
    topic_counts["date_range"] = f"{from_date} to {to_date}"

    return topic_counts


tool_get_guardian_coverage = {
    "type": "function",
    "function": {
        "name": "get_guardian_coverage",
        "description": (
            "Fetch Guardian newspaper articles mentioning a specific country "
            "within a date range and return a topic breakdown summary with counts, "
            "percentages, and per-capita coverage. "
            f"Available countries: {', '.join(COUNTRIES)}."
        ),
        "parameters": {
            "type": "object",
            "required": ["country", "from_date", "to_date"],
            "properties": {
                "country": {
                    "type": "string",
                    "description": f"The country to search for. Options are: {', '.join(COUNTRIES)}.",
                },
                "from_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format (e.g. '2026-03-01')",
                },
                "to_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format (e.g. '2026-04-01')",
                },
            },
        },
    },
}


# 4. STANDALONE DEMO (LOCAL RUN ONLY) ########################

if __name__ == "__main__":
    if not GUARDIAN_API_KEY or not OLLAMA_API_KEY:
        print("Set GUARDIAN_API_KEY and OLLAMA_API_KEY in .env at the project root.")
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "08_function_calling"))
    from functions import df_as_text

    print("=" * 60)
    print("  Multi-Agent Guardian Coverage Analyzer (Ollama Cloud)")
    print("=" * 60)

    task1 = "Get Guardian news coverage topic breakdown for Australia from 2026-03-01 to 2026-04-01"
    role1 = "You call the get_guardian_coverage tool with the country and dates from the user message."

    print(f"\nAgent 1 task: {task1}\n")
    result1 = cloud_agent_run(
        role=role1,
        task=task1,
        model=OLLAMA_MODEL,
        output="tools",
        tools=[tool_get_guardian_coverage],
    )

    coverage_df = result1[0]["output"]
    print("Agent 1 result:")
    print(df_as_text(coverage_df))

    role2 = (
        "You are a media analyst. Analyze the Guardian coverage table below. "
        "Report specific numbers and two brief insights. Use formal language."
    )
    print("\nRunning Agent 2...\n")
    result2 = cloud_agent_run(role=role2, task=df_as_text(coverage_df), model=OLLAMA_MODEL, output="text")
    print("=" * 60)
    print(result2)
