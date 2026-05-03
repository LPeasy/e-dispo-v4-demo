import assert from "node:assert/strict"
import test from "node:test"

import { logistic } from "./logisticModel"
import {
  predictPooledEmpiricalDisposition,
  type PooledEmpiricalPredictionInputs,
} from "./pooledEmpiricalPrediction"
import { pooledEmpiricalModel } from "../data/pooledEmpiricalModel"

const baselineInputs: PooledEmpiricalPredictionInputs = {
  age: 42,
  painSeverity: "moderate",
  fever: "no",
  vomiting: "no",
  heartRateBpm: 100,
}

const coefficients = {
  intercept: -2.5279874917252374,
  ageCentered: 0.043118787834530395,
  painSevere: 0.52181881795062,
  fever: 0.8870420313203969,
  vomiting: 0.46912257968096427,
  tachycardiaBurden: 0.4269432162227637,
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

test("mild and moderate pain are the e-dispo-v4.0 non-severe reference", () => {
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

test("severe pain applies the e-dispo-v4.0 severe-vs-non-severe coefficient", () => {
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

test("pain missing is not an active e-dispo-v4.0 app path", () => {
  assert.throws(() =>
    predictPooledEmpiricalDisposition({
      ...baselineInputs,
      painSeverity: "missing",
    }),
    /Observed pain severity is required/
  )
})

test("missing HR blocks e-dispo-v4.0 empirical prediction", () => {
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

test("unsupported prototype inputs do not change empirical P(admit)", () => {
  const unchangedInputs = {
    ...baselineInputs,
    broadPainRegion: "upper_abdomen",
    onsetDurationCategory: "sudden_less_than_24_hours",
    constantVsIntermittent: "constant",
    hematemesis: "yes",
    aap3: { dangerDistress: "q1_5_danger_or_immediate_concern" },
    systolicBloodPressure: 86,
  }

  const baseline = predictPooledEmpiricalDisposition(baselineInputs)
  const withUnsupported = predictPooledEmpiricalDisposition(unchangedInputs)

  assert.equal(withUnsupported.probabilityAdmit, baseline.probabilityAdmit)
  assert.equal(withUnsupported.linearPredictor, baseline.linearPredictor)
})
