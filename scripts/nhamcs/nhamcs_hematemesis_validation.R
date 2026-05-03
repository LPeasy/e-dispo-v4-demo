#!/usr/bin/env Rscript

# Hematemesis validation gate for pooled NHAMCS.
# Hematemesis is RFV 15802 only. Ordinary vomiting RFV 15300 remains in the base model.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: nhamcs_hematemesis_validation.R <pooled_analytic_cohort_csv> <output_dir>")
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
RANDOM_SEED <- 20260430L
DRAW_COUNT <- 10000L
MIN_POSITIVE_N <- 30L
MIN_POSITIVE_EVENTS <- 10L
MIN_POSITIVE_NONEVENTS <- 10L
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
              "fever_or_temp", "vomiting_present", "hematemesis_rfv_position_tier",
              "hematemesis_present", "pooled_weight", "pooled_stratum", "pooled_psu")
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
binary$hematemesis_present <- as.numeric(binary$hematemesis_present)
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
binary$vomiting_present[is.na(binary$vomiting_present)] <- 0
binary$hematemesis_present[is.na(binary$hematemesis_present)] <- 0
binary$hematemesis_rfv_position_tier[is.na(binary$hematemesis_rfv_position_tier) | binary$hematemesis_rfv_position_tier == ""] <- "none"
binary$hematemesis_rfv_position_tier <- factor(binary$hematemesis_rfv_position_tier, levels = c("none", "secondary_rfv2_5", "primary_rfv1"))
complete_temp <- binary[!is.na(binary$fever_or_temp), , drop = FALSE]
if (nrow(complete_temp) == 0 || length(unique(complete_temp$admit)) < 2) {
  stop("No usable complete-temperature strict-binary records with outcome variation.")
}

MODEL_SPECS <- list(
  list(model_id = "hematemesis_base_complete_temp", formula = admit ~ age_centered + pain_bin3 + pain_missing + fever_or_temp + vomiting_present),
  list(model_id = "hematemesis_candidate_binary_complete_temp", formula = admit ~ age_centered + pain_bin3 + pain_missing + fever_or_temp + vomiting_present + hematemesis_present),
  list(model_id = "hematemesis_tier_sensitivity_complete_temp", formula = admit ~ age_centered + pain_bin3 + pain_missing + fever_or_temp + vomiting_present + hematemesis_rfv_position_tier)
)

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

parse_coefficient <- function(name) {
  if (identical(name, "(Intercept)")) return(list(term = "intercept", level = ""))
  if (identical(name, "age_centered")) return(list(term = "age_centered", level = "per_1_year_centered_at_42"))
  if (startsWith(name, "pain_bin3")) return(list(term = "pain_bin3", level = substring(name, nchar("pain_bin3") + 1)))
  if (identical(name, "pain_missing")) return(list(term = "pain_missing", level = "1"))
  if (identical(name, "fever_or_temp")) return(list(term = "fever_or_temp", level = "1"))
  if (identical(name, "vomiting_present")) return(list(term = "vomiting_present", level = "1"))
  if (identical(name, "hematemesis_present")) return(list(term = "hematemesis_present", level = "1"))
  if (startsWith(name, "hematemesis_rfv_position_tier")) {
    return(list(term = "hematemesis_rfv_position_tier", level = substring(name, nchar("hematemesis_rfv_position_tier") + 1)))
  }
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

fit_one_model <- function(spec, frame) {
  model_frame <- frame[!is.na(frame$age_centered) & !is.na(frame$pain_bin3) &
    !is.na(frame$pain_missing) & !is.na(frame$fever_or_temp) &
    !is.na(frame$weight) & frame$weight > 0 & !is.na(frame$stratum) & !is.na(frame$psu), , drop = FALSE]
  blocked <- function(status, note) list(
    fit = NULL, model_frame = model_frame, coefficients = empty_coefficients(), covariance = empty_covariance(),
    draws = empty_draws(),
    calibration = data.frame(model_id = spec$model_id, dataset = DATASET, n = nrow(model_frame),
      events = if (nrow(model_frame) > 0) sum(model_frame$admit) else 0,
      observed_prevalence = NA_real_, mean_predicted = NA_real_, calibration_in_the_large = NA_real_,
      calibration_slope = NA_real_, brier_score = NA_real_, auroc = NA_real_, pass_fail_status = status,
      notes = note, stringsAsFactors = FALSE),
    deciles = empty_deciles(), fit_error = note
  )
  if (nrow(model_frame) == 0 || length(unique(model_frame$admit)) < 2) {
    return(blocked("blocked_no_outcome_variation", "No usable binary outcome variation after hematemesis-gate model filtering."))
  }
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = model_frame)
  fit_error <- NULL
  fit <- tryCatch(survey::svyglm(spec$formula, design = design, family = quasibinomial()),
    error = function(error) { fit_error <<- conditionMessage(error); NULL })
  if (is.null(fit)) return(blocked("blocked_fit_failed", paste("survey::svyglm failed:", fit_error)))

  coef_table <- summary(fit)$coefficients
  beta <- stats::coef(fit)
  covariance <- stats::vcov(fit)
  if (any(!is.finite(beta)) || any(!is.finite(covariance))) {
    return(blocked("blocked_nonfinite_coefficients", "survey::svyglm produced non-finite hematemesis-gate coefficient or covariance values."))
  }
  parsed_terms <- lapply(names(beta), parse_coefficient)
  labels <- vapply(parsed_terms, coefficient_label, character(1))
  se <- sqrt(pmax(diag(covariance), 0))
  coefficients <- data.frame(model_id = spec$model_id, dataset = DATASET,
    term = vapply(parsed_terms, function(item) item$term, character(1)),
    level = vapply(parsed_terms, function(item) item$level, character(1)),
    beta = as.numeric(beta), se = as.numeric(se), odds_ratio = exp(as.numeric(beta)),
    ci_low = exp(as.numeric(beta) - 1.96 * as.numeric(se)), ci_high = exp(as.numeric(beta) + 1.96 * as.numeric(se)),
    p_value = as.numeric(coef_table[, ncol(coef_table)]), evidence_tier = "survey_weighted_candidate",
    limitation_note = "Hematemesis validation only; no coefficient promotion or app activation.",
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
  calibration <- data.frame(model_id = spec$model_id, dataset = DATASET,
    n = nrow(model_frame), events = sum(y), observed_prevalence = observed, mean_predicted = mean_predicted,
    calibration_in_the_large = calibration_intercept, calibration_slope = calibration_slope,
    brier_score = weighted_mean((predicted - y) ^ 2, weight), auroc = weighted_auc(y, predicted, weight),
    pass_fail_status = calibration_status(calibration_slope, observed, mean_predicted, sum(y)),
    notes = "Survey-weighted apparent calibration for hematemesis validation.", stringsAsFactors = FALSE)

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
  list(fit = fit, model_frame = model_frame, coefficients = coefficients, covariance = covariance_rows,
    draws = mvn_draws(spec$model_id, beta, covariance, parsed_terms), calibration = calibration,
    deciles = deciles, fit_error = NULL)
}

count_row <- function(frame, group, level, subset, year_value = "pooled") {
  part <- frame[subset, , drop = FALSE]
  data.frame(dataset = DATASET, year = year_value, group = group, level = level,
    n = nrow(part), admissions = if (nrow(part) > 0) sum(part$admit == 1) else 0,
    non_admissions = if (nrow(part) > 0) sum(part$admit == 0) else 0,
    weighted_n = if (nrow(part) > 0) sum(part$weight) else 0,
    weighted_admissions = if (nrow(part) > 0) sum(part$weight[part$admit == 1]) else 0,
    stringsAsFactors = FALSE)
}
counts_for_frame <- function(frame, year_value = "pooled") {
  rows <- data.frame()
  rows <- rbind(rows, count_row(frame, "hematemesis_present", "0", frame$hematemesis_present == 0, year_value))
  rows <- rbind(rows, count_row(frame, "hematemesis_present", "1", frame$hematemesis_present == 1, year_value))
  for (level in c("none", "secondary_rfv2_5", "primary_rfv1")) {
    rows <- rbind(rows, count_row(frame, "hematemesis_rfv_position_tier", level, as.character(frame$hematemesis_rfv_position_tier) == level, year_value))
  }
  rows <- rbind(rows, count_row(frame, "vomiting_present_context", "1", frame$vomiting_present == 1, year_value))
  rows
}
cell_counts <- do.call(rbind, c(list(counts_for_frame(complete_temp, "pooled")),
  lapply(sort(unique(complete_temp$year)), function(year) counts_for_frame(complete_temp[complete_temp$year == year, , drop = FALSE], as.character(year)))))

unadjusted_rates <- cell_counts
unadjusted_rates$admit_rate <- ifelse(unadjusted_rates$n > 0, unadjusted_rates$admissions / unadjusted_rates$n, NA_real_)
unadjusted_rates$weighted_admit_rate <- ifelse(unadjusted_rates$weighted_n > 0, unadjusted_rates$weighted_admissions / unadjusted_rates$weighted_n, NA_real_)

fit_results <- lapply(MODEL_SPECS, fit_one_model, frame = complete_temp)
names(fit_results) <- vapply(MODEL_SPECS, function(spec) spec$model_id, character(1))
coefficients <- do.call(rbind, lapply(fit_results, function(item) item$coefficients))
covariance <- do.call(rbind, lapply(fit_results, function(item) item$covariance))
draws <- do.call(rbind, lapply(fit_results, function(item) item$draws))
calibration <- do.call(rbind, lapply(fit_results, function(item) item$calibration))
deciles <- do.call(rbind, lapply(fit_results, function(item) item$deciles))

coefficient_row <- function(rows, model_id, term, level = "1") {
  selected <- rows[rows$model_id == model_id & rows$term == term & as.character(rows$level) == as.character(level), , drop = FALSE]
  if (nrow(selected) == 0) return(NULL)
  selected[1, , drop = FALSE]
}
calibration_row <- function(model_id) {
  rows <- calibration[calibration$model_id == model_id, , drop = FALSE]
  if (nrow(rows) == 0) return(NULL)
  rows[1, , drop = FALSE]
}

heldout_metric_row <- function(spec, train, test, heldout_year) {
  train_hema <- train[train$hematemesis_present == 1, , drop = FALSE]
  test_hema <- test[test$hematemesis_present == 1, , drop = FALSE]
  blocked_row <- function(status, note) data.frame(heldout_year = heldout_year, model_id = spec$model_id, dataset = DATASET,
    train_n = nrow(train), train_events = if (nrow(train) > 0) sum(train$admit) else 0,
    train_hematemesis_positive_n = nrow(train_hema),
    train_hematemesis_positive_events = if (nrow(train_hema) > 0) sum(train_hema$admit == 1) else 0,
    train_hematemesis_positive_non_events = if (nrow(train_hema) > 0) sum(train_hema$admit == 0) else 0,
    heldout_n = nrow(test), heldout_events = if (nrow(test) > 0) sum(test$admit) else 0,
    heldout_hematemesis_positive_n = nrow(test_hema),
    heldout_hematemesis_positive_events = if (nrow(test_hema) > 0) sum(test_hema$admit == 1) else 0,
    heldout_hematemesis_positive_non_events = if (nrow(test_hema) > 0) sum(test_hema$admit == 0) else 0,
    observed_prevalence = NA_real_, mean_predicted = NA_real_, calibration_in_the_large = NA_real_,
    calibration_slope = NA_real_, brier_score = NA_real_, auroc = NA_real_, hematemesis_beta = NA_real_,
    hematemesis_se = NA_real_, hematemesis_or = NA_real_, hematemesis_ci_low = NA_real_, hematemesis_ci_high = NA_real_,
    pass_fail_status = status, evidence_tier = "survey_weighted_candidate", notes = note, stringsAsFactors = FALSE)
  if (nrow(train) == 0 || nrow(test) == 0 || length(unique(train$admit)) < 2) {
    return(blocked_row("blocked_no_train_or_test_outcome_variation", "Leave-one-year-out hematemesis validation."))
  }
  result <- fit_one_model(spec, train)
  if (is.null(result$fit)) return(blocked_row("blocked_fit_failed", paste("Leave-one-year-out hematemesis validation fit failed:", result$fit_error)))
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
  hema <- coefficient_row(result$coefficients, spec$model_id, "hematemesis_present", "1")
  data.frame(heldout_year = heldout_year, model_id = spec$model_id, dataset = DATASET,
    train_n = nrow(train), train_events = sum(train$admit), train_hematemesis_positive_n = nrow(train_hema),
    train_hematemesis_positive_events = if (nrow(train_hema) > 0) sum(train_hema$admit == 1) else 0,
    train_hematemesis_positive_non_events = if (nrow(train_hema) > 0) sum(train_hema$admit == 0) else 0,
    heldout_n = nrow(test), heldout_events = sum(test$admit), heldout_hematemesis_positive_n = nrow(test_hema),
    heldout_hematemesis_positive_events = if (nrow(test_hema) > 0) sum(test_hema$admit == 1) else 0,
    heldout_hematemesis_positive_non_events = if (nrow(test_hema) > 0) sum(test_hema$admit == 0) else 0,
    observed_prevalence = weighted_mean(y, weight), mean_predicted = weighted_mean(predicted, weight),
    calibration_in_the_large = calibration_intercept, calibration_slope = calibration_slope,
    brier_score = weighted_mean((predicted - y) ^ 2, weight), auroc = weighted_auc(y, predicted, weight),
    hematemesis_beta = if (is.null(hema)) NA_real_ else hema$beta[[1]],
    hematemesis_se = if (is.null(hema)) NA_real_ else hema$se[[1]],
    hematemesis_or = if (is.null(hema)) NA_real_ else hema$odds_ratio[[1]],
    hematemesis_ci_low = if (is.null(hema)) NA_real_ else hema$ci_low[[1]],
    hematemesis_ci_high = if (is.null(hema)) NA_real_ else hema$ci_high[[1]],
    pass_fail_status = calibration_status(calibration_slope, weighted_mean(y, weight), weighted_mean(predicted, weight), sum(y)),
    evidence_tier = "survey_weighted_candidate",
    notes = "Leave-one-year-out hematemesis validation on complete-temperature rows.", stringsAsFactors = FALSE)
}

leave_one_year_out <- data.frame()
validation_specs <- MODEL_SPECS[vapply(MODEL_SPECS, function(spec) spec$model_id %in% c("hematemesis_base_complete_temp", "hematemesis_candidate_binary_complete_temp"), logical(1))]
for (heldout_year in sort(unique(complete_temp$year))) {
  train <- complete_temp[complete_temp$year != heldout_year, , drop = FALSE]
  test <- complete_temp[complete_temp$year == heldout_year, , drop = FALSE]
  for (spec in validation_specs) {
    leave_one_year_out <- rbind(leave_one_year_out, heldout_metric_row(spec, train, test, heldout_year))
  }
}

base_calibration <- calibration_row("hematemesis_base_complete_temp")
candidate_calibration <- calibration_row("hematemesis_candidate_binary_complete_temp")
tier_calibration <- calibration_row("hematemesis_tier_sensitivity_complete_temp")
pooled_hematemesis_counts <- cell_counts[cell_counts$year == "pooled" & cell_counts$group == "hematemesis_present" & cell_counts$level == "1", , drop = FALSE]
pooled_hematemesis_positive_n <- if (nrow(pooled_hematemesis_counts) > 0) pooled_hematemesis_counts$n[[1]] else 0
pooled_hematemesis_positive_events <- if (nrow(pooled_hematemesis_counts) > 0) pooled_hematemesis_counts$admissions[[1]] else 0
pooled_hematemesis_positive_nonevents <- if (nrow(pooled_hematemesis_counts) > 0) pooled_hematemesis_counts$non_admissions[[1]] else 0
hematemesis_coef <- coefficient_row(coefficients, "hematemesis_candidate_binary_complete_temp", "hematemesis_present", "1")
hematemesis_draws <- draws[draws$model_id == "hematemesis_candidate_binary_complete_temp" & draws$term == "hematemesis_present", , drop = FALSE]
prob_beta_positive <- if (nrow(hematemesis_draws) > 0) mean(hematemesis_draws$beta > 0) else NA_real_

candidate_loo <- leave_one_year_out[leave_one_year_out$model_id == "hematemesis_candidate_binary_complete_temp", , drop = FALSE]
base_loo <- leave_one_year_out[leave_one_year_out$model_id == "hematemesis_base_complete_temp", , drop = FALSE]
merged_loo <- merge(base_loo, candidate_loo, by = "heldout_year", suffixes = c("_base", "_hematemesis"), sort = TRUE)
heldout_brier_worsening <- if (nrow(merged_loo) > 0) weighted_mean(merged_loo$brier_score_hematemesis - merged_loo$brier_score_base, merged_loo$heldout_n_base) else NA_real_
heldout_auroc_change <- if (nrow(merged_loo) > 0) weighted_mean(merged_loo$auroc_hematemesis - merged_loo$auroc_base, merged_loo$heldout_n_base) else NA_real_
heldout_status_degraded <- if (nrow(merged_loo) > 0) any(mapply(status_degraded, merged_loo$pass_fail_status_base, merged_loo$pass_fail_status_hematemesis), na.rm = TRUE) else TRUE
apparent_brier_worsening <- if (!is.null(base_calibration) && !is.null(candidate_calibration)) candidate_calibration$brier_score[[1]] - base_calibration$brier_score[[1]] else NA_real_
apparent_auroc_change <- if (!is.null(base_calibration) && !is.null(candidate_calibration)) candidate_calibration$auroc[[1]] - base_calibration$auroc[[1]] else NA_real_
apparent_status_degraded <- if (!is.null(base_calibration) && !is.null(candidate_calibration)) status_degraded(base_calibration$pass_fail_status[[1]], candidate_calibration$pass_fail_status[[1]]) else TRUE

positive_coefficient_gate <- !is.null(hematemesis_coef) && is.finite(hematemesis_coef$beta[[1]]) && hematemesis_coef$beta[[1]] > 0
uncertainty_exported_gate <- !is.null(hematemesis_coef) && nrow(covariance[covariance$model_id == "hematemesis_candidate_binary_complete_temp", , drop = FALSE]) > 0 &&
  length(unique(hematemesis_draws$draw_id)) == DRAW_COUNT && is.finite(prob_beta_positive) && prob_beta_positive >= MIN_PROB_BETA_POSITIVE
sparse_cell_gate <- pooled_hematemesis_positive_n >= MIN_POSITIVE_N &&
  pooled_hematemesis_positive_events >= MIN_POSITIVE_EVENTS &&
  pooled_hematemesis_positive_nonevents >= MIN_POSITIVE_NONEVENTS
training_split_gate <- nrow(candidate_loo) == length(unique(complete_temp$year)) &&
  all(candidate_loo$train_hematemesis_positive_events >= MIN_POSITIVE_EVENTS, na.rm = FALSE) &&
  all(candidate_loo$train_hematemesis_positive_non_events >= MIN_POSITIVE_NONEVENTS, na.rm = FALSE)
loo_stability_gate <- nrow(candidate_loo) == length(unique(complete_temp$year)) &&
  all(!startsWith(candidate_loo$pass_fail_status, "blocked")) &&
  all(is.finite(candidate_loo$hematemesis_beta)) && all(candidate_loo$hematemesis_beta > 0) &&
  all(is.finite(candidate_loo$hematemesis_ci_high)) && all(candidate_loo$hematemesis_ci_high <= MAX_OR_CI_HIGH)
calibration_no_worse_gate <- is.finite(apparent_brier_worsening) && apparent_brier_worsening <= MAX_BRIER_WORSENING &&
  is.finite(apparent_auroc_change) && apparent_auroc_change >= -MAX_AUROC_WORSENING && !apparent_status_degraded &&
  is.finite(heldout_brier_worsening) && heldout_brier_worsening <= MAX_BRIER_WORSENING &&
  is.finite(heldout_auroc_change) && heldout_auroc_change >= -MAX_AUROC_WORSENING && !heldout_status_degraded
documentation_gate <- all(complete_temp$vomiting_present %in% c(0, 1)) &&
  all(complete_temp$hematemesis_present %in% c(0, 1)) &&
  all(as.character(complete_temp$hematemesis_rfv_position_tier) %in% c("none", "secondary_rfv2_5", "primary_rfv1"))

tier_counts <- cell_counts[cell_counts$year == "pooled" & cell_counts$group == "hematemesis_rfv_position_tier" &
  cell_counts$level %in% c("secondary_rfv2_5", "primary_rfv1"), , drop = FALSE]
tier_cell_gate <- nrow(tier_counts) == 2 && all(tier_counts$admissions >= MIN_POSITIVE_EVENTS) && all(tier_counts$non_admissions >= MIN_POSITIVE_NONEVENTS)
tier_brier_worsening_vs_binary <- if (!is.null(tier_calibration) && !is.null(candidate_calibration)) tier_calibration$brier_score[[1]] - candidate_calibration$brier_score[[1]] else NA_real_
tier_auroc_change_vs_binary <- if (!is.null(tier_calibration) && !is.null(candidate_calibration)) tier_calibration$auroc[[1]] - candidate_calibration$auroc[[1]] else NA_real_
tier_clearly_better <- tier_cell_gate && is.finite(tier_brier_worsening_vs_binary) && tier_brier_worsening_vs_binary <= -MAX_BRIER_WORSENING &&
  is.finite(tier_auroc_change_vs_binary) && tier_auroc_change_vs_binary >= MAX_AUROC_WORSENING
recommended_form <- if (tier_clearly_better) "tiered_rfv_position_sensitivity" else "binary_hematemesis_present"

mapping_or_fitting_blocked <- is.null(hematemesis_coef) || is.null(base_calibration) || is.null(candidate_calibration) || !documentation_gate
all_gates <- positive_coefficient_gate && uncertainty_exported_gate && sparse_cell_gate && training_split_gate &&
  loo_stability_gate && calibration_no_worse_gate && documentation_gate
promotion_status <- if (mapping_or_fitting_blocked) {
  "blocked"
} else if (all_gates) {
  "eligible_for_evidence_promotion"
} else if (positive_coefficient_gate) {
  "sensitivity_only"
} else {
  "blocked"
}

tier_sensitivity <- data.frame(
  dataset = DATASET,
  binary_model_id = "hematemesis_candidate_binary_complete_temp",
  tier_model_id = "hematemesis_tier_sensitivity_complete_temp",
  tier_cell_gate = tier_cell_gate,
  tier_brier_worsening_vs_binary = tier_brier_worsening_vs_binary,
  tier_auroc_change_vs_binary = tier_auroc_change_vs_binary,
  tier_clearly_better = tier_clearly_better,
  recommended_form = recommended_form,
  notes = "RFV position is documentation prominence, not hematemesis severity.",
  evidence_tier = "survey_weighted_candidate",
  stringsAsFactors = FALSE
)

gate_rows <- data.frame(
  gate = c("positive_pooled_coefficient", "uncertainty_exported", "sparse_cell_adequacy",
    "training_split_adequacy", "leave_one_year_out_stability", "calibration_no_worse",
    "documentation_handled", "tier_sensitivity", "promotion_suitability"),
  passed = c(positive_coefficient_gate, uncertainty_exported_gate, sparse_cell_gate, training_split_gate,
    loo_stability_gate, calibration_no_worse_gate, documentation_gate, !tier_clearly_better,
    identical(promotion_status, "eligible_for_evidence_promotion")),
  status = c(ifelse(positive_coefficient_gate, "pass", "fail"), ifelse(uncertainty_exported_gate, "pass", "fail"),
    ifelse(sparse_cell_gate, "pass", "fail"), ifelse(training_split_gate, "pass", "fail"),
    ifelse(loo_stability_gate, "pass", "fail"), ifelse(calibration_no_worse_gate, "pass", "fail"),
    ifelse(documentation_gate, "pass", "fail"),
    ifelse(tier_clearly_better, "tier_candidate_for_future_review", "binary_preferred_or_tier_not_better"),
    promotion_status),
  metric = c(if (!is.null(hematemesis_coef)) hematemesis_coef$beta[[1]] else NA_real_, prob_beta_positive,
    pooled_hematemesis_positive_events, if (nrow(candidate_loo) > 0) min(candidate_loo$train_hematemesis_positive_events) else NA_real_,
    if (nrow(candidate_loo) > 0) max(candidate_loo$hematemesis_ci_high, na.rm = TRUE) else NA_real_,
    apparent_brier_worsening, sum(complete_temp$hematemesis_present == 1), tier_brier_worsening_vs_binary, NA_real_),
  threshold = c("> 0", paste0(">= ", MIN_PROB_BETA_POSITIVE, " with ", DRAW_COUNT, " draws"),
    paste0("hematemesis n >= ", MIN_POSITIVE_N, "; events >= ", MIN_POSITIVE_EVENTS, "; non-events >= ", MIN_POSITIVE_NONEVENTS),
    paste0("each training split hematemesis events/non-events >= ", MIN_POSITIVE_EVENTS, "/", MIN_POSITIVE_NONEVENTS),
    paste0("all LOO hematemesis betas > 0 and OR CI high <= ", MAX_OR_CI_HIGH),
    paste0("Brier worsening <= ", MAX_BRIER_WORSENING, "; AUROC change >= -", MAX_AUROC_WORSENING, "; no pass-to-fail degradation"),
    "vomiting_present and hematemesis_present are separate binary RFV documentation flags",
    "tiered form must materially outperform binary and pass tier sparse-cell gates",
    "all binary hematemesis gates pass"),
  details = c(
    if (!is.null(hematemesis_coef)) paste0("beta=", signif(hematemesis_coef$beta[[1]], 6), ", se=", signif(hematemesis_coef$se[[1]], 6), ", OR=", signif(hematemesis_coef$odds_ratio[[1]], 6)) else "hematemesis coefficient unavailable",
    paste0("draws=", length(unique(hematemesis_draws$draw_id)), ", Pr(beta>0)=", signif(prob_beta_positive, 6)),
    paste0("pooled hematemesis n=", pooled_hematemesis_positive_n, ", events=", pooled_hematemesis_positive_events, ", non-events=", pooled_hematemesis_positive_nonevents),
    if (nrow(candidate_loo) > 0) paste0("minimum train hematemesis events=", min(candidate_loo$train_hematemesis_positive_events), ", minimum train hematemesis non-events=", min(candidate_loo$train_hematemesis_positive_non_events)) else "LOO rows unavailable",
    if (nrow(candidate_loo) > 0) paste0("finite positive beta years=", sum(is.finite(candidate_loo$hematemesis_beta) & candidate_loo$hematemesis_beta > 0), "/", nrow(candidate_loo), ", max OR CI high=", signif(max(candidate_loo$hematemesis_ci_high, na.rm = TRUE), 6)) else "LOO rows unavailable",
    paste0("apparent Brier worsening=", signif(apparent_brier_worsening, 6), ", apparent AUROC change=", signif(apparent_auroc_change, 6), ", held-out Brier worsening=", signif(heldout_brier_worsening, 6), ", held-out AUROC change=", signif(heldout_auroc_change, 6)),
    paste0("ordinary vomiting positives in base model=", sum(complete_temp$vomiting_present == 1), ", hematemesis positives=", sum(complete_temp$hematemesis_present == 1)),
    paste0("recommended form=", recommended_form, ", tier cell gate=", tier_cell_gate),
    paste0("final hematemesis promotion gate status: ", promotion_status)),
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
  lines <- c("| Model | N | Events | Observed | Mean predicted | Cal intercept | Cal slope | Brier | AUROC | Status |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
  for (index in seq_len(nrow(rows))) {
    row <- rows[index, ]
    lines <- c(lines, paste0("| `", row$model_id, "` | ", row$n, " | ", row$events, " | ",
      format_number(row$observed_prevalence), " | ", format_number(row$mean_predicted), " | ",
      format_number(row$calibration_in_the_large, 6), " | ", format_number(row$calibration_slope), " | ",
      format_number(row$brier_score), " | ", format_number(row$auroc), " | `", row$pass_fail_status, "` |"))
  }
  lines
}

report <- c(
  "# Hematemesis RFV Validation Gate", "",
  paste0("Dataset: `", DATASET, "`"), "",
  paste0("Decision: `", promotion_status, "`."), "",
  "This gate evaluates hematemesis from RFV code `15802` only. Ordinary vomiting RFV `15300` remains a separate base-model predictor.",
  "", "## Gate Summary", "", markdown_gate_table(gate_rows),
  "", "## Model Comparison", "", markdown_calibration_table(calibration),
  "", "## Hematemesis Coefficient", "",
  if (!is.null(hematemesis_coef)) paste0("- Pooled hematemesis coefficient: beta ", format_number(hematemesis_coef$beta[[1]], 4),
    ", SE ", format_number(hematemesis_coef$se[[1]], 4), ", OR ", format_number(hematemesis_coef$odds_ratio[[1]], 3),
    ", 95% CI ", format_number(hematemesis_coef$ci_low[[1]], 3), " to ", format_number(hematemesis_coef$ci_high[[1]], 3), ".") else "- Pooled hematemesis coefficient was not estimated.",
  paste0("- MVN draw probability beta > 0: ", format_number(prob_beta_positive, 4), "."),
  "", "## Sparse Cells", "",
  paste0("- Pooled hematemesis-positive N: ", pooled_hematemesis_positive_n, "."),
  paste0("- Pooled hematemesis-positive admissions: ", pooled_hematemesis_positive_events, "."),
  paste0("- Pooled hematemesis-positive non-admissions: ", pooled_hematemesis_positive_nonevents, "."),
  paste0("- Ordinary vomiting-positive N retained in the base model: ", sum(complete_temp$vomiting_present == 1), "."),
  "", "## Tier Sensitivity", "",
  paste0("- Recommended form: `", recommended_form, "`."),
  "- RFV position is documentation prominence/order, not hematemesis severity.",
  "", "## Boundary", "",
  "- Passing this gate means hematemesis is eligible for later evidence-engine review, not automatically promoted.",
  "- Failing this gate keeps hematemesis as sensitivity-only or blocked according to the decision row.",
  "- This output does not claim clinical validity."
)

utils::write.csv(cell_counts, file.path(output_dir, "hematemesis_cell_counts_by_year.csv"), row.names = FALSE, na = "")
utils::write.csv(unadjusted_rates, file.path(output_dir, "hematemesis_unadjusted_rates_by_year.csv"), row.names = FALSE, na = "")
utils::write.csv(coefficients, file.path(output_dir, "hematemesis_model_comparison_coefficients.csv"), row.names = FALSE, na = "")
utils::write.csv(covariance, file.path(output_dir, "hematemesis_model_comparison_covariance.csv"), row.names = FALSE, na = "")
utils::write.csv(draws, file.path(output_dir, "hematemesis_model_comparison_draws.csv"), row.names = FALSE, na = "")
utils::write.csv(calibration, file.path(output_dir, "hematemesis_model_comparison_calibration.csv"), row.names = FALSE, na = "")
utils::write.csv(deciles, file.path(output_dir, "hematemesis_model_comparison_deciles.csv"), row.names = FALSE, na = "")
utils::write.csv(leave_one_year_out, file.path(output_dir, "hematemesis_leave_one_year_out_validation.csv"), row.names = FALSE, na = "")
utils::write.csv(tier_sensitivity, file.path(output_dir, "hematemesis_tier_sensitivity.csv"), row.names = FALSE, na = "")
utils::write.csv(gate_rows, file.path(output_dir, "hematemesis_gate_decision.csv"), row.names = FALSE, na = "")
writeLines(report, con = file.path(output_dir, "hematemesis_validation_report.md"))

cat("Wrote hematemesis validation outputs under ", output_dir, "\n", sep = "")
