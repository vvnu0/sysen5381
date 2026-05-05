# AI Report Validation System Documentation

This document describes the custom validation system for the Geographic Attention Reporter app. The system evaluates AI-generated Guardian coverage reports, compares Prompt A/B/C, and produces statistical evidence showing which prompt performs best.

**This documentation is based on the latest validation run for March 1, 2026 to May 5, 2026.** The latest run used `--from-date 2026-03-01`, `--to-date 2026-05-05`, and `--samples-per-prompt 50`.

## 1. Validation Criteria Table

The validator uses a custom 0-100 weighted rubric tailored to this app's Guardian coverage report use case.


| Dimension             | Description                                                                                                                                                                    | Scale / measurement method                                                                                                      | Benchmark                                                 |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Numeric Grounding     | Checks whether report numbers match the benchmark dashboard facts: source, selected date window, countries, article totals, raw counts, per-capita values, and coverage ratio. | 0-25 points. Credit is awarded for correct benchmark facts and reduced when numbers are missing or unsupported.                 | 20+ points and no major contradiction.                    |
| Comparative Reasoning | Checks whether the report compares raw article volume, per-capita coverage, top/bottom countries, and geographic imbalance.                                                    | 0-20 points based on content-analysis tags such as `raw_volume_comparison`, `per_capita_comparison`, and `top_bottom_contrast`. | 15+ points and at least one raw-vs-per-capita comparison. |
| Source Scope Control  | Checks whether the report clearly names The Guardian, the selected date window, and the country scope.                                                                         | 0-15 points based on explicit source, date, and country mentions.                                                               | 12+ points and explicit Guardian mention.                 |
| Editorial Usefulness  | Checks whether the report gives a useful next step for editors, researchers, or students.                                                                                      | 0-20 points based on tags such as `editorial_action`, `coverage_gap`, and `research_use`.                                       | 15+ points and at least one concrete action.              |
| Risk Control          | Checks whether the report avoids unsupported causal claims, sensational language, and overgeneralization.                                                                      | 0-20 points. Starts from a risk-control score and subtracts for unsupported or dramatic claims; caveats add credit.             | 16+ points and no severe unsupported claim.               |


### Difference From The LAB Likert Scales

The `09_text_analysis` LAB uses general 1-5 Likert ratings for broad qualities such as accuracy, formality, faithfulness, clarity, succinctness, and relevance. This app's validator is different because it uses:

- **App-specific benchmarks:** Guardian source, selected date window, country list, article totals, raw/per-capita counts, and coverage ratio.
- **Weighted custom scale:** 0-100 total score instead of generic 1-5 ratings.
- **Qualitative content-analysis tags:** explicit tags such as `per_capita_comparison`, `editorial_action`, `coverage_gap`, and `unsupported_claim`.
- **Decision thresholds:** `publish`, `revise`, or `reject` based on the final score.

## 2. Experimental Design

The experiment compares three report-generation prompts against the same benchmark facts and the same selected date window. Keeping the benchmark fixed means the prompt design is the main thing being tested.


| Prompt   | Name                          | Design                                                                                                 |
| -------- | ----------------------------- | ------------------------------------------------------------------------------------------------------ |
| Prompt A | Evidence-first newsroom brief | Requires exact numbers, source/date scope, raw-vs-per-capita comparison, caveat, and editorial action. |
| Prompt B | Concise executive summary     | Asks for a short summary with the main pattern and one number, but fewer details.                      |
| Prompt C | Narrative opinion style       | Encourages broader interpretation and dramatic language, which should be riskier for this app.         |


**Latest run date window: March 1, 2026 to May 5, 2026.**

The latest run collected:

- **50 generated reports per prompt**
- **3 prompts**
- **150 total reports validated**
- **150 validation score rows**

Reports were generated from fixture text for reproducibility. The script also supports live Ollama Cloud generation and AI reviewer mode when `OLLAMA_API_KEY` is configured.

## 3. Statistical Analysis

The main hypothesis is:

- **H1:** Prompt A has a higher mean validation score than Prompt B because it is aligned with the custom rubric.
- **H0:** Prompt A and Prompt B have equal mean validation scores.

The experiment uses:

- **Welch t-test** for Prompt A vs Prompt B because it compares two independent groups and does not require equal variances.
- **One-way ANOVA** for Prompt A/B/C because it tests whether prompt choice affects scores across all three prompts.
- **Cohen's d** for practical effect size between Prompt A and Prompt B.

**Latest results for March 1, 2026 to May 5, 2026:**


| Prompt | n   | Mean score | Std. dev | Min | Max |
| ------ | --- | ---------- | -------- | --- | --- |
| A      | 50  | 89.58      | 6.22     | 81  | 94  |
| B      | 50  | 50.00      | 6.06     | 44  | 56  |
| C      | 50  | 11.00      | 3.03     | 8   | 14  |


Test results:

- **Welch t-test, Prompt A vs Prompt B:** `t = 32.224`, `p = 6.248e-54`
- **Mean difference, A - B:** `39.58`
- **Cohen's d:** `6.44`
- **One-way ANOVA, A/B/C:** `F = 2736.599`, `p = 4.910e-117`

Interpretation: Prompt A performed significantly better than Prompt B, and the ANOVA shows that prompt choice significantly affected validation scores overall. This supports using an evidence-first prompt for this app's AI-generated Guardian coverage report.

## 4. System Design

The validation system is implemented in `[prompt_validation_experiment.py](prompt_validation_experiment.py)`.

The workflow has four stages:

1. **Generate reports:** The script creates reports using Prompt A, Prompt B, and Prompt C. It can use deterministic fixtures or live Ollama Cloud calls.
2. **Validate reports:** Each report is scored against `[validation_rubric.md](validation_rubric.md)`.
3. **Save evidence:** Generated reports are saved separately from validation scores so the scoring can be audited.
4. **Run statistics:** The script runs Welch t-test and ANOVA on the score distributions, then writes Markdown, CSV, JSONL, and HTML chart outputs.

### AI Reviewer's Role

In AI reviewer mode, Ollama Cloud acts as the qualitative content-analysis reviewer. It receives:

- The custom rubric.
- The selected date window and benchmark facts.
- The generated report text.
- A strict JSON schema for the score output.

The reviewer returns structured scores for each dimension, content-analysis tags, a strength, a weakness, and a recommendation: `publish`, `revise`, or `reject`.

The script also has a deterministic heuristic reviewer for local testing. The heuristic reviewer mirrors the same rubric and is useful for reproducible runs without an API key, while AI reviewer mode demonstrates AI-as-reviewer qualitative content analysis.

## 5. Technical Details

### API Keys

- `OLLAMA_API_KEY` is required for:
  - `--generation-mode live`
  - `--reviewer-mode ai`
- The key should live in the repo-root `.env` file:

```text
OLLAMA_API_KEY=your_key_here
```

No API key is needed for a reproducible local run:

```powershell
python prompt_validation_experiment.py --from-date 2026-03-01 --to-date 2026-05-05 --samples-per-prompt 50 --generation-mode fixtures --reviewer-mode heuristic
```

### Packages

Dependencies are listed in `[requirements.txt](requirements.txt)`. The validation experiment uses:

- `pandas`
- `plotly`
- `requests`
- `python-dotenv`
- `scipy`

The wider app also uses Shiny, sentence-transformers, and sqlite-vec.

### File Structure

```text
04_deployment/app/
  app.py
  prompt_validation_experiment.py
  validation_rubric.md
  VALIDATION_SYSTEM_DOCUMENTATION.md
  requirements.txt
  validated_reports/
    prompt_experiment_reports_20260505_142038.csv
    prompt_experiment_reports_20260505_142038.jsonl
  validation_results/
    prompt_experiment_summary_20260505_142038.md
    prompt_validation_scores_20260505_142038.csv
    prompt_validation_scores_20260505_142038.jsonl
    prompt_score_summary_20260505_142038.csv
    prompt_score_boxplot_20260505_142038.html
    example_evaluated_report_20260505_142038.md
```

## 6. Usage Instructions

From the repository root:

```powershell
cd 04_deployment/app
pip install -r requirements.txt
```

Run the latest reproducible experiment for March 1, 2026 to May 5, 2026 with no API key:

```powershell
python prompt_validation_experiment.py --from-date 2026-03-01 --to-date 2026-05-05 --samples-per-prompt 50 --generation-mode fixtures --reviewer-mode heuristic
```

Run the same date window with the AI reviewer:

```powershell
python prompt_validation_experiment.py --from-date 2026-03-01 --to-date 2026-05-05 --samples-per-prompt 50 --generation-mode fixtures --reviewer-mode ai
```

Generate both reports and validation scores with live Ollama Cloud:

```powershell
python prompt_validation_experiment.py --from-date 2026-03-01 --to-date 2026-05-05 --samples-per-prompt 50 --generation-mode live --reviewer-mode ai
```

After running, check:

- `validated_reports/` for generated report text.
- `validation_results/` for validation scores, the statistical summary, the one-report example, and the prompt comparison chart.

