# Fidelity Ledger

Concept: `docs/design/ed-disposition-v3-concept.png`

Implementation screenshots:

- `docs/qa/demo-results.png`
- `docs/qa/stage-1-safety-dashboard.png`
- `docs/qa/stage-2-case-customization-dashboard.png`
- `docs/qa/stage-3-worksheet-dashboard.png`
- `docs/qa/stage-4-results-dashboard.png`
- `docs/qa/stage-5-report-dashboard.png`
- `docs/qa/documentation-parameter-evidence.png`
- `docs/qa/mobile-stage-2-case-customization.png`
- `docs/qa/mobile-stage-4-results-dashboard.png`
- `docs/qa/documentation-overview.png`
- `docs/qa/documentation-nhamcs.png`
- `docs/qa/mobile-documentation-sources.png`
- `docs/qa/desktop-results.png`
- `docs/qa/desktop-blocked.png`
- `docs/qa/mobile-safety.png`

## Verification Method

Browser plugin navigation/screenshot tooling was not exposed in this session, so QA used Playwright from the bundled Codex runtime with the locally installed Chrome executable. No Playwright browser download was installed.

Checked viewport sizes:

- Desktop: 1440 x 1000
- Mobile: 390 x 900

## Comparison Points

- Information architecture: updated to two top-level areas, `Model Demo` and `Documentation`.
- Required demo states: safety gate, intake, worksheet review, simulation results, and report summary are implemented as navigable app states.
- Dashboard shell: each demo stage has a consistent stage header and desktop case-summary rail; mobile stacks the rail below the active stage content.
- Case customization: age band is derived from eligibility age, and the seven current predictors remain the only forward-facing inputs.
- Required documentation states: overview, model card, endpoint recoding, NHAMCS appendix, uncertainty method, bias/applicability, reporting checklist, QA evidence, and sources are implemented as navigable pages.
- Parameter evidence: documentation includes dose-response mapping, effect-distribution evidence tiers, source anchors, limitations, and empirical readiness for all seven predictors.
- Copy discipline: above-the-fold copy remains limited to the project scope, educational limitation, status badges, and workflow labels.
- Safety behavior: red-flag selection blocks probability output and shows `Blocked: out of scope`.
- Probability framing: `P(treat_and_release)` is derived only after the gate and binary recoding language is visible.
- Uncertainty display: results include median, 80% interval, 95% interval, histogram, and sensitivity ranking labeled as model/simulation uncertainty.
- Worker behavior: browser QA confirmed the 100,000-sample worker calculation shows a loading state before completion.
- Documentation artifact gate: NHAMCS-derived labels remain hidden while the coefficient artifact is absent or invalid.
- Responsive behavior: mobile stacks navigation, workflow, and documentation pages without table clipping in the checked documentation state.

## Intentional Deviations

- The generated concept used some clinical/lab-style example predictors in lower-state previews. The implementation keeps the bounded worksheet experience while `e-dispo-v4.1-pas5-high-acuity-surrogate` uses the reduced empirical subset plus PAS-5 `high_acuity_proxy` for P(admit).
- The concept included a right evidence pane. The revised implementation intentionally moves evaluator-facing evidence into the Documentation section so the Model Demo stays lean.
- The concept included a top utility bar. The implementation keeps status and documentation navigation in the page header and sidebar to match the existing shadcn/Vite app shell.

## Result

The implementation was visually and functionally verified against the generated concept with no remaining material mismatches for the course prototype scope.
