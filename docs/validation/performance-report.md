# Pooled Empirical Model Performance Report

This report summarizes the active reduced empirical model implemented as `e-dispo-v4.0`.

The model is for educational/statistical use only. It is not clinical decision support, medical advice, a triage tool, or a discharge-safety tool.

## Model Status

- Model ID: `e-dispo-v4.0`
- Dataset: `NHAMCS_2018_2022_POOLED`
- Endpoint: same-hospital admission vs routine home discharge after exclusions
- Population: adult men ages 18-64, ED, non-traumatic abdominal pain
- Empirical activation: active for educational use after app-side export validation
- Formula: `admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden`
- Age transformation: `age_centered = age - 42`
- Tachycardia transformation: `tachycardia_burden = max(HR - 100, 0) / 10`
- Pain transformation: `pain_severe = 1[pain_bin3 == severe]`; mild and moderate are collapsed as non-severe.
- Pain monotonicity verdict: `nonmonotonic_collapsed_to_severe_binary`
- Missingness handling: observed pain and observed HR are required; HR missing is not treated as normal.

## Cohort Snapshot

- Complete-case unweighted N for `e-dispo-v4.0` fit: 2,674
- Admission events in complete-case `e-dispo-v4.0` fit: 307
- Full strict binary pooled NHAMCS N before complete-case restriction: 3,805
- Full strict binary pooled NHAMCS admission events before complete-case restriction: 459
- Event-count gate: passed

## Apparent Performance

- AUROC/C-statistic: 0.713
- Brier score: 0.0976
- Observed prevalence: 11.75%
- Mean predicted probability: 11.75%
- Calibration intercept: approximately 0.000
- Calibration slope: approximately 1.000

On the same complete-case cohort, the severe-only pain model had AUROC 0.713095 and Brier 0.097640. The current flexible pain comparator had AUROC 0.713136 and Brier 0.097694; the no-pain comparator had AUROC 0.701754 and Brier 0.098208. Leave-one-year-out mean performance favored severe-only pain over the flexible pain comparator: AUROC 0.705185 vs 0.695440 and Brier 0.098783 vs 0.099243.

The prevalence-only Brier score for the exported observed prevalence is approximately 0.104. The active model Brier score of 0.0976 is an absolute improvement of about 0.006. This is useful signal for a small educational model, but it is not a large error-reduction gain.

## Coefficient Interpretation

Approximate odds ratios from the exported coefficients:

| Term | Beta | Approximate OR | Interpretation boundary |
|---|---:|---:|---|
| `age_centered` | 0.043 | 1.04 per year; 1.54 per decade | Direct age signal inside the narrow adult male cohort. |
| `pain_severe` | 0.522 | 1.69 | Severe vs non-severe pain signal; not a monotonic pain dose response. |
| `fever_or_temp` | 0.887 | 2.43 | Fever/temperature proxy remains positive, with a large standard error. |
| `vomiting_present` | 0.469 | 1.60 | Ordinary vomiting RFV/symptom proxy is active. |
| `tachycardia_burden` | 0.427 | 1.53 per 10 bpm over 100 | Observed HR signal; missing HR blocks the `e-dispo-v4.0` estimate. |

## Predictive-Power Finding

The `e-dispo-v4.0` model has moderate discrimination and coherent apparent calibration in the exported pooled dataset. Its severe-only pain term retains essentially all flexible-pain discrimination while removing the imprecise mild-vs-moderate contrast. Its predictive power is enough to demonstrate endpoint recoding, evidence-gated coefficients, a defensible observed physiologic input, and transparent probability calculation. It is not strong enough to support individual-level clinical action, safety claims, triage claims, or deployment claims.

The exact calibration intercept and slope should be read as an apparent/exported calibration check, not as proof of transportability. External validation, subgroup performance, and interval estimates remain required before any stronger claim.

## Usability Finding

The active empirical input set remains simple but now requires one numeric vital sign: exact age, severe-vs-non-severe pain status, fever/temperature proxy, vomiting, and observed HR. The HR rule is understandable in the UI because values at or below 100 contribute zero and each 10 bpm above 100 adds one tachycardia-burden unit.

Current usability limitations:

- The UI still displays excluded prototype controls. They are labeled as excluded, but users may still expect them to affect the empirical probability.
- Pain missingness was removed from the active model by requiring observed pain; the app should not silently treat missing pain as non-severe.
- Missing HR blocks the `e-dispo-v4.0` empirical estimate because NHAMCS missing HR is not normal HR.
- Unknown fever or vomiting does not activate the empirical yes coefficient. Unknown should not be interpreted as confirmed absence.
- AAP-3 is useful as an explanatory acuity proxy, but it is not dataset-derived and does not change P(admit).
- NHAMCS has one `PULSE` value, so tachycardia duration is not feasible in this source.
- The model applies only after the strict scope and endpoint rules. It is not designed for patients outside the narrow adult male, non-traumatic abdominal pain cohort.

## Recommended Next Work

1. Keep excluded prototype controls visually separated from the empirical input set.
2. Add grouped calibration tables or plots and interval estimates for AUROC and Brier score.
3. Add subgroup and proxy-availability checks for age band, race/ethnicity, payer, region, pain availability, and HR availability.
4. Validate AAP-3 against NHAMCS `IMMEDR` or MIMIC-IV-ED triage acuity before allowing it to affect risk.
5. Treat tachycardia duration as a later MIMIC-only question that requires timestamp-preserving vital-sign extraction.
