# Custom AI Report Validation Rubric

This rubric validates the **AI-generated Guardian coverage report** in the Geographic Attention Reporter app. It is customized for this app's use case: turning dashboard coverage statistics into a grounded newsroom or research brief.

Unlike the generic Likert-scale lab rubric, this framework uses:

- App-specific benchmark facts from the Guardian dashboard.
- Weighted 0-100 scoring.
- Qualitative content-analysis tags.
- Publish/revise/reject thresholds.
- Statistical comparison of Prompt A, Prompt B, and Prompt C.

## Benchmark Facts

The experiment uses the same benchmark facts for every prompt so the comparison is fair. The **date window is supplied at runtime** with `--from-date` and `--to-date`; **the example below uses March 1, 2026 to May 5, 2026.**


| Fact                        | Benchmark                                           |
| --------------------------- | --------------------------------------------------- |
| Source                      | The Guardian Open Platform                          |
| Date window                 | User supplied, e.g. `2026-03-01 to 2026-05-05`      |
| Countries analyzed          | United Kingdom, United States, India, Brazil, Japan |
| Total reports/articles      | 240                                                 |
| Average per country         | 48                                                  |
| Highest raw coverage        | United Kingdom, 90 articles                         |
| Lowest raw coverage         | Japan, 18 articles                                  |
| Highest per-capita coverage | United Kingdom, 1.32 articles per 1M people         |
| Lowest per-capita coverage  | India, 0.02 articles per 1M people                  |
| Coverage ratio              | 5.0x between highest and lowest raw coverage        |
| Topic pattern               | Politics and crisis coverage dominate               |


## Scoring Framework


| Dimension             | Points | What The Reviewer Looks For                                                                                 | Benchmark                                          |
| --------------------- | ------ | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| Numeric Grounding     | 25     | Correct use of benchmark numbers, source facts, dates, country names, and article counts.                   | 20+ and no major contradiction.                    |
| Comparative Reasoning | 20     | Raw volume comparison, per-capita comparison, top/bottom contrast, and explanation of geographic imbalance. | 15+ and at least one raw-vs-per-capita comparison. |
| Source Scope Control  | 15     | Clear statement that the data come from The Guardian, with date window and country scope.                   | 12+ and explicit Guardian mention.                 |
| Editorial Usefulness  | 20     | Practical implication for editors, researchers, or students; identifies coverage gaps or next steps.        | 15+ and at least one concrete action.              |
| Risk Control          | 20     | Avoids unsupported causal claims, sensational wording, and overgeneralization; includes caveats.            | 16+ and no severe unsupported claim.               |


## Content-Analysis Tags

The reviewer assigns tags when a report contains specific qualitative features:

- `numeric_grounding`
- `raw_volume_comparison`
- `per_capita_comparison`
- `top_bottom_contrast`
- `coverage_imbalance_explained`
- `source_scope_control`
- `source_date_country_scope`
- `editorial_action`
- `research_use`
- `coverage_gap`
- `risk_control`
- `unsupported_claim`
- `sensational_language`

## Decision Thresholds


| Overall Score | Recommendation | Meaning                                                         |
| ------------- | -------------- | --------------------------------------------------------------- |
| 85-100        | publish        | Report is grounded, useful, and low risk.                       |
| 65-84         | revise         | Report has value but needs better grounding, scope, or caution. |
| 0-64          | reject         | Report is too incomplete, risky, or unsupported for use.        |


## Prompt Experiment

The experiment compares three prompts:

- **Prompt A: Evidence-first newsroom brief** asks for exact numbers, scope, caveats, raw/per-capita comparison, and editorial action.
- **Prompt B: Concise executive summary** asks for a short summary with fewer required details.
- **Prompt C: Narrative opinion style** invites broader interpretation and is expected to score lower on grounding and risk control.

The hypothesis is that **Prompt A will perform significantly better** because its instructions align directly with the custom validation criteria.