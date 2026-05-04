import { runLatinHypercubeSimulation } from "./latinHypercube"
import {
  CoefficientDrawAssetError,
  loadCoefficientDrawsForModel,
  loadPooledEmpiricalCoefficientDraws,
} from "@/data/pooledEmpiricalCoefficientDraws"
import type { PooledEmpiricalCoefficientDraw } from "@/data/pooledEmpiricalCoefficientDraws"
import { modelMetadata } from "./modelParameters"
import {
  inputHashForSimulation,
  type SimulationRequest,
  type SimulationResponse,
} from "./simulationProtocol"
import type { SimulationResult } from "./types"

const simulationCache = new Map<string, SimulationResult>()
const simulationFailureMessage =
  "The range view could not finish. Try running the model again."

export type CoefficientDrawLoader = (
  modelId: NonNullable<SimulationRequest["modelId"]>
) => Promise<PooledEmpiricalCoefficientDraw[]>

export type RunCachedSimulationOptions = {
  loadCoefficientDraws?: CoefficientDrawLoader
}

export async function runCachedSimulation(
  request: SimulationRequest,
  options: RunCachedSimulationOptions = {}
): Promise<SimulationResponse> {
  const sampleCount = request.sampleCount ?? modelMetadata.sampleCount
  const seed = request.seed ?? modelMetadata.seed
  const modelId =
    request.modelId ?? "e-dispo-v4.1-pas5-high-acuity-surrogate"
  const inputHash = inputHashForSimulation({
    modelId,
    inputs: request.inputs,
    generalInputs: request.generalInputs,
    age: request.age,
    heartRateBpm: request.heartRateBpm,
    sampleCount,
    seed,
  })

  const cachedResult = simulationCache.get(inputHash)
  if (cachedResult) {
    return {
      requestId: request.requestId,
      inputHash,
      status: "complete",
      result: cachedResult,
      cached: true,
    }
  }

  try {
    const coefficientDraws =
      options.loadCoefficientDraws !== undefined
        ? await options.loadCoefficientDraws(modelId)
        : modelId === "e-dispo-v4.1-pas5-high-acuity-surrogate"
          ? await loadPooledEmpiricalCoefficientDraws()
          : await loadCoefficientDrawsForModel(modelId)
    const result = runLatinHypercubeSimulation(
      request.inputs,
      sampleCount,
      seed,
      request.age,
      request.heartRateBpm === undefined ? 88 : request.heartRateBpm,
      coefficientDraws,
      {
        modelId,
        generalInputs: request.generalInputs,
      }
    )
    simulationCache.set(inputHash, result)

    return {
      requestId: request.requestId,
      inputHash,
      status: "complete",
      result,
      cached: false,
    }
  } catch (error) {
    return {
      requestId: request.requestId,
      inputHash,
      status: "error",
      error: simulationFailureMessage,
      errorCode:
        error instanceof CoefficientDrawAssetError
          ? "coefficient_draw_asset_error"
          : "simulation_runtime_error",
      cached: false,
    }
  }
}

export function clearSimulationCache() {
  simulationCache.clear()
}
