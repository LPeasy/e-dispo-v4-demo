# ED Disposition Model e-dispo-v4.0 - Reviewer Report

Prepared for: Model reviewer  
Project: ED Disposition Personal Risk Model, e-dispo-v4.0  
Date: 2026-05-01

## 1. Executive Summary

This project is an educational class model. It estimates the probability that a narrow group of emergency department visits will end in one of two outcomes:

- `admit`: same-hospital hospitalization/admission.
- `treat_and_release`: routine home release.

The model applies only to adult men ages 18-64 who are already in the emergency department with non-traumatic abdominal pain. It is not a tool for deciding whether someone should go to the emergency department. It is not a diagnosis tool, triage tool, treatment recommendation, discharge recommendation, or clinical safety tool.

Plain-English translation: this model is a school project that asks, "For a very specific kind of ED patient, does this visit look more like a hospital admission or a routine release home?" It does not tell anyone what disease they have or what care they need.

## 2. What You Are Reviewing

You are reviewing three things:

1. The model concept: whether the question, population, outcome, inputs, and limitations are reasonable.
2. The technical implementation: whether the app and model logic match the written model plan.
3. The documentation: whether the model is explained honestly enough for a class project and does not overclaim clinical usefulness.

The main reviewer task is not to prove the model is clinically valid. The active coefficients are pooled NHAMCS educational estimates, not clinical estimates. Instead, the review should focus on whether the model is well-scoped, understandable, internally consistent, and honest about what is not yet proven.

Plain-English translation: please check whether the project is clear, consistent, and honest. Do not treat it like a finished hospital product.

## 3. Intended Use And Safety Boundary

### Intended Use

The intended use is a course demonstration of a transparent prediction-model workflow. The app shows how a structured worksheet can feed a simple logistic model, then display a probability estimate and uncertainty summary.

### Not Intended For

The model is not intended for:

- Diagnosis.
- Triage.
- Treatment decisions.
- Discharge planning.
- Real patient care.
- Deciding whether someone should seek emergency care.
- Estimating death risk.
- Estimating transfer risk as a primary outcome.

Plain-English translation: this is a model-building demo. It should never be used to make medical decisions.

## 4. Population Scope

The model is intentionally narrow.

Included population:

- Adult men.
- Ages 18-64.
- Already presenting to the emergency department.
- Non-traumatic abdominal pain.

Excluded before model output:

- Not already in the ED.
- Age under 18 or over 64.
- Non-male sex for this class version.
- Non-abdominal chief complaint.
- Trauma or injury-related abdominal pain.
- Red-flag statements selected in the app.

Plain-English translation: the model only covers one small slice of ED visits. If a case does not fit the slice, the app should block the result.

## 5. Outcome Definition

The model predicts a binary endpoint after disposition recoding:

| Model label | Technical meaning | Plain-English meaning |
|---|---|---|
| `admit` | Same-hospital hospitalization/admission, including direct same-hospital admission and observation -> hospitalized when documented. | The patient stayed in the same hospital. |
| `treat_and_release` | Routine home release through no follow-up planned, return to ED if needed, or outpatient follow-up. | The patient went home with routine follow-up instructions. |

Primary exclusions:

- Observation -> discharged.
- Transfer.
- Death/DOA/died in ED.
- AMA, LWBS, LBTC, elopement.
- Other, unknown, missing, blank, or conflicting dispositions.

Sensitivity-only endpoints:

- Sensitivity A: counts observation -> discharged as eventual home release.
- Sensitivity B: counts acute-hospital transfer as acute-care escalation.

Plain-English translation: the main model compares "hospitalized here" versus "sent home routinely." Messier outcomes, like transfer or leaving before care is complete, are not forced into the main two buckets.

## 6. Why Endpoint Recoding Matters

ED disposition data often has many possible outcomes. Some outcomes are not interchangeable. For example, a transfer to another hospital is not the same thing as admission to the same hospital. Death is also not just a stronger version of admission; it is a rare sentinel outcome and would require a different model.

The endpoint-refined v3 model keeps the active app binary but uses a more careful definition:

- Same-hospital admission and observation -> hospitalized are positive outcomes.
- Routine home-release pathways are negative outcomes.
- Observation -> discharged is excluded from the primary endpoint because it is not a routine ED discharge, even though the final destination is home.
- Transfer is excluded from the primary endpoint because it can depend heavily on hospital resources, bed availability, specialty access, and system operations.
- Death/DOA/died-in-ED is excluded and disclosed as a limitation, not predicted.

Plain-English translation: the model avoids mixing apples and oranges. It only compares two outcomes that are similar enough to compare cleanly.

## 7. Model Inputs

The worksheet collects seven inputs, but `e-dispo-v4.0` uses only the reduced empirical subset for P(admit):

| Input | Example categories | Why it is included |
|---|---|---|
| Age band | 18-29, 30-44, 45-54, 55-64 | Age is a basic risk/context variable. |
| Broad pain region | Upper, lower, diffuse/hard to pinpoint | Abdominal pain location may relate to disposition patterns. |
| Pain severity | Mild, moderate, severe | Severe pain is active; mild and moderate are collapsed as non-severe. |
| Onset/duration | Sudden <24h, gradual <24h, 1-7 days, >7 days, unknown | Timing may help describe acuity. |
| Pain pattern | Constant, intermittent, unknown | Pattern may help describe symptom behavior. |
| Vomiting | Yes, no, unknown | Associated symptom proxy. |
| Fever | Yes, no, unknown | Associated symptom proxy. |

Plain-English translation: the worksheet uses broad symptom facts, not a full medical chart. The active probability model uses only the empirically supported subset.

## 8. Model Form

The model uses logistic regression.

Technical equation:

```text
logit(P(admit)) = intercept + sum(beta_i * predictor_i)
P(treat_and_release) = 1 - P(admit)
```

What that means:

- Active coefficients are exact age, severe pain status, fever/temperature proxy, vomiting, and tachycardia burden.
- Excluded worksheet inputs and AAP-3 do not change P(admit).
- The model adds the active effects together.
- The logistic function converts the total into a probability between 0 and 1.
- The release-home probability is calculated as the complement of admission probability, but only after the binary endpoint rules are applied.

Important coefficient status:

- The active app model is `e-dispo-v4.0`.
- Active coefficients are dataset-derived from the pooled NHAMCS 2018-2022 educational cohort, with app-side schema gates.
- Severe pain is active only as `pain_severe = 1[pain_bin3 == severe]`; mild and moderate are collapsed as non-severe.
- The coefficients are not validated clinical estimates.

Plain-English translation: the math is a weighted scoring system that turns selected inputs into a probability. The active weights come from a bounded educational refit, not from a clinically validated hospital decision model.

## 9. Uncertainty Method

The app uses Latin Hypercube Sampling with 100,000 samples and a fixed seed. This is a structured simulation method that samples plausible coefficient values and shows how much the output could move if the assumed coefficients vary.

The app reports:

- Median predicted probability.
- 80% simulation interval.
- 95% simulation interval.
- Histogram of sampled probabilities.
- Sensitivity ranking showing which parameters move the output the most.

Important limitation:

These are model/simulation uncertainty intervals. They are not clinical confidence intervals and do not prove accuracy against real patients.

Plain-English translation: the app does not just give one number. It also shows how shaky that number might be if the assumed model weights are off.

## 10. Data Sources And Empirical Status

The project documents three relevant data paths:

| Source | Role in project | Main limitation |
|---|---|---|
| NHAMCS 2022 ED public-use file | Course-friendly public path for endpoint and cohort documentation. | Some symptom predictors are proxy-only or unavailable. |
| NEDS | Stronger large-scale ED endpoint source. | Less open/free and weaker for symptom detail. |
| MIMIC-IV-ED | Richer ED workflow and symptom-proxy prototyping. | Credentialed access and not nationally representative. |

The app includes an offline NHAMCS pipeline plan. Raw NHAMCS data is not bundled. The active `e-dispo-v4.0` artifact requires documented cohort counts, endpoint counts, missingness handling, coefficient estimates, covariance/draw outputs, calibration metrics, predictor support notes, and limitations.

Plain-English translation: the project has a realistic path toward real-data support, but the current app has not yet completed that path.

## 11. App Implementation Summary

The app is a static React/Vite/TypeScript web application. It has no backend, no login, no database, and no patient data storage.

Main app areas:

- Model Demo: guided workflow for eligibility, worksheet review, simulation results, and report summary.
- Documentation: model card, parameter evidence, endpoint recoding, NHAMCS appendix, uncertainty method, bias/applicability, reporting checklist, QA evidence, and sources.

Technical safeguards:

- Eligibility gate blocks out-of-scope cases.
- Worksheet validation requires all class-model fields.
- Probability outputs are bounded between 0 and 1.
- Worker-based simulation avoids blocking the UI.
- Schema gate prevents unsupported empirical coefficient labels.

Plain-English translation: the app is self-contained and mostly safe as a demo because it does not collect patient data or claim to be clinically validated.

## 12. Key Limitations

The reviewer should pay special attention to these limitations:

- The model is not clinically validated.
- The active coefficients are educational NHAMCS-derived estimates, not clinical estimates.
- The population is narrow.
- Some predictors may not be well-supported in public datasets.
- The model predicts disposition, not disease severity.
- Admission is affected by medical factors and system factors.
- Transfer, death, observation discharge, and incomplete-care exits are not active primary predictions.
- Apparent calibration and discrimination are reported for educational review, but no external validation or clinical validity claim is made.

Plain-English translation: the model is useful as a structured class project, but it is not ready for clinical use.

## 13. What Feedback Is Needed

Please provide feedback on:

- Whether the model question is clear.
- Whether the population scope is clear and reasonable.
- Whether the outcome recoding makes sense.
- Whether the exclusions are understandable.
- Whether the seven inputs are reasonable for a simple class model.
- Whether the app explains its limits clearly enough.
- Whether any wording sounds like medical advice.
- Whether the reviewer checklist identifies the right issues.
- Whether the documentation would let another person understand and reproduce the project.

Plain-English translation: we need feedback on clarity, honesty, scope, and whether the model story holds together.

## 14. Bottom-Line Review Question

The most important question for the reviewer:

Does this project clearly and honestly present an educational endpoint-refined ED disposition model, without overstating what the current prototype can prove?

If the answer is no, please identify exactly what wording, model assumption, app behavior, or missing document needs to change.
