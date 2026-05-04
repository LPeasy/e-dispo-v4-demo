import assert from "node:assert/strict"
import test from "node:test"

import {
  calculatePas5Acuity,
  initialPas5Inputs,
  pas5ClassToGroup,
  pas5ScoreToClass,
  type Pas5Inputs,
} from "./aap3Acuity"

test("PAS-5 default score maps to A5 lower-acuity group", () => {
  const result = calculatePas5Acuity(initialPas5Inputs)

  assert.equal(result.score, 0)
  assert.equal(result.unguardedClass, "A5")
  assert.equal(result.acuityClass, "A5")
  assert.equal(result.group, "lower_acuity")
  assert.equal(result.highAcuityProxy, false)
  assert.equal(result.guardrailApplied, false)
})

test("PAS-5 score thresholds map to the prespecified classes", () => {
  assert.equal(pas5ScoreToClass(0), "A5")
  assert.equal(pas5ScoreToClass(2), "A5")
  assert.equal(pas5ScoreToClass(3), "A4")
  assert.equal(pas5ScoreToClass(5), "A4")
  assert.equal(pas5ScoreToClass(6), "A3")
  assert.equal(pas5ScoreToClass(8), "A3")
  assert.equal(pas5ScoreToClass(9), "A2")
  assert.equal(pas5ScoreToClass(11), "A2")
  assert.equal(pas5ScoreToClass(12), "A1")
  assert.equal(pas5ScoreToClass(15), "A1")
})

test("PAS-5 one guardrail answer prevents class below A2", () => {
  const result = calculatePas5Acuity({
    ...initialPas5Inputs,
    immediateConcern: "unsafe_waiting",
  })

  assert.equal(result.score, 3)
  assert.equal(result.unguardedClass, "A4")
  assert.equal(result.acuityClass, "A2")
  assert.equal(result.group, "high_acuity")
  assert.equal(result.highAcuityProxy, true)
  assert.equal(result.guardrailCount, 1)
  assert.equal(result.guardrailApplied, true)
})

test("PAS-5 two guardrail answers prevent class below A1", () => {
  const result = calculatePas5Acuity({
    ...initialPas5Inputs,
    immediateConcern: "unsafe_waiting",
    distress: "overwhelming",
  })

  assert.equal(result.score, 6)
  assert.equal(result.unguardedClass, "A3")
  assert.equal(result.acuityClass, "A1")
  assert.equal(result.group, "high_acuity")
  assert.equal(result.guardrailCount, 2)
  assert.equal(result.guardrailApplied, true)
})

test("PAS-5 class grouping uses high, urgent reference, and lower groups", () => {
  assert.equal(pas5ClassToGroup("A1"), "high_acuity")
  assert.equal(pas5ClassToGroup("A2"), "high_acuity")
  assert.equal(pas5ClassToGroup("A3"), "urgent_reference")
  assert.equal(pas5ClassToGroup("A4"), "lower_acuity")
  assert.equal(pas5ClassToGroup("A5"), "lower_acuity")
})

test("PAS-5 binary high-acuity proxy is true only for A1/A2", () => {
  assert.equal(
    calculatePas5Acuity({
      ...initialPas5Inputs,
      immediateConcern: "unsafe_waiting",
    }).highAcuityProxy,
    true,
  )
  assert.equal(
    calculatePas5Acuity({
      ...initialPas5Inputs,
      trajectory: "rapidly_worse_or_new_major_symptoms",
      expectedResources: "labs_iv_or_imaging",
      distress: "uncomfortable",
    }).highAcuityProxy,
    false,
  )
  assert.equal(calculatePas5Acuity(initialPas5Inputs).highAcuityProxy, false)
})

test("PAS-5 rejects missing or unsupported answers", () => {
  const missing = {
    ...initialPas5Inputs,
    distress: undefined,
  } as unknown as Pas5Inputs
  const unsupported = {
    ...initialPas5Inputs,
    trajectory: "unknown",
  } as unknown as Pas5Inputs

  assert.throws(
    () => calculatePas5Acuity(missing),
    /Missing PAS-5 answer for distress/,
  )
  assert.throws(
    () => calculatePas5Acuity(unsupported),
    /Missing PAS-5 answer for trajectory/,
  )
})
