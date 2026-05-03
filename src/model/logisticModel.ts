import { intercept } from "./modelParameters"
import { activeParameterTerms } from "./parameterRegistry"
import type { LogisticTerm, ModelInputs, PredictionResult } from "./types"

export function logistic(value: number): number {
  return 1 / (1 + Math.exp(-value))
}

export function activeTermsForInputs(inputs: ModelInputs): LogisticTerm[] {
  return [intercept, ...activeParameterTerms(inputs)]
}

export function predictDisposition(inputs: ModelInputs): PredictionResult {
  const activeTerms = activeTermsForInputs(inputs)
  const linearPredictor = activeTerms.reduce((sum, term) => sum + term.mean, 0)
  const probabilityAdmit = clampProbability(logistic(linearPredictor))

  return {
    probabilityAdmit,
    probabilityTreatAndRelease: clampProbability(1 - probabilityAdmit),
    linearPredictor,
    activeTerms,
  }
}

export function clampProbability(value: number): number {
  if (Number.isNaN(value)) {
    return 0
  }

  return Math.min(1, Math.max(0, value))
}

export function formatPercent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`
}
