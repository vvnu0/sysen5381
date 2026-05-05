# Prompt Validation Experiment Results

## Experiment Design

- Prompts compared: A, B, C
- Samples per prompt: 12
- Total reports validated: 36
- Generation mode: fixtures
- Reviewer mode: heuristic
- Reports file: `validated_reports\prompt_experiment_reports_20260505_135637.csv`
- Scores file: `validation_results\prompt_validation_scores_20260505_135637.csv`

## Prompt Variants

- Prompt A: Evidence-first newsroom brief - Write a newsroom analytics brief. Use exact numbers from the source, compare raw coverage with per-capita coverage, state the Guardian date scope, include one caveat, and give one practical editorial action.
- Prompt B: Concise executive summary - Write a short executive summary. Mention the main pattern and one number. Keep it brief and avoid detailed caveats.
- Prompt C: Narrative opinion style - Write a lively narrative about global media attention. Emphasize drama, possible explanations, and broad implications.

## Validation Criteria

The custom rubric uses weighted 0-100 scoring across Numeric Grounding, Comparative Reasoning, Source Scope Control, Editorial Usefulness, and Risk Control. It differs from the LAB because it uses app-specific benchmarks, content-analysis tags, and explicit publish/revise/reject thresholds.

## Descriptive Statistics

| prompt_id   |   count |   mean |   std |   min |   max |
|:------------|--------:|-------:|------:|------:|------:|
| A           |      12 |  89.67 |  6.4  |    81 |    94 |
| B           |      12 |  50    |  6.27 |    44 |    56 |
| C           |      12 |  11    |  3.13 |     8 |    14 |

## Statistical Analysis

- Hypothesis: H1: Prompt A has a higher mean custom validation score than Prompt B. H0: their mean scores are equal.
- Welch t-test: t = 15.340, p = 3.153e-13
- Mean difference (A - B): 39.67
- Cohen's d: 6.26
- One-way ANOVA: F = 618.443, p = 6.972e-27

## Interpretation

Prompt A performed significantly better than Prompt B (Welch t-test p = 3.153e-13). The ANOVA p-value was 6.972e-27, showing that prompt choice affected validation scores overall.

## System Design

The script generates reports from three prompt styles, validates each report against a custom qualitative content-analysis rubric, stores report text and validation scores, and runs statistical tests on the resulting score distributions. In AI reviewer mode, Ollama Cloud reads the rubric and source benchmark and returns structured JSON. In heuristic mode, a deterministic fallback mirrors the rubric for reproducible classroom evidence.
