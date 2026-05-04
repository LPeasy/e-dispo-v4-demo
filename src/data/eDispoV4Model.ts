import type { PooledEmpiricalModelArtifact } from "./pooledEmpiricalModel"

export const E_DISPO_V4_MODEL_ID = "e-dispo-v4.0" as const
export const E_DISPO_V4_1_PAS5_MODEL_ID =
  "e-dispo-v4.1-pas5-high-acuity-surrogate" as const

const limitationNote =
  "Dataset-derived from pooled NHAMCS 2018-2022 severe-only pain refit for educational use only; not clinical decision support."
const pas5V41LimitationNote =
  "Dataset-derived from pooled NHAMCS 2018-2022 PAS-5/IMMEDR complete-case refit for educational use only; not clinical decision support."
const pas5SurrogateLimitation =
  "Direct PAS-5 patient answers are not observed in NHAMCS."

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
  performance_intervals: [
    {
      ci_high: 0.757748157327689,
      ci_low: 0.670617442965302,
      estimate: 0.713095417183504,
      interval_level: 0.95,
      limitation:
        "Design-aware apparent interval using pooled NHAMCS survey bootstrap replicate weights and fixed fitted-model predictions. It does not refit the model, correct optimism, validate externally, or prove transportability.",
      method: "survey_bootstrap_replicate_weights_fixed_apparent_predictions",
      metric: "auroc",
      status: "ok",
    },
    {
      ci_high: 0.111065781877554,
      ci_low: 0.0846318005776967,
      estimate: 0.0976402591025939,
      interval_level: 0.95,
      limitation:
        "Design-aware apparent interval using pooled NHAMCS survey bootstrap replicate weights and fixed fitted-model predictions. It does not refit the model, correct optimism, validate externally, or prove transportability.",
      method: "survey_bootstrap_replicate_weights_fixed_apparent_predictions",
      metric: "brier_score",
      status: "ok",
    },
  ],
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
  validation_artifact_paths: {
    calibration_by_decile:
      "outputs/nhamcs_pooled/e_dispo_v4_pain_severe_calibration_by_decile.csv",
    calibration_plot_data:
      "outputs/nhamcs_pooled/e_dispo_v4_pain_severe_calibration_plot_data.csv",
    candidate_refinement_gate:
      "outputs/nhamcs_pooled/e_dispo_v4_candidate_refinement_gate.csv",
    full_source_endpoint_screen_calibration:
      "outputs/nhamcs_pooled/e_dispo_v4_full_source_endpoint_screen_calibration.csv",
    full_source_endpoint_screen_missingness:
      "outputs/nhamcs_pooled/e_dispo_v4_full_source_endpoint_screen_missingness.csv",
    full_source_endpoint_screen_performance:
      "outputs/nhamcs_pooled/e_dispo_v4_full_source_endpoint_screen_performance.csv",
    full_source_nontrauma_screen_calibration:
      "outputs/nhamcs_pooled/e_dispo_v4_full_source_nontrauma_screen_calibration.csv",
    full_source_nontrauma_screen_missingness:
      "outputs/nhamcs_pooled/e_dispo_v4_full_source_nontrauma_screen_missingness.csv",
    full_source_nontrauma_screen_performance:
      "outputs/nhamcs_pooled/e_dispo_v4_full_source_nontrauma_screen_performance.csv",
    full_source_scope_screen_report:
      "outputs/nhamcs_pooled/e_dispo_v4_full_source_scope_screen_report.md",
    missingness_performance:
      "outputs/nhamcs_pooled/e_dispo_v4_missingness_performance.csv",
    optimism_corrected_performance:
      "outputs/nhamcs_pooled/e_dispo_v4_optimism_corrected_performance.csv",
    performance_intervals:
      "outputs/nhamcs_pooled/e_dispo_v4_pain_severe_performance_intervals.csv",
    subgroup_calibration:
      "outputs/nhamcs_pooled/e_dispo_v4_subgroup_calibration.csv",
    subgroup_performance:
      "outputs/nhamcs_pooled/e_dispo_v4_subgroup_performance.csv",
    transportability_track:
      "outputs/nhamcs_pooled/e_dispo_v4_transportability_track.csv",
  },
}

export const eDispoV41Pas5Model: PooledEmpiricalModelArtifact = {
  ...eDispoV4Model,
  calibration: {
    auroc: 0.759077823237526,
    brier_score: 0.091311819980443,
    intercept: 1.60148283523398e-11,
    mean_predicted: 0.113520799126063,
    observed_prevalence: 0.113520799110049,
    slope: 1.00000000017151,
  },
  cohort_counts: {
    MIMIC_IV_ED: eDispoV4Model.cohort_counts.MIMIC_IV_ED,
    NHAMCS_2018_2022_POOLED: {
      admission_events: 459,
      event_count_gate_passed: true,
      model_fit_admission_events: 254,
      model_fit_complete_case_n: 2245,
      strict_binary_unweighted_n: 3805,
      weighted_admission_prevalence: 0.113520799110049,
    },
  },
  covariance_matrix_path: "outputs/nhamcs_pooled/pas5_acuity_covariance.csv",
  generated_at: "2026-05-04T00:00:00Z",
  model_id: E_DISPO_V4_1_PAS5_MODEL_ID,
  model_version: "e_dispo_v4_1_pas5_high_acuity_surrogate_20260504",
  performance_intervals: undefined,
  posterior_draws_path: "outputs/nhamcs_pooled/pas5_acuity_draws_app.csv",
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
    {
      blockers: "",
      evidence_tier: "dataset_derived_surrogate",
      level: "1",
      surrogate_limitation: pas5SurrogateLimitation,
      surrogate_source: "NHAMCS_IMMEDR",
      term: "high_acuity_proxy",
    },
  ],
  predictors: [
    {
      center_beta: -2.76223123530477,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "",
      limitation_note: pas5V41LimitationNote,
      reference: false,
      se_or_sd: 0.218351002600885,
      source: "NHAMCS_2018_2022_POOLED",
      term: "intercept",
    },
    {
      center_beta: 0.0450480147935024,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "per_1_year_centered_at_42",
      limitation_note: pas5V41LimitationNote,
      reference: false,
      se_or_sd: 0.00766744605803709,
      source: "NHAMCS_2018_2022_POOLED",
      term: "age_centered",
    },
    {
      center_beta: 0.556443332598118,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "1",
      limitation_note:
        "Dataset-derived severe-vs-non-severe pain term from the v4.1 PAS-5/IMMEDR complete-case refit. Mild and moderate remain collapsed; this is not a monotonic pain dose-response claim.",
      reference: false,
      se_or_sd: 0.205014382183013,
      source: "NHAMCS_2018_2022_POOLED",
      term: "pain_severe",
    },
    {
      center_beta: 0.994381942387039,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "1",
      limitation_note: pas5V41LimitationNote,
      reference: false,
      se_or_sd: 0.822770325700071,
      source: "NHAMCS_2018_2022_POOLED",
      term: "fever_or_temp",
    },
    {
      center_beta: 0.431253333679371,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "1",
      limitation_note: pas5V41LimitationNote,
      reference: false,
      se_or_sd: 0.211880868628859,
      source: "NHAMCS_2018_2022_POOLED",
      term: "vomiting_present",
    },
    {
      center_beta: 0.456426837475548,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived",
      level: "per_10_bpm_over_100",
      limitation_note: pas5V41LimitationNote,
      reference: false,
      se_or_sd: 0.12186294639143,
      source: "NHAMCS_2018_2022_POOLED",
      term: "tachycardia_burden",
    },
    {
      center_beta: 1.24984421126593,
      distribution: "normal_approximation_exploratory",
      evidence_tier: "dataset_derived_surrogate",
      level: "1",
      limitation_note:
        "PAS-5 A1/A2 high-acuity proxy fitted through NHAMCS IMMEDR clinician-acuity surrogate evidence. Direct PAS-5 patient answers are not observed in NHAMCS; this does not validate PAS-5 as triage, medical advice, clinical decision support, or direct patient self-assessment accuracy.",
      reference: false,
      se_or_sd: 0.315343146380296,
      source: "NHAMCS_2018_2022_POOLED",
      surrogate_limitation: pas5SurrogateLimitation,
      surrogate_source: "NHAMCS_IMMEDR",
      term: "high_acuity_proxy",
    },
  ],
  run_id: "e_dispo_v4_1_pas5_high_acuity_surrogate_20260504",
  validation_artifact_paths: {
    calibration_by_decile:
      "outputs/nhamcs_pooled/pas5_acuity_decile_calibration.csv",
    calibration_plot_data: "outputs/nhamcs_pooled/pas5_acuity_calibration.csv",
    pas5_calibration: "outputs/nhamcs_pooled/pas5_acuity_calibration.csv",
    pas5_cell_counts: "outputs/nhamcs_pooled/pas5_acuity_cell_counts.csv",
    pas5_coefficients: "outputs/nhamcs_pooled/pas5_acuity_coefficients.csv",
    pas5_covariance: "outputs/nhamcs_pooled/pas5_acuity_covariance.csv",
    pas5_decile_calibration:
      "outputs/nhamcs_pooled/pas5_acuity_decile_calibration.csv",
    pas5_draws_app: "outputs/nhamcs_pooled/pas5_acuity_draws_app.csv",
    pas5_draws_long: "outputs/nhamcs_pooled/pas5_acuity_draws_long.csv",
    pas5_gate_decision:
      "outputs/nhamcs_pooled/pas5_acuity_gate_decision.csv",
    pas5_leave_one_year_out:
      "outputs/nhamcs_pooled/pas5_acuity_leave_one_year_out.csv",
    pas5_mapping: "outputs/nhamcs_pooled/pas5_acuity_mapping.csv",
    pas5_missingness: "outputs/nhamcs_pooled/pas5_acuity_missingness.csv",
    pas5_report: "outputs/nhamcs_pooled/pas5_acuity_report.md",
  },
}

export const activeEmpiricalModel = eDispoV41Pas5Model
