# Model Reviewer Checklist

Reviewer name: ______________________________  
Review date: ______________________________  
Version reviewed: e-dispo-v4.1-pas5-high-acuity-surrogate

## How To Use This Checklist

Please mark each item as:

- Pass: looks good.
- Needs revision: understandable, but should be changed.
- Not sure: unclear or reviewer needs more information.

Add comments wherever possible. Specific feedback is more useful than general approval.

## A. Big-Picture Model Scope

| Item | Pass | Needs revision | Not sure | Comments |
|---|---:|---:|---:|---|
| The model question is understandable. | [ ] | [ ] | [ ] | |
| The project is clearly presented as educational, not clinical. | [ ] | [ ] | [ ] | |
| The population is clear: adult men ages 18-64 already in the ED with non-traumatic abdominal pain. | [ ] | [ ] | [ ] | |
| The app blocks out-of-scope cases before showing model output. | [ ] | [ ] | [ ] | |
| The document makes clear that the model does not advise whether someone should seek emergency care. | [ ] | [ ] | [ ] | |

## B. Outcome And Endpoint Recoding

| Item | Pass | Needs revision | Not sure | Comments |
|---|---:|---:|---:|---|
| `admit` is clearly defined as same-hospital hospitalization/admission. | [ ] | [ ] | [ ] | |
| Observation -> hospitalized is included in `admit` when documented. | [ ] | [ ] | [ ] | |
| `treat_and_release` is clearly defined as routine home release. | [ ] | [ ] | [ ] | |
| Observation -> discharged is excluded from the primary endpoint. | [ ] | [ ] | [ ] | |
| Transfer is excluded from the primary endpoint. | [ ] | [ ] | [ ] | |
| Death/DOA/died-in-ED is treated as a sentinel exclusion, not predicted. | [ ] | [ ] | [ ] | |
| Conflicting or missing dispositions are excluded and not forced into a binary bucket. | [ ] | [ ] | [ ] | |
| Sensitivity A and Sensitivity B are clearly labeled as report-only/future-work endpoints. | [ ] | [ ] | [ ] | |

## C. Inputs And Model Logic

| Item | Pass | Needs revision | Not sure | Comments |
|---|---:|---:|---:|---|
| The active model inputs, including the five PAS-5 patient-perceived acuity questions, are easy to understand. | [ ] | [ ] | [ ] | |
| The model explains why it uses broad symptom categories rather than diagnosis. | [ ] | [ ] | [ ] | |
| The logistic regression equation is technically correct and understandable. | [ ] | [ ] | [ ] | |
| The report explains that active coefficients are dataset-derived for educational use only, not clinical estimates. | [ ] | [ ] | [ ] | |
| The complement rule, `P(treat_and_release) = 1 - P(admit)`, is limited to the refined binary cohort. | [ ] | [ ] | [ ] | |
| The uncertainty display is explained as model/simulation uncertainty, not clinical confidence. | [ ] | [ ] | [ ] | |

## D. Data And Evidence

| Item | Pass | Needs revision | Not sure | Comments |
|---|---:|---:|---:|---|
| The report identifies NHAMCS, NEDS, and MIMIC-IV-ED as possible data sources. | [ ] | [ ] | [ ] | |
| The report explains why NHAMCS is useful for the class project. | [ ] | [ ] | [ ] | |
| The report explains that not all symptom predictors are directly available in public datasets. | [ ] | [ ] | [ ] | |
| The app identifies `e-dispo-v4.1-pas5-high-acuity-surrogate` NHAMCS-derived coefficients as active only for educational display. | [ ] | [ ] | [ ] | |
| PAS-5 is labeled as `high_acuity_proxy` derived through NHAMCS `IMMEDR` surrogate evidence, not direct patient self-assessment validation. | [ ] | [ ] | [ ] | |
| The future empirical artifact requirements are clear. | [ ] | [ ] | [ ] | |

## E. App And Documentation Review

| Item | Pass | Needs revision | Not sure | Comments |
|---|---:|---:|---:|---|
| The app is navigable enough for a reviewer. | [ ] | [ ] | [ ] | |
| The Model Demo and Documentation areas are clearly separated. | [ ] | [ ] | [ ] | |
| The report summary does not sound like medical advice. | [ ] | [ ] | [ ] | |
| The documentation includes a model card, endpoint recoding, NHAMCS appendix, uncertainty method, QA evidence, and sources. | [ ] | [ ] | [ ] | |
| The portable package includes enough material to review the model without needing the full development workspace. | [ ] | [ ] | [ ] | |

## F. Required Reviewer Feedback

Please answer these directly.

1. What is the single biggest weakness of the model as currently presented?

   ____________________________________________________________________________

2. What wording, if any, sounds too clinical or too strong?

   ____________________________________________________________________________

3. Which endpoint/exclusion rule is most confusing?

   ____________________________________________________________________________

4. Which model input seems least justified?

   ____________________________________________________________________________

5. What would make the model easier to understand for a non-technical reviewer?

   ____________________________________________________________________________

6. Would you approve this as an educational class-project prototype after revisions?

   [ ] Yes
   [ ] Yes, with minor revisions
   [ ] No, major revisions needed
   [ ] Not sure

7. Final comments:

   ____________________________________________________________________________
