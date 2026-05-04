import {
  GENERAL_E_DISPO_PUBLIC_MODEL_ID,
  generalCoefficientByKey,
} from "@/data/generalEDispoModel"
import { clampProbability, logistic } from "./logisticModel"
import {
  tachycardiaBurdenFromHeartRate,
} from "./pooledEmpiricalPrediction"
import type {
  GeneralAcuityCode,
  GeneralArrivalTransferContext,
  GeneralModelInputs,
  LogisticTerm,
  PredictionResult,
} from "./types"

const referenceAcuity: GeneralAcuityCode = "urgent"
const referenceArrivalTransferContext: GeneralArrivalTransferContext =
  "no_not_transferred_from_hospital_or_urgent_care"

export function predictGeneralEDispoDisposition(
  inputs: GeneralModelInputs
): PredictionResult {
  const activeTerms = activeGeneralEDispoTermsForInputs(inputs)
  const linearPredictor = activeTerms.reduce((sum, term) => sum + term.mean, 0)
  const probabilityAdmit = clampProbability(logistic(linearPredictor))

  return {
    probabilityAdmit,
    probabilityTreatAndRelease: clampProbability(1 - probabilityAdmit),
    linearPredictor,
    activeTerms,
  }
}

export function activeGeneralEDispoTermsForInputs(
  inputs: GeneralModelInputs
): LogisticTerm[] {
  validateGeneralInputs(inputs)

  const ageCoefficient = generalCoefficientByKey("age_centered_40")
  const tachycardiaCoefficient = generalCoefficientByKey("tachycardia_burden")
  const hypotensionCoefficient = generalCoefficientByKey("hypotension_burden")
  const ageCentered = inputs.age - 40
  const tachycardiaBurden = tachycardiaBurdenFromHeartRate(
    inputs.heartRateBpm as number
  )
  const hypotensionBurden = hypotensionBurdenFromSbp(
    inputs.systolicBloodPressure as number
  )
  const terms: LogisticTerm[] = [
    termFromGeneralCoefficient("intercept"),
    {
      ...termFromGeneralCoefficient("age_centered_40"),
      mean: ageCoefficient.beta * ageCentered,
      standardError: ageCoefficient.standardError * Math.abs(ageCentered),
    },
    {
      ...termFromGeneralCoefficient("tachycardia_burden"),
      mean: tachycardiaCoefficient.beta * tachycardiaBurden,
      standardError:
        tachycardiaCoefficient.standardError * Math.abs(tachycardiaBurden),
    },
    {
      ...termFromGeneralCoefficient("hypotension_burden"),
      mean: hypotensionCoefficient.beta * hypotensionBurden,
      standardError:
        hypotensionCoefficient.standardError * Math.abs(hypotensionBurden),
    },
  ]

  if (inputs.sex === "2") {
    terms.push(termFromGeneralCoefficient("sex_2"))
  }

  if (inputs.acuityCode !== referenceAcuity) {
    terms.push(
      termFromGeneralCoefficient(`acuity_code_${inputs.acuityCode}`)
    )
  }

  if (inputs.arrivalTransferContext !== referenceArrivalTransferContext) {
    terms.push(
      termFromGeneralCoefficient(
        `arrival_transfer_context_${inputs.arrivalTransferContext}`
      )
    )
  }

  if (inputs.fever === "yes") {
    terms.push(termFromGeneralCoefficient("fever_or_temp"))
  }

  return terms
}

export function hypotensionBurdenFromSbp(
  systolicBloodPressure: number
): number {
  if (!Number.isFinite(systolicBloodPressure)) {
    throw new Error("Systolic blood pressure must be finite for hypotension burden.")
  }

  return Math.max(100 - systolicBloodPressure, 0) / 10
}

export function generalModelIdForDisplay(): typeof GENERAL_E_DISPO_PUBLIC_MODEL_ID {
  return GENERAL_E_DISPO_PUBLIC_MODEL_ID
}

function validateGeneralInputs(inputs: GeneralModelInputs) {
  if (!Number.isFinite(inputs.age) || inputs.age < 0 || inputs.age > 120) {
    throw new Error("Age must be a finite whole number from 0 to 120 for the general model.")
  }

  if (inputs.heartRateBpm === null || !Number.isFinite(inputs.heartRateBpm)) {
    throw new Error("Observed heart rate is required for the general model.")
  }

  if (
    inputs.systolicBloodPressure === null ||
    !Number.isFinite(inputs.systolicBloodPressure)
  ) {
    throw new Error("Observed systolic blood pressure is required for the general model.")
  }

  if (inputs.fever !== "yes" && inputs.fever !== "no") {
    throw new Error("Fever must be a required yes/no input for the general model.")
  }
}

function termFromGeneralCoefficient(
  key: Parameters<typeof generalCoefficientByKey>[0]
): LogisticTerm {
  const coefficient = generalCoefficientByKey(key)

  return {
    key,
    label: coefficient.label,
    mean: coefficient.beta,
    standardError: coefficient.standardError,
  }
}
