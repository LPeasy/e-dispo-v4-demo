import assert from "node:assert/strict"
import test from "node:test"

import {
  buildSimulationWorkerFailureState,
  handleSimulationWorkerTimeout,
  simulationFailureMessage,
  simulationWorkerTimeoutMs,
} from "./useSimulationWorker"

test("simulation worker timeout uses the generic failure state", () => {
  const state = buildSimulationWorkerFailureState()

  assert.equal(simulationWorkerTimeoutMs, 60_000)
  assert.equal(state.status, "error")
  assert.equal(state.result, null)
  assert.equal(state.error, simulationFailureMessage)
  assert.equal(state.cached, false)
})

test("simulation worker timeout terminates and resets the active worker", () => {
  let terminateCount = 0
  let resetCount = 0

  const state = handleSimulationWorkerTimeout({
    activeRequestId: 4,
    timedOutRequestId: 4,
    worker: {
      terminate: () => {
        terminateCount += 1
      },
    },
    resetWorker: () => {
      resetCount += 1
    },
  })

  assert.equal(state?.status, "error")
  assert.equal(state?.error, simulationFailureMessage)
  assert.equal(terminateCount, 1)
  assert.equal(resetCount, 1)
})

test("simulation worker timeout ignores stale requests", () => {
  let terminateCount = 0
  let resetCount = 0

  const state = handleSimulationWorkerTimeout({
    activeRequestId: 5,
    timedOutRequestId: 4,
    worker: {
      terminate: () => {
        terminateCount += 1
      },
    },
    resetWorker: () => {
      resetCount += 1
    },
  })

  assert.equal(state, null)
  assert.equal(terminateCount, 0)
  assert.equal(resetCount, 0)
})
