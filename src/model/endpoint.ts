import type {
  EligibilityResult,
  EligibilityState,
  EndpointRecodingResult,
  EndpointRecodingRow,
  RecodingResult,
} from "./types"

const trueValues = new Set<unknown>([
  true,
  1,
  "1",
  "Y",
  "YES",
  "Yes",
  "yes",
  "TRUE",
  "True",
  "true",
])

type TerminalClasses = {
  admitOrObservationHospitalized: boolean
  homeRelease: boolean
  observationDischarged: boolean
  transferAny: boolean
  nonroutineExit: boolean
  otherUnknown: boolean
}

function flag(row: EndpointRecodingRow, ...names: string[]): boolean {
  return names.some((name) => {
    const value = row[name]

    if (trueValues.has(value)) {
      return true
    }

    return typeof value === "string" && trueValues.has(value.trim())
  })
}

function terminalClasses(row: EndpointRecodingRow): TerminalClasses {
  const admit = flag(
    row,
    "ADMITHOS",
    "admit_to_this_hospital",
    "ADMITTED",
    "hadm_id_present"
  )
  const observationHospitalized = flag(
    row,
    "OBSHOS",
    "observation_then_hospitalized"
  )
  const homeRelease = flag(
    row,
    "NOFU",
    "RETRNED",
    "RETREFFU",
    "no_followup",
    "return_to_ed",
    "return_refer_outpatient",
    "HOME"
  )
  const observationDischarged = flag(
    row,
    "OBSDIS",
    "observation_then_discharged"
  )
  const transferAny = flag(
    row,
    "TRANOTH",
    "TRANNH",
    "TRANPSYC",
    "TRANSFER",
    "transfer_to_other_hospital",
    "transfer_to_psych",
    "transfer_to_nursing_home"
  )
  const nonroutineExit = flag(
    row,
    "LEFTAMA",
    "LWBS",
    "LBTC",
    "ELOPED",
    "left_ama",
    "left_without_being_seen",
    "left_before_treatment_complete",
    "eloped"
  )
  const otherUnknown = flag(
    row,
    "OTHDISP",
    "NODISP",
    "OTHER",
    "UNKNOWN",
    "MISSING",
    "blank",
    "unknown",
    "missing"
  )

  return {
    admitOrObservationHospitalized: admit || observationHospitalized,
    homeRelease,
    observationDischarged,
    transferAny,
    nonroutineExit,
    otherUnknown,
  }
}

export function recodeEndpoint(row: EndpointRecodingRow): EndpointRecodingResult {
  const death = flag(
    row,
    "DOA",
    "DIEDED",
    "EXPIRED",
    "death",
    "died_in_ed",
    "dead_on_arrival"
  )
  const classes = terminalClasses(row)
  const acuteTransfer = flag(
    row,
    "TRANOTH",
    "transfer_to_other_hospital",
    "acute_transfer",
    "TRANSFER"
  )

  if (death) {
    return {
      endpointPrimary: "EXCLUDE_SENTINEL_DEATH",
      endpointSensAEventualHome: "EXCLUDE_SENTINEL_DEATH",
      endpointSensBAcuteEscalation: "EXCLUDE_SENTINEL_DEATH",
      sentinelDeathFlag: true,
      reason: "Death/DOA/died-in-ED sentinel exclusion",
    }
  }

  const terminalCount = Object.values(classes).filter(Boolean).length
  if (terminalCount > 1) {
    return {
      endpointPrimary: "EXCLUDE_CONFLICT",
      endpointSensAEventualHome: "EXCLUDE_CONFLICT",
      endpointSensBAcuteEscalation: "EXCLUDE_CONFLICT",
      sentinelDeathFlag: false,
      reason: "Conflicting terminal disposition flags",
    }
  }

  if (classes.transferAny) {
    return {
      endpointPrimary: "EXCLUDE_TRANSFER_PRIMARY",
      endpointSensAEventualHome: "EXCLUDE_TRANSFER_PRIMARY",
      endpointSensBAcuteEscalation: acuteTransfer
        ? "ACUTE_ESCALATION_POSITIVE"
        : "EXCLUDE_TRANSFER_PRIMARY",
      sentinelDeathFlag: false,
      reason:
        "Transfer excluded from primary; acute transfer included only in sensitivity B",
    }
  }

  if (classes.nonroutineExit) {
    return {
      endpointPrimary: "EXCLUDE_NONROUTINE_EXIT",
      endpointSensAEventualHome: "EXCLUDE_NONROUTINE_EXIT",
      endpointSensBAcuteEscalation: "EXCLUDE_NONROUTINE_EXIT",
      sentinelDeathFlag: false,
      reason: "AMA/LWBS/LBTC/elopement excluded",
    }
  }

  if (classes.admitOrObservationHospitalized) {
    return {
      endpointPrimary: "ADMIT",
      endpointSensAEventualHome: "ADMIT",
      endpointSensBAcuteEscalation: "ACUTE_ESCALATION_POSITIVE",
      sentinelDeathFlag: false,
      reason: "Same-hospital admission/hospitalization",
    }
  }

  if (classes.homeRelease) {
    return {
      endpointPrimary: "TREAT_AND_RELEASE",
      endpointSensAEventualHome: "TREAT_AND_RELEASE",
      endpointSensBAcuteEscalation: "TREAT_AND_RELEASE",
      sentinelDeathFlag: false,
      reason: "Routine home release",
    }
  }

  if (classes.observationDischarged) {
    return {
      endpointPrimary: "EXCLUDE_OBS_DISCHARGED_PRIMARY",
      endpointSensAEventualHome: "TREAT_AND_RELEASE",
      endpointSensBAcuteEscalation: "TREAT_AND_RELEASE",
      sentinelDeathFlag: false,
      reason:
        "Observation -> discharged included only in eventual-home sensitivity",
    }
  }

  return {
    endpointPrimary: "EXCLUDE_OTHER_UNKNOWN",
    endpointSensAEventualHome: "EXCLUDE_OTHER_UNKNOWN",
    endpointSensBAcuteEscalation: "EXCLUDE_OTHER_UNKNOWN",
    sentinelDeathFlag: false,
    reason: "Other/unknown/missing endpoint",
  }
}

const dispositionMap: Record<string, RecodingResult> = {
  same_hospital_admission: {
    status: "included",
    label: "admit",
    reason: "Same-hospital inpatient admission/hospitalization.",
  },
  observation_then_hospitalization: {
    status: "included",
    label: "admit",
    reason: "Observation followed by hospitalization maps to admit.",
  },
  home_routine: {
    status: "included",
    label: "treat_and_release",
    reason:
      "Routine home release, including no follow-up, return if needed, or outpatient follow-up disposition.",
  },
  transfer: {
    status: "excluded",
    reason:
      "Transfer is excluded from the primary same-hospital hospitalization/admission endpoint.",
  },
  death_expired: {
    status: "excluded",
    reason:
      "Death/expired/DOA is a sentinel exclusion and is not predicted.",
  },
  ama_lwbs_eloped: {
    status: "excluded",
    reason: "AMA, LWBS, left before treatment complete, or eloped cases are excluded.",
  },
  observation_only: {
    status: "excluded",
    reason:
      "Observation -> discharged is excluded from primary v3 and included only in sensitivity endpoints.",
  },
  other_unknown: {
    status: "excluded",
    reason: "Other, missing, unavailable, or unknown dispositions are excluded.",
  },
}

export function recodeDisposition(sourceDisposition: string): RecodingResult {
  return (
    dispositionMap[sourceDisposition] ?? {
      status: "excluded",
      reason: "Unrecognized source disposition is excluded until explicitly mapped.",
    }
  )
}

export function evaluateEligibility(state: EligibilityState): EligibilityResult {
  const reasons: string[] = []

  if (!state.alreadyInEd) {
    reasons.push("The class model begins only after ED presentation.")
  }

  if (state.age < 18 || state.age > 64) {
    reasons.push("Age must be 18-64 for the class model.")
  }

  if (state.sex !== "male") {
    reasons.push("The current class package is scoped to adult men.")
  }

  if (state.chiefComplaint !== "abdominal_pain") {
    reasons.push("Chief complaint must be non-traumatic abdominal pain.")
  }

  if (state.traumaRelated) {
    reasons.push("Trauma/injury-related abdominal pain is excluded.")
  }

  if (state.redFlagStatement) {
    reasons.push(
      "Red-flag statements are redirected to local ED clinical processes before model output."
    )
  }

  return {
    canProceed: reasons.length === 0,
    title: reasons.length === 0 ? "Eligible for class-model demo" : "Blocked: out of scope",
    reasons:
      reasons.length === 0
        ? [
            "Adult man ages 18-64.",
            "Already in ED.",
            "Non-traumatic abdominal pain.",
            "No red-flag block selected.",
          ]
        : reasons,
  }
}

export const endpointRows = [
  {
    source: "Same-hospital inpatient admission or observation -> hospitalized",
    model: "admit",
    action: "Include",
  },
  {
    source: "No follow-up, return if needed, or outpatient follow-up",
    model: "treat_and_release",
    action: "Include",
  },
  {
    source: "Observation -> discharged",
    model: "Excluded from primary",
    action: "Sensitivity A/B only as eventual home release",
  },
  {
    source: "Transfer, death/expired, AMA/LWBS/LBTC/eloped",
    model: "Excluded",
    action: "Remove before primary binary probabilities",
  },
  {
    source: "Other, missing, unknown, or conflicting flags",
    model: "Excluded",
    action: "Remove and tabulate",
  },
]
