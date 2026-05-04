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
import {
  GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID,
  GENERAL_E_DISPO_HOME_MODEL_ID,
  generalCoefficientByKey,
} from "../data/generalEDispoModel"
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

test("general E-Dispo home default applies age, sex, PAS-5 high-acuity proxy, fever, and HR without SBP", () => {
  const highAcuityPas5 = {
    ...initialPas5Inputs,
    immediateConcern: "unsafe_waiting",
  }
  const generalInputs: GeneralModelInputs = {
    age: 50,
    sex: "2",
    pas5: highAcuityPas5,
    fever: "yes",
    heartRateBpm: 120,
    systolicBloodPressure: null,
  }
  const modelId = GENERAL_E_DISPO_HOME_MODEL_ID
  const prediction = predictGeneralEDispoDisposition(generalInputs)
  const expectedLinearPredictor =
    generalCoefficientByKey("intercept", modelId).beta +
    generalCoefficientByKey("age_centered_40", modelId).beta * 10 +
    generalCoefficientByKey("sex_2", modelId).beta +
    generalCoefficientByKey("high_acuity_proxy", modelId).beta +
    generalCoefficientByKey("fever_or_temp", modelId).beta +
    generalCoefficientByKey("tachycardia_burden", modelId).beta * 2

  assert.ok(Math.abs(prediction.linearPredictor - expectedLinearPredictor) < 1e-12)
  assert.ok(
    Math.abs(prediction.probabilityAdmit - logistic(expectedLinearPredictor)) <
      1e-12
  )
  assert.equal(
    prediction.activeTerms.some((term) => term.key === "sex_2"),
    true
  )
  assert.equal(
    prediction.activeTerms.some((term) => term.key === "pain_severe"),
    false
  )
  assert.equal(
    prediction.activeTerms.some((term) => term.key === "high_acuity_proxy"),
    true
  )
  assert.equal(
    prediction.activeTerms.some((term) => term.key === "hypotension_burden"),
    false
  )
})

test("general E-Dispo measured-SBP branch applies hypotension burden when SBP is supplied", () => {
  const highAcuityPas5 = {
    ...initialPas5Inputs,
    immediateConcern: "unsafe_waiting",
  }
  const generalInputs: GeneralModelInputs = {
    age: 50,
    sex: "2",
    pas5: highAcuityPas5,
    fever: "yes",
    heartRateBpm: 120,
    systolicBloodPressure: 80,
  }
  const modelId = GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID
  const prediction = predictGeneralEDispoDisposition(generalInputs)
  const expectedLinearPredictor =
    generalCoefficientByKey("intercept", modelId).beta +
    generalCoefficientByKey("age_centered_40", modelId).beta * 10 +
    generalCoefficientByKey("sex_2", modelId).beta +
    generalCoefficientByKey("high_acuity_proxy", modelId).beta +
    generalCoefficientByKey("fever_or_temp", modelId).beta +
    generalCoefficientByKey("tachycardia_burden", modelId).beta * 2 +
    generalCoefficientByKey("hypotension_burden", modelId).beta * 2

  assert.ok(Math.abs(prediction.linearPredictor - expectedLinearPredictor) < 1e-12)
  assert.ok(
    Math.abs(prediction.probabilityAdmit - logistic(expectedLinearPredictor)) <
      1e-12
  )
  assert.equal(
    prediction.activeTerms.some((term) => term.key === "hypotension_burden"),
    true
  )
})

test("general E-Dispo model blocks missing HR but allows missing SBP", () => {
  const generalInputs: GeneralModelInputs = {
    age: 40,
    sex: "1",
    pas5: initialPas5Inputs,
    fever: "no",
    heartRateBpm: null,
    systolicBloodPressure: null,
  }

  assert.throws(
    () => predictGeneralEDispoDisposition(generalInputs),
    /Observed heart rate is required/
  )
})
