# Full-Source NHAMCS Scope Screen

Date: 2026-05-03

Active app model: `e-dispo-v4.1-pas5-high-acuity-surrogate`

This note documents a source-scope stress test of the fixed active educational model. It is not external validation, transportability evidence, clinical decision support, triage software, diagnosis, treatment advice, or a model update.

## Method

The pipeline now builds two parallel pooled NHAMCS 2018-2022 strict-binary endpoint cohorts from the full source files:

- `outputs/nhamcs_pooled/full_source_endpoint_cohort_nhamcs_2018_2022.csv`
- `outputs/nhamcs_pooled/full_source_nontrauma_cohort_nhamcs_2018_2022.csv`

The endpoint-only full ED screen removes the active model's age, sex, abdominal-pain, and trauma filters, then keeps only records with the same strict admit-vs-routine-home-discharge endpoint. The non-trauma sensitivity screen removes age, sex, and abdominal-pain filters but retains the non-trauma restriction.

Both screens apply the fixed predecessor `e-dispo-v4.0` coefficients without refitting. They remain archived source-scope stress tests. Active v4.1 additionally requires PAS-5/IMMEDR availability for `high_acuity_proxy`, so these older fixed-coefficient screens should not be read as the current v4.1 validation result. Sparse cells, no-outcome-variation slices, missing source cohorts, and no-complete-case slices are written as explicit blocker/status rows.

## Outputs

- `outputs/nhamcs_pooled/e_dispo_v4_full_source_endpoint_screen_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_endpoint_screen_calibration.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_endpoint_screen_missingness.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_nontrauma_screen_performance.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_nontrauma_screen_calibration.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_nontrauma_screen_missingness.csv`
- `outputs/nhamcs_pooled/e_dispo_v4_full_source_scope_screen_report.md`

## Overall Results

| Screen | Strict-binary N | Events | Model-estimable N | Model-estimable events | AUROC | Brier | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| Endpoint-only full ED | 77,031 | 10,139 | 44,668 | 5,429 | 0.743845 | 0.097487 | `source_screen` |
| Non-trauma sensitivity | 50,070 | 7,447 | 29,096 | 4,035 | 0.745550 | 0.108448 | `source_screen` |

Performance rows include scope slices for active-scope membership, adult male age 18-64 membership, full age band, sex, abdominal-pain RFV flag, non-trauma flag, and active predictor availability. Calibration rows use weighted predicted-probability deciles where event support is adequate.

## Interpretation Boundary

These screens show how the fixed educational coefficient surface behaves on broader NHAMCS records under the same strict endpoint definition. They do not validate the model for children, women, older adults, trauma presentations, non-abdominal presentations, or general ED use. They also do not establish external validation because the source remains NHAMCS.

The active model population remains adult men ages 18-64 in the ED with non-traumatic abdominal pain. No coefficient, predictor, app behavior, or transportability claim is promoted by this artifact.
