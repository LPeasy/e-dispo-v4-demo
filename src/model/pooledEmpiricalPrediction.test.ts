import assert from "node:assert/strict"
import test from "node:test"

import { logistic } from "./logisticModel"
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
  E_DISPO_V4_1_PAS5_MODEL_ID,
} from "../data/eDispoV4Model"
import {
  pooledEmpiricalModel,
  type PooledEmpiricalModelArtifact,
} from "../data/pooledEmpiricalModel"

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

const highAcuityProxyCoefficient = 0.7

const v41Pas5Artifact: PooledEmpiricalModelArtifact = {
  ...eDispoV4Model,
  model_id: E_DISPO_V4_1_PAS5_MODEL_ID,
  model_version: "e_dispo_v4_1_pas5_high_acuity_test_fixture",
  run_id: "pas5_test_fixture",
  covariance_matrix_path:
    "outputs/nhamcs_pooled/pas5_acuity_test_fixture_covariance.csv",
  posterior_draws_path:
    "outputs/nhamcs_pooled/pas5_acuity_test_fixture_draws.csv",
  predictor_evidence_tiers: [
    ...eDispoV4Model.predictor_evidence_tiers,
    {
      blockers: "",
      evidence_tier: "dataset_derived",
      level: "1",
      term: "high_acuity_proxy",
    },
  ],
  predictors: [
    ...eDispoV4Model.predictors,
    {
      center_beta: highAcuityProxyCoefficient,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "1",
      limitation_note:
        "Test fixture for PAS-5 high-acuity IMMEDR surrogate coefficient plumbing only.",
      reference: false,
      se_or_sd: 0.12,
      source: "NHAMCS_2018_2022_POOLED",
      term: "high_acuity_proxy",
    },
  ],
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

test("PAS-5 input does not change P(admit) while e-dispo-v4.0 is active", () => {
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

  const baseline = predictPooledEmpiricalDisposition(baselineInputs)
  const withUnsupported = predictPooledEmpiricalDisposition(unchangedInputs)

  assert.equal(withUnsupported.probabilityAdmit, baseline.probabilityAdmit)
  assert.equal(withUnsupported.linearPredictor, baseline.linearPredictor)
})

test("e-dispo-v4.1 PAS-5 candidate maps A1/A2 to binary high-acuity proxy", () => {
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
    v41Pas5Artifact
  )
  const a2 = predictPooledEmpiricalDisposition(
    { ...baselineInputs, pas5: a2Pas5 },
    v41Pas5Artifact
  )
  const a3 = predictPooledEmpiricalDisposition(
    { ...baselineInputs, pas5: a3Pas5 },
    v41Pas5Artifact
  )
  const a4 = predictPooledEmpiricalDisposition(
    { ...baselineInputs, pas5: a4Pas5 },
    v41Pas5Artifact
  )
  const a5 = predictPooledEmpiricalDisposition(
    { ...baselineInputs, pas5: a5Pas5 },
    v41Pas5Artifact
  )

  assert.equal(a1Pas5.acuityClass, "A1")
  assert.equal(a2Pas5.acuityClass, "A2")
  assert.equal(a3Pas5.acuityClass, "A3")
  assert.equal(a4Pas5.acuityClass, "A4")
  assert.equal(a5Pas5.acuityClass, "A5")
  assert.equal(
    a1.linearPredictor,
    coefficients.intercept + highAcuityProxyCoefficient
  )
  assert.equal(
    a2.linearPredictor,
    coefficients.intercept + highAcuityProxyCoefficient
  )
  assert.equal(a3.linearPredictor, coefficients.intercept)
  assert.equal(a4.linearPredictor, coefficients.intercept)
  assert.equal(a5.linearPredictor, coefficients.intercept)
})
