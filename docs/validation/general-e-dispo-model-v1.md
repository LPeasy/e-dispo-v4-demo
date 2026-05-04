# general-E-Dispo-model-v1

Date: 2026-05-04

Active app model: `e-dispo-v4.1-pas5-high-acuity-surrogate`

Parallel model ID: `general-E-Dispo-model-v1`

This note documents a separate all-sex/all-age NHAMCS non-trauma educational/statistical model artifact. It is not the active GitHub Pages model, not a replacement for the adult-male abdominal-pain `e-dispo-v4.1-pas5-high-acuity-surrogate` model, not clinical decision support, not external validation, and not transportability evidence.

## Model Boundary

`e-dispo-v4.1-pas5-high-acuity-surrogate` is the active educational app model for adult men ages 18-64 with non-traumatic abdominal pain:

```text
admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden
```

`general-E-Dispo-model-v1` is a parallel reviewer/development artifact for broader NHAMCS non-trauma ED records:

```text
admit ~ age_centered_40
      + acuity_code
      + arrival_transfer_context
      + fever_or_temp
      + tachycardia_burden
      + hypotension_burden
```

No app toggle or active app constants are added in this pass.

## Cohort And Endpoint

Input file:

- `outputs/nhamcs_pooled/full_source_nontrauma_cohort_nhamcs_2018_2022.csv`

Scope:

- all sexes
- all ages
- non-trauma ED records
- no abdominal-pain gate
- same strict binary endpoint exclusions as the active model

Target:

```text
endpoint_class == admit
versus
endpoint_class == routine_home_discharge
```

Transfer remains excluded from the admit model. The prior transfer-vs-home screen remains report-only context.

## Predictor Mapping

The general model uses pre-disposition variables only:

| Predictor | Mapping |
|---|---|
| `age_centered_40` | `age - 40` |
| `acuity_code` | categorical NHAMCS `IMMEDR`; reference `urgent`; blank/unknown/no-triage levels preserved |
| `arrival_transfer_context` | categorical NHAMCS `AMBTRANSFER`; reference `no_not_transferred_from_hospital_or_urgent_care`; blank/unknown/not-applicable levels preserved |
| `fever_or_temp` | `1[temp >= 100.4F]` when temperature is observed |
| `tachycardia_burden` | `max(HR - 100, 0) / 10` |
| `hypotension_burden` | `max(100 - SBP, 0) / 10` |

The yearly/full-source cohort builder now carries:

- raw `IMMEDR`
- harmonized `acuity_code`
- raw `AMBTRANSFER`
- harmonized `arrival_transfer_context`
- derived `hypotension_burden`

The code-list map is versioned in `config/code_lists/nhamcs_general_e_dispo_model_recode_maps.yml`. The pooled harmonization audit includes rows for `acuity_code`, `arrival_transfer_context`, and `hypotension_burden`.

The primary formula intentionally excludes pain, vomiting, nausea, hematemesis, payer, sex, race/ethnicity, region, MSA, imaging, medication, length-of-visit, wait-time, treatment, diagnosis, and disposition-derived fields. Payer and demographics appear only in subgroup/fairness artifacts.

The 2026-05-04 sensitivity pass also fits `general-E-Dispo-model-v1-plus-sex`, which adds `sex` as a categorical main effect only. That sensitivity model is now exposed as the separate public runnable demo `general-E-Dispo-model-v1-sex-adjusted`. It is not the active adult-male abdominal-pain model and does not replace the primary clean `general-E-Dispo-model-v1` reviewer artifact.

## Public Runnable Demo

The active app workstream now builds two static site variants from `e-dispo-prototype/`:

| Build command | Output directory | Public model |
|---|---|---|
| `npm run build:v4` | `dist/e-dispo-v4-demo/` | current E-Dispo abdominal-pain app behavior |
| `npm run build:general` | `dist/general-e-dispo-demo/` | `general-E-Dispo-model-v1-sex-adjusted` |
| `npm run build:all-sites` | both directories | both public demos |

The general public demo uses the `general-E-Dispo-model-v1-plus-sex` coefficients and covariance artifact, generated into a browser coefficient-draw asset at `src/data/general-e-dispo-coefficient-draws.csv`. The public model ID is deliberately different from the reviewer source artifact ID:

- Source statistical artifact: `general-E-Dispo-model-v1-plus-sex`
- Runnable public model: `general-E-Dispo-model-v1-sex-adjusted`

This naming keeps the reviewer evidence trail separate from the public runnable site. It also prevents the broader general model from being confused with the adult-male abdominal-pain `e-dispo-v4.1-pas5-high-acuity-surrogate` app model.

## Outputs

- `outputs/nhamcs_pooled/general_e_dispo_model_v1_coefficients.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_covariance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_performance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_calibration.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_calibration_by_decile.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_performance_intervals.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_optimism_corrected_performance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_subgroup_performance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_subgroup_calibration.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_missingness.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_model_spec.json`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_report.md`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_coefficients.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_covariance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_performance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_calibration.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_calibration_by_decile.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_performance_intervals.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_optimism_corrected_performance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_subgroup_performance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_subgroup_calibration.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_missingness.csv`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_model_spec.json`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_report.md`
- `outputs/nhamcs_pooled/general_e_dispo_model_v1_sex_sensitivity_comparison.csv`

## Counts

| Quantity | Value |
|---|---:|
| Admit-vs-home denominator, all sexes/all ages non-trauma | 50,070 |
| Admissions before complete-case restriction | 7,447 |
| Complete-case N | 42,300 |
| Complete-case admissions | 6,488 |
| Sex gate applied | No |
| Admit-vs-home sex-code counts | sex=1: 28,185; sex=2: 21,885 |
| Rows also satisfying original adult-male age 18-64 flag | 17,703 |

The active v4.1 full strict-binary counts remain `3,805` with `459` admission events; the PAS-5/IMMEDR complete-case fit uses `2,245 / 254`.

## Apparent Performance

| Metric | Estimate |
|---|---:|
| AUROC | 0.817657 |
| Brier score | 0.104806 |
| Observed prevalence | 0.159203 |
| Mean predicted probability | 0.159203 |
| Calibration-in-the-large | approximately 0.000000 |
| Calibration slope | 1.000000 |

The calibration intercept and slope are apparent same-cohort diagnostics. They do not validate the model outside NHAMCS.

## Intervals And Optimism Correction

AUROC and Brier intervals use 1,000 `survey::as.svrepdesign(..., type = "bootstrap")` replicate weights from pooled NHAMCS strata/PSUs with fixed apparent predictions.

| Metric | Estimate | 95% interval | Method |
|---|---:|---:|---|
| AUROC | 0.817657 | 0.806684 to 0.827352 | Survey bootstrap replicate weights, fixed apparent predictions |
| Brier score | 0.104806 | 0.099189 to 0.110763 | Survey bootstrap replicate weights, fixed apparent predictions |

Internal optimism correction uses 200 survey-bootstrap refits of the general formula. All 200 refits completed.

| Metric | Apparent estimate | Optimism-corrected estimate |
|---|---:|---:|
| AUROC | 0.817657 | 0.815737 |
| Brier score | 0.104806 | 0.105250 |
| Calibration-in-the-large | approximately 0.000000 | -0.002014 |
| Calibration slope | 1.000000 | 0.987855 |

These are internal NHAMCS analyses only. They do not provide external validation, clinical validation, or transportability.

## Plus-Sex Sensitivity

`general-E-Dispo-model-v1-plus-sex` uses the same denominator, endpoint, complete-case restriction, survey design, interval method, and optimism-correction method as the base general model, but adds `sex` as a categorical main effect:

```text
admit ~ age_centered_40
      + sex
      + acuity_code
      + arrival_transfer_context
      + fever_or_temp
      + tachycardia_burden
      + hypotension_burden
```

Sex is presentation-available but fairness-sensitive. The sensitivity artifact is reviewer evidence only; it is not a promotion decision.

| Model | AUROC | Brier | Optimism-corrected AUROC | Optimism-corrected Brier | Maximum absolute sex calibration gap |
|---|---:|---:|---:|---:|---:|
| `general-E-Dispo-model-v1` | 0.817657 | 0.104806 | 0.815737 | 0.105250 | 0.012625 |
| `general-E-Dispo-model-v1-plus-sex` | 0.818263 | 0.104635 | 0.816054 | 0.105424 | approximately 0.000000 |
| Plus-sex minus base | +0.000606 | -0.000171 | +0.000317 | +0.000174 | -0.012625 |

The plus-sex model nearly eliminates the within-NHAMCS sex subgroup calibration gap, but the overall predictive gain is very small and optimism-corrected Brier is slightly worse. The current reviewer conclusion is therefore: keep as a sensitivity artifact and do not promote sex into the primary clean general model.

## Subgroup And Missingness Artifacts

Subgroup rows are written for sex, full age band, race/ethnicity, payer, region, MSA, original active-scope flags, acuity level, arrival-transfer context, and vital availability. Forty-eight subgroup performance rows are estimable. The only sparse-cell blocker in this pass is payer `Worker's compensation` with 46 rows and 2 admissions.

Required predictor missingness is not imputed. Missing temperature, HR, or SBP rows are explicit `blocked_no_model_estimable_rows` in `general_e_dispo_model_v1_missingness.csv`.

## Interpretation

This model has stronger apparent discrimination than the earlier compact full-source non-trauma candidate because it adds triage acuity, transfer-in context, and hypotension burden. That does not make it the active app model. It is a cleaner parallel development artifact whose predictors are more logically suited to a general non-trauma ED scope.

The next defensible step is prespecified comparison against alternative clean pre-disposition formulas, subgroup interval estimation where supported, and source-specific validation when lawful full-access data are available. The plus-sex sensitivity should remain documented but unpromoted unless a later fairness review and external/source-specific validation justify adding a fairness-sensitive demographic predictor.
