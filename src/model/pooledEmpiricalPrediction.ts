import { activeEmpiricalModel, E_DISPO_V4_MODEL_ID } from "@/data/eDispoV4Model"
import { validatePooledEmpiricalModelArtifact } from "@/data/empiricalArtifacts"
import { clampProbability, logistic } from "./logisticModel"
import type {
  BinarySymptom,
  LogisticTerm,
  ModelInputs,
  PainSeverity,
  PredictionResult,
} from "./types"

import type { PooledEmpiricalModelArtifact } from "@/data/pooledEmpiricalModel"

export type PooledEmpiricalPainSeverity = PainSeverity | "missing"

export type PooledEmpiricalPredictionInputs = {
  age: number
  painSeverity: PooledEmpiricalPainSeverity
  fever: BinarySymptom
  vomiting: BinarySymptom
  heartRateBpm: number | null
}

type CoefficientKey =
  | "intercept"
  | "age_centered"
  | "pain_bin3[mild]"
  | "pain_bin3[severe]"
  | "pain_severe"
  | "fever_or_temp"
  | "vomiting_present"
  | "tachycardia_burden"

const empiricalTermLabels: Record<CoefficientKey, string> = {
  intercept: "Intercept",
  age_centered: "Age, centered at 42",
  "pain_bin3[mild]": "Pain severity: mild",
  "pain_bin3[severe]": "Pain severity: severe",
  pain_severe: "Pain severity: severe vs non-severe",
  fever_or_temp: "Fever or temperature",
  vomiting_present: "Vomiting present",
  tachycardia_burden: "Tachycardia burden",
}

export function toPooledEmpiricalPredictionInputs(
  inputs: ModelInputs,
  age: number,
  heartRateBpm: number | null
): PooledEmpiricalPredictionInputs {
  return {
    age,
    painSeverity: inputs.painSeverity,
    fever: inputs.fever,
    vomiting: inputs.vomiting,
    heartRateBpm,
  }
}

export function predictPooledEmpiricalDisposition(
  inputs: PooledEmpiricalPredictionInputs,
  artifact: PooledEmpiricalModelArtifact = activeEmpiricalModel
): PredictionResult {
  const activeTerms = activePooledEmpiricalTermsForInputs(inputs, artifact)
  const linearPredictor = activeTerms.reduce((sum, term) => sum + term.mean, 0)
  const probabilityAdmit = clampProbability(logistic(linearPredictor))

  return {
    probabilityAdmit,
    probabilityTreatAndRelease: clampProbability(1 - probabilityAdmit),
    linearPredictor,
    activeTerms,
  }
}

export function activePooledEmpiricalTermsForInputs(
  inputs: PooledEmpiricalPredictionInputs,
  artifact: PooledEmpiricalModelArtifact = activeEmpiricalModel
): LogisticTerm[] {
  validateReadyArtifact(artifact)

  if (!Number.isFinite(inputs.age)) {
    throw new Error("Exact age must be finite for the pooled empirical model.")
  }

  if (inputs.painSeverity === "missing") {
    throw new Error(
      "Observed pain severity is required for the active pooled empirical model."
    )
  }

  if (inputs.heartRateBpm === null || !Number.isFinite(inputs.heartRateBpm)) {
    throw new Error(
      "Observed heart rate is required for the active pooled empirical model."
    )
  }

  const coefficients = coefficientMapForArtifact(artifact)
  const ageCoefficient = requiredCoefficient("age_centered", coefficients)
  const tachycardiaCoefficient = requiredCoefficient(
    "tachycardia_burden",
    coefficients
  )
  const tachycardiaBurden = tachycardiaBurdenFromHeartRate(inputs.heartRateBpm)
  const terms: LogisticTerm[] = [
    termFromCoefficient("intercept", coefficients),
    {
      ...termFromCoefficient("age_centered", coefficients),
      mean: ageCoefficient.mean * (inputs.age - 42),
      standardError: ageCoefficient.standardError * Math.abs(inputs.age - 42),
    },
    {
      ...termFromCoefficient("tachycardia_burden", coefficients),
      mean: tachycardiaCoefficient.mean * tachycardiaBurden,
      standardError:
        tachycardiaCoefficient.standardError * Math.abs(tachycardiaBurden),
    },
  ]

  if (artifact.model_id === E_DISPO_V4_MODEL_ID) {
    if (inputs.painSeverity === "severe") {
      terms.push(termFromCoefficient("pain_severe", coefficients))
    } else if (
      inputs.painSeverity !== "mild" &&
      inputs.painSeverity !== "moderate"
    ) {
      throw new Error("Pain severity must be mild, moderate, or severe.")
    }
  } else {
    if (inputs.painSeverity === "mild") {
      terms.push(termFromCoefficient("pain_bin3[mild]", coefficients))
    } else if (inputs.painSeverity === "severe") {
      terms.push(termFromCoefficient("pain_bin3[severe]", coefficients))
    } else if (inputs.painSeverity !== "moderate") {
      throw new Error("Pain severity must be mild, moderate, or severe.")
    }
  }

  if (inputs.fever === "yes") {
    terms.push(termFromCoefficient("fever_or_temp", coefficients))
  } else if (inputs.fever === "unknown") {
    terms.push({
      key: "fever_or_temp.unknown_not_activated",
      label: "Fever unknown; empirical yes indicator not activated",
      mean: 0,
      standardError: 0,
    })
  }

  if (inputs.vomiting === "yes") {
    terms.push(termFromCoefficient("vomiting_present", coefficients))
  } else if (inputs.vomiting === "unknown") {
    terms.push({
      key: "vomiting_present.unknown_not_activated",
      label: "Vomiting unknown; empirical yes indicator not activated",
      mean: 0,
      standardError: 0,
    })
  }

  return terms
}

export function tachycardiaBurdenFromHeartRate(heartRateBpm: number): number {
  if (!Number.isFinite(heartRateBpm)) {
    throw new Error("Heart rate must be finite for tachycardia burden.")
  }

  return Math.max(heartRateBpm - 100, 0) / 10
}

function validateReadyArtifact(artifact: PooledEmpiricalModelArtifact) {
  const status = validatePooledEmpiricalModelArtifact(artifact)

  if (!status.valid) {
    throw new Error(
      `Pooled empirical model artifact is not activation-ready: ${status.issues.join(
        "; "
      )}`
    )
  }
}

function coefficientMapForArtifact(artifact: PooledEmpiricalModelArtifact) {
  const pairs = artifact.predictors.map((predictor) => [
    coefficientKeyForPredictor(predictor.term, predictor.level),
    {
      mean: predictor.center_beta,
      standardError: predictor.se_or_sd,
    },
  ])

  return Object.fromEntries(pairs) as Partial<
    Record<CoefficientKey, { mean: number; standardError: number }>
  >
}

function coefficientKeyForPredictor(
  term: PooledEmpiricalModelArtifact["predictors"][number]["term"],
  level: string
): CoefficientKey {
  if (term === "intercept") {
    return "intercept"
  }

  if (term === "age_centered") {
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

  if (term === "fever_or_temp") {
    return "fever_or_temp"
  }

  if (term === "vomiting_present") {
    return "vomiting_present"
  }

  if (term === "tachycardia_burden" && level === "per_10_bpm_over_100") {
    return "tachycardia_burden"
  }

  throw new Error(`Unsupported pooled empirical predictor: ${term}.${level}`)
}

function termFromCoefficient(
  key: CoefficientKey,
  coefficients: Partial<
    Record<CoefficientKey, { mean: number; standardError: number }>
  >
): LogisticTerm {
  const coefficient = requiredCoefficient(key, coefficients)

  return {
    key,
    label: empiricalTermLabels[key],
    mean: coefficient.mean,
    standardError: coefficient.standardError,
  }
}

function requiredCoefficient(
  key: CoefficientKey,
  coefficients: Partial<
    Record<CoefficientKey, { mean: number; standardError: number }>
  >
) {
  const coefficient = coefficients[key]

  if (!coefficient) {
    throw new Error(`Missing pooled empirical coefficient: ${key}`)
  }

  return coefficient
}
