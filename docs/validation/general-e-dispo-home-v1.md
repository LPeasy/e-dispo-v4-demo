# general-E-Dispo-home-v1

Date: 2026-05-04

Public general model IDs:

- `general-E-Dispo-home-v1`
- `general-E-Dispo-home-v1-measured-sbp`

Active abdominal-pain app model: `e-dispo-v4.1-pas5-high-acuity-surrogate`

This note documents the home-facing public general model revision. It is a parallel educational/statistical NHAMCS model artifact, not a replacement for the adult-male abdominal-pain model, not clinical decision support, not medical advice, not external validation, and not transportability evidence.

## Why This Revision Exists

The source-scope `general-E-Dispo-model-v1-plus-sex` artifact included `arrival_transfer_context` and required SBP. That was defensible for a reviewer model fitted to ED records, but not for a public home-facing demo. A person starting at home is not being transferred in from another hospital or urgent care, and SBP should not be guessed.

The public general demo therefore removes transfer-in context, replaces the raw acuity dropdown with the same five PAS-5 questions used by the adult-male abdominal-pain model, and uses a two-branch SBP design:

- blank SBP uses `general-E-Dispo-home-v1`
- measured SBP uses `general-E-Dispo-home-v1-measured-sbp`

SBP is acceptable only as an actual measured value from a cuff, EMS, clinic, or ED reading; this matches CDC home blood-pressure guidance that home BP measurement requires a monitor: https://www.cdc.gov/high-blood-pressure/measure/index.html.

## Formulas

Default public formula:

```text
admit ~ age_centered_40
      + sex
      + high_acuity_proxy
      + fever_or_temp
      + tachycardia_burden
```

Measured-SBP formula:

```text
admit ~ age_centered_40
      + sex
      + high_acuity_proxy
      + fever_or_temp
      + tachycardia_burden
      + hypotension_burden
```

`high_acuity_proxy` is derived in the public app from PAS-5: A1/A2 activate the term and A3/A4/A5 are reference. The NHAMCS fit uses `IMMEDR` only as a surrogate source: `IMMEDR` 1 maps to A1, 2 maps to A2, 3 maps to A3, 4 maps to A4, and 5 maps to A5. Unknown, blank, and no-triage values are non-estimable for this term.

`arrival_transfer_context` and raw categorical `acuity_code` are not included in either public home-facing formula. Race/ethnicity, payer, region, and MSA remain subgroup/fairness review variables only.

## Method

Both branches are fitted in `scripts/nhamcs/nhamcs_general_e_dispo_home_v1.R` against `outputs/nhamcs_pooled/full_source_nontrauma_cohort_nhamcs_2018_2022.csv`.

The target is `admit` versus `routine_home_discharge` in the all-sex/all-age NHAMCS non-trauma source cohort. Transfer rows remain excluded from the admit model.

Fitting uses `survey::svyglm(..., family = quasibinomial())` with pooled NHAMCS weights, strata, and PSUs. AUROC and Brier intervals use 1,000 survey-bootstrap replicate weights with fixed apparent predictions. Optimism correction uses 200 survey-bootstrap refits.

## Performance Summary

| Model | Denominator | Events | Complete-case N | Complete-case events | AUROC | Brier | Optimism-corrected AUROC | Optimism-corrected Brier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `general-E-Dispo-home-v1` | 50,070 | 7,447 | 32,681 | 4,702 | 0.811803 | 0.101883 | 0.810300 | 0.102111 |
| `general-E-Dispo-home-v1-measured-sbp` | 50,070 | 7,447 | 29,761 | 4,581 | 0.807020 | 0.107047 | 0.805531 | 0.107319 |

| Model | AUROC 95% interval | Brier 95% interval |
|---|---:|---:|
| `general-E-Dispo-home-v1` | 0.796539 to 0.824578 | 0.094929 to 0.108322 |
| `general-E-Dispo-home-v1-measured-sbp` | 0.792927 to 0.818820 | 0.099894 to 0.113953 |

The measured-SBP branch did not improve overall apparent or optimism-corrected AUROC/Brier compared with the no-SBP default. It is retained only so a real measured SBP can be used without forcing SBP on users who do not have a measurement.

## Output Artifacts

- `outputs/nhamcs_pooled/general_e_dispo_home_v1_coefficients.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_covariance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_performance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_calibration.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_calibration_by_decile.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_performance_intervals.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_optimism_corrected_performance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_subgroup_performance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_subgroup_calibration.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_missingness.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_model_spec.json`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_report.md`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_coefficients.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_covariance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_performance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_calibration.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_calibration_by_decile.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_performance_intervals.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_optimism_corrected_performance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_subgroup_performance.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_subgroup_calibration.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_missingness.csv`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_model_spec.json`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_report.md`
- `outputs/nhamcs_pooled/general_e_dispo_home_v1_sbp_optional_comparison.csv`

Browser draw assets use `high_acuity_proxy` and do not include `acuity_code_*` or `arrival_transfer_context_*` terms:

- `src/data/general-e-dispo-home-coefficient-draws.csv`
- `src/data/general-e-dispo-home-measured-sbp-coefficient-draws.csv`

## Limitations

These are internal NHAMCS apparent and optimism-corrected analyses only. They do not prove clinical validity, external validation, transportability, or individual-level safety. The general model is broader than the adult-male abdominal-pain model, but it is still an educational/statistical demo.
