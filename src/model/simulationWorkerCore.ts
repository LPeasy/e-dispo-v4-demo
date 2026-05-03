import { runLatinHypercubeSimulation } from "./latinHypercube"
import {
  CoefficientDrawAssetError,
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

export type CoefficientDrawLoader = () => Promise<
  PooledEmpiricalCoefficientDraw[]
>

export type RunCachedSimulationOptions = {
  loadCoefficientDraws?: CoefficientDrawLoader
}

export async function runCachedSimulation(
  request: SimulationRequest,
  options: RunCachedSimulationOptions = {}
): Promise<SimulationResponse> {
  const sampleCount = request.sampleCount ?? modelMetadata.sampleCount
  const seed = request.seed ?? modelMetadata.seed
  const inputHash = inputHashForSimulation({
    inputs: request.inputs,
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
    const coefficientDraws = await (
      options.loadCoefficientDraws ?? loadPooledEmpiricalCoefficientDraws
    )()
    const result = runLatinHypercubeSimulation(
      request.inputs,
      sampleCount,
      seed,
      request.age,
      request.heartRateBpm === undefined ? 88 : request.heartRateBpm,
      coefficientDraws
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
