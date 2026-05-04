import {
  calculatePas5Acuity,
  pas5Questions,
  type Pas5Result,
} from "./aap3Acuity"
import type { ModelInputs, WorksheetField } from "./types"

const scalarFieldKeys = [
  "ageBand",
  "broadPainRegion",
  "painSeverity",
  "onsetDurationCategory",
  "constantVsIntermittent",
  "vomiting",
  "fever",
] as const satisfies Array<Exclude<keyof ModelInputs, "pas5">>

export const fieldLabels: Record<keyof ModelInputs, string> = {
  ageBand: "Age band",
  broadPainRegion: "Broad pain region",
  painSeverity: "Pain severity",
  onsetDurationCategory: "Onset/duration category",
  constantVsIntermittent: "Constant vs intermittent",
  vomiting: "Vomiting",
  fever: "Fever",
  pas5: "Patient-perceived acuity proxy",
}

export const valueLabels: Record<string, string> = {
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
  safe_wait: "I feel okay waiting if needed.",
  concerned_but_safe: "I am worried, but I still feel okay waiting.",
  should_be_seen_soon: "I feel I should be checked soon.",
  unsafe_waiting: "I feel I cannot safely wait.",
  improving_or_stable: "It is getting better or staying about the same.",
  persistent_not_worse: "It is still there, but not getting worse.",
  worse_or_spreading: "It is getting worse or spreading.",
  rapidly_worse_or_new_major_symptoms:
    "It is getting worse quickly, or new major symptoms have started.",
  normal_activity: "I can move around and do normal activities.",
  limited_independent: "I am limited, but I can manage by myself.",
  needs_support_or_must_lie_down: "I need help, or I need to lie down.",
  cannot_stand_walk_or_nearly_faint:
    "I cannot stand or walk, or I feel like I may faint.",
  manageable: "Manageable.",
  uncomfortable: "Uncomfortable.",
  severe_hard_to_focus: "Severe; it is hard to focus on anything else.",
  overwhelming: "Overwhelming.",
  exam_only: "A check by medical staff only.",
  one_test_or_oral_med: "One simple test or medicine by mouth.",
  labs_iv_or_imaging:
    "Blood tests, X-ray/CT/ultrasound, or fluids/medicine through an IV.",
  monitoring_procedure_specialist_or_possible_hospitalization:
    "Close monitoring, a procedure, a specialist, or possible hospital stay.",
  high_acuity: "High-acuity surrogate",
  urgent_reference: "Urgent reference",
  lower_acuity: "Lower-acuity surrogate",
}

export function buildWorksheetFields(
  inputs: ModelInputs
): WorksheetField<string>[] {
  const scalarFields: WorksheetField<string>[] = scalarFieldKeys.map((key) => {
    const value = inputs[key]
    const isUnknown = value === "unknown"

    return {
      name: fieldLabels[key],
      value: valueLabels[value],
      status: isUnknown ? "needs_confirmation" : "user_entered",
      confidence: isUnknown ? 0.48 : 0.92,
      provenance: "Structured MVP form input",
      requiresConfirmation: isUnknown,
    }
  })

  return [
    ...scalarFields,
    {
      name: fieldLabels.pas5,
      value: formatPas5Inputs(inputs.pas5),
      status: "user_entered" as const,
      confidence: 0.92,
      provenance: "Structured PAS-5 form input",
      requiresConfirmation: false,
    },
  ]
}

export function formatPas5Inputs(inputs: ModelInputs["pas5"]): string {
  return formatPas5Result(calculatePas5Acuity(inputs))
}

export function formatPas5Result(result: Pas5Result): string {
  return `${result.acuityClass} (${result.score}/15; high-acuity proxy: ${
    result.highAcuityProxy ? "yes" : "no"
  })`
}

export function hasRequiredClassFields(inputs: Partial<ModelInputs>): boolean {
  const scalarFieldsPresent = scalarFieldKeys.every(
    (key) => inputs[key] !== undefined && inputs[key] !== null
  )
  const pas5FieldsPresent = pas5Questions.every(
    (question) =>
      inputs.pas5?.[question.id] !== undefined &&
      inputs.pas5?.[question.id] !== null
  )

  return scalarFieldsPresent && pas5FieldsPresent
}
