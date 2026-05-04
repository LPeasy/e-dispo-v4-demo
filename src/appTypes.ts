import type {
  GeneralModelInputs,
  ModelInputs,
  PredictionResult,
  RunnableModelId,
} from "@/model/types";

export type Page = "landing" | "customer" | "explorer" | "use" | "results" | "docs";
export type SimulationCount = 1000 | 10000 | 100000;
export type ReadinessState = {
  canRun: boolean;
  error: string | null;
};
export type ModelRun = {
  key: string;
  modelId: RunnableModelId;
  age: number;
  heartRateBpm: number;
  generalInputs?: GeneralModelInputs;
  inputs: ModelInputs;
  prediction: PredictionResult;
  sampleCount: SimulationCount;
};
export type PageHeaderTone = "customer" | "reviewer";
