# Endpoint Refinement Decision Log

Date: 2026-04-28

## Active Decision

The active class-project model remains baseline v3 with an endpoint-recoding refinement. It is not a v4 model and does not change the seven predictors, model form, coefficients, or uncertainty method.

The active endpoint is routine home release versus same-hospital hospitalization/admission.

## Primary Endpoint

Positive class:
- Same-hospital inpatient admission.
- Observation -> hospitalized.

Negative class:
- No follow-up planned.
- Return to ED if needed.
- Return/refer outpatient follow-up.

Primary exclusions:
- Observation -> discharged.
- Transfer.
- Death/DOA/died in ED.
- AMA, LWBS, LBTC, elopement.
- Other, unknown, missing, blank, and conflicting dispositions.

## Sensitivity Endpoints

Sensitivity A is report-only and treats observation -> discharged as eventual home release.

Sensitivity B is report-only/future work and treats acute-hospital transfer as acute-care escalation.

Death/DOA/died-in-ED remains a sentinel exclusion. The app does not estimate or display death probability.

## Coefficient Rule

No coefficient may be promoted to `dataset_derived` because of this endpoint recoding update alone. Promotion requires a refined analytic cohort, refit coefficients, documented uncertainty, calibration reporting, and reviewed predictor support.
