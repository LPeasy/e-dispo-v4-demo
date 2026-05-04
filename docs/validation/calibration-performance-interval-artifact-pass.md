# Calibration, Performance, And Robustness Artifact Pass

Date: 2026-05-03

Model: archived `e-dispo-v4.0` predecessor; active app model is now `e-dispo-v4.1-pas5-high-acuity-surrogate`.

This note documents the reviewer-facing calibration, performance interval, subgroup, missingness, optimism-correction, full-source NHAMCS scope-screen, and blocker artifacts added for the v4.0 educational/statistical predecessor. The current PAS-5 v4.1 artifacts are documented separately in `pas5-acuity-candidate-screen.md` and `performance-report.md`. The model remains educational only. These artifacts do not establish clinical validity, deployment readiness, external validation, or transportability.

## New Artifacts

- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_calibration_by_decile.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_calibration_plot_data.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_performance_intervals.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_pain_severe_validation_report.md`
- `outputs/nhamcs_pooled/e_dispo_v4_subgroup_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_subgroup_calibration.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_missingness_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_optimism_corrected_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_transportability_track.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_transportability_report.md`
- `outputs/nhamcs_pooled/e_dispo_v4_candidate_refinement_gate.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_candidate_refinement_report.md`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_endpoint_screen_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_endpoint_screen_calibration.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_endpoint_screen_missingness.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_nontrauma_screen_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_nontrauma_screen_calibration.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_nontrauma_screen_missingness.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_scope_screen_report.md`

## Method

Grouped calibration uses weighted predicted-probability deciles from the active model's apparent predictions in the pooled NHAMCS 2018-2022 complete-case cohort. Each row reports unweighted N/events, weighted N/events, predicted range, survey-weighted mean predicted probability, survey-weighted observed admission rate, and a Taylor-linearized survey interval for the observed group rate.

AUROC and Brier intervals use `survey::as.svrepdesign(..., type = "bootstrap")` to generate 1,000 bootstrap replicate weights from the pooled NHAMCS stratum/PSU design. The metric is recomputed on each replicate using the fixed apparent predictions from the active fitted model.

Subgroup and missingness rows use the active model's fitted predictions where the active complete-case model can estimate a row. They report unweighted N/events, weighted N/events, observed prevalence, mean predicted probability, calibration gap, AUROC, Brier score, and a sparse/blocker status. Missing fields required by the plan are written as blocker rows instead of imputed.

Optimism correction uses 200 deterministic survey bootstrap refits. For each replicate, the script refits the active formula with replicate weights, scores the bootstrap sample and the original complete-case cohort, estimates optimism, and subtracts mean optimism from the apparent metric. Metrics are AUROC, Brier score, calibration-in-the-large, and calibration slope. This is internal validation only.

The source-specific transportability track applies the NHAMCS coefficient surface to an available MIMIC-IV-ED analytic cohort only as a replication/proxy screen. The available complete-case sample is sparse, so the artifact writes a blocker and no external-validation claim. Candidate-refinement gates likewise write blocker rows for AAP-3, SBP, acuity, hematemesis, nausea-alone, tachycardia duration, and pain representation.

The full-source NHAMCS screen applies the fixed active coefficient surface to two broader strict-binary endpoint cohorts without refitting: an endpoint-only full ED cohort and a non-trauma sensitivity cohort. This is a source-scope stress test only.

The fixed-prediction AUROC/Brier interval is a design-aware apparent-performance interval for the fitted educational model surface. It is not a bootstrap refit, optimism correction, external validation, or transportability test.

## Results

| Metric | Estimate | 95% interval | Method |
|---|---:|---:|---|
| AUROC | 0.713095 | 0.670617 to 0.757748 | Survey bootstrap replicate weights, fixed apparent predictions |
| Brier score | 0.097640 | 0.084632 to 0.111066 | Survey bootstrap replicate weights, fixed apparent predictions |

The grouped calibration file contains 10 weighted decile rows. The plot-data file repeats the decile means with identity-line coordinates for reviewer plotting.

| Internal-validation metric | Apparent estimate | Optimism-corrected estimate | Method |
|---|---:|---:|---|
| AUROC | 0.713095 | 0.704894 | 200 survey-bootstrap refits |
| Brier score | 0.097640 | 0.099565 | 200 survey-bootstrap refits |
| Calibration-in-the-large | 0.000000 | 0.012975 | 200 survey-bootstrap refits |
| Calibration slope | 1.000000 | 0.954089 | 200 survey-bootstrap refits |

Subgroup/missingness artifacts include age-band, predictor-availability, race/ethnicity, payer, region, and MSA rows. Race/ethnicity, region, and MSA are estimable. Payer includes sparse or no-outcome-variation blocker rows for small levels such as blank, no charge/charity, and worker's compensation. The MIMIC-IV-ED transportability row is `blocked_sparse_replication_only`.

Full-source scope screen overall rows:

| Screen | Strict-binary N | Events | Model-estimable N | AUROC | Brier | Status |
|---|---:|---:|---:|---:|---:|---|
| Endpoint-only full ED | 77,031 | 10,139 | 44,668 | 0.743845 | 0.097487 | `source_screen` |
| Non-trauma sensitivity | 50,070 | 7,447 | 29,096 | 0.745550 | 0.108448 | `source_screen` |

## Remaining Limits

- No external validation was added.
- No transportability claim was added; the MIMIC-IV-ED source-specific screen is blocked by sparse complete-case data.
- The full-source NHAMCS screen is not external validation because it remains within NHAMCS, and rows outside the active cohort are out-of-scope extrapolations from the active educational model.
- Race/ethnicity, payer, region, and MSA are carried into the pooled analytic cohort; remaining subgroup blockers are sparse-cell or no-outcome-variation blockers, not missing-field blockers.
- The 1,000-replicate AUROC/Brier interval workflow uses fixed apparent predictions and does not refit the model.
- The 200-replicate optimism correction is internal and does not replace external/source-specific validation.
- Subgroup calibration/performance rows are point estimates or blocker rows; subgroup interval estimation remains future work.
