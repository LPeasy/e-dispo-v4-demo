# e-dispo-v4.1 PAS-5 Surrogate Prompt Set

Use this prompt set when assigning or auditing the active `e-dispo-v4.1-pas5-high-acuity-surrogate` implementation.

## Intent Lock

Promote PAS-5 only as `high_acuity_proxy`: PAS-5 A1/A2 activate the term, and PAS-5 A3/A4/A5 are the reference side.

Maintain all safety language: educational/statistical only; not clinical decision support, diagnosis, triage, treatment, discharge-planning, or medical advice.

## Evidence Lock

Use `scripts/nhamcs/nhamcs_pas5_acuity_candidate_screen.R` and `outputs/nhamcs_pooled/analytic_cohort_nhamcs_2018_2022.csv`.

The active formula is:

```text
admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden + high_acuity_proxy
```

The PAS-5 coefficient is derived from NHAMCS `IMMEDR` as clinician-acuity surrogate evidence. NHAMCS does not contain direct PAS-5 patient answers.

## Acceptance Checks

- Active model ID is `e-dispo-v4.1-pas5-high-acuity-surrogate`.
- Active draw asset uses `outputs/nhamcs_pooled/pas5_acuity_draws_app.csv`.
- `high_acuity_proxy` is labeled `dataset_derived_surrogate` with `surrogate_source: "NHAMCS_IMMEDR"`.
- Direct v4.1 terms remain `dataset_derived`.
- Documentation states that this does not validate PAS-5 as direct patient self-assessment accuracy.
- `npm run test`, `npm run lint`, and `npm run build` pass.
