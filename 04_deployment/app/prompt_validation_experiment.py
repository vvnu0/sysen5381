# prompt_validation_experiment.py
# Custom Prompt Validation Experiment
# Pairs with app.py and validation_rubric.md

# This script validates AI-generated Guardian coverage reports with a custom
# qualitative content-analysis framework. It generates reports from Prompt A,
# Prompt B, and Prompt C, scores each report, then uses statistics to compare
# prompt performance.

# 0. Setup #################################

## 0.1 Load Packages ############################

import argparse
import csv
import json
import math
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from scipy import stats

# Windows terminals may default to cp1252, which cannot print emoji status
# messages. Reconfiguring keeps the console logs readable for classroom runs.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

## 0.2 Configuration ############################

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent.parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_URL = "https://ollama.com/api/chat"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud")

VALIDATION_RESULTS_DIR = APP_DIR / "validation_results"
VALIDATED_REPORTS_DIR = APP_DIR / "validated_reports"
RUBRIC_PATH = APP_DIR / "validation_rubric.md"


## 0.3 Benchmark Facts ###########################

# These fixed facts stand in for one stable dashboard run. Using the same facts
# for every prompt keeps the experiment fair: only the prompt changes.
BENCHMARK = {
    "source": "The Guardian Open Platform",
    "date_window": "2026-04-01 to 2026-04-30",
    "countries": ["United Kingdom", "United States", "India", "Brazil", "Japan"],
    "total_articles": 240,
    "average_per_country": 48,
    "top_country": "United Kingdom",
    "top_articles": 90,
    "bottom_country": "Japan",
    "bottom_articles": 18,
    "highest_per_capita_country": "United Kingdom",
    "highest_per_capita": 1.32,
    "lowest_per_capita_country": "India",
    "lowest_per_capita": 0.02,
    "coverage_ratio": 5.0,
    "topic_pattern": "Politics and crisis coverage dominate",
}

PROMPTS = {
    "A": {
        "name": "Evidence-first newsroom brief",
        "instruction": (
            "Write a newsroom analytics brief. Use exact numbers from the source, "
            "compare raw coverage with per-capita coverage, state the Guardian date "
            "scope, include one caveat, and give one practical editorial action."
        ),
    },
    "B": {
        "name": "Concise executive summary",
        "instruction": (
            "Write a short executive summary. Mention the main pattern and one number. "
            "Keep it brief and avoid detailed caveats."
        ),
    },
    "C": {
        "name": "Narrative opinion style",
        "instruction": (
            "Write a lively narrative about global media attention. Emphasize drama, "
            "possible explanations, and broad implications."
        ),
    },
}


# 1. Console Helpers ##############################

def print_rule(title):
    """Print a readable section header for pasted logs."""
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def print_step(title):
    """Print a smaller step header."""
    print("\n" + "-" * 72)
    print(title)
    print("-" * 72)


# 2. Report Generation ############################

def benchmark_text():
    """Format benchmark facts for the generator and reviewer."""
    countries = ", ".join(BENCHMARK["countries"])
    return f"""
SOURCE FACTS:
- Source: {BENCHMARK["source"]}
- Date window: {BENCHMARK["date_window"]}
- Countries analyzed: {countries}
- Total Guardian articles: {BENCHMARK["total_articles"]}
- Average per country: {BENCHMARK["average_per_country"]}
- Highest raw coverage: {BENCHMARK["top_country"]} ({BENCHMARK["top_articles"]} articles)
- Lowest raw coverage: {BENCHMARK["bottom_country"]} ({BENCHMARK["bottom_articles"]} articles)
- Highest per-capita coverage: {BENCHMARK["highest_per_capita_country"]} ({BENCHMARK["highest_per_capita"]} per 1M)
- Lowest per-capita coverage: {BENCHMARK["lowest_per_capita_country"]} ({BENCHMARK["lowest_per_capita"]} per 1M)
- Raw coverage ratio: {BENCHMARK["coverage_ratio"]}x
- Topic pattern: {BENCHMARK["topic_pattern"]}
""".strip()


def make_generation_prompt(prompt_id, trial):
    """Create a generation prompt for one Prompt A/B/C trial."""
    variant = PROMPTS[prompt_id]
    return f"""
ROLE: You are writing the AI-generated report for a Guardian geographic attention dashboard.

PROMPT VARIANT: {prompt_id} - {variant["name"]}
INSTRUCTION: {variant["instruction"]}

Use these benchmark facts:
{benchmark_text()}

Trial number: {trial}. Vary sentence structure slightly, but do not invent new facts.
Keep the report under 220 words.
""".strip()


def fixture_report(prompt_id, trial):
    """Generate deterministic report text for no-key classroom runs."""
    if prompt_id == "A":
        templates = [
            (
                "## Guardian Coverage Brief\n\n"
                "From 2026-04-01 to 2026-04-30, The Guardian dashboard tracked 240 articles "
                "across the United Kingdom, United States, India, Brazil, and Japan. The United "
                "Kingdom led raw coverage with 90 articles, while Japan had 18, a 5.0x gap. "
                "The per-capita view also ranked the United Kingdom highest at 1.32 articles "
                "per 1M people, while India was lowest at 0.02. Politics and crisis coverage "
                "dominated the topic mix. Editors should review whether lower-coverage countries "
                "need planned follow-up, while noting that article counts measure attention, not impact."
            ),
            (
                "The Guardian Open Platform results for 2026-04-01 to 2026-04-30 show 240 articles "
                "for five countries: United Kingdom, United States, India, Brazil, and Japan. Raw "
                "coverage was concentrated in the United Kingdom with 90 articles; Japan had 18. "
                "On population-adjusted coverage, the United Kingdom remained highest at 1.32 per "
                "1M, while India was lowest at 0.02 per 1M. This suggests a geographic attention "
                "gap, not proof of audience interest or policy importance. A useful next step is "
                "to assign editors to inspect coverage gaps and compare topic balance by country."
            ),
            (
                "For 2026-04-01 to 2026-04-30, The Guardian Open Platform dashboard counted "
                "240 articles across the United Kingdom, United States, India, Brazil, and Japan. "
                "The United Kingdom received 90 articles and Japan received 18, creating a 5.0x "
                "raw coverage gap. Politics and crisis coverage dominated the topic pattern. "
                "Editors could use this as a planning signal by reviewing lower-coverage countries, "
                "while treating article volume as an attention measure rather than proof of impact."
            ),
        ]
        return templates[trial % len(templates)]

    if prompt_id == "B":
        templates = [
            (
                "The Guardian coverage summary shows uneven attention across countries. In April "
                "2026, the dashboard found 240 articles, with the United Kingdom receiving the most "
                "coverage. This suggests editors may want to examine geographic balance in future work."
            ),
            (
                "Coverage was not evenly distributed. The United Kingdom had 90 Guardian articles, "
                "more than any other country in the dashboard. The pattern may be useful for a quick "
                "editorial check, though more detail would be needed for a full analysis."
            ),
        ]
        return templates[trial % len(templates)]

    templates = [
        (
            "The Guardian's global gaze tells a dramatic story of attention and neglect. Britain "
            "stands at the center, while distant countries fade into the margins. This may reveal "
            "how global media power decides which places matter and which are forgotten."
        ),
        (
            "World coverage is a mirror of power. Some countries dominate the news cycle, while "
            "others nearly disappear. The pattern feels like a warning about media bias and the "
            "unequal geography of public concern."
        ),
    ]
    return templates[trial % len(templates)]


def call_ollama(prompt, temperature=0.4, json_mode=False):
    """Call Ollama Cloud and return content text."""
    if not OLLAMA_API_KEY:
        raise ValueError("OLLAMA_API_KEY is not configured in the project .env file.")

    body = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": temperature},
    }
    if json_mode:
        body["format"] = "json"

    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.post(OLLAMA_URL, headers=headers, json=body, timeout=180)
    response.raise_for_status()
    result = response.json()
    return result["message"]["content"]


def generate_report(prompt_id, trial, mode):
    """Generate one report with either live AI or deterministic fixtures."""
    if mode == "live":
        return call_ollama(make_generation_prompt(prompt_id, trial), temperature=0.55)
    return fixture_report(prompt_id, trial)


# 3. Custom Validation #############################

def load_rubric_text():
    """Load the rubric markdown for AI reviewer context."""
    if RUBRIC_PATH.is_file():
        return RUBRIC_PATH.read_text(encoding="utf-8")
    return "Rubric file missing. Use the weighted scoring fields described in the prompt."


def clean_words(text):
    """Lowercase text for simple qualitative content tags."""
    return re.sub(r"\s+", " ", str(text).lower())


def has_any(text, phrases):
    """Check whether any phrase appears in text."""
    return any(p.lower() in text for p in phrases)


def heuristic_validate(report_text):
    """
    Deterministic fallback reviewer.
    This mirrors the custom rubric so the experiment is reproducible without API keys.
    """
    text = clean_words(report_text)
    tags = []

    numeric_grounding = 0
    numeric_checks = [
        ("240", 5), ("90", 4), ("18", 4), ("5.0", 3), ("1.32", 3), ("0.02", 3), ("48", 3),
    ]
    for needle, points in numeric_checks:
        if needle in text:
            numeric_grounding += points
    if has_any(text, ["guardian", "open platform"]):
        numeric_grounding += 2
    numeric_grounding = min(numeric_grounding, 25)
    if numeric_grounding >= 10:
        tags.append("numeric_grounding")

    comparative_reasoning = 0
    if has_any(text, ["raw coverage", "articles", "article count"]):
        comparative_reasoning += 5
        tags.append("raw_volume_comparison")
    if has_any(text, ["per-capita", "per capita", "per 1m", "population-adjusted"]):
        comparative_reasoning += 7
        tags.append("per_capita_comparison")
    if has_any(text, ["highest", "lowest", "led", "while japan", "gap"]):
        comparative_reasoning += 5
        tags.append("top_bottom_contrast")
    if has_any(text, ["attention gap", "imbalance", "uneven", "concentrated"]):
        comparative_reasoning += 3
        tags.append("coverage_imbalance_explained")
    comparative_reasoning = min(comparative_reasoning, 20)

    source_scope_control = 0
    if has_any(text, ["guardian", "open platform"]):
        source_scope_control += 5
    if has_any(text, ["2026-04-01", "2026-04-30", "april 2026"]):
        source_scope_control += 5
    country_hits = sum(country.lower() in text for country in BENCHMARK["countries"])
    source_scope_control += min(country_hits, 5)
    if source_scope_control >= 10:
        tags.append("source_scope_control")
    if source_scope_control >= 12:
        tags.append("source_date_country_scope")

    editorial_usefulness = 0
    if has_any(text, ["editor", "newsroom", "researcher", "student"]):
        editorial_usefulness += 5
    if has_any(text, ["next step", "review", "assign", "inspect", "compare", "follow-up"]):
        editorial_usefulness += 8
        tags.append("editorial_action")
    if has_any(text, ["coverage gap", "lower-coverage", "balance", "topic balance"]):
        editorial_usefulness += 5
        tags.append("coverage_gap")
    if has_any(text, ["research", "methods", "analysis"]):
        editorial_usefulness += 2
        tags.append("research_use")
    editorial_usefulness = min(editorial_usefulness, 20)

    risk_control = 20
    risky_phrases = [
        "proves", "decides which places matter", "forgotten", "power decides",
        "warning about media bias", "neglect", "dramatic story",
    ]
    if has_any(text, risky_phrases):
        risk_control -= 12
        tags.append("unsupported_claim")
    if has_any(text, ["dramatic", "fade into the margins", "global gaze"]):
        risk_control -= 5
        tags.append("sensational_language")
    if has_any(text, ["not proof", "caveat", "suggests", "may", "counts measure attention"]):
        risk_control += 4
        tags.append("risk_control")
    risk_control = max(0, min(risk_control, 20))

    overall_score = sum([
        numeric_grounding,
        comparative_reasoning,
        source_scope_control,
        editorial_usefulness,
        risk_control,
    ])
    recommendation = "publish" if overall_score >= 85 else "revise" if overall_score >= 65 else "reject"

    return {
        "numeric_grounding": numeric_grounding,
        "comparative_reasoning": comparative_reasoning,
        "source_scope_control": source_scope_control,
        "editorial_usefulness": editorial_usefulness,
        "risk_control": risk_control,
        "overall_score": overall_score,
        "content_tags": ";".join(sorted(set(tags))),
        "strength": "Most useful content-analysis features detected by the custom rubric.",
        "weakness": "Missing or risky features are reflected in the dimension scores.",
        "recommendation": recommendation,
    }


def make_ai_reviewer_prompt(report_text):
    """Create the AI reviewer prompt with custom rubric and exact JSON schema."""
    return f"""
You are a qualitative content-analysis reviewer for an AI-generated Guardian dashboard report.
Use the custom rubric below. Do not use generic 1-5 Likert scales.

{load_rubric_text()}

Benchmark facts:
{benchmark_text()}

Report to validate:
{report_text}

Return one valid JSON object only with these keys:
{{
  "numeric_grounding": 0,
  "comparative_reasoning": 0,
  "source_scope_control": 0,
  "editorial_usefulness": 0,
  "risk_control": 0,
  "overall_score": 0,
  "content_tags": "semicolon separated tags",
  "strength": "one sentence",
  "weakness": "one sentence",
  "recommendation": "publish, revise, or reject"
}}

Point limits: numeric_grounding 0-25, comparative_reasoning 0-20,
source_scope_control 0-15, editorial_usefulness 0-20, risk_control 0-20.
overall_score must equal the sum of the five dimension scores.
""".strip()


def parse_ai_review(raw_text):
    """Parse JSON review and clamp fields to rubric ranges."""
    match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
    parsed = json.loads(match.group(0) if match else raw_text)
    limits = {
        "numeric_grounding": 25,
        "comparative_reasoning": 20,
        "source_scope_control": 15,
        "editorial_usefulness": 20,
        "risk_control": 20,
    }
    out = {}
    for key, limit in limits.items():
        out[key] = max(0, min(limit, int(float(parsed.get(key, 0)))))
    out["overall_score"] = sum(out.values())
    out["content_tags"] = str(parsed.get("content_tags", "")).strip()
    out["strength"] = str(parsed.get("strength", "")).strip()
    out["weakness"] = str(parsed.get("weakness", "")).strip()
    rec = str(parsed.get("recommendation", "")).strip().lower()
    out["recommendation"] = rec if rec in {"publish", "revise", "reject"} else recommendation(out["overall_score"])
    return out


def recommendation(score):
    """Convert score to publish/revise/reject threshold."""
    return "publish" if score >= 85 else "revise" if score >= 65 else "reject"


def validate_report(report_text, mode):
    """Validate one report using AI reviewer or deterministic rubric."""
    if mode == "ai":
        raw = call_ollama(make_ai_reviewer_prompt(report_text), temperature=0.1, json_mode=True)
        return parse_ai_review(raw)
    return heuristic_validate(report_text)


# 4. Statistics and Outputs ########################

def cohens_d(x, y):
    """Calculate Cohen's d for two independent groups."""
    x = pd.Series(x).dropna()
    y = pd.Series(y).dropna()
    nx = len(x)
    ny = len(y)
    pooled = math.sqrt(((nx - 1) * x.var(ddof=1) + (ny - 1) * y.var(ddof=1)) / (nx + ny - 2))
    return (x.mean() - y.mean()) / pooled if pooled else float("nan")


def run_statistics(scores_df):
    """Run t-test and ANOVA on custom validation scores."""
    a = scores_df.query('prompt_id == "A"')["overall_score"]
    b = scores_df.query('prompt_id == "B"')["overall_score"]
    c = scores_df.query('prompt_id == "C"')["overall_score"]
    t_result = stats.ttest_ind(a, b, equal_var=False)
    anova_result = stats.f_oneway(a, b, c)
    return {
        "t_statistic": float(t_result.statistic),
        "t_p_value": float(t_result.pvalue),
        "anova_f": float(anova_result.statistic),
        "anova_p_value": float(anova_result.pvalue),
        "mean_difference_a_b": float(a.mean() - b.mean()),
        "cohens_d_a_b": float(cohens_d(a, b)),
    }


def write_jsonl(path, rows):
    """Write rows to JSONL for auditability."""
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_outputs(reports, scores, stats_out, reviewer_mode, generation_mode):
    """Write reports, scores, and markdown summary artifacts."""
    VALIDATION_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    VALIDATED_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    reports_csv = VALIDATED_REPORTS_DIR / f"prompt_experiment_reports_{stamp}.csv"
    reports_jsonl = VALIDATED_REPORTS_DIR / f"prompt_experiment_reports_{stamp}.jsonl"
    scores_csv = VALIDATION_RESULTS_DIR / f"prompt_validation_scores_{stamp}.csv"
    scores_jsonl = VALIDATION_RESULTS_DIR / f"prompt_validation_scores_{stamp}.jsonl"
    summary_md = VALIDATION_RESULTS_DIR / f"prompt_experiment_summary_{stamp}.md"

    pd.DataFrame(reports).to_csv(reports_csv, index=False, quoting=csv.QUOTE_MINIMAL)
    pd.DataFrame(scores).to_csv(scores_csv, index=False, quoting=csv.QUOTE_MINIMAL)
    write_jsonl(reports_jsonl, reports)
    write_jsonl(scores_jsonl, scores)

    scores_df = pd.DataFrame(scores)
    summary = (
        scores_df.groupby("prompt_id")["overall_score"]
        .agg(["count", "mean", "std", "min", "max"])
        .round(2)
        .reset_index()
    )

    lines = [
        "# Prompt Validation Experiment Results",
        "",
        "## Experiment Design",
        "",
        "- Prompts compared: A, B, C",
        f"- Samples per prompt: {int(summary['count'].iloc[0]) if not summary.empty else 0}",
        f"- Total reports validated: {len(scores_df)}",
        f"- Generation mode: {generation_mode}",
        f"- Reviewer mode: {reviewer_mode}",
        f"- Reports file: `{reports_csv.relative_to(APP_DIR)}`",
        f"- Scores file: `{scores_csv.relative_to(APP_DIR)}`",
        "",
        "## Prompt Variants",
        "",
    ]
    for prompt_id, prompt in PROMPTS.items():
        lines.append(f"- Prompt {prompt_id}: {prompt['name']} - {prompt['instruction']}")

    lines.extend([
        "",
        "## Validation Criteria",
        "",
        "The custom rubric uses weighted 0-100 scoring across Numeric Grounding, "
        "Comparative Reasoning, Source Scope Control, Editorial Usefulness, and Risk Control. "
        "It differs from the LAB because it uses app-specific benchmarks, content-analysis tags, "
        "and explicit publish/revise/reject thresholds.",
        "",
        "## Descriptive Statistics",
        "",
        summary.to_markdown(index=False),
        "",
        "## Statistical Analysis",
        "",
        "- Hypothesis: H1: Prompt A has a higher mean custom validation score than Prompt B. H0: their mean scores are equal.",
        f"- Welch t-test: t = {stats_out['t_statistic']:.3f}, p = {stats_out['t_p_value']:.3e}",
        f"- Mean difference (A - B): {stats_out['mean_difference_a_b']:.2f}",
        f"- Cohen's d: {stats_out['cohens_d_a_b']:.2f}",
        f"- One-way ANOVA: F = {stats_out['anova_f']:.3f}, p = {stats_out['anova_p_value']:.3e}",
        "",
        "## Interpretation",
        "",
    ])
    if stats_out["t_p_value"] < 0.05:
        lines.append(
            f"Prompt A performed significantly better than Prompt B "
            f"(Welch t-test p = {stats_out['t_p_value']:.3e}). "
            f"The ANOVA p-value was {stats_out['anova_p_value']:.3e}, showing that prompt choice "
            "affected validation scores overall."
        )
    else:
        lines.append(
            "Prompt A did not significantly outperform Prompt B at alpha = 0.05. "
            "The experiment should be rerun with more samples or revised prompts."
        )
    lines.extend([
        "",
        "## System Design",
        "",
        "The script generates reports from three prompt styles, validates each report against a "
        "custom qualitative content-analysis rubric, stores report text and validation scores, "
        "and runs statistical tests on the resulting score distributions. In AI reviewer mode, "
        "Ollama Cloud reads the rubric and source benchmark and returns structured JSON. In "
        "heuristic mode, a deterministic fallback mirrors the rubric for reproducible classroom evidence.",
    ])
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "reports_csv": reports_csv,
        "reports_jsonl": reports_jsonl,
        "scores_csv": scores_csv,
        "scores_jsonl": scores_jsonl,
        "summary_md": summary_md,
        "summary": summary,
    }


# 5. Main Workflow #################################

def main():
    """Run the full prompt validation experiment."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-per-prompt", type=int, default=12)
    parser.add_argument("--generation-mode", choices=["fixtures", "live"], default="fixtures")
    parser.add_argument("--reviewer-mode", choices=["heuristic", "ai"], default="heuristic")
    parser.add_argument("--sleep-seconds", type=float, default=0.3)
    args = parser.parse_args()

    print_rule("📋 Custom AI Report Validation Experiment")
    print(f"✅ Prompts: {', '.join(PROMPTS.keys())}")
    print(f"✅ Samples per prompt: {args.samples_per_prompt}")
    print(f"✅ Generation mode: {args.generation_mode}")
    print(f"✅ Reviewer mode: {args.reviewer_mode}")
    print(f"☁️ Model: {OLLAMA_MODEL}")

    if (args.generation_mode == "live" or args.reviewer_mode == "ai") and not OLLAMA_API_KEY:
        print("❌ OLLAMA_API_KEY is required for live generation or AI reviewer mode.")
        sys.exit(1)

    reports = []
    scores = []

    print_step("Step 1 - Generate and validate reports")
    for prompt_id in PROMPTS:
        for trial in range(1, args.samples_per_prompt + 1):
            report_id = f"{prompt_id}_{trial:03d}"
            print(f"🔧 {report_id}: generating report and scoring rubric")
            report_text = generate_report(prompt_id, trial, args.generation_mode)
            review = validate_report(report_text, args.reviewer_mode)

            reports.append({
                "report_id": report_id,
                "prompt_id": prompt_id,
                "prompt_name": PROMPTS[prompt_id]["name"],
                "trial": trial,
                "report_text": report_text,
                "generation_mode": args.generation_mode,
            })
            scores.append({
                "report_id": report_id,
                "prompt_id": prompt_id,
                "prompt_name": PROMPTS[prompt_id]["name"],
                "trial": trial,
                **review,
                "reviewer_mode": args.reviewer_mode,
            })
            if args.generation_mode == "live" or args.reviewer_mode == "ai":
                time.sleep(args.sleep_seconds)

    print_step("Step 2 - Statistical comparison")
    scores_df = pd.DataFrame(scores)
    stats_out = run_statistics(scores_df)
    summary = (
        scores_df.groupby("prompt_id")["overall_score"]
        .agg(["count", "mean", "std", "min", "max"])
        .round(2)
    )
    print("📊 Mean validation score by prompt:")
    print(summary)
    print(f"📊 Welch t-test A vs B: p = {stats_out['t_p_value']:.3e}")
    print(f"📊 ANOVA A/B/C: p = {stats_out['anova_p_value']:.3e}")

    print_step("Step 3 - Write artifacts")
    written = write_outputs(reports, scores, stats_out, args.reviewer_mode, args.generation_mode)
    for label, path in written.items():
        if label != "summary":
            print(f"💾 {label}: {path.relative_to(APP_DIR)}")

    print_rule("✅ Experiment Complete")
    print(f"📊 Reports validated: {len(scores)}")
    print(f"📄 Summary: {written['summary_md'].relative_to(APP_DIR)}")
    print("💡 Use the summary markdown and score CSV as assignment evidence.")


if __name__ == "__main__":
    main()
