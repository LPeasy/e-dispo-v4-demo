import assert from "node:assert/strict"
import test from "node:test"

import {
  aap3AcuityClasses,
  calculateAap3Posterior,
  initialAap3Inputs,
} from "./aap3Acuity"
import { predictPooledEmpiricalDisposition } from "./pooledEmpiricalPrediction"

test("AAP-3 posterior probabilities sum to 1", () => {
  const posterior = calculateAap3Posterior(initialAap3Inputs)
  const total = aap3AcuityClasses.reduce(
    (sum, { id }) => sum + posterior.probabilities[id],
    0
  )

  assert.ok(Math.abs(total - 1) < 1e-12)
})

test("higher danger and distress shifts posterior mass toward A1/A2", () => {
  const lowConcern = calculateAap3Posterior({
    ...initialAap3Inputs,
    dangerDistress: "q1_1_none",
  })
  const highConcern = calculateAap3Posterior({
    ...initialAap3Inputs,
    dangerDistress: "q1_5_danger_or_immediate_concern",
  })

  const lowHighAcuity =
    lowConcern.probabilities.A1 + lowConcern.probabilities.A2
  const highHighAcuity =
    highConcern.probabilities.A1 + highConcern.probabilities.A2

  assert.ok(highHighAcuity > lowHighAcuity)
})

test("unknown vitals differs from normal vitals", () => {
  const normalVitals = calculateAap3Posterior({
    ...initialAap3Inputs,
    vitalsSystemic: "q2_1_normal_vitals",
  })
  const unknownVitals = calculateAap3Posterior({
    ...initialAap3Inputs,
    vitalsSystemic: "q2_2_vitals_unknown",
  })

  assert.notEqual(
    normalVitals.probabilities.A4 + normalVitals.probabilities.A5,
    unknownVitals.probabilities.A4 + unknownVitals.probabilities.A5
  )
})

test("Q1-5 guardrail prevents low-acuity down-triage", () => {
  const posterior = calculateAap3Posterior({
    dangerDistress: "q1_5_danger_or_immediate_concern",
    vitalsSystemic: "q2_1_normal_vitals",
    abdominalFeatures: "q3_1_no_high_risk_features",
  })

  assert.equal(posterior.guardrailApplied, true)
  assert.ok(posterior.probabilities.A4 + posterior.probabilities.A5 <= 0.0500000001)
  assert.ok(
    posterior.probabilities.A1 + posterior.probabilities.A2 >
      posterior.probabilities.A4 + posterior.probabilities.A5
  )
})

test("AAP-3 output does not change empirical P(admit)", () => {
  const empiricalInputs = {
    age: 42,
    painSeverity: "moderate" as const,
    fever: "no" as const,
    vomiting: "no" as const,
    heartRateBpm: 100,
  }
  const lowConcernAap3 = calculateAap3Posterior({
    dangerDistress: "q1_1_none",
    vitalsSystemic: "q2_1_normal_vitals",
    abdominalFeatures: "q3_1_no_high_risk_features",
  })
  const highConcernAap3 = calculateAap3Posterior({
    dangerDistress: "q1_5_danger_or_immediate_concern",
    vitalsSystemic: "q2_5_unstable_systemic",
    abdominalFeatures: "q3_4_bleeding_or_severe_abdominal_features",
  })

  const lowConcernRiskInputs = {
    ...empiricalInputs,
    aap3: lowConcernAap3,
  }
  const highConcernRiskInputs = {
    ...empiricalInputs,
    aap3: highConcernAap3,
  }
  const lowConcernRisk = predictPooledEmpiricalDisposition(lowConcernRiskInputs)
  const highConcernRisk = predictPooledEmpiricalDisposition(highConcernRiskInputs)

  assert.equal(lowConcernRisk.probabilityAdmit, highConcernRisk.probabilityAdmit)
  assert.equal(lowConcernAap3.evidenceLabel, "prototype_acuity_proxy")
  assert.equal(highConcernAap3.evidenceLabel, "prototype_acuity_proxy")
})
