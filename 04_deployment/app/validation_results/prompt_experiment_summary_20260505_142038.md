# Prompt Validation Experiment Results

## Experiment Design

- Prompts compared: A, B, C
- Date window: 2026-03-01 to 2026-05-05
- Samples per prompt: 50
- Total reports validated: 150
- Generation mode: fixtures
- Reviewer mode: heuristic
- Reports file: `validated_reports\prompt_experiment_reports_20260505_142038.csv`
- Scores file: `validation_results\prompt_validation_scores_20260505_142038.csv`
- Summary statistics file: `validation_results\prompt_score_summary_20260505_142038.csv`
- Score comparison chart: `validation_results\prompt_score_boxplot_20260505_142038.html`
- Example evaluated report: `validation_results\example_evaluated_report_20260505_142038.md`

## Prompt Variants

- Prompt A: Evidence-first newsroom brief - Write a newsroom analytics brief. Use exact numbers from the source, compare raw coverage with per-capita coverage, state the Guardian date scope, include one caveat, and give one practical editorial action.
- Prompt B: Concise executive summary - Write a short executive summary. Mention the main pattern and one number. Keep it brief and avoid detailed caveats.
- Prompt C: Narrative opinion style - Write a lively narrative about global media attention. Emphasize drama, possible explanations, and broad implications.

## Validation Criteria

The custom rubric uses weighted 0-100 scoring across Numeric Grounding, Comparative Reasoning, Source Scope Control, Editorial Usefulness, and Risk Control. It differs from the LAB because it uses app-specific benchmarks, content-analysis tags, and explicit publish/revise/reject thresholds.

## Descriptive Statistics

| prompt_id   |   count |   mean |   std |   min |   max |
|:------------|--------:|-------:|------:|------:|------:|
| A           |      50 |  89.58 |  6.22 |    81 |    94 |
| B           |      50 |  50    |  6.06 |    44 |    56 |
| C           |      50 |  11    |  3.03 |     8 |    14 |

## Statistical Analysis

- Hypothesis: H1: Prompt A has a higher mean custom validation score than Prompt B. H0: their mean scores are equal.
- Welch t-test: t = 32.224, p = 6.248e-54
- Mean difference (A - B): 39.58
- Cohen's d: 6.44
- One-way ANOVA: F = 2736.599, p = 4.910e-117

## Interpretation

Prompt A performed significantly better than Prompt B (Welch t-test p = 6.248e-54). The ANOVA p-value was 4.910e-117, showing that prompt choice affected validation scores overall.

## System Design

The script generates reports from three prompt styles, validates each report against a custom qualitative content-analysis rubric, stores report text and validation scores, and runs statistical tests on the resulting score distributions. In AI reviewer mode, Ollama Cloud reads the rubric and source benchmark and returns structured JSON. In heuristic mode, a deterministic fallback mirrors the rubric for reproducible classroom evidence.
