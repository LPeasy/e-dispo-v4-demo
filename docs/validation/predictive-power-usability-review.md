# Predictive Power And Usability Review

Date: 2026-05-01

Reviewed source of truth:

- `src/data/eDispoV4Model.ts`
- `scripts/nhamcs/nhamcs_e_dispo_v4_pain_severe_validation.R`
- `scripts/nhamcs/nhamcs_nausea_candidate_screen.R`
- `outputs/nhamcs_pooled/tachycardia_burden_validation_report.md`
- `outputs/nhamcs_pooled/nausea_candidate_screen_report.md`
- current app specification under `src/data/` and `src/model/`

## Bottom Line

The active `e-dispo-v4.0` model has real but limited predictive signal. Switching from flexible `pain_bin3` to `pain_severe = 1[pain_bin3 == severe]` is statistically and logically defensible for the educational app because the severe-only term preserves apparent discrimination, slightly improves Brier score, avoids the unsupported mild/moderate contrast, and does not claim a monotonic pain dose response.

The model remains appropriate only for an educational demonstration of endpoint discipline, evidence-gated predictors, and transparent uncertainty reporting. It is not appropriate for clinical decision support, triage, discharge safety, or patient-level action.

## Predictive-Power Findings

1. Discrimination is moderate. The `e-dispo-v4.0` AUROC is 0.713, which supports coarse ranking better than chance but is not strong enough for high-stakes individual decisions.
2. Probability-error improvement remains small in absolute terms. The `e-dispo-v4.0` Brier score is 0.0976; the prevalence-only Brier score in the complete-case cohort is about 0.104, so the absolute improvement is about 0.006.
3. Severe-only pain preserves the flexible-pain signal on the same rows. Severe-only AUROC/Brier are 0.713095/0.097640; flexible pain AUROC/Brier are 0.713136/0.097694; no-pain AUROC/Brier are 0.701754/0.098208.
4. Apparent calibration is internally coherent. Observed prevalence and mean predicted probability both round to 11.75%, with calibration intercept near 0 and slope near 1.
5. Leave-one-year-out checks favor severe-only pain on average: AUROC 0.705185 and Brier 0.098783 vs flexible-pain AUROC 0.695440 and Brier 0.099243.
6. Nausea-alone does not currently justify a future model change. The paired NHAMCS screen estimated OR 0.879 with direction probability 0.7298, below the 0.95 uncertainty gate, with no meaningful performance gain.
7. Transportability is not established. The calibration metrics are export/apparent metrics for the pooled NHAMCS setting, not proof that the model transports to a different ED, data source, subgroup, or user workflow.

## Usability Findings

1. Input burden remains acceptable. The active empirical estimate uses exact age, observed severe-vs-non-severe pain status, fever/temperature proxy, vomiting, and observed HR.
2. HR is a defensible numeric input. Values at or below 100 contribute zero tachycardia burden; HR 110 contributes one coefficient unit; HR 120 contributes two.
3. Missingness handling is cleaner than v1. Pain missingness was removed from the active formula by requiring observed pain, and missing HR withholds the `e-dispo-v4.0` estimate instead of being treated as normal.
4. Mixed active and excluded controls still create cognitive load. Broad pain region, onset/duration, pain pattern, PAS-5, hematemesis, acuity, SBP, and other prototype inputs do not alter the `e-dispo-v4.0` empirical estimate and must remain visibly separated.
5. Unknown symptom answers need careful wording. Fever or vomiting marked unknown does not activate the empirical yes coefficient and should not be described as confirmed absence.
6. PAS-5 improves explanation but not current prediction. It remains `patient_perceived_acuity_proxy`, not dataset-derived as direct patient self-assessment, and not part of `e-dispo-v4.0` P(admit).
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
