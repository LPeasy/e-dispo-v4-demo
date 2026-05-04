# Pooled Empirical Model Performance Report

This report summarizes the active reduced empirical model implemented as `e-dispo-v4.0`.

The model is for educational/statistical use only. It is not clinical decision support, medical advice, a triage tool, or a discharge-safety tool.

## Model Status

- Model ID: `e-dispo-v4.0`
- Dataset: `NHAMCS_2018_2022_POOLED`
- Endpoint: same-hospital admission vs routine home discharge after exclusions
- Population: adult men ages 18-64, ED, non-traumatic abdominal pain
- Empirical activation: active for educational use after app-side export validation
- Formula: `admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden`
- Age transformation: `age_centered = age - 42`
- Tachycardia transformation: `tachycardia_burden = max(HR - 100, 0) / 10`
- Pain transformation: `pain_severe = 1[pain_bin3 == severe]`; mild and moderate are collapsed as non-severe.
- Pain monotonicity verdict: `nonmonotonic_collapsed_to_severe_binary`
- Missingness handling: observed pain and observed HR are required; HR missing is not treated as normal.

## Cohort Snapshot

- Complete-case unweighted N for `e-dispo-v4.0` fit: 2,674
- Admission events in complete-case `e-dispo-v4.0` fit: 307
- Full strict binary pooled NHAMCS N before complete-case restriction: 3,805
- Full strict binary pooled NHAMCS admission events before complete-case restriction: 459
- Event-count gate: passed

## Apparent Performance

- AUROC/C-statistic: 0.713
- Brier score: 0.0976
- Observed prevalence: 11.75%
- Mean predicted probability: 11.75%
- Calibration intercept: approximately 0.000
- Calibration slope: approximately 1.000

## Reviewer Calibration And Interval Artifacts

The 2026-05-03 reviewer artifact pass added grouped calibration, apparent-performance interval, subgroup, missingness, optimism-correction, transportability-blocker, candidate-gate, and full-source NHAMCS scope-screen outputs for the active model:

- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_calibration_by_decile.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_calibration_plot_data.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_performance_intervals.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_subgroup_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_subgroup_calibration.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_missingness_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_optimism_corrected_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_transportability_track.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_candidate_refinement_gate.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_endpoint_screen_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_endpoint_screen_calibration.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_endpoint_screen_missingness.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_nontrauma_screen_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_nontrauma_screen_calibration.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_nontrauma_screen_missingness.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_scope_screen_report.md`
- `outputs/nhamcs_pooled/full_source_nontrauma_admit_model_coefficients.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_admit_model_covariance.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_admit_model_calibration.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_admit_model_performance.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_analytic_variable_correlations.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_raw_variable_correlations.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_transfer_variable_correlations.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_variable_screen_report.md`
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
- `docs/validation/calibration-performance-interval-artifact-pass.md`
- `docs/validation/full-source-scope-screen.md`
- `docs/validation/full-source-nontrauma-admit-candidate.md`
- `docs/validation/general-e-dispo-model-v1.md`

Grouped calibration uses weighted predicted-probability deciles from the active model's apparent predictions. The grouped table reports unweighted N/events, weighted N/events, predicted range, survey-weighted mean prediction, survey-weighted observed admission rate, and a Taylor-linearized survey interval for the observed group rate.

AUROC and Brier intervals use 1,000 `survey::as.svrepdesign(..., type = "bootstrap")` replicate weights from the pooled NHAMCS stratum/PSU design, with fixed apparent predictions from the active fitted model.

| Metric | Estimate | 95% interval | Interval method |
|---|---:|---:|---|
| AUROC | 0.713095 | 0.670617 to 0.757748 | Survey bootstrap replicate weights, fixed apparent predictions |
| Brier score | 0.097640 | 0.084632 to 0.111066 | Survey bootstrap replicate weights, fixed apparent predictions |

These are apparent-performance intervals for the fitted educational model surface. They do not refit the model inside each replicate, correct optimism, provide external validation, or prove transportability.

## Robustness And Internal Validation Artifacts

Subgroup and missingness outputs report unweighted N/events, weighted N/events, observed prevalence, mean predicted probability, calibration gap, AUROC, Brier score, and status for age band, predictor/proxy availability, race/ethnicity, payer, region, and MSA rows. Race/ethnicity, region, and MSA are estimable. Payer is estimable for the larger levels, while small levels such as blank, no charge/charity, and worker's compensation are explicit sparse-cell or no-outcome-variation blockers rather than fabricated estimates.

Optimism-corrected internal validation uses 200 deterministic survey-bootstrap refits of the active formula. For each bootstrap replicate, the model is refit with replicate weights, then scored on both the bootstrap sample and the original complete-case cohort. Mean optimism is subtracted from apparent performance.

| Metric | Apparent estimate | Optimism-corrected estimate | Method |
|---|---:|---:|---|
| AUROC | 0.713095 | 0.704894 | 200 survey-bootstrap refits |
| Brier score | 0.097640 | 0.099565 | 200 survey-bootstrap refits |
| Calibration-in-the-large | 0.000000 | 0.012975 | 200 survey-bootstrap refits |
| Calibration slope | 1.000000 | 0.954089 | 200 survey-bootstrap refits |

The source-specific transportability track currently writes `blocked_sparse_replication_only` for MIMIC-IV-ED. The available strict binary MIMIC sample has 12 rows and 11 complete-case rows for the active predictor surface, which is too small for validation. This is a blocker artifact only, not external validation.

The candidate-refinement gate blocks AAP-3, SBP, acuity, hematemesis, nausea-alone, tachycardia duration, and pain-representation changes pending prespecified mapping, sparse-cell, timestamp, or monotonicity evidence gates. No new predictor is promoted.

## Full-Source NHAMCS Scope Screen

The 2026-05-03 full-source screen applies the fixed active `e-dispo-v4.0` coefficients to broader NHAMCS strict-binary endpoint cohorts. It does not refit the model, does not change coefficients, and does not promote a broader population claim.

| Screen | Strict-binary N | Events | Model-estimable N | Model-estimable events | AUROC | Brier | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| Endpoint-only full ED | 77,031 | 10,139 | 44,668 | 5,429 | 0.743845 | 0.097487 | `source_screen` |
| Non-trauma sensitivity | 50,070 | 7,447 | 29,096 | 4,035 | 0.745550 | 0.108448 | `source_screen` |

The endpoint-only full ED screen removes age, sex, abdominal-pain, and trauma filters while retaining the strict same-hospital admission versus routine home discharge endpoint exclusions. The non-trauma sensitivity keeps the same broader population but retains the non-trauma restriction. Both screens include scope flags for active-scope membership, adult male age 18-64 membership, full age band, sex, abdominal-pain RFV flag, non-trauma flag, and active predictor availability.

These rows are out-of-scope NHAMCS source/generalization screens. They are useful for seeing how the fixed educational model behaves when applied beyond its fitted population, but they are not external validation, transportability evidence, clinical validation, or a basis to use the model outside the adult male non-traumatic abdominal-pain cohort.

## Full-Source Non-Trauma Candidate Track

The 2026-05-03 candidate track adds a separate broader NHAMCS non-trauma development model, `e-dispo-v4.1-full-source-nontrauma-admit`. This candidate is not male-only: it removes the active model's sex, age, and abdominal-pain gates while retaining the non-trauma restriction. The model is labeled `survey_weighted_candidate`; it does not replace active `e-dispo-v4.0` and is not used by the GitHub Pages app.

| Candidate | Target | Denominator | Events | Complete-case N | Complete-case events | AUROC | Brier | Status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `e-dispo-v4.1-full-source-nontrauma-admit` | admit vs routine home discharge, all-sex/all-age non-trauma | 50,070 | 7,447 | 29,096 | 4,035 | 0.757181 | 0.105462 | `survey_weighted_candidate` |

The candidate uses the same compact predictor surface for comparability: `admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden`. It is fit with `survey::svyglm(..., family = quasibinomial())` using pooled NHAMCS weights, strata, and PSUs. Apparent calibration-in-the-large is approximately 0.000000 and apparent calibration slope is approximately 1.000000 because this is an apparent same-cohort fit. The admit-vs-home candidate denominator contains sex code 1 rows (28,185) and sex code 2 rows (21,885); 17,703 rows also satisfy the original adult-male age 18-64 flag, but that flag is not used as a gate for this candidate model.

The companion variable screen writes one row or explicit status/blocker output for every generated analytic variable and raw public-use NHAMCS variable it screens:

| Artifact | Target | Source variables | Rows | Status summary |
|---|---|---:|---:|---|
| `full_source_nontrauma_analytic_variable_correlations.csv` | admit vs home | 53 | 118 | 96 ok; 20 excluded; 2 no-variable-variation blockers |
| `full_source_nontrauma_raw_variable_correlations.csv` | admit vs home | 954 | 4,073 | 3,183 ok; 33 excluded; 857 blocker rows |
| `full_source_nontrauma_transfer_variable_correlations.csv` | transfer vs home | 1,000 analytic/raw variables | 3,975 | 2,937 ok; 53 excluded; 985 blocker rows |

Continuous/numeric variables use weighted Pearson/point-biserial correlation plus an unweighted comparator. Binary variables use weighted phi/point-biserial correlation. Categorical variables use weighted Cramer's V plus one-vs-rest level rows when level count is within the screen cap. Disposition, design, identifier, and outcome-leakage fields are excluded with explicit rows. High-cardinality, all-missing, no-variation, or sparse fields are blocked rather than silently omitted.

Transfer is report-only in this pass. The transfer companion denominator is 44,218 rows with 1,595 transfer events, and transfer is not combined with admission for model fitting.

This candidate track is a development artifact only. Raw-variable associations can reflect treatment, workflow, documentation, or other source-process signals and do not promote predictors into `dataset_derived` status. Any future replacement model would need prespecified candidate selection, leakage review, model comparison, missingness review, calibration, and optimism correction.

## Parallel General Non-Trauma Model

The 2026-05-04 pass adds `general-E-Dispo-model-v1`, a separate all-sex/all-age NHAMCS non-trauma educational/statistical model artifact. This model is not the active app model and is not a candidate replacement for `e-dispo-v4.0` in this pass.

The source cohort is `outputs/nhamcs_pooled/full_source_nontrauma_cohort_nhamcs_2018_2022.csv`. The yearly/full-source builder now carries raw `AMBTRANSFER`, harmonized `arrival_transfer_context`, raw `IMMEDR`, harmonized `acuity_code`, and derived `hypotension_burden`; the corresponding code-list map is `config/code_lists/nhamcs_general_e_dispo_model_recode_maps.yml`.

Primary formula:

```text
admit ~ age_centered_40
      + acuity_code
      + arrival_transfer_context
      + fever_or_temp
      + tachycardia_burden
      + hypotension_burden
```

Payer, sex, race/ethnicity, region, and MSA are not in the fitted primary formula. They appear only in subgroup/fairness artifacts.

| Model | Target | Denominator | Events | Complete-case N | Complete-case events | AUROC | Brier | Status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `general-E-Dispo-model-v1` | admit vs routine home discharge, all-sex/all-age non-trauma | 50,070 | 7,447 | 42,300 | 6,488 | 0.817657 | 0.104806 | `survey_weighted_parallel_model` |
| `general-E-Dispo-model-v1-plus-sex` | same, plus categorical sex main effect | 50,070 | 7,447 | 42,300 | 6,488 | 0.818263 | 0.104635 | `survey_weighted_parallel_sensitivity_model` |

The admit-vs-home denominator remains all-sex/all-age with sex-code counts 28,185 / 21,885. The original adult-male age 18-64 flag is retained for review only; 17,703 rows also satisfy that flag, but it is not a gate.

Performance intervals use 1,000 survey-bootstrap replicate weights with fixed apparent predictions:

| Metric | Estimate | 95% interval | Method |
|---|---:|---:|---|
| AUROC | 0.817657 | 0.806684 to 0.827352 | Survey bootstrap replicate weights, fixed apparent predictions |
| Brier score | 0.104806 | 0.099189 to 0.110763 | Survey bootstrap replicate weights, fixed apparent predictions |

For the plus-sex sensitivity model, the same interval method gives AUROC 0.818263 with a 95% interval of 0.808518 to 0.828209, and Brier score 0.104635 with a 95% interval of 0.099073 to 0.110226.

The 200-refit survey-bootstrap optimism correction completed:

| Metric | Apparent estimate | Optimism-corrected estimate |
|---|---:|---:|
| AUROC | 0.817657 | 0.815737 |
| Brier score | 0.104806 | 0.105250 |
| Calibration-in-the-large | approximately 0.000000 | -0.002014 |
| Calibration slope | 1.000000 | 0.987855 |

The plus-sex 200-refit optimism correction also completed. Compared with the base general model, plus-sex improved apparent AUROC by 0.000606 and apparent Brier by 0.000171, improved optimism-corrected AUROC by 0.000317, but worsened optimism-corrected Brier by 0.000174. It reduced the maximum absolute sex subgroup calibration gap from 0.012625 to approximately 0.000000. This is a calibration sensitivity finding, not a promotion decision; sex remains fairness-sensitive and is not added to the primary clean general model.

Subgroup performance/calibration artifacts are written for sex, full age band, race/ethnicity, payer, region, MSA, active-scope flags, acuity, arrival-transfer context, and vital availability. Forty-eight subgroup performance rows are estimable; payer `Worker's compensation` is the only sparse-cell blocker in this pass.

This parallel model remains internal NHAMCS evidence. It is not external validation, not transportability evidence, not clinical validation, and not an app behavior change.

On the same complete-case cohort, the severe-only pain model had AUROC 0.713095 and Brier 0.097640. The current flexible pain comparator had AUROC 0.713136 and Brier 0.097694; the no-pain comparator had AUROC 0.701754 and Brier 0.098208. Leave-one-year-out mean performance favored severe-only pain over the flexible pain comparator: AUROC 0.705185 vs 0.695440 and Brier 0.098783 vs 0.099243.

The prevalence-only Brier score for the exported observed prevalence is approximately 0.104. The active model Brier score of 0.0976 is an absolute improvement of about 0.006. This is useful signal for a small educational model, but it is not a large error-reduction gain.

## Coefficient Interpretation

Approximate odds ratios from the exported coefficients:

| Term | Beta | Approximate OR | Interpretation boundary |
|---|---:|---:|---|
| `age_centered` | 0.043 | 1.04 per year; 1.54 per decade | Direct age signal inside the narrow adult male cohort. |
| `pain_severe` | 0.522 | 1.69 | Severe vs non-severe pain signal; not a monotonic pain dose response. |
| `fever_or_temp` | 0.887 | 2.43 | Fever/temperature proxy remains positive, with a large standard error. |
| `vomiting_present` | 0.469 | 1.60 | Ordinary vomiting RFV/symptom proxy is active. |
| `tachycardia_burden` | 0.427 | 1.53 per 10 bpm over 100 | Observed HR signal; missing HR blocks the `e-dispo-v4.0` estimate. |

## Predictive-Power Finding

The `e-dispo-v4.0` model has moderate discrimination and coherent apparent calibration in the exported pooled dataset. Its severe-only pain term retains essentially all flexible-pain discrimination while removing the imprecise mild-vs-moderate contrast. Its predictive power is enough to demonstrate endpoint recoding, evidence-gated coefficients, a defensible observed physiologic input, and transparent probability calculation. It is not strong enough to support individual-level clinical action, safety claims, triage claims, or deployment claims.

The exact apparent calibration intercept and slope should be read as an apparent/exported calibration check, not as proof of transportability. The fixed-prediction intervals quantify design-aware apparent metric variability. The bootstrap-refit pass adds internal optimism correction. The full-source NHAMCS screen is an out-of-scope source stress test. None of these establishes external validation or transportability.

## Usability Finding

The active empirical input set remains simple but now requires one numeric vital sign: exact age, severe-vs-non-severe pain status, fever/temperature proxy, vomiting, and observed HR. The HR rule is understandable in the UI because values at or below 100 contribute zero and each 10 bpm above 100 adds one tachycardia-burden unit.

Current usability limitations:

- The UI still displays excluded prototype controls. They are labeled as excluded, but users may still expect them to affect the empirical probability.
- Pain missingness was removed from the active model by requiring observed pain; the app should not silently treat missing pain as non-severe.
- Missing HR blocks the `e-dispo-v4.0` empirical estimate because NHAMCS missing HR is not normal HR.
- Unknown fever or vomiting does not activate the empirical yes coefficient. Unknown should not be interpreted as confirmed absence.
- AAP-3 is useful as an explanatory acuity proxy, but it is not dataset-derived and does not change P(admit).
- NHAMCS has one `PULSE` value, so tachycardia duration is not feasible in this source.
- The model applies only after the strict scope and endpoint rules. It is not designed for patients outside the narrow adult male, non-traumatic abdominal pain cohort.

## Recommended Next Work

1. Keep excluded prototype controls visually separated from the empirical input set.
2. Review the new grouped calibration tables, plot data, AUROC/Brier apparent intervals, full-source scope screens, and 200-refit optimism-corrected internal estimates.
3. Add subgroup interval estimates where event counts and survey design support them.
4. Build an adequate source-specific validation cohort before making any external-validation or transportability claim.
5. Validate AAP-3 against NHAMCS `IMMEDR` or MIMIC-IV-ED triage acuity before allowing it to affect risk.
6. Treat tachycardia duration as a later MIMIC-only question that requires timestamp-preserving vital-sign extraction.
