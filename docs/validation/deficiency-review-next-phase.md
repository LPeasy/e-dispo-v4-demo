# Deficiency Review And Next-Phase Validation Plan

Date: 2026-04-30

## Plain-English Bottom Line

The current app is a well-documented educational/statistical model with an active reduced pooled NHAMCS empirical estimate. It is not a validated medical model. The next phase is to test whether its moderate apparent predictive signal transports across years, subgroups, and richer workflow data.

## Deficiencies Addressed In This Pass

- The validation baseline is now frozen in `version-manifest.md`.
- A real NHAMCS 2022 endpoint audit artifact was generated.
- A reduced NHAMCS model-fit artifact was generated for review.
- Predictor support was locked before fitting.
- The app artifact gate now rejects incomplete empirical artifacts.
- Endpoint tests now cover additional truthy values, death precedence, non-acute transfer behavior, missing/unmapped cases, and source-specific aliases.
- A pipeline fixture test now checks expected endpoint and weighted counts.
- The reduced pooled NHAMCS 2018-2022 export is now active in the app for educational use.
- The tachycardia-burden gate passed; observed HR is active as `tachycardia_burden = max(HR - 100, 0) / 10`.
- Pain missingness was removed from the active formula by requiring observed pain; missing HR now withholds the empirical estimate.
- AAP-3 is implemented only as `prototype_acuity_proxy` and does not affect P(admit).
- Predictive-power and usability review is documented in `predictive-power-usability-review.md`.

## Remaining Deficiencies

| Area | Current status | Next required work |
|---|---|---|
| Empirical model | `e-dispo-v4.0` reduced pooled age, severe-vs-non-severe pain, fever/temperature, vomiting, and tachycardia-burden export is active for educational use. | Add external/source-specific validation and interval estimates before any stronger claim. |
| Survey design | Weighted counts are reported with `PATWT`. | Implement full NHAMCS survey-design variance using weights, strata, and PSU fields. |
| Missingness | `e-dispo-v4.0` requires observed pain and observed HR; missing HR is not treated as normal. | Add missingness/subgroup checks for pain and HR availability, and avoid silent reference-category recoding. |
| Calibration | Apparent calibration intercept/slope are reported and internally coherent. | Add calibration plot, grouped calibration table, and optimism-corrected or survey-aware validation if feasible. |
| Discrimination | AUROC is moderate at 0.713. | Add interval estimation and subgroup comparisons. |
| Probability error | `e-dispo-v4.0` Brier score is 0.0976, about 0.006 better than prevalence-only baseline in the complete-case cohort. | Quantify uncertainty around Brier and compare against candidate augmented models. |
| Tachycardia duration | NHAMCS has one `PULSE` value. | Treat duration as MIMIC-only future work requiring timestamp-preserving vital extraction. |
| Fairness/applicability | Scope is adult men only. | Add age-band, race/ethnicity, payer, region, and hospital/proxy-availability checks. |
| External validation | Not performed. | Consider NEDS for endpoint-scale validation and MIMIC-IV-ED for workflow/proxy validation if access is available. |
| AAP-3 | Explanatory only, `prototype_acuity_proxy`. | Validate against NHAMCS `IMMEDR` or MIMIC-IV-ED triage acuity before any risk-model use. |
| Safety/regulatory boundary | Educational-only wording is preserved. | Keep patient-facing or directive clinical language out of the app and documents. |

## Next Phase Work Products

1. Empirical development protocol: follow `docs/validation/empirical-model-development-protocol.md`.
2. Reviewed endpoint audit: approve or revise `artifacts/nhamcs/endpoint-audit-2022.json`.
3. Reviewed predictor lock: approve or revise `docs/validation/predictor-mapping-lock.md`.
4. Full missingness and subgroup table: add by predictor, endpoint, age band, race/ethnicity, payer, region, and proxy availability.
5. Survey-aware analysis upgrade: incorporate weights, strata, and PSU design for variance where feasible.
6. Pain severity report: unadjusted trend, adjusted sequential models, spline/flexible model, monotone constrained model, missingness sensitivity, and NHAMCS/MIMIC transportability result.
7. Calibration figure: add grouped calibration plot and calibration table.
8. Usability revision: keep observed HR required for `e-dispo-v4.0`, clarify unknown fever/vomiting handling in the UI, and document that missing pain/HR withholds or excludes the empirical path.
9. Validation report update: include AUC interval, Brier score interval, calibration interval, limitations, and sensitivity endpoint comparison.
10. Reviewer decision: decide whether `e-dispo-v4.0` remains sufficient for the course app or whether a later replacement should wait for acuity/vitals validation.

## Standards Used

- TRIPOD+AI for transparent prediction-model reporting.
- PROBAST+AI for risk-of-bias and applicability review.
- FDA Clinical Decision Support Software guidance for maintaining a non-directive educational boundary.
- DECIDE-AI for later-stage evaluation planning if the work ever moves beyond offline validation.
