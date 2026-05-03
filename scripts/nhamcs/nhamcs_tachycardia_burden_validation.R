#!/usr/bin/env Rscript

# Survey-weighted pooled NHAMCS tachycardia-burden validation.
#
# This gate tests tachycardia_burden = max(HR - 100, 0) / 10 after removing
# pain_missing from the candidate model by requiring observed pain.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: nhamcs_tachycardia_burden_validation.R <pooled_analytic_cohort_csv> <output_dir>")
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
MODEL_ID <- "pooled_empirical_v2_age_pain_fever_vomiting_tachycardia"
BASE_MODEL_ID <- "tachycardia_base_no_hr_complete_case"
HR110_MODEL_ID <- "tachycardia_sensitivity_hr_ge_110_complete_case"
LINEAR_HR_MODEL_ID <- "tachycardia_sensitivity_linear_hr_complete_case"
CLIPPED_MODEL_ID <- "tachycardia_sensitivity_clipped_burden_complete_case"
AGE_CENTER <- 42
RANDOM_SEED <- 20260428L
DRAW_COUNT <- 10000L
MIN_EVENTS <- 100
MIN_CELL_EVENTS <- 10
MIN_CELL_NONEVENTS <- 10
MIN_PROB_BETA_POSITIVE <- 0.95
MAX_BRIER_WORSENING <- 0
MAX_AUROC_WORSENING <- 0
set.seed(RANDOM_SEED)

MODEL_SPECS <- list(
  list(model_id = BASE_MODEL_ID, formula = admit ~ age_centered + pain_bin3 + fever_or_temp + vomiting_present),
  list(model_id = MODEL_ID, formula = admit ~ age_centered + pain_bin3 + fever_or_temp + vomiting_present + tachycardia_burden),
  list(model_id = HR110_MODEL_ID, formula = admit ~ age_centered + pain_bin3 + fever_or_temp + vomiting_present + HR_ge_110),
  list(model_id = LINEAR_HR_MODEL_ID, formula = admit ~ age_centered + pain_bin3 + fever_or_temp + vomiting_present + HR_centered_per_10),
  list(model_id = CLIPPED_MODEL_ID, formula = admit ~ age_centered + pain_bin3 + fever_or_temp + vomiting_present + tachycardia_burden_clipped)
)

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
normal_ci <- function(rate, n) {
  if (is.na(rate) || n <= 0) return(c(NA_real_, NA_real_))
  se <- sqrt(rate * (1 - rate) / n)
  c(max(0, rate - 1.96 * se), min(1, rate + 1.96 * se))
}
calibration_status <- function(slope, observed, predicted, events) {
  if (is.na(slope) || is.na(observed) || is.na(predicted) || events < MIN_EVENTS) return("fail")
  absolute_gap <- abs(predicted - observed)
  relative_gap <- absolute_gap / max(abs(observed), 1e-6)
  if (slope >= 0.8 && slope <= 1.2 && absolute_gap <= 0.02 && relative_gap <= 0.10) "pass" else "fail"
}
status_degraded <- function(base_status, candidate_status) {
  identical(base_status, "pass") && !identical(candidate_status, "pass")
}
format_number <- function(value, digits = 6) {
  if (is.na(value) || !is.finite(value)) return("")
  format(round(value, digits), nsmall = digits, trim = TRUE)
}

parse_coefficient <- function(name) {
  if (identical(name, "(Intercept)")) return(list(term = "intercept", level = ""))
  if (identical(name, "age_centered")) return(list(term = "age_centered", level = "per_1_year_centered_at_42"))
  if (startsWith(name, "pain_bin3")) return(list(term = "pain_bin3", level = substring(name, nchar("pain_bin3") + 1)))
  if (identical(name, "fever_or_temp")) return(list(term = "fever_or_temp", level = "1"))
  if (identical(name, "vomiting_present")) return(list(term = "vomiting_present", level = "1"))
  if (identical(name, "tachycardia_burden")) return(list(term = "tachycardia_burden", level = "per_10_bpm_over_100"))
  if (identical(name, "HR_ge_110")) return(list(term = "HR_ge_110", level = "1"))
  if (identical(name, "HR_centered_per_10")) return(list(term = "HR_centered_per_10", level = "per_10_bpm_centered"))
  if (identical(name, "tachycardia_burden_clipped")) return(list(term = "tachycardia_burden_clipped", level = "per_10_bpm_over_100_clipped_at_160"))
  list(term = name, level = "")
}
coefficient_label <- function(parsed) if (identical(parsed$level, "")) parsed$term else paste0(parsed$term, "[", parsed$level, "]")
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
  data.frame(model_id = model_id, dataset = DATASET, draw_id = rep(seq_len(DRAW_COUNT), each = length(beta)),
    term = rep(term_names, times = DRAW_COUNT), level = rep(levels, times = DRAW_COUNT),
    beta = as.numeric(t(draws)), seed = RANDOM_SEED, stringsAsFactors = FALSE)
}

empty_coefficients <- function() data.frame(model_id = character(), dataset = character(), term = character(), level = character(),
  beta = numeric(), se = numeric(), odds_ratio = numeric(), ci_low = numeric(), ci_high = numeric(),
  p_value = numeric(), evidence_tier = character(), limitation_note = character(), stringsAsFactors = FALSE)
empty_covariance <- function() data.frame(model_id = character(), dataset = character(), row_term = character(), column_term = character(),
  covariance = numeric(), stringsAsFactors = FALSE)
empty_draws <- function() data.frame(model_id = character(), dataset = character(), draw_id = integer(), term = character(),
  level = character(), beta = numeric(), seed = integer(), stringsAsFactors = FALSE)
empty_deciles <- function() data.frame(model_id = character(), dataset = character(), decile = integer(), n = integer(),
  events = integer(), mean_predicted = numeric(), observed_rate = numeric(), ci_low = numeric(), ci_high = numeric(),
  notes = character(), stringsAsFactors = FALSE)

fit_one_model <- function(spec, frame) {
  blocked <- function(status, note) list(
    fit = NULL, model_frame = frame, coefficients = empty_coefficients(), covariance = empty_covariance(),
    draws = empty_draws(),
    calibration = data.frame(model_id = spec$model_id, dataset = DATASET, n = nrow(frame),
      events = if (nrow(frame) > 0) sum(frame$admit) else 0,
      observed_prevalence = NA_real_, mean_predicted = NA_real_, calibration_in_the_large = NA_real_,
      calibration_slope = NA_real_, brier_score = NA_real_, auroc = NA_real_, pass_fail_status = status,
      notes = note, stringsAsFactors = FALSE),
    deciles = empty_deciles(), fit_error = note
  )
  if (nrow(frame) == 0 || length(unique(frame$admit)) < 2) {
    return(blocked("blocked_no_outcome_variation", "No usable complete-case outcome variation."))
  }
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = frame)
  fit_error <- NULL
  fit <- tryCatch(survey::svyglm(spec$formula, design = design, family = quasibinomial()),
    error = function(error) { fit_error <<- conditionMessage(error); NULL })
  if (is.null(fit)) return(blocked("blocked_fit_failed", paste("survey::svyglm failed:", fit_error)))

  coef_table <- summary(fit)$coefficients
  beta <- stats::coef(fit)
  covariance <- stats::vcov(fit)
  parsed_terms <- lapply(names(beta), parse_coefficient)
  labels <- vapply(parsed_terms, coefficient_label, character(1))
  se <- sqrt(pmax(diag(covariance), 0))
  coefficients <- data.frame(model_id = spec$model_id, dataset = DATASET,
    term = vapply(parsed_terms, function(item) item$term, character(1)),
    level = vapply(parsed_terms, function(item) item$level, character(1)),
    beta = as.numeric(beta), se = as.numeric(se), odds_ratio = exp(as.numeric(beta)),
    ci_low = exp(as.numeric(beta) - 1.96 * as.numeric(se)), ci_high = exp(as.numeric(beta) + 1.96 * as.numeric(se)),
    p_value = as.numeric(coef_table[, ncol(coef_table)]), evidence_tier = "survey_weighted_candidate",
    limitation_note = "Tachycardia burden validation candidate; not active unless all gates pass.",
    stringsAsFactors = FALSE)
  covariance_rows <- empty_covariance()
  for (row_index in seq_along(labels)) {
    for (column_index in seq_along(labels)) {
      covariance_rows <- rbind(covariance_rows, data.frame(model_id = spec$model_id, dataset = DATASET,
        row_term = labels[[row_index]], column_term = labels[[column_index]],
        covariance = covariance[row_index, column_index], stringsAsFactors = FALSE))
    }
  }

  predicted <- as.numeric(stats::predict(fit, type = "response"))
  y <- frame$admit
  weight <- frame$weight
  observed <- weighted_mean(y, weight)
  mean_predicted <- weighted_mean(predicted, weight)
  linear_prediction <- logit(predicted)
  frame$.__linear_prediction <- linear_prediction
  calibration_intercept <- NA_real_
  calibration_slope <- NA_real_
  if (length(unique(y)) >= 2 && length(unique(linear_prediction)) >= 2) {
    calibration_design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = frame)
    intercept_fit <- survey::svyglm(admit ~ 1 + offset(.__linear_prediction), design = calibration_design, family = quasibinomial())
    slope_fit <- survey::svyglm(admit ~ .__linear_prediction, design = calibration_design, family = quasibinomial())
    calibration_intercept <- as.numeric(stats::coef(intercept_fit)[[1]])
    calibration_slope <- as.numeric(stats::coef(slope_fit)[[".__linear_prediction"]])
  }
  calibration <- data.frame(model_id = spec$model_id, dataset = DATASET,
    n = nrow(frame), events = sum(y), observed_prevalence = observed, mean_predicted = mean_predicted,
    calibration_in_the_large = calibration_intercept, calibration_slope = calibration_slope,
    brier_score = weighted_mean((predicted - y) ^ 2, weight), auroc = weighted_auc(y, predicted, weight),
    pass_fail_status = calibration_status(calibration_slope, observed, mean_predicted, sum(y)),
    notes = "Survey-weighted apparent calibration for tachycardia burden validation.", stringsAsFactors = FALSE)

  order_index <- order(predicted)
  decile <- rep(NA_integer_, length(predicted))
  decile[order_index] <- pmin(10L, pmax(1L, ceiling(cumsum(weight[order_index]) / sum(weight) * 10L)))
  deciles <- empty_deciles()
  for (group in sort(unique(decile))) {
    subset <- decile == group
    observed_rate <- weighted_mean(y[subset], weight[subset])
    ci <- normal_ci(observed_rate, sum(subset))
    deciles <- rbind(deciles, data.frame(model_id = spec$model_id, dataset = DATASET, decile = group,
      n = sum(subset), events = sum(y[subset]),
      mean_predicted = weighted_mean(predicted[subset], weight[subset]), observed_rate = observed_rate,
      ci_low = ci[[1]], ci_high = ci[[2]],
      notes = "Survey-weighted decile calibration; CI is approximate unweighted normal interval.", stringsAsFactors = FALSE))
  }
  list(fit = fit, model_frame = frame, coefficients = coefficients, covariance = covariance_rows,
    draws = mvn_draws(spec$model_id, beta, covariance, parsed_terms), calibration = calibration,
    deciles = deciles, fit_error = NULL)
}

predict_heldout <- function(spec, train, test) {
  blocked <- function(status, note) data.frame(heldout_year = unique(test$year)[[1]], model_id = spec$model_id,
    dataset = DATASET, train_n = nrow(train), train_events = if (nrow(train) > 0) sum(train$admit) else 0,
    heldout_n = nrow(test), heldout_events = if (nrow(test) > 0) sum(test$admit) else 0,
    brier_score = NA_real_, auroc = NA_real_, observed_prevalence = NA_real_, mean_predicted = NA_real_,
    pass_fail_status = status, tachycardia_beta = NA_real_, tachycardia_ci_high = NA_real_,
    note = note, stringsAsFactors = FALSE)
  if (nrow(train) == 0 || nrow(test) == 0 || length(unique(train$admit)) < 2) {
    return(blocked("blocked_split_no_outcome_variation", "Training or held-out split lacks outcome variation."))
  }
  fit <- tryCatch({
    design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = train)
    survey::svyglm(spec$formula, design = design, family = quasibinomial())
  }, error = function(error) error)
  if (inherits(fit, "error")) {
    return(blocked("blocked_fit_failed", conditionMessage(fit)))
  }
  predicted <- tryCatch(as.numeric(stats::predict(fit, newdata = test, type = "response")), error = function(error) rep(NA_real_, nrow(test)))
  y <- test$admit
  weight <- test$weight
  beta <- stats::coef(fit)
  covariance <- stats::vcov(fit)
  tachy_beta <- if ("tachycardia_burden" %in% names(beta)) as.numeric(beta[["tachycardia_burden"]]) else NA_real_
  tachy_ci_high <- if ("tachycardia_burden" %in% names(beta)) {
    se <- sqrt(max(covariance["tachycardia_burden", "tachycardia_burden"], 0))
    exp(as.numeric(beta[["tachycardia_burden"]]) + 1.96 * se)
  } else {
    NA_real_
  }
  observed <- weighted_mean(y, weight)
  mean_predicted <- weighted_mean(predicted, weight)
  data.frame(heldout_year = unique(test$year)[[1]], model_id = spec$model_id,
    dataset = DATASET, train_n = nrow(train), train_events = sum(train$admit),
    heldout_n = nrow(test), heldout_events = sum(test$admit),
    brier_score = weighted_mean((predicted - y) ^ 2, weight), auroc = weighted_auc(y, predicted, weight),
    observed_prevalence = observed, mean_predicted = mean_predicted,
    pass_fail_status = ifelse(all(is.finite(predicted)) && !is.na(observed) && !is.na(mean_predicted), "pass_prediction", "blocked_prediction"),
    tachycardia_beta = tachy_beta, tachycardia_ci_high = tachy_ci_high,
    note = "", stringsAsFactors = FALSE)
}

cell_count <- function(frame, group, level, subset) {
  part <- frame[subset, , drop = FALSE]
  data.frame(dataset = DATASET, model_id = MODEL_ID, group = group, level = level,
    n = nrow(part), events = if (nrow(part) > 0) sum(part$admit == 1) else 0,
    non_events = if (nrow(part) > 0) sum(part$admit == 0) else 0,
    weighted_n = if (nrow(part) > 0) sum(part$weight) else 0,
    weighted_events = if (nrow(part) > 0) sum(part$weight[part$admit == 1]) else 0,
    stringsAsFactors = FALSE)
}

cohort <- read.csv(input_path, stringsAsFactors = FALSE, na.strings = c("", "NA", "NaN"))
if ("dataset" %in% names(cohort) && length(unique(cohort$dataset[!is.na(cohort$dataset)])) > 0) {
  DATASET <- unique(cohort$dataset[!is.na(cohort$dataset)])[[1]]
}
required <- c("include_strict_binary", "admit", "year", "age", "pain_bin3", "pain_missing",
              "fever_or_temp", "vomiting_present", "HR", "tachycardia_burden",
              "pooled_weight", "pooled_stratum", "pooled_psu")
missing_required <- setdiff(required, names(cohort))
if (length(missing_required) > 0) {
  stop(paste("Missing required columns:", paste(missing_required, collapse = ", ")))
}

binary <- cohort[truthy(cohort$include_strict_binary), , drop = FALSE]
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
binary$expected_tachycardia_burden <- ifelse(is.na(binary$HR), NA_real_, pmax(binary$HR - 100, 0) / 10)
valid <- !is.na(binary$admit) & binary$admit %in% c(0, 1) &
  !is.na(binary$year) & !is.na(binary$age_centered) &
  !is.na(binary$weight) & binary$weight > 0 &
  !is.na(binary$stratum) & !is.na(binary$psu)
binary <- binary[valid, , drop = FALSE]

complete_case <- binary[
  binary$pain_missing == 0 &
    !is.na(binary$pain_bin3) &
    !is.na(binary$fever_or_temp) &
    !is.na(binary$vomiting_present) &
    !is.na(binary$HR) &
    !is.na(binary$tachycardia_burden),
  , drop = FALSE
]
if (nrow(complete_case) == 0 || length(unique(complete_case$admit)) < 2) {
  stop("No usable complete-case strict-binary records with observed pain, fever/temp, vomiting, HR, and outcome variation.")
}
complete_case$pain_bin3 <- stats::relevel(as.factor(complete_case$pain_bin3), ref = "moderate")
complete_case$HR_ge_110 <- as.numeric(complete_case$HR >= 110)
hr_weighted_mean <- weighted_mean(complete_case$HR, complete_case$weight)
complete_case$HR_centered_per_10 <- (complete_case$HR - hr_weighted_mean) / 10
complete_case$tachycardia_burden_clipped <- pmax(pmin(complete_case$HR, 160) - 100, 0) / 10

fit_results <- lapply(MODEL_SPECS, fit_one_model, frame = complete_case)
names(fit_results) <- vapply(MODEL_SPECS, function(spec) spec$model_id, character(1))
coefficients <- do.call(rbind, lapply(fit_results, function(item) item$coefficients))
covariance <- do.call(rbind, lapply(fit_results, function(item) item$covariance))
draws <- do.call(rbind, lapply(fit_results, function(item) item$draws))
calibration <- do.call(rbind, lapply(fit_results, function(item) item$calibration))
deciles <- do.call(rbind, lapply(fit_results, function(item) item$deciles))

leave_one_year_out <- data.frame()
for (heldout_year in sort(unique(complete_case$year))) {
  train <- complete_case[complete_case$year != heldout_year, , drop = FALSE]
  test <- complete_case[complete_case$year == heldout_year, , drop = FALSE]
  for (spec in MODEL_SPECS[vapply(MODEL_SPECS, function(item) item$model_id %in% c(BASE_MODEL_ID, MODEL_ID), logical(1))]) {
    leave_one_year_out <- rbind(leave_one_year_out, predict_heldout(spec, train, test))
  }
}

cell_counts <- data.frame()
for (level in c("mild", "moderate", "severe")) {
  cell_counts <- rbind(cell_counts, cell_count(complete_case, "pain_bin3_observed", level, as.character(complete_case$pain_bin3) == level))
}
for (level in c("0", "1")) {
  cell_counts <- rbind(cell_counts, cell_count(complete_case, "fever_or_temp", level, complete_case$fever_or_temp == as.numeric(level)))
  cell_counts <- rbind(cell_counts, cell_count(complete_case, "vomiting_present", level, complete_case$vomiting_present == as.numeric(level)))
}
cell_counts <- rbind(cell_counts, cell_count(complete_case, "tachycardia_burden_positive", "0", complete_case$tachycardia_burden == 0))
cell_counts <- rbind(cell_counts, cell_count(complete_case, "tachycardia_burden_positive", "1", complete_case$tachycardia_burden > 0))
cell_counts <- rbind(cell_counts, cell_count(complete_case, "HR_ge_110", "1", complete_case$HR >= 110))

calibration_row <- function(model_id) {
  selected <- calibration[calibration$model_id == model_id, , drop = FALSE]
  if (nrow(selected) == 0) return(NULL)
  selected[1, , drop = FALSE]
}
coefficient_row <- function(model_id, term, level) {
  selected <- coefficients[coefficients$model_id == model_id & coefficients$term == term & as.character(coefficients$level) == as.character(level), , drop = FALSE]
  if (nrow(selected) == 0) return(NULL)
  selected[1, , drop = FALSE]
}
draw_count_for <- function(term, level) {
  selected <- draws[draws$model_id == MODEL_ID & draws$term == term & as.character(draws$level) == as.character(level), , drop = FALSE]
  length(unique(selected$draw_id))
}
draw_probability_positive <- function(term, level) {
  selected <- draws[draws$model_id == MODEL_ID & draws$term == term & as.character(draws$level) == as.character(level), , drop = FALSE]
  if (nrow(selected) == 0) return(NA_real_)
  mean(selected$beta > 0)
}
count_for <- function(group, level) {
  cell_counts[cell_counts$group == group & as.character(cell_counts$level) == as.character(level), , drop = FALSE]
}

base_calibration <- calibration_row(BASE_MODEL_ID)
candidate_calibration <- calibration_row(MODEL_ID)
tachy_coef <- coefficient_row(MODEL_ID, "tachycardia_burden", "per_10_bpm_over_100")
candidate_loo <- leave_one_year_out[leave_one_year_out$model_id == MODEL_ID, , drop = FALSE]
base_loo <- leave_one_year_out[leave_one_year_out$model_id == BASE_MODEL_ID, , drop = FALSE]
merged_loo <- merge(base_loo, candidate_loo, by = "heldout_year", suffixes = c("_base", "_candidate"), sort = TRUE)

apparent_brier_change <- if (!is.null(base_calibration) && !is.null(candidate_calibration)) candidate_calibration$brier_score[[1]] - base_calibration$brier_score[[1]] else NA_real_
apparent_auroc_change <- if (!is.null(base_calibration) && !is.null(candidate_calibration)) candidate_calibration$auroc[[1]] - base_calibration$auroc[[1]] else NA_real_
apparent_status_degraded <- if (!is.null(base_calibration) && !is.null(candidate_calibration)) status_degraded(base_calibration$pass_fail_status[[1]], candidate_calibration$pass_fail_status[[1]]) else TRUE
heldout_brier_change <- if (nrow(merged_loo) > 0) weighted_mean(merged_loo$brier_score_candidate - merged_loo$brier_score_base, merged_loo$heldout_n_base) else NA_real_
heldout_auroc_change <- if (nrow(merged_loo) > 0) weighted_mean(merged_loo$auroc_candidate - merged_loo$auroc_base, merged_loo$heldout_n_base) else NA_real_
heldout_prediction_complete <- nrow(merged_loo) == length(unique(complete_case$year)) &&
  all(merged_loo$pass_fail_status_base == "pass_prediction") &&
  all(merged_loo$pass_fail_status_candidate == "pass_prediction")

complete_case_event_gate <- nrow(complete_case) > 0 && sum(complete_case$admit) >= MIN_EVENTS
positive_coefficient_gate <- !is.null(tachy_coef) && is.finite(tachy_coef$beta[[1]]) && tachy_coef$beta[[1]] > 0
uncertainty_exported_gate <- nrow(covariance[covariance$model_id == MODEL_ID, , drop = FALSE]) > 0 &&
  draw_count_for("tachycardia_burden", "per_10_bpm_over_100") == DRAW_COUNT &&
  is.finite(draw_probability_positive("tachycardia_burden", "per_10_bpm_over_100")) &&
  draw_probability_positive("tachycardia_burden", "per_10_bpm_over_100") >= MIN_PROB_BETA_POSITIVE
apparent_calibration_gate <- !is.null(candidate_calibration) && identical(candidate_calibration$pass_fail_status[[1]], "pass")
pain_cells <- cell_counts[cell_counts$group == "pain_bin3_observed", , drop = FALSE]
fever_cells <- cell_counts[cell_counts$group == "fever_or_temp", , drop = FALSE]
vomiting_cells <- cell_counts[cell_counts$group == "vomiting_present", , drop = FALSE]
tachy_cells <- cell_counts[cell_counts$group == "tachycardia_burden_positive", , drop = FALSE]
cell_event_gate <- all(pain_cells$events >= MIN_CELL_EVENTS) && all(pain_cells$non_events >= MIN_CELL_NONEVENTS) &&
  all(fever_cells$events >= MIN_CELL_EVENTS) && all(fever_cells$non_events >= MIN_CELL_NONEVENTS) &&
  all(vomiting_cells$events >= MIN_CELL_EVENTS) && all(vomiting_cells$non_events >= MIN_CELL_NONEVENTS) &&
  all(tachy_cells$events >= MIN_CELL_EVENTS) && all(tachy_cells$non_events >= MIN_CELL_NONEVENTS)
loo_stability_gate <- heldout_prediction_complete && nrow(candidate_loo) == length(unique(complete_case$year)) &&
  all(is.finite(candidate_loo$tachycardia_beta)) && all(candidate_loo$tachycardia_beta > 0)
performance_preserved_gate <- is.finite(apparent_brier_change) && apparent_brier_change <= MAX_BRIER_WORSENING &&
  is.finite(apparent_auroc_change) && apparent_auroc_change >= -MAX_AUROC_WORSENING &&
  !apparent_status_degraded &&
  is.finite(heldout_brier_change) && heldout_brier_change <= MAX_BRIER_WORSENING &&
  is.finite(heldout_auroc_change) && heldout_auroc_change >= -MAX_AUROC_WORSENING
transform_gate <- all(abs(complete_case$tachycardia_burden - complete_case$expected_tachycardia_burden) < 1e-12)
documentation_gate <- all(complete_case$pain_missing == 0) &&
  all(!is.na(complete_case$HR)) &&
  all(complete_case$vomiting_present %in% c(0, 1)) &&
  all(complete_case$fever_or_temp %in% c(0, 1)) &&
  transform_gate

activation_pass <- complete_case_event_gate && positive_coefficient_gate && uncertainty_exported_gate &&
  apparent_calibration_gate && cell_event_gate && loo_stability_gate && performance_preserved_gate && documentation_gate

term_decision <- function(term, level) {
  coef <- coefficient_row(MODEL_ID, term, level)
  blockers <- c()
  if (is.null(coef) || !is.finite(coef$beta[[1]]) || !is.finite(coef$se[[1]])) blockers <- c(blockers, "missing_or_nonfinite_coefficient")
  if (!uncertainty_exported_gate) blockers <- c(blockers, "missing_or_insufficient_uncertainty_export")
  if (!complete_case_event_gate) blockers <- c(blockers, "model_event_count_lt_100")
  if (!apparent_calibration_gate) blockers <- c(blockers, "apparent_calibration_failure")
  if (!loo_stability_gate) blockers <- c(blockers, "leave_one_year_out_instability")
  if (!performance_preserved_gate) blockers <- c(blockers, "performance_not_preserved")
  if (!documentation_gate) blockers <- c(blockers, "documentation_or_transform_gate_failed")
  if (!cell_event_gate) blockers <- c(blockers, "cell_event_gate_failed")
  if (term %in% c("age_centered", "fever_or_temp", "vomiting_present", "tachycardia_burden")) {
    if (!is.null(coef) && is.finite(coef$beta[[1]]) && coef$beta[[1]] <= 0) blockers <- c(blockers, paste0(term, "_beta_not_positive"))
  }
  if (term == "tachycardia_burden") {
    if (draw_probability_positive(term, level) < MIN_PROB_BETA_POSITIVE) blockers <- c(blockers, "tachycardia_beta_positive_probability_low")
  }
  tier <- if (length(blockers) == 0) "dataset_derived" else "survey_weighted_candidate"
  data.frame(dataset = DATASET, model_id = MODEL_ID, source_model_id = MODEL_ID,
    term = term, level = level, assigned_evidence_tier = tier,
    blockers = paste(unique(blockers), collapse = "; "),
    beta = if (!is.null(coef)) coef$beta[[1]] else NA_real_,
    se = if (!is.null(coef)) coef$se[[1]] else NA_real_,
    draw_count = draw_count_for(term, level),
    evidence_tier = "survey_weighted_candidate",
    stringsAsFactors = FALSE)
}

term_decisions <- do.call(rbind, list(
  term_decision("intercept", ""),
  term_decision("age_centered", "per_1_year_centered_at_42"),
  term_decision("pain_bin3", "mild"),
  term_decision("pain_bin3", "severe"),
  term_decision("fever_or_temp", "1"),
  term_decision("vomiting_present", "1"),
  term_decision("tachycardia_burden", "per_10_bpm_over_100")
))
activation_pass <- activation_pass && all(term_decisions$assigned_evidence_tier == "dataset_derived")

for (index in seq_len(nrow(term_decisions))) {
  row <- term_decisions[index, ]
  match <- coefficients$model_id == MODEL_ID & coefficients$term == row$term & as.character(coefficients$level) == as.character(row$level)
  coefficients$evidence_tier[match] <- row$assigned_evidence_tier
  if (row$assigned_evidence_tier == "dataset_derived") {
    coefficients$limitation_note[match] <- "Dataset-derived from pooled NHAMCS tachycardia burden evidence gates for educational use only; not clinical decision support."
  }
}

gate_rows <- data.frame(
  dataset = DATASET,
  model_id = MODEL_ID,
  gate = c("complete_case_event_count", "positive_tachycardia_coefficient", "uncertainty_exported",
    "apparent_calibration", "cell_event_adequacy", "leave_one_year_out_stability",
    "performance_preserved_or_improved", "documentation_and_transform", "all_terms_dataset_derived",
    "activation_suitability"),
  passed = c(complete_case_event_gate, positive_coefficient_gate, uncertainty_exported_gate,
    apparent_calibration_gate, cell_event_gate, loo_stability_gate,
    performance_preserved_gate, documentation_gate, all(term_decisions$assigned_evidence_tier == "dataset_derived"),
    activation_pass),
  status = c(ifelse(complete_case_event_gate, "pass", "fail"), ifelse(positive_coefficient_gate, "pass", "fail"),
    ifelse(uncertainty_exported_gate, "pass", "fail"), ifelse(apparent_calibration_gate, "pass", "fail"),
    ifelse(cell_event_gate, "pass", "fail"), ifelse(loo_stability_gate, "pass", "fail"),
    ifelse(performance_preserved_gate, "pass", "fail"), ifelse(documentation_gate, "pass", "fail"),
    ifelse(all(term_decisions$assigned_evidence_tier == "dataset_derived"), "pass", "fail"),
    ifelse(activation_pass, "eligible_for_educational_activation", "blocked")),
  metric = c(sum(complete_case$admit), if (!is.null(tachy_coef)) tachy_coef$beta[[1]] else NA_real_,
    draw_count_for("tachycardia_burden", "per_10_bpm_over_100"),
    if (!is.null(candidate_calibration)) candidate_calibration$calibration_slope[[1]] else NA_real_,
    min(c(pain_cells$events, fever_cells$events, vomiting_cells$events, tachy_cells$events)),
    if (nrow(candidate_loo) > 0) min(candidate_loo$tachycardia_beta, na.rm = TRUE) else NA_real_,
    apparent_brier_change, sum(abs(complete_case$tachycardia_burden - complete_case$expected_tachycardia_burden) < 1e-12),
    sum(term_decisions$assigned_evidence_tier == "dataset_derived"), NA_real_),
  threshold = c("admission events >= 100", "> 0",
    paste0(DRAW_COUNT, " draws and Pr(beta>0) >= ", MIN_PROB_BETA_POSITIVE),
    "slope 0.8-1.2 and mean predicted close to observed",
    "each target cell has >=10 events and >=10 non-events",
    "all heldout fits complete and tachycardia beta > 0",
    "apparent and heldout Brier/AUROC preserved or improved",
    "pain and HR observed; tachycardia_burden exactly max(HR - 100, 0) / 10",
    "all target terms assigned dataset_derived", "all gates pass"),
  details = c(
    paste0("complete-case N=", nrow(complete_case), ", events=", sum(complete_case$admit)),
    if (!is.null(tachy_coef)) paste0("beta=", format_number(tachy_coef$beta[[1]]), ", se=", format_number(tachy_coef$se[[1]]), ", OR=", format_number(tachy_coef$odds_ratio[[1]])) else "tachycardia coefficient unavailable",
    paste0("draws=", draw_count_for("tachycardia_burden", "per_10_bpm_over_100"), ", Pr(beta>0)=", format_number(draw_probability_positive("tachycardia_burden", "per_10_bpm_over_100"))),
    if (!is.null(candidate_calibration)) paste0("observed=", format_number(candidate_calibration$observed_prevalence[[1]]), ", mean_predicted=", format_number(candidate_calibration$mean_predicted[[1]]), ", slope=", format_number(candidate_calibration$calibration_slope[[1]])) else "calibration unavailable",
    paste0("minimum target-cell events=", min(c(pain_cells$events, fever_cells$events, vomiting_cells$events, tachy_cells$events)), ", minimum non-events=", min(c(pain_cells$non_events, fever_cells$non_events, vomiting_cells$non_events, tachy_cells$non_events))),
    if (nrow(candidate_loo) > 0) paste0("heldout years=", nrow(candidate_loo), ", minimum tachy beta=", format_number(min(candidate_loo$tachycardia_beta, na.rm = TRUE))) else "LOO rows unavailable",
    paste0("apparent Brier change=", format_number(apparent_brier_change), ", apparent AUROC change=", format_number(apparent_auroc_change), ", heldout Brier change=", format_number(heldout_brier_change), ", heldout AUROC change=", format_number(heldout_auroc_change)),
    paste0("pain_missing excluded=", sum(binary$pain_missing == 1, na.rm = TRUE), " rows; HR-missing excluded=", sum(is.na(binary$HR)), " rows"),
    paste0("dataset_derived terms=", sum(term_decisions$assigned_evidence_tier == "dataset_derived"), "/", nrow(term_decisions)),
    ifelse(activation_pass, "tachycardia burden v2 model can activate for educational use", "tachycardia burden v2 model remains blocked")),
  evidence_tier = "survey_weighted_candidate",
  stringsAsFactors = FALSE)

report_lines <- c(
  "# Tachycardia Burden Validation Gate", "",
  paste0("Model ID: `", MODEL_ID, "`"),
  "Formula: `admit ~ age_centered + pain_bin3 + fever_or_temp + vomiting_present + tachycardia_burden`",
  "Transform: `tachycardia_burden = max(HR - 100, 0) / 10`.",
  "Pain missingness is removed from the model by requiring observed pain.",
  "HR missing is not normal; records with missing HR are excluded from this fit.",
  paste0("Decision: `", ifelse(activation_pass, "eligible_for_educational_activation", "blocked"), "`."),
  "",
  "## Model Comparison",
  "| Model | N | Events | AUROC | Brier | Calibration slope | Status |",
  "|---|---:|---:|---:|---:|---:|---|"
)
for (index in seq_len(nrow(calibration))) {
  row <- calibration[index, ]
  report_lines <- c(report_lines, paste0("| `", row$model_id, "` | ", row$n, " | ", row$events,
    " | ", format_number(row$auroc), " | ", format_number(row$brier_score),
    " | ", format_number(row$calibration_slope), " | `", row$pass_fail_status, "` |"))
}
report_lines <- c(report_lines, "",
  "## Term Decisions",
  "| Term | Level | Evidence tier | Beta | SE | Blockers |",
  "|---|---|---|---:|---:|---|")
for (index in seq_len(nrow(term_decisions))) {
  row <- term_decisions[index, ]
  report_lines <- c(report_lines, paste0("| `", row$term, "` | `", row$level, "` | `",
    row$assigned_evidence_tier, "` | ", format_number(row$beta), " | ",
    format_number(row$se), " | ", ifelse(row$blockers == "", "", row$blockers), " |"))
}
report_lines <- c(report_lines, "",
  "## Gate Decisions",
  "| Gate | Passed | Status | Details |",
  "|---|---:|---|---|")
for (index in seq_len(nrow(gate_rows))) {
  row <- gate_rows[index, ]
  report_lines <- c(report_lines, paste0("| `", row$gate, "` | ", tolower(as.character(row$passed)),
    " | `", row$status, "` | ", row$details, " |"))
}
report_lines <- c(report_lines, "",
  "## Interpretation",
  "- Tachycardia burden is an observed physiologic predictor, not a documentation-missingness term.",
  "- NHAMCS provides one PULSE value; tachycardia duration cannot be evaluated in this source.",
  "- Duration of tachycardia remains a future MIMIC-only validation question requiring timestamp-preserving vital-sign extraction.",
  "- The model is educational/statistical only and is not clinical decision support.",
  "")

utils::write.csv(cell_counts, file.path(output_dir, "tachycardia_burden_cell_counts.csv"), row.names = FALSE, na = "")
utils::write.csv(coefficients, file.path(output_dir, "tachycardia_model_comparison_coefficients.csv"), row.names = FALSE, na = "")
utils::write.csv(covariance, file.path(output_dir, "tachycardia_model_comparison_covariance.csv"), row.names = FALSE, na = "")
utils::write.csv(draws, file.path(output_dir, "tachycardia_model_comparison_draws.csv"), row.names = FALSE, na = "")
utils::write.csv(calibration, file.path(output_dir, "tachycardia_model_comparison_calibration.csv"), row.names = FALSE, na = "")
utils::write.csv(deciles, file.path(output_dir, "tachycardia_model_comparison_deciles.csv"), row.names = FALSE, na = "")
utils::write.csv(leave_one_year_out, file.path(output_dir, "tachycardia_burden_leave_one_year_out_validation.csv"), row.names = FALSE, na = "")
utils::write.csv(gate_rows, file.path(output_dir, "tachycardia_burden_gate_decision.csv"), row.names = FALSE, na = "")
utils::write.csv(term_decisions, file.path(output_dir, "tachycardia_burden_term_decisions.csv"), row.names = FALSE, na = "")
writeLines(report_lines, con = file.path(output_dir, "tachycardia_burden_validation_report.md"))

cat("Wrote tachycardia burden validation outputs under ", output_dir, "\n", sep = "")
