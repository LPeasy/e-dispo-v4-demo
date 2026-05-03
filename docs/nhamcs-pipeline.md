# Offline NHAMCS Appendix Pipeline

This pipeline keeps raw public-use files out of the static app bundle. It produces small review artifacts only: endpoint audit JSON/CSV, a reduced model-fit JSON/CSV, and validation reports.

## Inputs

- CDC 2022 NHAMCS ED public-use data archive: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHAMCS/ed2022.zip
- CDC 2022 NHAMCS ED Stata archive: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHAMCS/stata/ed2022-stata.zip
- CDC 2022 NHAMCS ED documentation: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/dataset_documentation/nhamcs/doc22-ed-508.pdf

## Local Data Rule

Do not commit raw NHAMCS files. Keep downloads under the ignored local directory:

```text
data/raw/nhamcs_2022/
```

Only derived artifacts under `artifacts/nhamcs/` should be used for review. Raw public-use data stays outside the static app and outside the reviewer package.

## Script Entry Points

Download/extract the CDC Stata archive:

```powershell
python scripts/nhamcs/derive_nhamcs_2022.py --config scripts/nhamcs/config.example.json --download
```

Generate validation artifacts after the Stata file is available:

```powershell
python scripts/nhamcs/validate_nhamcs_2022.py
```

Run the pipeline fixture test:

```powershell
python scripts/nhamcs/test_validate_nhamcs_2022.py
```

On this workstation, the bundled Python runtime has the required `pandas` and `numpy` dependencies:

```powershell
& "C:\Users\lawto\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts/nhamcs/validate_nhamcs_2022.py
```

## Refined NHAMCS Mapping

The current config uses the 2022 NHAMCS flag-based disposition mapping:

- Same-hospital hospitalization/admission: `ADMITHOS`.
- Observation -> hospitalized: `OBSHOS`, mapped to `admit`.
- Routine home release: `NOFU`, `RETRNED`, `RETREFFU`, mapped to `treat_and_release`.
- Observation -> discharged: `OBSDIS`, excluded from primary and included as eventual home release in Sensitivity A/B.
- Acute transfer: `TRANOTH`, excluded from primary and counted as acute escalation in Sensitivity B only.
- Non-acute transfer: `TRANNH`, `TRANPSYC`, excluded from primary and from Sensitivity B positives.
- Death sentinel: `DOA`, `DIEDED`, excluded before conflict handling.
- Nonroutine exits: `LEFTAMA`, `LWBS`, `LBTC`, and `ELOPED` if present.
- Other/unknown/missing: `OTHDISP`, `NODISP`, or no terminal disposition flag.
- Conflicts: more than one non-death terminal disposition class, excluded from primary and sensitivities.

The 2022 public-use file used here contains `LEFTAMA`, `LWBS`, and `LBTC`; `ELOPED` is retained in the config as a source-compatible flag but is absent in the audited file.

## Cohort Construction

1. Start from all 2022 NHAMCS ED records.
2. Keep male encounters.
3. Keep ages 18-64.
4. Keep abdominal pain reason-for-visit codes `15450`, `15451`, `15452`, and `15453`.
5. Keep strict non-trauma/non-poisoning/non-adverse-effect proxy `INJPOISAD == 4`.
6. Recode endpoint flags before denominator construction.
7. Emit primary endpoint counts, Sensitivity A/B counts, exclusion counts, conflict counts, weighted counts, and variable-audit fields.

## Derived Artifact Shape

The app accepts only a validation-grade model-fit artifact with `schemaVersion: "2.0.0"` and `artifactKind: "nhamcs_validation_model_fit"`. Required fields include:

- `modelVersion`, `endpointSpecVersion`, `configHash`, `generatedBy`, and `modelName`.
- `surveyDesign` with weight, strata, PSU, weighted count, and effective sample size.
- `cohortFlow` with unweighted and weighted counts.
- `endpointCounts` and `sensitivityEndpointCounts`, including weighted counts.
- `predictorMapping` for all seven class predictors.
- `coefficients`, 95% intervals, and `coefficientCovariance`.
- `performanceMetrics` with AUC, Brier score, calibration intercept, calibration slope, prevalence, sample size, event counts, missing predictor exclusions, and weighted binary count.
- `internalValidation` with method, iteration count, seed, and interval summaries.
- `sensitivityAnalyses` for primary endpoint, Sensitivity A, and Sensitivity B.
- `limitations`.

The app must continue to show prototype labels unless this schema gate passes.

## Current Reduced Empirical Candidate

The validation script fits a reduced NHAMCS-supported logistic model using `ageBand` and `painSeverity` only. It does not fit onset/duration, constant/intermittent pattern, broad pain region, vomiting, or fever because their first-pass NHAMCS support is unavailable, weak, or proxy-dependent.

This reduced fit is a validation work product, not the active app model. It is not a clinical model and is not promoted into the web app.

The active `e-dispo-v4.0` educational model is a later pooled NHAMCS 2018-2022 reduced refit. Its version-specific script is `scripts/nhamcs/nhamcs_e_dispo_v4_pain_severe_validation.R`, and its active pain term is `pain_severe = 1[pain_bin3 == severe]` with mild and moderate collapsed as non-severe.

## Pooled Nausea-Alone Candidate Screen

`scripts/nhamcs/nhamcs_nausea_candidate_screen.R` is a candidate-variable screen only. It refits the active base formula and the base-plus-nausea candidate formula on the exact same complete-case pooled NHAMCS rows:

```text
admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden
admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden + nausea_present
```

`nausea_present` is mapped from RFV code `15250` and remains separate from ordinary vomiting code `15300`. The screen writes mapping, run metadata, missingness, cell/event counts, coefficients, covariance, deterministic draws, calibration, leave-one-year-out checks, gate decisions, and a ranked decision report under `outputs/nhamcs_pooled/nausea_*`.

Run it after rebuilding the pooled cohort:

```powershell
Rscript scripts/nhamcs/nhamcs_nausea_candidate_screen.R outputs/nhamcs_pooled/analytic_cohort_nhamcs_2018_2022.csv outputs/nhamcs_pooled
```

The 2026-05-01 run found that nausea-alone did not pass every prespecified gate, so no additional user-feasible NHAMCS symptom was promoted. The output evidence tier remains `survey_weighted_candidate`; the script does not write an app export or change `e-dispo-v4.0`.

## Required Review Before Promotion

Before any future app activation:

1. Confirm the NHAMCS variable names and true-value codings against the official 2022 public-use documentation.
2. Review the RFV abdominal pain cohort rule and `INJPOISAD == 4` non-trauma proxy.
3. Review all endpoint exclusions and conflicts.
4. Decide whether the reduced two-predictor fit is acceptable or whether additional proxy mapping is required.
5. Implement full survey-design variance where feasible.
6. Review calibration, discrimination, missingness, subgroup applicability, and sensitivity analyses.
7. Keep the app educational unless a completed validation dossier is approved.
