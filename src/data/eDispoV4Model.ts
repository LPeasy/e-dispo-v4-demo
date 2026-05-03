import type { PooledEmpiricalModelArtifact } from "./pooledEmpiricalModel"

export const E_DISPO_V4_MODEL_ID = "e-dispo-v4.0" as const

const limitationNote =
  "Dataset-derived from pooled NHAMCS 2018-2022 severe-only pain refit for educational use only; not clinical decision support."

export const eDispoV4Model: PooledEmpiricalModelArtifact = {
  allowed_use: "educational only; not clinical decision support",
  calibration: {
    auroc: 0.7130954171835037,
    brier_score: 0.09764025910259386,
    intercept: 7.189863181029586e-9,
    mean_predicted: 0.11754651739805459,
    observed_prevalence: 0.11754651739758315,
    slope: 1.0000000000048073,
  },
  coefficient_source: "nhamcs_pooled_2018_2022",
  cohort_counts: {
    MIMIC_IV_ED: {
      admission_events: 9,
      routine_home_discharge: 3,
      start_n: 222,
      strict_binary_n: 12,
    },
    NHAMCS_2018_2022_POOLED: {
      admission_events: 459,
      event_count_gate_passed: true,
      strict_binary_unweighted_n: 3805,
      weighted_admission_prevalence: 0.12448514982051484,
    },
  },
  covariance_matrix_path:
    "outputs/nhamcs_pooled/e_dispo_v4_pain_severe_covariance.csv",
  dataset_sources: ["NHAMCS_2018_2022_POOLED", "MIMIC_IV_ED"],
  endpoint: "same-hospital admission vs routine home discharge after exclusions",
  fever_promotion_gate_status: "dataset_derived",
  generated_at: "2026-05-01T00:00:00Z",
  model_activation_status: "eligible_for_educational_activation_after_review",
  model_id: E_DISPO_V4_MODEL_ID,
  model_version: "e_dispo_v4_0_pain_severe_20260501",
  pain_monotonicity_verdict: "nonmonotonic_collapsed_to_severe_binary",
  population: "adult men 18-64, ED, non-traumatic abdominal pain",
  posterior_draws_path:
    "outputs/nhamcs_pooled/e_dispo_v4_pain_severe_draws.csv",
  predictor_evidence_tiers: [
    {
      blockers: "",
      evidence_tier: "dataset_derived",
      level: "",
      term: "intercept",
    },
    {
      blockers: "",
      evidence_tier: "dataset_derived",
      level: "per_1_year_centered_at_42",
      term: "age_centered",
    },
    {
      blockers: "",
      evidence_tier: "dataset_derived",
      level: "1",
      term: "pain_severe",
    },
    {
      blockers: "",
      evidence_tier: "dataset_derived",
      level: "1",
      term: "fever_or_temp",
    },
    {
      blockers: "",
      evidence_tier: "dataset_derived",
      level: "1",
      term: "vomiting_present",
    },
    {
      blockers: "",
      evidence_tier: "dataset_derived",
      level: "per_10_bpm_over_100",
      term: "tachycardia_burden",
    },
  ],
  predictors: [
    {
      center_beta: -2.5279874917252374,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "",
      limitation_note: limitationNote,
      reference: false,
      se_or_sd: 0.18433118832706466,
      source: "NHAMCS_2018_2022_POOLED",
      term: "intercept",
    },
    {
      center_beta: 0.043118787834530395,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "per_1_year_centered_at_42",
      limitation_note: limitationNote,
      reference: false,
      se_or_sd: 0.007146450287031601,
      source: "NHAMCS_2018_2022_POOLED",
      term: "age_centered",
    },
    {
      center_beta: 0.52181881795062,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "1",
      limitation_note:
        "Dataset-derived severe-vs-non-severe pain term. Mild and moderate are collapsed because flexible pain showed nonmonotonic mild/moderate behavior; this is not a monotonic pain dose-response claim.",
      reference: false,
      se_or_sd: 0.1839432889582862,
      source: "NHAMCS_2018_2022_POOLED",
      term: "pain_severe",
    },
    {
      center_beta: 0.8870420313203969,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "1",
      limitation_note: limitationNote,
      reference: false,
      se_or_sd: 0.7464334685513486,
      source: "NHAMCS_2018_2022_POOLED",
      term: "fever_or_temp",
    },
    {
      center_beta: 0.46912257968096427,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "1",
      limitation_note: limitationNote,
      reference: false,
      se_or_sd: 0.18280173695731686,
      source: "NHAMCS_2018_2022_POOLED",
      term: "vomiting_present",
    },
    {
      center_beta: 0.4269432162227637,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "per_10_bpm_over_100",
      limitation_note: limitationNote,
      reference: false,
      se_or_sd: 0.11216275972001569,
      source: "NHAMCS_2018_2022_POOLED",
      term: "tachycardia_burden",
    },
  ],
  run_id: "e_dispo_v4_0_pain_severe_20260501",
  status: "versioned_empirical_candidate",
}

export const activeEmpiricalModel = eDispoV4Model
