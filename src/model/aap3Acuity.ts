export type Pas5AcuityClass = "A1" | "A2" | "A3" | "A4" | "A5"
export type Pas5AcuityGroup =
  | "high_acuity"
  | "urgent_reference"
  | "lower_acuity"

export type Pas5QuestionId =
  | "immediateConcern"
  | "trajectory"
  | "function"
  | "distress"
  | "expectedResources"

export type Pas5AnswerId =
  | "safe_wait"
  | "concerned_but_safe"
  | "should_be_seen_soon"
  | "unsafe_waiting"
  | "improving_or_stable"
  | "persistent_not_worse"
  | "worse_or_spreading"
  | "rapidly_worse_or_new_major_symptoms"
  | "normal_activity"
  | "limited_independent"
  | "needs_support_or_must_lie_down"
  | "cannot_stand_walk_or_nearly_faint"
  | "manageable"
  | "uncomfortable"
  | "severe_hard_to_focus"
  | "overwhelming"
  | "exam_only"
  | "one_test_or_oral_med"
  | "labs_iv_or_imaging"
  | "monitoring_procedure_specialist_or_possible_hospitalization"

export type Pas5Inputs = Record<Pas5QuestionId, Pas5AnswerId>

export type Pas5AnswerOption = {
  id: Pas5AnswerId
  label: string
  score: 0 | 1 | 2 | 3
}

export type Pas5Question = {
  id: Pas5QuestionId
  label: string
  options: Pas5AnswerOption[]
}

export type Pas5Result = {
  evidenceLabel: "patient_perceived_acuity_proxy"
  score: number
  acuityClass: Pas5AcuityClass
  unguardedClass: Pas5AcuityClass
  group: Pas5AcuityGroup
  highAcuityProxy: boolean
  guardrailCount: number
  guardrailApplied: boolean
  selectedAnswers: Record<Pas5QuestionId, Pas5AnswerOption>
}

export const pas5AcuityClasses: Array<{
  id: Pas5AcuityClass
  label: string
}> = [
  { id: "A1", label: "Highest perceived acuity proxy" },
  { id: "A2", label: "High perceived acuity proxy" },
  { id: "A3", label: "Urgent reference proxy" },
  { id: "A4", label: "Lower perceived acuity proxy" },
  { id: "A5", label: "Lowest perceived acuity proxy" },
]

export const pas5ImmediateConcernOptions: Pas5AnswerOption[] = [
  {
    id: "safe_wait",
    label: "I feel okay waiting if needed.",
    score: 0,
  },
  {
    id: "concerned_but_safe",
    label: "I am worried, but I still feel okay waiting.",
    score: 1,
  },
  {
    id: "should_be_seen_soon",
    label: "I feel I should be checked soon.",
    score: 2,
  },
  {
    id: "unsafe_waiting",
    label: "I feel I cannot safely wait.",
    score: 3,
  },
]

export const pas5TrajectoryOptions: Pas5AnswerOption[] = [
  {
    id: "improving_or_stable",
    label: "It is getting better or staying about the same.",
    score: 0,
  },
  {
    id: "persistent_not_worse",
    label: "It is still there, but not getting worse.",
    score: 1,
  },
  {
    id: "worse_or_spreading",
    label: "It is getting worse or spreading.",
    score: 2,
  },
  {
    id: "rapidly_worse_or_new_major_symptoms",
    label: "It is getting worse quickly, or new major symptoms have started.",
    score: 3,
  },
]

export const pas5FunctionOptions: Pas5AnswerOption[] = [
  {
    id: "normal_activity",
    label: "I can move around and do normal activities.",
    score: 0,
  },
  {
    id: "limited_independent",
    label: "I am limited, but I can manage by myself.",
    score: 1,
  },
  {
    id: "needs_support_or_must_lie_down",
    label: "I need help, or I need to lie down.",
    score: 2,
  },
  {
    id: "cannot_stand_walk_or_nearly_faint",
    label: "I cannot stand or walk, or I feel like I may faint.",
    score: 3,
  },
]

export const pas5DistressOptions: Pas5AnswerOption[] = [
  {
    id: "manageable",
    label: "Manageable.",
    score: 0,
  },
  {
    id: "uncomfortable",
    label: "Uncomfortable.",
    score: 1,
  },
  {
    id: "severe_hard_to_focus",
    label: "Severe; it is hard to focus on anything else.",
    score: 2,
  },
  {
    id: "overwhelming",
    label: "Overwhelming.",
    score: 3,
  },
]

export const pas5ExpectedResourcesOptions: Pas5AnswerOption[] = [
  {
    id: "exam_only",
    label: "A check by medical staff only.",
    score: 0,
  },
  {
    id: "one_test_or_oral_med",
    label: "One simple test or medicine by mouth.",
    score: 1,
  },
  {
    id: "labs_iv_or_imaging",
    label: "Blood tests, X-ray/CT/ultrasound, or fluids/medicine through an IV.",
    score: 2,
  },
  {
    id: "monitoring_procedure_specialist_or_possible_hospitalization",
    label: "Close monitoring, a procedure, a specialist, or possible hospital stay.",
    score: 3,
  },
]

export const pas5Questions: Pas5Question[] = [
  {
    id: "immediateConcern",
    label: "Right now, how worried are you about waiting before medical staff check you?",
    options: pas5ImmediateConcernOptions,
  },
  {
    id: "trajectory",
    label: "Since this started, how has it changed?",
    options: pas5TrajectoryOptions,
  },
  {
    id: "function",
    label: "Right now, how much can you do on your own?",
    options: pas5FunctionOptions,
  },
  {
    id: "distress",
    label: "How hard is this to handle right now?",
    options: pas5DistressOptions,
  },
  {
    id: "expectedResources",
    label: "What do you think this emergency visit may need?",
    options: pas5ExpectedResourcesOptions,
  },
]

export const initialPas5Inputs: Pas5Inputs = {
  immediateConcern: "safe_wait",
  trajectory: "improving_or_stable",
  function: "normal_activity",
  distress: "manageable",
  expectedResources: "exam_only",
}

const pas5ClassRank: Record<Pas5AcuityClass, number> = {
  A1: 1,
  A2: 2,
  A3: 3,
  A4: 4,
  A5: 5,
}

export function calculatePas5Acuity(inputs: Pas5Inputs): Pas5Result {
  const selectedAnswers = selectedPas5Answers(inputs)
  const score = pas5Questions.reduce(
    (sum, question) => sum + selectedAnswers[question.id].score,
    0,
  )
  const unguardedClass = pas5ScoreToClass(score)
  const guardrailCount = pas5GuardrailCount(inputs)
  const acuityClass =
    guardrailCount >= 2
      ? applyMinimumClass(unguardedClass, "A1")
      : guardrailCount === 1
        ? applyMinimumClass(unguardedClass, "A2")
        : unguardedClass

  return {
    evidenceLabel: "patient_perceived_acuity_proxy",
    score,
    acuityClass,
    unguardedClass,
    group: pas5ClassToGroup(acuityClass),
    highAcuityProxy: pas5ClassToHighAcuityProxy(acuityClass),
    guardrailCount,
    guardrailApplied: acuityClass !== unguardedClass,
    selectedAnswers,
  }
}

export function pas5ScoreToClass(score: number): Pas5AcuityClass {
  if (!Number.isFinite(score) || score < 0 || score > 15) {
    throw new Error("PAS-5 score must be a finite number from 0 through 15.")
  }

  if (score <= 2) {
    return "A5"
  }

  if (score <= 5) {
    return "A4"
  }

  if (score <= 8) {
    return "A3"
  }

  if (score <= 11) {
    return "A2"
  }

  return "A1"
}

export function pas5ClassToGroup(
  acuityClass: Pas5AcuityClass,
): Pas5AcuityGroup {
  if (acuityClass === "A1" || acuityClass === "A2") {
    return "high_acuity"
  }

  if (acuityClass === "A3") {
    return "urgent_reference"
  }

  return "lower_acuity"
}

export function pas5ClassToHighAcuityProxy(
  acuityClass: Pas5AcuityClass,
): boolean {
  return acuityClass === "A1" || acuityClass === "A2"
}

function selectedPas5Answers(
  inputs: Pas5Inputs,
): Record<Pas5QuestionId, Pas5AnswerOption> {
  return Object.fromEntries(
    pas5Questions.map((question) => {
      const answer = question.options.find(
        (option) => option.id === inputs[question.id],
      )

      if (!answer) {
        throw new Error(`Missing PAS-5 answer for ${question.id}.`)
      }

      return [question.id, answer]
    }),
  ) as Record<Pas5QuestionId, Pas5AnswerOption>
}

function pas5GuardrailCount(inputs: Pas5Inputs): number {
  return [
    inputs.immediateConcern === "unsafe_waiting",
    inputs.function === "cannot_stand_walk_or_nearly_faint",
    inputs.distress === "overwhelming",
  ].filter(Boolean).length
}

function applyMinimumClass(
  acuityClass: Pas5AcuityClass,
  minimumClass: Pas5AcuityClass,
): Pas5AcuityClass {
  return pas5ClassRank[acuityClass] > pas5ClassRank[minimumClass]
    ? minimumClass
    : acuityClass
}
