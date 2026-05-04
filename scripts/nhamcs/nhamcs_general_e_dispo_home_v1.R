#!/usr/bin/env Rscript

# Home-facing General E-Dispo v1.
#
# Fits two parallel all-sex/all-age NHAMCS non-trauma educational/statistical
# models for public home-facing use:
# - general-E-Dispo-home-v1: no transfer-in context and no required SBP.
# - general-E-Dispo-home-v1-measured-sbp: same model plus measured SBP burden.
#
# These models do not replace e-dispo-v4.1 or the source-scope
# general-E-Dispo-model-v1-plus-sex reviewer artifact.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: nhamcs_general_e_dispo_home_v1.R <full_source_nontrauma_cohort_csv> <output_dir>")
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
SOURCE_SCOPE <- "full_source_nontrauma_home_facing"
TARGET <- "admit_vs_home"
AGE_CENTER <- 40
SEED <- 20260504L
PERFORMANCE_INTERVAL_REPLICATES <- as.integer(Sys.getenv("GENERAL_E_DISPO_PERFORMANCE_INTERVAL_REPLICATES", "1000"))
OPTIMISM_BOOTSTRAP_REPLICATES <- as.integer(Sys.getenv("GENERAL_E_DISPO_OPTIMISM_BOOTSTRAP_REPLICATES", "200"))
MIN_VALID_INTERVAL_REPLICATES <- max(1L, as.integer(ceiling(0.8 * PERFORMANCE_INTERVAL_REPLICATES)))
MIN_OPTIMISM_VALID_REPLICATES <- 50L
MIN_SUBGROUP_EVENTS <- 10L
MIN_SUBGROUP_NONEVENTS <- 10L
INTERVAL_LEVEL <- 0.95
set.seed(SEED)

map_immedr_class <- function(value) {
  numeric_value <- suppressWarnings(as.integer(as.character(value)))
  ifelse(
    numeric_value %in% 1:5,
    paste0("A", numeric_value),
    NA_character_
  )
}

model_configs <- list(
  list(
    model_id = "general-E-Dispo-home-v1",
    role = "home_default_no_sbp",
    prefix = "general_e_dispo_home_v1",
    include_sbp = FALSE,
    formula_text = "admit ~ age_centered_40 + sex + high_acuity_proxy + fever_or_temp + tachycardia_burden",
    evidence_tier = "survey_weighted_home_model",
    limitation_note = paste(
      "Home-facing educational/statistical model; transfer-in context is excluded because it does not map to a person starting at home.",
      "Public acuity uses PAS-5 high_acuity_proxy; NHAMCS IMMEDR is only the surrogate fitting source.",
      "SBP is not required in this default branch. No external validation, transportability, clinical-use, or medical-advice claim."
    )
  ),
  list(
    model_id = "general-E-Dispo-home-v1-measured-sbp",
    role = "home_measured_sbp_variant",
    prefix = "general_e_dispo_home_v1_measured_sbp",
    include_sbp = TRUE,
    formula_text = "admit ~ age_centered_40 + sex + high_acuity_proxy + fever_or_temp + tachycardia_burden + hypotension_burden",
    evidence_tier = "survey_weighted_home_measured_sbp_model",
    limitation_note = paste(
      "Home-facing measured-SBP variant; SBP must be an actual measured value from a cuff or clinical/EMS reading, not guessed.",
      "Public acuity uses PAS-5 high_acuity_proxy; NHAMCS IMMEDR is only the surrogate fitting source.",
      "Transfer-in context is excluded. No external validation, transportability, clinical-use, or medical-advice claim."
    )
  )
)

output_files <- function(prefix) {
  c(
    coefficients = paste0(prefix, "_coefficients.csv"),
    covariance = paste0(prefix, "_covariance.csv"),
    performance = paste0(prefix, "_performance.csv"),
    calibration = paste0(prefix, "_calibration.csv"),
    calibration_by_decile = paste0(prefix, "_calibration_by_decile.csv"),
    performance_intervals = paste0(prefix, "_performance_intervals.csv"),
    optimism = paste0(prefix, "_optimism_corrected_performance.csv"),
    subgroup_performance = paste0(prefix, "_subgroup_performance.csv"),
    subgroup_calibration = paste0(prefix, "_subgroup_calibration.csv"),
    missingness = paste0(prefix, "_missingness.csv"),
    spec = paste0(prefix, "_model_spec.json"),
    report = paste0(prefix, "_report.md")
  )
}

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
  positive_weight <- sum(weight[y == 1])
  negative_weight <- sum(weight[y == 0])
  if (positive_weight <= 0 || negative_weight <= 0) return(NA_real_)

  order_index <- order(predicted)
  ordered_prediction <- predicted[order_index]
  ordered_y <- y[order_index]
  ordered_weight <- weight[order_index]
  tie_group <- cumsum(c(TRUE, diff(ordered_prediction) != 0))
  positive_by_group <- as.numeric(rowsum(ordered_weight * (ordered_y == 1), tie_group, reorder = FALSE))
  negative_by_group <- as.numeric(rowsum(ordered_weight * (ordered_y == 0), tie_group, reorder = FALSE))
  negative_before <- c(0, head(cumsum(negative_by_group), -1))
  sum(positive_by_group * (negative_before + 0.5 * negative_by_group)) / (positive_weight * negative_weight)
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
      observed_prevalence = observed, mean_predicted = mean_predicted,
      calibration_gap = observed - mean_predicted, calibration_in_the_large = NA_real_,
      calibration_slope = NA_real_, brier_score = NA_real_, auroc = NA_real_,
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

first_column_value <- function(frame, column_name, default = NA) {
  if (is.null(frame) || nrow(frame) == 0 || !(column_name %in% names(frame))) return(default)
  frame[[column_name]][[1]]
}

performance_interval_blocker_rows <- function(config, n, events, weighted_n, weighted_events, reason) {
  data.frame(
    model_id = config$model_id, dataset = DATASET, metric = c("auroc", "brier_score"),
    estimate = NA_real_, ci_low = NA_real_, ci_high = NA_real_, interval_level = INTERVAL_LEVEL,
    replicate_metric_sd = NA_real_, bootstrap_replicates_requested = PERFORMANCE_INTERVAL_REPLICATES,
    bootstrap_replicates_used = 0L, seed = SEED, n = n, events = events,
    weighted_n = weighted_n, weighted_events = weighted_events, method = "blocked",
    status = "blocked_interval_not_estimated", limitation = reason,
    stringsAsFactors = FALSE
  )
}

performance_intervals <- function(config, frame, predicted, performance_row) {
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
    return(list(rows = performance_interval_blocker_rows(config, n, events, weighted_n, weighted_events, reason), blocker = reason))
  }
  replicate_weights <- tryCatch(as.matrix(stats::weights(replicate_design, type = "analysis")), error = function(error) error)
  if (inherits(replicate_weights, "error") || !is.matrix(replicate_weights) || nrow(replicate_weights) != n) {
    reason <- "Bootstrap replicate weights were unavailable or did not align with the home-model analysis frame."
    if (inherits(replicate_weights, "error")) reason <- paste(reason, conditionMessage(replicate_weights))
    return(list(rows = performance_interval_blocker_rows(config, n, events, weighted_n, weighted_events, reason), blocker = reason))
  }
  auroc_replicates <- apply(replicate_weights, 2, function(weight) weighted_auc(frame$admit, frame$.__predicted, weight))
  brier_replicates <- apply(replicate_weights, 2, function(weight) weighted_mean(frame$.__brier_error, weight))
  interval_row <- function(metric, estimate, values) {
    valid_values <- values[is.finite(values)]
    if (length(valid_values) < MIN_VALID_INTERVAL_REPLICATES) {
      return(data.frame(
        model_id = config$model_id, dataset = DATASET, metric = metric, estimate = estimate,
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
      model_id = config$model_id, dataset = DATASET, metric = metric, estimate = estimate,
      ci_low = ci[[1]], ci_high = ci[[2]], interval_level = INTERVAL_LEVEL,
      replicate_metric_sd = stats::sd(valid_values),
      bootstrap_replicates_requested = PERFORMANCE_INTERVAL_REPLICATES,
      bootstrap_replicates_used = length(valid_values), seed = SEED, n = n, events = events,
      weighted_n = weighted_n, weighted_events = weighted_events,
      method = "survey_bootstrap_replicate_weights_fixed_apparent_predictions",
      status = "ok",
      limitation = paste(
        "Interval uses survey bootstrap replicate weights from pooled NHAMCS strata/PSUs and fixed apparent predictions.",
        "It is not external validation, clinical validation, or transportability evidence."
      ),
      stringsAsFactors = FALSE
    )
  }
  rows <- rbind(
    interval_row("auroc", performance_row$auroc[[1]], auroc_replicates),
    interval_row("brier_score", performance_row$brier_score[[1]], brier_replicates)
  )
  blocked <- rows$status != "ok"
  list(rows = rows, blocker = ifelse(any(blocked), paste(rows$limitation[blocked], collapse = "; "), ""))
}

write_interval_blocker <- function(config, blocker) {
  path <- file.path(output_dir, paste0(config$prefix, "_performance_intervals_blocker.md"))
  if (!nzchar(blocker)) {
    if (file.exists(path)) unlink(path)
    return(invisible(NULL))
  }
  writeLines(c(
    paste0("# ", config$model_id, " Performance Interval Blocker"),
    "",
    "At least one AUROC/Brier interval row could not be estimated defensibly.",
    "",
    "## Blocker",
    paste0("- ", blocker),
    "",
    paste0("No interval value should be inferred for blocked rows in `", config$prefix, "_performance_intervals.csv`."),
    ""
  ), con = path)
}

grouped_calibration <- function(config, frame, predicted) {
  frame$.__predicted <- predicted
  frame$.__calibration_decile <- weighted_decile(predicted, frame$weight)
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = frame)
  rows <- data.frame()
  for (group in sort(unique(frame$.__calibration_decile[!is.na(frame$.__calibration_decile)]))) {
    part <- frame[frame$.__calibration_decile == group, , drop = FALSE]
    group_design <- subset(design, .__calibration_decile == group)
    observed <- survey_mean_ci(group_design, "admit")
    predicted_mean <- survey_mean_ci(group_design, ".__predicted")
    observed_rate <- observed$estimate
    if (!is.finite(observed_rate)) observed_rate <- weighted_mean(part$admit, part$weight)
    fallback_ci <- normal_ci(observed_rate, nrow(part))
    predicted_estimate <- ifelse(is.finite(predicted_mean$estimate), predicted_mean$estimate, weighted_mean(part$.__predicted, part$weight))
    rows <- rbind(rows, data.frame(
      model_id = config$model_id, dataset = DATASET, grouping = "weighted_predicted_probability_decile",
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
      notes = paste0("Apparent grouped calibration for ", config$model_id, "; no external validation or transportability claim."),
      stringsAsFactors = FALSE
    ))
  }
  rows
}

subgroup_levels <- function(frame) {
  candidates <- c(
    "sex", "age_band_full", "race_ethnicity", "payer", "region", "msa_status",
    "adult_male_18_64_flag", "abdominal_pain_flag", "pas5_surrogate_class",
    "high_acuity_proxy",
    "temp_availability", "HR_availability", "SBP_availability"
  )
  candidates[candidates %in% names(frame)]
}

subgroup_metric_rows <- function(config, frame, predicted) {
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
        model_id = config$model_id, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
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

subgroup_calibration_rows <- function(config, frame, predicted) {
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
          model_id = config$model_id, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
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
        model_id = config$model_id, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
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

missingness_rows <- function(config, binary, complete_case) {
  rows <- data.frame()
  fields <- c("age_availability", "sex_availability", "pas5_surrogate_availability", "temp_availability", "HR_availability", "SBP_availability")
  for (field in fields) {
    for (value in sort(unique(binary[[field]]))) {
      part <- binary[binary[[field]] == value, , drop = FALSE]
      complete_part <- complete_case[rownames(complete_case) %in% rownames(part), , drop = FALSE]
      rows <- rbind(rows, data.frame(
        model_id = config$model_id, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
        field = field, level = value,
        denominator_n = nrow(part), denominator_events = sum(part$admit == 1),
        denominator_weighted_n = sum(part$weight), denominator_weighted_events = sum(part$weight[part$admit == 1]),
        model_estimable_n = nrow(complete_part), model_estimable_events = sum(complete_part$admit == 1),
        status = ifelse(nrow(complete_part) > 0, "ok", "blocked_no_model_estimable_rows"),
        blocker = ifelse(nrow(complete_part) > 0, "", "No complete-case rows for this missingness level."),
        method = "required_predictor_missingness_audit",
        limitation = ifelse(
          config$include_sbp,
          "Measured-SBP branch does not impute missing SBP.",
          "Default home branch does not require or impute SBP."
        ),
        stringsAsFactors = FALSE
      ))
    }
  }
  rows
}

optimism_blocker_rows <- function(config, reason, apparent_metrics) {
  data.frame(
    model_id = config$model_id, dataset = DATASET,
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

write_optimism_blocker <- function(config, reason) {
  path <- file.path(output_dir, paste0(config$prefix, "_optimism_corrected_performance_blocker.md"))
  if (!nzchar(reason)) {
    if (file.exists(path)) unlink(path)
    return(invisible(NULL))
  }
  writeLines(c(
    paste0("# ", config$model_id, " Optimism-Corrected Performance Blocker"),
    "",
    "Survey-bootstrap refit optimism correction was not produced.",
    "",
    "## Blocker",
    paste0("- ", reason),
    "",
    paste0("Use `", config$prefix, "_performance_intervals.csv` as the current fixed-prediction interval artifact."),
    ""
  ), con = path)
}

optimism_corrected_performance <- function(config, frame, formula, apparent_metrics) {
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = frame)
  set.seed(SEED)
  replicate_design <- tryCatch(
    survey::as.svrepdesign(design, type = "bootstrap", replicates = OPTIMISM_BOOTSTRAP_REPLICATES, mse = TRUE),
    error = function(error) error
  )
  if (inherits(replicate_design, "error")) {
    reason <- paste("survey::as.svrepdesign bootstrap failed:", conditionMessage(replicate_design))
    write_optimism_blocker(config, reason)
    return(optimism_blocker_rows(config, reason, apparent_metrics))
  }
  replicate_weights <- tryCatch(as.matrix(stats::weights(replicate_design, type = "analysis")), error = function(error) error)
  if (inherits(replicate_weights, "error") || !is.matrix(replicate_weights) || nrow(replicate_weights) != nrow(frame)) {
    reason <- "Bootstrap replicate weights were unavailable or did not align with the home-model analysis frame."
    if (inherits(replicate_weights, "error")) reason <- paste(reason, conditionMessage(replicate_weights))
    write_optimism_blocker(config, reason)
    return(optimism_blocker_rows(config, reason, apparent_metrics))
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
    write_optimism_blocker(config, reason)
    return(optimism_blocker_rows(config, reason, apparent_metrics))
  }
  write_optimism_blocker(config, "")
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
      model_id = config$model_id, dataset = DATASET, metric = metric,
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
  if (identical(name, "high_acuity_proxy")) return(list(term = "high_acuity_proxy", level = "1"))
  if (identical(name, "tachycardia_burden")) return(list(term = "tachycardia_burden", level = "per_10_bpm_over_100"))
  if (identical(name, "hypotension_burden")) return(list(term = "hypotension_burden", level = "per_10_mmhg_below_100"))
  if (startsWith(name, "sex")) return(list(term = "sex", level = sub("^sex", "", name)))
  list(term = name, level = "")
}

coefficient_label <- function(parsed) {
  if (identical(parsed$level, "")) parsed$term else paste0(parsed$term, "[", parsed$level, "]")
}

optimism_metric <- function(optimism, metric_name) {
  if (is.null(optimism) || nrow(optimism) == 0 || !("metric" %in% names(optimism))) return(NA_real_)
  rows <- optimism[optimism$metric == metric_name, , drop = FALSE]
  if (nrow(rows) == 0 || !("optimism_corrected_estimate" %in% names(rows))) return(NA_real_)
  as.numeric(rows$optimism_corrected_estimate[[1]])
}

comparison_row <- function(config, performance, calibration, optimism, status, limitation) {
  data.frame(
    model_id = config$model_id,
    comparison_role = config$role,
    dataset = DATASET,
    target = TARGET,
    source_scope = SOURCE_SCOPE,
    n = as.numeric(first_column_value(performance, "n")),
    events = as.numeric(first_column_value(performance, "events")),
    model_estimable_n = as.numeric(first_column_value(performance, "model_estimable_n")),
    model_estimable_events = as.numeric(first_column_value(performance, "model_estimable_events")),
    auroc = as.numeric(first_column_value(performance, "auroc")),
    brier_score = as.numeric(first_column_value(performance, "brier_score")),
    calibration_in_the_large = as.numeric(first_column_value(calibration, "calibration_in_the_large")),
    calibration_slope = as.numeric(first_column_value(calibration, "calibration_slope")),
    optimism_corrected_auroc = optimism_metric(optimism, "auroc"),
    optimism_corrected_brier_score = optimism_metric(optimism, "brier_score"),
    status = status,
    limitation = limitation,
    stringsAsFactors = FALSE
  )
}

delta_row <- function(default_row, measured_row) {
  numeric_columns <- c(
    "n", "events", "model_estimable_n", "model_estimable_events", "auroc",
    "brier_score", "calibration_in_the_large", "calibration_slope",
    "optimism_corrected_auroc", "optimism_corrected_brier_score"
  )
  row <- measured_row
  row$model_id <- "general-E-Dispo-home-v1-measured-sbp_minus_default"
  row$comparison_role <- "measured_sbp_minus_default"
  for (column_name in numeric_columns) {
    row[[column_name]] <- as.numeric(measured_row[[column_name]]) - as.numeric(default_row[[column_name]])
  }
  row$status <- ifelse(
    all(is.finite(c(as.numeric(row$auroc), as.numeric(row$brier_score)))),
    "computed",
    "blocked_nonfinite_delta"
  )
  row$limitation <- "Metric deltas compare the measured-SBP branch against the home default using internal NHAMCS apparent/internal artifacts only."
  row
}

write_model_spec <- function(config, input_n, input_events, complete_case_n, complete_case_events) {
  survey_version <- ""
  if (requireNamespace("survey", quietly = TRUE)) survey_version <- as.character(utils::packageVersion("survey"))
  files <- output_files(config$prefix)
  transformations <- c(
    '    "age_centered_40": "age - 40"',
    '    "sex": "categorical harmonized cohort sex column; main effect only"',
    '    "pas5_surrogate_class": "NHAMCS IMMEDR 1-5 maps to PAS-5 A1-A5 surrogate classes"',
    '    "high_acuity_proxy": "1 for PAS-5 surrogate A1/A2; 0 for A3/A4/A5; missing for unmappable IMMEDR"',
    '    "fever_or_temp": "1[temp >= 100.4F] when temperature observed"',
    '    "tachycardia_burden": "max(HR - 100, 0) / 10"'
  )
  if (config$include_sbp) {
    transformations <- c(transformations, '    "hypotension_burden": "max(100 - SBP, 0) / 10; only when SBP is measured"')
  }
  transformation_lines <- paste0(transformations, c(rep(",", length(transformations) - 1), ""))
  lines <- c(
    "{",
    paste0('  "model_id": "', config$model_id, '",'),
    paste0('  "model_role": "', config$role, '",'),
    '  "active_adult_male_abdominal_pain_app_model": false,',
    '  "replaces_e_dispo_v4_1": false,',
    '  "replaces_general_e_dispo_model_v1_plus_sex": false,',
    '  "public_general_demo_branch": true,',
    paste0('  "dataset": "', DATASET, '",'),
    paste0('  "source_scope": "', SOURCE_SCOPE, '",'),
    '  "cohort": "all-sex/all-age NHAMCS 2018-2022 non-trauma ED records with strict admit-vs-routine-home endpoint",',
    '  "target": "endpoint_class == admit versus endpoint_class == routine_home_discharge; transfer excluded from fitting",',
    paste0('  "formula": "', config$formula_text, '",'),
    paste0('  "age_center": ', AGE_CENTER, ','),
    '  "factor_references": {',
    '    "sex": "1"',
    '  },',
    '  "transformations": {',
    transformation_lines,
    '  },',
    '  "excluded_from_primary_formula": ["arrival_transfer_context", "raw_acuity_code", "pain", "vomiting", "nausea", "hematemesis", "payer", "race_ethnicity", "region", "MSA", "imaging", "medication", "length_of_visit", "wait_time", "treatment", "diagnosis", "disposition_derived_fields"],',
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
    '    "not medical advice",',
    '    "not external validation",',
    '    "not transportability evidence",',
    '    "transfer-in context is excluded from the fitted formula and public user inputs",',
    ifelse(config$include_sbp, '    "SBP is optional and must be measured when supplied"', '    "SBP is not required by this default branch"'),
    '  ]',
    "}"
  )
  writeLines(lines, con = file.path(output_dir, files[["spec"]]))
}

write_blocker_outputs <- function(config, reason, input_n = 0L, input_events = 0L, binary = NULL) {
  files <- output_files(config$prefix)
  weighted_n <- if (!is.null(binary) && "weight" %in% names(binary)) sum(binary$weight, na.rm = TRUE) else NA_real_
  weighted_events <- if (!is.null(binary) && all(c("weight", "admit") %in% names(binary))) sum(binary$weight[binary$admit == 1], na.rm = TRUE) else NA_real_
  coefficients <- data.frame(
    model_id = config$model_id, dataset = DATASET, term = "blocked", level = "",
    beta = NA_real_, se = NA_real_, odds_ratio = NA_real_, ci_low = NA_real_,
    ci_high = NA_real_, p_value = NA_real_, evidence_tier = "blocked",
    limitation_note = reason, stringsAsFactors = FALSE
  )
  covariance <- data.frame(
    model_id = config$model_id, dataset = DATASET, row_term = "blocked",
    column_term = "blocked", covariance = NA_real_, stringsAsFactors = FALSE
  )
  performance <- data.frame(
    model_id = config$model_id, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
    n = input_n, events = input_events, non_events = max(input_n - input_events, 0L),
    model_estimable_n = 0L, model_estimable_events = 0L, weighted_n = weighted_n,
    weighted_events = weighted_events, observed_prevalence = NA_real_, mean_predicted = NA_real_,
    calibration_gap = NA_real_, auroc = NA_real_, brier_score = NA_real_,
    formula = config$formula_text, method = "blocked", status = "blocked_not_fit",
    limitation = reason, stringsAsFactors = FALSE
  )
  calibration <- data.frame(
    model_id = config$model_id, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
    n = input_n, events = input_events, observed_prevalence = NA_real_,
    mean_predicted = NA_real_, calibration_in_the_large = NA_real_,
    calibration_slope = NA_real_, method = "blocked", status = "blocked_not_fit",
    limitation = reason, stringsAsFactors = FALSE
  )
  deciles <- data.frame(
    model_id = config$model_id, dataset = DATASET, grouping = "weighted_predicted_probability_decile",
    decile = NA_integer_, n = input_n, events = input_events, weighted_n = weighted_n,
    weighted_events = weighted_events, predicted_min = NA_real_, predicted_max = NA_real_,
    mean_predicted = NA_real_, mean_predicted_se = NA_real_, observed_rate = NA_real_,
    observed_rate_se = NA_real_, observed_rate_ci_low = NA_real_, observed_rate_ci_high = NA_real_,
    calibration_gap = NA_real_, ci_method = "blocked", status = "blocked_not_fit",
    notes = reason, stringsAsFactors = FALSE
  )
  intervals <- performance_interval_blocker_rows(config, input_n, input_events, weighted_n, weighted_events, reason)
  optimism <- optimism_blocker_rows(config, reason, list(auroc = NA_real_, brier_score = NA_real_, calibration_in_the_large = NA_real_, calibration_slope = NA_real_))
  subgroup <- data.frame(
    model_id = config$model_id, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
    subgroup = "overall", level = "blocked", n = input_n, events = input_events,
    non_events = max(input_n - input_events, 0L), weighted_n = weighted_n,
    weighted_events = weighted_events, observed_prevalence = NA_real_, mean_predicted = NA_real_,
    calibration_gap = NA_real_, auroc = NA_real_, brier_score = NA_real_,
    status = "blocked_not_fit", blocker = reason, method = "blocked",
    limitation = reason, stringsAsFactors = FALSE
  )
  subgroup_calibration <- data.frame(
    model_id = config$model_id, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
    subgroup = "overall", level = "blocked", n = input_n, events = input_events,
    non_events = max(input_n - input_events, 0L), calibration_in_the_large = NA_real_,
    calibration_slope = NA_real_, status = "blocked_not_fit", blocker = reason,
    method = "blocked", limitation = reason, stringsAsFactors = FALSE
  )
  missingness <- data.frame(
    model_id = config$model_id, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
    field = "blocked", level = "blocked", denominator_n = input_n,
    denominator_events = input_events, denominator_weighted_n = weighted_n,
    denominator_weighted_events = weighted_events, model_estimable_n = 0L,
    model_estimable_events = 0L, status = "blocked_not_fit", blocker = reason,
    method = "blocked", limitation = reason, stringsAsFactors = FALSE
  )
  utils::write.csv(coefficients, file.path(output_dir, files[["coefficients"]]), row.names = FALSE, na = "")
  utils::write.csv(covariance, file.path(output_dir, files[["covariance"]]), row.names = FALSE, na = "")
  utils::write.csv(performance, file.path(output_dir, files[["performance"]]), row.names = FALSE, na = "")
  utils::write.csv(calibration, file.path(output_dir, files[["calibration"]]), row.names = FALSE, na = "")
  utils::write.csv(deciles, file.path(output_dir, files[["calibration_by_decile"]]), row.names = FALSE, na = "")
  utils::write.csv(intervals, file.path(output_dir, files[["performance_intervals"]]), row.names = FALSE, na = "")
  utils::write.csv(optimism, file.path(output_dir, files[["optimism"]]), row.names = FALSE, na = "")
  utils::write.csv(subgroup, file.path(output_dir, files[["subgroup_performance"]]), row.names = FALSE, na = "")
  utils::write.csv(subgroup_calibration, file.path(output_dir, files[["subgroup_calibration"]]), row.names = FALSE, na = "")
  utils::write.csv(missingness, file.path(output_dir, files[["missingness"]]), row.names = FALSE, na = "")
  write_model_spec(config, input_n, input_events, 0L, 0L)
  writeLines(c(
    paste0("# ", config$model_id),
    "",
    "Status: `blocked_not_fit`.",
    "",
    "## Blocker",
    paste0("- ", reason),
    "",
    "No coefficient or performance estimate should be inferred from blocked rows.",
    "",
    "This artifact does not replace the active adult-male abdominal-pain model and does not support clinical use.",
    ""
  ), con = file.path(output_dir, files[["report"]]))
  list(config = config, performance = performance, calibration = calibration, optimism = optimism, subgroup = subgroup, blocked = TRUE)
}

fit_one_model <- function(config, binary) {
  input_n <- nrow(binary)
  input_events <- sum(binary$admit == 1)
  if (input_n == 0 || input_events == 0 || sum(binary$admit == 0) == 0) {
    return(write_blocker_outputs(config, "No usable admit-vs-home denominator after full-source non-trauma endpoint filtering.", input_n, input_events, binary))
  }

  sex_levels <- sort(unique(binary$sex[!is.na(binary$sex)]))
  if (length(sex_levels) == 0) {
    return(write_blocker_outputs(config, "The harmonized sex column is present but all values are missing in the admit-vs-home denominator.", input_n, input_events, binary))
  }
  if (length(sex_levels) < 2) {
    return(write_blocker_outputs(config, paste0("The harmonized sex column has only one non-missing level in the admit-vs-home denominator: ", paste(sex_levels, collapse = ", ")), input_n, input_events, binary))
  }

  required_mask <- !is.na(binary$admit) & binary$admit %in% c(0, 1) &
    !is.na(binary$year) & !is.na(binary$age_centered_40) &
    !is.na(binary$sex) & !is.na(binary$high_acuity_proxy) &
    !is.na(binary$fever_or_temp) & !is.na(binary$tachycardia_burden) &
    !is.na(binary$weight) & binary$weight > 0 &
    !is.na(binary$stratum) & !is.na(binary$psu)
  if (config$include_sbp) {
    required_mask <- required_mask & !is.na(binary$hypotension_burden)
  }
  complete_case <- binary[required_mask, , drop = FALSE]

  if (nrow(complete_case) == 0 || sum(complete_case$admit == 1) == 0 || sum(complete_case$admit == 0) == 0) {
    return(write_blocker_outputs(config, "No usable complete-case rows with both outcomes for the home-facing general predictor surface.", input_n, input_events, binary))
  }

  complete_sex_levels <- sort(unique(complete_case$sex[!is.na(complete_case$sex)]))
  if (length(complete_sex_levels) < 2) {
    return(write_blocker_outputs(config, paste0("The harmonized sex column has fewer than two non-missing levels after complete-case restriction: ", paste(complete_sex_levels, collapse = ", ")), input_n, input_events, binary))
  }

  complete_case$sex <- factor(complete_case$sex, levels = sex_levels)
  if ("1" %in% levels(complete_case$sex)) {
    complete_case$sex <- stats::relevel(complete_case$sex, ref = "1")
  }

  formula <- stats::as.formula(config$formula_text)
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = complete_case)
  fit <- tryCatch(survey::svyglm(formula, design = design, family = quasibinomial()), error = function(error) error)
  if (inherits(fit, "error")) {
    return(write_blocker_outputs(config, paste("survey::svyglm failed:", conditionMessage(fit)), input_n, input_events, binary))
  }

  predicted <- as.numeric(stats::predict(fit, type = "response"))
  if (!all(is.finite(predicted))) {
    return(write_blocker_outputs(config, "Fitted model produced non-finite predictions.", input_n, input_events, binary))
  }
  complete_case$.__predicted <- predicted

  beta <- stats::coef(fit)
  covariance_matrix <- stats::vcov(fit)
  se <- sqrt(pmax(diag(covariance_matrix), 0))
  coef_table <- summary(fit)$coefficients
  parsed_terms <- lapply(names(beta), parse_coefficient)
  labels <- vapply(parsed_terms, coefficient_label, character(1))

  coefficients <- data.frame(
    model_id = config$model_id,
    dataset = DATASET,
    term = vapply(parsed_terms, function(item) item$term, character(1)),
    level = vapply(parsed_terms, function(item) item$level, character(1)),
    beta = as.numeric(beta),
    se = as.numeric(se),
    odds_ratio = exp(as.numeric(beta)),
    ci_low = exp(as.numeric(beta) - 1.96 * as.numeric(se)),
    ci_high = exp(as.numeric(beta) + 1.96 * as.numeric(se)),
    p_value = as.numeric(coef_table[, ncol(coef_table)]),
    evidence_tier = config$evidence_tier,
    limitation_note = config$limitation_note,
    stringsAsFactors = FALSE
  )

  covariance_rows <- data.frame()
  for (row_index in seq_along(labels)) {
    for (column_index in seq_along(labels)) {
      covariance_rows <- rbind(covariance_rows, data.frame(
        model_id = config$model_id, dataset = DATASET, row_term = labels[[row_index]],
        column_term = labels[[column_index]], covariance = covariance_matrix[row_index, column_index],
        stringsAsFactors = FALSE
      ))
    }
  }

  metrics <- metric_summary(complete_case, predicted, complete_case$weight, status_prefix = config$evidence_tier)
  performance <- data.frame(
    model_id = config$model_id, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
    n = input_n, events = input_events, non_events = input_n - input_events,
    model_estimable_n = nrow(complete_case), model_estimable_events = sum(complete_case$admit == 1),
    weighted_n = sum(binary$weight), weighted_events = sum(binary$weight[binary$admit == 1]),
    observed_prevalence = metrics$observed_prevalence, mean_predicted = metrics$mean_predicted,
    calibration_gap = metrics$calibration_gap, auroc = metrics$auroc, brier_score = metrics$brier_score,
    formula = config$formula_text, method = "survey::svyglm_quasibinomial_full_source_nontrauma_complete_case",
    status = config$evidence_tier, limitation = config$limitation_note,
    stringsAsFactors = FALSE
  )

  calibration <- data.frame(
    model_id = config$model_id, dataset = DATASET, target = TARGET, source_scope = SOURCE_SCOPE,
    n = nrow(complete_case), events = sum(complete_case$admit == 1),
    observed_prevalence = metrics$observed_prevalence, mean_predicted = metrics$mean_predicted,
    calibration_in_the_large = metrics$calibration_in_the_large,
    calibration_slope = metrics$calibration_slope,
    method = "survey::svyglm_calibration_on_home_model_predictions",
    status = metrics$status, limitation = "Apparent calibration for the same NHAMCS source cohort; no external validation or transportability claim.",
    stringsAsFactors = FALSE
  )

  calibration_by_decile <- grouped_calibration(config, complete_case, predicted)
  interval_result <- performance_intervals(config, complete_case, predicted, performance)
  write_interval_blocker(config, interval_result$blocker)
  subgroup_performance <- subgroup_metric_rows(config, complete_case, predicted)
  subgroup_calibration <- subgroup_calibration_rows(config, complete_case, predicted)
  missingness <- missingness_rows(config, binary, complete_case)
  apparent_metrics <- list(
    auroc = performance$auroc[[1]],
    brier_score = performance$brier_score[[1]],
    calibration_in_the_large = calibration$calibration_in_the_large[[1]],
    calibration_slope = calibration$calibration_slope[[1]]
  )
  optimism <- optimism_corrected_performance(config, complete_case, formula, apparent_metrics)

  sex_table <- table(binary$sex, useNA = "ifany")
  sbp_lines <- if (config$include_sbp) {
    c(
      "- SBP branch: measured-SBP variant.",
      paste0("- Complete-case rows with measured SBP: ", nrow(complete_case))
    )
  } else {
    c(
      "- SBP branch: default no-SBP model.",
      "- Missing SBP does not block the default branch."
    )
  }

  report <- c(
    paste0("# ", config$model_id),
    "",
    paste0("Model ID: `", config$model_id, "`"),
    paste0("Status: `", config$evidence_tier, "`."),
    "",
    "This is a home-facing all-sex/all-age NHAMCS non-trauma educational/statistical model artifact. It is not the active adult-male abdominal-pain model, not clinical decision support, not medical advice, not external validation, and not transportability evidence.",
    "",
    "## Method",
    "",
    "- Cohort: full-source NHAMCS 2018-2022 non-trauma ED records; no sex, age, or abdominal-pain gate is applied.",
    "- Target: same-hospital admission versus routine home discharge; transfer remains excluded from the admit model endpoint.",
    paste0("- Formula: `", config$formula_text, "`."),
    "- Fit: `survey::svyglm(..., family = quasibinomial())` with pooled NHAMCS weights, strata, and PSUs.",
    "- Reference levels: `sex = 1`; `high_acuity_proxy = 0`.",
    "- PAS-5 proxy: NHAMCS `IMMEDR` maps to surrogate A1-A5 classes; A1/A2 activate `high_acuity_proxy`, and A3/A4/A5 are reference.",
    "- Transfer-in context is excluded from the fitted formula and public user inputs because it does not map to a person starting at home.",
    "- Excluded from fitted formula: arrival-transfer context, raw categorical acuity, pain, vomiting, nausea, hematemesis, payer, race/ethnicity, region, MSA, imaging, medication, length-of-visit, wait-time, treatment, diagnosis, and disposition-derived variables.",
    ifelse(config$include_sbp, "- SBP is optional and must be measured when supplied; this branch is not used for blank/unknown SBP.", "- SBP is not required in this default branch and is not imputed."),
    "",
    "## Counts",
    "",
    paste0("- Admit-vs-home denominator N: ", input_n),
    paste0("- Admission events before complete-case restriction: ", input_events),
    paste0("- Complete-case N: ", nrow(complete_case)),
    paste0("- Complete-case admission events: ", sum(complete_case$admit == 1)),
    paste0("- Admit-vs-home denominator sex-code counts: ", paste(paste0(names(sex_table), "=", as.integer(sex_table)), collapse = "; ")),
    sbp_lines,
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
    paste0("- ", unname(output_files(config$prefix))),
    "",
    "## Boundary",
    "",
    "This model remains educational/statistical only. It does not change the adult-male abdominal-pain model and does not support patient-level clinical use.",
    ""
  )

  files <- output_files(config$prefix)
  utils::write.csv(coefficients, file.path(output_dir, files[["coefficients"]]), row.names = FALSE, na = "")
  utils::write.csv(covariance_rows, file.path(output_dir, files[["covariance"]]), row.names = FALSE, na = "")
  utils::write.csv(performance, file.path(output_dir, files[["performance"]]), row.names = FALSE, na = "")
  utils::write.csv(calibration, file.path(output_dir, files[["calibration"]]), row.names = FALSE, na = "")
  utils::write.csv(calibration_by_decile, file.path(output_dir, files[["calibration_by_decile"]]), row.names = FALSE, na = "")
  utils::write.csv(interval_result$rows, file.path(output_dir, files[["performance_intervals"]]), row.names = FALSE, na = "")
  utils::write.csv(optimism, file.path(output_dir, files[["optimism"]]), row.names = FALSE, na = "")
  utils::write.csv(subgroup_performance, file.path(output_dir, files[["subgroup_performance"]]), row.names = FALSE, na = "")
  utils::write.csv(subgroup_calibration, file.path(output_dir, files[["subgroup_calibration"]]), row.names = FALSE, na = "")
  utils::write.csv(missingness, file.path(output_dir, files[["missingness"]]), row.names = FALSE, na = "")
  write_model_spec(config, input_n, input_events, nrow(complete_case), sum(complete_case$admit == 1))
  writeLines(report, con = file.path(output_dir, files[["report"]]))

  list(
    config = config,
    performance = performance,
    calibration = calibration,
    optimism = optimism,
    subgroup = subgroup_performance,
    blocked = FALSE
  )
}

prepare_binary <- function(cohort) {
  required_common <- c(
    "endpoint_class", "admit", "year", "age", "sex", "age_band_full",
    "fever_or_temp", "HR", "tachycardia_burden",
    "pooled_weight", "pooled_stratum", "pooled_psu"
  )
  missing_common <- setdiff(required_common, names(cohort))
  if (length(missing_common) > 0) {
    stop(paste("Missing required columns:", paste(missing_common, collapse = ", ")))
  }
  immedr_matches <- c("IMMEDR", "immedr", "acuity")[c("IMMEDR", "immedr", "acuity") %in% names(cohort)]
  if (length(immedr_matches) == 0) {
    stop("Missing required IMMEDR acuity surrogate column. Checked: IMMEDR, immedr, acuity")
  }
  immedr_column <- immedr_matches[[1]]

  binary <- cohort[cohort$endpoint_class %in% c("admit", "routine_home_discharge"), , drop = FALSE]
  binary$admit <- as.numeric(binary$endpoint_class == "admit")
  binary$year <- as.integer(binary$year)
  binary$age <- as.numeric(binary$age)
  binary$age_centered_40 <- binary$age - AGE_CENTER
  binary$sex <- trimws(as.character(binary$sex))
  binary$sex[binary$sex == ""] <- NA
  binary$.__raw_immedr <- binary[[immedr_column]]
  binary$pas5_surrogate_class <- map_immedr_class(binary$.__raw_immedr)
  binary$high_acuity_proxy <- ifelse(
    binary$pas5_surrogate_class %in% c("A1", "A2"),
    1,
    ifelse(binary$pas5_surrogate_class %in% c("A3", "A4", "A5"), 0, NA_real_)
  )
  binary$fever_or_temp <- as.numeric(binary$fever_or_temp)
  binary$HR <- as.numeric(binary$HR)
  binary$tachycardia_burden <- as.numeric(binary$tachycardia_burden)
  if ("SBP" %in% names(binary)) binary$SBP <- as.numeric(binary$SBP)
  if (!("hypotension_burden" %in% names(binary))) binary$hypotension_burden <- NA_real_
  binary$hypotension_burden <- as.numeric(binary$hypotension_burden)
  binary$weight <- as.numeric(binary$pooled_weight)
  binary$stratum <- as.factor(binary$pooled_stratum)
  binary$psu <- as.factor(binary$pooled_psu)
  binary$age_availability <- ifelse(is.na(binary$age), "missing_age", "observed_age")
  binary$sex_availability <- ifelse(is.na(binary$sex), "missing_sex", "observed_sex")
  binary$pas5_surrogate_availability <- ifelse(is.na(binary$high_acuity_proxy), "missing_or_unmappable_IMMEDR_for_pas5_proxy", "mapped_IMMEDR_to_pas5_proxy")
  binary$temp_availability <- ifelse(is.na(binary$fever_or_temp), "missing_temp_or_fever_proxy", "observed_temp_or_fever_proxy")
  binary$HR_availability <- ifelse(is.na(binary$tachycardia_burden), "missing_HR", "observed_HR")
  binary$SBP_availability <- ifelse(is.na(binary$hypotension_burden), "missing_SBP", "observed_SBP")
  binary
}

write_comparison <- function(results) {
  default_result <- results[[1]]
  measured_result <- results[[2]]
  default_row <- comparison_row(
    default_result$config,
    default_result$performance,
    default_result$calibration,
    default_result$optimism,
    as.character(first_column_value(default_result$performance, "status", "unknown")),
    as.character(first_column_value(default_result$performance, "limitation", ""))
  )
  measured_row <- comparison_row(
    measured_result$config,
    measured_result$performance,
    measured_result$calibration,
    measured_result$optimism,
    as.character(first_column_value(measured_result$performance, "status", "unknown")),
    as.character(first_column_value(measured_result$performance, "limitation", ""))
  )
  comparison <- rbind(default_row, measured_row, delta_row(default_row, measured_row))
  utils::write.csv(comparison, file.path(output_dir, "general_e_dispo_home_v1_sbp_optional_comparison.csv"), row.names = FALSE, na = "")
}

if (!file.exists(input_path)) {
  results <- lapply(model_configs, function(config) {
    write_blocker_outputs(config, paste("Input cohort is missing:", input_path))
  })
  write_comparison(results)
  quit(status = 2)
}

cohort <- read.csv(input_path, stringsAsFactors = FALSE, na.strings = c("", "NA", "NaN"))
binary <- tryCatch(prepare_binary(cohort), error = function(error) error)
if (inherits(binary, "error")) {
  results <- lapply(model_configs, function(config) {
    write_blocker_outputs(config, conditionMessage(binary))
  })
  write_comparison(results)
  quit(status = 2)
}

results <- lapply(model_configs, function(config) fit_one_model(config, binary))
write_comparison(results)

all_blocked <- all(vapply(results, function(result) isTRUE(result$blocked), logical(1)))
cat("Wrote general-E-Dispo home-facing outputs under ", output_dir, "\n", sep = "")
if (all_blocked) quit(status = 2)
