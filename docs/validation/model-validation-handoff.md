# Model Validation Handoff

Date: 2026-05-02

Active model: `e-dispo-v4.0`

This handoff is for model validation review of the current educational ED disposition model for adult men ages 18-64 already in the emergency department with non-traumatic abdominal pain. The model estimates the strict operational endpoint of same-hospital admission versus routine ED discharge home after exclusions.

This model is educational/statistical only. It is not clinical decision support, diagnosis, triage, treatment advice, discharge guidance, medical advice, or a medical device.

## Evidence Map

Primary repo evidence:

- `docs/model-card.md`
- `docs/validation/validation-dossier-readme.md`
- `docs/validation/performance-report.md`
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
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_leave_one_year_out.csv`

Reviewer action items:

- Require confidence intervals or uncertainty intervals for AUROC and Brier before stronger performance claims.
- Add grouped calibration plots/tables to the review packet if not already included in the reviewer package.
- Treat current calibration as apparent/internal unless external validation is completed.

## 7. Missingness, Sensitivity, And Subgroups

### Plain-language explanation

The model does not guess missing pain or missing heart rate. If pain or heart rate is not observed, the empirical estimate should be withheld rather than treating missing information as normal or non-severe.

Sensitivity endpoints exist for review, but they are not the active model. Subgroup and fairness checks are still next-phase work.

### Technical/statistical detail

Current missingness behavior:

- Observed pain is required for `e-dispo-v4.0`.
- Observed HR is required for `e-dispo-v4.0`.
- Missing HR is not normal HR.
- Missing pain is not non-severe pain.
- Unknown fever/vomiting does not activate the yes coefficient and should not be described as confirmed absence.

Files present for missingness and sensitivity review:

- `outputs/nhamcs_pooled/missingness_by_year_and_endpoint.csv`
- `docs/validation/sensitivity-report.md`
- `outputs/nhamcs_pooled/nausea_missingness_by_endpoint.csv`

Known validation gaps from the repo:

- Subgroup/fairness checks by age band, race/ethnicity, payer, region, and proxy availability remain next-phase work.
- External validation has not been performed.
- Full design-aware NHAMCS variance remains a gap.
- Tachycardia duration is not feasible in NHAMCS because the source has one `PULSE` value.

Evidence:

- `docs/model-card.md`
- `docs/validation/deficiency-review-next-phase.md`
- `docs/validation/probast-ai-risk-table.md`
- `docs/validation/predictive-power-usability-review.md`
- `outputs/nhamcs_pooled/missingness_by_year_and_endpoint.csv`

Reviewer action items:

- Review missingness rates by endpoint before accepting complete-case restrictions.
- Decide which subgroup checks are required for the next validation pass.
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
- No external validation.
- No transportability proof outside pooled NHAMCS.
- Moderate discrimination only.
- Small Brier improvement over prevalence-only prediction.
- Full NHAMCS survey-design variance remains incomplete.
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
| Analysis | Reduced fit exists, but survey-design completeness remains a concern. |
| Performance | Apparent and lightweight checks exist; stronger validation remains needed. |
| Applicability | Educational-only; not patient care. |
| Fairness | Subgroup performance is not yet reported. |

Evidence:

- `docs/validation/probast-ai-risk-table.md`
- `docs/validation/deficiency-review-next-phase.md`
- `docs/validation/predictive-power-usability-review.md`
- `docs/model-card.md`

Reviewer action items:

- Confirm that the model remains appropriate only for course/educational demonstration.
- Require external/source-specific validation before any stronger claim.
- Require subgroup and proxy-availability checks before broader applicability language.
- Require design-aware variance and calibration plots before non-exploratory statistical claims.

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

The repo supports `e-dispo-v4.0` as a bounded educational empirical model with moderate apparent predictive signal and clear limitations. It does not support clinical deployment, patient-level action, or broad generalization. The strongest next validation needs are design-aware variance, grouped calibration plots/tables, uncertainty intervals for performance metrics, missingness/subgroup review, and external or source-specific validation.
