import type { ModelInputs, WorksheetField } from "./types"

export const fieldLabels: Record<keyof ModelInputs, string> = {
  ageBand: "Age band",
  broadPainRegion: "Broad pain region",
  painSeverity: "Pain severity",
  onsetDurationCategory: "Onset/duration category",
  constantVsIntermittent: "Constant vs intermittent",
  vomiting: "Vomiting",
  fever: "Fever",
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
}

export function buildWorksheetFields(
  inputs: ModelInputs
): WorksheetField<string>[] {
  return (Object.keys(fieldLabels) as Array<keyof ModelInputs>).map((key) => {
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
}

export function hasRequiredClassFields(inputs: Partial<ModelInputs>): boolean {
  return (Object.keys(fieldLabels) as Array<keyof ModelInputs>).every(
    (key) => inputs[key] !== undefined && inputs[key] !== null
  )
}
