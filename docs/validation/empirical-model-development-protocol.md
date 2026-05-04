# Empirical Model Development Protocol

Date: 2026-04-28

Status: empirical development protocol with `e-dispo-v4.1-pas5-high-acuity-surrogate` adopted as the current educational app model. No pain monotonicity claim is made; active pain is severe vs non-severe only. PAS-5 is active only through `high_acuity_proxy`, fitted from NHAMCS `IMMEDR` as clinician-acuity surrogate evidence.

## Execution Readiness Checklist

Do not run, fit, export, or promote an empirical model until these items are complete or a `blocker_report.md` explains why they are blocked.

| Item | Required before fitting | Required evidence |
|---|---|---|
| Code lists | Yes | Version-controlled code-list files for NHAMCS RFV, NHAMCS exclusions, MIMIC chief-complaint regex, MIMIC diagnosis exclusions, vomiting, fever, and pain parsing. |
| Survey design | Yes for NHAMCS | Confirmed patient visit weight, stratum, PSU/cluster, and variance method. |
| Raw data availability | Yes for fitting | Local raw NHAMCS and/or MIMIC source tables, not committed to the repo. |
| Cohort functions | Yes | Tests or smoke outputs proving age/sex/symptom/trauma filters run in order. |
| Endpoint functions | Yes | Endpoint audit tables with conflicts excluded from the binary denominator. |
| Missingness plan | Yes | Missingness-by-endpoint output schema implemented. |
| Sparse-cell rules | Yes | Pre-fit sparse cell report or stop/collapse decision. |
| Deterministic randomness | Yes | Fixed seed recorded for bootstrap, simulation draws, posterior sampling, or split generation. |
| Fitting metadata | Yes | Formula, transformations, reference categories, package versions, seed, and fitting method saved. |
| Pain verdict | Yes if pain is evaluated | `pain_monotonicity.csv` with explicit verdict and reasons. |
| Calibration gate | Yes if fitting succeeds | Calibration metrics and calibration-by-decile outputs. |
| App export gate | Yes for app use | `app_export.json` passes schema validation and all `dataset_derived` gates below. |

## Primary Objective

Fit a transparent logistic ED disposition model for adult men ages 18-64 presenting to the emergency department with non-traumatic abdominal pain.

Primary endpoint:

```text
same-hospital inpatient admission
vs
routine ED discharge home
```

This is an educational/statistical model-development protocol. It is not clinical decision support, medical advice, a triage tool, or a production medical device.

The strict binary endpoint must be constructed only after all exclusions. Exclude observation-only, observation-discharge, transfer, death/expired/DOA, AMA, LWBS, LBTC/eloped, other, unknown, missing, and conflicting dispositions before forming the binary denominator.

Do not use `treat_and_release = 1 - admit` until the strict binary analytic cohort has already been filtered to the two allowed endpoint classes.

The empirical work has three linked goals:

| Goal | Required output |
|---|---|
| Fit documented NHAMCS and MIMIC analytic cohorts | Cohort-flow counts, endpoint counts, missingness tables |
| Estimate coefficients and uncertainty | Beta estimates, standard errors, covariance matrix, bootstrap draws, or posterior draws |
| Test pain severity | Determine whether pain is monotonic, weak, confounded, flexible-only, proxy-only, or unsupported |

NHAMCS is the primary national public derivation and calibration source. MIMIC-IV-ED is the granular replication and proxy-validation source. Do not naively pool NHAMCS and MIMIC coefficients as though they represent the same target population.

## Dataset-Derived Lock

No parameter, coefficient, prior, or app-export value may be labeled `dataset_derived` unless the output package documents all of the following:

1. Analytic cohort definition.
2. Endpoint recoding.
3. Predictor mapping.
4. Unweighted counts and weighted counts where applicable.
5. Cell/event counts.
6. Missingness by endpoint.
7. Fitted coefficient.
8. Standard error, covariance matrix, bootstrap draw, or posterior draw.
9. Calibration diagnostics.

If any item is missing, the value remains `prototype_assumption`, `unsupported`, or blocked. Do not fabricate fitted results when raw data are unavailable.

Surrogate-derived app terms must be labeled `dataset_derived_surrogate`, not ordinary `dataset_derived`. The active example is `high_acuity_proxy`, with `surrogate_source = NHAMCS_IMMEDR` and the limitation that direct PAS-5 patient answers are not observed in NHAMCS.

## Required Output Root

Future empirical scripts should write explicit files under a versioned run directory such as:

```text
outputs/empirical_runs/YYYY-MM-DD_source_model/
```

Each run directory must contain the deliverables listed in the "Deliverable File Schemas" section or a `blocker_report.md` explaining unavailable outputs.

## Cohort Construction

### NHAMCS Primary Cohort

Build the NHAMCS cohort in this exact order:

| Step | Rule | Required output |
|---:|---|---|
| 1 | Start with the selected NHAMCS ED public-use records. | Raw unweighted N and weighted N. |
| 2 | Restrict to male patients age 18-64. | N and weighted N after sex/age filters. |
| 3 | Identify abdominal pain using approved RFV inclusion codes. Build diagnosis-code sensitivity separately. | N and weighted N after complaint filter. |
| 4 | Exclude trauma, injury, poisoning, and adverse-effect presentations. | N and weighted N after exclusion filter. |
| 5 | Recode endpoint flags and detect conflicts. | Admit, routine home discharge, observation, transfer, death, AMA, LWBS/LBTC/eloped, other, unknown/missing, conflict. |
| 6 | Keep only same-hospital admission and routine home discharge. | Final denominator, outcome events, weighted admission prevalence. |

The current repository config uses NHAMCS 2022 RFV codes `15450`, `15451`, `15452`, and `15453` for abdominal pain and `INJPOISAD == 4` as the first-pass strict non-trauma/non-poisoning/non-adverse-effect proxy. Before a new empirical run, confirm these values against the codebook or mark them `TODO-confirm-from-codebook` and fail fitting.

### MIMIC-IV-ED Replication Cohort

Build the MIMIC cohort in parallel:

| Step | Rule | Required output |
|---:|---|---|
| 1 | Start with `edstays`. | Raw ED stay count. |
| 2 | Link age and sex from MIMIC-IV using `subject_id`; restrict to male patients age 18-64. | N after sex/age filters. |
| 3 | Identify abdominal pain using triage chief complaint regex. Build diagnosis sensitivity separately. | N after complaint filter. |
| 4 | Exclude trauma/injury terms and trauma diagnoses. | N after exclusion filter. |
| 5 | Recode endpoint using `disposition` and `hadm_id`. | Endpoint counts and conflicts. |
| 6 | Keep only `ADMITTED` with same-hospital admission linkage and `HOME` without admission linkage. | Final binary N and events. |

MIMIC-IV-ED's `edstays` table provides ED stay-level disposition fields. The `triage` table supports temperature, heart rate, respiratory rate, oxygen saturation, systolic and diastolic blood pressure, pain, acuity, and chief complaint. Use patient-level clustering or subject-level bootstrap because patients can have multiple ED stays.

## Endpoint Conflict Precedence

Conflicts are endpoint evidence, not data-cleaning noise. Default action: exclude conflicting records from the binary denominator and tabulate them in endpoint-audit outputs.

### NHAMCS Conflicts

Mark `endpoint_class = conflict` when any of these conditions occur:

| Conflict rule | Examples |
|---|---|
| More than one mutually exclusive terminal disposition class is active | Admission and routine discharge; transfer and home release. |
| Admission plus an exclusion flag | Admission with transfer, death, AMA, LWBS, observation-discharge, observation-only, or other/unknown. |
| Routine discharge plus an exclusion flag | Home release with admission, transfer, death, AMA, LWBS, observation, other, unknown, or missing terminal disposition. |
| Observation ambiguity | Observation-only or observation-discharge without same-hospital admission documentation. |
| Missing or unknown terminal disposition | No terminal class can be assigned with confidence. |

Death/expired/DOA remains a sentinel exclusion. Do not model death as admission, discharge, or acute escalation in the primary binary endpoint.

### MIMIC-IV-ED Conflicts

Mark `endpoint_class = conflict` when any of these conditions occur:

| Conflict rule | Examples |
|---|---|
| `disposition = HOME` with populated `hadm_id` | Home disposition conflicts with admission linkage. |
| `disposition = ADMITTED` without populated `hadm_id` | Admission disposition lacks same-hospital admission linkage. |
| Missing disposition with populated `hadm_id` | Admission linkage exists but terminal ED disposition is missing. |
| Exclusion disposition with admission linkage | Transfer, expired, AMA, LWBS, eloped, or other with populated `hadm_id`. |
| Multiple conflicting disposition sources | Source tables disagree after harmonization. |

The binary endpoint is valid only after these records are removed and counted.

## Predictor Set

### Current e-dispo-v4.1 Educational Model

Use this as the active educational empirical model only after predictor mapping, sparse-cell, uncertainty, calibration, and leave-one-year-out gates pass:

```text
logit(P(admit)) =
  alpha
  + f_age(age)
  + beta_pain_severe * 1[pain_bin3 == severe]
  + beta_vomit * vomiting
  + beta_temp * temperature_or_fever
  + beta_tachycardia * max(HR - 100, 0) / 10
  + beta_high_acuity_proxy * 1[PAS-5 in A1 or A2]
```

| Predictor | NHAMCS mapping | MIMIC mapping | Status |
|---|---|---|---|
| Age | Exact age; app bands 18-34, 35-49, 50-64; spline sensitivity. | Linked age. | Direct. |
| Pain severity | `PAINSCALE` 0-10; severe vs non-severe after observed mild/moderate/severe bins. | Parsed triage pain; numeric only primary. | Direct; severe-only term active in `e-dispo-v4.1`. |
| Pain missing | Missing/blank/unknown indicator. | Missing/non-numeric pain indicator. | Excluded from active `e-dispo-v4.1`; sensitivity/missingness audit only. |
| Vomiting | RFV/symptom/chief complaint/diagnosis proxy after code-list lock. | Chief-complaint vomiting terms; diagnosis sensitivity. | Proxy-supported only if counts pass. |
| Fever/temperature | Objective temperature preferred; fever RFV/text sensitivity. | Triage temperature preferred; chief-complaint fever sensitivity. | Objective vitals preferred. |
| Tachycardia burden | `PULSE`; `max(HR - 100, 0) / 10`; missing HR remains missing. | Triage/serial heart rate if timestamp-preserving extraction is available. | Active in `e-dispo-v4.1` as observed HR burden; duration is not feasible in NHAMCS. |
| PAS-5 high-acuity proxy | `IMMEDR` 1/2 mapped to high_acuity_proxy; `IMMEDR` 3/4/5 reference. | Direct PAS-5 answers would be preferred; MIMIC acuity is clinician-derived only. | Active in `e-dispo-v4.1` as `dataset_derived_surrogate`; not direct PAS-5 validation. |

Pain severity is measurable, but it is not established as a monotonic admission predictor. The active v4.1 model therefore uses only severe vs non-severe pain and must not be described as a monotonic dose response.

### Future Expanded Development Model

Use this as a future empirical development model only; it is not adopted by this protocol:

```text
logit(P(admit)) =
  alpha
  + f_age(age)
  + beta_acuity * acuity
  + f_pain(pain)
  + beta_temp * temperature_or_fever
  + beta_hr * heart_rate
  + beta_sbp * systolic_blood_pressure
  + beta_vomit * vomiting
```

Broad pain region may be added only if RFV/chief-complaint mapping has adequate counts and validation. Onset/duration and constant/intermittent pain remain excluded from empirical models unless validated NLP extraction is completed.
Pain missingness should remain a missingness audit or sensitivity term unless a future protocol explicitly justifies reintroducing it.

## Code-List Appendices

All code lists and regex mappings must live in version-controlled files before fitting. Recommended location:

```text
config/code_lists/
```

Recommended file shape for each CSV:

```text
source,domain,field,rule_id,match_type,pattern_or_code,include_exclude,normalized_value,notes,codebook_anchor,review_status
```

`review_status` must be one of `confirmed`, `TODO-confirm-from-codebook`, `rejected`, or `sensitivity_only`. Fitting must fail when a primary rule has `TODO-confirm-from-codebook`.

### Appendix A1. NHAMCS Abdominal-Pain RFV Inclusion Codes

Initial repository-configured inclusion list:

| Field | Codes | Action | Status |
|---|---|---|---|
| `RFV1`-`RFV5` | `15450`, `15451`, `15452`, `15453` | Include as abdominal pain RFV primary cohort. | Confirm against selected NHAMCS codebook before fitting. |

The appendix must include exact codebook labels for each code and must state whether upper, lower, generalized, or unspecified abdominal pain distinctions are used only for sensitivity analysis.

### Appendix A2. NHAMCS Trauma/Injury/Adverse-Effect Exclusions

Initial repository-configured primary rule:

| Field | Codes | Action | Status |
|---|---|---|---|
| `INJPOISAD` | keep `4` only | Exclude injury, poisoning, and adverse-effect records by keeping strict non-injury/non-poisoning/non-adverse-effect visits. | Confirm against selected NHAMCS codebook before fitting. |

The appendix must also define diagnosis/RFV sensitivity exclusions for injury, trauma, poisoning, and adverse effects. If exact diagnosis or RFV exclusion lists are unavailable, fitting is blocked or the model must be labeled exploratory.

### Appendix A3. MIMIC Abdominal-Pain Chief-Complaint Regex

Primary chief-complaint inclusion regex must be case-insensitive and version-controlled. Starting candidate:

```regex
(?i)\b(abd(ominal)?|belly|stomach|epigastr(ic|ium)|ruq|luq|rlq|llq|periumbilical|suprapubic)\b.*\b(pain|ache|aching|cramp|cramping|tender(ness)?)\b|\b(pain|ache|aching|cramp|cramping|tender(ness)?)\b.*\b(abd(ominal)?|belly|stomach|epigastr(ic|ium)|ruq|luq|rlq|llq|periumbilical|suprapubic)\b
```

Exclude complaint strings that match trauma exclusions before endpoint construction. Diagnosis-code sensitivity must be documented separately.

### Appendix A4. MIMIC Trauma Exclusion Regex And Diagnosis Exclusions

Primary chief-complaint exclusion regex must be case-insensitive and version-controlled. Starting candidate:

```regex
(?i)\b(trauma|injur(y|ies)|mvc|mva|motor vehicle|fall|fell|assault|stab|stabbing|gunshot|gsw|laceration|fracture|fx|burn|crush|pedestrian struck|bicycle accident|bike accident)\b
```

Diagnosis exclusions must include exact ICD-9/ICD-10 code patterns used for traumatic injury, poisoning, and adverse effects. Starting diagnosis families for review:

| Coding system | Candidate exclusion family | Status |
|---|---|---|
| ICD-10-CM | `S00`-`T88`, with sensitivity rules separating traumatic injury from complications/adverse effects. | TODO-confirm-from-codebook. |
| ICD-9-CM | `800`-`999` and E-code injury/adverse-effect families as applicable. | TODO-confirm-from-codebook. |

Do not fit a primary MIMIC model until exact diagnosis exclusions are reviewed and saved.

### Appendix A5. Vomiting RFV/Symptom/Chief-Complaint Terms

Version-control all vomiting mappings. Starting text regex:

```regex
(?i)\b(vomit(s|ed|ing)?|emesis|throw(ing)? up|n/?v|nausea and vomiting)\b
```

Do not count isolated nausea as vomiting unless a sensitivity analysis explicitly defines a nausea-or-vomiting proxy. NHAMCS RFV/symptom and diagnosis mappings must list exact codes and labels before use.

### Appendix A6. Fever Objective Temperature Threshold And Fever Text Terms

Primary fever/temperature rule:

| Source | Field | Rule | Normalized value |
|---|---|---|---|
| NHAMCS | Temperature field if available | Fever if temperature is `>= 100.4 F` or `>= 38.0 C`; implausible values flagged and excluded from temperature modeling. | `fever_objective = 1` |
| MIMIC-IV-ED | Triage temperature | Fever if temperature is `>= 100.4 F` or `>= 38.0 C`; implausible values flagged and excluded from temperature modeling. | `fever_objective = 1` |

Starting fever text regex for sensitivity only:

```regex
(?i)\b(fever|febrile|temp(erature)?|chills|rigors)\b
```

Objective temperature is preferred over text. Chills/rigors are sensitivity-only fever-text terms unless validated against objective temperature or clinician-coded fever.

### Appendix A7. Pain Parsing Rules

Pain parsing must preserve missingness and invalid text rather than silently recoding.

| Input pattern | Rule | Output |
|---|---|---|
| Blank, whitespace, null | Missing, not zero. | `pain_value = null`, `pain_missing_reason = blank`. |
| Pure integer or decimal from `0` to `10` | Parse numeric. | `pain_value = number`. |
| `10/10`, `7 out of 10`, `7 of 10` | Parse numerator if denominator is 10. | `pain_value = numerator`. |
| `"0"` | Parse as zero. | `pain_value = 0`. |
| `denies pain`, `no pain`, `pain free` with no conflicting positive number | Parse as zero. | `pain_value = 0`, `pain_text_zero = 1`. |
| `unable`, `uta`, `unable to assess`, `refused`, `declined`, `unknown`, `not recorded` | Missing, not zero. | `pain_value = null`, reason-specific missing flag. |
| Nonnumeric free text without a valid zero phrase | Missing. | `pain_value = null`, `pain_missing_reason = nonnumeric`. |
| Numeric value `<0` or `>10` | Implausible. | `pain_value = null`, `pain_missing_reason = implausible`; tabulate. |
| Multiple conflicting numeric values | Ambiguous. | `pain_value = null`, `pain_missing_reason = conflicting_values`; tabulate. |

Primary pain bins:

| Bin | Numeric values |
|---|---|
| Low | `0`-`3` |
| Moderate | `4`-`6` |
| Severe | `7`-`10` |

Do not treat unknown, refused, unable, nonnumeric, blank, or implausible pain values as low pain.

## NHAMCS Survey Design Variables

NHAMCS fitting must use documented survey design variables or stop before fitting. The current repository analysis config identifies these fields:

| Role | Variable | Source status | Fitting rule |
|---|---|---|---|
| Patient visit weight | `PATWT` | Present in existing repository analysis config. Confirm against the selected NHAMCS codebook for the run year. | Required for weighted counts and survey-weighted fitting. |
| Stratum variable | `CSTRATM` | Present in existing repository analysis config. Confirm against the selected NHAMCS codebook for the run year. | Required for design-based variance if available. |
| PSU/cluster variable | `CPSUM` | Present in existing repository analysis config. Confirm against the selected NHAMCS codebook for the run year. | Required for design-based variance if available. |
| Variance method | Taylor linearization, replicate-weight method, or documented survey-package equivalent | TODO-confirm-from-codebook and software implementation. | Required before a non-exploratory NHAMCS standard error or covariance claim. |

If any required design variable is missing, renamed, unconfirmed, or unusable, the run must write `blocker_report.md` or label the fit exploratory. Do not emit narrow standard errors from an unweighted or non-design-aware NHAMCS fit.

## Missingness Plan

Missingness is an evidence gate, not a nuisance detail.

### Required Missingness Tables

Create missingness tables overall and by endpoint:

| Field | NHAMCS | MIMIC |
|---|---|---|
| Pain score | `PAINSCALE` numeric vs blank/unknown/invalid. | Triage pain numeric, nonnumeric, missing, unable, refused, implausible. |
| Temperature | Temperature missing/outlier. | Triage temperature missing/outlier. |
| Acuity | Triage urgency/immediacy missing. | Acuity missing. |
| Vomiting proxy | RFV/symptom/proxy availability. | Chief complaint missing and vomiting-term availability. |
| Region proxy | Abdominal pain RFV granularity. | Chief-complaint region text. |
| Endpoint | Raw disposition conflicts/exclusions. | Disposition/`hadm_id` conflicts. |

### Primary Handling

Use missingness indicators, not silent imputation, for pain and core vitals. Unknown effects cannot receive directional coefficients without missingness evidence.

### Sensitivity Handling

Run these sensitivity analyses when the required data exist:

| Sensitivity | Purpose |
|---|---|
| Complete-case pain model | Checks whether missing-indicator model drives the result. |
| Missing pain as separate category | App-compatible categorical output. |
| Multiple imputation sensitivity | Secondary only; pain missingness may be informative. |
| Pain removed | Tests whether calibration/discrimination improves without pain. |
| Pain adjusted before vs after acuity/vitals | Quantifies confounding. |

## Sparse Cell And Event Rules

Apply these rules before fitting and document the decision in the run metadata.

| Condition | Required action |
|---|---|
| Any categorical level has `<10` admission events | Collapse with a clinically adjacent level, remove the level/predictor, or use prespecified penalization. |
| Total admission events `<100` in the final binary analytic cohort | Exploratory only; do not claim stable coefficients or narrow standard errors. |
| Sparse pain bin | Collapse bins, fit a regularized/flexible model, or omit pain from the primary empirical model. |
| Sparse vomiting positives or sparse fever positives | Use descriptive/proxy-only reporting unless penalization and validation are prespecified. |
| Complete-case pain model loses `>40%` of the analytic cohort | Treat complete-case pain as sensitivity only, not the primary pain result. |
| Separation or quasi-separation occurs | Use penalized or Bayesian logistic regression and report the issue. |

Do not hide sparse-cell decisions inside broad exception handling.

## Pain Severity Monotonicity Plan

The protocol tests pain monotonicity; it does not assume it.

### Pain Specifications To Fit

| Specification | Purpose |
|---|---|
| Pain bins `0`-`3`, `4`-`6`, `7`-`10` | Primary app-compatible severity test. |
| Pain bins `0`, `1`-`3`, `4`-`6`, `7`-`8`, `9`-`10` | Detect shape and ceiling effects. |
| Continuous pain `0`-`10` | Tests linear per-point association. |
| Restricted cubic spline pain | Detects nonlinear/nonmonotonic dose response. |
| Monotone constrained binned pain | Tests whether a monotonic model is defensible. |
| No-pain model | Quantifies incremental value of pain. |

### Unadjusted Pain Evidence

For each dataset, produce `pain_unadjusted_rates.csv`:

| Pain bin | N | Outcome events | Weighted N if NHAMCS | Admit percent | 95% CI |
|---|---:|---:|---:|---:|---:|

Graph weighted and unweighted admission probability by pain bin when plotting dependencies are available.

### Adjusted Pain Models

Fit sequential models:

| Model | Covariates | Question |
|---|---|---|
| A | Pain + age. | Does pain associate with admission minimally adjusted? |
| B | Pain + age + vomiting + fever/temp. | Does symptom context change pain effect? |
| C | Pain + age + vomiting + fever/temp + acuity. | Is pain independent of triage concern? |
| D | Pain + age + vomiting + fever/temp + acuity + vitals. | Is pain independent of objective severity? |

If pain has signal in Model A but disappears after acuity/vitals, classify it as a workflow/severity proxy rather than an independent predictor.

### Monotone Constrained Model

For the primary binned pain model:

```text
beta_0_3 = 0
beta_4_6 = delta_1
beta_7_10 = delta_1 + delta_2
delta_1 >= 0
delta_2 >= 0
```

Bayesian implementation:

```text
delta_1, delta_2 ~ HalfNormal(0, 0.5)
```

Frequentist implementation: fit the unconstrained model first, then compare it to an isotonic or logistic order-restricted model.

### Stricter Pain Monotonicity Rule

Pain monotonicity is established only if all of these conditions pass:

1. Unadjusted admission rates are nondecreasing across `0`-`3`, `4`-`6`, and `7`-`10` in NHAMCS.
2. MIMIC shows no material reversal after applying the harmonized pain parser and endpoint rules.
3. Unconstrained adjusted coefficients satisfy `severe >= moderate >= reference`, or any violations are trivial with overlapping uncertainty.
4. The monotone-constrained model does not materially worsen calibration or Brier score compared with flexible pain.
5. Pain retains signal after age + vomiting + fever/temp; if it disappears after acuity/vitals, classify it as a severity proxy, not an independent predictor.

Final classification must be written to `pain_monotonicity.csv`:

| Result | Classification |
|---|---|
| All criteria pass and calibration is acceptable | `dataset_derived_monotonic_candidate`, pending full app-export gate. |
| Positive but attenuated/confounded | `severity_proxy`, use wide uncertainty if retained. |
| Nonmonotonic but predictive | `flexible_or_spline_only`, no monotonic language. |
| Null or unstable | `unsupported_or_remove_from_empirical_model`. |
| Missingness too severe | `blocked_by_missingness`. |

Do not promote pain in the app unless the broader `dataset_derived` lock also passes.

## Model Fitting Strategy

### NHAMCS Fitting

Use survey-weighted logistic regression with documented design variables and patient visit weights.

Primary NHAMCS candidate models:

| Model | Formula |
|---|---|
| Active `e-dispo-v4.1` | `admit ~ age_centered + pain_severe + vomiting + fever_or_temp + tachycardia_burden + high_acuity_proxy` |
| Reduced plus acuity/vitals sensitivity | `admit ~ age_band + pain_bin + vomiting + temp + acuity + HR + SBP` |
| Flexible future expanded candidate | `admit ~ spline(age) + acuity + spline(pain) + temp + HR + SBP + vomiting` |
| Monotone pain test | Same as reduced/flexible model but with ordered pain increments. |

For NHAMCS, save:

| Output | Required |
|---|---|
| Beta vector | Yes if fitting succeeds. |
| Survey-adjusted SE | Yes for non-exploratory fit. |
| Survey covariance matrix | Yes for non-exploratory fit. |
| Weighted admission prevalence | Yes. |
| Design notes | Yes. |
| Unweighted event counts | Yes. |

### MIMIC-IV-ED Fitting

Use standard logistic, ridge logistic, or Bayesian logistic regression. Use patient-level clustering or subject-level bootstrap for uncertainty because patients can have multiple ED stays. Do not use a shifted-date temporal split as the primary validation split because MIMIC dates are shifted on a patient-specific basis.

Primary MIMIC candidate models:

| Model | Formula |
|---|---|
| Active-shape replication | `admit ~ age + pain_bin + vomiting + fever_or_temp + tachycardia_burden` |
| Objective severity | `admit ~ age + acuity + pain + temp + HR + SBP + vomiting` |
| Flexible future expanded candidate | `admit ~ spline(age) + acuity + spline(pain) + spline(temp) + HR + SBP + vomiting` |

## SE, Covariance, And Posterior Draws

### Minimum Frequentist Output

For each fitted model:

| Artifact | Format |
|---|---|
| Coefficient table | `term`, `level`, `beta`, `SE`, `OR`, `95% CI`, p-value or posterior probability if applicable. |
| Covariance matrix | Square matrix indexed by coefficient name. |
| Correlation matrix | Optional but useful for app simulation. |
| Model formula | Exact formula and transformations. |
| Reference categories | Explicit. |
| Missingness coding | Explicit. |

Do not use independent coefficient draws after fitting unless covariance is unavailable and the limitation is explicit.

### Simulation Draws For Static App

For frequentist models:

```text
beta_draw ~ MVN(beta_hat, Sigma_hat)
```

Generate at least 10,000 coefficient draws per model if using draws for app uncertainty.

For Bayesian models, export posterior draws with these fields:

| Field | Requirement |
|---|---|
| `draw_id` | Unique draw. |
| `term` | Coefficient name. |
| `beta` | Draw value. |
| `model_version` | NHAMCS, MIMIC, pooled, or calibrated model identifier. |
| `calibration_intercept` | Draw or fitted value. |
| `calibration_slope` | Draw or fitted value. |

### Pooling NHAMCS And MIMIC

| Use | Rule |
|---|---|
| NHAMCS | Primary national public derivation/calibration source. |
| MIMIC | Replication, proxy validation, and transportability check. |
| Combined inference | Random-effects/meta-analytic synthesis only after harmonized variables and compatible endpoint definitions. |
| App activation | Prefer NHAMCS-calibrated coefficients unless MIMIC is explicitly the target context. |

## Calibration And Validation

### Required Calibration Outputs

Report:

| Calibration item | Required output |
|---|---|
| Observed admission prevalence | Overall and by risk decile; weighted for NHAMCS. |
| Mean predicted probability | Compare with observed prevalence. |
| Calibration-in-the-large | Intercept error. |
| Calibration slope | Slope with interpretation. |
| Calibration plot data | Observed vs predicted by decile. |
| Brier score | With CI/bootstrap if possible. |
| AUROC | With CI, secondary to calibration. |

### Calibration Failure Rules

| Finding | Required action |
|---|---|
| Calibration slope `0.8`-`1.2` | Acceptable candidate educational-model range if other gates pass. |
| Calibration slope `<0.8` | Likely overfitting or extreme predictions; shrink, penalize, or recalibrate. |
| Calibration slope `>1.2` | Underfitting or weak predictions; inspect model form and missing predictors. |
| Mean predicted probability differs from observed by `>2` percentage points or `>10%` relative | Recalibrate intercept before any app export. |
| Pain worsens Brier score or calibration slope | Do not promote pain. |
| Poor NHAMCS-to-MIMIC transport calibration | Use source-specific calibration only; do not claim general transportability. |

### Adoption Gate

A candidate empirical model can be considered for app replacement only if it provides:

| Gate | Pass condition |
|---|---|
| Cohort | Final code-level cohort with flow counts. |
| Endpoint | Strict binary endpoint counts and exclusions. |
| Predictors | All active variables mapped and validated. |
| Coefficients | Beta, SE, covariance/posterior draws. |
| Missingness | Missingness by endpoint and sensitivity analysis. |
| Pain | Monotonicity verdict or explicit nonmonotonic/flexible/proxy/unsupported conclusion. |
| Calibration | Observed-vs-predicted calibration and calibration slope. |
| Transportability | NHAMCS/MIMIC comparison. |
| Reporting | TRIPOD+AI-style reporting and PROBAST+AI-style bias/applicability assessment. |

Passing these gates permits review. It does not automatically adopt v4.

## Concrete Deliverables

| Deliverable | Contents |
|---|---|
| D1. Cohort flow tables | NHAMCS and MIMIC counts after each inclusion/exclusion step. |
| D2. Endpoint audits | Raw disposition counts, conflict counts, final binary endpoint counts. |
| D3. Predictor mapping memo | Exact RFV, ICD, chief-complaint regex, temperature, pain, vomiting, and fever rules. |
| D4. Missingness report | Missingness by endpoint and source. |
| D5. Pain severity report | Unadjusted rates, adjusted ORs, spline/flexible model, monotone-model result. |
| D6. Coefficient table | Beta, SE, OR, CI, evidence tier, limitations. |
| D7. Covariance/posterior file | Covariance matrix or posterior coefficient draws. |
| D8. Calibration report | Calibration-in-the-large, slope, Brier, AUROC, decile data. |
| D9. Transportability report | NHAMCS vs MIMIC coefficient and calibration comparison. |
| D10. App export | Versioned JSON/constants file with coefficients, covariance/draws, transformations, evidence labels. |

## Deliverable File Schemas

All CSV files must include a header row. Required columns must be present even when a value is blank because the analysis is blocked or not applicable.

### `cohort_flow_nhamcs.csv`

```text
run_id,source,step_order,step_name,inclusion_exclusion_rule,unweighted_n,weighted_n,weighted_percent_of_start,records_removed,weighted_removed,code_list_version,notes
```

### `cohort_flow_mimic.csv`

```text
run_id,source,step_order,step_name,inclusion_exclusion_rule,n,percent_of_start,records_removed,code_list_version,notes
```

### `endpoint_audit_nhamcs.csv`

```text
run_id,source,raw_flag_or_class,endpoint_class,include_primary_binary,unweighted_n,weighted_n,admission_events,weighted_admission_events,conflict_rule,exclusion_reason,notes
```

Allowed `endpoint_class` values: `admit`, `routine_home_discharge`, `observation_only`, `observation_discharge`, `transfer`, `death_expired_doa`, `ama`, `lwbs_lbtc_eloped`, `other`, `unknown_missing`, `conflict`.

### `endpoint_audit_mimic.csv`

```text
run_id,source,raw_disposition,hadm_id_status,endpoint_class,include_primary_binary,n,admission_events,conflict_rule,exclusion_reason,notes
```

Allowed `hadm_id_status` values: `present`, `absent`, `not_applicable`.

### `missingness_by_endpoint.csv`

```text
run_id,source,endpoint_class,variable,missing_type,n_missing,n_total,missing_percent,weighted_missing,weighted_total,weighted_missing_percent,handling_rule,notes
```

For MIMIC, weighted fields should be blank. `missing_type` examples: `blank`, `unknown`, `refused`, `unable`, `nonnumeric`, `implausible`, `not_collected`.

### `pain_unadjusted_rates.csv`

```text
run_id,source,pain_bin,pain_value_min,pain_value_max,n,events,weighted_n,weighted_events,admit_percent,ci_lower,ci_upper,rate_order,notes
```

`rate_order` must record whether the bin participates in the `0-3 <= 4-6 <= 7-10` check.

### `coefficients.csv`

```text
run_id,source,model_id,model_role,term,level,reference_level,beta,se,or,ci_lower,ci_upper,p_value,posterior_probability,evidence_tier,sparse_cell_action,notes
```

Allowed `evidence_tier` values: `dataset_derived`, `prototype_assumption`, `unsupported`, `blocked`, `exploratory`.

### `covariance_matrix.csv`

Use long format:

```text
run_id,source,model_id,row_term,column_term,covariance
```

Every coefficient in `coefficients.csv` for the same `model_id` must appear as both `row_term` and `column_term`.

### `posterior_draws.csv`

Use long format:

```text
run_id,source,model_id,draw_id,term,beta,calibration_intercept,calibration_slope,seed,notes
```

If posterior draws are not used, this file may be omitted only when `covariance_matrix.csv` exists.

### `calibration_by_decile.csv`

```text
run_id,source,model_id,decile,n,events,weighted_n,weighted_events,mean_predicted,observed_rate,ci_lower,ci_upper,calibration_group_method,notes
```

For NHAMCS, `observed_rate` must be weighted when survey weights are available and confirmed.

### `calibration_metrics.csv`

```text
run_id,source,model_id,n,events,weighted_n,weighted_events,observed_prevalence,mean_predicted,absolute_calibration_error,relative_calibration_error,calibration_intercept,calibration_slope,brier_score,auc,validation_method,seed,verdict,notes
```

`verdict` must reflect the calibration failure rules above.

### `pain_monotonicity.csv`

```text
run_id,source,model_id,nhamcs_unadjusted_nondecreasing,mimic_no_material_reversal,adjusted_order_ok,monotone_model_calibration_ok,pain_signal_after_symptom_context,pain_signal_after_acuity_vitals,missingness_ok,brier_delta_vs_flexible,calibration_slope_delta_vs_flexible,verdict,reason
```

Allowed `verdict` values: `dataset_derived_monotonic_candidate`, `severity_proxy`, `flexible_or_spline_only`, `unsupported_or_remove_from_empirical_model`, `blocked_by_missingness`, `not_evaluated`.

### `app_export.json`

Required top-level keys:

```json
{
  "schemaVersion": "string",
  "runId": "string",
  "modelVersion": "string",
  "modelStatus": "candidate_not_adopted",
  "source": "NHAMCS|MIMIC|source_specific|meta_analytic",
  "endpointSpec": {
    "name": "same_hospital_inpatient_admission_vs_routine_ed_discharge_home",
    "constructedAfterExclusions": true,
    "excludedDispositionClasses": []
  },
  "cohort": {
    "population": "adult men ages 18-64 with non-traumatic abdominal pain",
    "cohortFlowFile": "string",
    "endpointAuditFile": "string"
  },
  "predictors": [],
  "formula": "string",
  "transformations": [],
  "referenceCategories": {},
  "coefficients": [],
  "covarianceMatrixFile": "string",
  "posteriorDrawsFile": "string",
  "calibration": {
    "metricsFile": "string",
    "byDecileFile": "string",
    "verdict": "string"
  },
  "painMonotonicity": {
    "file": "string",
    "verdict": "string"
  },
  "missingnessFile": "string",
  "evidenceGate": {
    "datasetDerivedAllowed": false,
    "gateFailures": []
  },
  "software": {
    "seed": 0,
    "fittingMethod": "string",
    "packageVersions": {}
  },
  "limitations": []
}
```

`modelStatus` must not be changed to `adopted` by this protocol. `datasetDerivedAllowed` may be `true` only when the dataset-derived lock passes.

Each object in `coefficients` must include:

```text
term,level,beta,se,evidence_tier,source,reference_level
```

### `blocker_report.md`

Required sections:

```text
# Blocker Report

Run ID:
Date:
Source:

## Blockers
## Missing Raw Data Or Permissions
## Unconfirmed Code Lists
## Missing Required Columns
## Survey Design Confirmation
## Endpoint Construction Blockers
## Sparse Cell Or Event Blockers
## Missingness Blockers
## Calibration Or Fitting Blockers
## Outputs Written
## Next Required Action
```

## Go/No-Go Logic

### Pain Severity

| Finding | Action |
|---|---|
| Monotonic and calibrated after all gates | Eligible for review as a `dataset_derived` pain candidate. |
| Monotonic unadjusted but not adjusted | Label as confounded; retain only if educationally needed with wide uncertainty. |
| Nonmonotonic but severe-only predictive | Collapse to severe vs non-severe; no monotonic language. |
| Nonmonotonic but broadly predictive | Use spline/flexible pain only with explicit nonmonotonic language. |
| Null | Remove from empirical candidate or keep only as prototype v3 input if the app requires it. |
| Missingness invalidates inference | Keep missingness as explicit limitation; no dataset-derived pain coefficient. |

### Model Activation

| Finding | Action |
|---|---|
| Reduced model calibrates well and coefficients are stable | Mark as reviewable empirical candidate, not automatically active. |
| Future expanded candidate improves calibration and all active predictors are documented | Consider replacement only after independent review and app-export gate. |
| Unsupported predictors remain active | Do not activate as empirical model. |
| Calibration poor | Recalibrate intercept/slope, revise model form, or keep v3 prototype. |

## Recommended Final Model Hierarchy

| Model | Purpose |
|---|---|
| Model A: Reduced empirical model | Age, pain if supported, vomiting, objective temperature/fever. |
| Model B: Objective severity future expanded candidate | Age spline, acuity, pain/missingness, temperature, HR, SBP, vomiting. |
| Model C: App-compatible v3 bridge | Same variables mapped back to app levels where possible. |
| Prototype expanded v3 | Broad region, onset/duration, constant/intermittent only as labeled educational assumptions. |

The strongest immediate empirical path may be Model B, but the cleanest app story may be Model A plus a v3 bridge: show the full app as educational, and show a reduced fitted model only after evidence gates pass.

## Source Anchors

- CDC NHAMCS 2022 public-use documentation: `docs/validation/source-table.md`.
- CDC masked design-variable guidance: public-use files include masked design variables for variance estimation.
- MIMIC-IV-ED: ED stays from 2011-2019 with `edstays`, `triage`, `vitalsign`, `diagnosis`, medication, and disposition-related tables.
- TRIPOD+AI and PROBAST+AI: reporting, risk-of-bias, and applicability framework for prediction-model development.

## Changelog

### 2026-04-28 Tightening Revision

- Added an execution-readiness checklist at the top of the protocol.
- Restated the core objective as a transparent logistic ED disposition model for adult men ages 18-64 with non-traumatic abdominal pain.
- Tightened strict endpoint construction after exclusions and added NHAMCS and MIMIC conflict precedence rules.
- Locked NHAMCS as the primary national derivation/calibration source and MIMIC-IV-ED as the granular replication/proxy-validation source.
- Added code-list appendices for NHAMCS abdominal-pain RFV codes, NHAMCS trauma/injury/adverse-effect exclusions, MIMIC chief-complaint regex, MIMIC trauma/diagnosis exclusions, vomiting terms, fever/temperature rules, and pain parsing.
- Added NHAMCS survey design placeholders for `PATWT`, `CSTRATM`, `CPSUM`, and the variance method.
- Added sparse cell/event stopping, collapse, and exploratory-label rules.
- Replaced the prior pain decision rule with stricter monotonicity criteria requiring NHAMCS trend, MIMIC non-reversal, adjusted coefficient order, calibration/Brier comparison, and confounding classification.
- Added calibration failure rules for slope, intercept error, pain worsening, and NHAMCS-to-MIMIC transport failure.
- Added exact deliverable schemas for cohort flow, endpoint audit, missingness, pain rates, coefficients, covariance, posterior draws, calibration, pain monotonicity, app export, and blocker reporting.
- Updated the adoption boundary: `e-dispo-v4.1-pas5-high-acuity-surrogate` is active for educational use, PAS-5 remains surrogate-labeled, and pain is not called monotonic unless testing supports it.
