import { activeEmpiricalModel } from "./eDispoV4Model"

import type { PooledEmpiricalModelArtifact } from "./pooledEmpiricalModel"

type PredictorSupport = "direct" | "proxy" | "weak_proxy" | "unavailable"

type PredictorFitStatus =
  | "included_in_reduced_empirical_fit"
  | "excluded_from_reduced_empirical_fit"
  | "prototype_only"

export type CohortFlowCount = {
  step: string
  count: number
  weightedCount: number
  note?: string
}

export type WeightedEndpointCounts = {
  admit: number
  treatAndRelease: number
  excluded: number
  excludedObservationDischarged: number
  excludedTransfer: number
  excludedSentinelDeath: number
  excludedNonroutineExit: number
  excludedOtherUnknown: number
  excludedConflict: number
}

export type EndpointCounts = {
  admit: number
  treatAndRelease: number
  excluded: number
  excludedObservationDischarged: number
  excludedTransfer: number
  excludedSentinelDeath: number
  excludedNonroutineExit: number
  excludedOtherUnknown: number
  excludedConflict: number
  weighted: WeightedEndpointCounts
}

export type SensitivityEndpointCounts = {
  endpointSensAEventualHome: {
    admit: number
    treatAndRelease: number
    excluded: number
    weighted: {
      admit: number
      treatAndRelease: number
      excluded: number
    }
  }
  endpointSensBAcuteEscalation: {
    acuteEscalationPositive: number
    treatAndRelease: number
    excluded: number
    weighted: {
      acuteEscalationPositive: number
      treatAndRelease: number
      excluded: number
    }
  }
}

export type SurveyDesignSummary = {
  weightVariable: string
  strataVariable: string
  psuVariable: string
  recordCount: number
  weightedCount: number
  effectiveSampleSizeApprox: number
  varianceImplementation: string
}

export type CoefficientEstimate = {
  key: string
  mean: number
  standardError: number
  ci95Low: number
  ci95High: number
  source: "nhamcs_2022" | "nhamcs_pooled_2018_2022"
}

export type CoefficientCovariance = {
  columns: string[]
  matrix: number[][]
}

export type PredictorMapping = {
  variable: string
  support: PredictorSupport
  fitStatus: PredictorFitStatus
  note: string
}

export type PerformanceMetrics = {
  auc: number
  brierScore: number
  calibrationIntercept: number
  calibrationSlope: number
  outcome: string
  positiveLabel: string
  sampleSize: number
  excludedForMissingPredictors: number
  eventCount: number
  nonEventCount: number
  outcomePrevalence: number
  weightedBinaryCount: number
}

export type InternalValidation = {
  method: string
  iterationsRequested: number
  iterationsCompleted: number
  randomSeed: number
  aucMedian: number
  aucP025: number
  aucP975: number
  brierMedian: number
  brierP025: number
  brierP975: number
  limitation: string
}

export type SensitivityAnalysisSummary = {
  outcome: string
  sampleSize: number
  eventCount: number
  outcomePrevalence: number
  auc: number
  brierScore: number
  calibrationIntercept: number
  calibrationSlope: number
}

export type NhamcsCoefficientArtifact = {
  schemaVersion: "2.0.0"
  artifactKind: "nhamcs_validation_model_fit"
  sourceDataset:
    | "NHAMCS 2022 ED public-use file"
    | "NHAMCS 2018-2022 pooled ED public-use files"
  derivedAt: string
  modelVersion: string
  endpointSpecVersion: string
  configHash: string
  generatedBy: string
  modelName: string
  cohortFlow: CohortFlowCount[]
  surveyDesign: SurveyDesignSummary
  endpointCounts: EndpointCounts
  sensitivityEndpointCounts: SensitivityEndpointCounts
  predictorMapping: PredictorMapping[]
  coefficients: CoefficientEstimate[]
  coefficientCovariance: CoefficientCovariance
  performanceMetrics: PerformanceMetrics
  internalValidation: InternalValidation
  sensitivityAnalyses: SensitivityAnalysisSummary[]
  limitations: string[]
}

export type ArtifactValidationResult = {
  valid: boolean
  label:
    | "Prototype assumptions active"
    | "NHAMCS-derived coefficients active"
    | "Pooled NHAMCS-derived coefficients active"
  issues: string[]
}

export const nhamcsCoefficientArtifact: NhamcsCoefficientArtifact | null = null

const pooledRequiredCoefficientKeys = [
  "intercept",
  "age_centered",
  "pain_bin3[mild]",
  "pain_bin3[severe]",
  "fever_or_temp",
  "vomiting_present",
  "tachycardia_burden",
] as const

const eDispoV4RequiredCoefficientKeys = [
  "intercept",
  "age_centered",
  "pain_severe",
  "fever_or_temp",
  "vomiting_present",
  "tachycardia_burden",
] as const

const eDispoV41Pas5RequiredCoefficientKeys = [
  ...eDispoV4RequiredCoefficientKeys,
  "high_acuity_proxy",
] as const

type PooledCoefficientKey =
  | (typeof pooledRequiredCoefficientKeys)[number]
  | (typeof eDispoV4RequiredCoefficientKeys)[number]
  | (typeof eDispoV41Pas5RequiredCoefficientKeys)[number]

const endpointCountKeys = [
  "admit",
  "treatAndRelease",
  "excluded",
  "excludedObservationDischarged",
  "excludedTransfer",
  "excludedSentinelDeath",
  "excludedNonroutineExit",
  "excludedOtherUnknown",
  "excludedConflict",
] as const

const requiredPredictorVariables = [
  "broadPainRegion",
  "painSeverity",
  "onsetDurationCategory",
  "constantVsIntermittent",
  "vomiting",
  "fever",
]

const agePredictorVariables = ["ageBand", "age"]

export function validateCoefficientArtifact(
  artifact: unknown
): ArtifactValidationResult {
  const issues: string[] = []

  if (artifact === null || artifact === undefined) {
    return {
      valid: false,
      label: "Prototype assumptions active",
      issues: ["No NHAMCS-derived coefficient artifact is present."],
    }
  }

  if (!isRecord(artifact)) {
    return invalid(["Artifact must be an object."])
  }

  if (artifact.schemaVersion !== "2.0.0") {
    issues.push("schemaVersion must be 2.0.0.")
  }

  if (artifact.artifactKind !== "nhamcs_validation_model_fit") {
    issues.push("artifactKind must be nhamcs_validation_model_fit.")
  }

  if (
    artifact.sourceDataset !== "NHAMCS 2022 ED public-use file" &&
    artifact.sourceDataset !== "NHAMCS 2018-2022 pooled ED public-use files"
  ) {
    issues.push(
      "sourceDataset must identify either NHAMCS 2022 or pooled NHAMCS 2018-2022 ED public-use files."
    )
  }

  for (const field of [
    "derivedAt",
    "modelVersion",
    "endpointSpecVersion",
    "configHash",
    "generatedBy",
    "modelName",
  ]) {
    if (!isNonEmptyString(artifact[field])) {
      issues.push(`${field} must be a non-empty string.`)
    }
  }

  if (!isSurveyDesignSummary(artifact.surveyDesign)) {
    issues.push(
      "surveyDesign must document weight/strata/PSU variables, weighted count, and effective sample size."
    )
  }

  if (!isCohortFlow(artifact.cohortFlow)) {
    issues.push("cohortFlow must contain unweighted and weighted non-negative counts.")
  }

  if (!isEndpointCounts(artifact.endpointCounts)) {
    issues.push(
      "endpointCounts must contain primary counts plus weighted exclusion and conflict counts."
    )
  }

  if (!isSensitivityEndpointCounts(artifact.sensitivityEndpointCounts)) {
    issues.push(
      "sensitivityEndpointCounts must contain non-negative unweighted and weighted Sensitivity A/B counts."
    )
  }

  if (!isCoefficientList(artifact.coefficients)) {
    issues.push("coefficients must contain finite estimates, standard errors, and 95% intervals.")
  }

  if (!isCoefficientCovariance(artifact.coefficientCovariance, artifact.coefficients)) {
    issues.push("coefficientCovariance must be a finite square matrix matching coefficient keys.")
  }

  if (!isPerformanceMetrics(artifact.performanceMetrics)) {
    issues.push(
      "performanceMetrics must include AUC, Brier score, calibration intercept/slope, outcome prevalence, sample size, event counts, missing predictor exclusions, and weighted binary count."
    )
  }

  if (!isInternalValidation(artifact.internalValidation)) {
    issues.push(
      "internalValidation must document method, iterations, seed, AUC interval, Brier interval, and limitation."
    )
  }

  if (!isSensitivityAnalyses(artifact.sensitivityAnalyses)) {
    issues.push(
      "sensitivityAnalyses must summarize primary, Sensitivity A, and Sensitivity B performance."
    )
  }

  if (!isPredictorMappingList(artifact.predictorMapping)) {
    issues.push(
      "predictorMapping must lock age or ageBand plus the six symptom/prototype predictors as direct, proxy, weak_proxy, or unavailable with fit status."
    )
  }

  if (
    !Array.isArray(artifact.limitations) ||
    artifact.limitations.length === 0 ||
    artifact.limitations.some((item) => !isNonEmptyString(item))
  ) {
    issues.push("limitations must contain at least one non-empty string.")
  }

  return issues.length === 0
    ? {
        valid: true,
        label: "NHAMCS-derived coefficients active",
        issues: [],
      }
    : invalid(issues)
}

export function validatePooledEmpiricalModelArtifact(
  artifact: unknown
): ArtifactValidationResult {
  const issues: string[] = []

  if (artifact === null || artifact === undefined) {
    return invalid(["No pooled empirical model export artifact is present."])
  }

  if (!isRecord(artifact)) {
    return invalid(["Pooled empirical model export must be an object."])
  }

  if (artifact.allowed_use !== "educational only; not clinical decision support") {
    issues.push("allowed_use must be educational only; not clinical decision support.")
  }

  const modelId = artifact.model_id
  const requiredCoefficientKeys = requiredPooledCoefficientKeys(modelId)

  if (requiredCoefficientKeys.length === 0) {
    issues.push(
      "model_id must be pooled_empirical_v2_age_pain_fever_vomiting_tachycardia, e-dispo-v4.0, or e-dispo-v4.1-pas5-high-acuity-surrogate."
    )
  }

  if (
    artifact.status !== "reduced_empirical_candidate" &&
    artifact.status !== "versioned_empirical_candidate"
  ) {
    issues.push("status must be reduced_empirical_candidate or versioned_empirical_candidate.")
  }

  if (
    artifact.model_activation_status !==
    "eligible_for_educational_activation_after_review"
  ) {
    issues.push(
      "model_activation_status must permit educational activation after review."
    )
  }

  if (artifact.coefficient_source !== "nhamcs_pooled_2018_2022") {
    issues.push("coefficient_source must be nhamcs_pooled_2018_2022.")
  }

  for (const field of [
    "generated_at",
    "model_version",
    "endpoint",
    "population",
    "posterior_draws_path",
    "covariance_matrix_path",
    "run_id",
  ]) {
    if (!isNonEmptyString(artifact[field])) {
      issues.push(`${field} must be a non-empty string.`)
    }
  }

  if (
    artifact.pain_monotonicity_verdict !== "nonmonotonic_flexible_only" &&
    artifact.pain_monotonicity_verdict !==
      "nonmonotonic_collapsed_to_severe_binary"
  ) {
    issues.push(
      "pain_monotonicity_verdict must document nonmonotonic flexible pain or severe-binary collapse."
    )
  }

  if (artifact.fever_promotion_gate_status !== "dataset_derived") {
    issues.push("fever_promotion_gate_status must be dataset_derived.")
  }

  if (!isPooledCalibration(artifact.calibration)) {
    issues.push(
      "calibration must include AUROC, Brier score, observed prevalence, mean predicted, intercept, and slope."
    )
  }

  if (!isPooledCohortCounts(artifact.cohort_counts)) {
    issues.push(
      "cohort_counts must document pooled NHAMCS strict binary N, admissions, weighted prevalence, and event-count gate."
    )
  }

  if (
    !Array.isArray(artifact.dataset_sources) ||
    !artifact.dataset_sources.includes("NHAMCS_2018_2022_POOLED")
  ) {
    issues.push("dataset_sources must include NHAMCS_2018_2022_POOLED.")
  }

  if (
    !isPooledPredictorEvidenceList(
      artifact.predictor_evidence_tiers,
      requiredCoefficientKeys,
      modelId
    )
  ) {
    issues.push(
      "predictor_evidence_tiers must mark direct promoted terms as dataset_derived and high_acuity_proxy as dataset_derived_surrogate when v4.1 is active."
    )
  }

  if (modelId === "e-dispo-v4.0") {
    if (!isPooledPerformanceIntervals(artifact.performance_intervals)) {
      issues.push(
        "e-dispo-v4.0 must include AUROC and Brier apparent performance intervals with method, status, and limitations."
      )
    }

    if (!isPooledValidationArtifactPaths(artifact.validation_artifact_paths)) {
      issues.push(
        "e-dispo-v4.0 must list validation artifact paths for calibration, intervals, subgroup, missingness, optimism, and transportability outputs."
      )
    }
  } else if (modelId === "e-dispo-v4.1-pas5-high-acuity-surrogate") {
    if (!isPas5ValidationArtifactPaths(artifact.validation_artifact_paths)) {
      issues.push(
        "e-dispo-v4.1 must list PAS-5 surrogate validation artifact paths including mapping, missingness, cells, coefficients, covariance, draws, calibration, leave-one-year-out, gate, and report outputs."
      )
    }
  } else if (
    artifact.performance_intervals !== undefined &&
    !isPooledPerformanceIntervals(artifact.performance_intervals)
  ) {
    issues.push("performance_intervals must contain valid AUROC and Brier rows when present.")
  }

  if (!isPooledPredictorList(artifact.predictors, requiredCoefficientKeys, modelId)) {
    issues.push(
      "predictors must contain promoted coefficients with finite betas, standard errors, and required surrogate labeling."
    )
  }

  return issues.length === 0
    ? {
        valid: true,
        label: "Pooled NHAMCS-derived coefficients active",
        issues: [],
      }
    : invalid(issues)
}

export const pooledEmpiricalModelStatus =
  validatePooledEmpiricalModelArtifact(activeEmpiricalModel)

export const coefficientArtifactStatus = pooledEmpiricalModelStatus

export function shouldUseEmpiricalCoefficients(
  artifact: unknown = activeEmpiricalModel
): boolean {
  return validatePooledEmpiricalModelArtifact(artifact).valid
}

export function shouldUsePooledEmpiricalModel(
  artifact: unknown = activeEmpiricalModel
): boolean {
  return validatePooledEmpiricalModelArtifact(artifact).valid
}

function invalid(issues: string[]): ArtifactValidationResult {
  return {
    valid: false,
    label: "Prototype assumptions active",
    issues,
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value)
}

function isNonNegativeNumber(value: unknown): value is number {
  return isFiniteNumber(value) && value >= 0
}

function isProbability(value: unknown): value is number {
  return isFiniteNumber(value) && value >= 0 && value <= 1
}

function isPooledCalibration(
  value: unknown
): value is PooledEmpiricalModelArtifact["calibration"] {
  return (
    isRecord(value) &&
    isProbability(value.auroc) &&
    isProbability(value.brier_score) &&
    isFiniteNumber(value.intercept) &&
    isProbability(value.mean_predicted) &&
    isProbability(value.observed_prevalence) &&
    isFiniteNumber(value.slope)
  )
}

function isPooledCohortCounts(
  value: unknown
): value is PooledEmpiricalModelArtifact["cohort_counts"] {
  if (!isRecord(value) || !isRecord(value.NHAMCS_2018_2022_POOLED)) {
    return false
  }

  const nhamcs = value.NHAMCS_2018_2022_POOLED

  return (
    isNonNegativeNumber(nhamcs.admission_events) &&
    isNonNegativeNumber(nhamcs.strict_binary_unweighted_n) &&
    isProbability(nhamcs.weighted_admission_prevalence) &&
    nhamcs.event_count_gate_passed === true
  )
}

function isPooledPerformanceIntervals(
  value: unknown
): value is PooledEmpiricalModelArtifact["performance_intervals"] {
  if (!Array.isArray(value) || value.length !== 2) {
    return false
  }

  const metrics = new Set(value.filter(isRecord).map((row) => row.metric))

  return (
    metrics.has("auroc") &&
    metrics.has("brier_score") &&
    value.every(
      (row) =>
        isRecord(row) &&
        (row.metric === "auroc" || row.metric === "brier_score") &&
        isProbability(row.estimate) &&
        isProbability(row.ci_low) &&
        isProbability(row.ci_high) &&
        row.ci_low <= row.estimate &&
        row.estimate <= row.ci_high &&
        row.interval_level === 0.95 &&
        row.method ===
          "survey_bootstrap_replicate_weights_fixed_apparent_predictions" &&
        row.status === "ok" &&
        isNonEmptyString(row.limitation)
    )
  )
}

function isPooledValidationArtifactPaths(value: unknown): boolean {
  if (!isRecord(value)) {
    return false
  }

  const required = [
    "calibration_by_decile",
    "calibration_plot_data",
    "full_source_endpoint_screen_calibration",
    "full_source_endpoint_screen_missingness",
    "full_source_endpoint_screen_performance",
    "full_source_nontrauma_screen_calibration",
    "full_source_nontrauma_screen_missingness",
    "full_source_nontrauma_screen_performance",
    "full_source_scope_screen_report",
    "missingness_performance",
    "optimism_corrected_performance",
    "performance_intervals",
    "subgroup_calibration",
    "subgroup_performance",
    "transportability_track",
  ]

  return required.every((key) => isNonEmptyString(value[key]))
}

function isPas5ValidationArtifactPaths(value: unknown): boolean {
  if (!isRecord(value)) {
    return false
  }

  const required = [
    "calibration_by_decile",
    "calibration_plot_data",
    "pas5_calibration",
    "pas5_cell_counts",
    "pas5_coefficients",
    "pas5_covariance",
    "pas5_decile_calibration",
    "pas5_draws_app",
    "pas5_draws_long",
    "pas5_gate_decision",
    "pas5_leave_one_year_out",
    "pas5_mapping",
    "pas5_missingness",
    "pas5_report",
  ]

  return required.every((key) => isNonEmptyString(value[key]))
}

function isPooledPredictorEvidenceList(
  value: unknown,
  requiredCoefficientKeys: readonly PooledCoefficientKey[],
  modelId: unknown
): value is PooledEmpiricalModelArtifact["predictor_evidence_tiers"] {
  if (!Array.isArray(value)) {
    return false
  }

  const keys = value
    .filter(isRecord)
    .map((row) => pooledCoefficientKey(row.term, row.level))

  if (
    keys.length !== requiredCoefficientKeys.length ||
    keys.some((key) => key === null) ||
    new Set(keys).size !== requiredCoefficientKeys.length
  ) {
    return false
  }

  const keySet = new Set(keys)

  return requiredCoefficientKeys.every((key) => {
    const match = value.find(
      (row) =>
        isRecord(row) &&
        pooledCoefficientKey(row.term, row.level) === key
    )

    return (
      keySet.has(key) &&
      isRecord(match) &&
      match.evidence_tier === expectedEvidenceTier(key, modelId) &&
      isValidSurrogateMetadata(match, key, modelId) &&
      match.blockers === ""
    )
  })
}

function isPooledPredictorList(
  value: unknown,
  requiredCoefficientKeys: readonly PooledCoefficientKey[],
  modelId: unknown
): value is PooledEmpiricalModelArtifact["predictors"] {
  if (!Array.isArray(value)) {
    return false
  }

  const keys = value
    .filter(isRecord)
    .map((row) => pooledCoefficientKey(row.term, row.level))

  if (
    keys.length !== requiredCoefficientKeys.length ||
    keys.some((key) => key === null) ||
    new Set(keys).size !== requiredCoefficientKeys.length
  ) {
    return false
  }

  return requiredCoefficientKeys.every((key) => {
    const match = value.find(
      (row) =>
        isRecord(row) &&
        pooledCoefficientKey(row.term, row.level) === key
    )

    return (
      isRecord(match) &&
      isFiniteNumber(match.center_beta) &&
      isNonNegativeNumber(match.se_or_sd) &&
      match.distribution === "normal_approximation_exploratory" &&
      match.evidence_tier === expectedEvidenceTier(key, modelId) &&
      match.source === "NHAMCS_2018_2022_POOLED" &&
      isNonEmptyString(match.limitation_note) &&
      isValidSurrogateMetadata(match, key, modelId)
    )
  })
}

function expectedEvidenceTier(
  key: PooledCoefficientKey,
  modelId: unknown
): "dataset_derived" | "dataset_derived_surrogate" {
  if (
    modelId === "e-dispo-v4.1-pas5-high-acuity-surrogate" &&
    key === "high_acuity_proxy"
  ) {
    return "dataset_derived_surrogate"
  }

  return "dataset_derived"
}

function isValidSurrogateMetadata(
  row: Record<string, unknown>,
  key: PooledCoefficientKey,
  modelId: unknown
): boolean {
  const isSurrogate =
    modelId === "e-dispo-v4.1-pas5-high-acuity-surrogate" &&
    key === "high_acuity_proxy"

  if (!isSurrogate) {
    return row.surrogate_source === undefined && row.surrogate_limitation === undefined
  }

  return (
    row.surrogate_source === "NHAMCS_IMMEDR" &&
    row.surrogate_limitation ===
      "Direct PAS-5 patient answers are not observed in NHAMCS."
  )
}

function pooledCoefficientKey(
  term: unknown,
  level: unknown
): PooledCoefficientKey | null {
  if (term === "intercept") {
    return "intercept"
  }

  if (term === "age_centered" && level === "per_1_year_centered_at_42") {
    return "age_centered"
  }

  if (term === "pain_bin3" && level === "mild") {
    return "pain_bin3[mild]"
  }

  if (term === "pain_bin3" && level === "severe") {
    return "pain_bin3[severe]"
  }

  if (term === "pain_severe" && level === "1") {
    return "pain_severe"
  }

  if (term === "fever_or_temp" && level === "1") {
    return "fever_or_temp"
  }

  if (term === "vomiting_present" && level === "1") {
    return "vomiting_present"
  }

  if (term === "tachycardia_burden" && level === "per_10_bpm_over_100") {
    return "tachycardia_burden"
  }

  if (term === "high_acuity_proxy" && level === "1") {
    return "high_acuity_proxy"
  }

  return null
}

function requiredPooledCoefficientKeys(
  modelId: unknown
): readonly PooledCoefficientKey[] {
  if (modelId === "pooled_empirical_v2_age_pain_fever_vomiting_tachycardia") {
    return pooledRequiredCoefficientKeys
  }

  if (modelId === "e-dispo-v4.0") {
    return eDispoV4RequiredCoefficientKeys
  }

  if (modelId === "e-dispo-v4.1-pas5-high-acuity-surrogate") {
    return eDispoV41Pas5RequiredCoefficientKeys
  }

  return []
}

function isCohortFlow(value: unknown): value is CohortFlowCount[] {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every(
      (row) =>
        isRecord(row) &&
        isNonEmptyString(row.step) &&
        isNonNegativeNumber(row.count) &&
        isNonNegativeNumber(row.weightedCount)
    )
  )
}

function isSurveyDesignSummary(value: unknown): value is SurveyDesignSummary {
  return (
    isRecord(value) &&
    isNonEmptyString(value.weightVariable) &&
    isNonEmptyString(value.strataVariable) &&
    isNonEmptyString(value.psuVariable) &&
    isNonNegativeNumber(value.recordCount) &&
    isNonNegativeNumber(value.weightedCount) &&
    isNonNegativeNumber(value.effectiveSampleSizeApprox) &&
    isNonEmptyString(value.varianceImplementation)
  )
}

function isEndpointCounts(value: unknown): value is EndpointCounts {
  if (!isRecord(value) || !isRecord(value.weighted)) {
    return false
  }

  const weighted = value.weighted

  return (
    endpointCountKeys.every((key) => isNonNegativeNumber(value[key])) &&
    endpointCountKeys.every((key) => isNonNegativeNumber(weighted[key]))
  )
}

function isSensitivityEndpointCounts(
  value: unknown
): value is SensitivityEndpointCounts {
  return (
    isRecord(value) &&
    isRecord(value.endpointSensAEventualHome) &&
    isNonNegativeNumber(value.endpointSensAEventualHome.admit) &&
    isNonNegativeNumber(value.endpointSensAEventualHome.treatAndRelease) &&
    isNonNegativeNumber(value.endpointSensAEventualHome.excluded) &&
    isRecord(value.endpointSensAEventualHome.weighted) &&
    isNonNegativeNumber(value.endpointSensAEventualHome.weighted.admit) &&
    isNonNegativeNumber(value.endpointSensAEventualHome.weighted.treatAndRelease) &&
    isNonNegativeNumber(value.endpointSensAEventualHome.weighted.excluded) &&
    isRecord(value.endpointSensBAcuteEscalation) &&
    isNonNegativeNumber(
      value.endpointSensBAcuteEscalation.acuteEscalationPositive
    ) &&
    isNonNegativeNumber(value.endpointSensBAcuteEscalation.treatAndRelease) &&
    isNonNegativeNumber(value.endpointSensBAcuteEscalation.excluded) &&
    isRecord(value.endpointSensBAcuteEscalation.weighted) &&
    isNonNegativeNumber(
      value.endpointSensBAcuteEscalation.weighted.acuteEscalationPositive
    ) &&
    isNonNegativeNumber(value.endpointSensBAcuteEscalation.weighted.treatAndRelease) &&
    isNonNegativeNumber(value.endpointSensBAcuteEscalation.weighted.excluded)
  )
}

function isCoefficientList(value: unknown): value is CoefficientEstimate[] {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every(
      (row) =>
        isRecord(row) &&
        isNonEmptyString(row.key) &&
        isFiniteNumber(row.mean) &&
        isNonNegativeNumber(row.standardError) &&
        isFiniteNumber(row.ci95Low) &&
        isFiniteNumber(row.ci95High) &&
        row.ci95Low <= row.mean &&
        row.mean <= row.ci95High &&
        (row.source === "nhamcs_2022" ||
          row.source === "nhamcs_pooled_2018_2022")
    )
  )
}

function isCoefficientCovariance(
  value: unknown,
  coefficients: unknown
): value is CoefficientCovariance {
  if (!isRecord(value) || !Array.isArray(value.columns) || !Array.isArray(value.matrix)) {
    return false
  }

  const keys = Array.isArray(coefficients)
    ? coefficients
        .filter(isRecord)
        .map((row) => row.key)
        .filter((key): key is string => typeof key === "string")
    : []

  const columns = value.columns
  const matrix = value.matrix
  return (
    columns.length > 0 &&
    columns.every((column) => typeof column === "string" && column.length > 0) &&
    keys.length === columns.length &&
    keys.every((key, index) => key === columns[index]) &&
    matrix.length === columns.length &&
    matrix.every(
      (row) =>
        Array.isArray(row) &&
        row.length === columns.length &&
        row.every((cell) => typeof cell === "number" && Number.isFinite(cell))
    )
  )
}

function isPerformanceMetrics(value: unknown): value is PerformanceMetrics {
  return (
    isRecord(value) &&
    isProbability(value.auc) &&
    isProbability(value.brierScore) &&
    isFiniteNumber(value.calibrationIntercept) &&
    isFiniteNumber(value.calibrationSlope) &&
    isNonEmptyString(value.outcome) &&
    isNonEmptyString(value.positiveLabel) &&
    isNonNegativeNumber(value.sampleSize) &&
    isNonNegativeNumber(value.excludedForMissingPredictors) &&
    isNonNegativeNumber(value.eventCount) &&
    isNonNegativeNumber(value.nonEventCount) &&
    value.eventCount + value.nonEventCount === value.sampleSize &&
    isProbability(value.outcomePrevalence) &&
    isNonNegativeNumber(value.weightedBinaryCount)
  )
}

function isInternalValidation(value: unknown): value is InternalValidation {
  return (
    isRecord(value) &&
    isNonEmptyString(value.method) &&
    isNonNegativeNumber(value.iterationsRequested) &&
    isNonNegativeNumber(value.iterationsCompleted) &&
    isFiniteNumber(value.randomSeed) &&
    isProbability(value.aucMedian) &&
    isProbability(value.aucP025) &&
    isProbability(value.aucP975) &&
    isProbability(value.brierMedian) &&
    isProbability(value.brierP025) &&
    isProbability(value.brierP975) &&
    isNonEmptyString(value.limitation)
  )
}

function isSensitivityAnalyses(value: unknown): value is SensitivityAnalysisSummary[] {
  return (
    Array.isArray(value) &&
    value.length >= 3 &&
    value.every(
      (row) =>
        isRecord(row) &&
        isNonEmptyString(row.outcome) &&
        isNonNegativeNumber(row.sampleSize) &&
        isNonNegativeNumber(row.eventCount) &&
        isProbability(row.outcomePrevalence) &&
        isProbability(row.auc) &&
        isProbability(row.brierScore) &&
        isFiniteNumber(row.calibrationIntercept) &&
        isFiniteNumber(row.calibrationSlope)
    )
  )
}

function isPredictorMappingList(value: unknown): value is PredictorMapping[] {
  const validSupport: PredictorSupport[] = [
    "direct",
    "proxy",
    "weak_proxy",
    "unavailable",
  ]
  const validFitStatus: PredictorFitStatus[] = [
    "included_in_reduced_empirical_fit",
    "excluded_from_reduced_empirical_fit",
    "prototype_only",
  ]

  if (
    !Array.isArray(value) ||
    value.length < requiredPredictorVariables.length ||
    !value.every(
      (row) =>
        isRecord(row) &&
        isNonEmptyString(row.variable) &&
        typeof row.support === "string" &&
        validSupport.includes(row.support as PredictorSupport) &&
        typeof row.fitStatus === "string" &&
        validFitStatus.includes(row.fitStatus as PredictorFitStatus) &&
        isNonEmptyString(row.note)
    )
  ) {
    return false
  }

  const variables = new Set(value.map((row) => row.variable))
  return (
    agePredictorVariables.some((variable) => variables.has(variable)) &&
    requiredPredictorVariables.every((variable) => variables.has(variable))
  )
}
