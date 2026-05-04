# Model Validation Handoff

Date: 2026-05-03

Active model: `e-dispo-v4.0`

This handoff is for model validation review of the current educational ED disposition model for adult men ages 18-64 already in the emergency department with non-traumatic abdominal pain. The model estimates the strict operational endpoint of same-hospital admission versus routine ED discharge home after exclusions.

This model is educational/statistical only. It is not clinical decision support, diagnosis, triage, treatment advice, discharge guidance, medical advice, or a medical device.

## Evidence Map

Primary repo evidence:

- `docs/model-card.md`
- `docs/validation/validation-dossier-readme.md`
- `docs/validation/performance-report.md`
- `docs/validation/calibration-performance-interval-artifact-pass.md`
- `docs/validation/full-source-scope-screen.md`
- `docs/validation/full-source-nontrauma-admit-candidate.md`
- `docs/validation/general-e-dispo-model-v1.md`
- `docs/validation/predictive-power-usability-review.md`
- `docs/validation/empirical-model-development-protocol.md`
- `docs/validation/e-dispo-v4.0-pain-severe-decision.md`
- `docs/validation/probast-ai-risk-table.md`
- `docs/validation/deficiency-review-next-phase.md`
- `src/data/eDispoV4Model.ts`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_coefficients.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_covariance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_draws.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_calibration.csv`
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
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_cell_counts.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_leave_one_year_out.csv`
- `outputs/nhamcs_pooled/analytic_cohort_nhamcs_2018_2022.csv`
- `outputs/nhamcs_pooled/cohort_flow_by_year.csv`
- `outputs/nhamcs_pooled/missingness_by_year_and_endpoint.csv`
- `artifacts/nhamcs/endpoint-audit-2022.csv`
- `artifacts/nhamcs/endpoint-audit-2022.json`
- `output/e-dispo-atRisk-v2.xlsx`

Where a reviewer question cannot be fully answered from the current repo, this handoff marks it as a validation gap.

## 1. Intended Use And Boundaries

### Plain-language explanation

The model is a class-project style educational model. It is meant to show how a narrow ED disposition risk model can be specified, documented, and reviewed. It should not be used to tell a patient, clinician, or hospital what to do.

The intended population is narrow: adult men ages 18-64 who are already in the ED with non-traumatic abdominal pain. The model does not apply to children, women, older adults, trauma cases, people deciding whether to seek care, or general ED patients.

### Technical/statistical detail

The active model is `e-dispo-v4.0`, using the endpoint `same-hospital admission vs routine home discharge after exclusions`. The model card and validation dossier both identify the active fit as a reduced pooled NHAMCS 2018-2022 empirical export for educational use.

The active predictor set is exact age, severe-vs-non-severe pain, fever/temperature proxy, vomiting, and tachycardia burden from observed heart rate. Excluded prototype inputs do not affect empirical `P(admit)`.

Evidence:

- `docs/model-card.md`
- `docs/validation/validation-dossier-readme.md`
- `docs/validation/predictive-power-usability-review.md`

Reviewer action items:

- Confirm every user-facing description keeps the educational-only boundary.
- Reject any wording that implies clinical deployment, diagnosis, triage, treatment, discharge safety, or patient-level action.

## 2. Endpoint Definition

### Plain-language explanation

The model asks only one narrow question: among visits that clearly ended in either same-hospital admission or routine discharge home, how much does this visit resemble the admission group?

Many ED outcomes are intentionally excluded. Transfers, observation-discharge, death, AMA/LWBS/LBTC/elopement, unknown outcomes, and conflicting records are not treated as either admission or routine discharge.

### Technical/statistical detail

Primary positive endpoint:

```text
admit = same-hospital hospitalization/admission
```

This includes direct same-hospital admission and observation followed by hospitalization when documented.

Primary negative endpoint:

```text
routine_home_discharge = routine ED discharge home
```

Excluded before binary denominator construction:

- observation-only
- observation-discharge
- transfer
- death/expired/DOA/died in ED
- AMA
- LWBS/LBTC/eloped
- other disposition
- unknown, missing, unavailable disposition
- conflicting terminal disposition flags

The complement rule is valid only after endpoint restriction:

```text
P(routine_home_discharge) = 1 - P(admit)
```

The historical NHAMCS 2022 endpoint audit records primary admit, primary routine home discharge, excluded categories, and weighted counts. The pooled model uses the same strict endpoint concept.

Evidence:

- `docs/model-card.md`
- `docs/endpoint-refinement-decision-log.md`
- `docs/validation/empirical-model-development-protocol.md`
- `artifacts/nhamcs/endpoint-audit-2022.csv`
- `artifacts/nhamcs/endpoint-audit-2022.json`

Reviewer action items:

- Verify all endpoint mappings against the NHAMCS codebook before stronger empirical claims.
- Confirm the workbook and app never apply the complement rule outside the strict binary endpoint frame.

## 3. Data And Cohort Construction

### Plain-language explanation

The current active model is based on pooled NHAMCS ED records from 2018-2022. The raw NHAMCS data are not bundled in the app or committed to the repo. The repo contains derived outputs, validation reports, and scripts that document how the cohort was built.

The reviewer should distinguish the current pooled `e-dispo-v4.0` model from the older NHAMCS 2022 baseline. The older baseline is still useful as an audit artifact, but it is not the current active model.

### Technical/statistical detail

Current active pooled model snapshot from the performance report:

| Quantity | Value |
|---|---:|
| Complete-case unweighted N for `e-dispo-v4.0` fit | 2,674 |
| Admission events in complete-case fit | 307 |
| Full strict binary pooled NHAMCS N before complete-case restriction | 3,805 |
| Full strict binary pooled NHAMCS admission events before complete-case restriction | 459 |
| Weighted admission prevalence in strict binary pooled NHAMCS artifact | 0.12448514982051484 |

Historical NHAMCS 2022 baseline snapshot from `version-manifest.md`:

| Step or count | Value |
|---|---:|
| All NHAMCS ED records | 16,025 |
| Male records | 8,465 |
| Male age 18-64 | 5,066 |
| Abdominal pain RFV proxy | 840 |
| Strict non-trauma proxy | 721 |
| Primary binary endpoint records before missing predictor exclusions | 660 |
| Reduced fit sample after pain-scale availability | 469 |
| Primary admit records | 87 |
| Primary routine home discharge records | 573 |
| Primary excluded records | 61 |

Historical 2022 weighted endpoint counts:

| Endpoint class | Weighted count |
|---|---:|
| Primary admit | 855,661.188 |
| Primary routine home discharge | 5,599,557.5 |
| Primary excluded | 490,441.344 |

Current pooled output files present in the repo include:

- `outputs/nhamcs_pooled/analytic_cohort_nhamcs_2018_2022.csv`
- `outputs/nhamcs_pooled/cohort_flow_by_year.csv`
- `outputs/nhamcs_pooled/missingness_by_year_and_endpoint.csv`
- `outputs/nhamcs_pooled/pooled_cohort_metadata.json`

Evidence:

- `docs/validation/performance-report.md`
- `docs/validation/version-manifest.md`
- `docs/validation/validation-dossier-readme.md`
- `outputs/nhamcs_pooled/`

Reviewer action items:

- Confirm whether the reviewer packet should include raw-data access instructions. Raw data should remain out of source control.
- Review `cohort_flow_by_year.csv` and `pooled_cohort_metadata.json` before accepting the pooled cohort as reproducible.

## 4. Predictor Mapping

### Plain-language explanation

The current model uses only five inputs because those are the inputs that the data pipeline currently supports well enough for the educational empirical model. Other inputs may appear in related app or worksheet materials, but they are not active model inputs.

Pain is not treated as a smooth severity ladder. The model only asks whether pain is severe or not severe. Mild and moderate pain are grouped together as non-severe.

### Technical/statistical detail

Active `e-dispo-v4.0` predictors:

| Predictor | Transformation | Notes |
|---|---|---|
| Age | `age_centered = age - 42` | Exact age inside adult male 18-64 cohort. |
| Pain | `pain_severe = 1[pain_bin3 == severe]` | Mild and moderate are non-severe. No monotonic claim. |
| Fever/temp | `fever_or_temp` | Fever or objective temperature proxy. Unknown does not activate yes coefficient. |
| Vomiting | `vomiting_present` | Symptom/proxy-supported active predictor. Unknown does not activate yes coefficient. |
| Heart rate | `tachycardia_burden = max(HR - 100, 0) / 10` | Observed HR required; missing HR is not normal HR. |

Excluded or non-active prototype concepts include broad pain region, onset/duration, pain pattern, hematemesis, nausea-alone, acuity, SBP, AAP-3, and tachycardia duration. AAP-3 is explanatory only and remains `prototype_acuity_proxy`.

Pain representation decision:

- Severe-only pain AUROC/Brier: 0.713095 / 0.097640.
- Flexible `pain_bin3` comparator AUROC/Brier: 0.713136 / 0.097694.
- No-pain comparator AUROC/Brier: 0.701754 / 0.098208.
- Severe-only pain coefficient: beta 0.522, SE 0.184, OR 1.69, p=0.0048.
- The unadjusted pain pattern is nonmonotonic, so mild/moderate/severe dose-response language is prohibited.

Evidence:

- `docs/model-card.md`
- `docs/validation/e-dispo-v4.0-pain-severe-decision.md`
- `docs/validation/predictive-power-usability-review.md`
- `docs/validation/predictor-mapping-lock.md`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_cell_counts.csv`

Reviewer action items:

- Confirm the fever/temp and vomiting proxies are acceptable for educational use.
- Confirm excluded worksheet inputs are visually and textually separated from active empirical predictors.

## 5. Model Specification

### Plain-language explanation

The model is a logistic regression. It adds up the weighted contribution of each input to produce a log-odds value, then converts that log-odds value into a probability.

The workbook also has a stochastic version for @RISK. In that version, coefficients are sampled from their uncertainty distributions so reviewers can inspect uncertainty around the model output.

### Technical/statistical detail

Formula:

```text
logit(P(admit)) =
  intercept
  + beta_age_centered * age_centered
  + beta_pain_severe * pain_severe
  + beta_fever_or_temp * fever_or_temp
  + beta_vomiting_present * vomiting_present
  + beta_tachycardia_burden * tachycardia_burden

P(admit) = 1 / (1 + EXP(-logit))
```

Current exported coefficients:

| Term | Beta | SE/SD | Evidence tier |
|---|---:|---:|---|
| `intercept` | -2.5279874917 | 0.1843311883 | `dataset_derived` |
| `age_centered` | 0.0431187878 | 0.0071464503 | `dataset_derived` |
| `pain_severe` | 0.5218188180 | 0.1839432890 | `dataset_derived` |
| `fever_or_temp` | 0.8870420313 | 0.7464334686 | `dataset_derived` |
| `vomiting_present` | 0.4691225797 | 0.1828017370 | `dataset_derived` |
| `tachycardia_burden` | 0.4269432162 | 0.1121627597 | `dataset_derived` |

Uncertainty files:

- Covariance matrix path in artifact: `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_covariance.csv`
- Draws path in artifact: `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_draws.csv`

The workbook `output/e-dispo-atRisk-v2.xlsx` uses live @RISK functions on the `Model` sheet and keeps deterministic audit-only formulas on `Audit`. The @RISK workbook uses normal approximations centered on the exported coefficients with the exported SE/SD values.

Evidence:

- `src/data/eDispoV4Model.ts`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_coefficients.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_covariance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_draws.csv`
- `output/e-dispo-atRisk-v2.xlsx`

Reviewer action items:

- Review whether @RISK should use the full covariance structure rather than independent normal coefficient draws.
- Confirm whether the current SE/SD values are design-aware enough for the validation purpose; the repo flags survey-design variance as a remaining gap.

## 6. Performance And Calibration

### Plain-language explanation

The model has real but limited predictive signal. It ranks visits better than chance, but it is not strong enough for patient-level clinical use. Its probability error is only modestly better than predicting the overall admission rate for everyone.

The calibration numbers are internally coherent for the exported pooled dataset, but they do not prove that the model will work in another hospital, another dataset, or a real clinical workflow.

### Technical/statistical detail

Active `e-dispo-v4.0` apparent performance:

| Metric | Value |
|---|---:|
| AUROC | 0.7130954172 |
| Brier score | 0.0976402591 |
| Observed prevalence | 0.1175465174 |
| Mean predicted probability | 0.1175465174 |
| Calibration intercept | 0.0000000072 |
| Calibration slope | 1.0000000000 |

Reviewer-facing calibration/performance artifact pass added on 2026-05-03:

| Artifact | Method | Current result |
|---|---|---|
| `e_dispo_v4_pain_severe_calibration_by_decile.csv` | Weighted predicted-probability deciles; survey-weighted observed rate with Taylor-linearized interval | 10 active-model decile rows |
| `e_dispo_v4_pain_severe_calibration_plot_data.csv` | Plot-ready decile means plus identity-line coordinates | 10 active-model plot rows |
| `e_dispo_v4_pain_severe_performance_intervals.csv` | 1,000 `survey::as.svrepdesign(..., type = "bootstrap")` replicate weights over pooled NHAMCS strata/PSUs, fixed apparent predictions | AUROC 0.713095, 95% interval 0.670617 to 0.757748; Brier 0.097640, 95% interval 0.084632 to 0.111066 |
| `e_dispo_v4_subgroup_performance.csv` | Active prediction summaries by subgroup/proxy availability; blocker rows when fields are sparse or active model cannot estimate | Age-band, predictor/proxy-availability, race/ethnicity, payer, region, and MSA rows; small payer levels have sparse/no-outcome blockers |
| `e_dispo_v4_subgroup_calibration.csv` | Within-subgroup predicted-probability deciles where estimable | Age-band and availability calibration rows for reviewer plotting |
| `e_dispo_v4_missingness_performance.csv` | Active prediction summaries by pain, HR, fever/temp, and vomiting-proxy availability | Missing/observed availability rows with model-estimability status |
| `e_dispo_v4_optimism_corrected_performance.csv` | 200 survey-bootstrap refits of the active formula, optimism estimated from bootstrap-test metric differences | AUROC 0.704894; Brier 0.099565; calibration-in-the-large 0.012975; calibration slope 0.954089 after optimism correction |
| `e_dispo_v4_transportability_track.csv` | NHAMCS coefficients applied to available MIMIC-IV-ED compatible rows only as a source-specific screen | `blocked_sparse_replication_only`; no transportability claim |
| `e_dispo_v4_candidate_refinement_gate.csv` | Prespecified blocker/gate table for proposed refinements | No candidate promoted |
| `e_dispo_v4_full_source_endpoint_screen_performance.csv` | Fixed active coefficients scored on all NHAMCS strict-binary ED records, removing age, sex, abdominal-pain, and trauma filters | 77,031 strict-binary rows; 44,668 model-estimable rows; AUROC 0.743845; Brier 0.097487; source-scope screen only |
| `e_dispo_v4_full_source_nontrauma_screen_performance.csv` | Fixed active coefficients scored on strict-binary non-trauma ED records, removing age, sex, and abdominal-pain filters | 50,070 strict-binary rows; 29,096 model-estimable rows; AUROC 0.745550; Brier 0.108448; source-scope screen only |
| `full_source_nontrauma_admit_model_performance.csv` | Separate broader all-sex/all-age non-trauma candidate model fit using the compact active-model predictor surface | 50,070 admit-vs-home rows; 29,096 complete-case rows; AUROC 0.757181; Brier 0.105462; `survey_weighted_candidate`, not active app model |
| `full_source_nontrauma_*_variable_correlations.csv` | Analytic and raw public-use variable association screens for admit-vs-home and transfer-vs-home | Every screened variable has an ok, excluded, or blocker row; transfer is report-only and not combined into the admit model |
| `general_e_dispo_model_v1_performance.csv` | Parallel all-sex/all-age non-trauma model artifact using age, acuity, arrival-transfer context, fever/temp, tachycardia burden, and hypotension burden | 50,070 admit-vs-home rows; 42,300 complete-case rows; AUROC 0.817657; Brier 0.104806; `survey_weighted_parallel_model`, not active app model |
| `general_e_dispo_model_v1_performance_intervals.csv` | 1,000 survey-bootstrap replicate weights over pooled NHAMCS strata/PSUs, fixed apparent predictions | AUROC 0.817657, 95% interval 0.806684 to 0.827352; Brier 0.104806, 95% interval 0.099189 to 0.110763 |
| `general_e_dispo_model_v1_optimism_corrected_performance.csv` | 200 survey-bootstrap refits of the general formula | Optimism-corrected AUROC 0.815737; Brier 0.105250; calibration-in-the-large -0.002014; calibration slope 0.987855 |
| `general_e_dispo_model_v1_plus_sex_performance.csv` | Prespecified plus-sex sensitivity model for the parallel general model; categorical sex main effect only | Same denominator and complete case as base general model; AUROC 0.818263; Brier 0.104635; `survey_weighted_parallel_sensitivity_model`, not active app model |
| `general_e_dispo_model_v1_plus_sex_performance_intervals.csv` | 1,000 survey-bootstrap replicate weights over pooled NHAMCS strata/PSUs, fixed apparent predictions | AUROC 0.818263, 95% interval 0.808518 to 0.828209; Brier 0.104635, 95% interval 0.099073 to 0.110226 |
| `general_e_dispo_model_v1_sex_sensitivity_comparison.csv` | Base-vs-plus-sex comparison for apparent and optimism-corrected metrics | Apparent AUROC +0.000606; apparent Brier -0.000171; optimism-corrected AUROC +0.000317; optimism-corrected Brier +0.000174; max absolute sex calibration gap 0.012625 to approximately 0.000000 |

The 1,000-replicate AUROC/Brier intervals describe design-aware apparent metric variability for the fitted model surface. They do not refit the model inside each replicate, correct optimism, validate externally, or prove transportability. The 200-refit optimism-corrected rows are internal validation only and also do not prove transportability. The full-source NHAMCS scope screens are out-of-scope source stress tests because they remain in NHAMCS and score rows outside the active fitted population by extrapolation.

The full-source non-trauma candidate track is separate from the active model. It fits `e-dispo-v4.1-full-source-nontrauma-admit` on the broader all-sex/all-age non-trauma NHAMCS source cohort with the same compact predictor surface for comparability. The admit-vs-home denominator contains sex code 1 rows (28,185) and sex code 2 rows (21,885); the original adult-male age 18-64 flag is retained for review but is not used as a gate. Coefficients are labeled `survey_weighted_candidate`, not `dataset_derived`, and no app-side active model changes are made. The companion transfer screen uses `transfer` versus routine home discharge only for reporting; transfer is not combined with admission.

`general-E-Dispo-model-v1` is a newer parallel clean pre-disposition general non-trauma artifact. It uses the same all-sex/all-age non-trauma denominator but replaces the compact abdominal-pain-style predictor surface with age centered at 40, NHAMCS `IMMEDR` acuity, NHAMCS `AMBTRANSFER` arrival-transfer context, fever/temp, tachycardia burden, and hypotension burden. Payer, sex, race/ethnicity, region, and MSA are subgroup/fairness fields only and are not in the fitted base formula. This track is also not active app behavior and does not broaden `e-dispo-v4.0`.

`general-E-Dispo-model-v1-plus-sex` is a prespecified sensitivity artifact, not a replacement. It adds sex as a categorical main effect to test residual sex calibration. The result is mixed: sex removes the apparent NHAMCS sex subgroup calibration gap, but the overall metric gain is tiny and optimism-corrected Brier is slightly worse. Current conclusion: keep the artifact, do not promote sex into the primary clean general model without later fairness review and source-specific validation.

Comparator performance:

| Model | AUROC | Brier |
|---|---:|---:|
| No pain comparator | 0.701754 | 0.098208 |
| Severe-only pain | 0.713095 | 0.097640 |
| Flexible `pain_bin3` comparator | 0.713136 | 0.097694 |

Leave-one-year-out mean performance favors severe-only pain over flexible pain:

| Model | Mean AUROC | Mean Brier |
|---|---:|---:|
| Severe-only pain | 0.705185 | 0.098783 |
| Flexible pain | 0.695440 | 0.099243 |

The performance report estimates the prevalence-only Brier score around 0.104, so the active model improves Brier by about 0.006 in absolute terms.

Evidence:

- `docs/validation/performance-report.md`
- `docs/validation/predictive-power-usability-review.md`
- `docs/validation/e-dispo-v4.0-pain-severe-decision.md`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_calibration.csv`
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
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_nontrauma_screen_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_scope_screen_report.md`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_leave_one_year_out.csv`

Reviewer action items:

- Review the fixed-prediction AUROC/Brier intervals and the separate 200-refit optimism-corrected internal estimates before accepting the reviewer packet.
- Use the grouped calibration, subgroup calibration, full-source scope-screen, and plot-data artifacts in the review packet.
- Treat all calibration/performance evidence as apparent/internal unless adequate external or source-specific validation is completed.

## 7. Missingness, Sensitivity, And Subgroups

### Plain-language explanation

The model does not guess missing pain or missing heart rate. If pain or heart rate is not observed, the empirical estimate should be withheld rather than treating missing information as normal or non-severe.

Sensitivity endpoints exist for review, but they are not the active model. The current pass adds age-band, predictor/proxy-availability, race/ethnicity, payer, region, and MSA subgroup rows.

### Technical/statistical detail

Current missingness behavior:

- Observed pain is required for `e-dispo-v4.0`.
- Observed HR is required for `e-dispo-v4.0`.
- Missing HR is not normal HR.
- Missing pain is not non-severe pain.
- Unknown fever/vomiting does not activate the yes coefficient and should not be described as confirmed absence.

Files present for missingness, sensitivity, and subgroup review:

- `outputs/nhamcs_pooled/missingness_by_year_and_endpoint.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_missingness_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_subgroup_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_subgroup_calibration.csv`
- `docs/validation/sensitivity-report.md`
- `outputs/nhamcs_pooled/nausea_missingness_by_endpoint.csv`

Current subgroup and missingness status:

- Age-band, pain-availability, HR-availability, fever/temp-availability, vomiting-proxy-availability, race/ethnicity, payer, region, and MSA rows are reported where the active model can estimate predictions.
- Small payer levels can remain explicit sparse-cell or no-outcome-variation blockers.
- Full subgroup interval estimation remains a gap.
- External validation has not been performed.
- Full-source NHAMCS endpoint-only and non-trauma screens have been performed, but they are source-scope stress tests and do not broaden the intended-use population.
- A separate full-source non-trauma admit candidate fit and analytic/raw variable screen exist for development review only; they do not broaden active `e-dispo-v4.0`.
- `general-E-Dispo-model-v1` subgroup and missingness artifacts exist for the parallel general non-trauma model; they are internal NHAMCS reviewer artifacts only and not active app evidence.
- `general-E-Dispo-model-v1-plus-sex` exists only as a prespecified sensitivity artifact. It is not promoted because the overall performance gain is tiny and optimism-corrected Brier is slightly worse despite better sex subgroup calibration.
- Tachycardia duration is not feasible in NHAMCS because the source has one `PULSE` value.

Evidence:

- `docs/model-card.md`
- `docs/validation/deficiency-review-next-phase.md`
- `docs/validation/probast-ai-risk-table.md`
- `docs/validation/predictive-power-usability-review.md`
- `outputs/nhamcs_pooled/missingness_by_year_and_endpoint.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_missingness_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_subgroup_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_subgroup_calibration.csv`

Reviewer action items:

- Review missingness/performance rows before accepting complete-case restrictions.
- Decide whether subgroup interval estimation is required for race/ethnicity, payer, region, and MSA rows with adequate event support.
- Confirm sensitivity endpoints remain report-only.

## 8. Workbook / Implementation Validation

### Plain-language explanation

The simplified Excel workbook is designed so reviewers see the stochastic @RISK model as the model surface. Deterministic point-estimate numbers are kept on the `Audit` sheet so they do not sit next to the stochastic model and confuse reviewers.

When @RISK is not loaded, live @RISK formulas can show add-in errors. That is expected in local inspection outside Excel with @RISK. The reviewer should open the workbook in Excel with @RISK loaded to run the simulation.

### Technical/statistical detail

Workbook artifact:

```text
output/e-dispo-atRisk-v2.xlsx
```

Workbook structure:

| Sheet | Purpose |
|---|---|
| `Model` | Live stochastic @RISK formulas and user inputs. |
| `Assumptions` | Coefficients, SE/SDs, recoding constants, source notes. |
| `Audit` | Deterministic audit-only calculations and formula checks. |

Implementation conventions:

- `Model` contains live `RiskNormal`, `RiskOutput`, `RiskMean`, `RiskPercentile`, and `RiskStdDev` formulas.
- `Audit` contains deterministic logistic calculations and checks for coefficient matching, sign logic, complement rule, and expected @RISK add-in behavior.
- Deterministic audit values are not presented as stochastic results.
- Simulation settings documented in workbook: seed 20260428 and 100,000 iterations.

Evidence:

- `output/e-dispo-atRisk-v2.xlsx`
- `ed-disposition-web-v3/output/excel_workbook_build/build_e_dispo_atrisk_v2.mjs`
- `src/data/eDispoV4Model.ts`

Reviewer action items:

- Open the workbook with @RISK loaded and confirm formulas resolve.
- Confirm the @RISK model uses the desired coefficient uncertainty structure.
- Confirm the deterministic audit values are treated as audit checks only.

## 9. Limitations And Claims Review

### Plain-language explanation

The model is useful as an educational example of how to define an endpoint, map predictors, fit a simple model, and document limitations. It is not validated for medical use.

The biggest remaining issues are not cosmetic. They are validation issues: survey design, missingness, subgroup performance, transportability, and external validation.

### Technical/statistical detail

Current documented limitations:

- No clinical validity claim.
- No external validation or transportability proof outside pooled NHAMCS.
- Full-source NHAMCS endpoint-only and non-trauma screens exist, but they are source-scope stress tests and out-of-scope extrapolations, not broader validation.
- A broader full-source non-trauma candidate model and variable-correlation screen exist, but they are development artifacts only and not an active model update.
- `general-E-Dispo-model-v1` exists as a cleaner parallel all-sex/all-age non-trauma educational/statistical artifact, not an active model update or external validation result. The plus-sex sensitivity artifact is documented but not promoted.
- Moderate discrimination only.
- Small Brier improvement over prevalence-only prediction.
- Design-aware apparent AUROC/Brier intervals and internal optimism correction exist, but no external validation exists.
- Fever/vomiting are proxy-supported predictors.
- Missing pain and missing HR withhold the empirical estimate.
- AAP-3 is `prototype_acuity_proxy` only.
- Tachycardia duration is not feasible in NHAMCS.
- Pain is severe vs non-severe only; no monotonic mild/moderate/severe claim is supported.

PROBAST-style concerns in the repo:

| Domain | Current concern |
|---|---|
| Participants | Narrow adult male non-traumatic abdominal-pain cohort. |
| Predictors | Active model uses reduced evidence-gated predictors; other worksheet inputs remain excluded. |
| Outcome | Endpoint recoding is explicit but depends on correct flag interpretation. |
| Analysis | Reduced fit exists, and the full-source non-trauma candidate/general tracks are clearly separated from the active model; survey-design methods still need extension to subgroup intervals and future candidate comparisons. |
| Performance | Apparent, fixed-prediction interval, grouped calibration, subgroup/missingness, full-source NHAMCS source-scope screens, full-source non-trauma candidate diagnostics, `general-E-Dispo-model-v1` diagnostics, plus-sex sensitivity diagnostics, and optimism-corrected internal checks exist; external validation remains needed. |
| Applicability | Educational-only; not patient care. |
| Fairness | Age/proxy-availability, race/ethnicity, payer, region, and MSA subgroup rows exist; sparse payer levels remain blocked where support is inadequate. |

Evidence:

- `docs/validation/probast-ai-risk-table.md`
- `docs/validation/deficiency-review-next-phase.md`
- `docs/validation/predictive-power-usability-review.md`
- `docs/model-card.md`

Reviewer action items:

- Confirm that the model remains appropriate only for course/educational demonstration.
- Require adequate external/source-specific validation before any stronger claim.
- Require subgroup interval estimation and adequate source-specific validation before broader subgroup language.
- Keep design-aware fixed-prediction intervals and optimism-corrected internal validation separate in reviewer language.

## Reviewer Decision Log Template

Use this section during review.

| Decision area | Reviewer decision | Notes |
|---|---|---|
| Educational-use boundary accepted? |  |  |
| Endpoint recoding accepted? |  |  |
| Cohort construction reproducible enough? |  |  |
| Predictor mapping accepted? |  |  |
| Coefficient and uncertainty export accepted? |  |  |
| Performance adequate for education only? |  |  |
| Missingness handling acceptable? |  |  |
| Workbook implementation acceptable? |  |  |
| Claims and limitations acceptable? |  |  |

## Bottom Line For Reviewer

The repo supports `e-dispo-v4.0` as a bounded educational empirical model with moderate apparent predictive signal and clear limitations. It does not support clinical deployment, patient-level action, external validation, or broad generalization. The 2026-05-03 pass adds grouped calibration, design-aware apparent AUROC/Brier intervals, missingness/subgroup rows including race/ethnicity, payer, region, and MSA, 200-refit optimism-corrected internal estimates, full-source NHAMCS source-scope screens, a separate full-source non-trauma candidate model and analytic/raw variable screen, a sparse MIMIC-IV-ED blocker, and candidate-refinement blocker rows. The 2026-05-04 pass adds `general-E-Dispo-model-v1` as a parallel clean pre-disposition all-sex/all-age non-trauma model artifact with its own coefficients, covariance, grouped calibration, intervals, optimism correction, subgroup, and missingness outputs. The same pass adds `general-E-Dispo-model-v1-plus-sex` as a prespecified sensitivity artifact; it improves sex subgroup calibration but is not promoted because the overall performance gain is negligible and optimism-corrected Brier is slightly worse. The strongest remaining validation needs are adequate source-specific/external validation, subgroup interval estimation where event counts support it, and prespecified leakage-reviewed candidate-model comparison before any replacement model is considered.
