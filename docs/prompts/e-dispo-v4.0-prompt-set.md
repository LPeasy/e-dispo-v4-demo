# e-dispo-v4.0 Structured Prompt Set

Use this prompt set when assigning or auditing the `e-dispo-v4.0` severe-pain implementation.

## Prompt 1: Intent Lock

You are updating the ED disposition educational model for adult men ages 18-64 already in the ED with non-traumatic abdominal pain. The new model version is `e-dispo-v4.0`.

Intent:

- Preserve the prior active v2 model as archived evidence.
- Make `e-dispo-v4.0` the active educational app model.
- Replace active flexible pain terms with `pain_severe = 1[pain_bin3 == severe]`.
- Keep mild and moderate pain collapsed as non-severe.
- Keep exact age, fever/temperature proxy, vomiting, and tachycardia burden as active terms.
- Maintain all safety language: educational/statistical only; not clinical decision support, diagnosis, triage, treatment, discharge-planning, or medical advice.

Clarifying-question rule:

- Ask only if the requested scope would change the active endpoint, population, evidence label, or model version name.
- Otherwise proceed with the defaults above.

## Prompt 2: Evidence And Fitting Process

Use the same complete-case pooled NHAMCS 2018-2022 analytic cohort as the active tachycardia-burden model.

Fit and compare these models on identical rows:

- `no_pain`: `admit ~ age_centered + fever_or_temp + vomiting_present + tachycardia_burden`
- `e-dispo-v4.0`: `admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden`
- `flexible_pain_comparator`: `admit ~ age_centered + pain_bin3 + fever_or_temp + vomiting_present + tachycardia_burden`

Required outputs:

- Formula and transformations.
- Complete-case N and event count.
- Severe, non-severe, mild, and moderate cell counts.
- Coefficients, standard errors, odds ratios, and p-values.
- Survey covariance matrix.
- Deterministic coefficient draws with recorded seed.
- AUROC, Brier score, mean predicted probability, observed prevalence, calibration intercept, and calibration slope.
- Leave-one-year-out AUROC/Brier comparisons.
- A decision note that explains why severe-only pain is active and why monotonic pain language is prohibited.

Decision rule:

- Activate severe-only pain if it preserves flexible-pain discrimination, does not worsen Brier score materially, has a positive adjusted severe coefficient, and avoids unsupported monotonic claims.
- Do not label any term `dataset_derived` unless all required evidence fields are present or reproducible from a committed script.

## Prompt 3: App Implementation

Implement `e-dispo-v4.0` as a new versioned app artifact.

Required app behavior:

- Default prediction uses `e-dispo-v4.0`, not the archived v2 artifact.
- Active pain behavior is binary: severe adds the `pain_severe` coefficient; mild and moderate add no pain term.
- Missing pain blocks the empirical estimate.
- Missing HR blocks the empirical estimate.
- Unknown fever and vomiting do not activate the yes indicators and are not treated as confirmed absence.
- AAP-3 and excluded prototype fields must not change P(admit).

Required source updates:

- Add a versioned model artifact for `e-dispo-v4.0`.
- Keep the prior v2 artifact available for archived validation/tests.
- Update artifact validation to accept `e-dispo-v4.0` and require exactly the v4 active coefficient keys.
- Update prediction tests for severe-only pain and archived v2 behavior.
- Update in-app copy, model metadata, documentation data, and parameter evidence wording.

## Prompt 4: Documentation And Acceptance

Update all source documentation that describes the active model.

Required wording:

- Say `e-dispo-v4.0`.
- Say `pain_severe = 1[pain_bin3 == severe]`.
- Say mild and moderate are collapsed as non-severe.
- Say this is not a monotonic pain dose-response claim.
- Say observed pain and observed HR are required.
- Say the model remains educational/statistical only.

Acceptance checks:

- `npm run test`
- `npm run lint`
- `npm run build`
- Run the v4 R validation script when the pooled analytic cohort and repo-local R library are available.

Do not close the task if:

- The app still describes the active pain term as flexible/nonmonotonic.
- The active model ID remains the old v2 ID.
- Missing pain or missing HR is silently treated as a reference value.
- AAP-3 or prototype controls affect P(admit).
- Documentation implies clinical deployment, triage, diagnosis, discharge safety, or medical advice.

## Defaults Chosen

- Active version name: `e-dispo-v4.0`.
- Active formula: `admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden`.
- Pain reference: non-severe, composed of mild plus moderate observed pain.
- Prior model handling: retain as archived v2 artifact and comparator, not active default.
- Evidence label: `dataset_derived` only for the refitted v4 terms with reproducible coefficient/covariance/draw/calibration outputs.
