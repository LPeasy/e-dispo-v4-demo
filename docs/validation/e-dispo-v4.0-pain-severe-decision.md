# e-dispo-v4.0 Pain Representation Decision

Date: 2026-05-01

## Decision

Use `pain_severe = 1[pain_bin3 == severe]` in the active educational model `e-dispo-v4.0`.

Do not use the old flexible active pain setup as the active model term. Preserve the prior v2 artifact as archived evidence only.

## Statistical Rationale

The comparison uses the same pooled NHAMCS 2018-2022 complete-case cohort used by the active tachycardia-burden model: observed pain, fever/temperature proxy, vomiting, HR, and strict binary endpoint.

| Model | AUROC | Brier |
|---|---:|---:|
| No pain comparator | 0.701754 | 0.098208 |
| Severe-only pain | 0.713095 | 0.097640 |
| Flexible `pain_bin3` comparator | 0.713136 | 0.097694 |

The severe-only adjusted coefficient is positive and finite: beta 0.522, SE 0.184, OR 1.69, p=0.0048.

The flexible mild-vs-moderate contrast is not useful: beta 0.180, SE 0.327, OR 1.20, p=0.58 in the prior active comparator.

Leave-one-year-out mean performance favors severe-only pain over flexible pain: AUROC 0.705185 vs 0.695440 and Brier 0.098783 vs 0.099243.

## Logical Rationale

The unadjusted pain rates are nonmonotonic: mild is higher than moderate, and severe is highest. That pattern does not support language that admission risk rises monotonically from mild to moderate to severe.

Collapsing mild and moderate into non-severe is logically cleaner because it keeps the empirically supported severe-pain signal while refusing to overinterpret the unsupported mild/moderate contrast.

## Evidence Boundary

The active model may say:

- Severe pain is associated with higher fitted admission odds than non-severe pain in this pooled NHAMCS educational cohort.
- Mild and moderate pain are collapsed as non-severe in `e-dispo-v4.0`.
- The model remains educational/statistical only.

The active model must not say:

- Pain has a monotonic dose response.
- The model is clinical decision support.
- The model is diagnostic, triage, discharge-planning, or medical-advice software.
- Missing HR is normal HR.
- Missing pain is non-severe pain.

## Reproducibility

The versioned validation script is:

```powershell
cd C:\Users\lawto\Documents\10_Projects\Models\ED_Disposition_PersonalRiskModel\e-dispo-prototype
$env:NHAMCS_R_LIBS = (Resolve-Path .\r-lib).Path
& 'C:\Program Files\R\R-4.6.0\bin\Rscript.exe' `
  scripts\nhamcs\nhamcs_e_dispo_v4_pain_severe_validation.R `
  outputs\nhamcs_pooled\analytic_cohort_nhamcs_2018_2022.csv `
  outputs\nhamcs_pooled
```

Required outputs include coefficient, covariance, draw, calibration, cell-count, leave-one-year-out, and report files with the prefix `e_dispo_v4_pain_severe_`.
