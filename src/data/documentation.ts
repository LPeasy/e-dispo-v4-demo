export type DocumentationPageId =
  | "overview"
  | "model-card"
  | "parameter-evidence"
  | "endpoint-recoding"
  | "nhamcs-appendix"
  | "uncertainty-method"
  | "bias-applicability"
  | "reporting-checklist"
  | "qa-evidence"
  | "sources"

export const documentationPages: Array<{
  id: DocumentationPageId
  label: string
  description: string
}> = [
  {
    id: "overview",
    label: "Overview",
    description: "Purpose, scope, and safety boundary for the final project.",
  },
  {
    id: "model-card",
    label: "Model Card",
    description: "Population, endpoint, predictors, coefficient status, and use limits.",
  },
  {
    id: "parameter-evidence",
    label: "Parameter Evidence",
    description: "Dose-response mappings, distributions, evidence tiers, and limitations.",
  },
  {
    id: "endpoint-recoding",
    label: "Endpoint Recoding",
    description: "Included and excluded ED disposition categories.",
  },
  {
    id: "nhamcs-appendix",
    label: "NHAMCS Appendix",
    description: "Cohort construction, variable mapping, and empirical artifact path.",
  },
  {
    id: "uncertainty-method",
    label: "Uncertainty Method",
    description: "Latin Hypercube Sampling and simulation output definitions.",
  },
  {
    id: "bias-applicability",
    label: "Bias & Applicability",
    description: "PROBAST-style course risk table.",
  },
  {
    id: "reporting-checklist",
    label: "Reporting Checklist",
    description: "TRIPOD-style reporting status for the final writeup.",
  },
  {
    id: "qa-evidence",
    label: "QA Evidence",
    description: "Automated checks and browser QA evidence.",
  },
  {
    id: "sources",
    label: "Sources",
    description: "Primary standards, datasets, tooling, and method links.",
  },
]

export const overviewEvidence = [
  {
    label: "User-facing purpose",
    value:
      "A structured educational demo for the e-dispo-v4.0 model workflow, not a clinical product.",
  },
  {
    label: "Evaluator-facing purpose",
    value:
      "A documentation package showing endpoint definitions, data readiness, reporting discipline, and QA.",
  },
  {
    label: "Safety boundary",
    value:
      "The app does not advise whether to seek emergency care and blocks out-of-scope cases before probability output.",
  },
  {
    label: "Data posture",
    value:
      "Static app only. No login, no backend, no database, no PHI, and no raw public-use data bundled.",
  },
  {
    label: "Validation baseline",
    value:
      "The active app uses the e-dispo-v4.0 reduced pooled NHAMCS 2018-2022 empirical model for educational use only.",
  },
]

export const modelCardRows = [
  {
    label: "Target population",
    value: "Adult men ages 18-64 already presenting to the emergency department.",
  },
  {
    label: "Clinical context",
    value: "Non-traumatic abdominal pain after ED presentation.",
  },
  {
    label: "Endpoint",
    value:
      "P(admit | endpoint-refined binary cohort, approved worksheet inputs).",
  },
  {
    label: "Binary labels",
    value:
      "admit is same-hospital hospitalization/admission, including observation -> hospitalized when documented. treat_and_release is routine home release.",
  },
  {
    label: "Primary exclusions",
    value:
      "Observation -> discharged, transfer, death/DOA, AMA/LWBS/LBTC/elopement, other, unknown, missing, and conflicting dispositions are excluded from the primary endpoint.",
  },
  {
    label: "Predictors",
    value:
      "Exact age, severe-vs-non-severe pain status, fever or temperature proxy, vomiting, and tachycardia_burden from observed HR.",
  },
  {
    label: "Predictive power",
    value:
      "Moderate apparent discrimination: AUROC 0.713, Brier 0.098, with severe-only pain preserving the flexible-pain discrimination on the same complete-case cohort.",
  },
  {
    label: "Usability boundary",
    value:
      "The empirical estimate uses a reduced input set; excluded prototype controls and AAP-3 do not change P(admit).",
  },
  {
    label: "Model form",
    value: "Transparent reduced logistic regression from pooled NHAMCS 2018-2022 export values.",
  },
  {
    label: "Intended use",
    value:
      "Course demonstration of scope control, endpoint recoding, structured worksheet state, and uncertainty reporting.",
  },
  {
    label: "Not intended for",
    value: "Diagnosis, triage, treatment decisions, discharge planning, or real patient care.",
  },
]

export const nhamcsCohortRows = [
  {
    step: "Start",
    rule: "2022 NHAMCS emergency department public-use file.",
    status: "Pipeline input",
  },
  {
    step: "Sex",
    rule: "Keep male encounters only.",
    status: "Required cohort filter",
  },
  {
    step: "Age",
    rule: "Keep ages 18-64.",
    status: "Required cohort filter",
  },
  {
    step: "Complaint",
    rule: "Use abdominal pain reason-for-visit codes and documented proxy rules.",
    status: "Direct/proxy mapping",
  },
  {
    step: "Trauma proxy",
    rule: "Exclude injury or trauma-related encounters where public-use variables support the rule.",
    status: "Proxy mapping",
  },
  {
    step: "Disposition",
    rule:
      "Apply endpoint-refined v3 recoding before denominator construction: routine home release vs same-hospital hospitalization/admission.",
    status: "Required endpoint filter",
  },
]

export const predictorSupportRows = [
  {
    variable: "Age band",
    nhamcs: "Exact age from public-use age field, centered at 42.",
    support: "Direct",
  },
  {
    variable: "Broad pain region",
    nhamcs: "Abdominal pain RFV codes support complaint inclusion but not detailed upper/lower/diffuse location.",
    support: "Weak proxy; excluded from reduced fit",
  },
  {
    variable: "Pain severity",
    nhamcs: "Pain scale field grouped as mild, moderate, or severe when available.",
    support: "Direct; severe is active, while mild and moderate are collapsed as non-severe",
  },
  {
    variable: "Onset/duration category",
    nhamcs: "Not available in the current public-use mapping.",
    support: "Unavailable; prototype only",
  },
  {
    variable: "Constant vs intermittent",
    nhamcs: "Not directly available in public-use fields.",
    support: "Unavailable; prototype only",
  },
  {
    variable: "Vomiting",
    nhamcs: "Reason-for-visit, diagnosis, or symptom proxy if coded.",
    support: "Proxy; ordinary vomiting included in reduced fit",
  },
  {
    variable: "Fever",
    nhamcs: "Reason-for-visit, diagnosis, or temperature proxy if coded.",
    support: "Objective fever or temperature proxy included in reduced fit",
  },
  {
    variable: "Observed HR",
    nhamcs: "`PULSE` transformed as tachycardia_burden = max(HR - 100, 0) / 10; missing HR is not normal.",
    support: "Direct observed vital sign; included in e-dispo-v4.0 reduced fit",
  },
]

export const probastRiskRows = [
  {
    domain: "Participants",
    concern:
      "Course scope is narrow and explicit, but empirical generalizability is limited to the source dataset and filters.",
    risk: "Medium",
    mitigation:
      "Document inclusion/exclusion rules and keep the app label as educational.",
  },
  {
    domain: "Predictors",
    concern:
      "Some simplified symptom predictors are direct while onset and pattern are weak or unavailable in NHAMCS.",
    risk: "High",
    mitigation:
      "Separate direct, proxy, and unsupported predictors in the appendix before making empirical claims.",
  },
  {
    domain: "Outcome",
    concern:
      "Binary disposition is defensible only after splitting observation outcomes, excluding transfer and sentinel death from the primary endpoint, and removing nonroutine, other, unknown, missing, and conflicting dispositions.",
    risk: "Low/medium",
    mitigation:
      "Apply endpoint-refined v3 recoding before calculating P(treat_and_release) = 1 - P(admit).",
  },
  {
    domain: "Analysis",
    concern:
      "The active reduced NHAMCS model does not use the full prototype input set or AAP-3.",
    risk: "High",
    mitigation:
      "Display excluded inputs separately and keep AAP-3 explanatory until validation gates pass.",
  },
  {
    domain: "Applicability",
    concern:
      "The app demonstrates model-building discipline and is not suitable for clinical deployment.",
    risk: "High for clinical use",
    mitigation:
      "Keep clinical validity claims out of the demo and documentation.",
  },
]

export const tripodChecklistRows = [
  {
    item: "Participants",
    status: "Complete for class scope",
    evidence: "Adult men ages 18-64, already in ED, non-traumatic abdominal pain.",
  },
  {
    item: "Data source",
    status: "Endpoint audit generated",
    evidence:
      "NHAMCS 2022 endpoint audit and reduced model-fit artifacts are saved under artifacts/nhamcs.",
  },
  {
    item: "Outcome",
    status: "Complete",
    evidence:
      "Endpoint-refined v3 table defines primary classes, sensitivity endpoints, sentinel death exclusion, and conflict handling.",
  },
  {
    item: "Predictors",
    status: "Complete for prototype",
    evidence: "Seven required class-model predictors are enforced in worksheet state.",
  },
  {
    item: "Sample size and missingness",
    status: "Partly complete",
    evidence:
      "Artifacts include cohort counts and pain-scale fit exclusions; a full missingness table remains next-phase work.",
  },
  {
    item: "Model specification",
    status: "Complete for reduced empirical app path",
    evidence: "Transparent logistic regression using pooled NHAMCS 2018-2022 export coefficients.",
  },
  {
    item: "Performance",
    status: "Reported for educational activation",
    evidence:
      "Pooled empirical report includes AUROC 0.713, Brier 0.098, calibration intercept, and calibration slope, but no clinical validity claim is made.",
  },
  {
    item: "Limitations",
    status: "Complete",
    evidence: "Prototype assumptions and dataset proxy limits are explicitly labeled.",
  },
]

export const qaEvidenceRows = [
  {
    check: "Endpoint recoding",
    evidence:
      "Unit tests cover OBSHOS admit, OBSDIS primary exclusion, transfer sensitivity B, sentinel death, routine home release, conflicts, and unmapped values.",
  },
  {
    check: "Eligibility blocking",
    evidence: "Unit tests verify out-of-scope cases cannot proceed to model output.",
  },
  {
    check: "Required fields",
    evidence: "Unit tests reject empty or incomplete class-model worksheet inputs.",
  },
  {
    check: "Probability bounds",
    evidence: "Unit tests verify probabilities remain in 0..1 and sum to one.",
  },
  {
    check: "Monte Carlo reproducibility",
    evidence: "Unit tests verify fixed-seed empirical coefficient simulation output is reproducible.",
  },
  {
    check: "Documentation artifacts",
    evidence: "Unit tests verify documentation page inventory, sources, and artifact gating.",
  },
  {
    check: "NHAMCS validation fixture",
    evidence:
      "Python fixture verifies primary, sensitivity, exclusion, conflict, and weighted endpoint counts.",
  },
  {
    check: "Validation-grade artifact gate",
    evidence:
      "Unit tests validate the pooled app export and reject missing or invalid empirical artifacts.",
  },
  {
    check: "AAP-3 isolation",
    evidence:
      "Unit tests verify AAP-3 probabilities, guardrails, evidence label, and no effect on empirical P(admit).",
  },
  {
    check: "Predictive power and usability review",
    evidence:
      "Documentation records moderate discrimination, severe-only pain comparison, pain-missing UI gap, and excluded-input boundaries.",
  },
  {
    check: "Browser QA",
    evidence: "Desktop and mobile screenshots are retained under docs/qa after checks.",
  },
]

export const demoBoundaryCopy = [
  "Educational statistical model only.",
  "This model does not advise whether to seek emergency care.",
  "No diagnosis, triage, treatment, or discharge-planning recommendation is made.",
  "The active e-dispo-v4.0 estimate uses pooled NHAMCS 2018-2022 export values.",
]

export const prohibitedClinicalClaims = [
  "clinically validated",
  "validated for clinical use",
  "diagnostic model",
  "triage recommendation",
  "this is medical advice",
  "safe to discharge",
]

export function containsProhibitedClinicalClaim(text: string): boolean {
  const lowerText = text.toLowerCase()

  return prohibitedClinicalClaims.some((claim) => lowerText.includes(claim))
}
