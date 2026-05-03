import type {
  AgeBand,
  BinarySymptom,
  LogisticTerm,
  OnsetDuration,
  PainPattern,
  PainRegion,
  PainSeverity,
} from "./types"
import { parameterTermRecords } from "./parameterRegistry"

export const modelMetadata = {
  name: "e-dispo-v4.0 pooled empirical model educational demo",
  endpoint:
    "P(admit | endpoint-refined binary cohort, reduced empirical inputs)",
  endpointDefinition:
    "admit means same-hospital hospitalization/admission, including observation -> hospitalized when documented.",
  sampleCount: 100000,
  seed: 20260428,
  coefficientStatus:
    "Dataset-derived e-dispo-v4.0 pooled NHAMCS 2018-2022 reduced empirical coefficients for educational use only; not clinical decision support.",
}

export const intercept: LogisticTerm = {
  key: "intercept",
  label: "Intercept",
  mean: -1.52,
  standardError: 0.2,
}

export const ageBandTerms: Record<AgeBand, LogisticTerm> = {
  ...parameterTermRecords("ageBand"),
}

export const painRegionTerms: Record<PainRegion, LogisticTerm> = {
  ...parameterTermRecords("broadPainRegion"),
}

export const severityTerms: Record<PainSeverity, LogisticTerm> = {
  ...parameterTermRecords("painSeverity"),
}

export const onsetTerms: Record<OnsetDuration, LogisticTerm> = {
  ...parameterTermRecords("onsetDurationCategory"),
}

export const patternTerms: Record<PainPattern, LogisticTerm> = {
  ...parameterTermRecords("constantVsIntermittent"),
}

export const vomitingTerms: Record<BinarySymptom, LogisticTerm> = {
  ...parameterTermRecords("vomiting"),
}

export const feverTerms: Record<BinarySymptom, LogisticTerm> = {
  ...parameterTermRecords("fever"),
}
