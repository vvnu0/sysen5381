# agent_workflow.py
# Multi-Agent Guardian Coverage Analyzer
# Pairs with app.py (Guardian News Coverage Analyzer)
# Tim Fraser

# This module defines a custom Guardian API tool, tool metadata for function calling,
# and a 2–3 agent orchestration: (1) fetch coverage via the tool, (2) analyze the
# table, (3) optionally condense into an executive brief. When local Ollama is
# available, Agent 1 uses LLM-driven tool calls; otherwise the tool runs directly
# and cloud LLM handles the analysis agents.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import os
import sys
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

## 0.2 Import Agent Functions (local Ollama only) ########################

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "08_function_calling"))

_env_path = _REPO_ROOT / ".env"
load_dotenv(dotenv_path=_env_path)
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")

## 0.3 Configuration ################################

MODEL = "smollm2:1.7b"

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


# 1. DEFINE CUSTOM TOOL FUNCTION ###################################

def get_guardian_coverage(country, from_date, to_date, api_key=None):
    """
    Query the Guardian API for articles mentioning a country and return
    a topic breakdown summary as a pandas DataFrame.
    """
    key = api_key or GUARDIAN_API_KEY
    if not key:
        return pd.DataFrame({"error": ["Missing GUARDIAN_API_KEY"]})

    response = requests.get(
        "https://content.guardianapis.com/search",
        params={
            "q": country,
            "from-date": from_date,
            "to-date": to_date,
            "page-size": 50,
            "show-fields": "wordcount",
            "api-key": key,
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


# 2. DEFINE TOOL METADATA ###################################

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
                    "description": f"The country to search for. Options are: {', '.join(COUNTRIES)}."
                },
                "from_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format (e.g. '2026-03-01')"
                },
                "to_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format (e.g. '2026-04-01')"
                }
            }
        }
    }
}


# 3. MULTI-AGENT ORCHESTRATION ###################################

def _df_to_markdown(df):
    """Markdown table for LLM consumption (requires tabulate for pandas)."""
    return df.to_markdown(index=False)


def run_coverage_orchestration(country, from_date, to_date, *, api_key, cloud_llm_fn):
    """
    Run a 3-agent workflow: (1) Guardian coverage via tool / function calling,
    (2) media analyst report from the table, (3) executive brief from the report.

    cloud_llm_fn(system_prompt: str, user_content: str) -> str
        Must call your cloud LLM (e.g. Ollama Cloud). Used for agents 2 and 3.

    Returns a dict with keys: mode, coverage_markdown, analyst_report, executive_brief, error (optional).
    """
    role_fetch = "I fetch news article data from the Guardian API for media coverage analysis."
    task_fetch = f"Get Guardian news coverage data for {country} from {from_date} to {to_date}"

    coverage_df = None
    mode = "direct_tool_call"

    # Agent 1: prefer local Ollama + function calling; else direct tool execution
    try:
        from functions import agent_run

        result1 = agent_run(
            role=role_fetch,
            task=task_fetch,
            model=MODEL,
            output="tools",
            tools=[tool_get_guardian_coverage],
        )
        if isinstance(result1, list) and result1 and "output" in result1[0]:
            cand = result1[0]["output"]
            if isinstance(cand, pd.DataFrame) and len(cand) > 0 and "error" not in cand.columns:
                coverage_df = cand
                mode = "local_llm_tool_call"
    except Exception:
        pass

    if coverage_df is None:
        coverage_df = get_guardian_coverage(country, from_date, to_date, api_key=api_key)

    if isinstance(coverage_df, pd.DataFrame) and "error" in coverage_df.columns:
        return {
            "mode": mode,
            "coverage_markdown": _df_to_markdown(coverage_df),
            "analyst_report": "",
            "executive_brief": "",
            "error": coverage_df["error"].iloc[0] if len(coverage_df) else "Coverage fetch failed",
        }

    coverage_md = _df_to_markdown(coverage_df)

    role_analyst = (
        "You are a media analyst specializing in global news coverage patterns. "
        "Analyze the Guardian newspaper coverage data provided below. "
        "Report specific numbers and percentages from the data. "
        "Provide exactly 2 insights about the coverage patterns and what they "
        "might indicate about media attention toward this country. "
        "Use formal language. Be concise but thorough."
    )
    analyst_report = cloud_llm_fn(role_analyst, coverage_md)

    role_editor = (
        "You are an editor. Given the analyst report below, produce a short "
        "executive brief: at most 5 bullet points for decision-makers. "
        "No new facts beyond the report; formal tone."
    )
    executive_brief = cloud_llm_fn(role_editor, analyst_report)

    return {
        "mode": mode,
        "coverage_markdown": coverage_md,
        "analyst_report": analyst_report,
        "executive_brief": executive_brief,
        "error": None,
    }


# 4. CLI DEMO ###################################

if __name__ == "__main__":
    if not GUARDIAN_API_KEY:
        print("ERROR: GUARDIAN_API_KEY not found in .env file.")
        sys.exit(1)

    from functions import agent_run, df_as_text

    print("=" * 60)
    print("  Multi-Agent Guardian Coverage Analyzer (CLI)")
    print("=" * 60)

    task1 = "Get Guardian news coverage data for Australia from 2026-03-01 to 2026-04-01"
    role1 = "I fetch news article data from the Guardian API for media coverage analysis."

    print(f"\nAgent 1 task: {task1}")
    print("Running Agent 1...")
    result1 = agent_run(
        role=role1,
        task=task1,
        model=MODEL,
        output="tools",
        tools=[tool_get_guardian_coverage]
    )
    coverage_df = result1[0]["output"]
    print("\nAgent 1 result (coverage data):")
    print(df_as_text(coverage_df))

    role2 = (
        "You are a media analyst specializing in global news coverage patterns. "
        "Analyze the Guardian newspaper coverage data provided below. "
        "Report specific numbers and percentages from the data. "
        "Provide exactly 2 insights about the coverage patterns and what they "
        "might indicate about media attention toward this country. "
        "Use formal language. Be concise but thorough."
    )
    print("\nRunning Agent 2...")
    result2 = agent_run(role=role2, task=df_as_text(coverage_df), model=MODEL, output="text")
    print("\n" + "=" * 60)
    print("  Agent 2 Analysis Report")
    print("=" * 60)
    print(result2)
