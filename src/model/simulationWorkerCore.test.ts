import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"

import {
  CoefficientDrawAssetError,
  clearPooledEmpiricalCoefficientDrawCache,
  loadCoefficientDrawsForModel,
  loadPooledEmpiricalCoefficientDraws,
  parsePooledEmpiricalCoefficientDrawCsv,
  pooledEmpiricalCoefficientDrawAssetUrl,
} from "../data/pooledEmpiricalCoefficientDraws"
import {
  GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID,
  GENERAL_E_DISPO_PUBLIC_MODEL_ID,
} from "../data/generalEDispoModel"
import { modelMetadata } from "./modelParameters"
import { initialPas5Inputs } from "./aap3Acuity"
import { isCurrentSimulationResponse } from "./simulationProtocol"
import {
  clearSimulationCache,
  runCachedSimulation,
} from "./simulationWorkerCore"
import type { GeneralModelInputs, ModelInputs } from "./types"

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

const coefficientDrawCsv = readFileSync(
  "src/data/pooled-empirical-coefficient-draws.csv",
  "utf-8"
)

const coefficientDraws = parsePooledEmpiricalCoefficientDrawCsv(
  coefficientDrawCsv
)

const generalCoefficientDrawCsv = readFileSync(
  "src/data/general-e-dispo-home-coefficient-draws.csv",
  "utf-8"
)

const generalCoefficientDraws = parsePooledEmpiricalCoefficientDrawCsv(
  generalCoefficientDrawCsv,
  GENERAL_E_DISPO_PUBLIC_MODEL_ID
)

const generalMeasuredSbpCoefficientDrawCsv = readFileSync(
  "src/data/general-e-dispo-home-measured-sbp-coefficient-draws.csv",
  "utf-8"
)

const generalMeasuredSbpCoefficientDraws =
  parsePooledEmpiricalCoefficientDrawCsv(
    generalMeasuredSbpCoefficientDrawCsv,
    GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID
  )

const validGeneralInputs: GeneralModelInputs = {
  age: 50,
  sex: "2",
  pas5: {
    ...initialPas5Inputs,
    immediateConcern: "unsafe_waiting",
  },
  fever: "yes",
  heartRateBpm: 112,
  systolicBloodPressure: null,
}

test("coefficient draw loader resolves the Vite-managed asset URL", async () => {
  clearPooledEmpiricalCoefficientDrawCache()
  const assetPath = "managed://pooled-empirical-coefficient-draws.csv"
  let requestedPath = ""

  const loadedDraws = await loadPooledEmpiricalCoefficientDraws({
    assetPath,
    fetchDraws: async (input) => {
      requestedPath = input
      return {
        ok: true,
        status: 200,
        text: async () => coefficientDrawCsv,
      }
    },
  })

  assert.equal(requestedPath, assetPath)
  assert.equal(loadedDraws.length, modelMetadata.sampleCount / 10)
  assert.match(
    pooledEmpiricalCoefficientDrawAssetUrl,
    /pooled-empirical-coefficient-draws\.csv/
  )
  assert.doesNotMatch(pooledEmpiricalCoefficientDrawAssetUrl, /^\/data\//)
  clearPooledEmpiricalCoefficientDrawCache()
})

test("coefficient draw loader fails fast when the asset cannot resolve", async () => {
  clearPooledEmpiricalCoefficientDrawCache()

  await assert.rejects(
    loadPooledEmpiricalCoefficientDraws({
      assetPath: "managed://missing-draws.csv",
      fetchDraws: async () => ({
        ok: false,
        status: 404,
        text: async () => "",
      }),
      timeoutMs: 100,
    }),
    (error) =>
      error instanceof CoefficientDrawAssetError &&
      error.code === "http_error"
  )
})

test("coefficient draw loader times out instead of staying pending", async () => {
  clearPooledEmpiricalCoefficientDrawCache()

  await assert.rejects(
    loadPooledEmpiricalCoefficientDraws({
      assetPath: "managed://slow-draws.csv",
      fetchDraws: async () => new Promise(() => undefined),
      timeoutMs: 1,
    }),
    (error) =>
      error instanceof CoefficientDrawAssetError &&
      error.code === "fetch_timeout"
  )
})

test("worker core loads draw data once and caches simulation repeats", async () => {
  clearSimulationCache()
  let drawLoadCount = 0
  const loadCoefficientDraws = async () => {
    drawLoadCount += 1
    return coefficientDraws
  }

  const first = await runCachedSimulation(
    {
      requestId: 1,
      inputs: validInputs,
    },
    { loadCoefficientDraws }
  )
  assert.equal(first.status, "complete")
  assert.equal(first.cached, false)
  assert.equal(first.result.sampleCount, modelMetadata.sampleCount)
  assert.equal(first.result.sampleCount, 100000)
  assert.ok(first.result.median >= 0)
  assert.ok(first.result.median <= 1)

  const second = await runCachedSimulation(
    {
      requestId: 2,
      inputs: validInputs,
    },
    { loadCoefficientDraws }
  )
  assert.equal(second.status, "complete")
  assert.equal(second.cached, true)
  assert.deepEqual(second.result, first.result)
  assert.equal(drawLoadCount, 1)
})

test("general coefficient draw loader resolves and validates the separate asset schema", async () => {
  clearPooledEmpiricalCoefficientDrawCache()
  const assetPath = "managed://general-e-dispo-home-coefficient-draws.csv"
  let requestedPath = ""

  const loadedDraws = await loadCoefficientDrawsForModel(
    GENERAL_E_DISPO_PUBLIC_MODEL_ID,
    {
      assetPath,
      fetchDraws: async (input) => {
        requestedPath = input
        return {
          ok: true,
          status: 200,
          text: async () => generalCoefficientDrawCsv,
        }
      },
    }
  )

  assert.equal(requestedPath, assetPath)
  assert.equal(loadedDraws.length, 10000)
  assert.equal(loadedDraws[0].modelId, GENERAL_E_DISPO_PUBLIC_MODEL_ID)
  assert.equal(loadedDraws[0].seed, 20260504)
  assert.equal(
    Number.isFinite(
      loadedDraws[0].coefficients.tachycardia_burden
    ),
    true
  )
  assert.equal(loadedDraws[0].coefficients.hypotension_burden, undefined)
  clearPooledEmpiricalCoefficientDrawCache()
})

test("measured-SBP general coefficient draw loader validates the SBP branch schema", async () => {
  clearPooledEmpiricalCoefficientDrawCache()
  const loadedDraws = await loadCoefficientDrawsForModel(
    GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID,
    {
      assetPath: "managed://general-e-dispo-home-measured-sbp-coefficient-draws.csv",
      fetchDraws: async () => ({
        ok: true,
        status: 200,
        text: async () => generalMeasuredSbpCoefficientDrawCsv,
      }),
    }
  )

  assert.equal(loadedDraws.length, 10000)
  assert.equal(
    loadedDraws[0].modelId,
    GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID
  )
  assert.equal(loadedDraws[0].seed, 20260504)
  assert.equal(
    Number.isFinite(loadedDraws[0].coefficients.hypotension_burden),
    true
  )
  clearPooledEmpiricalCoefficientDrawCache()
})

test("worker core runs the general E-Dispo model with model-specific draw data", async () => {
  clearSimulationCache()
  const response = await runCachedSimulation(
    {
      requestId: 30,
      modelId: GENERAL_E_DISPO_PUBLIC_MODEL_ID,
      inputs: validInputs,
      generalInputs: validGeneralInputs,
      sampleCount: 500,
      seed: 20260504,
    },
    { loadCoefficientDraws: async () => generalCoefficientDraws }
  )

  assert.equal(response.status, "complete")
  assert.equal(response.cached, false)
  assert.equal(response.result.sampleCount, 500)
  assert.ok(response.result.median >= 0)
  assert.ok(response.result.median <= 1)
})

test("worker core runs the measured-SBP general E-Dispo branch with branch-specific draw data", async () => {
  clearSimulationCache()
  const response = await runCachedSimulation(
    {
      requestId: 31,
      modelId: GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID,
      inputs: validInputs,
      generalInputs: {
        ...validGeneralInputs,
        systolicBloodPressure: 92,
      },
      sampleCount: 500,
      seed: 20260504,
    },
    { loadCoefficientDraws: async () => generalMeasuredSbpCoefficientDraws }
  )

  assert.equal(response.status, "complete")
  assert.equal(response.cached, false)
  assert.equal(response.result.sampleCount, 500)
  assert.ok(response.result.median >= 0)
  assert.ok(response.result.median <= 1)
})

test("stale worker responses can be ignored by request id", async () => {
  const response = await runCachedSimulation(
    {
      requestId: 10,
      inputs: validInputs,
      sampleCount: 500,
    },
    { loadCoefficientDraws: async () => coefficientDraws }
  )

  assert.equal(isCurrentSimulationResponse(10, response), true)
  assert.equal(isCurrentSimulationResponse(11, response), false)
})

test("worker core returns a controlled error for malformed draw assets", async () => {
  clearSimulationCache()
  const response = await runCachedSimulation(
    {
      requestId: 20,
      inputs: validInputs,
      sampleCount: 500,
    },
    {
      loadCoefficientDraws: async () => {
        throw new CoefficientDrawAssetError(
          "schema_mismatch",
          "Malformed test asset."
        )
      },
    }
  )

  assert.equal(response.status, "error")
  assert.equal(response.errorCode, "coefficient_draw_asset_error")
  assert.equal(
    response.error,
    "The range view could not finish. Try running the model again."
  )
})
