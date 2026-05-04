# Model Card

## Intended Use

Course/final-project educational model showing a defensible class-model workflow for ED disposition after explicit endpoint recoding.

The app does not diagnose disease, advise triage, recommend treatment, or tell anyone whether to seek emergency care.

The primary app flow is intentionally lean. Supporting validation, data-readiness, reporting, bias, QA, and source material live in the in-app Documentation section for instructors and reviewers.

## Population

- Adult men ages 18-64
- Already in the emergency department
- Non-traumatic abdominal pain

## Outcome

`admit`: same-hospital hospitalization/admission, including direct same-hospital admission and observation -> hospitalized when documented.

`treat_and_release`: routine home release through no follow-up planned, return to ED if needed, or outpatient follow-up disposition.

Excluded before primary binary analysis: observation -> discharged, transfer, death/expired/DOA/died in ED, AMA/LWBS/LBTC/elopement, other disposition, missing, unavailable, unknown disposition, or conflicting terminal disposition flags.

Sensitivity A treats observation -> discharged as eventual home release. Sensitivity B treats acute transfer as acute-care escalation. Both are report-only and not active app predictions.

## Predictors

- Exact age centered at 42
- Pain severity collapsed to `pain_severe = 1[pain_bin3 == severe]`
- Fever or objective temperature proxy
- Vomiting
- Observed HR as `tachycardia_burden = max(HR - 100, 0) / 10`

## Analysis

The app uses the versioned reduced pooled NHAMCS 2018-2022 empirical logistic-regression export `e-dispo-v4.0`. The app computes `P(admit)` as shorthand for same-hospital hospitalization/admission and derives `P(treat_and_release) = 1 - P(admit)` only after the endpoint-refined primary binary cohort restriction.

Latin Hypercube Sampling propagates exported coefficient uncertainty through the reduced empirical logistic model. The app reports median, p10-p90, p2.5-p97.5, histogram, and sensitivity ranking.

## Predictive Power And Usability

The active `e-dispo-v4.0` model has moderate discrimination, with exported AUROC 0.713. Its exported Brier score is 0.0976, compared with an approximate prevalence-only Brier score of 0.104 in the complete-case cohort. That is a small absolute improvement of about 0.006, so the model is useful for educational risk-model demonstration but not for individual-level clinical action.

The exported calibration check is internally coherent: observed prevalence and mean predicted probability both round to 11.75%, with calibration intercept near 0 and slope near 1. This is not external validation and does not establish transportability.

Usability is strongest when the app foregrounds the reduced empirical inputs: exact age, severe-vs-non-severe pain status, fever/temperature proxy, vomiting, and observed HR. PAS-5 and other excluded prototype controls should remain visually and textually separated because they do not alter the `e-dispo-v4.0` empirical estimate. Missing pain and missing HR are not silently treated as reference/normal values; the `e-dispo-v4.0` estimate requires observed pain and observed HR.

## Data-Ready Path

NHAMCS is the primary free public empirical path for the course appendix. NEDS is stronger for endpoint scale but less open/free. MIMIC-IV-ED is useful for richer workflow prototyping but is credentialed and not nationally representative.

Raw NHAMCS files should remain outside the static app bundle. The app shows NHAMCS-derived coefficients only through the validated static export gate in `src/data/empiricalArtifacts.ts`.

The active reduced empirical model uses pooled NHAMCS 2018-2022 exact age, severe-vs-non-severe pain status, fever or temperature proxy, ordinary vomiting, and observed HR transformed into tachycardia burden. Broad pain region, onset/duration, pain pattern, hematemesis, nausea-alone, acuity, SBP, and PAS-5 are not active `e-dispo-v4.0` risk-model inputs.

## Limitations

- The app remains educational/statistical only and is not clinical decision support.
- Endpoint support is stronger than exact symptom-predictor support in public datasets.
- Some symptom predictors require proxies.
- NHAMCS has one `PULSE` value, so tachycardia duration cannot be evaluated in this source.
- PAS-5 is a `patient_perceived_acuity_proxy`; it is explanatory only in `e-dispo-v4.0` and not dataset-derived as direct patient self-assessment.
- Unknown fever or vomiting does not activate the empirical yes coefficient and should not be interpreted as confirmed absence.
- Missing HR withholds the `e-dispo-v4.0` empirical estimate because missing HR is not normal HR.
- Severe pain is a binary signal in the active model; it must not be described as a monotonic mild/moderate/severe dose response.
- Nausea-alone was screened as a future NHAMCS candidate but did not pass the prespecified uncertainty gate; it remains excluded from the active model.
- The reduced NHAMCS export includes calibration and discrimination fields for educational review, but no clinical-validity claim is made.
- Any future empirical model must document cohort construction, endpoint recoding, missing-data handling, calibration, discrimination, and applicability.
- Future PAS-5 risk-model use requires the prespecified IMMEDR surrogate screen to pass cell-count, coefficient-direction, leave-one-year-out, calibration, and artifact gates. NHAMCS does not contain direct PAS-5 answers, so any IMMEDR result remains surrogate evidence.
