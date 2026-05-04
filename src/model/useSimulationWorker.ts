import { useEffect, useMemo, useRef, useState } from "react"
import type { MutableRefObject } from "react"
import { GENERAL_E_DISPO_PUBLIC_MODEL_ID } from "@/data/generalEDispoModel"
import { modelMetadata } from "./modelParameters"
import {
  inputHashForSimulation,
  isCurrentSimulationResponse,
} from "./simulationProtocol"
import type { SimulationResponse } from "./simulationProtocol"
import type {
  GeneralModelInputs,
  ModelInputs,
  RunnableModelId,
  SimulationResult,
} from "./types"

export const simulationWorkerTimeoutMs = 60_000
export const simulationFailureMessage =
  "The range view could not finish. Try running the model again."

export type SimulationWorkerState = {
  status: "idle" | "running" | "complete" | "error"
  result: SimulationResult | null
  error: string | null
  cached: boolean
}

const initialState: SimulationWorkerState = {
  status: "idle",
  result: null,
  error: null,
  cached: false,
}

type SimulationWorkerHandle = {
  terminate: () => void
}

export function buildSimulationWorkerFailureState(): SimulationWorkerState {
  return {
    status: "error",
    result: null,
    error: simulationFailureMessage,
    cached: false,
  }
}

export function handleSimulationWorkerTimeout({
  activeRequestId,
  timedOutRequestId,
  worker,
  resetWorker,
}: {
  activeRequestId: number
  timedOutRequestId: number
  worker: SimulationWorkerHandle | null
  resetWorker: () => void
}): SimulationWorkerState | null {
  if (activeRequestId !== timedOutRequestId) {
    return null
  }

  worker?.terminate()
  resetWorker()
  return buildSimulationWorkerFailureState()
}

export function useSimulationWorker(
  inputs: ModelInputs,
  enabled: boolean,
  age = 42,
  heartRateBpm: number | null = 88,
  sampleCount = modelMetadata.sampleCount,
  modelId: RunnableModelId = "e-dispo-v4.1-pas5-high-acuity-surrogate",
  generalInputs?: GeneralModelInputs
): SimulationWorkerState {
  const simulationSeed =
    modelId === GENERAL_E_DISPO_PUBLIC_MODEL_ID ? 20260429 : modelMetadata.seed
  const [state, setState] = useState<SimulationWorkerState>(initialState)
  const workerRef = useRef<Worker | null>(null)
  const requestIdRef = useRef(0)
  const startedAtRef = useRef(0)
  const watchdogTimeoutRef = useRef<number | null>(null)
  const completionTimeoutRef = useRef<number | null>(null)
  const inputHash = useMemo(
    () =>
      inputHashForSimulation({
        modelId,
        inputs,
        generalInputs,
        age,
        heartRateBpm,
        sampleCount,
        seed: simulationSeed,
      }),
    [
      age,
      generalInputs,
      heartRateBpm,
      inputs,
      modelId,
      sampleCount,
      simulationSeed,
    ]
  )

  useEffect(() => {
    if (!enabled) {
      return
    }

    clearTimeoutRef(watchdogTimeoutRef)
    clearTimeoutRef(completionTimeoutRef)

    if (!workerRef.current) {
      workerRef.current = new Worker(
        new URL("../workers/simulationWorker.ts", import.meta.url),
        { type: "module" }
      )
    }

    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    startedAtRef.current = performance.now()
    watchdogTimeoutRef.current = window.setTimeout(() => {
      const timeoutState = handleSimulationWorkerTimeout({
        activeRequestId: requestIdRef.current,
        timedOutRequestId: requestId,
        worker: workerRef.current,
        resetWorker: () => {
          workerRef.current = null
        },
      })

      if (timeoutState) {
        clearTimeoutRef(completionTimeoutRef)
        setState(timeoutState)
      }
    }, simulationWorkerTimeoutMs)
    queueMicrotask(() => {
      setState(() => ({
        status: "running",
        result: null,
        error: null,
        cached: false,
      }))
    })

    workerRef.current.onmessage = (
      event: MessageEvent<SimulationResponse>
    ) => {
      const response = event.data
      if (!isCurrentSimulationResponse(requestIdRef.current, response)) {
        return
      }

      clearTimeoutRef(watchdogTimeoutRef)

      if (response.status === "error") {
        setState({
          status: "error",
          result: null,
          error: response.error,
          cached: false,
        })
        return
      }

      const applyCompleteState = () => {
        if (!isCurrentSimulationResponse(requestIdRef.current, response)) {
          return
        }

        setState({
          status: "complete",
          result: response.result,
          error: null,
          cached: response.cached,
        })
      }
      const remainingLoadingMs = Math.max(
        0,
        900 - (performance.now() - startedAtRef.current)
      )
      completionTimeoutRef.current = window.setTimeout(
        applyCompleteState,
        remainingLoadingMs
      )
    }

    workerRef.current.onerror = () => {
      if (requestIdRef.current !== requestId) {
        return
      }

      clearTimeoutRef(watchdogTimeoutRef)
      setState(buildSimulationWorkerFailureState())
    }

    workerRef.current.postMessage({
      requestId,
      modelId,
      inputs,
      generalInputs,
      age,
      heartRateBpm,
      sampleCount,
      seed: simulationSeed,
    })

    return () => {
      clearTimeoutRef(watchdogTimeoutRef)
      clearTimeoutRef(completionTimeoutRef)
    }
  }, [
    age,
    enabled,
    generalInputs,
    heartRateBpm,
    inputHash,
    inputs,
    modelId,
    sampleCount,
    simulationSeed,
  ])

  useEffect(() => {
    return () => {
      clearTimeoutRef(watchdogTimeoutRef)
      clearTimeoutRef(completionTimeoutRef)
      workerRef.current?.terminate()
    }
  }, [])

  return enabled ? state : initialState
}

function clearTimeoutRef(ref: MutableRefObject<number | null>) {
  if (ref.current === null) {
    return
  }

  window.clearTimeout(ref.current)
  ref.current = null
}
