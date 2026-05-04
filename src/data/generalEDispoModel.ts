import type {
  GeneralModelInputs,
  GeneralSex,
  RunnableModelId,
} from "@/model/types"

export const GENERAL_E_DISPO_HOME_MODEL_ID =
  "general-E-Dispo-home-v1" as const satisfies RunnableModelId
export const GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID =
  "general-E-Dispo-home-v1-measured-sbp" as const satisfies RunnableModelId
export const GENERAL_E_DISPO_SOURCE_MODEL_ID =
  "general-E-Dispo-model-v1-plus-sex" as const
export const GENERAL_E_DISPO_PUBLIC_MODEL_ID = GENERAL_E_DISPO_HOME_MODEL_ID

export type GeneralHomeModelId =
  | typeof GENERAL_E_DISPO_HOME_MODEL_ID
  | typeof GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID

export type GeneralCoefficientKey =
  | "intercept"
  | "age_centered_40"
  | "sex_2"
  | "high_acuity_proxy"
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

type GeneralModelArtifact = {
  allowedUse: string
  apparentPerformance: {
    auroc: number
    brierScore: number
    calibrationInTheLarge: number
    calibrationSlope: number
    observedPrevalence: number
    meanPredicted: number
  }
  cohortCounts: {
    dataset: string
    sourceScope: string
    endpointRows: number
    admissionEvents: number
    completeCaseRows: number
    completeCaseAdmissionEvents: number
  }
  coefficients: GeneralModelCoefficient[]
  formula: string
  limitation: string
  modelId: GeneralHomeModelId
  sourceArtifactId: string
}

const generalHomeLimitation =
  "Dataset-derived from pooled NHAMCS 2018-2022 all-sex/all-age non-trauma home-facing educational model. PAS-5 high_acuity_proxy is bridged through NHAMCS IMMEDR surrogate evidence; not clinical decision support, not medical advice, not external validation, and not transportability evidence."

const generalMeasuredSbpLimitation =
  "Dataset-derived from pooled NHAMCS 2018-2022 all-sex/all-age non-trauma home-facing measured-SBP branch. PAS-5 high_acuity_proxy is bridged through NHAMCS IMMEDR surrogate evidence; SBP must be measured, not guessed; not clinical decision support, not medical advice, not external validation, and not transportability evidence."

export const generalSexOptions: Array<GeneralModelOption<GeneralSex>> = [
  {
    value: "1",
    label: "Male (NHAMCS code 1)",
    description: "Reference category in the fitted home-facing artifacts.",
  },
  {
    value: "2",
    label: "Female (NHAMCS code 2)",
    description: "Activates the prespecified sex main-effect term.",
  },
]

const sharedHomeCoefficients = [
  {
    key: "age_centered_40",
    term: "age_centered_40",
    level: "per_1_year_centered_at_40",
    label: "Age, centered at 40",
    beta: 0.0416505275512932,
    standardError: 0.0020308485670884,
  },
  {
    key: "sex_2",
    term: "sex",
    level: "2",
    label: "Sex: female code 2 vs male code 1",
    beta: 0.233521215462827,
    standardError: 0.0469650450669674,
  },
  {
    key: "high_acuity_proxy",
    term: "high_acuity_proxy",
    level: "1",
    label: "PAS-5 high-acuity proxy: A1/A2",
    beta: 1.51708422536487,
    standardError: 0.0816752390047766,
  },
  {
    key: "fever_or_temp",
    term: "fever_or_temp",
    level: "1",
    label: "Fever or temperature",
    beta: 0.185288854629282,
    standardError: 0.127490645891925,
  },
  {
    key: "tachycardia_burden",
    term: "tachycardia_burden",
    level: "per_10_bpm_over_100",
    label: "Tachycardia burden",
    beta: 0.2479901004269,
    standardError: 0.0205800313566031,
  },
] satisfies GeneralModelCoefficient[]

const measuredSbpCoefficients = [
  {
    key: "age_centered_40",
    term: "age_centered_40",
    level: "per_1_year_centered_at_40",
    label: "Age, centered at 40",
    beta: 0.0411245867493699,
    standardError: 0.0019587497244047,
  },
  {
    key: "sex_2",
    term: "sex",
    level: "2",
    label: "Sex: female code 2 vs male code 1",
    beta: 0.240566702816413,
    standardError: 0.0477114346087271,
  },
  {
    key: "high_acuity_proxy",
    term: "high_acuity_proxy",
    level: "1",
    label: "PAS-5 high-acuity proxy: A1/A2",
    beta: 1.44963222156645,
    standardError: 0.0801715289945278,
  },
  {
    key: "fever_or_temp",
    term: "fever_or_temp",
    level: "1",
    label: "Fever or temperature",
    beta: 0.318480099330423,
    standardError: 0.13071579087381,
  },
  {
    key: "tachycardia_burden",
    term: "tachycardia_burden",
    level: "per_10_bpm_over_100",
    label: "Tachycardia burden",
    beta: 0.285850116371489,
    standardError: 0.0280950733708761,
  },
  {
    key: "hypotension_burden",
    term: "hypotension_burden",
    level: "per_10_mmhg_below_100",
    label: "Hypotension burden",
    beta: 0.800360248682152,
    standardError: 0.113154139217707,
  },
] satisfies GeneralModelCoefficient[]

export const generalEDispoHomeModel = {
  allowedUse: "educational only; not clinical decision support",
  apparentPerformance: {
    auroc: 0.811803094666438,
    brierScore: 0.101883434958145,
    calibrationInTheLarge: -2.38065838756795e-10,
    calibrationSlope: 1.00000000017588,
    observedPrevalence: 0.149017386059159,
    meanPredicted: 0.149017386083174,
  },
  cohortCounts: {
    dataset: "NHAMCS_2018_2022_POOLED",
    sourceScope: "full_source_nontrauma_home_facing",
    endpointRows: 50070,
    admissionEvents: 7447,
    completeCaseRows: 32681,
    completeCaseAdmissionEvents: 4702,
  },
  coefficients: [
    {
      key: "intercept",
      term: "intercept",
      level: "",
      label: "Intercept",
      beta: -2.69591092938617,
      standardError: 0.068182297807492,
    },
    ...sharedHomeCoefficients,
  ] satisfies GeneralModelCoefficient[],
  formula:
    "admit ~ age_centered_40 + sex + high_acuity_proxy + fever_or_temp + tachycardia_burden",
  limitation: generalHomeLimitation,
  modelId: GENERAL_E_DISPO_HOME_MODEL_ID,
  sourceArtifactId: GENERAL_E_DISPO_HOME_MODEL_ID,
} as const satisfies GeneralModelArtifact

export const generalEDispoMeasuredSbpModel = {
  allowedUse: "educational only; not clinical decision support",
  apparentPerformance: {
    auroc: 0.807019870941267,
    brierScore: 0.107047330383386,
    calibrationInTheLarge: 7.52319879291264e-9,
    calibrationSlope: 1.00000000003979,
    observedPrevalence: 0.158758210128035,
    meanPredicted: 0.158758210133503,
  },
  cohortCounts: {
    dataset: "NHAMCS_2018_2022_POOLED",
    sourceScope: "full_source_nontrauma_home_facing",
    endpointRows: 50070,
    admissionEvents: 7447,
    completeCaseRows: 29761,
    completeCaseAdmissionEvents: 4581,
  },
  coefficients: [
    {
      key: "intercept",
      term: "intercept",
      level: "",
      label: "Intercept",
      beta: -2.70964365476787,
      standardError: 0.0689692379330426,
    },
    ...measuredSbpCoefficients,
  ] satisfies GeneralModelCoefficient[],
  formula:
    "admit ~ age_centered_40 + sex + high_acuity_proxy + fever_or_temp + tachycardia_burden + hypotension_burden",
  limitation: generalMeasuredSbpLimitation,
  modelId: GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID,
  sourceArtifactId: GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID,
} as const satisfies GeneralModelArtifact

export const generalEDispoModels = {
  [GENERAL_E_DISPO_HOME_MODEL_ID]: generalEDispoHomeModel,
  [GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID]: generalEDispoMeasuredSbpModel,
} as const

export const generalEDispoModel = generalEDispoHomeModel

export function generalModelIdForInputs(
  inputs: GeneralModelInputs
): GeneralHomeModelId {
  return inputs.systolicBloodPressure === null
    ? GENERAL_E_DISPO_HOME_MODEL_ID
    : GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID
}

export function generalModelForInputs(
  inputs: GeneralModelInputs
): GeneralModelArtifact {
  return generalEDispoModels[generalModelIdForInputs(inputs)]
}

export function generalModelById(
  modelId: GeneralHomeModelId
): GeneralModelArtifact {
  return generalEDispoModels[modelId]
}

export function isGeneralEDispoModelId(
  modelId: RunnableModelId
): modelId is GeneralHomeModelId {
  return (
    modelId === GENERAL_E_DISPO_HOME_MODEL_ID ||
    modelId === GENERAL_E_DISPO_HOME_MEASURED_SBP_MODEL_ID
  )
}

export function generalCoefficientByKey(
  key: GeneralCoefficientKey,
  modelId: GeneralHomeModelId = GENERAL_E_DISPO_HOME_MODEL_ID
): GeneralModelCoefficient {
  const coefficient = generalEDispoModels[modelId].coefficients.find(
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
