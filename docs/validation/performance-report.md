# Pooled Empirical Model Performance Report

This report summarizes the active reduced empirical model implemented as `e-dispo-v4.1-pas5-high-acuity-surrogate`.

The model is for educational/statistical use only. It is not clinical decision support, medical advice, a triage tool, or a discharge-safety tool.

## Public Build Split

The active app workstream now supports two separate static builds from the same codebase:

- `npm run build:v4` writes `dist/e-dispo-v4-demo/` for the current E-Dispo abdominal-pain app behavior.
- `npm run build:general` writes `dist/general-e-dispo-demo/` for the separate home-facing `general-E-Dispo-home-v1` all-sex/all-age non-trauma demo. A supplied measured SBP selects `general-E-Dispo-home-v1-measured-sbp`.
- `npm run build:all-sites` writes both outputs.

The public general demo is parallel. It is not a replacement for the abdominal-pain model and does not establish clinical use, external validation, transportability, or medical advice. Transfer-in context is not exposed in the public general demo, and SBP is optional because it must be measured rather than guessed.

## Model Status

- Model ID: `e-dispo-v4.1-pas5-high-acuity-surrogate`
- Dataset: `NHAMCS_2018_2022_POOLED`
- Endpoint: same-hospital admission vs routine home discharge after exclusions
- Population: adult men ages 18-64, ED, non-traumatic abdominal pain
- Empirical activation: active for educational use after app-side export validation
- Formula: `admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden + high_acuity_proxy`
- Age transformation: `age_centered = age - 42`
- Tachycardia transformation: `tachycardia_burden = max(HR - 100, 0) / 10`
- Pain transformation: `pain_severe = 1[pain_bin3 == severe]`; mild and moderate are collapsed as non-severe.
- PAS-5 transformation: `high_acuity_proxy = 1` when PAS-5 maps to A1/A2; PAS-5 A3/A4/A5 are reference.
- Pain monotonicity verdict: `nonmonotonic_collapsed_to_severe_binary`
- Missingness handling: observed pain and observed HR are required; HR missing is not treated as normal.
- Surrogate limitation: NHAMCS does not contain direct PAS-5 patient answers; `high_acuity_proxy` is fitted from `IMMEDR` as a clinician-acuity surrogate.

## Cohort Snapshot

- PAS-5/IMMEDR complete-case unweighted N for `e-dispo-v4.1` fit: 2,245
- Admission events in complete-case `e-dispo-v4.1` fit: 254
- Full strict binary pooled NHAMCS N before complete-case restriction: 3,805
- Full strict binary pooled NHAMCS admission events before complete-case restriction: 459
- Event-count gate: passed

## Apparent Performance

- AUROC/C-statistic: 0.759077823237526
- Brier score: 0.091311819980443
- Observed prevalence: 11.3520799110049%
- Mean predicted probability: 11.3520799126063%
- Calibration intercept: approximately 0.000
- Calibration slope: approximately 1.000

## PAS-5 v4.1 Surrogate Artifacts

The 2026-05-04 PAS-5 screen was rerun deterministically and wrote the active v4.1 artifact set:

- `outputs/nhamcs_pooled/pas5_acuity_mapping.csv`
- `outputs/nhamcs_pooled/pas5_acuity_missingness.csv`
- `outputs/nhamcs_pooled/pas5_acuity_cell_counts.csv`
- `outputs/nhamcs_pooled/pas5_acuity_coefficients.csv`
- `outputs/nhamcs_pooled/pas5_acuity_covariance.csv`
- `outputs/nhamcs_pooled/pas5_acuity_draws_app.csv`
- `outputs/nhamcs_pooled/pas5_acuity_draws_long.csv`
- `outputs/nhamcs_pooled/pas5_acuity_calibration.csv`
- `outputs/nhamcs_pooled/pas5_acuity_decile_calibration.csv`
- `outputs/nhamcs_pooled/pas5_acuity_leave_one_year_out.csv`
- `outputs/nhamcs_pooled/pas5_acuity_gate_decision.csv`
- `outputs/nhamcs_pooled/pas5_acuity_report.md`

The high-acuity proxy cell had n=163, 53 events, and 110 non-events. The fitted high-acuity coefficient was 1.24984421126593 (SE 0.315343146380296; OR 3.48979924370436; 95% CI 1.88093998584976 to 6.47479390782237). The same-subset base refit had AUROC 0.736367002137274 and Brier 0.093767198895187. The v4.1 candidate improved mean leave-one-year-out AUROC by 0.0195420688224538 and Brier by -0.00224960097683449; the 2018 heldout year worsened, so year-level stability remains imperfect.

This does not validate PAS-5 as direct patient self-assessment accuracy. The app-visible PAS-5 answers are bridged to the NHAMCS `IMMEDR` clinician-acuity surrogate because NHAMCS does not observe the direct patient answers.

## Reviewer Calibration And Interval Artifacts

The 2026-05-03 reviewer artifact pass added grouped calibration, apparent-performance interval, subgroup, missingness, optimism-correction, transportability-blocker, candidate-gate, and full-source NHAMCS scope-screen outputs for the historical v4.0 model. Those remain archived support rather than the active v4.1 PAS-5 draw source:

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
- `docs/validation/calibration-performance-interval-artifact-pass.md`
- `docs/validation/full-source-scope-screen.md`
- `docs/validation/full-source-nontrauma-admit-candidate.md`
- `docs/validation/general-e-dispo-model-v1.md`
- `docs/validation/general-e-dispo-home-v1.md`

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

The 2026-05-03 full-source screen applies the fixed predecessor `e-dispo-v4.0` coefficients to broader NHAMCS strict-binary endpoint cohorts. It does not refit the model, does not change coefficients, and does not promote a broader population claim. It remains archived support rather than the current v4.1 PAS-5/IMMEDR validation result.

| Screen | Strict-binary N | Events | Model-estimable N | Model-estimable events | AUROC | Brier | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| Endpoint-only full ED | 77,031 | 10,139 | 44,668 | 5,429 | 0.743845 | 0.097487 | `source_screen` |
| Non-trauma sensitivity | 50,070 | 7,447 | 29,096 | 4,035 | 0.745550 | 0.108448 | `source_screen` |

The endpoint-only full ED screen removes age, sex, abdominal-pain, and trauma filters while retaining the strict same-hospital admission versus routine home discharge endpoint exclusions. The non-trauma sensitivity keeps the same broader population but retains the non-trauma restriction. Both screens include scope flags for active-scope membership, adult male age 18-64 membership, full age band, sex, abdominal-pain RFV flag, non-trauma flag, and active predictor availability.

These rows are out-of-scope NHAMCS source/generalization screens. They are useful for seeing how the fixed educational model behaves when applied beyond its fitted population, but they are not external validation, transportability evidence, clinical validation, or a basis to use the model outside the adult male non-traumatic abdominal-pain cohort.

## Full-Source Non-Trauma Candidate Track

The 2026-05-03 candidate track adds a separate broader NHAMCS non-trauma development model, `e-dispo-v4.1-full-source-nontrauma-admit`. This candidate is not male-only: it removes the active model's sex, age, and abdominal-pain gates while retaining the non-trauma restriction. The model is labeled `survey_weighted_candidate`; it does not replace active `e-dispo-v4.1-pas5-high-acuity-surrogate` and is not used by the GitHub Pages app.

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

The 2026-05-04 pass adds `general-E-Dispo-model-v1`, a separate all-sex/all-age NHAMCS non-trauma educational/statistical model artifact. This model is not the active app model and is not a candidate replacement for `e-dispo-v4.1-pas5-high-acuity-surrogate` in this pass.

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

The source-scope general and plus-sex artifacts remain internal NHAMCS evidence. They are not external validation, not transportability evidence, not clinical validation, and not the public home-facing model branch.

## Home-Facing Public General Demo

The 2026-05-04 home-facing revision adds two public general model IDs:

- `general-E-Dispo-home-v1`
- `general-E-Dispo-home-v1-measured-sbp`

The public default formula removes `arrival_transfer_context` and uses PAS-5 `high_acuity_proxy` rather than a raw acuity dropdown. NHAMCS `IMMEDR` is only the surrogate fitting source for PAS-5 because direct PAS-5 answers are not observed:

```text
admit ~ age_centered_40
      + sex
      + high_acuity_proxy
      + fever_or_temp
      + tachycardia_burden
```

The measured-SBP branch is used only when the user supplies an actual measured SBP:

```text
admit ~ age_centered_40
      + sex
      + high_acuity_proxy
      + fever_or_temp
      + tachycardia_burden
      + hypotension_burden
```

Both branches use the all-sex/all-age NHAMCS non-trauma admit-vs-home denominator before complete-case restriction: 50,070 rows and 7,447 admissions.

| Model | Complete-case N | Complete-case events | AUROC | Brier | 95% AUROC interval | 95% Brier interval | Optimism-corrected AUROC | Optimism-corrected Brier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `general-E-Dispo-home-v1` | 32,681 | 4,702 | 0.811803 | 0.101883 | 0.796539 to 0.824578 | 0.094929 to 0.108322 | 0.810300 | 0.102111 |
| `general-E-Dispo-home-v1-measured-sbp` | 29,761 | 4,581 | 0.807020 | 0.107047 | 0.792927 to 0.818820 | 0.099894 to 0.113953 | 0.805531 | 0.107319 |

The measured-SBP branch did not improve AUROC, Brier, optimism-corrected AUROC, or optimism-corrected Brier compared with the no-SBP default. It is retained as an optional measured-vital branch only. SBP must not be guessed.

On the same complete-case cohort, the severe-only pain model had AUROC 0.713095 and Brier 0.097640. The current flexible pain comparator had AUROC 0.713136 and Brier 0.097694; the no-pain comparator had AUROC 0.701754 and Brier 0.098208. Leave-one-year-out mean performance favored severe-only pain over the flexible pain comparator: AUROC 0.705185 vs 0.695440 and Brier 0.098783 vs 0.099243.

The prevalence-only Brier score for the exported observed prevalence is approximately 0.104. The active model Brier score of 0.0976 is an absolute improvement of about 0.006. This is useful signal for a small educational model, but it is not a large error-reduction gain.

## Coefficient Interpretation

Approximate odds ratios from the exported coefficients:

| Term | Beta | Approximate OR | Interpretation boundary |
|---|---:|---:|---|
| `age_centered` | 0.045 | 1.05 per year | Direct age signal inside the narrow adult male cohort. |
| `pain_severe` | 0.556 | 1.74 | Severe vs non-severe pain signal; not a monotonic pain dose response. |
| `fever_or_temp` | 0.994 | 2.70 | Fever/temperature proxy remains positive, with a large standard error. |
| `vomiting_present` | 0.431 | 1.54 | Ordinary vomiting RFV/symptom proxy is active. |
| `tachycardia_burden` | 0.456 | 1.58 per 10 bpm over 100 | Observed HR signal; missing HR blocks the `e-dispo-v4.1` estimate. |
| `high_acuity_proxy` | 1.250 | 3.49 | PAS-5 A1/A2 vs A3/A4/A5, fitted through NHAMCS IMMEDR surrogate evidence. |

## Predictive-Power Finding

The `e-dispo-v4.1-pas5-high-acuity-surrogate` model has moderate discrimination and coherent apparent calibration in the exported pooled PAS-5/IMMEDR complete-case dataset. Adding the high-acuity proxy improved same-subset AUROC and Brier on average, but the source remains internal NHAMCS surrogate evidence with imperfect year-level stability. Its predictive power is enough to demonstrate endpoint recoding, evidence-gated coefficients, surrogate labeling, and transparent probability calculation. It is not strong enough to support individual-level clinical action, safety claims, triage claims, or deployment claims.

The exact apparent calibration intercept and slope should be read as an apparent/exported calibration check, not as proof of transportability. The fixed-prediction intervals quantify design-aware apparent metric variability. The bootstrap-refit pass adds internal optimism correction. The full-source NHAMCS screen is an out-of-scope source stress test. None of these establishes external validation or transportability.

## Usability Finding

The active empirical input set remains simple but now requires one numeric vital sign and a five-question self-report proxy: exact age, severe-vs-non-severe pain status, fever/temperature proxy, vomiting, observed HR, and PAS-5 high-acuity proxy status. The HR rule is understandable in the UI because values at or below 100 contribute zero and each 10 bpm above 100 adds one tachycardia-burden unit. PAS-5 is understandable because only A1/A2 activate the surrogate term.

Current usability limitations:

- The UI still displays excluded prototype controls. They are labeled as excluded, but users may still expect them to affect the empirical probability.
- Pain missingness was removed from the active model by requiring observed pain; the app should not silently treat missing pain as non-severe.
- Missing HR blocks the `e-dispo-v4.1` empirical estimate because NHAMCS missing HR is not normal HR.
- Unknown fever or vomiting does not activate the empirical yes coefficient. Unknown should not be interpreted as confirmed absence.
- PAS-5 is not direct self-acuity validation because direct patient answers are not observed in NHAMCS.
- NHAMCS has one `PULSE` value, so tachycardia duration is not feasible in this source.
- The model applies only after the strict scope and endpoint rules. It is not designed for patients outside the narrow adult male, non-traumatic abdominal pain cohort.

## Recommended Next Work

1. Keep excluded prototype controls visually separated from the empirical input set.
2. Review the PAS-5 v4.1 calibration tables, draw files, gate decision, and leave-one-year-out year-level caveat.
3. Add subgroup interval estimates where event counts and survey design support them.
4. Build an adequate source-specific validation cohort before making any external-validation or transportability claim.
5. Validate PAS-5 in a source with direct patient answers before making direct self-assessment claims.
6. Treat tachycardia duration as a later MIMIC-only question that requires timestamp-preserving vital-sign extraction.
