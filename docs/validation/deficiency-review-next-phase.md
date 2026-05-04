# Deficiency Review And Next-Phase Validation Plan

Date: 2026-05-03

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
- The 2026-05-03 reviewer artifact pass added active-model grouped calibration, plot-ready calibration data, and AUROC/Brier apparent-performance intervals in `outputs/nhamcs_pooled/`.
- Missingness and subgroup performance/calibration artifacts were added for age band, active predictor/proxy availability, race/ethnicity, payer, region, and MSA; remaining subgroup blockers are sparse-cell or no-outcome-variation blockers.
- A 200-replicate survey-bootstrap refit optimism-correction artifact was added for AUROC, Brier score, calibration-in-the-large, and calibration slope.
- Full-source NHAMCS endpoint-only and non-trauma source-scope screens were added using fixed active coefficients and the same strict endpoint exclusions.
- A separate all-sex/all-age full-source non-trauma admit candidate model was added as `e-dispo-v4.1-full-source-nontrauma-admit`; it is labeled `survey_weighted_candidate`, not active app model.
- Analytic and raw public-use NHAMCS variable screens were added for admit-vs-home and transfer-vs-home, with explicit excluded/blocker rows for leakage, design, all-missing, high-cardinality, no-variation, and sparse fields.
- `general-E-Dispo-model-v1` was added as a cleaner parallel all-sex/all-age non-trauma model artifact using age, NHAMCS acuity, AMBTRANSFER arrival-transfer context, fever/temp, tachycardia burden, and hypotension burden; it is labeled `survey_weighted_parallel_model` and does not replace `e-dispo-v4.0`.
- `general-E-Dispo-model-v1-plus-sex` was added as a prespecified sensitivity artifact. It adds categorical sex as a main effect, writes full calibration/performance artifacts and a base-vs-plus-sex comparison CSV, and is not promoted because the overall gain is tiny and optimism-corrected Brier is slightly worse.
- The yearly/full-source builder now carries `AMBTRANSFER`, `arrival_transfer_context`, `IMMEDR`, `acuity_code`, and `hypotension_burden`; `config/code_lists/nhamcs_general_e_dispo_model_recode_maps.yml` preserves explicit blank/unknown/no-triage/not-applicable levels.
- A MIMIC-IV-ED source-specific track now writes a sparse-sample blocker instead of making a transportability claim.
- Candidate-refinement gates now block AAP-3, SBP, acuity, hematemesis, nausea-alone, tachycardia duration, and pain-representation changes until prespecified evidence gates pass.

## Remaining Deficiencies

| Area | Current status | Next required work |
|---|---|---|
| Empirical model | `e-dispo-v4.0` reduced pooled age, severe-vs-non-severe pain, fever/temperature, vomiting, and tachycardia-burden export is active for educational use. | Add adequate source-specific/external validation before any stronger claim. |
| Survey design | Weighted counts, grouped calibration intervals, fixed-prediction AUROC/Brier intervals, and 200-refit internal optimism correction use pooled NHAMCS strata/PSU/weight fields. | Extend design-aware methods to subgroup intervals and any future candidate model comparisons. |
| Missingness | `e-dispo-v4.0` requires observed pain and observed HR; missingness/proxy-availability rows are now reported. | Review complete-case restriction impact and add subgroup intervals where supported. |
| Calibration | Apparent calibration, grouped calibration table/plot data, subgroup calibration rows, and optimism-corrected calibration slope/intercept are reported. | Add source-specific/external calibration when an adequate validation cohort exists. |
| Discrimination | AUROC is moderate at 0.713 with a 95% survey-bootstrap apparent interval of 0.670617 to 0.757748 and optimism-corrected internal AUROC of 0.704894. | Add adequate source-specific validation and subgroup intervals. |
| Probability error | `e-dispo-v4.0` Brier score is 0.0976 with a 95% survey-bootstrap apparent interval of 0.084632 to 0.111066 and optimism-corrected internal Brier of 0.099565. | Compare against candidate augmented models only after prespecified gates pass. |
| Full-source NHAMCS screen | Endpoint-only full ED screen: 77,031 strict-binary rows, 44,668 model-estimable rows, AUROC 0.743845, Brier 0.097487. Non-trauma sensitivity: 50,070 strict-binary rows, 29,096 model-estimable rows, AUROC 0.745550, Brier 0.108448. | Treat as source-scope stress tests only; do not broaden the active model population. |
| Full-source non-trauma candidate model | `e-dispo-v4.1-full-source-nontrauma-admit` fits the compact predictor surface on all-sex/all-age non-trauma records: 50,070 admit-vs-home rows, sex-code counts 28,185/21,885, 29,096 complete-case rows, AUROC 0.757181, and Brier 0.105462. Transfer is report-only with 44,218 transfer-vs-home rows and 1,595 transfer events. | Treat as development evidence only. Run leakage-reviewed, prespecified candidate comparisons and optimism correction before considering any replacement model. |
| Parallel general non-trauma model | `general-E-Dispo-model-v1` fits a clean pre-disposition all-sex/all-age non-trauma formula: age, `IMMEDR` acuity, `AMBTRANSFER` arrival-transfer context, fever/temp, tachycardia burden, and hypotension burden. Denominator 50,070 / 7,447; complete-case 42,300 / 6,488; AUROC 0.817657; Brier 0.104806; 95% fixed-prediction intervals 0.806684-0.827352 for AUROC and 0.099189-0.110763 for Brier; 200-refit optimism-corrected AUROC 0.815737 and Brier 0.105250. | Keep parallel and internal to NHAMCS. Do not add app toggle or replacement claim until prespecified comparisons, subgroup intervals, and adequate source-specific validation are complete. |
| Plus-sex general-model sensitivity | `general-E-Dispo-model-v1-plus-sex` uses the same denominator and complete case as the base general model but adds sex as a categorical main effect. AUROC 0.818263; Brier 0.104635; fixed-prediction intervals 0.808518-0.828209 for AUROC and 0.099073-0.110226 for Brier; optimism-corrected AUROC 0.816054 and Brier 0.105424. Maximum absolute sex subgroup calibration gap falls from 0.012625 to approximately 0.000000. | Keep as sensitivity evidence only. Do not promote sex into the primary clean model because the overall performance gain is negligible, optimism-corrected Brier is slightly worse, and sex is fairness-sensitive. |
| Variable correlation screen | Analytic admit screen: 53 variables; raw admit screen: 954 raw variables; transfer companion screen: 1,000 analytic/raw variables. Every screened variable has an ok, excluded, or blocker row. | Use only to define prespecified candidate predictor work. Do not promote variables from correlation alone. |
| Tachycardia duration | NHAMCS has one `PULSE` value. | Treat duration as MIMIC-only future work requiring timestamp-preserving vital extraction. |
| Fairness/applicability | Age-band, proxy-availability, race/ethnicity, payer, region, and MSA rows are reported; tiny payer levels can remain sparse/no-outcome blockers. | Add subgroup intervals and source-specific validation before broader subgroup or applicability language. |
| External validation | Not performed; MIMIC-IV-ED screen is blocked by sparse complete-case sample. | Build an adequate source-specific validation cohort before any external-validation or transportability claim. |
| AAP-3 | Explanatory only, `prototype_acuity_proxy`. | Validate against NHAMCS `IMMEDR` or MIMIC-IV-ED triage acuity before any risk-model use. |
| Safety/regulatory boundary | Educational-only wording is preserved. | Keep patient-facing or directive clinical language out of the app and documents. |

## Next Phase Work Products

1. Empirical development protocol: follow `docs/validation/empirical-model-development-protocol.md`.
2. Reviewed endpoint audit: approve or revise `artifacts/nhamcs/endpoint-audit-2022.json`.
3. Reviewed predictor lock: approve or revise `docs/validation/predictor-mapping-lock.md`.
4. Full missingness and subgroup table: review current age-band, availability, race/ethnicity, payer, region, and MSA outputs; add intervals for supported rows.
5. Survey-aware analysis upgrade: extend existing design-aware apparent intervals and bootstrap-refit optimism correction to subgroup intervals and future candidate comparisons.
6. Pain severity report: keep severe-vs-non-severe active unless a new pain report supports a replacement without monotonicity overclaiming.
7. Calibration figure: use the new grouped calibration plot data and subgroup calibration rows in the reviewer packet.
8. Usability revision: keep observed HR required for `e-dispo-v4.0`, clarify unknown fever/vomiting handling in the UI, and document that missing pain/HR withholds or excludes the empirical path.
9. Validation report update: keep fixed-prediction intervals, optimism correction, full-source NHAMCS screens, sparse subgroup blockers, sparse MIMIC blocker, and sensitivity endpoint comparison clearly separated.
10. Full-source non-trauma candidate review: use the new candidate fit and variable-screen artifacts to define prespecified candidate predictors, then apply leakage review, missingness review, calibration, and optimism correction before any replacement model is considered.
11. General model review: review `general-e-dispo-model-v1.md`, the model spec JSON, coefficient/covariance artifacts, grouped calibration, intervals, optimism correction, plus-sex sensitivity comparison, and subgroup/missingness outputs as a parallel development track only.
12. Reviewer decision: decide whether `e-dispo-v4.0` remains sufficient for the course app or whether a later replacement should wait for acuity/vitals validation.

## Standards Used

- TRIPOD+AI for transparent prediction-model reporting.
- PROBAST+AI for risk-of-bias and applicability review.
- FDA Clinical Decision Support Software guidance for maintaining a non-directive educational boundary.
- DECIDE-AI for later-stage evaluation planning if the work ever moves beyond offline validation.
