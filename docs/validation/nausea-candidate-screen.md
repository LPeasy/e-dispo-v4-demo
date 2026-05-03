# NHAMCS Nausea-Alone Candidate Screen

Date: 2026-05-01

Status: candidate-variable screen only. The active `e-dispo-v4.0` educational model is unchanged.

## Intent

Evaluate whether one additional user-feasible structured NHAMCS symptom, nausea-alone, should be considered for a future model version.

This is an educational/statistical review artifact. It is not clinical decision support, triage guidance, discharge guidance, medical advice, or an app activation record.

## Candidate Definition

`nausea_present` is derived from NHAMCS reason-for-visit fields:

```text
nausea_present = 1[RFV1-RFV5 contains 15250]
```

This is explicitly separate from ordinary vomiting:

```text
vomiting_present = 1[RFV1-RFV5 contains 15300]
```

## Paired Model Comparison

Base model:

```text
admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden
```

Candidate model:

```text
admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden + nausea_present
```

The base and candidate models are refit on the exact same complete-case rows. Fever and tachycardia-burden forms stay fixed. No app export, schema activation, UI change, or coefficient promotion occurs.

## Decision

Nausea-alone did not pass every prespecified gate. It had adequate cells and no material calibration harm, but failed the uncertainty gate:

- pooled nausea-positive rows: 798
- pooled nausea-positive events: 104
- nausea coefficient: -0.1285
- nausea odds ratio: 0.879
- direction probability from deterministic draws: 0.7298, below the 0.95 gate
- apparent delta AUROC/Brier: -0.000547 / -0.000017
- leave-one-year-out mean delta AUROC/Brier: -0.001749 / 0.000200

Conclusion: no additional user-feasible NHAMCS symptom passed this screen. Broader variable discovery should use a richer data source rather than lowering the evidence bar for NHAMCS nausea-alone.

## Reproduction

Rebuild the pooled cohort, then run the candidate screen:

```powershell
python scripts/nhamcs/build_yearly_cohorts.py --config config/nhamcs_year_harmonization.yml --output-dir outputs/nhamcs/yearly --years 2018 2019 2020 2021 2022
python scripts/nhamcs/build_pooled_cohort.py --config config/nhamcs_year_harmonization.yml --yearly-output-dir outputs/nhamcs/yearly --output-dir outputs/nhamcs_pooled --years 2018 2019 2020 2021 2022
Rscript scripts/nhamcs/nhamcs_nausea_candidate_screen.R outputs/nhamcs_pooled/analytic_cohort_nhamcs_2018_2022.csv outputs/nhamcs_pooled
```

Expected generated outputs:

- `outputs/nhamcs_pooled/nausea_mapping_audit.csv`
- `outputs/nhamcs_pooled/nausea_model_comparison_metadata.csv`
- `outputs/nhamcs_pooled/nausea_cell_counts_by_year.csv`
- `outputs/nhamcs_pooled/nausea_missingness_by_endpoint.csv`
- `outputs/nhamcs_pooled/nausea_model_comparison_coefficients.csv`
- `outputs/nhamcs_pooled/nausea_model_comparison_covariance.csv`
- `outputs/nhamcs_pooled/nausea_model_comparison_draws.csv`
- `outputs/nhamcs_pooled/nausea_model_comparison_calibration.csv`
- `outputs/nhamcs_pooled/nausea_leave_one_year_out_validation.csv`
- `outputs/nhamcs_pooled/nausea_candidate_gate_decision.csv`
- `outputs/nhamcs_pooled/nausea_candidate_ranked_decision.csv`
- `outputs/nhamcs_pooled/nausea_candidate_screen_report.md`

The coefficient evidence tier is `survey_weighted_candidate`, not `dataset_derived`.
