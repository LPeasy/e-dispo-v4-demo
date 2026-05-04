export type PooledEmpiricalEvidenceTier = "dataset_derived"

export type PooledEmpiricalModelId =
  | "pooled_empirical_v2_age_pain_fever_vomiting_tachycardia"
  | "e-dispo-v4.0"
  | "e-dispo-v4.1-pas5-high-acuity-surrogate"

export type PooledEmpiricalPredictor = {
  center_beta: number
  distribution: "normal_approximation_exploratory"
  evidence_tier: PooledEmpiricalEvidenceTier
  level: string
  limitation_note: string
  reference: boolean
  se_or_sd: number
  source: "NHAMCS_2018_2022_POOLED"
  term:
    | "intercept"
    | "age_centered"
    | "pain_bin3"
    | "pain_severe"
    | "fever_or_temp"
    | "vomiting_present"
    | "tachycardia_burden"
    | "high_acuity_proxy"
}

export type PooledEmpiricalPerformanceInterval = {
  ci_high: number
  ci_low: number
  estimate: number
  interval_level: number
  limitation: string
  method: "survey_bootstrap_replicate_weights_fixed_apparent_predictions"
  metric: "auroc" | "brier_score"
  status: "ok"
}

export type PooledEmpiricalModelArtifact = {
  allowed_use: "educational only; not clinical decision support"
  calibration: {
    auroc: number
    brier_score: number
    intercept: number
    mean_predicted: number
    observed_prevalence: number
    slope: number
  }
  coefficient_source: "nhamcs_pooled_2018_2022"
  cohort_counts: {
    NHAMCS_2018_2022_POOLED: {
      admission_events: number
      event_count_gate_passed: boolean
      strict_binary_unweighted_n: number
      weighted_admission_prevalence: number
    }
    MIMIC_IV_ED?: {
      admission_events: number
      routine_home_discharge: number
      start_n: number
      strict_binary_n: number
    }
  }
  covariance_matrix_path: string
  dataset_sources: string[]
  endpoint: string
  fever_promotion_gate_status: PooledEmpiricalEvidenceTier
  generated_at: string
  model_activation_status: "eligible_for_educational_activation_after_review"
  model_id: PooledEmpiricalModelId
  model_version: string
  pain_monotonicity_verdict:
    | "nonmonotonic_flexible_only"
    | "nonmonotonic_collapsed_to_severe_binary"
  performance_intervals?: PooledEmpiricalPerformanceInterval[]
  population: string
  posterior_draws_path: string
  predictor_evidence_tiers: Array<{
    blockers: string
    evidence_tier: PooledEmpiricalEvidenceTier
    level: string
    term:
      | "intercept"
      | "age_centered"
      | "pain_bin3"
      | "pain_severe"
      | "fever_or_temp"
      | "vomiting_present"
      | "tachycardia_burden"
      | "high_acuity_proxy"
  }>
  predictors: PooledEmpiricalPredictor[]
  run_id: string
  status: "reduced_empirical_candidate" | "versioned_empirical_candidate"
  validation_artifact_paths?: {
    calibration_by_decile: string
    calibration_plot_data: string
    candidate_refinement_gate?: string
    full_source_endpoint_screen_calibration?: string
    full_source_endpoint_screen_missingness?: string
    full_source_endpoint_screen_performance?: string
    full_source_nontrauma_screen_calibration?: string
    full_source_nontrauma_screen_missingness?: string
    full_source_nontrauma_screen_performance?: string
    full_source_scope_screen_report?: string
    missingness_performance?: string
    optimism_corrected_performance?: string
    performance_intervals: string
    subgroup_calibration?: string
    subgroup_performance?: string
    transportability_track?: string
  }
}

export const pooledEmpiricalModel: PooledEmpiricalModelArtifact = {
  allowed_use: "educational only; not clinical decision support",
  calibration: {
    auroc: 0.713136138278221,
    brier_score: 0.0976939138074894,
    intercept: 7.48672979015688e-09,
    mean_predicted: 0.117546517398504,
    observed_prevalence: 0.117546517397583,
    slope: 1.00000000001178,
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
    "outputs/nhamcs_pooled/tachycardia_model_comparison_covariance.csv",
  dataset_sources: ["NHAMCS_2018_2022_POOLED", "MIMIC_IV_ED"],
  endpoint: "same-hospital admission vs routine home discharge after exclusions",
  fever_promotion_gate_status: "dataset_derived",
  generated_at: "2026-04-30T04:38:49Z",
  model_activation_status: "eligible_for_educational_activation_after_review",
  model_id: "pooled_empirical_v2_age_pain_fever_vomiting_tachycardia",
  model_version: "ed_disposition_empirical_reporting_final_export_20260430043849",
  pain_monotonicity_verdict: "nonmonotonic_flexible_only",
  population: "adult men 18-64, ED, non-traumatic abdominal pain",
  posterior_draws_path:
    "outputs/nhamcs_pooled/tachycardia_model_comparison_draws.csv",
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
      level: "mild",
      term: "pain_bin3",
    },
    {
      blockers: "",
      evidence_tier: "dataset_derived",
      level: "severe",
      term: "pain_bin3",
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
      center_beta: -2.59951501883394,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "",
      limitation_note:
        "Dataset-derived from pooled NHAMCS tachycardia burden evidence gates for educational use only; not clinical decision support.",
      reference: false,
      se_or_sd: 0.188267290502029,
      source: "NHAMCS_2018_2022_POOLED",
      term: "intercept",
    },
    {
      center_beta: 0.0428859112061537,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "per_1_year_centered_at_42",
      limitation_note:
        "Dataset-derived from pooled NHAMCS tachycardia burden evidence gates for educational use only; not clinical decision support.",
      reference: false,
      se_or_sd: 0.00717600912093568,
      source: "NHAMCS_2018_2022_POOLED",
      term: "age_centered",
    },
    {
      center_beta: 0.179863742094317,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "mild",
      limitation_note:
        "Dataset-derived from pooled NHAMCS tachycardia burden evidence gates for educational use only; not clinical decision support.",
      reference: false,
      se_or_sd: 0.32670443289309,
      source: "NHAMCS_2018_2022_POOLED",
      term: "pain_bin3",
    },
    {
      center_beta: 0.594888679552716,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "severe",
      limitation_note:
        "Dataset-derived from pooled NHAMCS tachycardia burden evidence gates for educational use only; not clinical decision support.",
      reference: false,
      se_or_sd: 0.201900422342599,
      source: "NHAMCS_2018_2022_POOLED",
      term: "pain_bin3",
    },
    {
      center_beta: 0.876624346325165,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "1",
      limitation_note:
        "Dataset-derived from pooled NHAMCS tachycardia burden evidence gates for educational use only; not clinical decision support.",
      reference: false,
      se_or_sd: 0.751935416560386,
      source: "NHAMCS_2018_2022_POOLED",
      term: "fever_or_temp",
    },
    {
      center_beta: 0.467092510247221,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "1",
      limitation_note:
        "Dataset-derived from pooled NHAMCS tachycardia burden evidence gates for educational use only; not clinical decision support.",
      reference: false,
      se_or_sd: 0.183939361281035,
      source: "NHAMCS_2018_2022_POOLED",
      term: "vomiting_present",
    },
    {
      center_beta: 0.42559860829402,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "per_10_bpm_over_100",
      limitation_note:
        "Dataset-derived from pooled NHAMCS tachycardia burden evidence gates for educational use only; not clinical decision support.",
      reference: false,
      se_or_sd: 0.112857094794981,
      source: "NHAMCS_2018_2022_POOLED",
      term: "tachycardia_burden",
    },
  ],
  run_id: "final_export_20260430043849",
  status: "reduced_empirical_candidate",
}
