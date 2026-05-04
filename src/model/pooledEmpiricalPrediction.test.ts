import assert from "node:assert/strict"
import test from "node:test"

import { logistic } from "./logisticModel"
import {
  predictGeneralEDispoDisposition,
} from "./generalEDispoPrediction"
import {
  predictPooledEmpiricalDisposition,
  type PooledEmpiricalPredictionInputs,
} from "./pooledEmpiricalPrediction"
import {
  calculatePas5Acuity,
  initialPas5Inputs,
} from "./aap3Acuity"
import {
  eDispoV4Model,
  eDispoV41Pas5Model,
} from "../data/eDispoV4Model"
import { pooledEmpiricalModel } from "../data/pooledEmpiricalModel"
import type { GeneralModelInputs } from "./types"

const baselineInputs: PooledEmpiricalPredictionInputs = {
  age: 42,
  painSeverity: "moderate",
  fever: "no",
  vomiting: "no",
  heartRateBpm: 100,
  pas5: calculatePas5Acuity(initialPas5Inputs),
}

const coefficients = {
  intercept: -2.76223123530477,
  ageCentered: 0.0450480147935024,
  painSevere: 0.556443332598118,
  fever: 0.994381942387039,
  vomiting: 0.431253333679371,
  tachycardiaBurden: 0.456426837475548,
  highAcuityProxy: 1.24984421126593,
}

test("pooled empirical prediction uses exact age centered at 42", () => {
  const age42 = predictPooledEmpiricalDisposition(baselineInputs)
  const age47 = predictPooledEmpiricalDisposition({ ...baselineInputs, age: 47 })

  assert.equal(age42.linearPredictor, coefficients.intercept)
  assert.equal(
    age47.linearPredictor,
    coefficients.intercept + coefficients.ageCentered * 5
  )
})

test("mild and moderate pain are the active non-severe reference", () => {
  const mild = predictPooledEmpiricalDisposition({
    ...baselineInputs,
    painSeverity: "mild",
  })
  const prediction = predictPooledEmpiricalDisposition({
    ...baselineInputs,
    painSeverity: "moderate",
  })

  assert.equal(mild.linearPredictor, coefficients.intercept)
  assert.equal(prediction.linearPredictor, coefficients.intercept)
  assert.equal(
    prediction.activeTerms.some((term) => term.key === "pain_severe"),
    false
  )
})

test("severe pain applies the active severe-vs-non-severe coefficient", () => {
  const severe = predictPooledEmpiricalDisposition({
    ...baselineInputs,
    painSeverity: "severe",
  })

  assert.equal(
    severe.linearPredictor,
    coefficients.intercept + coefficients.painSevere
  )
})

test("archived v2 model still supports flexible pain when explicitly supplied", () => {
  const mild = predictPooledEmpiricalDisposition(
    {
      ...baselineInputs,
      painSeverity: "mild",
    },
    pooledEmpiricalModel
  )
  const severe = predictPooledEmpiricalDisposition(
    {
      ...baselineInputs,
      painSeverity: "severe",
    },
    pooledEmpiricalModel
  )

  assert.equal(mild.activeTerms.some((term) => term.key === "pain_bin3[mild]"), true)
  assert.equal(
    severe.activeTerms.some((term) => term.key === "pain_bin3[severe]"),
    true
  )
})

test("pain missing is not an active app path", () => {
  assert.throws(() =>
    predictPooledEmpiricalDisposition({
      ...baselineInputs,
      painSeverity: "missing",
    }),
    /Observed pain severity is required/
  )
})

test("missing HR blocks active empirical prediction", () => {
  assert.throws(() =>
    predictPooledEmpiricalDisposition({
      ...baselineInputs,
      heartRateBpm: null,
    }),
    /Observed heart rate is required/
  )
})

test("tachycardia burden scales above HR 100 by 10 bpm units", () => {
  const hr100 = predictPooledEmpiricalDisposition({
    ...baselineInputs,
  })
  const hr110 = predictPooledEmpiricalDisposition({
    ...baselineInputs,
    heartRateBpm: 110,
  })
  const hr120 = predictPooledEmpiricalDisposition({
    ...baselineInputs,
    heartRateBpm: 120,
  })

  assert.equal(hr100.linearPredictor, coefficients.intercept)
  assert.equal(
    hr110.linearPredictor,
    coefficients.intercept + coefficients.tachycardiaBurden
  )
  assert.equal(
    hr120.linearPredictor,
    coefficients.intercept + coefficients.tachycardiaBurden * 2
  )
})

test("fever and vomiting yes indicators apply empirical coefficients", () => {
  const prediction = predictPooledEmpiricalDisposition({
    ...baselineInputs,
    fever: "yes",
    vomiting: "yes",
  })

  assert.equal(
    prediction.linearPredictor,
    coefficients.intercept + coefficients.fever + coefficients.vomiting
  )
  assert.equal(
    prediction.probabilityAdmit,
    logistic(coefficients.intercept + coefficients.fever + coefficients.vomiting)
  )
})

test("archived e-dispo-v4.0 ignores PAS-5 when explicitly supplied", () => {
  const highConcernPas5 = calculatePas5Acuity({
    ...initialPas5Inputs,
    immediateConcern: "unsafe_waiting",
  })
  const unchangedInputs = {
    ...baselineInputs,
    broadPainRegion: "upper_abdomen",
    onsetDurationCategory: "sudden_less_than_24_hours",
    constantVsIntermittent: "constant",
    hematemesis: "yes",
    pas5: highConcernPas5,
    systolicBloodPressure: 86,
  }

  const baseline = predictPooledEmpiricalDisposition(baselineInputs, eDispoV4Model)
  const withUnsupported = predictPooledEmpiricalDisposition(
    unchangedInputs,
    eDispoV4Model
  )

  assert.equal(withUnsupported.probabilityAdmit, baseline.probabilityAdmit)
  assert.equal(withUnsupported.linearPredictor, baseline.linearPredictor)
})

test("active e-dispo-v4.1 maps PAS-5 A1/A2 to binary high-acuity proxy", () => {
  const a1Pas5 = calculatePas5Acuity({
    ...initialPas5Inputs,
    immediateConcern: "unsafe_waiting",
    distress: "overwhelming",
  })
  const a2Pas5 = calculatePas5Acuity({
    ...initialPas5Inputs,
    immediateConcern: "unsafe_waiting",
  })
  const a3Pas5 = calculatePas5Acuity({
    ...initialPas5Inputs,
    trajectory: "rapidly_worse_or_new_major_symptoms",
    expectedResources: "labs_iv_or_imaging",
    distress: "uncomfortable",
  })
  const a4Pas5 = calculatePas5Acuity({
    ...initialPas5Inputs,
    expectedResources: "monitoring_procedure_specialist_or_possible_hospitalization",
  })
  const a5Pas5 = calculatePas5Acuity(initialPas5Inputs)

  const a1 = predictPooledEmpiricalDisposition(
    { ...baselineInputs, pas5: a1Pas5 },
    eDispoV41Pas5Model
  )
  const a2 = predictPooledEmpiricalDisposition(
    { ...baselineInputs, pas5: a2Pas5 },
    eDispoV41Pas5Model
  )
  const a3 = predictPooledEmpiricalDisposition(
    { ...baselineInputs, pas5: a3Pas5 },
    eDispoV41Pas5Model
  )
  const a4 = predictPooledEmpiricalDisposition(
    { ...baselineInputs, pas5: a4Pas5 },
    eDispoV41Pas5Model
  )
  const a5 = predictPooledEmpiricalDisposition(
    { ...baselineInputs, pas5: a5Pas5 },
    eDispoV41Pas5Model
  )

  assert.equal(a1Pas5.acuityClass, "A1")
  assert.equal(a2Pas5.acuityClass, "A2")
  assert.equal(a3Pas5.acuityClass, "A3")
  assert.equal(a4Pas5.acuityClass, "A4")
  assert.equal(a5Pas5.acuityClass, "A5")
  assert.equal(
    a1.linearPredictor,
    coefficients.intercept + coefficients.highAcuityProxy
  )
  assert.equal(
    a2.linearPredictor,
    coefficients.intercept + coefficients.highAcuityProxy
  )
  assert.equal(a3.linearPredictor, coefficients.intercept)
  assert.equal(a4.linearPredictor, coefficients.intercept)
  assert.equal(a5.linearPredictor, coefficients.intercept)
})

test("general E-Dispo sex-adjusted model applies age, sex, acuity, arrival, fever, HR, and SBP terms", () => {
  const generalInputs: GeneralModelInputs = {
    age: 50,
    sex: "2",
    acuityCode: "emergent",
    arrivalTransferContext:
      "yes_transferred_from_hospital_or_urgent_care",
    fever: "yes",
    heartRateBpm: 120,
    systolicBloodPressure: 80,
  }
  const prediction = predictGeneralEDispoDisposition(generalInputs)
  const expectedLinearPredictor =
    -1.63407360872993 +
    0.0348494496590697 * 10 +
    0.204515775369273 +
    1.12126625563577 +
    1.57019283241495 +
    0.399404017910802 +
    0.262091867980015 * 2 +
    0.752126485698012 * 2

  assert.equal(prediction.linearPredictor, expectedLinearPredictor)
  assert.equal(prediction.probabilityAdmit, logistic(expectedLinearPredictor))
  assert.equal(
    prediction.activeTerms.some((term) => term.key === "sex_2"),
    true
  )
  assert.equal(
    prediction.activeTerms.some((term) => term.key === "pain_severe"),
    false
  )
})

test("general E-Dispo model blocks missing vitals", () => {
  const generalInputs: GeneralModelInputs = {
    age: 40,
    sex: "1",
    acuityCode: "urgent",
    arrivalTransferContext:
      "no_not_transferred_from_hospital_or_urgent_care",
    fever: "no",
    heartRateBpm: null,
    systolicBloodPressure: 120,
  }

  assert.throws(
    () => predictGeneralEDispoDisposition(generalInputs),
    /Observed heart rate is required/
  )
})
