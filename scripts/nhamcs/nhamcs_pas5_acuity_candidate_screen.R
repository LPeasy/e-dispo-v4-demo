#!/usr/bin/env Rscript

# PAS-5 perceived-acuity candidate screen.
#
# NHAMCS does not observe the five PAS-5 self-report answers. This screen uses
# NHAMCS IMMEDR only as a clinician-acuity surrogate. It does not activate a new
# app model unless every prespecified evidence gate passes and the generated
# export is separately reviewed.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1 || length(args) > 2) {
  stop("Usage: nhamcs_pas5_acuity_candidate_screen.R <pooled_analytic_cohort_csv> [output_dir]")
}

script_file <- grep("^--file=", commandArgs(FALSE), value = TRUE)
script_dir <- getwd()
if (length(script_file) > 0) {
  script_dir <- dirname(normalizePath(sub("^--file=", "", script_file[[1]]), winslash = "/"))
}

input_path <- args[[1]]
output_dir <- if (length(args) >= 2) args[[2]] else "outputs/nhamcs_pooled"
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

source(file.path(script_dir, "r_environment.R"))
nhamcs_configure_r_environment()
nhamcs_write_r_environment_report(output_dir, required_packages = c("survey"))
if (!requireNamespace("survey", quietly = TRUE)) {
  stop("R package 'survey' is required. Set NHAMCS_R_LIBS or install survey into an active R library.")
}

options(survey.lonely.psu = "adjust")

DATASET <- "NHAMCS_2018_2022_POOLED"
BASE_MODEL_ID <- "e_dispo_v4_base_refit_for_pas5_acuity_screen"
CANDIDATE_MODEL_ID <- "e-dispo-v4.1-pas5-high-acuity-surrogate"
AGE_CENTER <- 42
SEED <- 20260504L
DRAW_COUNT <- 10000L
MIN_CELL_N <- 30L
MIN_CELL_EVENTS <- 10L
MIN_CELL_NON_EVENTS <- 10L
MIN_DIRECTION_PROBABILITY <- 0.95
MIN_LOO_AUROC_GAIN <- 0.01
MAX_APPARENT_CALIBRATION_GAP <- 0.02
MIN_CALIBRATION_SLOPE <- 0.8
MAX_CALIBRATION_SLOPE <- 1.2
set.seed(SEED)

output_paths <- list()

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
  denominator <- sum(weight[positive]) * sum(weight[negative])
  if (denominator == 0) return(NA_real_)
  numerator / denominator
}

write_csv <- function(value, filename) {
  path <- file.path(output_dir, filename)
  utils::write.csv(value, path, row.names = FALSE, na = "")
  output_paths[[filename]] <<- path
  path
}

write_text <- function(lines, filename) {
  path <- file.path(output_dir, filename)
  writeLines(lines, con = path, useBytes = TRUE)
  output_paths[[filename]] <<- path
  path
}

first_existing_column <- function(frame, candidates, label) {
  matches <- candidates[candidates %in% names(frame)]
  if (length(matches) == 0) {
    stop(paste0("Missing required ", label, " column. Checked: ", paste(candidates, collapse = ", ")))
  }
  matches[[1]]
}

map_immedr_class <- function(value) {
  numeric_value <- suppressWarnings(as.integer(as.character(value)))
  ifelse(
    numeric_value %in% 1:5,
    paste0("A", numeric_value),
    NA_character_
  )
}

parse_coefficient <- function(name) {
  if (identical(name, "(Intercept)")) return(list(term = "intercept", level = ""))
  if (identical(name, "age_centered")) return(list(term = "age_centered", level = "per_1_year_centered_at_42"))
  if (identical(name, "pain_severe")) return(list(term = "pain_severe", level = "1"))
  if (identical(name, "fever_or_temp")) return(list(term = "fever_or_temp", level = "1"))
  if (identical(name, "vomiting_present")) return(list(term = "vomiting_present", level = "1"))
  if (identical(name, "tachycardia_burden")) return(list(term = "tachycardia_burden", level = "per_10_bpm_over_100"))
  if (identical(name, "high_acuity_proxy")) {
    return(list(term = "high_acuity_proxy", level = "1"))
  }
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

mvn_draw_matrix <- function(beta, covariance) {
  stable <- nearest_stable_covariance(covariance)
  eigen_result <- eigen(stable, symmetric = TRUE)
  values <- pmax(eigen_result$values, 1e-10)
  root <- eigen_result$vectors %*% diag(sqrt(values), nrow = length(values))
  z <- matrix(stats::rnorm(DRAW_COUNT * length(beta)), nrow = DRAW_COUNT, ncol = length(beta))
  draws <- sweep(z %*% t(root), 2, beta, "+")
  colnames(draws) <- names(beta)
  draws
}

mvn_draws_long <- function(model_id, beta, covariance, parsed_terms) {
  draws <- mvn_draw_matrix(beta, covariance)
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

mvn_draws_app_wide <- function(beta, covariance) {
  draws <- mvn_draw_matrix(beta, covariance)
  out <- data.frame(
    draw_id = seq_len(nrow(draws)),
    intercept = draws[, "(Intercept)"],
    age_centered = draws[, "age_centered"],
    pain_severe = draws[, "pain_severe"],
    fever_or_temp = draws[, "fever_or_temp"],
    vomiting_present = draws[, "vomiting_present"],
    tachycardia_burden = draws[, "tachycardia_burden"],
    check.names = FALSE
  )
  out[["high_acuity_proxy"]] <- draws[, "high_acuity_proxy"]
  out[["seed"]] <- SEED
  out
}

calibration_status <- function(slope, observed, predicted) {
  gap <- abs(predicted - observed)
  if (!is.finite(gap) || !is.finite(slope)) return("fail_calibration_unavailable")
  if (gap > MAX_APPARENT_CALIBRATION_GAP) return("fail_calibration_gap")
  if (slope < MIN_CALIBRATION_SLOPE || slope > MAX_CALIBRATION_SLOPE) return("fail_calibration_slope")
  "pass_candidate_range"
}

decile_calibration <- function(model_id, frame, predicted) {
  breaks <- unique(stats::quantile(predicted, probs = seq(0, 1, length.out = 11), na.rm = TRUE, names = FALSE, type = 8))
  if (length(breaks) < 3) {
    return(data.frame(
      model_id = model_id, dataset = DATASET, decile = NA_integer_, n = nrow(frame),
      events = sum(frame$admit == 1), weighted_n = sum(frame$weight),
      observed_prevalence = weighted_mean(frame$admit, frame$weight),
      mean_predicted = weighted_mean(predicted, frame$weight),
      calibration_gap = weighted_mean(predicted, frame$weight) - weighted_mean(frame$admit, frame$weight),
      stringsAsFactors = FALSE
    ))
  }
  decile <- cut(predicted, breaks = breaks, include.lowest = TRUE, labels = FALSE)
  rows <- data.frame()
  for (level in sort(unique(decile))) {
    part <- frame[decile == level, , drop = FALSE]
    part_predicted <- predicted[decile == level]
    rows <- rbind(rows, data.frame(
      model_id = model_id,
      dataset = DATASET,
      decile = level,
      n = nrow(part),
      events = sum(part$admit == 1),
      weighted_n = sum(part$weight),
      observed_prevalence = weighted_mean(part$admit, part$weight),
      mean_predicted = weighted_mean(part_predicted, part$weight),
      calibration_gap = weighted_mean(part_predicted, part$weight) - weighted_mean(part$admit, part$weight),
      stringsAsFactors = FALSE
    ))
  }
  rows
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
    evidence_tier = "survey_weighted_candidate_surrogate",
    limitation_note = "PAS-5 is not observed in NHAMCS; IMMEDR is used only as a clinician-acuity surrogate for educational screening.",
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
    events = sum(frame$admit == 1),
    observed_prevalence = observed,
    mean_predicted = mean_predicted,
    calibration_gap = abs(mean_predicted - observed),
    calibration_in_the_large = as.numeric(stats::coef(intercept_fit)[[1]]),
    calibration_slope = slope,
    brier_score = weighted_mean((predicted - frame$admit) ^ 2, frame$weight),
    auroc = weighted_auc(frame$admit, predicted, frame$weight),
    pass_fail_status = calibration_status(slope, observed, mean_predicted),
    stringsAsFactors = FALSE
  )

  list(
    fit = fit,
    beta = beta,
    covariance_matrix = covariance,
    parsed_terms = parsed_terms,
    coefficients = coefficients,
    covariance = covariance_rows,
    draws = mvn_draws_long(model_id, beta, covariance, parsed_terms),
    calibration = calibration,
    deciles = decile_calibration(model_id, frame, predicted),
    predicted = predicted
  )
}

predict_heldout <- function(model_id, formula, train, test) {
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = train)
  fit <- survey::svyglm(formula, design = design, family = quasibinomial())
  predicted <- as.numeric(stats::predict(fit, newdata = test, type = "response"))
  beta <- stats::coef(fit)

  data.frame(
    heldout_year = unique(test$year)[[1]],
    model_id = model_id,
    dataset = DATASET,
    train_n = nrow(train),
    train_events = sum(train$admit == 1),
    heldout_n = nrow(test),
    heldout_events = sum(test$admit == 1),
    brier_score = weighted_mean((predicted - test$admit) ^ 2, test$weight),
    auroc = weighted_auc(test$admit, predicted, test$weight),
    observed_prevalence = weighted_mean(test$admit, test$weight),
    mean_predicted = weighted_mean(predicted, test$weight),
    high_acuity_proxy_beta = if ("high_acuity_proxy" %in% names(beta)) as.numeric(beta[["high_acuity_proxy"]]) else NA_real_,
    stringsAsFactors = FALSE
  )
}

if (!file.exists(input_path)) {
  stop(paste("Input analytic cohort file does not exist:", input_path))
}
cohort <- read.csv(input_path, stringsAsFactors = FALSE, na.strings = c("", "NA", "NaN"))
if ("dataset" %in% names(cohort) && length(unique(cohort$dataset[!is.na(cohort$dataset)])) > 0) {
  DATASET <- unique(cohort$dataset[!is.na(cohort$dataset)])[[1]]
}

scope_column <- first_existing_column(cohort, c("in_active_scope", "include_active_scope", "active_scope"), "active scope")
weight_column <- first_existing_column(cohort, c("pooled_weight", "weight"), "survey weight")
stratum_column <- first_existing_column(cohort, c("pooled_stratum", "stratum"), "survey stratum")
psu_column <- first_existing_column(cohort, c("pooled_psu", "psu"), "survey PSU")
acuity_column <- first_existing_column(cohort, c("acuity", "IMMEDR", "immedr"), "IMMEDR acuity")
heart_rate_column <- first_existing_column(cohort, c("HR", "heart_rate_bpm", "PULSE", "pulse"), "observed heart rate")

required <- c("include_strict_binary", "admit", "year", "age", "pain_bin3",
              "fever_or_temp", "vomiting_present", weight_column,
              stratum_column, psu_column, scope_column, acuity_column,
              heart_rate_column)
missing_required <- setdiff(required, names(cohort))
if (length(missing_required) > 0) {
  stop(paste("Missing required columns:", paste(missing_required, collapse = ", ")))
}

cohort$.__raw_immedr <- cohort[[acuity_column]]
cohort$.__immedr_numeric <- suppressWarnings(as.integer(as.character(cohort$.__raw_immedr)))
cohort$pas5_surrogate_class <- map_immedr_class(cohort$.__raw_immedr)
cohort$high_acuity_proxy <- ifelse(
  cohort$pas5_surrogate_class %in% c("A1", "A2"),
  1,
  ifelse(cohort$pas5_surrogate_class %in% c("A3", "A4", "A5"), 0, NA_real_)
)

mapping_rows <- data.frame(
  source = c("NHAMCS IMMEDR", "NHAMCS IMMEDR", "NHAMCS IMMEDR", "NHAMCS IMMEDR", "NHAMCS IMMEDR",
             "PAS-5 score", "PAS-5 score", "PAS-5 score", "PAS-5 score", "PAS-5 score"),
  source_value = c("1", "2", "3", "4", "5", "0-2", "3-5", "6-8", "9-11", "12-15"),
  mapped_class = c("A1", "A2", "A3", "A4", "A5", "A5", "A4", "A3", "A2", "A1"),
  high_acuity_proxy = c(1, 1, 0, 0, 0, 0, 0, 0, 1, 1),
  role = c(rep("NHAMCS surrogate mapping", 5), rep("PAS-5 direct scoring rule", 5)),
  limitation = "NHAMCS IMMEDR is not patient-perceived PAS-5; it is used only as a surrogate candidate screen.",
  source_url = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/dataset_documentation/NHAMCS/doc22-ed-508.pdf",
  stringsAsFactors = FALSE
)

binary <- cohort[truthy(cohort$include_strict_binary) & truthy(cohort[[scope_column]]), , drop = FALSE]
if (nrow(binary) == 0) stop("Strict binary active-scope cohort is empty.")

binary$admit <- as.numeric(binary$admit)
binary$year <- as.integer(binary$year)
binary$age <- as.numeric(binary$age)
binary$age_centered <- binary$age - AGE_CENTER
binary$weight <- as.numeric(binary[[weight_column]])
binary$stratum <- as.factor(binary[[stratum_column]])
binary$psu <- as.factor(binary[[psu_column]])
binary$fever_or_temp <- as.numeric(binary$fever_or_temp)
binary$vomiting_present <- as.numeric(binary$vomiting_present)
binary$HR <- as.numeric(binary[[heart_rate_column]])
binary$tachycardia_burden <- if ("tachycardia_burden" %in% names(binary)) {
  as.numeric(binary$tachycardia_burden)
} else {
  pmax(binary$HR - 100, 0) / 10
}
binary$pain_missing <- if ("pain_missing" %in% names(binary)) as.numeric(binary$pain_missing) else as.numeric(is.na(binary$pain_bin3))
if (!"endpoint_class" %in% names(binary)) {
  binary$endpoint_class <- ifelse(binary$admit == 1, "admit", "routine_home_discharge")
}

binary <- binary[!is.na(binary$admit) & binary$admit %in% c(0, 1) &
  !is.na(binary$year) & !is.na(binary$age_centered) &
  !is.na(binary$weight) & binary$weight > 0 &
  !is.na(binary$stratum) & !is.na(binary$psu), , drop = FALSE]

active_complete <- binary[
  binary$pain_missing == 0 &
    !is.na(binary$pain_bin3) & trimws(as.character(binary$pain_bin3)) != "" &
    !is.na(binary$fever_or_temp) &
    !is.na(binary$vomiting_present) &
    !is.na(binary$HR) &
    !is.na(binary$tachycardia_burden),
  ,
  drop = FALSE
]
if (nrow(active_complete) == 0 || length(unique(active_complete$admit)) < 2) {
  stop("No usable active complete-case rows with endpoint variation for PAS-5 acuity screen.")
}

missingness_rows <- data.frame()
for (endpoint in sort(unique(active_complete$endpoint_class))) {
  endpoint_rows <- active_complete[active_complete$endpoint_class == endpoint, , drop = FALSE]
  code_values <- c(0L, 7L, -8L, -9L)
  for (code in code_values) {
    flagged <- endpoint_rows$.__immedr_numeric == code
    flagged[is.na(flagged)] <- FALSE
    missingness_rows <- rbind(missingness_rows, data.frame(
      dataset = DATASET,
      field = acuity_column,
      endpoint = endpoint,
      category = paste0("excluded_code_", code),
      n = nrow(endpoint_rows),
      missing_or_excluded_n = sum(flagged),
      missing_or_excluded_pct = if (nrow(endpoint_rows) > 0) sum(flagged) / nrow(endpoint_rows) else NA_real_,
      weighted_n = sum(endpoint_rows$weight),
      weighted_missing_or_excluded_n = sum(endpoint_rows$weight[flagged]),
      weighted_missing_or_excluded_pct = if (sum(endpoint_rows$weight) > 0) sum(endpoint_rows$weight[flagged]) / sum(endpoint_rows$weight) else NA_real_,
      stringsAsFactors = FALSE
    ))
  }
  missing_flag <- is.na(endpoint_rows$pas5_surrogate_class)
  missingness_rows <- rbind(missingness_rows, data.frame(
    dataset = DATASET,
    field = acuity_column,
    endpoint = endpoint,
    category = "excluded_missing_or_unmapped",
    n = nrow(endpoint_rows),
    missing_or_excluded_n = sum(missing_flag),
    missing_or_excluded_pct = if (nrow(endpoint_rows) > 0) sum(missing_flag) / nrow(endpoint_rows) else NA_real_,
    weighted_n = sum(endpoint_rows$weight),
    weighted_missing_or_excluded_n = sum(endpoint_rows$weight[missing_flag]),
    weighted_missing_or_excluded_pct = if (sum(endpoint_rows$weight) > 0) sum(endpoint_rows$weight[missing_flag]) / sum(endpoint_rows$weight) else NA_real_,
    stringsAsFactors = FALSE
  ))
}

complete_case <- active_complete[!is.na(active_complete$pas5_surrogate_class), , drop = FALSE]
if (nrow(complete_case) == 0 || length(unique(complete_case$admit)) < 2) {
  stop("No usable PAS-5/IMMEDR complete-case rows with endpoint variation.")
}

complete_case$pain_severe <- as.numeric(as.character(complete_case$pain_bin3) == "severe")
complete_case$fever_or_temp <- as.numeric(complete_case$fever_or_temp == 1)
complete_case$vomiting_present <- as.numeric(complete_case$vomiting_present == 1)
complete_case$high_acuity_proxy <- as.numeric(complete_case$high_acuity_proxy == 1)
complete_case$pas5_surrogate_class <- factor(complete_case$pas5_surrogate_class, levels = c("A1", "A2", "A3", "A4", "A5"))

cell_counts <- data.frame()
for (year_label in c(sort(unique(as.character(complete_case$year))), "pooled")) {
  part <- if (identical(year_label, "pooled")) complete_case else complete_case[as.character(complete_case$year) == year_label, , drop = FALSE]
  for (group in c("pas5_surrogate_class", "high_acuity_proxy")) {
    group_levels <- if (group == "pas5_surrogate_class") levels(part[[group]]) else c("0", "1")
    for (level in group_levels) {
      subset <- part[as.character(part[[group]]) == level, , drop = FALSE]
      for (endpoint in c("all", sort(unique(as.character(part$endpoint_class))))) {
        endpoint_subset <- if (endpoint == "all") subset else subset[as.character(subset$endpoint_class) == endpoint, , drop = FALSE]
        cell_counts <- rbind(cell_counts, data.frame(
          dataset = DATASET,
          model_id = CANDIDATE_MODEL_ID,
          year = year_label,
          variable = group,
          level = level,
          endpoint = endpoint,
          n = nrow(endpoint_subset),
          events = sum(endpoint_subset$admit == 1),
          non_events = sum(endpoint_subset$admit == 0),
          weighted_n = sum(endpoint_subset$weight),
          weighted_events = sum(endpoint_subset$weight[endpoint_subset$admit == 1]),
          weighted_admit_rate = weighted_mean(endpoint_subset$admit, endpoint_subset$weight),
          stringsAsFactors = FALSE
        ))
      }
    }
  }
}

base_formula <- admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden
candidate_formula <- admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden + high_acuity_proxy
base_fit <- fit_model(BASE_MODEL_ID, base_formula, complete_case)
candidate_fit <- fit_model(CANDIDATE_MODEL_ID, candidate_formula, complete_case)

coefficients <- rbind(base_fit$coefficients, candidate_fit$coefficients)
covariance <- rbind(base_fit$covariance, candidate_fit$covariance)
draws_long <- rbind(base_fit$draws, candidate_fit$draws)
draws_app <- mvn_draws_app_wide(candidate_fit$beta, candidate_fit$covariance_matrix)
calibration <- rbind(base_fit$calibration, candidate_fit$calibration)
deciles <- rbind(base_fit$deciles, candidate_fit$deciles)

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

high_draws <- draws_long[draws_long$model_id == CANDIDATE_MODEL_ID &
  draws_long$term == "high_acuity_proxy" &
  draws_long$level == "1", , drop = FALSE]
high_beta <- candidate_fit$coefficients$beta[
  candidate_fit$coefficients$term == "high_acuity_proxy" &
    candidate_fit$coefficients$level == "1"
]
high_direction_probability <- mean(high_draws$beta > 0)

pooled_proxy_counts <- cell_counts[
  cell_counts$year == "pooled" &
    cell_counts$variable == "high_acuity_proxy" &
    cell_counts$endpoint == "all",
  ,
  drop = FALSE
]
cell_adequacy <- all(pooled_proxy_counts$n >= MIN_CELL_N &
  pooled_proxy_counts$events >= MIN_CELL_EVENTS &
  pooled_proxy_counts$non_events >= MIN_CELL_NON_EVENTS) &&
  setequal(as.character(pooled_proxy_counts$level), c("0", "1"))

base_loo <- leave_one_year_out[leave_one_year_out$model_id == BASE_MODEL_ID, , drop = FALSE]
candidate_loo <- leave_one_year_out[leave_one_year_out$model_id == CANDIDATE_MODEL_ID, , drop = FALSE]
merged_loo <- merge(base_loo, candidate_loo, by = "heldout_year", suffixes = c("_base", "_candidate"), sort = TRUE)
mean_loo_auroc_base <- mean(merged_loo$auroc_base, na.rm = TRUE)
mean_loo_auroc_candidate <- mean(merged_loo$auroc_candidate, na.rm = TRUE)
mean_loo_brier_base <- mean(merged_loo$brier_score_base, na.rm = TRUE)
mean_loo_brier_candidate <- mean(merged_loo$brier_score_candidate, na.rm = TRUE)
loo_auroc_gain <- mean_loo_auroc_candidate - mean_loo_auroc_base
loo_brier_delta <- mean_loo_brier_candidate - mean_loo_brier_base

candidate_calibration <- calibration[calibration$model_id == CANDIDATE_MODEL_ID, , drop = FALSE]
apparent_gap <- candidate_calibration$calibration_gap[[1]]
apparent_slope <- candidate_calibration$calibration_slope[[1]]

candidate_written <- c(
  "pas5_acuity_mapping.csv",
  "pas5_acuity_missingness.csv",
  "pas5_acuity_cell_counts.csv",
  "pas5_acuity_coefficients.csv",
  "pas5_acuity_covariance.csv",
  "pas5_acuity_draws_long.csv",
  "pas5_acuity_draws_app.csv",
  "pas5_acuity_calibration.csv",
  "pas5_acuity_decile_calibration.csv",
  "pas5_acuity_leave_one_year_out.csv",
  "pas5_acuity_gate_decision.csv",
  "pas5_acuity_report.md"
)

gate_rows <- data.frame(
  gate = c(
    "mapping_documented",
    "binary_cell_adequacy",
    "high_acuity_proxy_beta_direction",
    "leave_one_year_out_auroc_gain",
    "leave_one_year_out_brier_no_worse",
    "apparent_calibration_gap",
    "apparent_calibration_slope",
    "required_artifacts_written",
    "active_model_change"
  ),
  passed = c(
    TRUE,
    cell_adequacy,
    is.finite(high_beta) && high_direction_probability >= MIN_DIRECTION_PROBABILITY,
    is.finite(loo_auroc_gain) && loo_auroc_gain >= MIN_LOO_AUROC_GAIN,
    is.finite(loo_brier_delta) && loo_brier_delta <= 0,
    is.finite(apparent_gap) && apparent_gap <= MAX_APPARENT_CALIBRATION_GAP,
    is.finite(apparent_slope) && apparent_slope >= MIN_CALIBRATION_SLOPE && apparent_slope <= MAX_CALIBRATION_SLOPE,
    FALSE,
    FALSE
  ),
  metric = c(
    NA_real_,
    min(pooled_proxy_counts$n, na.rm = TRUE),
    high_direction_probability,
    loo_auroc_gain,
    loo_brier_delta,
    apparent_gap,
    apparent_slope,
    NA_real_,
    NA_real_
  ),
  threshold = c(
    "IMMEDR 1-5 maps to A1-A5; PAS-5 score thresholds documented separately",
    paste0("both high_acuity_proxy levels n >= ", MIN_CELL_N, ", events >= ", MIN_CELL_EVENTS, ", non_events >= ", MIN_CELL_NON_EVENTS),
    paste0("Pr(beta > 0) >= ", MIN_DIRECTION_PROBABILITY),
    paste0("candidate mean LOO AUROC - base mean LOO AUROC >= ", MIN_LOO_AUROC_GAIN),
    "candidate mean LOO Brier - base mean LOO Brier <= 0",
    paste0("absolute apparent gap <= ", MAX_APPARENT_CALIBRATION_GAP),
    paste0(MIN_CALIBRATION_SLOPE, " <= slope <= ", MAX_CALIBRATION_SLOPE),
    "all required PAS-5 screen artifacts exist",
    "do not activate unless all prior gates pass"
  ),
  notes = c(
    "Direct PAS-5 answers are not observed in NHAMCS; this screen uses IMMEDR as a surrogate.",
    paste(paste0("high_acuity_proxy=", pooled_proxy_counts$level, ": n=", pooled_proxy_counts$n, ", events=", pooled_proxy_counts$events, ", non_events=", pooled_proxy_counts$non_events), collapse = "; "),
    paste0("beta=", signif(high_beta, 6), "; draw probability=", signif(high_direction_probability, 6)),
    paste0("base=", signif(mean_loo_auroc_base, 6), "; candidate=", signif(mean_loo_auroc_candidate, 6)),
    paste0("base=", signif(mean_loo_brier_base, 6), "; candidate=", signif(mean_loo_brier_candidate, 6)),
    paste0("gap=", signif(apparent_gap, 6)),
    paste0("slope=", signif(apparent_slope, 6)),
    "Evaluated after files are written.",
    "Will be set after all gates are evaluated."
  ),
  stringsAsFactors = FALSE
)

write_csv(mapping_rows, "pas5_acuity_mapping.csv")
write_csv(missingness_rows, "pas5_acuity_missingness.csv")
write_csv(cell_counts, "pas5_acuity_cell_counts.csv")
write_csv(coefficients, "pas5_acuity_coefficients.csv")
write_csv(covariance, "pas5_acuity_covariance.csv")
write_csv(draws_long, "pas5_acuity_draws_long.csv")
write_csv(draws_app, "pas5_acuity_draws_app.csv")
write_csv(calibration, "pas5_acuity_calibration.csv")
write_csv(deciles, "pas5_acuity_decile_calibration.csv")
write_csv(leave_one_year_out, "pas5_acuity_leave_one_year_out.csv")

artifact_paths_after_writes <- file.path(output_dir, candidate_written)
artifacts_written <- all(file.exists(artifact_paths_after_writes[!grepl("gate_decision|report", artifact_paths_after_writes)]))
gate_rows$passed[gate_rows$gate == "required_artifacts_written"] <- artifacts_written
gate_rows$metric[gate_rows$gate == "required_artifacts_written"] <- sum(file.exists(artifact_paths_after_writes))
gate_rows$notes[gate_rows$gate == "required_artifacts_written"] <- paste(names(output_paths), collapse = "; ")

pre_activation_gates <- gate_rows$gate != "active_model_change"
all_gates <- all(gate_rows$passed[pre_activation_gates])
gate_rows$passed[gate_rows$gate == "active_model_change"] <- all_gates
gate_rows$notes[gate_rows$gate == "active_model_change"] <- if (all_gates) {
  "PAS-5 surrogate candidate passed the screen; separate app artifact review is still required before activation."
} else {
  "PAS-5 remains explanatory only because one or more prespecified gates failed."
}
write_csv(gate_rows, "pas5_acuity_gate_decision.csv")

failed_gates <- gate_rows$gate[!gate_rows$passed]
report_lines <- c(
  "# PAS-5 Perceived Acuity Surrogate Candidate Screen",
  "",
  paste0("Model ID: `", CANDIDATE_MODEL_ID, "`."),
  paste0("Input: `", input_path, "`."),
  paste0("Rows in active complete-case base screen: ", nrow(active_complete), "."),
  paste0("Rows in PAS-5/IMMEDR complete-case candidate screen: ", nrow(complete_case), "."),
  "",
  "## Limitation",
  "",
  "PAS-5 patient self-assessment is not observed in NHAMCS. This screen maps NHAMCS `IMMEDR` 1-5 to A1-A5 only as a clinician-acuity surrogate. It does not validate PAS-5 as patient self-assessment, ESI, medical advice, or clinical decision support.",
  "",
  "## Formulae",
  "",
  "`base: admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden`",
  "",
  "`candidate: admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden + high_acuity_proxy`",
  "",
  "`high_acuity_proxy = 1` for surrogate A1/A2; A3/A4/A5 are the reference side.",
  "",
  "## Gate Decision",
  "",
  if (all_gates) {
    "Status: `eligible_for_separate_activation_review`."
  } else {
    "Status: `blocked_keep_pas5_explanatory_only`."
  },
  "",
  paste0("Failed gates: ", if (length(failed_gates) == 0) "none" else paste(failed_gates, collapse = ", "), "."),
  "",
  "## Sources",
  "",
  "- CDC/NCHS NHAMCS 2022 public-use documentation for `IMMEDR`: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/dataset_documentation/NHAMCS/doc22-ed-508.pdf",
  "- AHRQ ESI overview used only as conceptual background: https://www.ahrq.gov/patient-safety/settings/hospital/resource/about.html",
  "- ENA ESI handbook summary used only as conceptual background: https://enau.ena.org/AssetListing/Emergency-Severity-Index-Handbook-5th-Edition-85744/Emergency-Severity-Index-Handbook-5th-Edition-15946",
  "",
  "## Artifacts",
  "",
  paste0("- ", sort(names(output_paths)))
)
write_text(report_lines, "pas5_acuity_report.md")

if (!all_gates) {
  blocker_lines <- c(
    "# PAS-5 Acuity Surrogate Blocker Report",
    "",
    "PAS-5 remains explanatory only. The candidate is not active in `e-dispo-v4.0` and must not change P(admit).",
    "",
    paste0("Failed gates: ", paste(failed_gates, collapse = ", "), "."),
    "",
    "Primary limitation: NHAMCS does not contain PAS-5 patient self-acuity answers; `IMMEDR` is only a surrogate screen.",
    "",
    "Review `pas5_acuity_gate_decision.csv` and the supporting artifacts before considering a new app export."
  )
  write_text(blocker_lines, "pas5_acuity_blocker_report.md")
}

message(if (all_gates) {
  "PAS-5 surrogate screen passed; separate activation review required."
} else {
  "PAS-5 surrogate screen blocked; PAS-5 remains explanatory only."
})
