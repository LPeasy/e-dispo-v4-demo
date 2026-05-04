import { modelMetadata } from "./modelParameters"
import type {
  GeneralModelInputs,
  ModelInputs,
  RunnableModelId,
  SimulationResult,
} from "./types"

export type SimulationErrorCode =
  | "coefficient_draw_asset_error"
  | "simulation_runtime_error"

export type SimulationRequest = {
  requestId: number
  modelId?: RunnableModelId
  inputs: ModelInputs
  generalInputs?: GeneralModelInputs
  age?: number
  heartRateBpm?: number | null
  sampleCount?: number
  seed?: number
}

export type SimulationResponse =
  | {
      requestId: number
      inputHash: string
      status: "complete"
      result: SimulationResult
      cached: boolean
    }
  | {
      requestId: number
      inputHash: string
      status: "error"
      error: string
      errorCode: SimulationErrorCode
      cached: false
    }

export function inputHashForSimulation({
  modelId = "e-dispo-v4.1-pas5-high-acuity-surrogate",
  inputs,
  generalInputs,
  age = 42,
  heartRateBpm = 88,
  sampleCount = modelMetadata.sampleCount,
  seed = modelMetadata.seed,
}: Omit<SimulationRequest, "requestId">): string {
  return JSON.stringify({
    modelId,
    inputs,
    generalInputs,
    age,
    heartRateBpm,
    sampleCount,
    seed,
  })
}

export function isCurrentSimulationResponse(
  activeRequestId: number,
  response: SimulationResponse
): boolean {
  return response.requestId === activeRequestId
}
