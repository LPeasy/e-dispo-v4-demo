# Validation Reviewer Dossier README

This dossier is for reviewing the current reduced empirical ED disposition educational model. It should help a reviewer answer one main question:

Is the active reduced empirical model clear, bounded, and useful for education, or does it need more data mapping and validation work first?

## What The Reviewer Should Know First

- The active web app uses the reduced pooled NHAMCS 2018-2022 `e-dispo-v4.1-pas5-high-acuity-surrogate` empirical export for educational P(admit).
- The active fit uses exact age, severe-vs-non-severe pain status, fever/temperature proxy, vomiting, tachycardia burden from observed HR, and PAS-5 `high_acuity_proxy`.
- PAS-5 A1/A2 activate `high_acuity_proxy`; PAS-5 A3/A4/A5 are reference. The coefficient is derived from NHAMCS `IMMEDR` clinician-acuity surrogate evidence, not direct patient PAS-5 answers.
- Missing pain and missing HR are excluded from the `e-dispo-v4.1` fit; missing HR is not treated as normal in the app.
- The app still displays some excluded prototype controls; those controls do not affect empirical P(admit).
- Predictive power is moderate and limited: AUROC 0.759 and Brier 0.0913 in the PAS-5/IMMEDR complete-case screen.
- A separate all-sex/all-age `e-dispo-v4.1-full-source-nontrauma-admit` candidate track exists for reviewer/development work only; it is not the active app model.
- `general-E-Dispo-model-v1` is a newer parallel all-sex/all-age non-trauma model artifact using age, acuity, arrival-transfer context, fever/temp, tachycardia burden, and hypotension burden. It is not an app model and does not replace the active adult-male abdominal-pain v4.1 model.
- `general-E-Dispo-model-v1-plus-sex` is a prespecified sensitivity artifact only. It improves sex subgroup calibration inside NHAMCS but is not promoted because the overall performance gain is negligible and optimism-corrected Brier is slightly worse.
- The public general demo now uses `general-E-Dispo-home-v1`, with `general-E-Dispo-home-v1-measured-sbp` selected only when actual measured SBP is supplied. Transfer-in context and raw acuity dropdowns are removed from the public general formula, PAS-5 `high_acuity_proxy` is used, and blank SBP no longer blocks prediction.
- No clinical validity, diagnosis, triage, treatment, discharge-safety, or medical-advice claim is made.

## Recommended Review Order

1. Read `version-manifest.md`.
2. Read `predictor-mapping-lock.md`.
3. Read `empirical-model-development-protocol.md`.
4. Review `endpoint-audit-2022.csv`.
5. Review `performance-report.md`.
6. Review `full-source-scope-screen.md`.
7. Review `full-source-nontrauma-admit-candidate.md`.
8. Review `general-e-dispo-model-v1.md`.
9. Review `general-e-dispo-home-v1.md`.
10. Review `predictive-power-usability-review.md`.
11. Review `pas5-acuity-candidate-screen.md`.
12. Review `nausea-candidate-screen.md`.
13. Review `sensitivity-report.md`.
14. Review `deficiency-review-next-phase.md`.
15. Complete `model-reviewer-checklist.md`.

## Key Files

- `endpoint-audit-2022.json`: full endpoint audit artifact.
- `endpoint-audit-2022.csv`: plain table of endpoint counts and weighted counts.
- `outputs/combined/app_export.json`: source of truth for the active reduced pooled empirical app model.
- `outputs/combined/final_blocker_or_activation_decision.md`: activation and blocker decision.
- `predictive-power-usability-review.md`: current review of predictive signal, usability strengths, and remaining UI limitations.
- `full-source-scope-screen.md`: fixed-coefficient NHAMCS endpoint-only and non-trauma source-scope screens; not external validation.
- `full-source-nontrauma-admit-candidate.md`: separate broader non-trauma candidate model and analytic/raw variable screen; not an active model update.
- `general-e-dispo-model-v1.md`: separate clean pre-disposition all-sex/all-age non-trauma model artifact; not active app behavior.
- `general-e-dispo-home-v1.md`: public home-facing general model revision; transfer-in context removed and SBP made optional through a measured-SBP branch.
- `pas5-acuity-candidate-screen.md`: PAS-5 high-acuity proxy surrogate evidence and activation boundary.
- `nausea-candidate-screen.md`: narrow NHAMCS-only candidate-variable screen showing why nausea-alone is not promoted.
- `empirical-model-development-protocol.md`: work order for NHAMCS/MIMIC cohort fitting, pain monotonicity testing, covariance/posterior draws, and adoption gates.
- `model-card.md`: current app model card.
- `nhamcs-pipeline.md`: reproducible offline pipeline notes.
- `source-table.md`: standards and dataset links.

## Lay Summary

The app works as a class demonstration with an active reduced empirical model. The model has moderate discrimination and a modest Brier improvement over the same-subset base refit after adding PAS-5 `high_acuity_proxy`. The PAS-5 term is surrogate-derived from NHAMCS `IMMEDR`; NHAMCS does not contain direct patient PAS-5 answers, so this is not direct patient self-assessment validation. Nausea-alone was screened as the only additional user-feasible NHAMCS symptom in scope and was not promoted. Full-source NHAMCS screens now show fixed-coefficient behavior beyond the active cohort, but they are source-scope stress tests, not external validation or a broader-use claim. A separate full-source non-trauma candidate model and variable screen now exist to guide future development without changing the active app model. `general-E-Dispo-model-v1` is the cleaner parallel source-scope general non-trauma model artifact, and `general-E-Dispo-model-v1-plus-sex` remains a sensitivity artifact. The public general demo now uses the home-facing `general-E-Dispo-home-v1` default with PAS-5 `high_acuity_proxy`: AUROC 0.811803, Brier 0.101883, 1,000-replicate fixed-prediction intervals, and 200-refit optimism correction, all internal to NHAMCS. The optional measured-SBP branch has lower AUROC and higher Brier than the no-SBP default, so it is only a measured-vital branch, not a requirement to guess SBP. The reviewer should decide what validation should be required before any broader replacement model, SBP, sex, or serial-vital concept ever affects patient-facing interpretation.
