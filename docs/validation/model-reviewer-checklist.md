# Model Reviewer Checklist

Use this checklist to review the active reduced pooled empirical educational model. Mark each item as Pass, Needs revision, or Not reviewed.

| Review item | Pass | Needs revision | Not reviewed | Notes |
|---|---:|---:|---:|---|
| The app is clearly labeled as educational only. | [ ] | [ ] | [ ] | |
| The app does not diagnose, triage, recommend treatment, recommend discharge, or give medical advice. | [ ] | [ ] | [ ] | |
| `admit` is defined as same-hospital hospitalization/admission. | [ ] | [ ] | [ ] | |
| `treat_and_release` is defined as routine home release. | [ ] | [ ] | [ ] | |
| Observation -> hospitalized maps to `admit`. | [ ] | [ ] | [ ] | |
| Observation -> discharged is excluded from primary and included only in sensitivity endpoints. | [ ] | [ ] | [ ] | |
| Transfer is excluded from the primary endpoint. | [ ] | [ ] | [ ] | |
| Death/DOA/died in ED is a sentinel exclusion, not a predicted outcome. | [ ] | [ ] | [ ] | |
| Conflicting terminal disposition flags are excluded and counted. | [ ] | [ ] | [ ] | |
| The NHAMCS cohort flow is understandable. | [ ] | [ ] | [ ] | |
| Weighted and unweighted endpoint counts are included. | [ ] | [ ] | [ ] | |
| The predictor mapping lock explains which app inputs can and cannot be fitted in NHAMCS. | [ ] | [ ] | [ ] | |
| The reduced empirical candidate uses only defensible predictors. | [ ] | [ ] | [ ] | |
| The active app uses only the validated reduced pooled empirical export for P(admit). | [ ] | [ ] | [ ] | |
| The model-fit artifact includes coefficients, standard errors, intervals, and covariance. | [ ] | [ ] | [ ] | |
| The performance report includes AUC, Brier score, calibration intercept, and calibration slope. | [ ] | [ ] | [ ] | |
| The performance report explains that AUROC 0.713 is moderate and not clinically deployable. | [ ] | [ ] | [ ] | |
| The performance report explains that Brier improvement over prevalence-only prediction is small. | [ ] | [ ] | [ ] | |
| The empirical protocol requires covariance or posterior draws before dataset-derived simulation. | [ ] | [ ] | [ ] | |
| Pain severity has a documented monotonicity, confounding, missingness, and transportability decision rule. | [ ] | [ ] | [ ] | |
| NHAMCS and MIMIC are treated as derivation/calibration and replication/proxy-validation sources, not naively pooled. | [ ] | [ ] | [ ] | |
| The UI/documentation states that broad pain region, onset/duration, pain pattern, hematemesis, acuity, SBP, prototype inputs, and PAS-5 do not affect `e-dispo-v4.0` empirical P(admit). | [ ] | [ ] | [ ] | |
| The reviewer has checked whether requiring observed pain and observed HR for `e-dispo-v4.0` is acceptable. | [ ] | [ ] | [ ] | |
| The UI/documentation states that HR missing is not normal HR and withholds the `e-dispo-v4.0` empirical estimate. | [ ] | [ ] | [ ] | |
| Unknown fever/vomiting wording does not imply confirmed absence. | [ ] | [ ] | [ ] | |
| PAS-5 is labeled `patient_perceived_acuity_proxy`, not dataset-derived as direct patient self-assessment and not advice. | [ ] | [ ] | [ ] | |
| Sensitivity A and Sensitivity B are clearly report-only. | [ ] | [ ] | [ ] | |
| Limitations are visible and understandable to a non-technical reviewer. | [ ] | [ ] | [ ] | |
| No document claims clinical validity or safety. | [ ] | [ ] | [ ] | |
| The next-phase research tasks are specific enough to assign. | [ ] | [ ] | [ ] | |

## Questions For The Reviewer

1. Are the endpoint definitions understandable without technical background?
2. Do any parts sound like clinical advice or a real deployment claim?
3. Is the moderate predictive power of the reduced pooled model acceptable for the educational app, given AUROC 0.713 and small Brier improvement?
4. Which missingness, subgroup, or fairness checks should be prioritized next?
5. Is the observed-pain and observed-HR complete-case requirement acceptable for the `e-dispo-v4.0` empirical estimate?
6. What wording should be changed before class submission or instructor review?
7. What evidence would you require before allowing PAS-5, acuity, SBP, or tachycardia duration to affect P(admit)?
