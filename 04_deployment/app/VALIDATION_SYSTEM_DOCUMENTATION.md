# AI Report Validation System Documentation

This document describes the custom validation system for the Geographic Attention Reporter app. The system evaluates AI-generated Guardian coverage reports, compares Prompt A/B/C, and produces statistical evidence showing which prompt performs best.

## 1. Validation Criteria Table

The validator uses a custom 0-100 weighted rubric tailored to this app's Guardian coverage report use case.

| Dimension | Description | Scale / measurement method | Benchmark |
|---|---|---|---|
| Numeric Grounding | Checks whether report numbers match the benchmark dashboard facts: source, date window, countries, article totals, raw counts, per-capita values, and coverage ratio. | 0-25 points. Credit is awarded for correct benchmark facts and reduced when numbers are missing or unsupported. | 20+ points and no major contradiction. |
| Comparative Reasoning | Checks whether the report compares raw article volume, per-capita coverage, top/bottom countries, and geographic imbalance. | 0-20 points based on content-analysis tags such as `raw_volume_comparison`, `per_capita_comparison`, and `top_bottom_contrast`. | 15+ points and at least one raw-vs-per-capita comparison. |
| Source Scope Control | Checks whether the report clearly names The Guardian, the date window, and the country scope. | 0-15 points based on explicit source, date, and country mentions. | 12+ points and explicit Guardian mention. |
| Editorial Usefulness | Checks whether the report gives a useful next step for editors, researchers, or students. | 0-20 points based on tags such as `editorial_action`, `coverage_gap`, and `research_use`. | 15+ points and at least one concrete action. |
| Risk Control | Checks whether the report avoids unsupported causal claims, sensational language, and overgeneralization. | 0-20 points. Starts from a risk-control score and subtracts for unsupported or dramatic claims; caveats add credit. | 16+ points and no severe unsupported claim. |

### Difference From The LAB Likert Scales

The `09_text_analysis` LAB uses general 1-5 Likert ratings for broad qualities such as accuracy, formality, faithfulness, clarity, succinctness, and relevance. This app's validator is different because it uses:

- **App-specific benchmarks:** Guardian source, fixed date window, country list, article totals, raw/per-capita counts, and coverage ratio.
- **Weighted custom scale:** 0-100 total score instead of generic 1-5 ratings.
- **Qualitative content-analysis tags:** explicit tags such as `per_capita_comparison`, `editorial_action`, `coverage_gap`, and `unsupported_claim`.
- **Decision thresholds:** `publish`, `revise`, or `reject` based on the final score.

## 2. Experimental Design

The experiment compares three report-generation prompts against the same benchmark facts. Keeping the benchmark fixed means the prompt design is the main thing being tested.

| Prompt | Name | Design |
|---|---|---|
| Prompt A | Evidence-first newsroom brief | Requires exact numbers, source/date scope, raw-vs-per-capita comparison, caveat, and editorial action. |
| Prompt B | Concise executive summary | Asks for a short summary with the main pattern and one number, but fewer details. |
| Prompt C | Narrative opinion style | Encourages broader interpretation and dramatic language, which should be riskier for this app. |

The latest reproducible run collected:

- **12 generated reports per prompt**
- **3 prompts**
- **36 total reports validated**
- **36 validation score rows**

Reports are generated from fixture text by default so the class can reproduce the experiment without spending API credits. The script also supports live Ollama Cloud generation.

## 3. Statistical Analysis

The main hypothesis is:

- **H1:** Prompt A has a higher mean validation score than Prompt B because it is aligned with the custom rubric.
- **H0:** Prompt A and Prompt B have equal mean validation scores.

The experiment uses:

- **Welch t-test** for Prompt A vs Prompt B because it compares two independent groups and does not require equal variances.
- **One-way ANOVA** for Prompt A/B/C because it tests whether prompt choice affects scores across all three prompts.
- **Cohen's d** for practical effect size between Prompt A and Prompt B.

Latest reproducible run:

| Prompt | n | Mean score | Std. dev | Min | Max |
|---|---:|---:|---:|---:|---:|
| A | 12 | 89.67 | 6.40 | 81 | 94 |
| B | 12 | 50.00 | 6.27 | 44 | 56 |
| C | 12 | 11.00 | 3.13 | 8 | 14 |

Test results:

- **Welch t-test, Prompt A vs Prompt B:** `p = 3.153e-13`
- **Mean difference, A - B:** `39.67`
- **Cohen's d:** `6.26`
- **One-way ANOVA, A/B/C:** `p = 6.972e-27`

Interpretation: Prompt A performs significantly better than Prompt B, and prompt choice significantly affects validation scores overall. This supports using an evidence-first prompt for this app's AI-generated Guardian coverage report.

## 4. System Design

The validation system is implemented in [`prompt_validation_experiment.py`](prompt_validation_experiment.py).

The workflow has four stages:

1. **Generate reports:** The script creates reports using Prompt A, Prompt B, and Prompt C. It can use deterministic fixtures or live Ollama Cloud calls.
2. **Validate reports:** Each report is scored against [`validation_rubric.md`](validation_rubric.md).
3. **Save evidence:** Generated reports are saved separately from validation scores so the scoring can be audited.
4. **Run statistics:** The script runs Welch t-test and ANOVA on the score distributions.

### AI Reviewer's Role

In AI reviewer mode, Ollama Cloud acts as the qualitative content-analysis reviewer. It receives:

- The custom rubric.
- The benchmark facts.
- The generated report text.
- A strict JSON schema for the score output.

The reviewer returns structured scores for each dimension, content-analysis tags, a strength, a weakness, and a recommendation (`publish`, `revise`, or `reject`).

For no-key classroom demos, the script also includes a deterministic `heuristic` reviewer that mirrors the same rubric. This is useful for reproducible local testing, but the AI-reviewer mode is the version that demonstrates AI-as-reviewer qualitative content analysis.

## 5. Technical Details

### API Keys

- `OLLAMA_API_KEY` is required for:
  - `--generation-mode live`
  - `--reviewer-mode ai`
- The key should live in the repo-root `.env` file:

```text
OLLAMA_API_KEY=your_key_here
```

No API key is needed for:

```powershell
python prompt_validation_experiment.py --samples-per-prompt 12 --generation-mode fixtures --reviewer-mode heuristic
```

### Packages

Dependencies are listed in [`requirements.txt`](requirements.txt). The validation experiment uses:

- `pandas`
- `requests`
- `python-dotenv`
- `scipy`

The wider app also uses Shiny, Plotly, sentence-transformers, and sqlite-vec.

### File Structure

```text
04_deployment/app/
  app.py
  prompt_validation_experiment.py
  validation_rubric.md
  VALIDATION_SYSTEM_DOCUMENTATION.md
  requirements.txt
  validated_reports/
    prompt_experiment_reports_20260505_005644.csv
    prompt_experiment_reports_20260505_005644.jsonl
  validation_results/
    prompt_experiment_summary_20260505_005644.md
    prompt_validation_scores_20260505_005644.csv
    prompt_validation_scores_20260505_005644.jsonl
```

## 6. Usage Instructions

From the repository root:

```powershell
cd 04_deployment/app
pip install -r requirements.txt
```

Run a reproducible local experiment with no API key:

```powershell
python prompt_validation_experiment.py --samples-per-prompt 12 --generation-mode fixtures --reviewer-mode heuristic
```

Run the qualitative content-analysis reviewer with AI:

```powershell
python prompt_validation_experiment.py --samples-per-prompt 12 --generation-mode fixtures --reviewer-mode ai
```

Generate both reports and validation scores with live Ollama Cloud:

```powershell
python prompt_validation_experiment.py --samples-per-prompt 12 --generation-mode live --reviewer-mode ai
```

After running, check:

- `validated_reports/` for generated report text.
- `validation_results/` for validation scores and the statistical summary.

## Repository Links

- **Validation system script:** [`prompt_validation_experiment.py`](prompt_validation_experiment.py)
- **Validation criteria / rubric:** [`validation_rubric.md`](validation_rubric.md)
- **Example statistical summary:** [`validation_results/prompt_experiment_summary_20260505_005644.md`](validation_results/prompt_experiment_summary_20260505_005644.md)
- **Example validation score data:** [`validation_results/prompt_validation_scores_20260505_005644.csv`](validation_results/prompt_validation_scores_20260505_005644.csv)
- **Reports validated:** [`validated_reports/prompt_experiment_reports_20260505_005644.csv`](validated_reports/prompt_experiment_reports_20260505_005644.csv)
- **App source using the AI report workflow:** [`app.py`](app.py)
- **Dependencies:** [`requirements.txt`](requirements.txt)

## Anything Still Needed?

The validation system is implemented and runs locally. The only remaining step for strongest assignment evidence is to set `OLLAMA_API_KEY` and rerun:

```powershell
python prompt_validation_experiment.py --samples-per-prompt 12 --generation-mode fixtures --reviewer-mode ai
```

That produces the same type of CSV/JSONL/Markdown evidence, but with the AI reviewer directly performing the qualitative content analysis.
