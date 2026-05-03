# Validation Reviewer Dossier README

This dossier is for reviewing the current reduced empirical ED disposition educational model. It should help a reviewer answer one main question:

Is the active reduced empirical model clear, bounded, and useful for education, or does it need more data mapping and validation work first?

## What The Reviewer Should Know First

- The active web app uses the reduced pooled NHAMCS 2018-2022 `e-dispo-v4.0` empirical export for educational P(admit).
- The active fit uses exact age, severe-vs-non-severe pain status, fever/temperature proxy, vomiting, and tachycardia burden from observed HR.
- Missing pain and missing HR are excluded from the `e-dispo-v4.0` fit; missing HR is not treated as normal in the app.
- The app still displays some excluded prototype controls; those controls do not affect empirical P(admit).
- AAP-3 is `prototype_acuity_proxy` only and does not affect empirical P(admit).
- Predictive power is moderate and limited: AUROC 0.713 and Brier 0.0977.
- No clinical validity, diagnosis, triage, treatment, discharge-safety, or medical-advice claim is made.

## Recommended Review Order

1. Read `version-manifest.md`.
2. Read `predictor-mapping-lock.md`.
3. Read `empirical-model-development-protocol.md`.
4. Review `endpoint-audit-2022.csv`.
5. Review `performance-report.md`.
6. Review `predictive-power-usability-review.md`.
7. Review `nausea-candidate-screen.md`.
8. Review `sensitivity-report.md`.
9. Review `deficiency-review-next-phase.md`.
10. Complete `model-reviewer-checklist.md`.

## Key Files

- `endpoint-audit-2022.json`: full endpoint audit artifact.
- `endpoint-audit-2022.csv`: plain table of endpoint counts and weighted counts.
- `outputs/combined/app_export.json`: source of truth for the active reduced pooled empirical app model.
- `outputs/combined/final_blocker_or_activation_decision.md`: activation and blocker decision.
- `predictive-power-usability-review.md`: current review of predictive signal, usability strengths, and remaining UI limitations.
- `nausea-candidate-screen.md`: narrow NHAMCS-only candidate-variable screen showing why nausea-alone is not promoted.
- `empirical-model-development-protocol.md`: work order for NHAMCS/MIMIC cohort fitting, pain monotonicity testing, covariance/posterior draws, and adoption gates.
- `model-card.md`: current app model card.
- `nhamcs-pipeline.md`: reproducible offline pipeline notes.
- `source-table.md`: standards and dataset links.

## Lay Summary

The app works as a class demonstration with an active reduced empirical model. The model has moderate discrimination and a small absolute Brier improvement over prevalence-only prediction. Tachycardia burden is now active because it passed the pooled NHAMCS gate as an observed HR-derived predictor. Nausea-alone was screened as the only additional user-feasible NHAMCS symptom in scope and was not promoted. The reviewer should decide whether this is enough for the educational app and what validation should be required before AAP-3, acuity, SBP, or serial-vital concepts ever affect P(admit).
