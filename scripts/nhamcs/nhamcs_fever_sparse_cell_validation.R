#!/usr/bin/env Rscript

# Fever sparse-cell validation gate for pooled NHAMCS.
# Outputs are assessment-only; no coefficient is promoted here.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: nhamcs_fever_sparse_cell_validation.R <pooled_analytic_cohort_csv> <output_dir>")
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
AGE_CENTER <- 42
RANDOM_SEED <- 20260429L
DRAW_COUNT <- 10000L
MIN_FEVER_POSITIVE_N <- 30L
MIN_FEVER_POSITIVE_EVENTS <- 10L
MIN_FEVER_POSITIVE_NONEVENTS <- 10L
MIN_PROB_BETA_POSITIVE <- 0.95
MAX_OR_CI_HIGH <- 50
MAX_BRIER_WORSENING <- 0.002
MAX_AUROC_WORSENING <- 0.01
set.seed(RANDOM_SEED)

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
  if (events < 100) return("survey_weighted_candidate_exploratory_event_count_lt_100")
  if (is.na(slope)) return("fail_calibration_unavailable")
  absolute_gap <- abs(predicted - observed)
  relative_gap <- absolute_gap / max(observed, 1e-6)
  if (absolute_gap > 0.02 || relative_gap > 0.10) return("fail_recalibrate_intercept")
  if (slope < 0.8) return("fail_likely_overfit")
  if (slope > 1.2) return("fail_likely_underfit")
  "pass_candidate_range"
}
status_is_pass <- function(status) startsWith(as.character(status), "pass")
status_degraded <- function(base_status, candidate_status) status_is_pass(base_status) && !status_is_pass(candidate_status)

cohort <- read.csv(input_path, stringsAsFactors = FALSE, na.strings = c("", "NA", "NaN"))
if ("dataset" %in% names(cohort) && length(unique(cohort$dataset[!is.na(cohort$dataset)])) > 0) {
  DATASET <- unique(cohort$dataset[!is.na(cohort$dataset)])[[1]]
}
required <- c("include_strict_binary", "admit", "year", "age", "pain_bin3", "pain_missing",
              "fever_or_temp", "pooled_weight", "pooled_stratum", "pooled_psu")
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
if (!"endpoint_class" %in% names(binary)) {
  binary$endpoint_class <- ifelse(binary$admit == 1, "admit", "routine_home_discharge")
}
valid <- !is.na(binary$admit) & binary$admit %in% c(0, 1) &
  !is.na(binary$year) & !is.na(binary$age) &
  !is.na(binary$weight) & binary$weight > 0 &
  !is.na(binary$stratum) & !is.na(binary$psu)
binary <- binary[valid, , drop = FALSE]
if (nrow(binary) == 0 || length(unique(binary$admit)) < 2) {
  stop("No usable strict-binary records with outcome variation after base filtering.")
}
binary$pain_missing[is.na(binary$pain_missing)] <- ifelse(is.na(binary$pain_bin3[is.na(binary$pain_missing)]), 1, 0)
binary$pain_bin3[is.na(binary$pain_bin3)] <- "moderate"
binary$pain_bin3 <- stats::relevel(as.factor(binary$pain_bin3), ref = "moderate")
binary$temp_status <- ifelse(is.na(binary$fever_or_temp), "temp_missing", ifelse(binary$fever_or_temp == 1, "fever", "no_fever"))
binary$temp_status <- stats::relevel(as.factor(binary$temp_status), ref = "no_fever")
complete_temp <- binary[!is.na(binary$fever_or_temp), , drop = FALSE]
if (nrow(complete_temp) == 0 || length(unique(complete_temp$admit)) < 2) {
  stop("No usable complete-temperature strict-binary records with outcome variation.")
}

MODEL_SPECS <- list(
  list(model_id = "fever_base_complete_temp", formula = admit ~ age_centered + pain_bin3 + pain_missing, data_scope = "complete_temperature"),
  list(model_id = "fever_candidate_complete_temp", formula = admit ~ age_centered + pain_bin3 + pain_missing + fever_or_temp, data_scope = "complete_temperature"),
  list(model_id = "fever_temp_status_sensitivity", formula = admit ~ age_centered + pain_bin3 + pain_missing + temp_status, data_scope = "all_temperature_statuses")
)

empty_coefficients <- function() data.frame(model_id = character(), dataset = character(), term = character(), level = character(),
  beta = numeric(), se = numeric(), odds_ratio = numeric(), ci_low = numeric(), ci_high = numeric(),
  p_value = numeric(), evidence_tier = character(), limitation_note = character(), stringsAsFactors = FALSE)
empty_covariance <- function() data.frame(model_id = character(), dataset = character(), row_term = character(), column_term = character(),
  covariance = numeric(), stringsAsFactors = FALSE)
empty_draws <- function() data.frame(model_id = character(), dataset = character(), draw_id = integer(), term = character(),
  level = character(), beta = numeric(), seed = integer(), stringsAsFactors = FALSE)
empty_deciles <- function() data.frame(model_id = character(), dataset = character(), data_scope = character(), decile = integer(),
  n = integer(), events = integer(), mean_predicted = numeric(), observed_rate = numeric(), ci_low = numeric(),
  ci_high = numeric(), notes = character(), stringsAsFactors = FALSE)

parse_coefficient <- function(name) {
  if (identical(name, "(Intercept)")) return(list(term = "intercept", level = ""))
  if (identical(name, "age_centered")) return(list(term = "age_centered", level = "per_1_year_centered_at_42"))
  if (startsWith(name, "pain_bin3")) return(list(term = "pain_bin3", level = substring(name, nchar("pain_bin3") + 1)))
  if (identical(name, "pain_missing")) return(list(term = "pain_missing", level = "1"))
  if (identical(name, "fever_or_temp")) return(list(term = "fever_or_temp", level = "1"))
  if (startsWith(name, "temp_status")) return(list(term = "temp_status", level = substring(name, nchar("temp_status") + 1)))
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

model_frame_for_spec <- function(spec, frame) {
  model_frame <- if (identical(spec$data_scope, "complete_temperature")) frame[!is.na(frame$fever_or_temp), , drop = FALSE] else frame
  model_frame[!is.na(model_frame$age_centered) & !is.na(model_frame$pain_bin3) &
    !is.na(model_frame$pain_missing) & !is.na(model_frame$weight) & model_frame$weight > 0 &
    !is.na(model_frame$stratum) & !is.na(model_frame$psu), , drop = FALSE]
}

fit_one_model <- function(spec, frame) {
  model_frame <- model_frame_for_spec(spec, frame)
  blocked <- function(status, note) list(
    fit = NULL,
    model_frame = model_frame,
    coefficients = empty_coefficients(),
    covariance = empty_covariance(),
    draws = empty_draws(),
    calibration = data.frame(model_id = spec$model_id, dataset = DATASET, data_scope = spec$data_scope,
      n = nrow(model_frame), events = if (nrow(model_frame) > 0) sum(model_frame$admit) else 0,
      observed_prevalence = NA_real_, mean_predicted = NA_real_, calibration_in_the_large = NA_real_,
      calibration_slope = NA_real_, brier_score = NA_real_, auroc = NA_real_, pass_fail_status = status,
      notes = note, stringsAsFactors = FALSE),
    deciles = empty_deciles(),
    fit_error = note
  )
  if (nrow(model_frame) == 0 || length(unique(model_frame$admit)) < 2) {
    return(blocked("blocked_no_outcome_variation", "No usable binary outcome variation after fever-gate model filtering."))
  }
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = model_frame)
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
    limitation_note = "Fever sparse-cell validation only; no coefficient promotion or app activation.",
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
  y <- model_frame$admit
  weight <- model_frame$weight
  observed <- weighted_mean(y, weight)
  mean_predicted <- weighted_mean(predicted, weight)
  linear_prediction <- logit(predicted)
  model_frame$.__linear_prediction <- linear_prediction
  calibration_intercept <- NA_real_
  calibration_slope <- NA_real_
  if (length(unique(y)) >= 2 && length(unique(linear_prediction)) >= 2) {
    calibration_design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = model_frame)
    intercept_fit <- survey::svyglm(admit ~ 1 + offset(.__linear_prediction), design = calibration_design, family = quasibinomial())
    slope_fit <- survey::svyglm(admit ~ .__linear_prediction, design = calibration_design, family = quasibinomial())
    calibration_intercept <- as.numeric(stats::coef(intercept_fit)[[1]])
    calibration_slope <- as.numeric(stats::coef(slope_fit)[[".__linear_prediction"]])
  }
  calibration <- data.frame(model_id = spec$model_id, dataset = DATASET, data_scope = spec$data_scope,
    n = nrow(model_frame), events = sum(y), observed_prevalence = observed, mean_predicted = mean_predicted,
    calibration_in_the_large = calibration_intercept, calibration_slope = calibration_slope,
    brier_score = weighted_mean((predicted - y) ^ 2, weight), auroc = weighted_auc(y, predicted, weight),
    pass_fail_status = calibration_status(calibration_slope, observed, mean_predicted, sum(y)),
    notes = "Survey-weighted apparent calibration for fever sparse-cell validation.", stringsAsFactors = FALSE)

  order_index <- order(predicted)
  decile <- rep(NA_integer_, length(predicted))
  decile[order_index] <- pmin(10L, pmax(1L, ceiling(cumsum(weight[order_index]) / sum(weight) * 10L)))
  deciles <- empty_deciles()
  for (group in sort(unique(decile))) {
    subset <- decile == group
    observed_rate <- weighted_mean(y[subset], weight[subset])
    ci <- normal_ci(observed_rate, sum(subset))
    deciles <- rbind(deciles, data.frame(model_id = spec$model_id, dataset = DATASET, data_scope = spec$data_scope,
      decile = group, n = sum(subset), events = sum(y[subset]),
      mean_predicted = weighted_mean(predicted[subset], weight[subset]), observed_rate = observed_rate,
      ci_low = ci[[1]], ci_high = ci[[2]],
      notes = "Survey-weighted decile calibration; CI is approximate unweighted normal interval.", stringsAsFactors = FALSE))
  }
  list(fit = fit, model_frame = model_frame, coefficients = coefficients, covariance = covariance_rows,
    draws = mvn_draws(spec$model_id, beta, covariance, parsed_terms), calibration = calibration,
    deciles = deciles, fit_error = NULL)
}

counts_for_frame <- function(frame, year_value = NA_character_) {
  rows <- data.frame()
  for (status in c("0", "1", "missing")) {
    subset <- if (identical(status, "missing")) is.na(frame$fever_or_temp) else !is.na(frame$fever_or_temp) & frame$fever_or_temp == as.numeric(status)
    part <- frame[subset, , drop = FALSE]
    rows <- rbind(rows, data.frame(dataset = DATASET, year = year_value, fever_or_temp = status,
      n = nrow(part), admissions = if (nrow(part) > 0) sum(part$admit == 1) else 0,
      non_admissions = if (nrow(part) > 0) sum(part$admit == 0) else 0,
      weighted_n = if (nrow(part) > 0) sum(part$weight) else 0,
      weighted_admissions = if (nrow(part) > 0) sum(part$weight[part$admit == 1]) else 0,
      stringsAsFactors = FALSE))
  }
  rows
}
sparse_counts <- do.call(rbind, c(list(counts_for_frame(binary, "pooled")),
  lapply(sort(unique(binary$year)), function(year) counts_for_frame(binary[binary$year == year, , drop = FALSE], as.character(year)))))
missing_audit <- aggregate(weight ~ year + endpoint_class + admit + temp_status, data = binary,
  FUN = function(value) c(n = length(value), weighted_n = sum(value)))
missing_audit <- do.call(data.frame, missing_audit)
names(missing_audit)[names(missing_audit) == "weight.n"] <- "n"
names(missing_audit)[names(missing_audit) == "weight.weighted_n"] <- "weighted_n"
missing_audit$dataset <- DATASET
missing_audit <- missing_audit[, c("dataset", "year", "endpoint_class", "admit", "temp_status", "n", "weighted_n")]

fit_results <- lapply(MODEL_SPECS, fit_one_model, frame = binary)
names(fit_results) <- vapply(MODEL_SPECS, function(spec) spec$model_id, character(1))
coefficients <- do.call(rbind, lapply(fit_results, function(item) item$coefficients))
covariance <- do.call(rbind, lapply(fit_results, function(item) item$covariance))
draws <- do.call(rbind, lapply(fit_results, function(item) item$draws))
calibration <- do.call(rbind, lapply(fit_results, function(item) item$calibration))
deciles <- do.call(rbind, lapply(fit_results, function(item) item$deciles))

fever_row <- function(rows) {
  candidates <- rows[rows$model_id == "fever_candidate_complete_temp" & rows$term == "fever_or_temp", , drop = FALSE]
  if (nrow(candidates) == 0) return(NULL)
  candidates[1, , drop = FALSE]
}

heldout_metric_row <- function(spec, train, test, heldout_year) {
  train_fever <- train[!is.na(train$fever_or_temp) & train$fever_or_temp == 1, , drop = FALSE]
  test_fever <- test[!is.na(test$fever_or_temp) & test$fever_or_temp == 1, , drop = FALSE]
  blocked_row <- function(status, note) data.frame(heldout_year = heldout_year, model_id = spec$model_id, dataset = DATASET,
    train_n = nrow(train), train_events = if (nrow(train) > 0) sum(train$admit) else 0,
    train_fever_positive_n = nrow(train_fever),
    train_fever_positive_events = if (nrow(train_fever) > 0) sum(train_fever$admit == 1) else 0,
    train_fever_positive_non_events = if (nrow(train_fever) > 0) sum(train_fever$admit == 0) else 0,
    heldout_n = nrow(test), heldout_events = if (nrow(test) > 0) sum(test$admit) else 0,
    heldout_fever_positive_n = nrow(test_fever),
    heldout_fever_positive_events = if (nrow(test_fever) > 0) sum(test_fever$admit == 1) else 0,
    heldout_fever_positive_non_events = if (nrow(test_fever) > 0) sum(test_fever$admit == 0) else 0,
    observed_prevalence = NA_real_, mean_predicted = NA_real_, calibration_in_the_large = NA_real_,
    calibration_slope = NA_real_, brier_score = NA_real_, auroc = NA_real_, fever_beta = NA_real_,
    fever_se = NA_real_, fever_or = NA_real_, fever_ci_low = NA_real_, fever_ci_high = NA_real_,
    pass_fail_status = status, evidence_tier = "survey_weighted_candidate", notes = note, stringsAsFactors = FALSE)
  if (nrow(train) == 0 || nrow(test) == 0 || length(unique(train$admit)) < 2) {
    return(blocked_row("blocked_no_train_or_test_outcome_variation", "Leave-one-year-out fever validation."))
  }
  result <- fit_one_model(spec, train)
  if (is.null(result$fit)) return(blocked_row("blocked_fit_failed", paste("Leave-one-year-out fever validation fit failed:", result$fit_error)))
  predicted <- as.numeric(stats::predict(result$fit, newdata = test, type = "response"))
  y <- test$admit
  weight <- test$weight
  linear_prediction <- logit(predicted)
  calibration_intercept <- NA_real_
  calibration_slope <- NA_real_
  if (length(unique(y)) >= 2 && length(unique(linear_prediction)) >= 2) {
    calibration_frame <- test
    calibration_frame$.__linear_prediction <- linear_prediction
    calibration_design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = calibration_frame)
    intercept_fit <- survey::svyglm(admit ~ 1 + offset(.__linear_prediction), design = calibration_design, family = quasibinomial())
    slope_fit <- survey::svyglm(admit ~ .__linear_prediction, design = calibration_design, family = quasibinomial())
    calibration_intercept <- as.numeric(stats::coef(intercept_fit)[[1]])
    calibration_slope <- as.numeric(stats::coef(slope_fit)[[".__linear_prediction"]])
  }
  fever <- fever_row(result$coefficients)
  data.frame(heldout_year = heldout_year, model_id = spec$model_id, dataset = DATASET,
    train_n = nrow(train), train_events = sum(train$admit), train_fever_positive_n = nrow(train_fever),
    train_fever_positive_events = if (nrow(train_fever) > 0) sum(train_fever$admit == 1) else 0,
    train_fever_positive_non_events = if (nrow(train_fever) > 0) sum(train_fever$admit == 0) else 0,
    heldout_n = nrow(test), heldout_events = sum(test$admit), heldout_fever_positive_n = nrow(test_fever),
    heldout_fever_positive_events = if (nrow(test_fever) > 0) sum(test_fever$admit == 1) else 0,
    heldout_fever_positive_non_events = if (nrow(test_fever) > 0) sum(test_fever$admit == 0) else 0,
    observed_prevalence = weighted_mean(y, weight), mean_predicted = weighted_mean(predicted, weight),
    calibration_in_the_large = calibration_intercept, calibration_slope = calibration_slope,
    brier_score = weighted_mean((predicted - y) ^ 2, weight), auroc = weighted_auc(y, predicted, weight),
    fever_beta = if (is.null(fever)) NA_real_ else fever$beta[[1]],
    fever_se = if (is.null(fever)) NA_real_ else fever$se[[1]],
    fever_or = if (is.null(fever)) NA_real_ else fever$odds_ratio[[1]],
    fever_ci_low = if (is.null(fever)) NA_real_ else fever$ci_low[[1]],
    fever_ci_high = if (is.null(fever)) NA_real_ else fever$ci_high[[1]],
    pass_fail_status = calibration_status(calibration_slope, weighted_mean(y, weight), weighted_mean(predicted, weight), sum(y)),
    evidence_tier = "survey_weighted_candidate",
    notes = "Leave-one-year-out fever validation on complete-temperature rows.", stringsAsFactors = FALSE)
}

leave_one_year_out <- data.frame()
validation_specs <- MODEL_SPECS[vapply(MODEL_SPECS, function(spec) spec$model_id %in% c("fever_base_complete_temp", "fever_candidate_complete_temp"), logical(1))]
for (heldout_year in sort(unique(complete_temp$year))) {
  train <- complete_temp[complete_temp$year != heldout_year, , drop = FALSE]
  test <- complete_temp[complete_temp$year == heldout_year, , drop = FALSE]
  for (spec in validation_specs) {
    leave_one_year_out <- rbind(leave_one_year_out, heldout_metric_row(spec, train, test, heldout_year))
  }
}

calibration_row <- function(model_id) {
  rows <- calibration[calibration$model_id == model_id, , drop = FALSE]
  if (nrow(rows) == 0) return(NULL)
  rows[1, , drop = FALSE]
}
base_calibration <- calibration_row("fever_base_complete_temp")
fever_calibration <- calibration_row("fever_candidate_complete_temp")
pooled_fever_counts <- sparse_counts[sparse_counts$year == "pooled" & sparse_counts$fever_or_temp == "1", , drop = FALSE]
pooled_fever_positive_n <- if (nrow(pooled_fever_counts) > 0) pooled_fever_counts$n[[1]] else 0
pooled_fever_positive_events <- if (nrow(pooled_fever_counts) > 0) pooled_fever_counts$admissions[[1]] else 0
pooled_fever_positive_nonevents <- if (nrow(pooled_fever_counts) > 0) pooled_fever_counts$non_admissions[[1]] else 0
fever_coef <- fever_row(coefficients)
fever_draws <- draws[draws$model_id == "fever_candidate_complete_temp" & draws$term == "fever_or_temp", , drop = FALSE]
prob_beta_positive <- if (nrow(fever_draws) > 0) mean(fever_draws$beta > 0) else NA_real_

fever_loo <- leave_one_year_out[leave_one_year_out$model_id == "fever_candidate_complete_temp", , drop = FALSE]
base_loo <- leave_one_year_out[leave_one_year_out$model_id == "fever_base_complete_temp", , drop = FALSE]
merged_loo <- merge(base_loo, fever_loo, by = "heldout_year", suffixes = c("_base", "_fever"), sort = TRUE)
heldout_brier_worsening <- if (nrow(merged_loo) > 0) weighted_mean(merged_loo$brier_score_fever - merged_loo$brier_score_base, merged_loo$heldout_n_base) else NA_real_
heldout_auroc_change <- if (nrow(merged_loo) > 0) weighted_mean(merged_loo$auroc_fever - merged_loo$auroc_base, merged_loo$heldout_n_base) else NA_real_
heldout_status_degraded <- if (nrow(merged_loo) > 0) any(mapply(status_degraded, merged_loo$pass_fail_status_base, merged_loo$pass_fail_status_fever), na.rm = TRUE) else TRUE
apparent_brier_worsening <- if (!is.null(base_calibration) && !is.null(fever_calibration)) fever_calibration$brier_score[[1]] - base_calibration$brier_score[[1]] else NA_real_
apparent_auroc_change <- if (!is.null(base_calibration) && !is.null(fever_calibration)) fever_calibration$auroc[[1]] - base_calibration$auroc[[1]] else NA_real_
apparent_status_degraded <- if (!is.null(base_calibration) && !is.null(fever_calibration)) status_degraded(base_calibration$pass_fail_status[[1]], fever_calibration$pass_fail_status[[1]]) else TRUE

positive_coefficient_gate <- !is.null(fever_coef) && is.finite(fever_coef$beta[[1]]) && fever_coef$beta[[1]] > 0
uncertainty_exported_gate <- !is.null(fever_coef) && nrow(covariance[covariance$model_id == "fever_candidate_complete_temp", , drop = FALSE]) > 0 &&
  length(unique(fever_draws$draw_id)) == DRAW_COUNT && is.finite(prob_beta_positive) && prob_beta_positive >= MIN_PROB_BETA_POSITIVE
sparse_cell_gate <- pooled_fever_positive_n >= MIN_FEVER_POSITIVE_N &&
  pooled_fever_positive_events >= MIN_FEVER_POSITIVE_EVENTS &&
  pooled_fever_positive_nonevents >= MIN_FEVER_POSITIVE_NONEVENTS
training_split_gate <- nrow(fever_loo) == length(unique(complete_temp$year)) &&
  all(fever_loo$train_fever_positive_events >= MIN_FEVER_POSITIVE_EVENTS, na.rm = FALSE) &&
  all(fever_loo$train_fever_positive_non_events >= MIN_FEVER_POSITIVE_NONEVENTS, na.rm = FALSE)
loo_stability_gate <- nrow(fever_loo) == length(unique(complete_temp$year)) &&
  all(!startsWith(fever_loo$pass_fail_status, "blocked")) &&
  all(is.finite(fever_loo$fever_beta)) && all(fever_loo$fever_beta > 0) &&
  all(is.finite(fever_loo$fever_ci_high)) && all(fever_loo$fever_ci_high <= MAX_OR_CI_HIGH)
calibration_no_worse_gate <- is.finite(apparent_brier_worsening) && apparent_brier_worsening <= MAX_BRIER_WORSENING &&
  is.finite(apparent_auroc_change) && apparent_auroc_change >= -MAX_AUROC_WORSENING && !apparent_status_degraded &&
  is.finite(heldout_brier_worsening) && heldout_brier_worsening <= MAX_BRIER_WORSENING &&
  is.finite(heldout_auroc_change) && heldout_auroc_change >= -MAX_AUROC_WORSENING && !heldout_status_degraded
missing_temperature_gate <- nrow(missing_audit) > 0 && !is.null(fever_calibration) &&
  fever_calibration$n[[1]] == nrow(complete_temp) &&
  sum(binary$temp_status == "temp_missing") == nrow(binary[is.na(binary$fever_or_temp), , drop = FALSE])
mapping_or_fitting_blocked <- is.null(fever_coef) || is.null(base_calibration) || is.null(fever_calibration) || !missing_temperature_gate
all_gates <- positive_coefficient_gate && uncertainty_exported_gate && sparse_cell_gate && training_split_gate &&
  loo_stability_gate && calibration_no_worse_gate && missing_temperature_gate
promotion_status <- if (mapping_or_fitting_blocked) {
  "blocked"
} else if (all_gates) {
  "eligible_for_evidence_promotion"
} else if (positive_coefficient_gate) {
  "sensitivity_only"
} else {
  "blocked"
}

gate_rows <- data.frame(
  gate = c("positive_pooled_coefficient", "uncertainty_exported", "sparse_cell_adequacy",
    "training_split_adequacy", "leave_one_year_out_stability", "calibration_no_worse",
    "missing_temperature_handled", "promotion_suitability"),
  passed = c(positive_coefficient_gate, uncertainty_exported_gate, sparse_cell_gate, training_split_gate,
    loo_stability_gate, calibration_no_worse_gate, missing_temperature_gate, identical(promotion_status, "eligible_for_evidence_promotion")),
  status = c(ifelse(positive_coefficient_gate, "pass", "fail"), ifelse(uncertainty_exported_gate, "pass", "fail"),
    ifelse(sparse_cell_gate, "pass", "fail"), ifelse(training_split_gate, "pass", "fail"),
    ifelse(loo_stability_gate, "pass", "fail"), ifelse(calibration_no_worse_gate, "pass", "fail"),
    ifelse(missing_temperature_gate, "pass", "fail"), promotion_status),
  metric = c(if (!is.null(fever_coef)) fever_coef$beta[[1]] else NA_real_, prob_beta_positive,
    pooled_fever_positive_events, if (nrow(fever_loo) > 0) min(fever_loo$train_fever_positive_events) else NA_real_,
    if (nrow(fever_loo) > 0) max(fever_loo$fever_ci_high, na.rm = TRUE) else NA_real_,
    apparent_brier_worsening, sum(binary$temp_status == "temp_missing"), NA_real_),
  threshold = c("> 0", paste0(">= ", MIN_PROB_BETA_POSITIVE, " with ", DRAW_COUNT, " draws"),
    paste0("fever n >= ", MIN_FEVER_POSITIVE_N, "; events >= ", MIN_FEVER_POSITIVE_EVENTS, "; non-events >= ", MIN_FEVER_POSITIVE_NONEVENTS),
    paste0("each training split fever events/non-events >= ", MIN_FEVER_POSITIVE_EVENTS, "/", MIN_FEVER_POSITIVE_NONEVENTS),
    paste0("all LOO fever betas > 0 and OR CI high <= ", MAX_OR_CI_HIGH),
    paste0("Brier worsening <= ", MAX_BRIER_WORSENING, "; AUROC change >= -", MAX_AUROC_WORSENING, "; no pass-to-fail degradation"),
    "missing fever_or_temp excluded from primary model and audited", "all gates pass"),
  details = c(
    if (!is.null(fever_coef)) paste0("beta=", signif(fever_coef$beta[[1]], 6), ", se=", signif(fever_coef$se[[1]], 6), ", OR=", signif(fever_coef$odds_ratio[[1]], 6)) else "fever coefficient unavailable",
    paste0("draws=", length(unique(fever_draws$draw_id)), ", Pr(beta>0)=", signif(prob_beta_positive, 6)),
    paste0("pooled fever n=", pooled_fever_positive_n, ", events=", pooled_fever_positive_events, ", non-events=", pooled_fever_positive_nonevents),
    if (nrow(fever_loo) > 0) paste0("minimum train fever events=", min(fever_loo$train_fever_positive_events), ", minimum train fever non-events=", min(fever_loo$train_fever_positive_non_events)) else "LOO rows unavailable",
    if (nrow(fever_loo) > 0) paste0("finite positive beta years=", sum(is.finite(fever_loo$fever_beta) & fever_loo$fever_beta > 0), "/", nrow(fever_loo), ", max OR CI high=", signif(max(fever_loo$fever_ci_high, na.rm = TRUE), 6)) else "LOO rows unavailable",
    paste0("apparent Brier worsening=", signif(apparent_brier_worsening, 6), ", apparent AUROC change=", signif(apparent_auroc_change, 6), ", held-out Brier worsening=", signif(heldout_brier_worsening, 6), ", held-out AUROC change=", signif(heldout_auroc_change, 6)),
    paste0("missing temp rows=", sum(binary$temp_status == "temp_missing"), ", complete-temp model n=", if (!is.null(fever_calibration)) fever_calibration$n[[1]] else NA_integer_),
    paste0("final fever promotion gate status: ", promotion_status)),
  evidence_tier = "survey_weighted_candidate",
  stringsAsFactors = FALSE
)

format_number <- function(value, digits = 4) {
  if (is.na(value) || !is.finite(value)) return("")
  format(round(value, digits), nsmall = digits, trim = TRUE)
}
markdown_gate_table <- function(rows) {
  lines <- c("| Gate | Passed | Status | Metric | Threshold |", "|---|---:|---|---:|---|")
  for (index in seq_len(nrow(rows))) {
    row <- rows[index, ]
    lines <- c(lines, paste0("| `", row$gate, "` | ", tolower(as.character(row$passed)), " | `",
      row$status, "` | ", format_number(row$metric, 6), " | ", row$threshold, " |"))
  }
  lines
}
markdown_calibration_table <- function(rows) {
  lines <- c("| Model | Scope | N | Events | Observed | Mean predicted | Cal intercept | Cal slope | Brier | AUROC | Status |",
    "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
  for (index in seq_len(nrow(rows))) {
    row <- rows[index, ]
    lines <- c(lines, paste0("| `", row$model_id, "` | `", row$data_scope, "` | ", row$n, " | ", row$events, " | ",
      format_number(row$observed_prevalence), " | ", format_number(row$mean_predicted), " | ",
      format_number(row$calibration_in_the_large, 6), " | ", format_number(row$calibration_slope), " | ",
      format_number(row$brier_score), " | ", format_number(row$auroc), " | `", row$pass_fail_status, "` |"))
  }
  lines
}

report <- c(
  "# Fever Sparse-Cell Validation Gate", "",
  paste0("Dataset: `", DATASET, "`"), "",
  paste0("Decision: `", promotion_status, "`."), "",
  "This gate evaluates objective binary fever from valid `TEMPF` only. Missing temperature is not recoded as no fever. All coefficients remain `survey_weighted_candidate`.",
  "", "## Gate Summary", "", markdown_gate_table(gate_rows),
  "", "## Model Comparison", "", markdown_calibration_table(calibration),
  "", "## Fever Coefficient", "",
  if (!is.null(fever_coef)) paste0("- Pooled fever coefficient: beta ", format_number(fever_coef$beta[[1]], 4),
    ", SE ", format_number(fever_coef$se[[1]], 4), ", OR ", format_number(fever_coef$odds_ratio[[1]], 3),
    ", 95% CI ", format_number(fever_coef$ci_low[[1]], 3), " to ", format_number(fever_coef$ci_high[[1]], 3), ".") else "- Pooled fever coefficient was not estimated.",
  paste0("- MVN draw probability beta > 0: ", format_number(prob_beta_positive, 4), "."),
  "", "## Sparse Cells", "",
  paste0("- Pooled fever-positive N: ", pooled_fever_positive_n, "."),
  paste0("- Pooled fever-positive admissions: ", pooled_fever_positive_events, "."),
  paste0("- Pooled fever-positive non-admissions: ", pooled_fever_positive_nonevents, "."),
  "", "## Calibration No-Worse Check", "",
  paste0("- Apparent Brier worsening vs base: ", format_number(apparent_brier_worsening, 6), "."),
  paste0("- Apparent AUROC change vs base: ", format_number(apparent_auroc_change, 6), "."),
  paste0("- Held-out Brier worsening vs base: ", format_number(heldout_brier_worsening, 6), "."),
  paste0("- Held-out AUROC change vs base: ", format_number(heldout_auroc_change, 6), "."),
  "", "## Missing Temperature", "",
  paste0("- Missing temperature rows: ", sum(binary$temp_status == "temp_missing"), "."),
  paste0("- Complete-temperature primary fever model rows: ", if (!is.null(fever_calibration)) fever_calibration$n[[1]] else NA_integer_, "."),
  "", "## Boundary", "",
  "- Passing this gate means fever is eligible for later evidence-engine review, not automatically promoted.",
  "- Failing this gate keeps fever as sensitivity-only or blocked according to the decision row.",
  "- This output does not claim clinical validity."
)

utils::write.csv(sparse_counts, file.path(output_dir, "fever_sparse_cell_counts_by_year.csv"), row.names = FALSE, na = "")
utils::write.csv(missing_audit, file.path(output_dir, "fever_missing_temperature_audit.csv"), row.names = FALSE, na = "")
utils::write.csv(coefficients, file.path(output_dir, "fever_model_comparison_coefficients.csv"), row.names = FALSE, na = "")
utils::write.csv(covariance, file.path(output_dir, "fever_model_comparison_covariance.csv"), row.names = FALSE, na = "")
utils::write.csv(draws, file.path(output_dir, "fever_model_comparison_draws.csv"), row.names = FALSE, na = "")
utils::write.csv(calibration, file.path(output_dir, "fever_model_comparison_calibration.csv"), row.names = FALSE, na = "")
utils::write.csv(deciles, file.path(output_dir, "fever_model_comparison_deciles.csv"), row.names = FALSE, na = "")
utils::write.csv(leave_one_year_out, file.path(output_dir, "fever_leave_one_year_out_validation.csv"), row.names = FALSE, na = "")
utils::write.csv(gate_rows, file.path(output_dir, "fever_sparse_cell_gate_decision.csv"), row.names = FALSE, na = "")
writeLines(report, con = file.path(output_dir, "fever_sparse_cell_validation_report.md"))

cat("Wrote fever sparse-cell validation outputs under ", output_dir, "\n", sep = "")
