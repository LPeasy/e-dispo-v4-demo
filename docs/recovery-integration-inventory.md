# Recovery Integration Inventory

Date: 2026-05-01

## Canonical App

The working app is now `e-dispo-prototype`.

`ed-disposition-web-class` was left in place because Windows held a file lock during the folder rename. The class shell was copied into `e-dispo-prototype`, and all integration work in this pass was completed in the new folder.

## Retained From The Class Shell

- Customer-facing preview flow and reviewer-facing Use Model flow.
- Results input banner, run naming, saved runs, and compare dock.
- Portable static build settings with relative Vite asset paths.
- Worker-loaded coefficient draw asset with worker-side caching and request timeout behavior.
- Static dist portability check: `npm run check:dist`.
- Current reviewer-package tooling, updated to point at the v4 model artifacts.
- Hidden E-Dispatch arcade easter egg, including dashboard-style game window and optional muted audio controls.

## Ported From The V4 Recovery Source

- Active model export: `src/data/eDispoV4Model.ts`.
- Active empirical artifact validation: `src/data/empiricalArtifacts.ts`.
- Prediction logic: `src/model/pooledEmpiricalPrediction.ts`.
- v4 prediction tests: `src/model/pooledEmpiricalPrediction.test.ts`.
- v4 model metadata text: `src/model/modelParameters.ts`.
- v4 documentation data: `src/data/documentation.ts`.
- v4 validation script: `scripts/nhamcs/nhamcs_e_dispo_v4_pain_severe_validation.R`.
- v4 NHAMCS artifacts under `outputs/nhamcs_pooled/`.
- May 1 nausea-alone screen script, documentation, and generated `outputs/nhamcs_pooled/nausea_*` support artifacts.
- v4 reviewer and validation docs, including model card, performance report, predictive-power review, version manifest, and severe-pain decision note.

## Active Model State

The default active model is `e-dispo-v4.0`.

Formula:

```text
admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden
```

Pain handling:

- Severe pain activates `pain_severe`.
- Mild and moderate pain are the non-severe reference.
- Missing pain blocks the empirical estimate.
- Missing heart rate blocks the empirical estimate.
- The model does not claim a monotonic pain dose-response.

## Uncertainty Asset State

The app-bundled coefficient draw CSV now uses the v4 compact schema:

```text
draw_id,intercept,age_centered,pain_severe,fever_or_temp,vomiting_present,tachycardia_burden,seed
```

It is generated from the reviewed source artifact:

```text
outputs/nhamcs_pooled/e_dispo_v4_pain_severe_draws.csv
```

The generated app asset is:

```text
src/data/pooled-empirical-coefficient-draws.csv
```

The production build includes this CSV as a hashed Vite asset under `dist/assets/`.

## Archived V2 State

The prior v2 flexible-pain artifact remains in `src/data/pooledEmpiricalModel.ts` for explicit archived tests and historical comparison only. It is not the default active app model.

Remaining `pooled_empirical_v2`, `pain_bin3`, `flexible pain`, and `nonmonotonic_flexible_only` references are limited to archived v2 support code, historical validation notes, or explicit v4 decision rationale.

## Verified

- `npm run test`
- `npm run lint`
- `npm run build`
- `npm run check:dist`
- Browser check: app opens at `http://127.0.0.1:5173/`.
- Browser check: Use Model flow shows v4/severe-vs-non-severe copy.
- Browser check: default model run completes and exposes Run name / Save run controls.
- Browser check: missing HR blocks output with v4 wording.
- Browser check: Technical Docs show `e-dispo-v4.0` and the `pain_severe` formula.
- Browser check: hidden E-Dispatch game opens after repeated `PROTOTYPE` clicks and retains the dashboard-style modal.
