# AAP-3 Validation Workflow Design

## Status

AAP-3 is a `prototype_acuity_proxy`. It is explanatory only and must not affect the active pooled NHAMCS admission estimate until the promotion rule below is satisfied.

AAP-3 is patient/survey-derived. NHAMCS `IMMEDR` and MIMIC-IV-ED triage acuity are clinician/triage-derived. Validation may test alignment, but must not claim these constructs are identical.

## Public-Source Targets

Primary public-source target:

```text
NHAMCS IMMEDR
```

Potential richer target:

```text
MIMIC-IV-ED triage acuity
```

NHAMCS fields already harmonized for future mapping:

```text
IMMEDR -> acuity
TEMPF -> temp / fever_or_temp
PULSE -> HR
BPSYS -> SBP
```

MIMIC-IV-ED may support richer triage variables:

```text
temperature
heart rate
respiratory rate
oxygen saturation
SBP/DBP
pain
acuity
chief complaint
```

## Required Prespecification Before Fitting

Before any model with AAP-3 is fit, create a versioned mapping that states:

- how each app AAP-3 answer maps to NHAMCS and/or MIMIC fields
- how missing vitals are represented, preserving that unknown vitals are not normal vitals
- how `P(A1)` through `P(A5)` are computed from mapped answers
- whether the Q1-5 low-acuity guardrail is used unchanged
- how source-specific missingness is handled

## Planned Outputs

Future scripts should write:

```text
outputs/aap3_validation/aap3_vs_immedr_distribution.csv
outputs/aap3_validation/aap3_calibration_against_immedr.csv
outputs/aap3_validation/aap3_admission_model_comparison.csv
outputs/aap3_validation/aap3_validation_report.md
```

## Candidate Model Comparison

Current empirical model:

```text
admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden
```

AAP-3 augmented candidate:

```text
admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden
      + P(A1) + P(A2) + P(A4) + P(A5)
```

Use `A3` as the reference class. Do not fit this as a final model until the AAP-3-to-data mapping is prespecified.

## Promotion Rule

AAP-3 may affect empirical risk only if all are true:

- mapping from app answers to validation data is prespecified
- AAP-3 aligns directionally with IMMEDR or MIMIC triage acuity
- AAP-3 improves or preserves calibration
- AAP-3 does not materially degrade Brier score or AUROC
- coefficients and uncertainty are exported
- leave-one-year-out or source-specific validation is acceptable
- evidence engine assigns a non-prototype tier

Until then, AAP-3 remains `prototype_acuity_proxy`.
