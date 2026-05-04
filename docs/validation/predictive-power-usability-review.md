# Predictive Power And Usability Review

Date: 2026-05-04

Reviewed source of truth:

- `src/data/eDispoV4Model.ts`
- `scripts/nhamcs/nhamcs_e_dispo_v4_pain_severe_validation.R`
- `scripts/nhamcs/nhamcs_pas5_acuity_candidate_screen.R`
- `scripts/nhamcs/nhamcs_nausea_candidate_screen.R`
- `outputs/nhamcs_pooled/tachycardia_burden_validation_report.md`
- `outputs/nhamcs_pooled/nausea_candidate_screen_report.md`
- current app specification under `src/data/` and `src/model/`

## Bottom Line

The active `e-dispo-v4.1-pas5-high-acuity-surrogate` model has real but limited predictive signal. It keeps the severe-only pain representation from v4.0 and adds `high_acuity_proxy`, where PAS-5 A1/A2 activate the term and A3/A4/A5 are reference. The PAS-5 term is fitted through NHAMCS `IMMEDR` as a clinician-acuity surrogate because NHAMCS does not contain direct patient PAS-5 answers.

The model remains appropriate only for an educational demonstration of endpoint discipline, evidence-gated predictors, and transparent uncertainty reporting. It is not appropriate for clinical decision support, triage, discharge safety, or patient-level action.

## Predictive-Power Findings

1. Discrimination is moderate. The active v4.1 AUROC is 0.759 in the PAS-5/IMMEDR complete-case screen, which supports coarse ranking better than chance but is not strong enough for high-stakes individual decisions.
2. Probability-error improvement remains modest. The active v4.1 Brier score is 0.0913; the same-subset base refit without `high_acuity_proxy` had Brier 0.0938.
3. PAS-5 adds measurable surrogate signal. Same-subset AUROC improved from 0.7364 to 0.7591, and mean leave-one-year-out AUROC gain was +0.0195.
4. Apparent calibration is internally coherent. Observed prevalence and mean predicted probability both round to 11.35%, with calibration gap near 0 and slope near 1.
5. Year-level stability is imperfect. Mean leave-one-year-out AUROC and Brier gates passed, but the 2018 heldout year worsened.
6. Nausea-alone does not currently justify a future model change. The paired NHAMCS screen estimated OR 0.879 with direction probability 0.7298, below the 0.95 uncertainty gate, with no meaningful performance gain.
7. Transportability is not established. The calibration metrics are export/apparent metrics for the pooled NHAMCS setting, not proof that the model transports to a different ED, data source, subgroup, or user workflow.

## Usability Findings

1. Input burden remains acceptable. The active empirical estimate uses exact age, observed severe-vs-non-severe pain status, fever/temperature proxy, vomiting, observed HR, and the five PAS-5 patient-perceived acuity questions.
2. HR is a defensible numeric input. Values at or below 100 contribute zero tachycardia burden; HR 110 contributes one coefficient unit; HR 120 contributes two.
3. Missingness handling is cleaner than v1. Pain missingness was removed from the active formula by requiring observed pain, and missing HR withholds the `e-dispo-v4.1` estimate instead of being treated as normal.
4. Mixed active and excluded controls still create cognitive load. Broad pain region, onset/duration, pain pattern, hematemesis, direct clinician acuity, SBP, and other prototype inputs remain outside the `e-dispo-v4.1` empirical estimate and must remain visibly separated.
5. Unknown symptom answers need careful wording. Fever or vomiting marked unknown does not activate the empirical yes coefficient and should not be described as confirmed absence.
6. PAS-5 is active only as a surrogate high-acuity proxy. This is not direct patient self-assessment validation because direct PAS-5 answers are not observed in NHAMCS.
7. Tachycardia duration is not feasible in NHAMCS. The source contains one `PULSE` value, not serial vitals; duration can only be a future MIMIC-style timestamped extraction question.
8. No additional user-feasible structured NHAMCS symptom passed the current screen; broader variable discovery should use a richer data source rather than lowering the evidence gate.

## Current Fit For Purpose

| Use | Review finding |
|---|---|
| Course demonstration | Appropriate. The model is transparent and bounded. |
| Reviewer discussion | Appropriate with limitations stated. |
| Exploratory probability display | Appropriate only inside the locked cohort and endpoint, with observed pain and HR. |
| Clinical decision support | Not appropriate. |
| Triage or discharge guidance | Not appropriate. |
| General adult ED abdominal-pain use | Not appropriate without broader validation. |

## Documentation Actions

This review is reflected in:

- `docs/model-card.md`
- `docs/validation/performance-report.md`
- `docs/validation/nausea-candidate-screen.md`
- `docs/validation/deficiency-review-next-phase.md`
- `docs/validation/model-reviewer-checklist.md`
- `docs/class-deliverable-package.md`
- in-app documentation source in `src/data/documentation.ts`
