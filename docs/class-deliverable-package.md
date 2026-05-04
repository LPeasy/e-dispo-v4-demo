# Class Deliverable Package

This app is the course-ready `e-dispo-v4.1-pas5-high-acuity-surrogate` educational/statistical model for ED disposition modeling in adult men ages 18-64 already in the ED with non-traumatic abdominal pain.

## Required Work Products

- Runnable static web app: `npm run dev`, `npm run test`, `npm run lint`, and `npm run build`.
- Model card: `docs/model-card.md`.
- Endpoint decision log: `docs/endpoint-refinement-decision-log.md`.
- NHAMCS technical appendix path: `docs/nhamcs-pipeline.md` and `scripts/nhamcs/`.
- In-app documentation pages: overview, model card, parameter evidence, endpoint recoding, NHAMCS appendix, uncertainty method, bias/applicability, reporting checklist, QA evidence, and sources.
- Browser QA evidence: historical screenshots in `docs/qa/` and fresh endpoint-refined Playwright captures in `output/playwright/`.

## Submission Position

The app estimates `P(admit)` as shorthand for same-hospital hospitalization/admission among comparable endpoint-refined binary-disposition ED visits. `P(treat_and_release)` is derived as the complement only inside that primary binary analytic cohort.

The current active estimate uses the reduced pooled NHAMCS 2018-2022 empirical export `e-dispo-v4.1-pas5-high-acuity-surrogate` for educational use only. No clinical validity, external validation, diagnosis, triage, treatment, discharge-planning, or medical-advice claim is made.

Predictive power is moderate and limited: exported AUROC is 0.759 and Brier score is 0.0913 in the PAS-5/IMMEDR complete-case screen. On the same subset, the base refit without `high_acuity_proxy` had AUROC 0.736 and Brier 0.0938. This is enough for a transparent class demonstration, not for clinical action.

## Empirical Readiness Gate

The active NHAMCS-derived app export includes the reduced coefficient set, uncertainty fields, calibration/discrimination metrics, and evidence-tier assignments required for educational activation. The `e-dispo-v4.1` estimate requires observed pain and observed HR; missing HR is not treated as normal.

PAS-5 is active only as `high_acuity_proxy`: A1/A2 activate the term and A3/A4/A5 are reference. NHAMCS does not contain direct PAS-5 patient answers, so the coefficient is bridged through `IMMEDR` as clinician-acuity surrogate evidence. Broad pain region, onset/duration, pain pattern, hematemesis, direct clinician acuity, SBP, and other prototype inputs remain excluded from the empirical estimate until separate evidence gates pass. Severe pain is the active pain signal; mild and moderate are collapsed as non-severe and no monotonic pain dose-response claim is made.
