import type { LogisticTerm, ModelInputs } from "./types"

export type EvidenceTier =
  | "dataset_derived"
  | "literature_prior"
  | "prototype_assumption"
  | "unsupported"

export type EffectDistribution = {
  family: "normal"
  mean: number
  standardError: number
  evidenceTier: EvidenceTier
  sourceIds: string[]
}

export type DoseResponse =
  | { kind: "nominal"; reference: string; levels: string[] }
  | {
      kind: "ordinal"
      reference: string
      levels: string[]
      monotonic: "increasing" | "decreasing" | "none"
    }
  | { kind: "binary"; reference: string; positive: string; unknown?: string }

export type ParameterDefinition = {
  id: keyof ModelInputs
  label: string
  intendedMeaning: string
  userControl: "derived" | "select" | "segmented" | "toggle"
  doseResponse: DoseResponse
  distributions: Record<string, EffectDistribution>
  documentationAnchor: string
  limitations: string
  readyForEmpiricalUse: boolean
}

export const parameterOrder: Array<keyof ModelInputs> = [
  "ageBand",
  "broadPainRegion",
  "painSeverity",
  "onsetDurationCategory",
  "constantVsIntermittent",
  "vomiting",
  "fever",
]

export const parameterValueLabels: Record<string, string> = {
  "18_29": "18-29",
  "30_44": "30-44",
  "45_54": "45-54",
  "55_64": "55-64",
  upper_abdomen: "Upper abdomen",
  lower_abdomen: "Lower abdomen",
  diffuse_or_hard_to_pinpoint: "Diffuse or hard to pinpoint",
  mild: "Mild",
  moderate: "Moderate",
  severe: "Severe",
  sudden_less_than_24_hours: "Sudden, <24 hours",
  gradual_less_than_24_hours: "Gradual, <24 hours",
  one_to_seven_days: "1-7 days",
  more_than_seven_days: ">7 days",
  constant: "Constant",
  intermittent: "Intermittent",
  yes: "Yes",
  no: "No",
  unknown: "Unknown",
}

export const parameterRegistry: Record<keyof ModelInputs, ParameterDefinition> = {
  ageBand: {
    id: "ageBand",
    label: "Age band",
    intendedMeaning: "Age group within the locked adult male 18-64 cohort.",
    userControl: "derived",
    doseResponse: {
      kind: "ordinal",
      reference: "30_44",
      levels: ["18_29", "30_44", "45_54", "55_64"],
      monotonic: "increasing",
    },
    distributions: {
      "18_29": normalEffect(-0.22, 0.18, ["cdc-nhamcs", "nhamcs-2022-ed"]),
      "30_44": normalEffect(0, 0, ["cdc-nhamcs", "nhamcs-2022-ed"]),
      "45_54": normalEffect(0.24, 0.17, ["cdc-nhamcs", "nhamcs-2022-ed"]),
      "55_64": normalEffect(0.48, 0.18, ["cdc-nhamcs", "nhamcs-2022-ed"]),
    },
    documentationAnchor: "parameter-age-band",
    limitations:
      "Currently prototype coefficients; empirical support is expected to be direct because age is available in candidate datasets.",
    readyForEmpiricalUse: true,
  },
  broadPainRegion: {
    id: "broadPainRegion",
    label: "Broad pain region",
    intendedMeaning: "Patient-reported broad abdominal pain location.",
    userControl: "segmented",
    doseResponse: {
      kind: "nominal",
      reference: "diffuse_or_hard_to_pinpoint",
      levels: ["upper_abdomen", "lower_abdomen", "diffuse_or_hard_to_pinpoint"],
    },
    distributions: {
      upper_abdomen: normalEffect(0.18, 0.16, ["mimic-iv-ed", "nhamcs-2022-ed"]),
      lower_abdomen: normalEffect(0.12, 0.16, ["mimic-iv-ed", "nhamcs-2022-ed"]),
      diffuse_or_hard_to_pinpoint: normalEffect(0, 0, [
        "mimic-iv-ed",
        "nhamcs-2022-ed",
      ]),
    },
    documentationAnchor: "parameter-pain-region",
    limitations:
      "Public datasets may only support pain region through reason-for-visit, diagnosis, or text proxies.",
    readyForEmpiricalUse: false,
  },
  painSeverity: {
    id: "painSeverity",
    label: "Pain severity",
    intendedMeaning: "Patient-reported pain intensity grouped for the class model.",
    userControl: "segmented",
    doseResponse: {
      kind: "nominal",
      reference: "moderate",
      levels: ["mild", "moderate", "severe"],
    },
    distributions: {
      mild: normalEffect(-0.45, 0.18, ["nhamcs-2022-ed", "mimic-iv-ed"]),
      moderate: normalEffect(0, 0, ["nhamcs-2022-ed", "mimic-iv-ed"]),
      severe: normalEffect(0.68, 0.2, ["nhamcs-2022-ed", "mimic-iv-ed"]),
    },
    documentationAnchor: "parameter-pain-severity",
    limitations:
      "Pain scale availability and missingness must be documented before empirical claims.",
    readyForEmpiricalUse: true,
  },
  onsetDurationCategory: {
    id: "onsetDurationCategory",
    label: "Onset/duration",
    intendedMeaning: "Coarse timing of the abdominal pain episode.",
    userControl: "select",
    doseResponse: {
      kind: "nominal",
      reference: "one_to_seven_days",
      levels: [
        "sudden_less_than_24_hours",
        "gradual_less_than_24_hours",
        "one_to_seven_days",
        "more_than_seven_days",
        "unknown",
      ],
    },
    distributions: {
      sudden_less_than_24_hours: normalEffect(0.4, 0.2, ["mimic-iv-ed"]),
      gradual_less_than_24_hours: normalEffect(0.14, 0.18, ["mimic-iv-ed"]),
      one_to_seven_days: normalEffect(0, 0, ["mimic-iv-ed"]),
      more_than_seven_days: normalEffect(-0.18, 0.2, ["mimic-iv-ed"]),
      unknown: normalEffect(0.22, 0.24, ["mimic-iv-ed"]),
    },
    documentationAnchor: "parameter-onset-duration",
    limitations:
      "Timing is weak or unavailable in public-use datasets and may require text extraction in richer data.",
    readyForEmpiricalUse: false,
  },
  constantVsIntermittent: {
    id: "constantVsIntermittent",
    label: "Pain pattern",
    intendedMeaning: "Whether the pain is described as constant or intermittent.",
    userControl: "segmented",
    doseResponse: {
      kind: "nominal",
      reference: "intermittent",
      levels: ["constant", "intermittent", "unknown"],
    },
    distributions: {
      constant: normalEffect(0.3, 0.16, ["mimic-iv-ed"]),
      intermittent: normalEffect(0, 0, ["mimic-iv-ed"]),
      unknown: normalEffect(0.12, 0.2, ["mimic-iv-ed"]),
    },
    documentationAnchor: "parameter-pain-pattern",
    limitations:
      "Pattern is generally unsupported in public structured ED datasets and may require chart text proxies.",
    readyForEmpiricalUse: false,
  },
  vomiting: {
    id: "vomiting",
    label: "Vomiting",
    intendedMeaning: "Associated vomiting symptom status.",
    userControl: "toggle",
    doseResponse: {
      kind: "binary",
      reference: "no",
      positive: "yes",
      unknown: "unknown",
    },
    distributions: {
      yes: normalEffect(0.42, 0.18, ["nhamcs-2022-ed", "mimic-iv-ed"]),
      no: normalEffect(0, 0, ["nhamcs-2022-ed", "mimic-iv-ed"]),
      unknown: normalEffect(0.14, 0.22, ["nhamcs-2022-ed", "mimic-iv-ed"]),
    },
    documentationAnchor: "parameter-vomiting",
    limitations:
      "Vomiting may be present only as a reason-for-visit, diagnosis, or text proxy depending on dataset.",
    readyForEmpiricalUse: false,
  },
  fever: {
    id: "fever",
    label: "Fever",
    intendedMeaning: "Associated fever or fever-proxy status.",
    userControl: "toggle",
    doseResponse: {
      kind: "binary",
      reference: "no",
      positive: "yes",
      unknown: "unknown",
    },
    distributions: {
      yes: normalEffect(0.5, 0.2, ["nhamcs-2022-ed", "mimic-iv-ed"]),
      no: normalEffect(0, 0, ["nhamcs-2022-ed", "mimic-iv-ed"]),
      unknown: normalEffect(0.16, 0.22, ["nhamcs-2022-ed", "mimic-iv-ed"]),
    },
    documentationAnchor: "parameter-fever",
    limitations:
      "Fever may need a temperature or symptom-code proxy and requires dataset-specific recoding.",
    readyForEmpiricalUse: false,
  },
}

export function allParameterDefinitions(): ParameterDefinition[] {
  return parameterOrder.map((id) => parameterRegistry[id])
}

export function parameterTermRecords<T extends keyof ModelInputs>(
  id: T
): Record<ModelInputs[T], LogisticTerm> {
  const definition = parameterRegistry[id]

  return Object.fromEntries(
    Object.entries(definition.distributions).map(([value, distribution]) => [
      value,
      {
        key: `${id}.${value}`,
        label: parameterValueLabels[value] ?? value,
        mean: distribution.mean,
        standardError: distribution.standardError,
      },
    ])
  ) as Record<ModelInputs[T], LogisticTerm>
}

export function activeParameterTerms(inputs: ModelInputs): LogisticTerm[] {
  return parameterOrder.map((id) => {
    const value = inputs[id]
    const distribution = parameterRegistry[id].distributions[String(value)]

    return {
      key: `${id}.${value}`,
      label: parameterValueLabels[String(value)] ?? String(value),
      mean: distribution.mean,
      standardError: distribution.standardError,
    }
  })
}

export function evidenceTierLabel(tier: EvidenceTier): string {
  const labels: Record<EvidenceTier, string> = {
    dataset_derived: "Dataset-derived",
    literature_prior: "Literature prior",
    prototype_assumption: "Prototype assumption",
    unsupported: "Unsupported",
  }

  return labels[tier]
}

export function describeDoseResponse(response: DoseResponse): string {
  if (response.kind === "binary") {
    return `Binary: ${response.positive} vs ${response.reference}${
      response.unknown ? `, with ${response.unknown}` : ""
    }`
  }

  if (response.kind === "ordinal") {
    return `Ordinal ${response.monotonic}: ${response.levels.join(" -> ")}`
  }

  return `Nominal: ${response.levels.join(", ")}`
}

function normalEffect(
  mean: number,
  standardError: number,
  sourceIds: string[],
  evidenceTier: EvidenceTier = "prototype_assumption"
): EffectDistribution {
  return {
    family: "normal",
    mean,
    standardError,
    evidenceTier,
    sourceIds,
  }
}
