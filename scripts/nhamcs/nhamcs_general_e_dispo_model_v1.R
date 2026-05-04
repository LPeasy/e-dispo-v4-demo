#!/usr/bin/env Rscript

# General E-Dispo model v1.
#
# This is a parallel all-sex/all-age non-trauma NHAMCS educational/statistical
# model artifact. It is not the active e-dispo-v4.0 app model and it does not
# replace the adult-male abdominal-pain model.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: nhamcs_general_e_dispo_model_v1.R <full_source_nontrauma_cohort_csv> <output_dir>")
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
MODEL_ID <- "general-E-Dispo-model-v1"
SOURCE_SCOPE <- "full_source_nontrauma"
TARGET <- "admit_vs_home"
AGE_CENTER <- 40
SEED <- 20260428L
PERFORMANCE_INTERVAL_REPLICATES <- as.integer(Sys.getenv("GENERAL_E_DISPO_PERFORMANCE_INTERVAL_REPLICATES", "1000"))
OPTIMISM_BOOTSTRAP_REPLICATES <- as.integer(Sys.getenv("GENERAL_E_DISPO_OPTIMISM_BOOTSTRAP_REPLICATES", "200"))
MIN_VALID_INTERVAL_REPLICATES <- max(1L, as.integer(ceiling(0.8 * PERFORMANCE_INTERVAL_REPLICATES)))
MIN_OPTIMISM_VALID_REPLICATES <- 50L
MIN_SUBGROUP_EVENTS <- 10L
MIN_SUBGROUP_NONEVENTS <- 10L
INTERVAL_LEVEL <- 0.95
set.seed(SEED)

OUTPUT_FILES <- c(
  coefficients = "general_e_dispo_model_v1_coefficients.csv",
  covariance = "general_e_dispo_model_v1_covariance.csv",
  performance = "general_e_dispo_model_v1_performance.csv",
  calibration = "general_e_dispo_model_v1_calibration.csv",
  calibration_by_decile = "general_e_dispo_model_v1_calibration_by_decile.csv",
  performance_intervals = "general_e_dispo_model_v1_performance_intervals.csv",
  optimism = "general_e_dispo_model_v1_optimism_corrected_performance.csv",
  subgroup_performance = "general_e_dispo_model_v1_subgroup_performance.csv",
  subgroup_calibration = "general_e_dispo_model_v1_subgroup_calibration.csv",
  missingness = "general_e_dispo_model_v1_missingness.csv",
  spec = "general_e_dispo_model_v1_model_spec.json",
  report = "general_e_dispo_model_v1_report.md"
)

FORMULA_TEXT <- paste(
  "admit ~ age_centered_40 + acuity_code + arrival_transfer_context +",
  "fever_or_temp + tachycardia_burden + hypotension_burden"
)
MODEL_FORMULA <- stats::as.formula(FORMULA_TEXT)

truthy <- function(value) tolower(trimws(as.character(value))) %in% c("true", "1", "yes")

weighted_mean <- function(value, weight) {
  valid <- !is.na(value) & !is.na(weight) & weight > 0
  if (!any(valid) || sum(weight[valid]) == 0) return(NA_real_)
  sum(value[valid] * weight[valid]) / sum(weight[valid])
}

weighted_auc <- function(y, predicted, weight) {
  valid <- !is.na(y) & !is.na(predicted) & !is.na(weight) & weight > 0 & y %in% c(0, 1)
  y <- as.numeric(y[valid])
  predicted <- as.numeric(predicted[valid])
  weight <- as.numeric(weight[valid])
  if (length(y) == 0 || sum(y == 1) == 0 || sum(y == 0) == 0) return(NA_real_)
  total_positive_weight <- sum(weight[y == 1])
  total_negative_weight <- sum(weight[y == 0])
  if (total_positive_weight <= 0 || total_negative_weight <= 0) return(NA_real_)

  order_index <- order(predicted)
  ordered_prediction <- predicted[order_index]
  ordered_y <- y[order_index]
  ordered_weight <- weight[order_index]
  tie_group <- cumsum(c(TRUE, diff(ordered_prediction) != 0))
  positive_weight_by_group <- as.numeric(rowsum(ordered_weight * (ordered_y == 1), tie_group, reorder = FALSE))
  negative_weight_by_group <- as.numeric(rowsum(ordered_weight * (ordered_y == 0), tie_group, reorder = FALSE))
  negative_weight_before_group <- c(0, head(cumsum(negative_weight_by_group), -1))
  numerator <- sum(positive_weight_by_group * (negative_weight_before_group + 0.5 * negative_weight_by_group))
  numerator / (total_positive_weight * total_negative_weight)
}

logit <- function(value) {
  clipped <- pmin(pmax(value, 1e-6), 1 - 1e-6)
  log(clipped / (1 - clipped))
}

normal_ci <- function(estimate, n) {
  if (!is.finite(estimate) || n <= 0) return(c(NA_real_, NA_real_))
  se <- sqrt(max(estimate * (1 - estimate), 0) / n)
  c(max(0, estimate - 1.96 * se), min(1, estimate + 1.96 * se))
}

survey_mean_ci <- function(design, variable_name) {
  result <- tryCatch(
    survey::svymean(stats::as.formula(paste0("~", variable_name)), design, na.rm = TRUE),
    error = function(error) error
  )
  if (inherits(result, "error")) {
    return(list(estimate = NA_real_, se = NA_real_, ci_low = NA_real_, ci_high = NA_real_, status = "blocked_svymean_failed"))
  }
  estimate <- as.numeric(result[[1]])
  se <- as.numeric(survey::SE(result)[[1]])
  list(estimate = estimate, se = se, ci_low = estimate - 1.96 * se, ci_high = estimate + 1.96 * se, status = "ok")
}

weighted_decile <- function(predicted, weight) {
  out <- rep(NA_integer_, length(predicted))
  valid <- !is.na(predicted) & !is.na(weight) & weight > 0
  if (!any(valid)) return(out)
  order_index <- order(predicted[valid], seq_along(predicted[valid]))
  valid_index <- which(valid)[order_index]
  cumulative <- cumsum(weight[valid_index]) / sum(weight[valid_index])
  out[valid_index] <- pmin(10L, pmax(1L, ceiling(cumulative * 10)))
  out
}

metric_summary <- function(frame, predicted, weight, status_prefix = "ok") {
  y <- as.numeric(frame$admit)
  events <- sum(y == 1)
  non_events <- sum(y == 0)
  observed <- weighted_mean(y, weight)
  mean_predicted <- weighted_mean(predicted, weight)
  if (events == 0 || non_events == 0) {
    return(list(
      observed_prevalence = observed,
      mean_predicted = mean_predicted,
      calibration_gap = observed - mean_predicted,
      calibration_in_the_large = NA_real_,
      calibration_slope = NA_real_,
      brier_score = NA_real_,
      auroc = NA_real_,
      status = paste0(status_prefix, "_blocked_no_outcome_variation"),
      blocker = "Rows lack both admission and routine-home-discharge outcomes."
    ))
  }
  calibration_frame <- frame
  calibration_frame$.__predicted <- predicted
  calibration_frame$.__linear_prediction <- logit(predicted)
  calibration_frame$.__weight <- weight
  calibration_design <- tryCatch(
    survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~.__weight, nest = TRUE, data = calibration_frame),
    error = function(error) error
  )
  calibration_in_the_large <- NA_real_
  calibration_slope <- NA_real_
  calibration_status <- ""
  if (!inherits(calibration_design, "error")) {
    intercept_fit <- tryCatch(
      survey::svyglm(admit ~ 1 + offset(.__linear_prediction), design = calibration_design, family = quasibinomial()),
      error = function(error) error
    )
    slope_fit <- tryCatch(
      survey::svyglm(admit ~ .__linear_prediction, design = calibration_design, family = quasibinomial()),
      error = function(error) error
    )
    if (!inherits(intercept_fit, "error")) calibration_in_the_large <- as.numeric(stats::coef(intercept_fit)[[1]])
    if (!inherits(slope_fit, "error") && ".__linear_prediction" %in% names(stats::coef(slope_fit))) {
      calibration_slope <- as.numeric(stats::coef(slope_fit)[[".__linear_prediction"]])
    }
  } else {
    calibration_status <- "calibration_design_failed"
  }
  list(
    observed_prevalence = observed,
    mean_predicted = mean_predicted,
    calibration_gap = observed - mean_predicted,
    calibration_in_the_large = calibration_in_the_large,
    calibration_slope = calibration_slope,
    brier_score = weighted_mean((predicted - y) ^ 2, weight),
    auroc = weighted_auc(y, predicted, weight),
    status = ifelse(nzchar(calibration_status), paste0(status_prefix, "_partial_", calibration_status), status_prefix),
    blocker = calibration_status
  )
}

performance_interval_blocker_rows <- function(n, events, reason) {
  data.frame(
    model_id = MODEL_ID, dataset = DATASET, metric = c("auroc", "brier_score"),
    estimate = NA_real_, ci_low = NA_real_, ci_high = NA_real_, interval_level = INTERVAL_LEVEL,
    replicate_metric_sd = NA_real_, bootstrap_replicates_requested = PERFORMANCE_INTERVAL_REPLICATES,
    bootstrap_replicates_used = 0L, seed = SEED, n = n, events = events,
    weighted_n = NA_real_, weighted_events = NA_real_, method = "blocked",
    status = "blocked_interval_not_estimated", limitation = reason,
    stringsAsFactors = FALSE
  )
}

performance_intervals <- function(frame, predicted, performance_row) {
  frame$.__predicted <- predicted
  frame$.__brier_error <- (predicted - frame$admit) ^ 2
  n <- nrow(frame)
  events <- sum(frame$admit == 1)
  weighted_n <- sum(frame$weight)
  weighted_events <- sum(frame$weight[frame$admit == 1])
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = frame)
  set.seed(SEED)
  replicate_design <- tryCatch(
    survey::as.svrepdesign(design, type = "bootstrap", replicates = PERFORMANCE_INTERVAL_REPLICATES, mse = TRUE),
    error = function(error) error
  )
  if (inherits(replicate_design, "error")) {
    reason <- paste("survey::as.svrepdesign bootstrap failed:", conditionMessage(replicate_design))
    return(list(rows = performance_interval_blocker_rows(n, events, reason), blocker = reason))
  }
  replicate_weights <- tryCatch(
    as.matrix(stats::weights(replicate_design, type = "analysis")),
    error = function(error) error
  )
  if (inherits(replicate_weights, "error") || !is.matrix(replicate_weights) || nrow(replicate_weights) != n) {
    reason <- "Bootstrap replicate weights were unavailable or did not align with the general-model analysis frame."
    if (inherits(replicate_weights, "error")) reason <- paste(reason, conditionMessage(replicate_weights))
    return(list(rows = performance_interval_blocker_rows(n, events, reason), blocker = reason))
  }
  auroc_replicates <- apply(replicate_weights, 2, function(weight) weighted_auc(frame$admit, frame$.__predicted, weight))
  brier_replicates <- apply(replicate_weights, 2, function(weight) weighted_mean(frame$.__brier_error, weight))
  interval_row <- function(metric, estimate, values) {
    valid_values <- values[is.finite(values)]
    if (length(valid_values) < MIN_VALID_INTERVAL_REPLICATES) {
      return(data.frame(
        model_id = MODEL_ID, dataset = DATASET, metric = metric, estimate = estimate,
        ci_low = NA_real_, ci_high = NA_real_, interval_level = INTERVAL_LEVEL,
        replicate_metric_sd = ifelse(length(valid_values) > 1, stats::sd(valid_values), NA_real_),
        bootstrap_replicates_requested = PERFORMANCE_INTERVAL_REPLICATES,
        bootstrap_replicates_used = length(valid_values), seed = SEED, n = n, events = events,
        weighted_n = weighted_n, weighted_events = weighted_events,
        method = "survey_bootstrap_replicate_weights_fixed_apparent_predictions",
        status = "blocked_insufficient_valid_replicates",
        limitation = paste0("Fewer than ", MIN_VALID_INTERVAL_REPLICATES, " bootstrap replicates produced a finite metric."),
        stringsAsFactors = FALSE
      ))
    }
    ci <- stats::quantile(valid_values, probs = c((1 - INTERVAL_LEVEL) / 2, 1 - (1 - INTERVAL_LEVEL) / 2), na.rm = TRUE, names = FALSE)
    data.frame(
      model_id = MODEL_ID, dataset = DATASET, metric = metric, estimate = estimate,
      ci_low = ci[[1]], ci_high = ci[[2]], interval_level = INTERVAL_LEVEL,
      replicate_metric_sd = stats::sd(valid_values),
      bootstrap_replicates_requested = PERFORMANCE_INTERVAL_REPLICATES,
      bootstrap_replicates_used = length(valid_values), seed = SEED, n = n, events = events,
      weighted_n = weighted_n, weighted_events = weighted_events,
      method = "survey_bootstrap_replicate_weights_fixed_apparent_predictions",
      status = "ok",
      limitation = paste(
        "Interval uses survey bootstrap replicate weights from pooled NHAMCS strata/PSUs and fixed apparent predictions from the general model fit.",
        "It does not by itself provide external validation, clinical validation, or transportability."
      ),
      stringsAsFactors = FALSE
    )
  }
  rows <- rbind(
    interval_row("auroc", performance_row$auroc[[1]], auroc_replicates),
    interval_row("brier_score", performance_row$brier_score[[1]], brier_replicates)
  )
  blocker <- ""
  blocked <- rows$status != "ok"
  if (any(blocked)) blocker <- paste(rows$limitation[blocked], collapse = "; ")
  list(rows = rows, blocker = blocker)
}

write_interval_blocker <- function(blocker) {
  path <- file.path(output_dir, "general_e_dispo_model_v1_performance_intervals_blocker.md")
  if (!nzchar(blocker)) {
    if (file.exists(path)) unlink(path)
    return(invisible(NULL))
  }
  writeLines(c(
    "# general-E-Dispo-model-v1 Performance Interval Blocker",
    "",
    "At least one AUROC/Brier interval row could not be estimated defensibly.",
    "",
    "## Blocker",
    paste0("- ", blocker),
    "",
    "No interval value should be inferred for blocked rows in `general_e_dispo_model_v1_performance_intervals.csv`.",
    ""
  ), con = path)
}

grouped_calibration <- function(frame, predicted) {
  frame$.__predicted <- predicted
  frame$.__calibration_decile <- weighted_decile(predicted, frame$weight)
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = frame)
  rows <- data.frame()
  for (group in sort(unique(frame$.__calibration_decile[!is.na(frame$.__calibration_decile)]))) {
    subset_flag <- frame$.__calibration_decile == group
    part <- frame[subset_flag, , drop = FALSE]
    group_design <- subset(design, .__calibration_decile == group)
    observed <- survey_mean_ci(group_design, "admit")
    predicted_mean <- survey_mean_ci(group_design, ".__predicted")
    observed_rate <- observed$estimate
    if (!is.finite(observed_rate)) observed_rate <- weighted_mean(part$admit, part$weight)
    fallback_ci <- normal_ci(observed_rate, nrow(part))
    predicted_estimate <- ifelse(is.finite(predicted_mean$estimate), predicted_mean$estimate, weighted_mean(part$.__predicted, part$weight))
    rows <- rbind(rows, data.frame(
      model_id = MODEL_ID, dataset = DATASET, grouping = "weighted_predicted_probability_decile",
      decile = as.integer(group), n = nrow(part), events = sum(part$admit == 1),
      weighted_n = sum(part$weight), weighted_events = sum(part$weight[part$admit == 1]),
      predicted_min = min(part$.__predicted), predicted_max = max(part$.__predicted),
      mean_predicted = predicted_estimate, mean_predicted_se = predicted_mean$se,
      observed_rate = observed_rate, observed_rate_se = observed$se,
      observed_rate_ci_low = ifelse(is.finite(observed$ci_low), max(0, observed$ci_low), fallback_ci[[1]]),
      observed_rate_ci_high = ifelse(is.finite(observed$ci_high), min(1, observed$ci_high), fallback_ci[[2]]),
      calibration_gap = observed_rate - predicted_estimate,
      ci_method = ifelse(identical(observed$status, "ok"), "survey_taylor_linearized_group_mean", "fallback_unweighted_normal_group_interval"),
      status = ifelse(identical(observed$status, "ok") && identical(predicted_mean$status, "ok"), "ok", "partial"),
      notes = "Apparent grouped calibration for general-E-Dispo-model-v1; no external validation or transportability claim.",
      stringsAsFactors = FALSE
    ))
  }
  rows
}

subgroup_levels <- function(frame) {
  candidates <- c(
    "sex", "age_band_full", "race_ethnicity", "payer", "region", "msa_status",
    "adult_male_18_64_flag", "abdominal_pain_flag", "acuity_code", "arrival_transfer_context",
    "temp_availability", "HR_availability", "SBP_availability"
  )
  candidates[candidates %in% names(frame)]
}

subgroup_metric_rows <- function(frame, predicted) {
  frame$.__predicted <- predicted
  rows <- data.frame()
  for (field in subgroup_levels(frame)) {
    values <- sort(unique(as.character(frame[[field]])))
    for (value in values) {
      if (is.na(value) || !nzchar(value)) next
      part <- frame[as.character(frame[[field]]) == value, , drop = FALSE]
      events <- sum(part$admit == 1)
      non_events <- sum(part$admit == 0)
      status <- "ok"
      blocker <- ""
      if (events == 0 || non_events == 0) {
        status <- "blocked_no_outcome_variation"
        blocker <- "Subgroup lacks both admission and discharge outcomes."
      } else if (events < MIN_SUBGROUP_EVENTS || non_events < MIN_SUBGROUP_NONEVENTS) {
        status <- "blocked_sparse_cells"
        blocker <- paste0("Subgroup has events=", events, " and non-events=", non_events, "; required at least ", MIN_SUBGROUP_EVENTS, " events and ", MIN_SUBGROUP_NONEVENTS, " non-events.")
      }
      metrics <- metric_summary(part, part$.__predicted, part$weight, status_prefix = "ok")
      if (status != "ok") {
        metrics$auroc <- NA_real_
        metrics$brier_score <- NA_real_
        metrics$calibration_in_the_large <- NA_real_
        metrics$calibration_slope <- NA_real_
      }
      rows <- rbind(rows, data.frame(
        model_id = MODEL_ID, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
        subgroup = field, level = value, n = nrow(part), events = events, non_events = non_events,
        weighted_n = sum(part$weight), weighted_events = sum(part$weight[part$admit == 1]),
        observed_prevalence = metrics$observed_prevalence,
        mean_predicted = metrics$mean_predicted,
        calibration_gap = metrics$calibration_gap,
        auroc = metrics$auroc,
        brier_score = metrics$brier_score,
        status = status,
        blocker = blocker,
        method = "survey_weighted_subgroup_apparent_predictions",
        limitation = "Subgroup rows are internal NHAMCS apparent summaries; demographic/payer/geography fields are not fitted predictors.",
        stringsAsFactors = FALSE
      ))
    }
  }
  rows
}

subgroup_calibration_rows <- function(frame, predicted) {
  frame$.__predicted <- predicted
  rows <- data.frame()
  for (field in subgroup_levels(frame)) {
    values <- sort(unique(as.character(frame[[field]])))
    for (value in values) {
      if (is.na(value) || !nzchar(value)) next
      part <- frame[as.character(frame[[field]]) == value, , drop = FALSE]
      events <- sum(part$admit == 1)
      non_events <- sum(part$admit == 0)
      if (events < MIN_SUBGROUP_EVENTS || non_events < MIN_SUBGROUP_NONEVENTS) {
        rows <- rbind(rows, data.frame(
          model_id = MODEL_ID, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
          subgroup = field, level = value, n = nrow(part), events = events, non_events = non_events,
          calibration_in_the_large = NA_real_, calibration_slope = NA_real_,
          status = "blocked_sparse_cells",
          blocker = "Sparse cells prevent defensible subgroup calibration estimates.",
          method = "blocked", limitation = "No subgroup calibration estimate should be inferred.",
          stringsAsFactors = FALSE
        ))
        next
      }
      metrics <- metric_summary(part, part$.__predicted, part$weight, status_prefix = "ok")
      rows <- rbind(rows, data.frame(
        model_id = MODEL_ID, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
        subgroup = field, level = value, n = nrow(part), events = events, non_events = non_events,
        calibration_in_the_large = metrics$calibration_in_the_large,
        calibration_slope = metrics$calibration_slope,
        status = metrics$status,
        blocker = metrics$blocker,
        method = "survey_weighted_subgroup_calibration_on_apparent_predictions",
        limitation = "Internal same-source subgroup calibration only; no external validation or transportability claim.",
        stringsAsFactors = FALSE
      ))
    }
  }
  rows
}

missingness_rows <- function(binary, complete_case) {
  binary$temp_availability <- ifelse(is.na(binary$fever_or_temp), "missing_temp_or_fever_proxy", "observed_temp_or_fever_proxy")
  binary$HR_availability <- ifelse(is.na(binary$tachycardia_burden), "missing_HR", "observed_HR")
  binary$SBP_availability <- ifelse(is.na(binary$hypotension_burden), "missing_SBP", "observed_SBP")
  binary$age_availability <- ifelse(is.na(binary$age), "missing_age", "observed_age")
  binary$acuity_availability <- ifelse(is.na(binary$acuity_code), "missing_acuity_code", "observed_or_explicit_unknown_acuity_code")
  binary$arrival_transfer_availability <- ifelse(is.na(binary$arrival_transfer_context), "missing_arrival_transfer_context", "observed_or_explicit_unknown_arrival_transfer_context")
  rows <- data.frame()
  for (field in c("age_availability", "acuity_availability", "arrival_transfer_availability", "temp_availability", "HR_availability", "SBP_availability")) {
    for (value in sort(unique(binary[[field]]))) {
      part <- binary[binary[[field]] == value, , drop = FALSE]
      complete_part <- complete_case[rownames(complete_case) %in% rownames(part), , drop = FALSE]
      rows <- rbind(rows, data.frame(
        model_id = MODEL_ID, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
        field = field, level = value,
        denominator_n = nrow(part), denominator_events = sum(part$admit == 1),
        denominator_weighted_n = sum(part$weight), denominator_weighted_events = sum(part$weight[part$admit == 1]),
        model_estimable_n = nrow(complete_part), model_estimable_events = sum(complete_part$admit == 1),
        status = ifelse(nrow(complete_part) > 0, "ok", "blocked_no_model_estimable_rows"),
        blocker = ifelse(nrow(complete_part) > 0, "", "No complete-case rows for this missingness level."),
        method = "required_predictor_missingness_audit",
        limitation = "Missing required pre-disposition predictors are not imputed for this model artifact.",
        stringsAsFactors = FALSE
      ))
    }
  }
  rows
}

optimism_blocker_rows <- function(reason, apparent_metrics) {
  data.frame(
    model_id = MODEL_ID, dataset = DATASET,
    metric = c("auroc", "brier_score", "calibration_in_the_large", "calibration_slope"),
    apparent_estimate = c(
      apparent_metrics$auroc, apparent_metrics$brier_score,
      apparent_metrics$calibration_in_the_large, apparent_metrics$calibration_slope
    ),
    mean_bootstrap_apparent = NA_real_, mean_bootstrap_test = NA_real_, mean_optimism = NA_real_,
    optimism_corrected_estimate = NA_real_, test_metric_p025 = NA_real_, test_metric_p975 = NA_real_,
    bootstrap_replicates_requested = OPTIMISM_BOOTSTRAP_REPLICATES, bootstrap_replicates_used = 0L,
    seed = SEED, method = "blocked", status = "blocked_optimism_correction_not_estimated",
    blocker = reason, limitation = "Use apparent performance and fixed-prediction design-aware intervals as the current weaker artifact.",
    stringsAsFactors = FALSE
  )
}

write_optimism_blocker <- function(reason) {
  path <- file.path(output_dir, "general_e_dispo_model_v1_optimism_corrected_performance_blocker.md")
  if (!nzchar(reason)) {
    if (file.exists(path)) unlink(path)
    return(invisible(NULL))
  }
  writeLines(c(
    "# general-E-Dispo-model-v1 Optimism-Corrected Performance Blocker",
    "",
    "Survey-bootstrap refit optimism correction was not produced.",
    "",
    "## Blocker",
    paste0("- ", reason),
    "",
    "Use `general_e_dispo_model_v1_performance_intervals.csv` as the current fixed-prediction interval artifact.",
    ""
  ), con = path)
}

optimism_corrected_performance <- function(frame, formula, apparent_metrics) {
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = frame)
  set.seed(SEED)
  replicate_design <- tryCatch(
    survey::as.svrepdesign(design, type = "bootstrap", replicates = OPTIMISM_BOOTSTRAP_REPLICATES, mse = TRUE),
    error = function(error) error
  )
  if (inherits(replicate_design, "error")) {
    reason <- paste("survey::as.svrepdesign bootstrap failed:", conditionMessage(replicate_design))
    write_optimism_blocker(reason)
    return(optimism_blocker_rows(reason, apparent_metrics))
  }
  replicate_weights <- tryCatch(as.matrix(stats::weights(replicate_design, type = "analysis")), error = function(error) error)
  if (inherits(replicate_weights, "error") || !is.matrix(replicate_weights) || nrow(replicate_weights) != nrow(frame)) {
    reason <- "Bootstrap replicate weights were unavailable or did not align with the general-model analysis frame."
    if (inherits(replicate_weights, "error")) reason <- paste(reason, conditionMessage(replicate_weights))
    write_optimism_blocker(reason)
    return(optimism_blocker_rows(reason, apparent_metrics))
  }
  metric_rows <- data.frame()
  for (replicate_index in seq_len(ncol(replicate_weights))) {
    rep_weight <- replicate_weights[, replicate_index]
    if (sum(rep_weight[frame$admit == 1], na.rm = TRUE) <= 0 || sum(rep_weight[frame$admit == 0], na.rm = TRUE) <= 0) next
    rep_frame <- frame
    rep_frame$.__rep_weight <- rep_weight
    rep_design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~.__rep_weight, nest = TRUE, data = rep_frame)
    fit <- tryCatch(survey::svyglm(formula, design = rep_design, family = quasibinomial()), error = function(error) error)
    if (inherits(fit, "error")) next
    boot_pred <- tryCatch(as.numeric(stats::predict(fit, type = "response")), error = function(error) rep(NA_real_, nrow(rep_frame)))
    test_pred <- tryCatch(as.numeric(stats::predict(fit, newdata = frame, type = "response")), error = function(error) rep(NA_real_, nrow(frame)))
    if (!all(is.finite(boot_pred)) || !all(is.finite(test_pred))) next
    boot_metrics <- metric_summary(rep_frame, boot_pred, rep_weight, status_prefix = "bootstrap_apparent")
    test_metrics <- metric_summary(frame, test_pred, frame$weight, status_prefix = "bootstrap_test")
    metric_rows <- rbind(metric_rows, data.frame(
      replicate = replicate_index,
      metric = c("auroc", "brier_score", "calibration_in_the_large", "calibration_slope"),
      bootstrap_apparent = c(boot_metrics$auroc, boot_metrics$brier_score, boot_metrics$calibration_in_the_large, boot_metrics$calibration_slope),
      bootstrap_test = c(test_metrics$auroc, test_metrics$brier_score, test_metrics$calibration_in_the_large, test_metrics$calibration_slope),
      stringsAsFactors = FALSE
    ))
  }
  valid_replicates <- length(unique(metric_rows$replicate[is.finite(metric_rows$bootstrap_apparent) & is.finite(metric_rows$bootstrap_test)]))
  if (valid_replicates < MIN_OPTIMISM_VALID_REPLICATES) {
    reason <- paste0("Only ", valid_replicates, " valid bootstrap refits completed; required at least ", MIN_OPTIMISM_VALID_REPLICATES, ".")
    write_optimism_blocker(reason)
    return(optimism_blocker_rows(reason, apparent_metrics))
  }
  write_optimism_blocker("")
  apparent <- c(
    auroc = apparent_metrics$auroc,
    brier_score = apparent_metrics$brier_score,
    calibration_in_the_large = apparent_metrics$calibration_in_the_large,
    calibration_slope = apparent_metrics$calibration_slope
  )
  rows <- data.frame()
  for (metric in names(apparent)) {
    subset_rows <- metric_rows[metric_rows$metric == metric & is.finite(metric_rows$bootstrap_apparent) & is.finite(metric_rows$bootstrap_test), , drop = FALSE]
    optimism <- subset_rows$bootstrap_apparent - subset_rows$bootstrap_test
    test_ci <- stats::quantile(subset_rows$bootstrap_test, probs = c(0.025, 0.975), na.rm = TRUE, names = FALSE)
    rows <- rbind(rows, data.frame(
      model_id = MODEL_ID, dataset = DATASET, metric = metric,
      apparent_estimate = apparent[[metric]],
      mean_bootstrap_apparent = mean(subset_rows$bootstrap_apparent),
      mean_bootstrap_test = mean(subset_rows$bootstrap_test),
      mean_optimism = mean(optimism),
      optimism_corrected_estimate = apparent[[metric]] - mean(optimism),
      test_metric_p025 = test_ci[[1]], test_metric_p975 = test_ci[[2]],
      bootstrap_replicates_requested = OPTIMISM_BOOTSTRAP_REPLICATES,
      bootstrap_replicates_used = length(unique(subset_rows$replicate)),
      seed = SEED, method = "survey_bootstrap_refit_optimism_correction",
      status = "ok", blocker = "",
      limitation = "Internal same-source optimism correction only; no external validation or transportability claim.",
      stringsAsFactors = FALSE
    ))
  }
  rows
}

parse_coefficient <- function(name) {
  if (identical(name, "(Intercept)")) return(list(term = "intercept", level = ""))
  if (identical(name, "age_centered_40")) return(list(term = "age_centered_40", level = "per_1_year_centered_at_40"))
  if (identical(name, "fever_or_temp")) return(list(term = "fever_or_temp", level = "1"))
  if (identical(name, "tachycardia_burden")) return(list(term = "tachycardia_burden", level = "per_10_bpm_over_100"))
  if (identical(name, "hypotension_burden")) return(list(term = "hypotension_burden", level = "per_10_mmhg_below_100"))
  if (startsWith(name, "acuity_code")) return(list(term = "acuity_code", level = sub("^acuity_code", "", name)))
  if (startsWith(name, "arrival_transfer_context")) return(list(term = "arrival_transfer_context", level = sub("^arrival_transfer_context", "", name)))
  list(term = name, level = "")
}

coefficient_label <- function(parsed) {
  if (identical(parsed$level, "")) parsed$term else paste0(parsed$term, "[", parsed$level, "]")
}

write_model_spec <- function(input_n, input_events, complete_case_n, complete_case_events, package_status) {
  survey_version <- ""
  if (requireNamespace("survey", quietly = TRUE)) survey_version <- as.character(utils::packageVersion("survey"))
  lines <- c(
    "{",
    paste0('  "model_id": "', MODEL_ID, '",'),
    '  "model_role": "parallel_general_nontrauma_educational_statistical_artifact",',
    '  "active_app_model": false,',
    '  "replaces_e_dispo_v4_0": false,',
    paste0('  "dataset": "', DATASET, '",'),
    paste0('  "source_scope": "', SOURCE_SCOPE, '",'),
    '  "cohort": "all-sex/all-age NHAMCS 2018-2022 non-trauma ED records with strict admit-vs-routine-home endpoint",',
    '  "target": "endpoint_class == admit versus endpoint_class == routine_home_discharge; transfer excluded from fitting",',
    paste0('  "formula": "', FORMULA_TEXT, '",'),
    paste0('  "age_center": ', AGE_CENTER, ','),
    '  "factor_references": {',
    '    "acuity_code": "urgent",',
    '    "arrival_transfer_context": "no_not_transferred_from_hospital_or_urgent_care"',
    '  },',
    '  "transformations": {',
    '    "age_centered_40": "age - 40",',
    '    "fever_or_temp": "1[temp >= 100.4F] when temperature observed",',
    '    "tachycardia_burden": "max(HR - 100, 0) / 10",',
    '    "hypotension_burden": "max(100 - SBP, 0) / 10"',
    '  },',
    '  "excluded_from_primary_formula": ["pain", "vomiting", "nausea", "hematemesis", "payer", "sex", "race_ethnicity", "region", "MSA", "imaging", "medication", "length_of_visit", "wait_time", "treatment", "diagnosis", "disposition_derived_fields"],',
    paste0('  "input_n": ', input_n, ','),
    paste0('  "input_events": ', input_events, ','),
    paste0('  "complete_case_n": ', complete_case_n, ','),
    paste0('  "complete_case_events": ', complete_case_events, ','),
    paste0('  "seed": ', SEED, ','),
    paste0('  "performance_interval_replicates": ', PERFORMANCE_INTERVAL_REPLICATES, ','),
    paste0('  "optimism_bootstrap_replicates": ', OPTIMISM_BOOTSTRAP_REPLICATES, ','),
    '  "fitting_method": "survey::svyglm(..., family = quasibinomial()) with pooled NHAMCS weights, strata, and PSUs",',
    paste0('  "r_version": "', paste(R.version$major, R.version$minor, sep = "."), '",'),
    paste0('  "survey_package_version": "', survey_version, '",'),
    '  "limitations": [',
    '    "educational/statistical artifact only",',
    '    "not clinical decision support",',
    '    "not active GitHub Pages app model",',
    '    "not external validation",',
    '    "not transportability evidence"',
    '  ]',
    "}"
  )
  writeLines(lines, con = file.path(output_dir, OUTPUT_FILES[["spec"]]))
}

write_blocker_outputs <- function(reason, input_n = 0L, input_events = 0L) {
  coefficients <- data.frame(
    model_id = MODEL_ID, dataset = DATASET, term = "blocked", level = "",
    beta = NA_real_, se = NA_real_, odds_ratio = NA_real_, ci_low = NA_real_,
    ci_high = NA_real_, p_value = NA_real_, evidence_tier = "blocked",
    limitation_note = reason, stringsAsFactors = FALSE
  )
  covariance <- data.frame(
    model_id = MODEL_ID, dataset = DATASET, row_term = "blocked",
    column_term = "blocked", covariance = NA_real_, stringsAsFactors = FALSE
  )
  performance <- data.frame(
    model_id = MODEL_ID, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
    n = input_n, events = input_events, non_events = max(input_n - input_events, 0L),
    model_estimable_n = 0L, model_estimable_events = 0L, weighted_n = NA_real_,
    weighted_events = NA_real_, observed_prevalence = NA_real_, mean_predicted = NA_real_,
    calibration_gap = NA_real_, auroc = NA_real_, brier_score = NA_real_,
    formula = FORMULA_TEXT, method = "blocked", status = "blocked_not_fit",
    limitation = reason, stringsAsFactors = FALSE
  )
  calibration <- data.frame(
    model_id = MODEL_ID, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
    n = input_n, events = input_events, observed_prevalence = NA_real_,
    mean_predicted = NA_real_, calibration_in_the_large = NA_real_,
    calibration_slope = NA_real_, method = "blocked", status = "blocked_not_fit",
    limitation = reason, stringsAsFactors = FALSE
  )
  deciles <- data.frame(
    model_id = MODEL_ID, dataset = DATASET, grouping = "weighted_predicted_probability_decile",
    decile = NA_integer_, n = input_n, events = input_events, weighted_n = NA_real_,
    weighted_events = NA_real_, predicted_min = NA_real_, predicted_max = NA_real_,
    mean_predicted = NA_real_, mean_predicted_se = NA_real_, observed_rate = NA_real_,
    observed_rate_se = NA_real_, observed_rate_ci_low = NA_real_, observed_rate_ci_high = NA_real_,
    calibration_gap = NA_real_, ci_method = "blocked", status = "blocked_not_fit",
    notes = reason, stringsAsFactors = FALSE
  )
  intervals <- performance_interval_blocker_rows(input_n, input_events, reason)
  optimism <- optimism_blocker_rows(reason, list(auroc = NA_real_, brier_score = NA_real_, calibration_in_the_large = NA_real_, calibration_slope = NA_real_))
  subgroup <- data.frame(
    model_id = MODEL_ID, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
    subgroup = "overall", level = "blocked", n = input_n, events = input_events,
    non_events = max(input_n - input_events, 0L), weighted_n = NA_real_,
    weighted_events = NA_real_, observed_prevalence = NA_real_, mean_predicted = NA_real_,
    calibration_gap = NA_real_, auroc = NA_real_, brier_score = NA_real_,
    status = "blocked_not_fit", blocker = reason, method = "blocked",
    limitation = reason, stringsAsFactors = FALSE
  )
  subgroup_calibration <- data.frame(
    model_id = MODEL_ID, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
    subgroup = "overall", level = "blocked", n = input_n, events = input_events,
    non_events = max(input_n - input_events, 0L), calibration_in_the_large = NA_real_,
    calibration_slope = NA_real_, status = "blocked_not_fit", blocker = reason,
    method = "blocked", limitation = reason, stringsAsFactors = FALSE
  )
  missingness <- data.frame(
    model_id = MODEL_ID, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
    field = "blocked", level = "blocked", denominator_n = input_n,
    denominator_events = input_events, denominator_weighted_n = NA_real_,
    denominator_weighted_events = NA_real_, model_estimable_n = 0L,
    model_estimable_events = 0L, status = "blocked_not_fit", blocker = reason,
    method = "blocked", limitation = reason, stringsAsFactors = FALSE
  )
  utils::write.csv(coefficients, file.path(output_dir, OUTPUT_FILES[["coefficients"]]), row.names = FALSE, na = "")
  utils::write.csv(covariance, file.path(output_dir, OUTPUT_FILES[["covariance"]]), row.names = FALSE, na = "")
  utils::write.csv(performance, file.path(output_dir, OUTPUT_FILES[["performance"]]), row.names = FALSE, na = "")
  utils::write.csv(calibration, file.path(output_dir, OUTPUT_FILES[["calibration"]]), row.names = FALSE, na = "")
  utils::write.csv(deciles, file.path(output_dir, OUTPUT_FILES[["calibration_by_decile"]]), row.names = FALSE, na = "")
  utils::write.csv(intervals, file.path(output_dir, OUTPUT_FILES[["performance_intervals"]]), row.names = FALSE, na = "")
  utils::write.csv(optimism, file.path(output_dir, OUTPUT_FILES[["optimism"]]), row.names = FALSE, na = "")
  utils::write.csv(subgroup, file.path(output_dir, OUTPUT_FILES[["subgroup_performance"]]), row.names = FALSE, na = "")
  utils::write.csv(subgroup_calibration, file.path(output_dir, OUTPUT_FILES[["subgroup_calibration"]]), row.names = FALSE, na = "")
  utils::write.csv(missingness, file.path(output_dir, OUTPUT_FILES[["missingness"]]), row.names = FALSE, na = "")
  write_model_spec(input_n, input_events, 0L, 0L, NULL)
  writeLines(c(
    "# general-E-Dispo-model-v1",
    "",
    paste0("Status: `blocked_not_fit`."),
    "",
    "## Blocker",
    paste0("- ", reason),
    "",
    "No coefficient or performance estimate should be inferred from blocked rows.",
    "",
    "This parallel model artifact does not replace active `e-dispo-v4.0`.",
    ""
  ), con = file.path(output_dir, OUTPUT_FILES[["report"]]))
}

if (!file.exists(input_path)) {
  write_blocker_outputs(paste("Input cohort is missing:", input_path))
  quit(status = 2)
}

cohort <- read.csv(input_path, stringsAsFactors = FALSE, na.strings = c("", "NA", "NaN"))
required <- c(
  "endpoint_class", "admit", "year", "age", "sex", "age_band_full",
  "acuity_code", "arrival_transfer_context", "fever_or_temp", "HR",
  "tachycardia_burden", "SBP", "hypotension_burden", "pooled_weight",
  "pooled_stratum", "pooled_psu"
)
missing_required <- setdiff(required, names(cohort))
if (length(missing_required) > 0) {
  write_blocker_outputs(paste("Missing required columns:", paste(missing_required, collapse = ", ")))
  quit(status = 2)
}

binary <- cohort[cohort$endpoint_class %in% c("admit", "routine_home_discharge"), , drop = FALSE]
binary$admit <- as.numeric(binary$endpoint_class == "admit")
binary$year <- as.integer(binary$year)
binary$age <- as.numeric(binary$age)
binary$age_centered_40 <- binary$age - AGE_CENTER
binary$fever_or_temp <- as.numeric(binary$fever_or_temp)
binary$HR <- as.numeric(binary$HR)
binary$tachycardia_burden <- as.numeric(binary$tachycardia_burden)
binary$SBP <- as.numeric(binary$SBP)
binary$hypotension_burden <- as.numeric(binary$hypotension_burden)
binary$weight <- as.numeric(binary$pooled_weight)
binary$stratum <- as.factor(binary$pooled_stratum)
binary$psu <- as.factor(binary$pooled_psu)

binary$temp_availability <- ifelse(is.na(binary$fever_or_temp), "missing_temp_or_fever_proxy", "observed_temp_or_fever_proxy")
binary$HR_availability <- ifelse(is.na(binary$tachycardia_burden), "missing_HR", "observed_HR")
binary$SBP_availability <- ifelse(is.na(binary$hypotension_burden), "missing_SBP", "observed_SBP")

input_n <- nrow(binary)
input_events <- sum(binary$admit == 1)
if (input_n == 0 || input_events == 0 || sum(binary$admit == 0) == 0) {
  write_blocker_outputs("No usable admit-vs-home denominator after full-source non-trauma endpoint filtering.", input_n, input_events)
  quit(status = 2)
}

expected_acuity <- c("blank", "unknown", "no_triage_esa_conducts_triage", "immediate", "emergent", "urgent", "semi_urgent", "nonurgent", "no_nursing_triage_esa")
expected_arrival <- c("blank", "unknown", "not_applicable", "yes_transferred_from_hospital_or_urgent_care", "no_not_transferred_from_hospital_or_urgent_care")
unexpected_acuity <- setdiff(unique(binary$acuity_code[!is.na(binary$acuity_code)]), expected_acuity)
unexpected_arrival <- setdiff(unique(binary$arrival_transfer_context[!is.na(binary$arrival_transfer_context)]), expected_arrival)
if (length(unexpected_acuity) > 0 || length(unexpected_arrival) > 0) {
  write_blocker_outputs(
    paste(
      "Unconfirmed recode levels detected:",
      paste(c(paste0("acuity=", unexpected_acuity), paste0("arrival_transfer=", unexpected_arrival)), collapse = ", ")
    ),
    input_n,
    input_events
  )
  quit(status = 2)
}

complete_case <- binary[
  !is.na(binary$admit) & binary$admit %in% c(0, 1) &
    !is.na(binary$year) & !is.na(binary$age_centered_40) &
    !is.na(binary$acuity_code) & !is.na(binary$arrival_transfer_context) &
    !is.na(binary$fever_or_temp) & !is.na(binary$tachycardia_burden) &
    !is.na(binary$hypotension_burden) &
    !is.na(binary$weight) & binary$weight > 0 &
    !is.na(binary$stratum) & !is.na(binary$psu),
  ,
  drop = FALSE
]

if (nrow(complete_case) == 0 || sum(complete_case$admit == 1) == 0 || sum(complete_case$admit == 0) == 0) {
  write_blocker_outputs("No usable complete-case rows with both outcomes for the general pre-disposition predictor surface.", input_n, input_events)
  quit(status = 2)
}

complete_case$acuity_code <- factor(complete_case$acuity_code, levels = expected_acuity)
if ("urgent" %in% levels(complete_case$acuity_code)) {
  complete_case$acuity_code <- stats::relevel(complete_case$acuity_code, ref = "urgent")
}
complete_case$arrival_transfer_context <- factor(complete_case$arrival_transfer_context, levels = expected_arrival)
if ("no_not_transferred_from_hospital_or_urgent_care" %in% levels(complete_case$arrival_transfer_context)) {
  complete_case$arrival_transfer_context <- stats::relevel(complete_case$arrival_transfer_context, ref = "no_not_transferred_from_hospital_or_urgent_care")
}

design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = complete_case)
fit <- tryCatch(survey::svyglm(MODEL_FORMULA, design = design, family = quasibinomial()), error = function(error) error)
if (inherits(fit, "error")) {
  write_blocker_outputs(paste("survey::svyglm failed:", conditionMessage(fit)), input_n, input_events)
  quit(status = 2)
}

predicted <- as.numeric(stats::predict(fit, type = "response"))
if (!all(is.finite(predicted))) {
  write_blocker_outputs("Fitted model produced non-finite predictions.", input_n, input_events)
  quit(status = 2)
}
complete_case$.__predicted <- predicted

beta <- stats::coef(fit)
covariance_matrix <- stats::vcov(fit)
se <- sqrt(pmax(diag(covariance_matrix), 0))
coef_table <- summary(fit)$coefficients
parsed_terms <- lapply(names(beta), parse_coefficient)
labels <- vapply(parsed_terms, coefficient_label, character(1))

coefficients <- data.frame(
  model_id = MODEL_ID,
  dataset = DATASET,
  term = vapply(parsed_terms, function(item) item$term, character(1)),
  level = vapply(parsed_terms, function(item) item$level, character(1)),
  beta = as.numeric(beta),
  se = as.numeric(se),
  odds_ratio = exp(as.numeric(beta)),
  ci_low = exp(as.numeric(beta) - 1.96 * as.numeric(se)),
  ci_high = exp(as.numeric(beta) + 1.96 * as.numeric(se)),
  p_value = as.numeric(coef_table[, ncol(coef_table)]),
  evidence_tier = "survey_weighted_parallel_model",
  limitation_note = "Parallel all-sex/all-age NHAMCS non-trauma model artifact only; not active e-dispo-v4.0, not external validation, and not clinical-use evidence.",
  stringsAsFactors = FALSE
)

covariance_rows <- data.frame()
for (row_index in seq_along(labels)) {
  for (column_index in seq_along(labels)) {
    covariance_rows <- rbind(covariance_rows, data.frame(
      model_id = MODEL_ID, dataset = DATASET, row_term = labels[[row_index]],
      column_term = labels[[column_index]], covariance = covariance_matrix[row_index, column_index],
      stringsAsFactors = FALSE
    ))
  }
}

metrics <- metric_summary(complete_case, predicted, complete_case$weight, status_prefix = "survey_weighted_parallel_model")
performance <- data.frame(
  model_id = MODEL_ID, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
  n = input_n, events = input_events, non_events = input_n - input_events,
  model_estimable_n = nrow(complete_case), model_estimable_events = sum(complete_case$admit == 1),
  weighted_n = sum(binary$weight), weighted_events = sum(binary$weight[binary$admit == 1]),
  observed_prevalence = metrics$observed_prevalence, mean_predicted = metrics$mean_predicted,
  calibration_gap = metrics$calibration_gap, auroc = metrics$auroc, brier_score = metrics$brier_score,
  formula = FORMULA_TEXT, method = "survey::svyglm_quasibinomial_full_source_nontrauma_complete_case",
  status = "survey_weighted_parallel_model",
  limitation = "Parallel broader NHAMCS non-trauma educational/statistical artifact only; no replacement of e-dispo-v4.0, no clinical-use claim, and no external-validation claim.",
  stringsAsFactors = FALSE
)

calibration <- data.frame(
  model_id = MODEL_ID, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
  n = nrow(complete_case), events = sum(complete_case$admit == 1),
  observed_prevalence = metrics$observed_prevalence, mean_predicted = metrics$mean_predicted,
  calibration_in_the_large = metrics$calibration_in_the_large,
  calibration_slope = metrics$calibration_slope,
  method = "survey::svyglm_calibration_on_general_model_predictions",
  status = metrics$status, limitation = "Apparent calibration for the same NHAMCS source cohort; no external validation or transportability claim.",
  stringsAsFactors = FALSE
)

calibration_by_decile <- grouped_calibration(complete_case, predicted)
interval_result <- performance_intervals(complete_case, predicted, performance)
write_interval_blocker(interval_result$blocker)
subgroup_performance <- subgroup_metric_rows(complete_case, predicted)
subgroup_calibration <- subgroup_calibration_rows(complete_case, predicted)
missingness <- missingness_rows(binary, complete_case)
apparent_metrics <- list(
  auroc = performance$auroc[[1]],
  brier_score = performance$brier_score[[1]],
  calibration_in_the_large = calibration$calibration_in_the_large[[1]],
  calibration_slope = calibration$calibration_slope[[1]]
)
optimism <- optimism_corrected_performance(complete_case, MODEL_FORMULA, apparent_metrics)

sex_lines <- character(0)
if ("sex" %in% names(binary)) {
  sex_table <- table(binary$sex, useNA = "ifany")
  sex_lines <- c(
    "- Sex gate applied: no.",
    paste0("- Admit-vs-home denominator sex-code counts: ", paste(paste0(names(sex_table), "=", as.integer(sex_table)), collapse = "; "))
  )
}
if ("adult_male_18_64_flag" %in% names(binary)) {
  adult_male_count <- sum(truthy(binary$adult_male_18_64_flag), na.rm = TRUE)
  sex_lines <- c(sex_lines, paste0("- Rows that also satisfy the original adult-male age 18-64 flag: ", adult_male_count))
}

report <- c(
  "# general-E-Dispo-model-v1",
  "",
  paste0("Model ID: `", MODEL_ID, "`"),
  "Status: `survey_weighted_parallel_model`.",
  "",
  "This is a parallel all-sex/all-age NHAMCS non-trauma educational/statistical model artifact. It is not the active GitHub Pages model, not a candidate replacement for `e-dispo-v4.0` in this pass, not clinical decision support, not external validation, and not transportability evidence.",
  "",
  "## Method",
  "",
  "- Cohort: full-source NHAMCS 2018-2022 non-trauma ED records; no sex, age, or abdominal-pain gate is applied.",
  "- Target: same-hospital admission versus routine home discharge; transfer remains excluded from the admit model.",
  paste0("- Formula: `", FORMULA_TEXT, "`."),
  "- Fit: `survey::svyglm(..., family = quasibinomial())` with pooled NHAMCS weights, strata, and PSUs.",
  "- Reference levels: `acuity_code = urgent`; `arrival_transfer_context = no_not_transferred_from_hospital_or_urgent_care`.",
  "- Excluded from primary formula: pain, vomiting, nausea, hematemesis, payer, sex, race/ethnicity, region, MSA, imaging, medication, length-of-visit, wait-time, treatment, diagnosis, and disposition-derived variables.",
  "",
  "## Counts",
  "",
  paste0("- Admit-vs-home denominator N: ", input_n),
  paste0("- Admission events before complete-case restriction: ", input_events),
  paste0("- Complete-case N: ", nrow(complete_case)),
  paste0("- Complete-case admission events: ", sum(complete_case$admit == 1)),
  sex_lines,
  "",
  "## Apparent Performance",
  "",
  paste0("- AUROC: ", round(performance$auroc[[1]], 6)),
  paste0("- Brier score: ", round(performance$brier_score[[1]], 6)),
  paste0("- Observed prevalence: ", round(performance$observed_prevalence[[1]], 6)),
  paste0("- Mean predicted: ", round(performance$mean_predicted[[1]], 6)),
  paste0("- Calibration-in-the-large: ", round(calibration$calibration_in_the_large[[1]], 6)),
  paste0("- Calibration slope: ", round(calibration$calibration_slope[[1]], 6)),
  "",
  "## Intervals And Internal Validation",
  "",
  paste0("- AUROC interval status: `", interval_result$rows$status[interval_result$rows$metric == "auroc"][[1]], "`."),
  paste0("- Brier interval status: `", interval_result$rows$status[interval_result$rows$metric == "brier_score"][[1]], "`."),
  paste0("- Optimism-correction status: `", paste(unique(optimism$status), collapse = "; "), "`."),
  "",
  "Performance intervals use survey-bootstrap replicate weights with fixed apparent predictions. Optimism correction uses survey-bootstrap refits when enough replicates converge. Both are internal NHAMCS analyses only.",
  "",
  "## Output Files",
  "",
  paste0("- ", unname(OUTPUT_FILES)),
  "",
  "## Boundary",
  "",
  "This model remains a reviewer/development artifact. It does not alter app behavior, does not broaden the intended-use boundary of `e-dispo-v4.0`, and does not support patient-level clinical use.",
  ""
)

utils::write.csv(coefficients, file.path(output_dir, OUTPUT_FILES[["coefficients"]]), row.names = FALSE, na = "")
utils::write.csv(covariance_rows, file.path(output_dir, OUTPUT_FILES[["covariance"]]), row.names = FALSE, na = "")
utils::write.csv(performance, file.path(output_dir, OUTPUT_FILES[["performance"]]), row.names = FALSE, na = "")
utils::write.csv(calibration, file.path(output_dir, OUTPUT_FILES[["calibration"]]), row.names = FALSE, na = "")
utils::write.csv(calibration_by_decile, file.path(output_dir, OUTPUT_FILES[["calibration_by_decile"]]), row.names = FALSE, na = "")
utils::write.csv(interval_result$rows, file.path(output_dir, OUTPUT_FILES[["performance_intervals"]]), row.names = FALSE, na = "")
utils::write.csv(optimism, file.path(output_dir, OUTPUT_FILES[["optimism"]]), row.names = FALSE, na = "")
utils::write.csv(subgroup_performance, file.path(output_dir, OUTPUT_FILES[["subgroup_performance"]]), row.names = FALSE, na = "")
utils::write.csv(subgroup_calibration, file.path(output_dir, OUTPUT_FILES[["subgroup_calibration"]]), row.names = FALSE, na = "")
utils::write.csv(missingness, file.path(output_dir, OUTPUT_FILES[["missingness"]]), row.names = FALSE, na = "")
write_model_spec(input_n, input_events, nrow(complete_case), sum(complete_case$admit == 1), NULL)
writeLines(report, con = file.path(output_dir, OUTPUT_FILES[["report"]]))

cat("Wrote general-E-Dispo-model-v1 outputs under ", output_dir, "\n", sep = "")
