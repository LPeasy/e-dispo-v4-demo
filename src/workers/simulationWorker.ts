import { runCachedSimulation } from "@/model/simulationWorkerCore"
import type {
  SimulationRequest,
  SimulationResponse,
} from "@/model/simulationProtocol"

const ctx: Worker = self as unknown as Worker

ctx.onmessage = async (event: MessageEvent<SimulationRequest>) => {
  const response: SimulationResponse = await runCachedSimulation(event.data)
  ctx.postMessage(response)
}
