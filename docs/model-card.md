# Model Card

## Intended Use

Course/final-project educational model showing a defensible class-model workflow for ED disposition after explicit endpoint recoding.

The app does not diagnose disease, advise triage, recommend treatment, or tell anyone whether to seek emergency care.

The primary app flow is intentionally lean. Supporting validation, data-readiness, reporting, bias, QA, and source material live in the in-app Documentation section for instructors and reviewers.

The repo now builds a separate home-facing `general-E-Dispo-home-v1` public demo for all-sex/all-age non-trauma NHAMCS records. It uses the same PAS-5 high-acuity proxy behavior as this model, excludes transfer-in context and raw acuity dropdowns, and uses `general-E-Dispo-home-v1-measured-sbp` only when an actual measured SBP is supplied. That general demo is parallel to this adult-male abdominal-pain model, not a replacement, and does not establish external validation, transportability, clinical-use evidence, or medical advice.

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
- PAS-5 `high_acuity_proxy`, where PAS-5 A1/A2 = 1 and A3/A4/A5 = 0

## Analysis

The app uses the versioned reduced pooled NHAMCS 2018-2022 empirical logistic-regression export `e-dispo-v4.1-pas5-high-acuity-surrogate`. The app computes `P(admit)` as shorthand for same-hospital hospitalization/admission and derives `P(treat_and_release) = 1 - P(admit)` only after the endpoint-refined primary binary cohort restriction.

Latin Hypercube Sampling propagates exported coefficient uncertainty through the reduced empirical logistic model. The app reports median, p10-p90, p2.5-p97.5, histogram, and sensitivity ranking.

## Predictive Power And Usability

The active `e-dispo-v4.1-pas5-high-acuity-surrogate` model has moderate discrimination in the PAS-5/IMMEDR complete-case screen, with exported AUROC 0.759 and Brier score 0.0913. On the same complete-case subset, the base refit without the PAS-5 high-acuity proxy had AUROC 0.736 and Brier 0.0938. Mean leave-one-year-out AUROC improved by 0.0195 and mean leave-one-year-out Brier improved by 0.00225, although the 2018 heldout year worsened.

The exported calibration check is internally coherent: observed prevalence and mean predicted probability both round to 11.35%, with calibration gap near 0 and slope near 1. This is not external validation and does not establish transportability.

Usability is strongest when the app foregrounds the reduced empirical inputs: exact age, severe-vs-non-severe pain status, fever/temperature proxy, vomiting, observed HR, and PAS-5 high-acuity proxy status. Missing pain and missing HR are not silently treated as reference/normal values; the `e-dispo-v4.1` estimate requires observed pain and observed HR.

## Data-Ready Path

NHAMCS is the primary free public empirical path for the course appendix. NEDS is stronger for endpoint scale but less open/free. MIMIC-IV-ED is useful for richer workflow prototyping but is credentialed and not nationally representative.

Raw NHAMCS files should remain outside the static app bundle. The app shows NHAMCS-derived coefficients only through the validated static export gate in `src/data/empiricalArtifacts.ts`.

The active reduced empirical model uses pooled NHAMCS 2018-2022 exact age, severe-vs-non-severe pain status, fever or temperature proxy, ordinary vomiting, observed HR transformed into tachycardia burden, and PAS-5 high-acuity proxy status. Broad pain region, onset/duration, pain pattern, hematemesis, nausea-alone, direct clinician acuity, and SBP remain outside the active app formula.

## Limitations

- The app remains educational/statistical only and is not clinical decision support.
- Endpoint support is stronger than exact symptom-predictor support in public datasets.
- Some symptom predictors require proxies.
- NHAMCS has one `PULSE` value, so tachycardia duration cannot be evaluated in this source.
- PAS-5 is active only through `high_acuity_proxy`; it is derived from NHAMCS `IMMEDR` as clinician-acuity surrogate evidence, not direct patient self-acuity validation.
- Unknown fever or vomiting does not activate the empirical yes coefficient and should not be interpreted as confirmed absence.
- Missing HR withholds the `e-dispo-v4.1` empirical estimate because missing HR is not normal HR.
- Severe pain is a binary signal in the active model; it must not be described as a monotonic mild/moderate/severe dose response.
- Nausea-alone was screened as a future NHAMCS candidate but did not pass the prespecified uncertainty gate; it remains excluded from the active model.
- The reduced NHAMCS export includes calibration and discrimination fields for educational review, but no clinical-validity claim is made.
- Any future empirical model must document cohort construction, endpoint recoding, missing-data handling, calibration, discrimination, and applicability.
- The PAS-5 surrogate coefficient does not validate PAS-5 as medical advice, direct patient self-assessment accuracy, or a real-world patient-care workflow.
