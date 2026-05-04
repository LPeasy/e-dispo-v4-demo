# E-Dispo Prototype Web App

This is a Vite + React + TypeScript educational/statistical app for reviewing ED disposition models.

The app estimates `P(admit)` for adult men ages 18-64 who are already in the emergency department with non-traumatic abdominal pain. Here, `admit` means same-hospital admission or hospitalization after explicit endpoint exclusions.

The app is not medical advice. It is not diagnosis, triage, treatment guidance, discharge guidance, or clinical decision support.

## Public Site Variants

The repo now supports two separate static builds from the same codebase:

- `e_dispo_v4`: current E-Dispo educational app behavior for the adult-male non-traumatic abdominal-pain model workstream.
- `general_e_dispo`: separate `general-E-Dispo-model-v1-sex-adjusted` runnable demo for all-sex/all-age NHAMCS non-trauma records.

The general model is parallel. It does not replace the abdominal-pain model and does not create external validation, transportability, or clinical-use evidence.

The GitHub Pages workflow builds the default root app plus both named subdirectory builds before uploading `dist/`.

## Current Active Model

The current active model is the reduced pooled NHAMCS 2018-2022 `e-dispo-v4.1-pas5-high-acuity-surrogate` model:

```text
e-dispo-v4.1-pas5-high-acuity-surrogate
```

In plain English, the active estimate uses:

- exact age, centered at 42
- observed severe pain status, with mild and moderate treated as non-severe
- fever or objective temperature proxy
- vomiting
- observed heart rate as `tachycardia_burden = max(HR - 100, 0) / 10`
- PAS-5 `high_acuity_proxy`, where A1/A2 activate the term and A3/A4/A5 are reference

Missing pain and missing heart rate do not silently become normal or reference values. The v4.1 empirical estimate requires observed pain and observed heart rate.

The v4 pain term does not claim a monotonic pain dose-response. It uses `pain_severe` because the previous flexible mild/moderate contrast was imprecise while severe pain retained useful signal.

Unknown fever or vomiting does not activate the empirical "yes" coefficient and should not be read as confirmed absence.

PAS-5 is bridged through NHAMCS `IMMEDR` clinician-acuity surrogate evidence because direct PAS-5 patient answers are not observed in NHAMCS.

## What Is Not Active

These concepts do not affect current `P(admit)`:

- broad pain region
- onset or duration
- constant versus intermittent pain pattern
- hematemesis
- direct clinician acuity
- systolic blood pressure
- the E-Dispatch arcade easter egg

They may appear in documentation as explanation, historical context, or future work. They are not active model inputs.

## Outcome

`admit` means same-hospital hospitalization or admission, including observation -> hospitalized when documented.

`treat_and_release` means routine release home.

Excluded from the primary binary endpoint:

- observation -> discharged
- transfer
- death, expired, dead on arrival, or died in ED
- AMA, LWBS, LBTC, elopement
- other, unknown, missing, blank, or conflicting dispositions

`P(treat_and_release) = 1 - P(admit)` is valid only after applying the strict binary endpoint rules.

## Model Method

The app uses transparent logistic regression. A logistic regression model combines inputs and converts them into a probability between 0 and 1.

The app's uncertainty view keeps the selected user inputs fixed and samples full coefficient vectors from bundled joint coefficient draws. This is used for selected-run model uncertainty. It does not resample different patients from the source population.

The simulation runs in a Web Worker and reports:

- median estimate
- 80% interval
- 95% interval
- histogram
- sensitivity ranking

All intervals are model/simulation uncertainty ranges, not clinical confidence guarantees.

## Stack

- Vite + React + TypeScript
- Tailwind CSS v4
- shadcn/ui source components
- Recharts
- static deployment target

## Local Commands

Run commands from this folder.

```powershell
npm run dev
npm run test
npm run lint
npm run build
npm run build:v4
npm run build:general
npm run build:all-sites
npm run check:dist
```

On this workstation, a local npm wrapper and bundled Node runtime may be needed:

```powershell
$env:Path = "C:\Users\lawto\Documents\10_Projects\Models\ED_Disposition_PersonalRiskModel\.tools\bin;C:\Users\lawto\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin;" + $env:Path
npm run test
npm run lint
npm run build
npm run build:v4
npm run build:general
npm run build:all-sites
npm run check:dist
```

## Reviewer Package

Build the current-model reviewer package with:

```powershell
python scripts/build_reviewer_package.py
```

The package is written for an educated non-technical reviewer. It includes a plain-language report, reviewer checklist, glossary, static app build, current-model evidence artifacts, QA evidence, and selected source extracts.

The app build must be served over HTTP. Do not open the built `index.html` with `file://`.

## Documentation

Key documents:

- `docs/model-card.md`
- `docs/class-deliverable-package.md`
- `docs/validation/performance-report.md`
- `docs/validation/predictive-power-usability-review.md`
- `docs/validation/nausea-candidate-screen.md`
- `docs/validation/uncertainty-simulation-method.md`
- `docs/reviewer/model-review-report.md`
- `docs/reviewer/model-reviewer-checklist.md`
- `docs/reviewer/current-model-glossary.md`

Raw NHAMCS data is not bundled. Reviewed derived artifacts can be included in the reviewer package, but raw public-use files stay outside the app and package.

## Source Grounding

- CDC NHAMCS documentation: https://www.cdc.gov/nchs/nhamcs/documentation/index.html
- 2022 NHAMCS ED documentation: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/dataset_documentation/nhamcs/doc22-ed-508.pdf
- TRIPOD+AI: https://www.bmj.com/content/385/bmj-2023-078378
- PROBAST+AI: https://www.bmj.com/content/388/bmj-2024-082505
- CDC Clear Communication Index: https://www.cdc.gov/ccindex/
