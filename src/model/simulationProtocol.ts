import { modelMetadata } from "./modelParameters"
import type { ModelInputs, SimulationResult } from "./types"

export type SimulationErrorCode =
  | "coefficient_draw_asset_error"
  | "simulation_runtime_error"

export type SimulationRequest = {
  requestId: number
  inputs: ModelInputs
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
  inputs,
  age = 42,
  heartRateBpm = 88,
  sampleCount = modelMetadata.sampleCount,
  seed = modelMetadata.seed,
}: Omit<SimulationRequest, "requestId">): string {
  return JSON.stringify({
    inputs,
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
