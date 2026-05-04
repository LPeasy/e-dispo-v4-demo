import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"

import {
  parsePooledEmpiricalCoefficientDrawCsv,
  type PooledEmpiricalCoefficientDraw,
} from "../data/pooledEmpiricalCoefficientDraws"
import { evaluateEligibility, recodeDisposition, recodeEndpoint } from "./endpoint"
import { calculatePas5Acuity, initialPas5Inputs } from "./aap3Acuity"
import { runLatinHypercubeSimulation } from "./latinHypercube"
import { logistic, predictDisposition } from "./logisticModel"
import type { EligibilityState, ModelInputs } from "./types"
import { hasRequiredClassFields } from "./worksheet"

const validInputs: ModelInputs = {
  ageBand: "45_54",
  broadPainRegion: "upper_abdomen",
  painSeverity: "severe",
  onsetDurationCategory: "sudden_less_than_24_hours",
  constantVsIntermittent: "constant",
  vomiting: "yes",
  fever: "no",
  pas5: initialPas5Inputs,
}

const allActiveInputs: ModelInputs = {
  ...validInputs,
  fever: "yes",
  vomiting: "yes",
}

const highAcuityInputs: ModelInputs = {
  ...allActiveInputs,
  pas5: {
    ...initialPas5Inputs,
    immediateConcern: "unsafe_waiting",
  },
}

const pooledEmpiricalCoefficientDraws = parsePooledEmpiricalCoefficientDrawCsv(
  readFileSync("src/data/pooled-empirical-coefficient-draws.csv", "utf-8")
)

const validEligibility: EligibilityState = {
  alreadyInEd: true,
  age: 45,
  sex: "male",
  chiefComplaint: "abdominal_pain",
  traumaRelated: false,
  redFlagStatement: false,
}

function selectedDrawForSingleSample(
  seed: number,
): PooledEmpiricalCoefficientDraw {
  const random = mulberry32(seed)
  const drawIndex = Math.min(
    pooledEmpiricalCoefficientDraws.length - 1,
    Math.floor(random() * pooledEmpiricalCoefficientDraws.length),
  )
  return pooledEmpiricalCoefficientDraws[drawIndex]
}

function expectedJointDrawProbability(
  draw: PooledEmpiricalCoefficientDraw,
  inputs: ModelInputs,
  age: number,
  heartRateBpm: number,
): number {
  let logit =
    draw.coefficients.intercept +
    draw.coefficients.age_centered * (age - 42) +
    draw.coefficients.tachycardia_burden *
      (Math.max(heartRateBpm - 100, 0) / 10)

  if (inputs.painSeverity === "severe") {
    logit += draw.coefficients.pain_severe
  }

  if (inputs.fever === "yes") {
    logit += draw.coefficients.fever_or_temp
  }

  if (inputs.vomiting === "yes") {
    logit += draw.coefficients.vomiting_present
  }

  if (calculatePas5Acuity(inputs.pas5).highAcuityProxy) {
    const coefficient = draw.coefficients.high_acuity_proxy
    assert.equal(typeof coefficient, "number")
    logit += coefficient
  }

  return logistic(logit)
}

function mulberry32(seed: number): () => number {
  let state = seed >>> 0

  return () => {
    state += 0x6d2b79f5
    let value = Math.imul(state ^ (state >>> 15), 1 | state)
    value ^= value + Math.imul(value ^ (value >>> 7), 61 | value)
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296
  }
}

test("endpoint recoding includes only binary disposition labels", () => {
  assert.deepEqual(recodeDisposition("same_hospital_admission"), {
    status: "included",
    label: "admit",
    reason: "Same-hospital inpatient admission/hospitalization.",
  })
  assert.equal(recodeDisposition("home_routine").status, "included")
  assert.equal(recodeDisposition("transfer").status, "excluded")
  assert.equal(recodeDisposition("death_expired").status, "excluded")
  assert.equal(recodeDisposition("ama_lwbs_eloped").status, "excluded")
  assert.equal(recodeDisposition("other_unknown").status, "excluded")
  assert.equal(recodeDisposition("not_mapped").status, "excluded")
})

test("endpoint-refined v3 row recoding matches source package cases", () => {
  assert.equal(recodeEndpoint({ OBSHOS: 1 }).endpointPrimary, "ADMIT")

  const observationDischarged = recodeEndpoint({ OBSDIS: 1 })
  assert.equal(
    observationDischarged.endpointPrimary,
    "EXCLUDE_OBS_DISCHARGED_PRIMARY"
  )
  assert.equal(
    observationDischarged.endpointSensAEventualHome,
    "TREAT_AND_RELEASE"
  )

  const transfer = recodeEndpoint({ TRANOTH: 1 })
  assert.equal(transfer.endpointPrimary, "EXCLUDE_TRANSFER_PRIMARY")
  assert.equal(
    transfer.endpointSensBAcuteEscalation,
    "ACUTE_ESCALATION_POSITIVE"
  )

  const death = recodeEndpoint({ DIEDED: 1 })
  assert.equal(death.endpointPrimary, "EXCLUDE_SENTINEL_DEATH")
  assert.equal(death.sentinelDeathFlag, true)

  assert.equal(recodeEndpoint({ RETREFFU: 1 }).endpointPrimary, "TREAT_AND_RELEASE")
  assert.equal(
    recodeEndpoint({ ADMITHOS: 1, RETREFFU: 1 }).endpointPrimary,
    "EXCLUDE_CONFLICT"
  )
})

test("endpoint recoding handles truthy values, precedence, and source-specific aliases", () => {
  assert.equal(recodeEndpoint({ ADMITHOS: " yes " }).endpointPrimary, "ADMIT")
  assert.equal(
    recodeEndpoint({ no_followup: " TRUE " }).endpointPrimary,
    "TREAT_AND_RELEASE"
  )

  const observationDischarged = recodeEndpoint({
    observation_then_discharged: "Y",
  })
  assert.equal(
    observationDischarged.endpointPrimary,
    "EXCLUDE_OBS_DISCHARGED_PRIMARY"
  )
  assert.equal(
    observationDischarged.endpointSensBAcuteEscalation,
    "TREAT_AND_RELEASE"
  )

  const nursingHomeTransfer = recodeEndpoint({ TRANNH: 1 })
  assert.equal(nursingHomeTransfer.endpointPrimary, "EXCLUDE_TRANSFER_PRIMARY")
  assert.equal(
    nursingHomeTransfer.endpointSensBAcuteEscalation,
    "EXCLUDE_TRANSFER_PRIMARY"
  )

  const acuteTransfer = recodeEndpoint({ transfer_to_other_hospital: true })
  assert.equal(acuteTransfer.endpointPrimary, "EXCLUDE_TRANSFER_PRIMARY")
  assert.equal(
    acuteTransfer.endpointSensBAcuteEscalation,
    "ACUTE_ESCALATION_POSITIVE"
  )

  const deathPlusConflict = recodeEndpoint({ DIEDED: 1, ADMITHOS: 1, NOFU: 1 })
  assert.equal(deathPlusConflict.endpointPrimary, "EXCLUDE_SENTINEL_DEATH")
  assert.equal(deathPlusConflict.sentinelDeathFlag, true)

  assert.equal(
    recodeEndpoint({ hadm_id_present: true }).endpointPrimary,
    "ADMIT"
  )
  assert.equal(
    recodeEndpoint({ discharge_disposition: "not mapped" }).endpointPrimary,
    "EXCLUDE_OTHER_UNKNOWN"
  )
  assert.equal(recodeEndpoint({}).endpointPrimary, "EXCLUDE_OTHER_UNKNOWN")
})

test("eligibility gate blocks out-of-scope cases before output", () => {
  assert.equal(evaluateEligibility(validEligibility).canProceed, true)

  assert.equal(
    evaluateEligibility({ ...validEligibility, alreadyInEd: false }).canProceed,
    false
  )
  assert.equal(evaluateEligibility({ ...validEligibility, age: 65 }).canProceed, false)
  assert.equal(
    evaluateEligibility({ ...validEligibility, sex: "female" }).canProceed,
    false
  )
  assert.equal(
    evaluateEligibility({ ...validEligibility, traumaRelated: true }).canProceed,
    false
  )
  assert.equal(
    evaluateEligibility({ ...validEligibility, redFlagStatement: true })
      .canProceed,
    false
  )
})

test("worksheet class fields are required", () => {
  assert.equal(hasRequiredClassFields(validInputs), true)
  assert.equal(
    hasRequiredClassFields({
      ...validInputs,
      fever: undefined,
    }),
    false
  )
  assert.equal(hasRequiredClassFields({}), false)
})

test("deterministic probabilities are bounded and sum to one", () => {
  const prediction = predictDisposition(validInputs)
  assert.ok(prediction.probabilityAdmit >= 0)
  assert.ok(prediction.probabilityAdmit <= 1)
  assert.ok(prediction.probabilityTreatAndRelease >= 0)
  assert.ok(prediction.probabilityTreatAndRelease <= 1)
  assert.ok(
    Math.abs(
      prediction.probabilityAdmit + prediction.probabilityTreatAndRelease - 1
    ) < 1e-12
  )
})

test("Latin Hypercube simulation is reproducible with a fixed seed", () => {
  const first = runLatinHypercubeSimulation(validInputs, 500, 1234)
  const second = runLatinHypercubeSimulation(validInputs, 500, 1234)

  assert.equal(first.median, second.median)
  assert.equal(first.p10, second.p10)
  assert.equal(first.p90, second.p90)
  assert.deepEqual(first.histogram, second.histogram)
  assert.deepEqual(first.sensitivity, second.sensitivity)
})

test("joint coefficient simulation is reproducible with a fixed seed", () => {
  const first = runLatinHypercubeSimulation(
    validInputs,
    100,
    5678,
    48,
    115,
    pooledEmpiricalCoefficientDraws
  )
  const second = runLatinHypercubeSimulation(
    validInputs,
    100,
    5678,
    48,
    115,
    pooledEmpiricalCoefficientDraws
  )

  assert.deepEqual(first.samples, second.samples)
  assert.deepEqual(first.histogram, second.histogram)
  assert.deepEqual(first.sensitivity, second.sensitivity)
})

test("Latin Hypercube simulation uses full coefficient draw vectors", () => {
  const seed = 901
  const age = 54
  const heartRateBpm = 124
  const selectedDraw = selectedDrawForSingleSample(seed)
  const simulation = runLatinHypercubeSimulation(
    highAcuityInputs,
    1,
    seed,
    age,
    heartRateBpm,
    pooledEmpiricalCoefficientDraws
  )
  const expected = expectedJointDrawProbability(
    selectedDraw,
    highAcuityInputs,
    age,
    heartRateBpm,
  )

  assert.equal(simulation.samples.length, 1)
  assert.ok(Math.abs(simulation.samples[0] - expected) < 1e-12)
})

test("joint coefficient simulation keeps selected inputs fixed", () => {
  const seed = 902
  const selectedDraw = selectedDrawForSingleSample(seed)
  const lowBurden = runLatinHypercubeSimulation(
    allActiveInputs,
    1,
    seed,
    42,
    100,
    pooledEmpiricalCoefficientDraws
  )
  const highBurden = runLatinHypercubeSimulation(
    allActiveInputs,
    1,
    seed,
    52,
    130,
    pooledEmpiricalCoefficientDraws
  )
  const expectedLow = expectedJointDrawProbability(
    selectedDraw,
    allActiveInputs,
    42,
    100,
  )
  const expectedHigh = expectedJointDrawProbability(
    selectedDraw,
    allActiveInputs,
    52,
    130,
  )

  assert.ok(Math.abs(lowBurden.samples[0] - expectedLow) < 1e-12)
  assert.ok(Math.abs(highBurden.samples[0] - expectedHigh) < 1e-12)
  assert.notEqual(lowBurden.samples[0], highBurden.samples[0])
})
