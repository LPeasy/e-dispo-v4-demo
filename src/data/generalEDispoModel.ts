import type {
  GeneralAcuityCode,
  GeneralArrivalTransferContext,
  GeneralSex,
  RunnableModelId,
} from "@/model/types"

export const GENERAL_E_DISPO_SOURCE_MODEL_ID =
  "general-E-Dispo-model-v1-plus-sex" as const
export const GENERAL_E_DISPO_PUBLIC_MODEL_ID =
  "general-E-Dispo-model-v1-sex-adjusted" as const satisfies RunnableModelId

export type GeneralCoefficientKey =
  | "intercept"
  | "age_centered_40"
  | "sex_2"
  | `acuity_code_${GeneralAcuityCode}`
  | `arrival_transfer_context_${GeneralArrivalTransferContext}`
  | "fever_or_temp"
  | "tachycardia_burden"
  | "hypotension_burden"

export type GeneralModelCoefficient = {
  key: GeneralCoefficientKey
  term: string
  level: string
  label: string
  beta: number
  standardError: number
}

export type GeneralModelOption<T extends string> = {
  value: T
  label: string
  description: string
}

const generalLimitation =
  "Dataset-derived from pooled NHAMCS 2018-2022 all-sex/all-age non-trauma source-scope sensitivity model for educational use only; not clinical decision support, not external validation, and not transportability evidence."

export const generalSexOptions: Array<GeneralModelOption<GeneralSex>> = [
  {
    value: "1",
    label: "Male (NHAMCS code 1)",
    description: "Reference category in the fitted sensitivity artifact.",
  },
  {
    value: "2",
    label: "Female (NHAMCS code 2)",
    description: "Activates the prespecified sex main-effect term.",
  },
]

export const generalAcuityOptions: Array<
  GeneralModelOption<GeneralAcuityCode>
> = [
  {
    value: "immediate",
    label: "Immediate",
    description: "NHAMCS IMMEDR immediate level.",
  },
  {
    value: "emergent",
    label: "Emergent",
    description: "NHAMCS IMMEDR emergent level.",
  },
  {
    value: "urgent",
    label: "Urgent",
    description: "Reference category in the fitted model.",
  },
  {
    value: "semi_urgent",
    label: "Semi-urgent",
    description: "NHAMCS IMMEDR semi-urgent level.",
  },
  {
    value: "nonurgent",
    label: "Nonurgent",
    description: "NHAMCS IMMEDR nonurgent level.",
  },
  {
    value: "no_triage_esa_conducts_triage",
    label: "No triage, ESA conducts triage",
    description: "Explicit NHAMCS acuity level; not silently missing.",
  },
  {
    value: "no_nursing_triage_esa",
    label: "No nursing triage or ESA",
    description: "Explicit NHAMCS acuity level; not silently missing.",
  },
  {
    value: "unknown",
    label: "Unknown acuity",
    description: "Explicit unknown level carried from the source cohort.",
  },
  {
    value: "blank",
    label: "Blank acuity",
    description: "Explicit blank level carried from the source cohort.",
  },
]

export const generalArrivalTransferOptions: Array<
  GeneralModelOption<GeneralArrivalTransferContext>
> = [
  {
    value: "no_not_transferred_from_hospital_or_urgent_care",
    label: "No transfer-in context",
    description: "Reference category in the fitted model.",
  },
  {
    value: "yes_transferred_from_hospital_or_urgent_care",
    label: "Transferred from hospital or urgent care",
    description: "NHAMCS AMBTRANSFER positive context.",
  },
  {
    value: "not_applicable",
    label: "Not applicable",
    description: "Explicit source level; not silently missing.",
  },
  {
    value: "unknown",
    label: "Unknown transfer context",
    description: "Explicit unknown level carried from the source cohort.",
  },
  {
    value: "blank",
    label: "Blank transfer context",
    description: "Explicit blank level carried from the source cohort.",
  },
]

export const generalEDispoModel = {
  allowedUse: "educational only; not clinical decision support",
  apparentPerformance: {
    auroc: 0.818263165851652,
    brierScore: 0.104635316684325,
    calibrationInTheLarge: -0.00184070381137826,
    calibrationSlope: 0.986112905235899,
    observedPrevalence: 0.159202726162058,
    meanPredicted: 0.159202726171801,
  },
  cohortCounts: {
    dataset: "NHAMCS_2018_2022_POOLED",
    sourceScope: "full_source_nontrauma",
    endpointRows: 50070,
    admissionEvents: 7447,
    completeCaseRows: 42300,
    completeCaseAdmissionEvents: 6488,
  },
  coefficients: [
    {
      key: "intercept",
      term: "intercept",
      level: "",
      label: "Intercept",
      beta: -1.63407360872993,
      standardError: 0.0790819151851508,
    },
    {
      key: "age_centered_40",
      term: "age_centered_40",
      level: "per_1_year_centered_at_40",
      label: "Age, centered at 40",
      beta: 0.0348494496590697,
      standardError: 0.00156041212334405,
    },
    {
      key: "sex_2",
      term: "sex",
      level: "2",
      label: "Sex: female code 2 vs male code 1",
      beta: 0.204515775369273,
      standardError: 0.0410061550205075,
    },
    {
      key: "acuity_code_blank",
      term: "acuity_code",
      level: "blank",
      label: "Acuity: blank",
      beta: 0.215507040625597,
      standardError: 0.256354939261223,
    },
    {
      key: "acuity_code_unknown",
      term: "acuity_code",
      level: "unknown",
      label: "Acuity: unknown",
      beta: 0.18264735998137,
      standardError: 0.113155388217957,
    },
    {
      key: "acuity_code_no_triage_esa_conducts_triage",
      term: "acuity_code",
      level: "no_triage_esa_conducts_triage",
      label: "Acuity: no triage, ESA conducts triage",
      beta: 0.326414958813862,
      standardError: 0.248475564940765,
    },
    {
      key: "acuity_code_immediate",
      term: "acuity_code",
      level: "immediate",
      label: "Acuity: immediate",
      beta: 1.120799323406,
      standardError: 0.424115094178656,
    },
    {
      key: "acuity_code_emergent",
      term: "acuity_code",
      level: "emergent",
      label: "Acuity: emergent",
      beta: 1.12126625563577,
      standardError: 0.0677781784084267,
    },
    {
      key: "acuity_code_semi_urgent",
      term: "acuity_code",
      level: "semi_urgent",
      label: "Acuity: semi-urgent",
      beta: -1.6108261436946,
      standardError: 0.158125361977884,
    },
    {
      key: "acuity_code_nonurgent",
      term: "acuity_code",
      level: "nonurgent",
      label: "Acuity: nonurgent",
      beta: -0.564515347842142,
      standardError: 0.329639044926522,
    },
    {
      key: "acuity_code_no_nursing_triage_esa",
      term: "acuity_code",
      level: "no_nursing_triage_esa",
      label: "Acuity: no nursing triage or ESA",
      beta: -0.125933844733567,
      standardError: 0.166563666864056,
    },
    {
      key: "arrival_transfer_context_blank",
      term: "arrival_transfer_context",
      level: "blank",
      label: "Arrival context: blank",
      beta: -0.250310424370882,
      standardError: 0.167458142406169,
    },
    {
      key: "arrival_transfer_context_unknown",
      term: "arrival_transfer_context",
      level: "unknown",
      label: "Arrival context: unknown",
      beta: 0.102316070460079,
      standardError: 0.149918909680129,
    },
    {
      key: "arrival_transfer_context_not_applicable",
      term: "arrival_transfer_context",
      level: "not_applicable",
      label: "Arrival context: not applicable",
      beta: -0.940177426001096,
      standardError: 0.0558006651786644,
    },
    {
      key: "arrival_transfer_context_yes_transferred_from_hospital_or_urgent_care",
      term: "arrival_transfer_context",
      level: "yes_transferred_from_hospital_or_urgent_care",
      label: "Arrival context: transferred from hospital or urgent care",
      beta: 1.57019283241495,
      standardError: 0.222134865057962,
    },
    {
      key: "fever_or_temp",
      term: "fever_or_temp",
      level: "1",
      label: "Fever or temperature",
      beta: 0.399404017910802,
      standardError: 0.113293823131377,
    },
    {
      key: "tachycardia_burden",
      term: "tachycardia_burden",
      level: "per_10_bpm_over_100",
      label: "Tachycardia burden",
      beta: 0.262091867980015,
      standardError: 0.0237030810350694,
    },
    {
      key: "hypotension_burden",
      term: "hypotension_burden",
      level: "per_10_mmhg_below_100",
      label: "Hypotension burden",
      beta: 0.752126485698012,
      standardError: 0.0888304600616499,
    },
  ] satisfies GeneralModelCoefficient[],
  formula:
    "admit ~ age_centered_40 + sex + acuity_code + arrival_transfer_context + fever_or_temp + tachycardia_burden + hypotension_burden",
  limitation: generalLimitation,
  modelId: GENERAL_E_DISPO_PUBLIC_MODEL_ID,
  sourceArtifactId: GENERAL_E_DISPO_SOURCE_MODEL_ID,
} as const

export function generalCoefficientByKey(
  key: GeneralCoefficientKey
): GeneralModelCoefficient {
  const coefficient = generalEDispoModel.coefficients.find(
    (candidate) => candidate.key === key
  )

  if (!coefficient) {
    throw new Error(`Missing general E-Dispo coefficient: ${key}`)
  }

  return coefficient
}

export function generalOptionLabel<T extends string>(
  options: Array<GeneralModelOption<T>>,
  value: T
): string {
  return options.find((option) => option.value === value)?.label ?? value
}
