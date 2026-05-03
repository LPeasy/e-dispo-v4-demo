#!/usr/bin/env Rscript

# User-feasible NHAMCS candidate screen for nausea-alone.
#
# This script does not activate a new app model. It compares the active
# e-dispo-v4.0 model shape against the same rows plus a single structured
# NHAMCS RFV candidate: nausea_present = 1[RFV1-RFV5 contains 15250].

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: nhamcs_nausea_candidate_screen.R <pooled_analytic_cohort_csv> <output_dir>")
}

script_file <- grep("^--file=", commandArgs(FALSE), value = TRUE)
script_dir <- getwd()
if (length(script_file) > 0) {
  script_dir <- dirname(normalizePath(sub("^--file=", "", script_file[[1]]), winslash = "/"))
}

input_path <- args[[1]]
output_dir <- args[[2]]
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

source(file.path(script_dir, "r_environment.R"))
nhamcs_configure_r_environment()
nhamcs_write_r_environment_report(output_dir, required_packages = c("survey"))
if (!requireNamespace("survey", quietly = TRUE)) {
  stop("R package 'survey' is required. Set NHAMCS_R_LIBS or install survey into an active R library.")
}

options(survey.lonely.psu = "adjust")

DATASET <- "NHAMCS_2018_2022_POOLED"
BASE_MODEL_ID <- "e_dispo_v4_base_refit_for_nausea_screen"
CANDIDATE_MODEL_ID <- "e_dispo_v4_plus_nausea_candidate"
AGE_CENTER <- 42
SEED <- 20260501L
DRAW_COUNT <- 10000L
MIN_POSITIVE_N <- 30L
MIN_POSITIVE_EVENTS <- 10L
MIN_POSITIVE_NONEVENTS <- 10L
MIN_DIRECTION_PROBABILITY <- 0.95
MAX_BRIER_WORSENING <- 0.002
MAX_AUROC_WORSENING <- 0.01
set.seed(SEED)

truthy <- function(value) tolower(trimws(as.character(value))) %in% c("true", "1", "yes")

weighted_mean <- function(value, weight) {
  valid <- !is.na(value) & !is.na(weight)
  if (!any(valid) || sum(weight[valid]) == 0) return(NA_real_)
  sum(value[valid] * weight[valid]) / sum(weight[valid])
}

logit <- function(value) {
  clipped <- pmin(pmax(value, 1e-6), 1 - 1e-6)
  log(clipped / (1 - clipped))
}

weighted_auc <- function(y, predicted, weight) {
  positive <- which(y == 1)
  negative <- which(y == 0)
  if (length(positive) == 0 || length(negative) == 0) return(NA_real_)
  comparisons <- outer(predicted[positive], predicted[negative], "-")
  weight_pairs <- outer(weight[positive], weight[negative], "*")
  numerator <- sum(weight_pairs[comparisons > 0]) + 0.5 * sum(weight_pairs[comparisons == 0])
  numerator / (sum(weight[positive]) * sum(weight[negative]))
}

status_is_pass <- function(status) startsWith(as.character(status), "pass")

calibration_status <- function(slope, observed, predicted, events) {
  if (events < 100) return("survey_weighted_candidate_exploratory_event_count_lt_100")
  if (is.na(slope)) return("fail_calibration_unavailable")
  absolute_gap <- abs(predicted - observed)
  relative_gap <- absolute_gap / max(observed, 1e-6)
  if (absolute_gap > 0.02 || relative_gap > 0.10) return("fail_recalibrate_intercept")
  if (slope < 0.8) return("fail_likely_overfit")
  if (slope > 1.2) return("fail_likely_underfit")
  "pass_candidate_range"
}

format_number <- function(value, digits = 4) {
  if (!is.finite(value)) return("NA")
  format(round(value, digits), nsmall = digits, trim = TRUE)
}

parse_coefficient <- function(name) {
  if (identical(name, "(Intercept)")) return(list(term = "intercept", level = ""))
  if (identical(name, "age_centered")) return(list(term = "age_centered", level = "per_1_year_centered_at_42"))
  if (identical(name, "pain_severe")) return(list(term = "pain_severe", level = "1"))
  if (identical(name, "fever_or_temp")) return(list(term = "fever_or_temp", level = "1"))
  if (identical(name, "vomiting_present")) return(list(term = "vomiting_present", level = "1"))
  if (identical(name, "tachycardia_burden")) return(list(term = "tachycardia_burden", level = "per_10_bpm_over_100"))
  if (identical(name, "nausea_present")) return(list(term = "nausea_present", level = "1"))
  list(term = name, level = "")
}

coefficient_label <- function(parsed) {
  if (identical(parsed$level, "")) parsed$term else paste0(parsed$term, "[", parsed$level, "]")
}

nearest_stable_covariance <- function(covariance) {
  symmetric <- (covariance + t(covariance)) / 2
  eigen_result <- eigen(symmetric, symmetric = TRUE)
  values <- pmax(eigen_result$values, 1e-10)
  eigen_result$vectors %*% diag(values, nrow = length(values)) %*% t(eigen_result$vectors)
}

mvn_draws <- function(model_id, beta, covariance, parsed_terms) {
  stable <- nearest_stable_covariance(covariance)
  eigen_result <- eigen(stable, symmetric = TRUE)
  values <- pmax(eigen_result$values, 1e-10)
  root <- eigen_result$vectors %*% diag(sqrt(values), nrow = length(values))
  z <- matrix(stats::rnorm(DRAW_COUNT * length(beta)), nrow = DRAW_COUNT, ncol = length(beta))
  draws <- sweep(z %*% t(root), 2, beta, "+")
  term_names <- vapply(parsed_terms, function(item) item$term, character(1))
  levels <- vapply(parsed_terms, function(item) item$level, character(1))
  data.frame(
    model_id = model_id,
    dataset = DATASET,
    draw_id = rep(seq_len(DRAW_COUNT), each = length(beta)),
    term = rep(term_names, times = DRAW_COUNT),
    level = rep(levels, times = DRAW_COUNT),
    beta = as.numeric(t(draws)),
    seed = SEED,
    stringsAsFactors = FALSE
  )
}

fit_model <- function(model_id, formula, frame) {
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = frame)
  fit <- survey::svyglm(formula, design = design, family = quasibinomial())
  beta <- stats::coef(fit)
  covariance <- stats::vcov(fit)
  se <- sqrt(pmax(diag(covariance), 0))
  coef_table <- summary(fit)$coefficients
  parsed_terms <- lapply(names(beta), parse_coefficient)
  labels <- vapply(parsed_terms, coefficient_label, character(1))
  predicted <- as.numeric(stats::predict(fit, type = "response"))
  frame$.__linear_prediction <- logit(predicted)
  calibration_design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = frame)
  intercept_fit <- survey::svyglm(admit ~ 1 + offset(.__linear_prediction), design = calibration_design, family = quasibinomial())
  slope_fit <- survey::svyglm(admit ~ .__linear_prediction, design = calibration_design, family = quasibinomial())
  events <- sum(frame$admit == 1)
  observed <- weighted_mean(frame$admit, frame$weight)
  mean_predicted <- weighted_mean(predicted, frame$weight)
  slope <- as.numeric(stats::coef(slope_fit)[[".__linear_prediction"]])

  coefficients <- data.frame(
    model_id = model_id,
    dataset = DATASET,
    term = vapply(parsed_terms, function(item) item$term, character(1)),
    level = vapply(parsed_terms, function(item) item$level, character(1)),
    beta = as.numeric(beta),
    se = as.numeric(se),
    odds_ratio = exp(as.numeric(beta)),
    ci_low = exp(as.numeric(beta) - 1.96 * as.numeric(se)),
    ci_high = exp(as.numeric(beta) + 1.96 * as.numeric(se)),
    p_value = as.numeric(coef_table[, ncol(coef_table)]),
    evidence_tier = "survey_weighted_candidate",
    limitation_note = "Nausea-alone candidate screen only; not active in e-dispo-v4.0 and not clinical decision support.",
    stringsAsFactors = FALSE
  )

  covariance_rows <- data.frame()
  for (row_index in seq_along(labels)) {
    for (column_index in seq_along(labels)) {
      covariance_rows <- rbind(covariance_rows, data.frame(
        model_id = model_id,
        dataset = DATASET,
        row_term = labels[[row_index]],
        column_term = labels[[column_index]],
        covariance = covariance[row_index, column_index],
        stringsAsFactors = FALSE
      ))
    }
  }

  calibration <- data.frame(
    model_id = model_id,
    dataset = DATASET,
    n = nrow(frame),
    events = events,
    observed_prevalence = observed,
    mean_predicted = mean_predicted,
    calibration_in_the_large = as.numeric(stats::coef(intercept_fit)[[1]]),
    calibration_slope = slope,
    brier_score = weighted_mean((predicted - frame$admit) ^ 2, frame$weight),
    auroc = weighted_auc(frame$admit, predicted, frame$weight),
    pass_fail_status = calibration_status(slope, observed, mean_predicted, events),
    stringsAsFactors = FALSE
  )

  list(
    fit = fit,
    coefficients = coefficients,
    covariance = covariance_rows,
    draws = mvn_draws(model_id, beta, covariance, parsed_terms),
    calibration = calibration
  )
}

predict_heldout <- function(model_id, formula, train, test) {
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = train)
  fit <- survey::svyglm(formula, design = design, family = quasibinomial())
  beta <- stats::coef(fit)
  covariance <- stats::vcov(fit)
  predicted <- as.numeric(stats::predict(fit, newdata = test, type = "response"))
  nausea_beta <- if ("nausea_present" %in% names(beta)) as.numeric(beta[["nausea_present"]]) else NA_real_
  nausea_se <- if ("nausea_present" %in% rownames(covariance)) sqrt(max(covariance["nausea_present", "nausea_present"], 0)) else NA_real_

  data.frame(
    heldout_year = unique(test$year)[[1]],
    model_id = model_id,
    dataset = DATASET,
    train_n = nrow(train),
    train_events = sum(train$admit == 1),
    train_nausea_positive_n = sum(train$nausea_present == 1),
    train_nausea_positive_events = sum(train$admit == 1 & train$nausea_present == 1),
    train_nausea_positive_non_events = sum(train$admit == 0 & train$nausea_present == 1),
    heldout_n = nrow(test),
    heldout_events = sum(test$admit == 1),
    brier_score = weighted_mean((predicted - test$admit) ^ 2, test$weight),
    auroc = weighted_auc(test$admit, predicted, test$weight),
    observed_prevalence = weighted_mean(test$admit, test$weight),
    mean_predicted = weighted_mean(predicted, test$weight),
    nausea_beta = nausea_beta,
    nausea_or = if (is.finite(nausea_beta)) exp(nausea_beta) else NA_real_,
    nausea_ci_low = if (is.finite(nausea_beta) && is.finite(nausea_se)) exp(nausea_beta - 1.96 * nausea_se) else NA_real_,
    nausea_ci_high = if (is.finite(nausea_beta) && is.finite(nausea_se)) exp(nausea_beta + 1.96 * nausea_se) else NA_real_,
    stringsAsFactors = FALSE
  )
}

cohort <- read.csv(input_path, stringsAsFactors = FALSE, na.strings = c("", "NA", "NaN"))
if ("dataset" %in% names(cohort) && length(unique(cohort$dataset[!is.na(cohort$dataset)])) > 0) {
  DATASET <- unique(cohort$dataset[!is.na(cohort$dataset)])[[1]]
}

if (!"nausea_present" %in% names(cohort)) {
  rfv_columns <- intersect(c("RFV1", "RFV2", "RFV3", "RFV4", "RFV5"), names(cohort))
  if (length(rfv_columns) == 0) {
    stop("Missing nausea_present and RFV1-RFV5. Rebuild the pooled NHAMCS cohort with the updated cohort builder.")
  }
  cohort$nausea_present <- as.numeric(apply(cohort[rfv_columns], 1, function(row) any(trimws(as.character(row)) == "15250")))
}

required <- c("include_strict_binary", "admit", "year", "age", "pain_bin3", "pain_missing",
              "fever_or_temp", "vomiting_present", "HR", "tachycardia_burden", "nausea_present",
              "pooled_weight", "pooled_stratum", "pooled_psu")
missing_required <- setdiff(required, names(cohort))
if (length(missing_required) > 0) {
  stop(paste("Missing required columns:", paste(missing_required, collapse = ", ")))
}

binary <- cohort[truthy(cohort$include_strict_binary), , drop = FALSE]
if (nrow(binary) == 0) stop("Strict binary analytic cohort is empty.")
binary$admit <- as.numeric(binary$admit)
binary$year <- as.integer(binary$year)
binary$age <- as.numeric(binary$age)
binary$age_centered <- binary$age - AGE_CENTER
binary$weight <- as.numeric(binary$pooled_weight)
binary$stratum <- as.factor(binary$pooled_stratum)
binary$psu <- as.factor(binary$pooled_psu)
binary$pain_missing <- as.numeric(binary$pain_missing)
binary$fever_or_temp <- as.numeric(binary$fever_or_temp)
binary$vomiting_present <- as.numeric(binary$vomiting_present)
binary$HR <- as.numeric(binary$HR)
binary$tachycardia_burden <- as.numeric(binary$tachycardia_burden)
binary$nausea_present <- as.numeric(binary$nausea_present)
if (!"endpoint_class" %in% names(binary)) {
  binary$endpoint_class <- ifelse(binary$admit == 1, "admit", "routine_home_discharge")
}

binary <- binary[!is.na(binary$admit) & binary$admit %in% c(0, 1) &
  !is.na(binary$year) & !is.na(binary$age_centered) &
  !is.na(binary$weight) & binary$weight > 0 &
  !is.na(binary$stratum) & !is.na(binary$psu), , drop = FALSE]

complete_case <- binary[binary$pain_missing == 0 &
  !is.na(binary$pain_bin3) & !is.na(binary$fever_or_temp) &
  !is.na(binary$vomiting_present) & !is.na(binary$HR) &
  !is.na(binary$tachycardia_burden) & !is.na(binary$nausea_present), , drop = FALSE]
if (nrow(complete_case) == 0 || length(unique(complete_case$admit)) < 2) {
  stop("No usable paired complete-case rows with outcome variation for nausea candidate screen.")
}
complete_case$pain_bin3 <- as.factor(complete_case$pain_bin3)
complete_case$pain_severe <- as.numeric(as.character(complete_case$pain_bin3) == "severe")
complete_case$nausea_present <- as.numeric(complete_case$nausea_present == 1)
complete_case$vomiting_present <- as.numeric(complete_case$vomiting_present == 1)
complete_case$fever_or_temp <- as.numeric(complete_case$fever_or_temp == 1)

mapping_audit <- data.frame(
  dataset = DATASET,
  field = c("nausea_present", "vomiting_present"),
  source_column = c("RFV1-RFV5", "RFV1-RFV5"),
  stored_code = c("15250", "15300"),
  codebook_label = c("Nausea", "Vomiting"),
  role = c("new user-feasible candidate", "active base-model symptom"),
  review_status = c("confirmed_codebook", "confirmed_codebook"),
  notes = c(
    "Nausea-alone is separate from ordinary vomiting and is not counted as vomiting.",
    "Ordinary vomiting remains active as vomiting_present; nausea-alone is tested only as an added candidate."
  ),
  stringsAsFactors = FALSE
)

missingness_rows <- data.frame()
for (endpoint in sort(unique(binary$endpoint_class))) {
  endpoint_rows <- binary[binary$endpoint_class == endpoint, , drop = FALSE]
  for (field in c("pain_bin3", "fever_or_temp", "vomiting_present", "HR", "tachycardia_burden", "nausea_present")) {
    missing <- is.na(endpoint_rows[[field]])
    missingness_rows <- rbind(missingness_rows, data.frame(
      dataset = DATASET,
      field = field,
      endpoint = endpoint,
      n = nrow(endpoint_rows),
      missing_n = sum(missing),
      missing_pct = if (nrow(endpoint_rows) > 0) sum(missing) / nrow(endpoint_rows) else NA_real_,
      weighted_n = sum(endpoint_rows$weight),
      weighted_missing_n = sum(endpoint_rows$weight[missing]),
      weighted_missing_pct = if (sum(endpoint_rows$weight) > 0) sum(endpoint_rows$weight[missing]) / sum(endpoint_rows$weight) else NA_real_,
      stringsAsFactors = FALSE
    ))
  }
}

cell_counts <- data.frame()
for (year_label in c(sort(unique(as.character(complete_case$year))), "pooled")) {
  part <- if (identical(year_label, "pooled")) complete_case else complete_case[as.character(complete_case$year) == year_label, , drop = FALSE]
  for (level in c(0, 1)) {
    subset <- part[part$nausea_present == level, , drop = FALSE]
    cell_counts <- rbind(cell_counts, data.frame(
      dataset = DATASET,
      model_id = CANDIDATE_MODEL_ID,
      year = year_label,
      group = "nausea_present",
      level = as.character(level),
      n = nrow(subset),
      events = sum(subset$admit == 1),
      non_events = sum(subset$admit == 0),
      weighted_n = sum(subset$weight),
      weighted_events = sum(subset$weight[subset$admit == 1]),
      weighted_admit_rate = weighted_mean(subset$admit, subset$weight),
      stringsAsFactors = FALSE
    ))
  }
}

base_formula <- admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden
candidate_formula <- admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden + nausea_present
base_fit <- fit_model(BASE_MODEL_ID, base_formula, complete_case)
candidate_fit <- fit_model(CANDIDATE_MODEL_ID, candidate_formula, complete_case)

coefficients <- rbind(base_fit$coefficients, candidate_fit$coefficients)
covariance <- rbind(base_fit$covariance, candidate_fit$covariance)
draws <- rbind(base_fit$draws, candidate_fit$draws)
calibration <- rbind(base_fit$calibration, candidate_fit$calibration)

leave_one_year_out <- data.frame()
for (heldout_year in sort(unique(complete_case$year))) {
  train <- complete_case[complete_case$year != heldout_year, , drop = FALSE]
  test <- complete_case[complete_case$year == heldout_year, , drop = FALSE]
  leave_one_year_out <- rbind(
    leave_one_year_out,
    predict_heldout(BASE_MODEL_ID, base_formula, train, test),
    predict_heldout(CANDIDATE_MODEL_ID, candidate_formula, train, test)
  )
}

coefficient_row <- coefficients[coefficients$model_id == CANDIDATE_MODEL_ID & coefficients$term == "nausea_present", , drop = FALSE]
nausea_draws <- draws[draws$model_id == CANDIDATE_MODEL_ID & draws$term == "nausea_present", , drop = FALSE]
base_calibration <- calibration[calibration$model_id == BASE_MODEL_ID, , drop = FALSE]
candidate_calibration <- calibration[calibration$model_id == CANDIDATE_MODEL_ID, , drop = FALSE]
base_loo <- leave_one_year_out[leave_one_year_out$model_id == BASE_MODEL_ID, , drop = FALSE]
candidate_loo <- leave_one_year_out[leave_one_year_out$model_id == CANDIDATE_MODEL_ID, , drop = FALSE]
merged_loo <- merge(base_loo, candidate_loo, by = "heldout_year", suffixes = c("_base", "_candidate"), sort = TRUE)

pooled_counts <- cell_counts[cell_counts$year == "pooled" & cell_counts$level == "1", , drop = FALSE]
pooled_nausea_positive_n <- if (nrow(pooled_counts) > 0) pooled_counts$n[[1]] else 0
pooled_nausea_positive_events <- if (nrow(pooled_counts) > 0) pooled_counts$events[[1]] else 0
pooled_nausea_positive_nonevents <- if (nrow(pooled_counts) > 0) pooled_counts$non_events[[1]] else 0

nausea_beta <- if (nrow(coefficient_row) > 0) coefficient_row$beta[[1]] else NA_real_
pooled_direction <- if (is.finite(nausea_beta) && nausea_beta != 0) sign(nausea_beta) else 0
direction_probability <- if (pooled_direction > 0) {
  mean(nausea_draws$beta > 0)
} else if (pooled_direction < 0) {
  mean(nausea_draws$beta < 0)
} else {
  NA_real_
}

apparent_brier_worsening <- candidate_calibration$brier_score[[1]] - base_calibration$brier_score[[1]]
apparent_auroc_change <- candidate_calibration$auroc[[1]] - base_calibration$auroc[[1]]
heldout_brier_worsening <- if (nrow(merged_loo) > 0) weighted_mean(merged_loo$brier_score_candidate - merged_loo$brier_score_base, merged_loo$heldout_n_base) else NA_real_
heldout_auroc_change <- if (nrow(merged_loo) > 0) weighted_mean(merged_loo$auroc_candidate - merged_loo$auroc_base, merged_loo$heldout_n_base) else NA_real_

mapping_gate <- all(complete_case$nausea_present %in% c(0, 1)) && all(complete_case$vomiting_present %in% c(0, 1))
sparse_cell_gate <- pooled_nausea_positive_n >= MIN_POSITIVE_N &&
  pooled_nausea_positive_events >= MIN_POSITIVE_EVENTS &&
  pooled_nausea_positive_nonevents >= MIN_POSITIVE_NONEVENTS
coefficient_gate <- is.finite(nausea_beta) && pooled_direction != 0
uncertainty_gate <- nrow(coefficient_row) == 1 &&
  nrow(covariance[covariance$model_id == CANDIDATE_MODEL_ID, , drop = FALSE]) > 0 &&
  length(unique(nausea_draws$draw_id)) == DRAW_COUNT &&
  is.finite(direction_probability) && direction_probability >= MIN_DIRECTION_PROBABILITY
loo_stability_gate <- nrow(candidate_loo) == length(unique(complete_case$year)) &&
  all(is.finite(candidate_loo$nausea_beta)) &&
  all(sign(candidate_loo$nausea_beta) == pooled_direction) &&
  all(candidate_loo$train_nausea_positive_events >= MIN_POSITIVE_EVENTS, na.rm = FALSE) &&
  all(candidate_loo$train_nausea_positive_non_events >= MIN_POSITIVE_NONEVENTS, na.rm = FALSE)
calibration_no_harm_gate <- status_is_pass(base_calibration$pass_fail_status[[1]]) &&
  status_is_pass(candidate_calibration$pass_fail_status[[1]]) &&
  is.finite(apparent_brier_worsening) && apparent_brier_worsening <= MAX_BRIER_WORSENING &&
  is.finite(apparent_auroc_change) && apparent_auroc_change >= -MAX_AUROC_WORSENING &&
  is.finite(heldout_brier_worsening) && heldout_brier_worsening <= MAX_BRIER_WORSENING &&
  is.finite(heldout_auroc_change) && heldout_auroc_change >= -MAX_AUROC_WORSENING

all_gates <- mapping_gate && sparse_cell_gate && coefficient_gate && uncertainty_gate && loo_stability_gate && calibration_no_harm_gate
candidate_status <- if (all_gates) "eligible_for_future_model_consideration_not_active" else "blocked_recommend_new_data_source"
decision_reason <- if (all_gates) {
  "Nausea-alone passed the prespecified user-feasible NHAMCS gates, but this screen does not activate a model."
} else {
  "Nausea-alone did not pass every prespecified gate; no additional user-feasible NHAMCS symptom passed, so broader discovery requires a new data source."
}

gate_rows <- data.frame(
  gate = c(
    "mapping_documented",
    "sparse_cell_adequacy",
    "coefficient_direction_defined",
    "uncertainty_exported",
    "leave_one_year_out_direction_stability",
    "calibration_no_material_harm",
    "active_model_unchanged",
    "final_candidate_usefulness"
  ),
  passed = c(mapping_gate, sparse_cell_gate, coefficient_gate, uncertainty_gate, loo_stability_gate, calibration_no_harm_gate, TRUE, all_gates),
  status = c(
    ifelse(mapping_gate, "pass", "fail"),
    ifelse(sparse_cell_gate, "pass", "fail"),
    ifelse(coefficient_gate, "pass", "fail"),
    ifelse(uncertainty_gate, "pass", "fail"),
    ifelse(loo_stability_gate, "pass", "fail"),
    ifelse(calibration_no_harm_gate, "pass", "fail"),
    "pass_no_app_export_or_activation",
    candidate_status
  ),
  metric = c(
    sum(complete_case$nausea_present == 1),
    pooled_nausea_positive_events,
    nausea_beta,
    direction_probability,
    if (nrow(candidate_loo) > 0) min(abs(candidate_loo$nausea_beta), na.rm = TRUE) else NA_real_,
    apparent_brier_worsening,
    NA_real_,
    NA_real_
  ),
  threshold = c(
    "nausea_present and vomiting_present are separate binary RFV fields",
    paste0("n >= ", MIN_POSITIVE_N, "; events >= ", MIN_POSITIVE_EVENTS, "; non-events >= ", MIN_POSITIVE_NONEVENTS),
    "finite nonzero pooled coefficient",
    paste0("draws=", DRAW_COUNT, "; Pr(direction) >= ", MIN_DIRECTION_PROBABILITY),
    "all LOO nausea betas share pooled direction and train splits pass event counts",
    paste0("Brier worsening <= ", MAX_BRIER_WORSENING, "; AUROC change >= -", MAX_AUROC_WORSENING),
    "do not write app export, active artifact, schema activation, or UI change",
    "all gates pass"
  ),
  notes = c(
    "RFV 15250 is nausea-alone; RFV 15300 remains ordinary vomiting.",
    paste0("pooled nausea n=", pooled_nausea_positive_n, ", events=", pooled_nausea_positive_events, ", non-events=", pooled_nausea_positive_nonevents),
    if (nrow(coefficient_row) > 0) paste0("beta=", signif(nausea_beta, 6), ", OR=", signif(coefficient_row$odds_ratio[[1]], 6)) else "nausea coefficient unavailable",
    paste0("nausea draws=", length(unique(nausea_draws$draw_id)), ", direction probability=", signif(direction_probability, 6)),
    if (nrow(candidate_loo) > 0) paste0("finite stable-direction years=", sum(is.finite(candidate_loo$nausea_beta) & sign(candidate_loo$nausea_beta) == pooled_direction), "/", nrow(candidate_loo)) else "LOO rows unavailable",
    paste0("apparent delta Brier=", signif(apparent_brier_worsening, 6), "; apparent delta AUROC=", signif(apparent_auroc_change, 6), "; LOO delta Brier=", signif(heldout_brier_worsening, 6), "; LOO delta AUROC=", signif(heldout_auroc_change, 6)),
    "This analysis is a ranking screen only.",
    decision_reason
  ),
  evidence_tier = "survey_weighted_candidate",
  stringsAsFactors = FALSE
)

ranked_decision <- data.frame(
  rank = 1,
  candidate_variable = "nausea_present",
  user_feasible = TRUE,
  status = candidate_status,
  recommended_for_active_model_change = FALSE,
  evidence_tier = "survey_weighted_candidate",
  reason = decision_reason,
  stringsAsFactors = FALSE
)

base_formula_text <- gsub("\\s+", " ", paste(deparse(base_formula), collapse = " "))
candidate_formula_text <- gsub("\\s+", " ", paste(deparse(candidate_formula), collapse = " "))
run_metadata <- data.frame(
  model_id = c(BASE_MODEL_ID, CANDIDATE_MODEL_ID),
  dataset = DATASET,
  formula = c(base_formula_text, candidate_formula_text),
  fitting_method = "survey::svyglm quasibinomial; ids=psu; strata=stratum; weights=weight; nest=TRUE",
  complete_case_policy = "Strict binary cohort with observed pain_bin3, fever_or_temp, vomiting_present, HR, tachycardia_burden, nausea_present, positive pooled weight, stratum, and PSU.",
  age_transform = paste0("age_centered = age - ", AGE_CENTER),
  pain_transform = "pain_severe = 1[pain_bin3 == severe]; mild and moderate are the non-severe reference; pain_missing excluded.",
  fever_transform = "fever_or_temp = 1 when fever/temperature proxy is present; 0 reference is not documented by the mapped field.",
  vomiting_transform = "vomiting_present = 1[RFV1-RFV5 contains 15300]; 0 reference is not documented in RFV1-RFV5.",
  tachycardia_transform = "tachycardia_burden = max(HR - 100, 0) / 10",
  nausea_transform = "nausea_present = 1[RFV1-RFV5 contains 15250]; separate from ordinary vomiting code 15300.",
  reference_categories = c(
    "non-severe pain; no fever/temp proxy; no ordinary vomiting; tachycardia_burden 0",
    "non-severe pain; no fever/temp proxy; no ordinary vomiting; tachycardia_burden 0; no nausea-alone"
  ),
  seed = SEED,
  draw_count = DRAW_COUNT,
  r_version = R.version.string,
  survey_package_version = as.character(utils::packageVersion("survey")),
  evidence_tier = "survey_weighted_candidate",
  active_model_change = FALSE,
  stringsAsFactors = FALSE
)

report <- c(
  "# NHAMCS Nausea-Alone Candidate Screen",
  "",
  "This report covers an educational/statistical ED disposition model. It is not clinical decision support.",
  "",
  "## Intent",
  "Rank whether a single additional user-feasible structured NHAMCS symptom, nausea-alone, should be considered for a future model version. The active `e-dispo-v4.0` app model is unchanged.",
  "",
  "## Model Comparison",
  paste0("- Base formula: `", base_formula_text, "`."),
  paste0("- Candidate formula: `", candidate_formula_text, "`."),
  "- Paired-row policy: base and candidate were fit on the same complete-case rows.",
  "- Nausea mapping: `nausea_present = 1[RFV1-RFV5 contains 15250]`; ordinary vomiting remains `vomiting_present = 1[RFV1-RFV5 contains 15300]`.",
  "",
  "## Performance",
  paste0("- Base AUROC/Brier: ", format_number(base_calibration$auroc[[1]], 6), " / ", format_number(base_calibration$brier_score[[1]], 6), "."),
  paste0("- Candidate AUROC/Brier: ", format_number(candidate_calibration$auroc[[1]], 6), " / ", format_number(candidate_calibration$brier_score[[1]], 6), "."),
  paste0("- Apparent delta AUROC/Brier: ", format_number(apparent_auroc_change, 6), " / ", format_number(apparent_brier_worsening, 6), "."),
  paste0("- Leave-one-year-out mean delta AUROC/Brier: ", format_number(heldout_auroc_change, 6), " / ", format_number(heldout_brier_worsening, 6), "."),
  "",
  "## Decision",
  paste0("Status: `", candidate_status, "`."),
  decision_reason,
  "",
  "## Required Outputs",
  "- nausea_mapping_audit.csv",
  "- nausea_model_comparison_metadata.csv",
  "- nausea_cell_counts_by_year.csv",
  "- nausea_missingness_by_endpoint.csv",
  "- nausea_model_comparison_coefficients.csv",
  "- nausea_model_comparison_covariance.csv",
  "- nausea_model_comparison_draws.csv",
  "- nausea_model_comparison_calibration.csv",
  "- nausea_leave_one_year_out_validation.csv",
  "- nausea_candidate_gate_decision.csv",
  "- nausea_candidate_ranked_decision.csv",
  "- nausea_candidate_screen_report.md"
)

utils::write.csv(mapping_audit, file.path(output_dir, "nausea_mapping_audit.csv"), row.names = FALSE, na = "")
utils::write.csv(run_metadata, file.path(output_dir, "nausea_model_comparison_metadata.csv"), row.names = FALSE, na = "")
utils::write.csv(cell_counts, file.path(output_dir, "nausea_cell_counts_by_year.csv"), row.names = FALSE, na = "")
utils::write.csv(missingness_rows, file.path(output_dir, "nausea_missingness_by_endpoint.csv"), row.names = FALSE, na = "")
utils::write.csv(coefficients, file.path(output_dir, "nausea_model_comparison_coefficients.csv"), row.names = FALSE, na = "")
utils::write.csv(covariance, file.path(output_dir, "nausea_model_comparison_covariance.csv"), row.names = FALSE, na = "")
utils::write.csv(draws, file.path(output_dir, "nausea_model_comparison_draws.csv"), row.names = FALSE, na = "")
utils::write.csv(calibration, file.path(output_dir, "nausea_model_comparison_calibration.csv"), row.names = FALSE, na = "")
utils::write.csv(leave_one_year_out, file.path(output_dir, "nausea_leave_one_year_out_validation.csv"), row.names = FALSE, na = "")
utils::write.csv(gate_rows, file.path(output_dir, "nausea_candidate_gate_decision.csv"), row.names = FALSE, na = "")
utils::write.csv(ranked_decision, file.path(output_dir, "nausea_candidate_ranked_decision.csv"), row.names = FALSE, na = "")
writeLines(report, con = file.path(output_dir, "nausea_candidate_screen_report.md"))

cat("Wrote NHAMCS nausea candidate screen outputs under ", output_dir, "\n", sep = "")
