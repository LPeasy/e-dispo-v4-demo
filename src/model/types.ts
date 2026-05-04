import type { Pas5Inputs } from "./aap3Acuity";

export type EndpointLabel = "admit" | "treat_and_release";
export type RecodingResult =
  | { status: "included"; label: EndpointLabel; reason: string }
  | { status: "excluded"; reason: string };

export type EndpointStatus =
  | "ADMIT"
  | "TREAT_AND_RELEASE"
  | "ACUTE_ESCALATION_POSITIVE"
  | "EXCLUDE_SENTINEL_DEATH"
  | "EXCLUDE_CONFLICT"
  | "EXCLUDE_TRANSFER_PRIMARY"
  | "EXCLUDE_NONROUTINE_EXIT"
  | "EXCLUDE_OBS_DISCHARGED_PRIMARY"
  | "EXCLUDE_OTHER_UNKNOWN";

export type EndpointRecodingRow = Record<string, unknown>;

export interface EndpointRecodingResult {
  endpointPrimary: EndpointStatus;
  endpointSensAEventualHome: EndpointStatus;
  endpointSensBAcuteEscalation: EndpointStatus;
  sentinelDeathFlag: boolean;
  reason: string;
}

export type AgeBand = "18_29" | "30_44" | "45_54" | "55_64";
export type PainRegion =
  | "upper_abdomen"
  | "lower_abdomen"
  | "diffuse_or_hard_to_pinpoint";
export type PainSeverity = "mild" | "moderate" | "severe";
export type OnsetDuration =
  | "sudden_less_than_24_hours"
  | "gradual_less_than_24_hours"
  | "one_to_seven_days"
  | "more_than_seven_days"
  | "unknown";
export type PainPattern = "constant" | "intermittent" | "unknown";
export type BinarySymptom = "yes" | "no" | "unknown";

export type RunnableModelId =
  | "e-dispo-v4.1-pas5-high-acuity-surrogate"
  | "general-E-Dispo-home-v1"
  | "general-E-Dispo-home-v1-measured-sbp";
export type GeneralSex = "1" | "2";

export interface GeneralModelInputs {
  age: number;
  sex: GeneralSex;
  pas5: Pas5Inputs;
  fever: Exclude<BinarySymptom, "unknown">;
  heartRateBpm: number | null;
  systolicBloodPressure: number | null;
}

export interface ModelInputs {
  ageBand: AgeBand;
  broadPainRegion: PainRegion;
  painSeverity: PainSeverity;
  onsetDurationCategory: OnsetDuration;
  constantVsIntermittent: PainPattern;
  vomiting: BinarySymptom;
  fever: BinarySymptom;
  pas5: Pas5Inputs;
}

export interface EligibilityState {
  alreadyInEd: boolean;
  age: number;
  sex: "male" | "female" | "other_or_unspecified";
  chiefComplaint: "abdominal_pain" | "other";
  traumaRelated: boolean;
  redFlagStatement: boolean;
}

export interface EligibilityResult {
  canProceed: boolean;
  title: string;
  reasons: string[];
}

export type FieldStatus =
  | "user_entered"
  | "llm_inferred"
  | "unknown"
  | "needs_confirmation";

export interface WorksheetField<T = string | number | boolean> {
  name: string;
  value: T;
  status: FieldStatus;
  confidence: number;
  provenance: string;
  requiresConfirmation: boolean;
}

export interface LogisticTerm {
  key: string;
  label: string;
  mean: number;
  standardError: number;
}

export interface PredictionResult {
  probabilityAdmit: number;
  probabilityTreatAndRelease: number;
  linearPredictor: number;
  activeTerms: LogisticTerm[];
}

export interface HistogramBin {
  range: string;
  midpoint: number;
  count: number;
}

export interface SensitivityResult {
  parameter: string;
  correlation: number;
  absoluteCorrelation: number;
}

export interface SimulationResult {
  sampleCount: number;
  seed: number;
  samples: number[];
  median: number;
  p10: number;
  p90: number;
  p025: number;
  p975: number;
  histogram: HistogramBin[];
  sensitivity: SensitivityResult[];
}
