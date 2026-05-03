export type Aap3AcuityClass = "A1" | "A2" | "A3" | "A4" | "A5"

export type Aap3QuestionId =
  | "dangerDistress"
  | "vitalsSystemic"
  | "abdominalFeatures"

export type Aap3AnswerId =
  | "q1_1_none"
  | "q1_2_uncomfortable"
  | "q1_3_moderate_distress"
  | "q1_4_severe_distress"
  | "q1_5_danger_or_immediate_concern"
  | "q2_1_normal_vitals"
  | "q2_2_vitals_unknown"
  | "q2_3_mild_systemic"
  | "q2_4_abnormal_vitals"
  | "q2_5_unstable_systemic"
  | "q3_1_no_high_risk_features"
  | "q3_2_persistent_vomiting_or_dehydration"
  | "q3_3_focal_peritoneal_or_obstructive_features"
  | "q3_4_bleeding_or_severe_abdominal_features"

export type Aap3Inputs = Record<Aap3QuestionId, Aap3AnswerId>

export type Aap3AnswerOption = {
  id: Aap3AnswerId
  label: string
  probabilities: Record<Aap3AcuityClass, number>
}

export type Aap3Question = {
  id: Aap3QuestionId
  label: string
  weight: number
  options: Aap3AnswerOption[]
}

export type Aap3Posterior = {
  evidenceLabel: "prototype_acuity_proxy"
  probabilities: Record<Aap3AcuityClass, number>
  selectedAnswers: Record<Aap3QuestionId, Aap3AnswerOption>
  guardrailApplied: boolean
}

export const aap3AcuityClasses: Array<{
  id: Aap3AcuityClass
  label: string
}> = [
  { id: "A1", label: "Critical / immediate concern" },
  { id: "A2", label: "Emergent / high-risk" },
  { id: "A3", label: "Urgent" },
  { id: "A4", label: "Lower-acuity" },
  { id: "A5", label: "Minimal-acuity" },
]

export const aap3NeutralPrior: Record<Aap3AcuityClass, number> = {
  A1: 0.02,
  A2: 0.18,
  A3: 0.5,
  A4: 0.22,
  A5: 0.08,
}

export const aap3Epsilon = 0.005

export const aap3Questions: Aap3Question[] = [
  {
    id: "dangerDistress",
    label: "Q1 danger/distress",
    weight: 1,
    options: [
      {
        id: "q1_1_none",
        label: "No danger signs or severe distress",
        probabilities: { A1: 0.005, A2: 0.035, A3: 0.24, A4: 0.46, A5: 0.26 },
      },
      {
        id: "q1_2_uncomfortable",
        label: "Uncomfortable, no severe distress",
        probabilities: { A1: 0.01, A2: 0.08, A3: 0.5, A4: 0.3, A5: 0.11 },
      },
      {
        id: "q1_3_moderate_distress",
        label: "Moderate distress",
        probabilities: { A1: 0.02, A2: 0.22, A3: 0.58, A4: 0.15, A5: 0.03 },
      },
      {
        id: "q1_4_severe_distress",
        label: "Severe distress",
        probabilities: { A1: 0.08, A2: 0.55, A3: 0.32, A4: 0.04, A5: 0.01 },
      },
      {
        id: "q1_5_danger_or_immediate_concern",
        label: "Danger signs or immediate concern",
        probabilities: { A1: 0.55, A2: 0.38, A3: 0.06, A4: 0.008, A5: 0.002 },
      },
    ],
  },
  {
    id: "vitalsSystemic",
    label: "Q2 vitals/systemic illness",
    weight: 0.9,
    options: [
      {
        id: "q2_1_normal_vitals",
        label: "Normal vitals and well appearing",
        probabilities: { A1: 0.004, A2: 0.04, A3: 0.32, A4: 0.42, A5: 0.216 },
      },
      {
        id: "q2_2_vitals_unknown",
        label: "Vitals unknown",
        probabilities: { A1: 0.02, A2: 0.18, A3: 0.5, A4: 0.22, A5: 0.08 },
      },
      {
        id: "q2_3_mild_systemic",
        label: "Mild systemic illness",
        probabilities: { A1: 0.015, A2: 0.17, A3: 0.56, A4: 0.2, A5: 0.055 },
      },
      {
        id: "q2_4_abnormal_vitals",
        label: "Abnormal vitals or systemic concern",
        probabilities: { A1: 0.06, A2: 0.42, A3: 0.43, A4: 0.08, A5: 0.01 },
      },
      {
        id: "q2_5_unstable_systemic",
        label: "Unstable or toxic appearing",
        probabilities: { A1: 0.45, A2: 0.42, A3: 0.11, A4: 0.015, A5: 0.005 },
      },
    ],
  },
  {
    id: "abdominalFeatures",
    label: "Q3 abdominal-specific high-risk features",
    weight: 0.75,
    options: [
      {
        id: "q3_1_no_high_risk_features",
        label: "No abdominal high-risk features",
        probabilities: { A1: 0.005, A2: 0.05, A3: 0.4, A4: 0.38, A5: 0.165 },
      },
      {
        id: "q3_2_persistent_vomiting_or_dehydration",
        label: "Persistent vomiting or dehydration concern",
        probabilities: { A1: 0.02, A2: 0.24, A3: 0.56, A4: 0.15, A5: 0.03 },
      },
      {
        id: "q3_3_focal_peritoneal_or_obstructive_features",
        label: "Focal peritoneal or obstructive features",
        probabilities: { A1: 0.06, A2: 0.45, A3: 0.4, A4: 0.08, A5: 0.01 },
      },
      {
        id: "q3_4_bleeding_or_severe_abdominal_features",
        label: "Bleeding or severe abdominal features",
        probabilities: { A1: 0.12, A2: 0.55, A3: 0.28, A4: 0.04, A5: 0.01 },
      },
    ],
  },
]

export const initialAap3Inputs: Aap3Inputs = {
  dangerDistress: "q1_2_uncomfortable",
  vitalsSystemic: "q2_2_vitals_unknown",
  abdominalFeatures: "q3_1_no_high_risk_features",
}

export function calculateAap3Posterior(inputs: Aap3Inputs): Aap3Posterior {
  const selectedAnswers = selectedAap3Answers(inputs)
  const scores = Object.fromEntries(
    aap3AcuityClasses.map(({ id }) => {
      const prior = aap3NeutralPrior[id]
      const weightedEvidence = aap3Questions.reduce((sum, question) => {
        const answer = selectedAnswers[question.id]

        return (
          sum +
          question.weight *
            (Math.log(answer.probabilities[id] + aap3Epsilon) - Math.log(prior))
        )
      }, 0)

      return [id, Math.log(prior) + weightedEvidence]
    })
  ) as Record<Aap3AcuityClass, number>

  const rawProbabilities = softmax(scores)
  const guarded = applyQ1DangerGuardrail(inputs, rawProbabilities)

  return {
    evidenceLabel: "prototype_acuity_proxy",
    probabilities: guarded.probabilities,
    selectedAnswers,
    guardrailApplied: guarded.applied,
  }
}

function selectedAap3Answers(inputs: Aap3Inputs) {
  return Object.fromEntries(
    aap3Questions.map((question) => {
      const answer = question.options.find((option) => option.id === inputs[question.id])

      if (!answer) {
        throw new Error(`Missing AAP-3 answer for ${question.id}.`)
      }

      return [question.id, answer]
    })
  ) as Record<Aap3QuestionId, Aap3AnswerOption>
}

function softmax(
  scores: Record<Aap3AcuityClass, number>
): Record<Aap3AcuityClass, number> {
  const maxScore = Math.max(...Object.values(scores))
  const expScores = Object.fromEntries(
    aap3AcuityClasses.map(({ id }) => [id, Math.exp(scores[id] - maxScore)])
  ) as Record<Aap3AcuityClass, number>
  const denominator = Object.values(expScores).reduce((sum, value) => sum + value, 0)

  return Object.fromEntries(
    aap3AcuityClasses.map(({ id }) => [id, expScores[id] / denominator])
  ) as Record<Aap3AcuityClass, number>
}

function applyQ1DangerGuardrail(
  inputs: Aap3Inputs,
  probabilities: Record<Aap3AcuityClass, number>
): { probabilities: Record<Aap3AcuityClass, number>; applied: boolean } {
  if (inputs.dangerDistress !== "q1_5_danger_or_immediate_concern") {
    return { probabilities, applied: false }
  }

  const lowAcuityMass = probabilities.A4 + probabilities.A5
  const maxLowAcuityMass = 0.05

  if (lowAcuityMass <= maxLowAcuityMass) {
    return { probabilities, applied: false }
  }

  const excess = lowAcuityMass - maxLowAcuityMass
  const highAcuityMass = probabilities.A1 + probabilities.A2
  const a4Share = probabilities.A4 / lowAcuityMass
  const a5Share = probabilities.A5 / lowAcuityMass
  const a1Share = highAcuityMass === 0 ? 0.5 : probabilities.A1 / highAcuityMass
  const a2Share = highAcuityMass === 0 ? 0.5 : probabilities.A2 / highAcuityMass

  // Q1-5 is an immediate-concern answer. It caps A4/A5 mass and moves the
  // excess to A1/A2 so normal/unknown Q2 or low-risk Q3 cannot down-shift it.
  return {
    probabilities: {
      A1: probabilities.A1 + excess * a1Share,
      A2: probabilities.A2 + excess * a2Share,
      A3: probabilities.A3,
      A4: probabilities.A4 - excess * a4Share,
      A5: probabilities.A5 - excess * a5Share,
    },
    applied: true,
  }
}
