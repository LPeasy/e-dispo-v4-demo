import {
  generalCoefficientByKey,
  generalModelForInputs,
  generalModelIdForInputs,
} from "@/data/generalEDispoModel"
import { calculatePas5Acuity, initialPas5Inputs } from "./aap3Acuity"
import { clampProbability, logistic } from "./logisticModel"
import {
  tachycardiaBurdenFromHeartRate,
} from "./pooledEmpiricalPrediction"
import type {
  GeneralModelInputs,
  LogisticTerm,
  PredictionResult,
  RunnableModelId,
} from "./types"

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

  const model = generalModelForInputs(inputs)
  const ageCoefficient = generalCoefficientByKey(
    "age_centered_40",
    model.modelId
  )
  const tachycardiaCoefficient = generalCoefficientByKey(
    "tachycardia_burden",
    model.modelId
  )
  const ageCentered = inputs.age - 40
  const tachycardiaBurden = tachycardiaBurdenFromHeartRate(
    inputs.heartRateBpm as number
  )
  const pas5 = calculatePas5Acuity(inputs.pas5)
  const terms: LogisticTerm[] = [
    termFromGeneralCoefficient("intercept", model.modelId),
    {
      ...termFromGeneralCoefficient("age_centered_40", model.modelId),
      mean: ageCoefficient.beta * ageCentered,
      standardError: ageCoefficient.standardError * Math.abs(ageCentered),
    },
    {
      ...termFromGeneralCoefficient("tachycardia_burden", model.modelId),
      mean: tachycardiaCoefficient.beta * tachycardiaBurden,
      standardError:
        tachycardiaCoefficient.standardError * Math.abs(tachycardiaBurden),
    },
  ]

  if (inputs.sex === "2") {
    terms.push(termFromGeneralCoefficient("sex_2", model.modelId))
  }

  if (pas5.highAcuityProxy) {
    terms.push(termFromGeneralCoefficient("high_acuity_proxy", model.modelId))
  }

  if (inputs.systolicBloodPressure !== null) {
    const hypotensionCoefficient = generalCoefficientByKey(
      "hypotension_burden",
      model.modelId
    )
    const hypotensionBurden = hypotensionBurdenFromSbp(
      inputs.systolicBloodPressure
    )
    terms.push({
      ...termFromGeneralCoefficient("hypotension_burden", model.modelId),
      mean: hypotensionCoefficient.beta * hypotensionBurden,
      standardError:
        hypotensionCoefficient.standardError * Math.abs(hypotensionBurden),
    })
  }

  if (inputs.fever === "yes") {
    terms.push(termFromGeneralCoefficient("fever_or_temp", model.modelId))
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

export function generalModelIdForDisplay(
  inputs?: GeneralModelInputs
): RunnableModelId {
  return inputs ? generalModelIdForInputs(inputs) : generalModelIdForInputs({
    age: 40,
    sex: "1",
    pas5: initialPas5Inputs,
    fever: "no",
    heartRateBpm: 88,
    systolicBloodPressure: null,
  })
}

function validateGeneralInputs(inputs: GeneralModelInputs) {
  if (!Number.isFinite(inputs.age) || inputs.age < 0 || inputs.age > 120) {
    throw new Error("Age must be a finite whole number from 0 to 120 for the general model.")
  }

  if (inputs.heartRateBpm === null || !Number.isFinite(inputs.heartRateBpm)) {
    throw new Error("Observed heart rate is required for the general model.")
  }

  if (
    inputs.systolicBloodPressure !== null &&
    !Number.isFinite(inputs.systolicBloodPressure)
  ) {
    throw new Error("Systolic blood pressure must be finite when supplied.")
  }

  if (inputs.fever !== "yes" && inputs.fever !== "no") {
    throw new Error("Fever must be a required yes/no input for the general model.")
  }
}

function termFromGeneralCoefficient(
  key: Parameters<typeof generalCoefficientByKey>[0],
  modelId: Parameters<typeof generalCoefficientByKey>[1]
): LogisticTerm {
  const coefficient = generalCoefficientByKey(key, modelId)

  return {
    key,
    label: coefficient.label,
    mean: coefficient.beta,
    standardError: coefficient.standardError,
  }
}
