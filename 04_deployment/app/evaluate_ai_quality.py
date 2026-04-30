# evaluate_ai_quality.py
# Validation runner for the Geographic Attention Reporter
# Tim Fraser / Nairv

# This script tests whether the AI planner, Guardian API tool, and RAG retrieval
# path behave consistently across representative user questions.

# 0. Setup #################################

## 0.1 Load Packages ############################

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from agent_workflow import (
    COUNTRIES,
    GUARDIAN_API_KEY,
    OLLAMA_API_KEY,
    OLLAMA_MODEL,
    cloud_agent_run,
    tool_search_guardian_articles,
)
from rag_guardian import build_index, connect_db, reset_rag_schema, search as rag_search


## 0.2 Evaluation Cases #########################

TEST_CASES = [
    {
        "id": "us_basketball_last_week",
        "question": "What was happening in basketball in the United States last week?",
        "expected_country": "United States",
        "min_sources": 1,
    },
    {
        "id": "uk_yesterday",
        "question": "What did The Guardian cover about the United Kingdom yesterday?",
        "expected_country": "United Kingdom",
        "min_sources": 1,
    },
    {
        "id": "brazil_climate_last_month",
        "question": "What was covered about climate and Brazil last month?",
        "expected_country": "Brazil",
        "min_sources": 1,
    },
    {
        "id": "france_politics_last_week",
        "question": "Summarize French politics coverage from last week.",
        "expected_country": "France",
        "min_sources": 1,
    },
    {
        "id": "australia_sport_last_week",
        "question": "What sports stories mentioned Australia last week?",
        "expected_country": "Australia",
        "min_sources": 1,
    },
    {
        "id": "japan_business_last_month",
        "question": "What business coverage mentioned Japan last month?",
        "expected_country": "Japan",
        "min_sources": 1,
    },
]


# 1. Helper Functions ##############################

def print_rule(title):
    """Print a visible section divider for readable logs."""
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def extract_tool_arguments(tool_call):
    """Parse tool-call arguments returned by the planner model."""
    raw_args = tool_call.get("function", {}).get("arguments", {})
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args)
        except json.JSONDecodeError:
            return {}
    return raw_args if isinstance(raw_args, dict) else {}


def extract_articles_and_args(tool_calls):
    """Return planner arguments, retrieved articles, and an optional error."""
    if not isinstance(tool_calls, list) or not tool_calls:
        return {}, [], "Planner returned no tool calls."

    for tool_call in tool_calls:
        args = extract_tool_arguments(tool_call)
        output = tool_call.get("output")
        if not isinstance(output, list) or not output:
            continue
        if isinstance(output[0], dict) and "error" in output[0]:
            return args, [], output[0].get("error", "Guardian API error")
        return args, output, None

    return {}, [], "Planner did not return usable tool output."


def valid_date_range(from_date, to_date):
    """Check that planner dates are valid YYYY-MM-DD strings in ascending order."""
    date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(date_pattern, str(from_date)) or not re.match(date_pattern, str(to_date)):
        return False
    return str(from_date) <= str(to_date)


def retrieve_sources(question, articles, k=5):
    """Build an in-memory RAG index and return the top matching Guardian sources."""
    conn = None
    try:
        conn = connect_db(":memory:")
        reset_rag_schema(conn)
        build_index(conn, articles)
        return rag_search(conn, question, k=k)
    finally:
        if conn is not None:
            conn.close()


def planner_role(today):
    """Use the same planner contract as the live Ask The Guardian app."""
    return (
        "You plan Guardian API searches. "
        f"Today's date is {today} (YYYY-MM-DD). "
        "Interpret relative time: 'yesterday' = the previous calendar day only; "
        "'last week' = the 7 days ending yesterday; 'last month' ≈ 30 days ending yesterday. "
        "Map locations to EXACT country names from this list only: "
        f"{', '.join(COUNTRIES)}. "
        "Examples: US / America / USA → United States; UK / Britain → United Kingdom. "
        "You MUST call search_guardian_articles exactly once with "
        "country, from_date, and to_date (YYYY-MM-DD). "
        "Do not put topic keywords (e.g. basketball) in the tool — only country and dates."
    )


def evaluate_case(case, today):
    """Run one evaluation case through planner, tool execution, and RAG retrieval."""
    tool_calls = cloud_agent_run(
        role=planner_role(today),
        task=case["question"],
        tools=[tool_search_guardian_articles],
        output="tools",
        model=OLLAMA_MODEL,
    )
    args, articles, error = extract_articles_and_args(tool_calls)
    hits = retrieve_sources(case["question"], articles) if articles else []

    country_match = args.get("country") == case["expected_country"]
    dates_valid = valid_date_range(args.get("from_date"), args.get("to_date"))
    enough_sources = len(hits) >= case.get("min_sources", 1)
    passed = country_match and dates_valid and enough_sources and error is None
    average_relevance = None
    if hits:
        average_relevance = round(sum(float(h.get("score", 0)) for h in hits) / len(hits), 3)

    return {
        "id": case["id"],
        "question": case["question"],
        "expected_country": case["expected_country"],
        "tool_country": args.get("country", ""),
        "from_date": args.get("from_date", ""),
        "to_date": args.get("to_date", ""),
        "dates_valid": dates_valid,
        "country_match": country_match,
        "articles_fetched": len(articles),
        "sources_used": len(hits),
        "average_relevance": average_relevance,
        "passed": passed,
        "error": error or "",
    }


def write_results(results, out_dir):
    """Write validation results as CSV and JSONL for the assignment evidence."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = out_dir / f"ai_validation_results_{stamp}.csv"
    jsonl_path = out_dir / f"ai_validation_results_{stamp}.jsonl"

    fieldnames = list(results[0].keys()) if results else []
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return csv_path, jsonl_path


# 2. Main Evaluation Workflow #######################

def main():
    """Run the validation set and save quality-control evidence."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-cases", type=int, default=None, help="Limit cases for a quick smoke test.")
    parser.add_argument("--out-dir", default="validation_results", help="Folder for CSV and JSONL outputs.")
    args = parser.parse_args()

    print_rule("📋 AI Quality Validation")
    if not GUARDIAN_API_KEY or not OLLAMA_API_KEY:
        print("❌ Missing GUARDIAN_API_KEY or OLLAMA_API_KEY in the project .env file.")
        sys.exit(1)

    today = datetime.now().strftime("%Y-%m-%d")
    cases = TEST_CASES[:args.max_cases] if args.max_cases else TEST_CASES
    print(f"✅ Loaded {len(cases)} validation cases")
    print(f"☁️ Model: {OLLAMA_MODEL}")

    results = []
    for i, case in enumerate(cases, 1):
        print_rule(f"Step {i} — {case['id']}")
        print(f"Question: {case['question']}")
        try:
            row = evaluate_case(case, today)
        except Exception as e:
            row = {
                "id": case["id"],
                "question": case["question"],
                "expected_country": case["expected_country"],
                "tool_country": "",
                "from_date": "",
                "to_date": "",
                "dates_valid": False,
                "country_match": False,
                "articles_fetched": 0,
                "sources_used": 0,
                "average_relevance": None,
                "passed": False,
                "error": str(e),
            }
        results.append(row)
        status = "✅ PASS" if row["passed"] else "⚠️ REVIEW"
        print(
            f"{status} | country={row['tool_country']} | "
            f"articles={row['articles_fetched']} | sources={row['sources_used']} | "
            f"avg_relevance={row['average_relevance']}"
        )
        if row["error"]:
            print(f"   ⚠️ {row['error']}")

    pass_count = sum(1 for r in results if r["passed"])
    csv_path, jsonl_path = write_results(results, Path(args.out_dir))

    print_rule("📊 Validation Summary")
    print(f"✅ Passed: {pass_count}/{len(results)}")
    print(f"💾 CSV:   {csv_path}")
    print(f"💾 JSONL: {jsonl_path}")


if __name__ == "__main__":
    main()
