import type { AgeBand, BinarySymptom, ModelInputs, PainSeverity } from "@/model/types";
import type { ReadinessState, SimulationCount } from "@/appTypes";
import { pas5Questions } from "@/model/aap3Acuity";

export const simulationCounts = [1000, 10000, 100000] as const;
export const painOptions: PainSeverity[] = ["mild", "moderate", "severe"];
export const binaryOptions: BinarySymptom[] = ["yes", "no"];

export function buildReadinessState(
  age: number,
  heartRateBpm: number | null,
): ReadinessState {
  if (deriveAgeBand(age) === null) {
    return { canRun: false, error: "Age must be in the 18-64 class range." };
  }

  if (heartRateBpm === null) {
    return {
      canRun: false,
      error: "observed HR is required for this v4 estimate.",
    };
  }

  return { canRun: true, error: null };
}

export function buildModelRunKey(
  inputs: ModelInputs,
  age: number,
  heartRateBpm: number | null,
  sampleCount: SimulationCount,
): string {
  return [
    age,
    heartRateBpm ?? "missing_hr",
    inputs.painSeverity,
    inputs.fever,
    inputs.vomiting,
    ...pas5Questions.map((question) => inputs.pas5[question.id]),
    sampleCount,
  ].join("|");
}

export function clampNumber(value: number, minimum: number, maximum: number): number {
  if (!Number.isFinite(value)) {
    return minimum;
  }

  return Math.max(minimum, Math.min(maximum, value));
}

export function deriveAgeBand(age: number): AgeBand | null {
  if (!Number.isFinite(age)) {
    return null;
  }

  if (age >= 18 && age <= 29) {
    return "18_29";
  }

  if (age >= 30 && age <= 44) {
    return "30_44";
  }

  if (age >= 45 && age <= 54) {
    return "45_54";
  }

  if (age >= 55 && age <= 64) {
    return "55_64";
  }

  return null;
}

export function parseHeartRate(value: string): number | null {
  if (value.trim().length === 0) {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function isPainSeverity(value: string): value is PainSeverity {
  return painOptions.includes(value as PainSeverity);
}

export function isBinarySymptom(value: string): value is BinarySymptom {
  return binaryOptions.includes(value as BinarySymptom);
}

export function parseSimulationCount(value: string): SimulationCount | null {
  const parsed = Number(value);
  return simulationCounts.includes(parsed as SimulationCount)
    ? (parsed as SimulationCount)
    : null;
}

export function formatCoefficient(value: number): string {
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(3)}`;
}
