# Full-Source Non-Trauma Admit Candidate Track

Date: 2026-05-03

Active model remains: `e-dispo-v4.0`

Candidate model ID: `e-dispo-v4.1-full-source-nontrauma-admit`

This note documents a separate reviewer/development track on the broader full-source NHAMCS non-trauma cohort. It is educational/statistical only. It is not the active GitHub Pages model, not clinical decision support, not external validation, and not transportability evidence.

Status note, 2026-05-04: `general-E-Dispo-model-v1` now exists as a cleaner parallel all-sex/all-age non-trauma model artifact using age, NHAMCS acuity, AMBTRANSFER arrival-transfer context, fever/temp, tachycardia burden, and hypotension burden. This older `e-dispo-v4.1-full-source-nontrauma-admit` track remains useful for comparability to the compact active-model predictor surface, but it is not the clean general model and it still does not replace `e-dispo-v4.0`.

## Candidate Model Method

The candidate fit uses `outputs/nhamcs_pooled/full_source_nontrauma_cohort_nhamcs_2018_2022.csv`. This cohort is not male-only: it removes the active model's sex, age, and abdominal-pain gates, and retains the non-trauma restriction.

Target:

```text
endpoint_class == admit
versus
endpoint_class == routine_home_discharge
```

The transfer class remains excluded from fitting and is reported separately in the variable screen.

Formula:

```text
admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden
```

Fit method:

- `survey::svyglm(..., family = quasibinomial())`
- pooled weight: `pooled_weight = PATWT / 5`
- pooled strata/PSU design: year-prefixed NHAMCS strata and PSU fields
- complete-case scoring for the same compact predictor surface
- coefficient evidence tier: `survey_weighted_candidate`

## Candidate Model Outputs

- `outputs/nhamcs_pooled/full_source_nontrauma_admit_model_coefficients.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_admit_model_covariance.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_admit_model_calibration.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_admit_model_performance.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_admit_model_report.md`

## Candidate Model Results

| Quantity | Value |
|---|---:|
| Admit-vs-home denominator, all sexes/all ages non-trauma | 50,070 |
| Admissions before complete-case restriction | 7,447 |
| Complete-case N | 29,096 |
| Complete-case admissions | 4,035 |
| Sex gate applied | No |
| Admit-vs-home sex-code counts | sex=1: 28,185; sex=2: 21,885 |
| Rows also satisfying original adult-male age 18-64 flag | 17,703 |
| Weighted observed prevalence | 0.139248 |
| Mean predicted probability | 0.139248 |
| AUROC | 0.757181 |
| Brier score | 0.105462 |
| Calibration-in-the-large | 0.000000 |
| Calibration slope | 1.000000 |

The apparent calibration intercept and slope are expected to be near 0 and 1 because this is the same cohort used for fitting. These are apparent candidate-model diagnostics, not external validation.

## Candidate Coefficients

| Term | Beta | SE | Odds ratio | Evidence tier |
|---|---:|---:|---:|---|
| `intercept` | -2.336571 | 0.076362 | 0.096659 | `survey_weighted_candidate` |
| `age_centered` | 0.045061 | 0.002104 | 1.046092 | `survey_weighted_candidate` |
| `pain_severe` | 0.013617 | 0.056926 | 1.013710 | `survey_weighted_candidate` |
| `fever_or_temp` | 0.265537 | 0.129901 | 1.304131 | `survey_weighted_candidate` |
| `vomiting_present` | 0.432729 | 0.076006 | 1.541458 | `survey_weighted_candidate` |
| `tachycardia_burden` | 0.317068 | 0.020883 | 1.373096 | `survey_weighted_candidate` |

The severe-pain coefficient is much smaller in this broader non-trauma source scope than in the active adult-male abdominal-pain model. That is a useful development finding, but it does not update `e-dispo-v4.0`.

## Variable Screen Outputs

- `outputs/nhamcs_pooled/full_source_nontrauma_analytic_variable_correlations.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_raw_variable_correlations.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_transfer_variable_correlations.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_variable_screen_report.md`

Targets:

- `admit_vs_home`: `endpoint_class == admit` versus `routine_home_discharge`
- `transfer_vs_home`: `endpoint_class == transfer` versus `routine_home_discharge`

Variable-screen methods:

- continuous/numeric variables: weighted Pearson/point-biserial correlation plus unweighted correlation
- binary variables: weighted phi/point-biserial correlation plus event/reference prevalence columns
- categorical variables: weighted Cramer's V plus one-vs-rest level rows when level count is within the screen cap
- leakage/design/identifier columns: explicit excluded rows
- all-missing, no-variation, sparse, or high-cardinality fields: explicit blocker rows

Variable-screen row status summary:

| Artifact | Rows | Variables | Status summary |
|---|---:|---:|---|
| Analytic admit screen | 118 | 53 | 96 ok; 20 excluded; 2 no-variable-variation blockers |
| Raw admit screen | 4,073 | 954 | 3,183 ok; 33 excluded; 857 blocker rows |
| Transfer companion screen | 3,975 | 1,000 | 2,937 ok; 53 excluded; 985 blocker rows |

The transfer companion denominator is 44,218 rows with 1,595 transfer events. Transfer is not combined with admission for fitting.

## Interpretation Boundary

This pass is a development screen for a possible broader all-sex/all-age non-trauma NHAMCS model track. It does not promote a new active app model and does not prove a broader intended-use population.

Raw-variable associations can be strong for medication, workflow, or other source-process fields. Those rows are screening observations only and are not automatically valid pre-disposition predictors. No variable is promoted to `dataset_derived` from correlation alone.

The next defensible development step is to use these screen artifacts to define prespecified candidate predictors, then evaluate them through fitted model comparisons, missingness review, leakage review, calibration, and optimism correction before considering any replacement model.
