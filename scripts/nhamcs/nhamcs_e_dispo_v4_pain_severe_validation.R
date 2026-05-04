#!/usr/bin/env Rscript

# Versioned e-dispo-v4.0 severe-pain validation.
#
# This script refits the active educational model with
# pain_severe = 1[pain_bin3 == severe], preserving the v2 complete-case
# restrictions for observed pain, fever/temp, vomiting, HR, and endpoint.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: nhamcs_e_dispo_v4_pain_severe_validation.R <pooled_analytic_cohort_csv> <output_dir>")
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
MODEL_ID <- "e-dispo-v4.0"
SEED <- 20260428L
DRAW_COUNT <- 10000L
PERFORMANCE_INTERVAL_REPLICATES <- 1000L
OPTIMISM_BOOTSTRAP_REPLICATES <- 200L
INTERVAL_LEVEL <- 0.95
AGE_CENTER <- 42
MIN_SUBGROUP_EVENTS <- 10L
MIN_SUBGROUP_NONEVENTS <- 10L
MIN_OPTIMISM_VALID_REPLICATES <- 50L
set.seed(SEED)

weighted_mean <- function(value, weight) {
  valid <- !is.na(value) & !is.na(weight)
  if (!any(valid) || sum(weight[valid]) == 0) return(NA_real_)
  sum(value[valid] * weight[valid]) / sum(weight[valid])
}

truthy <- function(value) tolower(trimws(as.character(value))) %in% c("true", "1", "yes")

logit <- function(value) {
  clipped <- pmin(pmax(value, 1e-6), 1 - 1e-6)
  log(clipped / (1 - clipped))
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

normal_ci <- function(rate, n) {
  if (is.na(rate) || !is.finite(rate) || n <= 0) return(c(NA_real_, NA_real_))
  se <- sqrt(rate * (1 - rate) / n)
  c(max(0, rate - 1.96 * se), min(1, rate + 1.96 * se))
}

survey_mean_ci <- function(design, variable_name) {
  formula <- stats::as.formula(paste0("~", variable_name))
  result <- tryCatch({
    mean_result <- survey::svymean(formula, design = design, na.rm = TRUE)
    ci <- stats::confint(mean_result, level = INTERVAL_LEVEL)
    list(
      estimate = as.numeric(stats::coef(mean_result)[[1]]),
      se = as.numeric(survey::SE(mean_result)[[1]]),
      ci_low = as.numeric(ci[1, 1]),
      ci_high = as.numeric(ci[1, 2]),
      status = "ok",
      note = ""
    )
  }, error = function(error) {
    list(
      estimate = NA_real_,
      se = NA_real_,
      ci_low = NA_real_,
      ci_high = NA_real_,
      status = "blocked_survey_mean_failed",
      note = conditionMessage(error)
    )
  })
  result
}

weighted_decile <- function(predicted, weight) {
  decile <- rep(NA_integer_, length(predicted))
  valid <- !is.na(predicted) & !is.na(weight) & weight > 0
  if (!any(valid) || sum(weight[valid]) <= 0) return(decile)
  valid_index <- which(valid)
  order_index <- valid_index[order(predicted[valid], seq_along(predicted[valid]))]
  cumulative_share <- cumsum(weight[order_index]) / sum(weight[order_index])
  decile[order_index] <- pmin(10L, pmax(1L, ceiling(cumulative_share * 10L)))
  decile
}

grouped_calibration <- function(model_id, frame, predicted) {
  frame$.__predicted <- predicted
  frame$.__calibration_decile <- weighted_decile(predicted, frame$weight)
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = frame)
  rows <- data.frame()
  for (group in sort(unique(frame$.__calibration_decile[!is.na(frame$.__calibration_decile)]))) {
    subset <- frame$.__calibration_decile == group
    part <- frame[subset, , drop = FALSE]
    group_design <- subset(design, .__calibration_decile == group)
    observed <- survey_mean_ci(group_design, "admit")
    predicted_mean <- survey_mean_ci(group_design, ".__predicted")
    observed_rate <- observed$estimate
    if (!is.finite(observed_rate)) {
      observed_rate <- weighted_mean(part$admit, part$weight)
    }
    fallback_ci <- normal_ci(observed_rate, nrow(part))
    rows <- rbind(rows, data.frame(
      model_id = model_id,
      dataset = DATASET,
      grouping = "weighted_predicted_probability_decile",
      decile = as.integer(group),
      n = nrow(part),
      events = sum(part$admit == 1),
      weighted_n = sum(part$weight),
      weighted_events = sum(part$weight[part$admit == 1]),
      predicted_min = min(part$.__predicted),
      predicted_max = max(part$.__predicted),
      mean_predicted = ifelse(is.finite(predicted_mean$estimate), predicted_mean$estimate, weighted_mean(part$.__predicted, part$weight)),
      mean_predicted_se = predicted_mean$se,
      observed_rate = observed_rate,
      observed_rate_se = observed$se,
      observed_rate_ci_low = ifelse(is.finite(observed$ci_low), max(0, observed$ci_low), fallback_ci[[1]]),
      observed_rate_ci_high = ifelse(is.finite(observed$ci_high), min(1, observed$ci_high), fallback_ci[[2]]),
      calibration_gap = observed_rate - ifelse(is.finite(predicted_mean$estimate), predicted_mean$estimate, weighted_mean(part$.__predicted, part$weight)),
      ci_method = ifelse(identical(observed$status, "ok"), "survey_taylor_linearized_group_mean", "fallback_unweighted_normal_group_interval"),
      status = ifelse(identical(observed$status, "ok") && identical(predicted_mean$status, "ok"), "ok", "partial"),
      notes = paste(
        "Grouped calibration for apparent active-model predictions.",
        "Groups are weighted deciles of predicted probability.",
        "Intervals are for observed group admission rate, not external calibration."
      ),
      stringsAsFactors = FALSE
    ))
  }
  rows
}

calibration_plot_data <- function(calibration_groups) {
  data.frame(
    model_id = calibration_groups$model_id,
    dataset = calibration_groups$dataset,
    series = "apparent_weighted_decile_calibration",
    decile = calibration_groups$decile,
    x_mean_predicted = calibration_groups$mean_predicted,
    y_observed_rate = calibration_groups$observed_rate,
    y_observed_rate_ci_low = calibration_groups$observed_rate_ci_low,
    y_observed_rate_ci_high = calibration_groups$observed_rate_ci_high,
    identity_x = calibration_groups$mean_predicted,
    identity_y = calibration_groups$mean_predicted,
    n = calibration_groups$n,
    weighted_n = calibration_groups$weighted_n,
    method = "survey-weighted grouped calibration by weighted predicted-probability decile",
    notes = "Plot-ready data only; no claim of external validation or transportability.",
    stringsAsFactors = FALSE
  )
}

performance_interval_blocker_rows <- function(model_id, n, events, reason) {
  data.frame(
    model_id = model_id,
    dataset = DATASET,
    metric = c("auroc", "brier_score"),
    estimate = NA_real_,
    ci_low = NA_real_,
    ci_high = NA_real_,
    interval_level = INTERVAL_LEVEL,
    replicate_metric_sd = NA_real_,
    bootstrap_replicates_requested = PERFORMANCE_INTERVAL_REPLICATES,
    bootstrap_replicates_used = 0L,
    seed = SEED,
    n = n,
    events = events,
    weighted_n = NA_real_,
    weighted_events = NA_real_,
    method = "blocked",
    status = "blocked_interval_not_estimated",
    limitation = reason,
    stringsAsFactors = FALSE
  )
}

performance_intervals <- function(model_id, frame, predicted, calibration_row) {
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
    return(list(rows = performance_interval_blocker_rows(model_id, n, events, reason), blocker = reason))
  }
  replicate_weights <- tryCatch(
    as.matrix(stats::weights(replicate_design, type = "analysis")),
    error = function(error) error
  )
  if (inherits(replicate_weights, "error") || !is.matrix(replicate_weights) || nrow(replicate_weights) != n) {
    reason <- "Bootstrap replicate weights were unavailable or did not align with the analysis frame."
    if (inherits(replicate_weights, "error")) {
      reason <- paste(reason, conditionMessage(replicate_weights))
    }
    return(list(rows = performance_interval_blocker_rows(model_id, n, events, reason), blocker = reason))
  }
  auroc_replicates <- apply(replicate_weights, 2, function(weight) weighted_auc(frame$admit, frame$.__predicted, weight))
  brier_replicates <- apply(replicate_weights, 2, function(weight) weighted_mean(frame$.__brier_error, weight))
  interval_row <- function(metric, estimate, values) {
    valid_values <- values[is.finite(values)]
    if (length(valid_values) < max(50L, floor(PERFORMANCE_INTERVAL_REPLICATES * 0.8))) {
      return(data.frame(
        model_id = model_id, dataset = DATASET, metric = metric, estimate = estimate,
        ci_low = NA_real_, ci_high = NA_real_, interval_level = INTERVAL_LEVEL,
        replicate_metric_sd = ifelse(length(valid_values) > 1, stats::sd(valid_values), NA_real_),
        bootstrap_replicates_requested = PERFORMANCE_INTERVAL_REPLICATES,
        bootstrap_replicates_used = length(valid_values), seed = SEED, n = n, events = events,
        weighted_n = weighted_n, weighted_events = weighted_events,
        method = "survey_bootstrap_replicate_weights_fixed_apparent_predictions",
        status = "blocked_insufficient_valid_replicates",
        limitation = "Fewer than 80% of requested bootstrap replicates produced a finite metric.",
        stringsAsFactors = FALSE
      ))
    }
    ci <- stats::quantile(valid_values, probs = c((1 - INTERVAL_LEVEL) / 2, 1 - (1 - INTERVAL_LEVEL) / 2), na.rm = TRUE, names = FALSE)
    data.frame(
      model_id = model_id,
      dataset = DATASET,
      metric = metric,
      estimate = estimate,
      ci_low = ci[[1]],
      ci_high = ci[[2]],
      interval_level = INTERVAL_LEVEL,
      replicate_metric_sd = stats::sd(valid_values),
      bootstrap_replicates_requested = PERFORMANCE_INTERVAL_REPLICATES,
      bootstrap_replicates_used = length(valid_values),
      seed = SEED,
      n = n,
      events = events,
      weighted_n = weighted_n,
      weighted_events = weighted_events,
      method = "survey_bootstrap_replicate_weights_fixed_apparent_predictions",
      status = "ok",
      limitation = paste(
        "Interval uses survey bootstrap replicate weights from pooled NHAMCS strata/PSUs and fixed predictions from the apparent active-model fit.",
        "It does not refit the model inside each replicate, correct optimism, provide external validation, or prove transportability."
      ),
      stringsAsFactors = FALSE
    )
  }
  rows <- rbind(
    interval_row("auroc", calibration_row$auroc[[1]], auroc_replicates),
    interval_row("brier_score", calibration_row$brier_score[[1]], brier_replicates)
  )
  blocker <- if (any(rows$status != "ok")) paste(unique(rows$limitation[rows$status != "ok"]), collapse = "; ") else ""
  list(rows = rows, blocker = blocker)
}

write_interval_blocker <- function(output_dir, blocker) {
  path <- file.path(output_dir, "e_dispo_v4_pain_severe_performance_interval_blocker.md")
  if (identical(blocker, "")) {
    if (file.exists(path)) unlink(path)
    return(invisible(NULL))
  }
  lines <- c(
    "# e-dispo-v4.0 Performance Interval Blocker",
    "",
    "AUROC and Brier interval estimates were not produced for at least one metric.",
    "",
    "## Blocker",
    paste0("- ", blocker),
    "",
    "No interval value should be inferred for blocked rows in `e_dispo_v4_pain_severe_performance_intervals.csv`.",
    ""
  )
  writeLines(lines, con = path)
}

survey_metric_summary <- function(frame, predicted, weight, status_prefix = "ok") {
  y <- frame$admit
  events <- sum(y == 1)
  non_events <- sum(y == 0)
  weighted_n <- sum(weight, na.rm = TRUE)
  weighted_events <- sum(weight[y == 1], na.rm = TRUE)
  if (nrow(frame) == 0 || events == 0 || non_events == 0 || weighted_n <= 0) {
    return(list(
      observed_prevalence = ifelse(weighted_n > 0, weighted_events / weighted_n, NA_real_),
      mean_predicted = NA_real_,
      calibration_gap = NA_real_,
      calibration_in_the_large = NA_real_,
      calibration_slope = NA_real_,
      brier_score = NA_real_,
      auroc = NA_real_,
      status = paste0(status_prefix, "_blocked_no_outcome_variation"),
      blocker = "Subgroup lacks both admission and discharge outcomes."
    ))
  }
  if (events < MIN_SUBGROUP_EVENTS || non_events < MIN_SUBGROUP_NONEVENTS) {
    return(list(
      observed_prevalence = weighted_mean(y, weight),
      mean_predicted = weighted_mean(predicted, weight),
      calibration_gap = weighted_mean(y, weight) - weighted_mean(predicted, weight),
      calibration_in_the_large = NA_real_,
      calibration_slope = NA_real_,
      brier_score = NA_real_,
      auroc = NA_real_,
      status = paste0(status_prefix, "_blocked_sparse_cells"),
      blocker = paste0("Subgroup has events=", events, " and non-events=", non_events,
        "; required at least ", MIN_SUBGROUP_EVENTS, " events and ", MIN_SUBGROUP_NONEVENTS, " non-events.")
    ))
  }
  metric_frame <- frame
  metric_frame$.__weight <- weight
  metric_frame$.__predicted <- predicted
  metric_frame$.__linear_prediction <- logit(predicted)
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~.__weight, nest = TRUE, data = metric_frame)
  calibration <- tryCatch({
    intercept_fit <- survey::svyglm(admit ~ 1 + offset(.__linear_prediction), design = design, family = quasibinomial())
    slope_fit <- survey::svyglm(admit ~ .__linear_prediction, design = design, family = quasibinomial())
    list(
      intercept = as.numeric(stats::coef(intercept_fit)[[1]]),
      slope = as.numeric(stats::coef(slope_fit)[[".__linear_prediction"]]),
      status = status_prefix,
      blocker = ""
    )
  }, error = function(error) {
    list(
      intercept = NA_real_,
      slope = NA_real_,
      status = paste0(status_prefix, "_partial_calibration_fit_blocked"),
      blocker = conditionMessage(error)
    )
  })
  observed <- weighted_mean(y, weight)
  mean_predicted <- weighted_mean(predicted, weight)
  list(
    observed_prevalence = observed,
    mean_predicted = mean_predicted,
    calibration_gap = observed - mean_predicted,
    calibration_in_the_large = calibration$intercept,
    calibration_slope = calibration$slope,
    brier_score = weighted_mean((predicted - y) ^ 2, weight),
    auroc = weighted_auc(y, predicted, weight),
    status = calibration$status,
    blocker = calibration$blocker
  )
}

availability_fields <- function(frame) {
  out <- frame
  out$.__pain_availability <- ifelse(out$pain_missing == 0 & !is.na(out$pain_bin3), "observed", "missing_or_unusable")
  out$.__hr_availability <- ifelse(!is.na(out$HR) & !is.na(out$tachycardia_burden), "observed", "missing_or_unusable")
  out$.__fever_temp_availability <- ifelse(!is.na(out$fever_or_temp), "observed", "missing_or_unusable")
  out$.__vomiting_proxy_availability <- ifelse(!is.na(out$vomiting_present), "observed", "missing_or_unusable")
  out
}

subgroup_row <- function(subgroup_name, subgroup_level, source_field, full_group, estimable_group, note) {
  predicted <- estimable_group$.__predicted
  metrics <- if (nrow(estimable_group) > 0) {
    survey_metric_summary(estimable_group, predicted, estimable_group$weight, status_prefix = "ok")
  } else {
    list(
      observed_prevalence = if (nrow(full_group) > 0) weighted_mean(full_group$admit, full_group$weight) else NA_real_,
      mean_predicted = NA_real_,
      calibration_gap = NA_real_,
      calibration_in_the_large = NA_real_,
      calibration_slope = NA_real_,
      brier_score = NA_real_,
      auroc = NA_real_,
      status = "blocked_not_estimable_by_active_model",
      blocker = "No rows in this group satisfy all active e-dispo-v4.0 complete-case requirements."
    )
  }
  data.frame(
    model_id = MODEL_ID,
    dataset = DATASET,
    subgroup = subgroup_name,
    level = subgroup_level,
    source_field = source_field,
    n = nrow(full_group),
    events = if (nrow(full_group) > 0) sum(full_group$admit == 1) else 0,
    non_events = if (nrow(full_group) > 0) sum(full_group$admit == 0) else 0,
    weighted_n = if (nrow(full_group) > 0) sum(full_group$weight) else 0,
    weighted_events = if (nrow(full_group) > 0) sum(full_group$weight[full_group$admit == 1]) else 0,
    model_estimable_n = nrow(estimable_group),
    model_estimable_events = if (nrow(estimable_group) > 0) sum(estimable_group$admit == 1) else 0,
    observed_prevalence = metrics$observed_prevalence,
    mean_predicted = metrics$mean_predicted,
    calibration_gap = metrics$calibration_gap,
    calibration_in_the_large = metrics$calibration_in_the_large,
    calibration_slope = metrics$calibration_slope,
    brier_score = metrics$brier_score,
    auroc = metrics$auroc,
    status = metrics$status,
    blocker = metrics$blocker,
    notes = paste(note, "N/events describe the full subgroup; prediction metrics describe model-estimable complete-case rows."),
    stringsAsFactors = FALSE
  )
}

missing_field_subgroup_row <- function(subgroup_name, source_field) {
  data.frame(
    model_id = MODEL_ID,
    dataset = DATASET,
    subgroup = subgroup_name,
    level = "blocked_field_missing",
    source_field = source_field,
    n = 0L,
    events = 0L,
    non_events = 0L,
    weighted_n = 0,
    weighted_events = 0,
    model_estimable_n = 0L,
    model_estimable_events = 0L,
    observed_prevalence = NA_real_,
    mean_predicted = NA_real_,
    calibration_gap = NA_real_,
    calibration_in_the_large = NA_real_,
    calibration_slope = NA_real_,
    brier_score = NA_real_,
    auroc = NA_real_,
    status = "blocked_field_missing_from_pooled_analytic_cohort",
    blocker = paste0(source_field, " is not present in analytic_cohort_nhamcs_2018_2022.csv."),
    notes = "Applicability subgroup must be added to cohort construction before performance can be estimated.",
    stringsAsFactors = FALSE
  )
}

subgroup_performance <- function(binary_frame, active_frame) {
  binary_with_availability <- availability_fields(binary_frame)
  active_with_availability <- availability_fields(active_frame)
  rows <- data.frame()

  if ("age_band" %in% names(active_with_availability)) {
    for (level in sort(unique(as.character(active_with_availability$age_band[!is.na(active_with_availability$age_band)])))) {
      full_group <- binary_with_availability[as.character(binary_with_availability$age_band) == level, , drop = FALSE]
      estimable_group <- active_with_availability[as.character(active_with_availability$age_band) == level, , drop = FALSE]
      rows <- rbind(rows, subgroup_row("age_band", level, "age_band", full_group, estimable_group,
        "Age-band subgroup on active-model complete-case rows."))
    }
  } else {
    rows <- rbind(rows, missing_field_subgroup_row("age_band", "age_band"))
  }

  for (item in list(
    list(name = "pain_availability", field = ".__pain_availability"),
    list(name = "HR_availability", field = ".__hr_availability"),
    list(name = "fever_temp_availability", field = ".__fever_temp_availability"),
    list(name = "vomiting_proxy_availability", field = ".__vomiting_proxy_availability")
  )) {
    values <- sort(unique(as.character(binary_with_availability[[item$field]])))
    for (level in values) {
      full_group <- binary_with_availability[as.character(binary_with_availability[[item$field]]) == level, , drop = FALSE]
      estimable_group <- active_with_availability[as.character(active_with_availability[[item$field]]) == level, , drop = FALSE]
      rows <- rbind(rows, subgroup_row(item$name, level, item$field, full_group, estimable_group,
        "Availability subgroup; missing or unusable active predictors block e-dispo-v4.0 estimation."))
    }
  }

  for (item in list(
    list(name = "race_ethnicity", field = "race_ethnicity"),
    list(name = "payer", field = "payer"),
    list(name = "region", field = "region"),
    list(name = "msa_status", field = "msa_status")
  )) {
    if (item$field %in% names(binary_with_availability)) {
      for (level in sort(unique(as.character(binary_with_availability[[item$field]][!is.na(binary_with_availability[[item$field]])])))) {
        full_group <- binary_with_availability[as.character(binary_with_availability[[item$field]]) == level, , drop = FALSE]
        estimable_group <- active_with_availability[as.character(active_with_availability[[item$field]]) == level, , drop = FALSE]
        rows <- rbind(rows, subgroup_row(item$name, level, item$field, full_group, estimable_group,
          "Applicability subgroup on active-model complete-case rows."))
      }
    } else {
      rows <- rbind(rows, missing_field_subgroup_row(item$name, item$field))
    }
  }
  rows
}

subgroup_calibration <- function(subgroup_rows, active_frame) {
  rows <- data.frame()
  supported <- subgroup_rows[subgroup_rows$model_estimable_n > 0 & subgroup_rows$status %in% c("ok", "ok_partial_calibration_fit_blocked"), , drop = FALSE]
  active_with_availability <- availability_fields(active_frame)
  for (index in seq_len(nrow(supported))) {
    item <- supported[index, ]
    field <- item$source_field[[1]]
    level <- item$level[[1]]
    if (!field %in% names(active_with_availability)) next
    group_frame <- active_with_availability[as.character(active_with_availability[[field]]) == level, , drop = FALSE]
    if (nrow(group_frame) == 0) next
    if (sum(group_frame$admit == 1) < MIN_SUBGROUP_EVENTS || sum(group_frame$admit == 0) < MIN_SUBGROUP_NONEVENTS) {
      rows <- rbind(rows, data.frame(
        model_id = MODEL_ID, dataset = DATASET, subgroup = item$subgroup, level = level,
        decile = NA_integer_, n = nrow(group_frame), events = sum(group_frame$admit == 1),
        weighted_n = sum(group_frame$weight), mean_predicted = NA_real_, observed_rate = NA_real_,
        observed_rate_ci_low = NA_real_, observed_rate_ci_high = NA_real_, calibration_gap = NA_real_,
        status = "blocked_sparse_cells", blocker = "Insufficient events/non-events for subgroup calibration deciles.",
        notes = "No decile rows emitted for sparse subgroup.", stringsAsFactors = FALSE))
      next
    }
    calibration_groups <- grouped_calibration(MODEL_ID, group_frame, group_frame$.__predicted)
    calibration_groups$subgroup <- item$subgroup
    calibration_groups$level <- level
    rows <- rbind(rows, data.frame(
      model_id = calibration_groups$model_id,
      dataset = calibration_groups$dataset,
      subgroup = calibration_groups$subgroup,
      level = calibration_groups$level,
      decile = calibration_groups$decile,
      n = calibration_groups$n,
      events = calibration_groups$events,
      weighted_n = calibration_groups$weighted_n,
      mean_predicted = calibration_groups$mean_predicted,
      observed_rate = calibration_groups$observed_rate,
      observed_rate_ci_low = calibration_groups$observed_rate_ci_low,
      observed_rate_ci_high = calibration_groups$observed_rate_ci_high,
      calibration_gap = calibration_groups$calibration_gap,
      status = calibration_groups$status,
      blocker = "",
      notes = "Weighted decile calibration within subgroup; apparent active-model predictions only.",
      stringsAsFactors = FALSE
    ))
  }
  blocked <- subgroup_rows[!(subgroup_rows$status %in% c("ok", "ok_partial_calibration_fit_blocked")) | subgroup_rows$model_estimable_n == 0, , drop = FALSE]
  if (nrow(blocked) > 0) {
    for (index in seq_len(nrow(blocked))) {
      item <- blocked[index, ]
      rows <- rbind(rows, data.frame(
        model_id = MODEL_ID, dataset = DATASET, subgroup = item$subgroup, level = item$level,
        decile = NA_integer_, n = item$n, events = item$events, weighted_n = item$weighted_n,
        mean_predicted = NA_real_, observed_rate = item$observed_prevalence,
        observed_rate_ci_low = NA_real_, observed_rate_ci_high = NA_real_, calibration_gap = NA_real_,
        status = item$status, blocker = item$blocker,
        notes = "Subgroup calibration blocked; see subgroup performance row.", stringsAsFactors = FALSE))
    }
  }
  rows
}

missingness_performance <- function(binary_frame, active_frame) {
  subgroup_rows <- subgroup_performance(binary_frame, active_frame)
  subgroup_rows[subgroup_rows$subgroup %in% c("pain_availability", "HR_availability", "fever_temp_availability", "vomiting_proxy_availability"), , drop = FALSE]
}

optimism_blocker_rows <- function(reason, apparent_metrics) {
  data.frame(
    model_id = MODEL_ID,
    dataset = DATASET,
    metric = c("auroc", "brier_score", "calibration_in_the_large", "calibration_slope"),
    apparent_estimate = c(apparent_metrics$auroc, apparent_metrics$brier_score,
      apparent_metrics$calibration_in_the_large, apparent_metrics$calibration_slope),
    mean_bootstrap_apparent = NA_real_,
    mean_bootstrap_test = NA_real_,
    mean_optimism = NA_real_,
    optimism_corrected_estimate = NA_real_,
    test_metric_p025 = NA_real_,
    test_metric_p975 = NA_real_,
    bootstrap_replicates_requested = OPTIMISM_BOOTSTRAP_REPLICATES,
    bootstrap_replicates_used = 0L,
    seed = SEED,
    method = "survey_bootstrap_refit_optimism_correction",
    status = "blocked_optimism_correction_not_estimated",
    blocker = reason,
    limitation = "Apparent fixed-prediction intervals remain the weaker available performance interval.",
    stringsAsFactors = FALSE
  )
}

optimism_corrected_performance <- function(frame, formula, apparent_metrics, output_dir) {
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = frame)
  set.seed(SEED)
  replicate_design <- tryCatch(
    survey::as.svrepdesign(design, type = "bootstrap", replicates = OPTIMISM_BOOTSTRAP_REPLICATES, mse = TRUE),
    error = function(error) error
  )
  if (inherits(replicate_design, "error")) {
    reason <- paste("survey::as.svrepdesign bootstrap failed:", conditionMessage(replicate_design))
    write_optimism_blocker(output_dir, reason)
    return(optimism_blocker_rows(reason, apparent_metrics))
  }
  replicate_weights <- tryCatch(as.matrix(stats::weights(replicate_design, type = "analysis")), error = function(error) error)
  if (inherits(replicate_weights, "error") || !is.matrix(replicate_weights) || nrow(replicate_weights) != nrow(frame)) {
    reason <- "Bootstrap replicate weights were unavailable or did not align with the analysis frame."
    if (inherits(replicate_weights, "error")) reason <- paste(reason, conditionMessage(replicate_weights))
    write_optimism_blocker(output_dir, reason)
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
    boot_metrics <- survey_metric_summary(rep_frame, boot_pred, rep_weight, status_prefix = "bootstrap_apparent")
    test_metrics <- survey_metric_summary(frame, test_pred, frame$weight, status_prefix = "bootstrap_test")
    metric_rows <- rbind(metric_rows, data.frame(
      replicate = replicate_index,
      metric = c("auroc", "brier_score", "calibration_in_the_large", "calibration_slope"),
      bootstrap_apparent = c(boot_metrics$auroc, boot_metrics$brier_score,
        boot_metrics$calibration_in_the_large, boot_metrics$calibration_slope),
      bootstrap_test = c(test_metrics$auroc, test_metrics$brier_score,
        test_metrics$calibration_in_the_large, test_metrics$calibration_slope),
      stringsAsFactors = FALSE
    ))
  }
  valid_replicates <- length(unique(metric_rows$replicate[is.finite(metric_rows$bootstrap_apparent) & is.finite(metric_rows$bootstrap_test)]))
  if (valid_replicates < MIN_OPTIMISM_VALID_REPLICATES) {
    reason <- paste0("Only ", valid_replicates, " valid bootstrap refits completed; required at least ", MIN_OPTIMISM_VALID_REPLICATES, ".")
    write_optimism_blocker(output_dir, reason)
    return(optimism_blocker_rows(reason, apparent_metrics))
  }
  if (file.exists(file.path(output_dir, "e_dispo_v4_optimism_corrected_performance_blocker.md"))) {
    unlink(file.path(output_dir, "e_dispo_v4_optimism_corrected_performance_blocker.md"))
  }
  apparent <- c(
    auroc = apparent_metrics$auroc,
    brier_score = apparent_metrics$brier_score,
    calibration_in_the_large = apparent_metrics$calibration_in_the_large,
    calibration_slope = apparent_metrics$calibration_slope
  )
  rows <- data.frame()
  for (metric in names(apparent)) {
    subset <- metric_rows[metric_rows$metric == metric & is.finite(metric_rows$bootstrap_apparent) & is.finite(metric_rows$bootstrap_test), , drop = FALSE]
    optimism <- subset$bootstrap_apparent - subset$bootstrap_test
    test_ci <- stats::quantile(subset$bootstrap_test, probs = c(0.025, 0.975), na.rm = TRUE, names = FALSE)
    rows <- rbind(rows, data.frame(
      model_id = MODEL_ID,
      dataset = DATASET,
      metric = metric,
      apparent_estimate = apparent[[metric]],
      mean_bootstrap_apparent = mean(subset$bootstrap_apparent),
      mean_bootstrap_test = mean(subset$bootstrap_test),
      mean_optimism = mean(optimism),
      optimism_corrected_estimate = apparent[[metric]] - mean(optimism),
      test_metric_p025 = test_ci[[1]],
      test_metric_p975 = test_ci[[2]],
      bootstrap_replicates_requested = OPTIMISM_BOOTSTRAP_REPLICATES,
      bootstrap_replicates_used = length(unique(subset$replicate)),
      seed = SEED,
      method = "survey_bootstrap_refit_optimism_correction",
      status = "ok",
      blocker = "",
      limitation = paste(
        "Bootstrap refits use pooled NHAMCS survey bootstrap replicate weights.",
        "This is internal optimism correction only and does not provide external validation or transportability."
      ),
      stringsAsFactors = FALSE
    ))
  }
  rows
}

write_optimism_blocker <- function(output_dir, reason) {
  writeLines(c(
    "# e-dispo-v4.0 Optimism-Corrected Performance Blocker",
    "",
    "Survey-bootstrap refit optimism correction was not produced.",
    "",
    "## Blocker",
    paste0("- ", reason),
    "",
    "Use `e_dispo_v4_pain_severe_performance_intervals.csv` as the current weaker fixed-prediction interval artifact.",
    ""
  ), con = file.path(output_dir, "e_dispo_v4_optimism_corrected_performance_blocker.md"))
}

transportability_track <- function(output_dir, coefficients) {
  mimic_path <- file.path(dirname(output_dir), "mimic", "analytic_cohort_mimic.csv")
  if (!file.exists(mimic_path)) {
    return(data.frame(
      model_id = MODEL_ID, source = "MIMIC_IV_ED", source_path = mimic_path,
      n = 0L, events = 0L, complete_case_n = 0L, complete_case_events = 0L,
      observed_prevalence = NA_real_, mean_predicted = NA_real_, calibration_gap = NA_real_,
      auroc = NA_real_, brier_score = NA_real_, calibration_in_the_large = NA_real_,
      calibration_slope = NA_real_, status = "blocked_source_cohort_missing",
      blocker = "MIMIC analytic cohort is missing; run scripts/mimic/build_cohort.py and fit_models.py first.",
      notes = "Transportability track only; no coefficient pooling or model promotion.", stringsAsFactors = FALSE))
  }
  mimic <- read.csv(mimic_path, stringsAsFactors = FALSE, na.strings = c("", "NA", "NaN"))
  required <- c("include_strict_binary", "admit", "age", "pain_bin3", "fever_or_temp", "vomiting", "HR")
  missing_required <- setdiff(required, names(mimic))
  if (length(missing_required) > 0) {
    return(data.frame(
      model_id = MODEL_ID, source = "MIMIC_IV_ED", source_path = mimic_path,
      n = 0L, events = 0L, complete_case_n = 0L, complete_case_events = 0L,
      observed_prevalence = NA_real_, mean_predicted = NA_real_, calibration_gap = NA_real_,
      auroc = NA_real_, brier_score = NA_real_, calibration_in_the_large = NA_real_,
      calibration_slope = NA_real_, status = "blocked_required_columns_missing",
      blocker = paste("Missing MIMIC columns:", paste(missing_required, collapse = ", ")),
      notes = "Transportability track only; no coefficient pooling or model promotion.", stringsAsFactors = FALSE))
  }
  binary_mimic <- mimic[truthy(mimic$include_strict_binary), , drop = FALSE]
  binary_mimic$admit <- as.numeric(binary_mimic$admit)
  binary_mimic$age <- as.numeric(binary_mimic$age)
  binary_mimic$fever_or_temp <- as.numeric(binary_mimic$fever_or_temp)
  binary_mimic$vomiting <- as.numeric(binary_mimic$vomiting)
  binary_mimic$HR <- as.numeric(binary_mimic$HR)
  binary_mimic$age_centered <- binary_mimic$age - AGE_CENTER
  binary_mimic$pain_severe <- as.numeric(as.character(binary_mimic$pain_bin3) == "severe")
  binary_mimic$tachycardia_burden <- pmax(binary_mimic$HR - 100, 0) / 10
  binary_mimic$weight <- 1
  binary_mimic$stratum <- factor("mimic_single_stratum")
  binary_mimic$psu <- factor(seq_len(nrow(binary_mimic)))
  complete_mimic <- binary_mimic[!is.na(binary_mimic$admit) & binary_mimic$admit %in% c(0, 1) &
    !is.na(binary_mimic$age_centered) & !is.na(binary_mimic$pain_severe) &
    !is.na(binary_mimic$fever_or_temp) & !is.na(binary_mimic$vomiting) &
    !is.na(binary_mimic$tachycardia_burden), , drop = FALSE]
  beta <- setNames(coefficients$beta[coefficients$model_id == MODEL_ID], coefficients$term[coefficients$model_id == MODEL_ID])
  predicted <- 1 / (1 + exp(-(beta[["intercept"]] + beta[["age_centered"]] * complete_mimic$age_centered +
    beta[["pain_severe"]] * complete_mimic$pain_severe + beta[["fever_or_temp"]] * complete_mimic$fever_or_temp +
    beta[["vomiting_present"]] * complete_mimic$vomiting + beta[["tachycardia_burden"]] * complete_mimic$tachycardia_burden)))
  metrics <- if (nrow(complete_mimic) > 0) survey_metric_summary(complete_mimic, predicted, complete_mimic$weight, status_prefix = "mimic_transport") else NULL
  sparse_blocker <- nrow(complete_mimic) < 100 || sum(complete_mimic$admit == 1) < 30 || sum(complete_mimic$admit == 0) < 30
  data.frame(
    model_id = MODEL_ID,
    source = "MIMIC_IV_ED",
    source_path = mimic_path,
    n = nrow(binary_mimic),
    events = sum(binary_mimic$admit == 1, na.rm = TRUE),
    complete_case_n = nrow(complete_mimic),
    complete_case_events = sum(complete_mimic$admit == 1, na.rm = TRUE),
    observed_prevalence = if (!is.null(metrics)) metrics$observed_prevalence else NA_real_,
    mean_predicted = if (!is.null(metrics)) metrics$mean_predicted else NA_real_,
    calibration_gap = if (!is.null(metrics)) metrics$calibration_gap else NA_real_,
    auroc = if (!is.null(metrics) && !sparse_blocker) metrics$auroc else NA_real_,
    brier_score = if (!is.null(metrics) && !sparse_blocker) metrics$brier_score else NA_real_,
    calibration_in_the_large = if (!is.null(metrics) && !sparse_blocker) metrics$calibration_in_the_large else NA_real_,
    calibration_slope = if (!is.null(metrics) && !sparse_blocker) metrics$calibration_slope else NA_real_,
    status = ifelse(sparse_blocker, "blocked_sparse_replication_only", "ok_transport_calibration_screen"),
    blocker = ifelse(sparse_blocker, "MIMIC complete-case transport sample is too small for validation; no transportability claim.", ""),
    notes = "NHAMCS coefficients applied to MIMIC-compatible fields for source-specific screen only; no coefficient pooling or model promotion.",
    stringsAsFactors = FALSE
  )
}

write_transportability_report <- function(output_dir, transportability_rows) {
  row <- transportability_rows[1, ]
  writeLines(c(
    "# e-dispo-v4.0 Source-Specific Transportability Track",
    "",
    "This report applies the active NHAMCS `e-dispo-v4.0` coefficient surface only as a source-specific screen when a MIMIC analytic cohort is available.",
    "",
    paste0("Status: `", row$status, "`."),
    paste0("Blocker: ", ifelse(row$blocker == "", "None for the screen; still no external-validation claim.", row$blocker)),
    "",
    "The result must not be described as external validation unless sample size, endpoint mapping, predictor harmonization, and calibration gates pass.",
    ""
  ), con = file.path(output_dir, "e_dispo_v4_transportability_report.md"))
}

candidate_refinement_gate <- function(output_dir) {
  rows <- data.frame(
    model_id = MODEL_ID,
    candidate = c("AAP-3", "SBP", "acuity", "hematemesis", "nausea_alone", "tachycardia_duration", "pain_representation"),
    available_source = c("NHAMCS_IMMEDR_or_MIMIC_triage_acuity", "NHAMCS_BPSYS_or_MIMIC_triage_SBP",
      "NHAMCS_IMMEDR_or_MIMIC_triage_acuity", "NHAMCS_RFV_proxy", "NHAMCS_RFV_proxy",
      "MIMIC_timestamped_vitals_only", "NHAMCS_pain_scale_and_MIMIC_triage_pain"),
    current_status = c("prototype_acuity_proxy", "excluded_candidate", "excluded_candidate",
      "sensitivity_only", "supporting_evidence_only", "unavailable_in_NHAMCS", "active_severe_binary_only"),
    promotion_status = c("blocked_no_row_level_AAP3_mapping", "blocked_prespecified_gate_required",
      "blocked_prespecified_gate_required", "blocked_sparse_or_sensitivity_only",
      "blocked_failed_candidate_screen", "blocked_requires_timestamp_preserving_MIMIC_extraction",
      "blocked_no_new_monotonicity_evidence"),
    next_action = c(
      "Prespecify AAP-3 answer-to-IMMEDR/MIMIC mapping before fitting any risk model with AAP-3.",
      "Run SBP candidate gate with cell counts, coefficient uncertainty, calibration, and leave-one-year-out checks.",
      "Run acuity candidate gate and keep separate from AAP-3 until construct mapping is reviewed.",
      "Keep hematemesis separate from ordinary vomiting; review existing sensitivity-only gate.",
      "Keep nausea out of e-dispo-v4.0; existing screen did not promote it.",
      "Use MIMIC vitalsign timestamps; NHAMCS has one PULSE value and cannot support duration.",
      "Keep severe-vs-non-severe pain unless a new pain report supports a replacement without monotonic overclaim."
    ),
    evidence_tier = "unsupported_or_supporting_only",
    stringsAsFactors = FALSE
  )
  writeLines(c(
    "# e-dispo-v4.0 Candidate Refinement Gate",
    "",
    "No candidate predictor is promoted by this artifact pass.",
    "AAP-3, SBP, acuity, hematemesis, nausea, tachycardia duration, and alternative pain representations remain blocked or supporting-only until their prespecified gates pass.",
    ""
  ), con = file.path(output_dir, "e_dispo_v4_candidate_refinement_report.md"))
  rows
}

parse_coefficient <- function(name) {
  if (identical(name, "(Intercept)")) return(list(term = "intercept", level = ""))
  if (identical(name, "age_centered")) return(list(term = "age_centered", level = "per_1_year_centered_at_42"))
  if (identical(name, "pain_severe")) return(list(term = "pain_severe", level = "1"))
  if (startsWith(name, "pain_bin3")) return(list(term = "pain_bin3", level = substring(name, nchar("pain_bin3") + 1)))
  if (identical(name, "fever_or_temp")) return(list(term = "fever_or_temp", level = "1"))
  if (identical(name, "vomiting_present")) return(list(term = "vomiting_present", level = "1"))
  if (identical(name, "tachycardia_burden")) return(list(term = "tachycardia_burden", level = "per_10_bpm_over_100"))
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
    evidence_tier = "dataset_derived",
    limitation_note = "e-dispo-v4.0 severe-only pain refit; educational use only, not clinical decision support.",
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
    observed_prevalence = weighted_mean(frame$admit, frame$weight),
    mean_predicted = weighted_mean(predicted, frame$weight),
    calibration_in_the_large = as.numeric(stats::coef(intercept_fit)[[1]]),
    calibration_slope = as.numeric(stats::coef(slope_fit)[[".__linear_prediction"]]),
    brier_score = weighted_mean((predicted - frame$admit) ^ 2, frame$weight),
    auroc = weighted_auc(frame$admit, predicted, frame$weight),
    stringsAsFactors = FALSE
  )

  list(
    fit = fit,
    model_frame = frame,
    predicted = predicted,
    coefficients = coefficients,
    covariance = covariance_rows,
    draws = mvn_draws(model_id, beta, covariance, parsed_terms),
    calibration = calibration
  )
}

predict_heldout <- function(model_id, formula, train, test) {
  design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = train)
  fit <- survey::svyglm(formula, design = design, family = quasibinomial())
  predicted <- as.numeric(stats::predict(fit, newdata = test, type = "response"))
  data.frame(
    heldout_year = unique(test$year)[[1]],
    model_id = model_id,
    dataset = DATASET,
    heldout_n = nrow(test),
    heldout_events = sum(test$admit == 1),
    brier_score = weighted_mean((predicted - test$admit) ^ 2, test$weight),
    auroc = weighted_auc(test$admit, predicted, test$weight),
    observed_prevalence = weighted_mean(test$admit, test$weight),
    mean_predicted = weighted_mean(predicted, test$weight),
    stringsAsFactors = FALSE
  )
}

cohort_year_suffix <- function(path) {
  name <- basename(path)
  suffix <- sub("^analytic_cohort_nhamcs_", "", name)
  sub("\\.csv$", "", suffix)
}

full_source_scope_path <- function(scope_name) {
  file.path(dirname(input_path), paste0(scope_name, "_cohort_nhamcs_", cohort_year_suffix(input_path), ".csv"))
}

screen_definition <- function(screen_name) {
  if (identical(screen_name, "full_source_endpoint")) {
    return("Endpoint-only full ED screen: strict admit-vs-routine-home-discharge endpoint exclusions only; no age, sex, abdominal-pain, or trauma filter.")
  }
  if (identical(screen_name, "full_source_nontrauma")) {
    return("Non-trauma full ED sensitivity screen: strict endpoint exclusions plus non-trauma restriction; no age, sex, or abdominal-pain filter.")
  }
  "Full-source scope screen."
}

prepare_screen_binary <- function(cohort) {
  required <- c("include_strict_binary", "admit", "year", "age", "pain_bin3", "pain_missing",
                "fever_or_temp", "vomiting_present", "HR", "tachycardia_burden",
                "pooled_weight", "pooled_stratum", "pooled_psu")
  missing_required <- setdiff(required, names(cohort))
  if (length(missing_required) > 0) {
    stop(paste("Missing required full-source screen columns:", paste(missing_required, collapse = ", ")))
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
  binary <- binary[!is.na(binary$admit) & binary$admit %in% c(0, 1) &
    !is.na(binary$year) & !is.na(binary$age_centered) &
    !is.na(binary$weight) & binary$weight > 0 &
    !is.na(binary$stratum) & !is.na(binary$psu), , drop = FALSE]
  binary
}

screen_complete_case <- function(binary) {
  complete <- binary[binary$pain_missing == 0 &
    !is.na(binary$pain_bin3) & !is.na(binary$fever_or_temp) &
    !is.na(binary$vomiting_present) & !is.na(binary$HR) &
    !is.na(binary$tachycardia_burden), , drop = FALSE]
  complete$pain_severe <- as.numeric(as.character(complete$pain_bin3) == "severe")
  complete
}

fixed_active_prediction <- function(frame, beta) {
  eta <- beta[["intercept"]] +
    beta[["age_centered"]] * frame$age_centered +
    beta[["pain_severe"]] * frame$pain_severe +
    beta[["fever_or_temp"]] * frame$fever_or_temp +
    beta[["vomiting_present"]] * frame$vomiting_present +
    beta[["tachycardia_burden"]] * frame$tachycardia_burden
  1 / (1 + exp(-eta))
}

screen_level_values <- function(frame, field) {
  values <- as.character(frame[[field]])
  values[is.na(values)] <- "missing"
  sort(unique(values))
}

screen_subset <- function(frame, field, level) {
  values <- as.character(frame[[field]])
  values[is.na(values)] <- "missing"
  frame[values == level, , drop = FALSE]
}

screen_performance_blocker_row <- function(screen_name, source_path, reason) {
  data.frame(
    model_id = MODEL_ID, dataset = DATASET, screen = screen_name,
    cohort_definition = screen_definition(screen_name), subgroup = "overall",
    level = "blocked", source_field = "", n = 0L, events = 0L, non_events = 0L,
    weighted_n = 0, weighted_events = 0, model_estimable_n = 0L,
    model_estimable_events = 0L, observed_prevalence = NA_real_,
    mean_predicted = NA_real_, calibration_gap = NA_real_,
    calibration_in_the_large = NA_real_, calibration_slope = NA_real_,
    brier_score = NA_real_, auroc = NA_real_, status = "blocked_source_screen_not_run",
    blocker = paste(reason, source_path), notes = "No full-source screen estimate should be inferred from this blocker row.",
    stringsAsFactors = FALSE
  )
}

screen_performance_row <- function(screen_name, subgroup_name, subgroup_level, source_field, full_group, estimable_group, note) {
  metrics <- if (nrow(estimable_group) > 0) {
    survey_metric_summary(estimable_group, estimable_group$.__predicted, estimable_group$weight, status_prefix = "source_screen")
  } else {
    list(
      observed_prevalence = if (nrow(full_group) > 0) weighted_mean(full_group$admit, full_group$weight) else NA_real_,
      mean_predicted = NA_real_, calibration_gap = NA_real_, calibration_in_the_large = NA_real_,
      calibration_slope = NA_real_, brier_score = NA_real_, auroc = NA_real_,
      status = "blocked_not_estimable_by_active_model",
      blocker = "No strict-binary rows in this slice satisfy all active e-dispo-v4.0 complete-case requirements."
    )
  }
  data.frame(
    model_id = MODEL_ID,
    dataset = DATASET,
    screen = screen_name,
    cohort_definition = screen_definition(screen_name),
    subgroup = subgroup_name,
    level = subgroup_level,
    source_field = source_field,
    n = nrow(full_group),
    events = if (nrow(full_group) > 0) sum(full_group$admit == 1) else 0,
    non_events = if (nrow(full_group) > 0) sum(full_group$admit == 0) else 0,
    weighted_n = if (nrow(full_group) > 0) sum(full_group$weight) else 0,
    weighted_events = if (nrow(full_group) > 0) sum(full_group$weight[full_group$admit == 1]) else 0,
    model_estimable_n = nrow(estimable_group),
    model_estimable_events = if (nrow(estimable_group) > 0) sum(estimable_group$admit == 1) else 0,
    observed_prevalence = metrics$observed_prevalence,
    mean_predicted = metrics$mean_predicted,
    calibration_gap = metrics$calibration_gap,
    calibration_in_the_large = metrics$calibration_in_the_large,
    calibration_slope = metrics$calibration_slope,
    brier_score = metrics$brier_score,
    auroc = metrics$auroc,
    status = metrics$status,
    blocker = metrics$blocker,
    notes = paste(
      note,
      "Fixed active e-dispo-v4.0 coefficients are applied without refitting or promotion.",
      "This is an out-of-scope NHAMCS source screen, not external validation or transportability evidence."
    ),
    stringsAsFactors = FALSE
  )
}

screen_performance_rows <- function(screen_name, binary, complete) {
  binary_with_availability <- availability_fields(binary)
  complete_with_availability <- availability_fields(complete)
  rows <- screen_performance_row(
    screen_name, "overall", "all_strict_binary", "", binary_with_availability, complete_with_availability,
    "Overall strict-binary source-scope screen."
  )
  for (item in list(
    list(name = "active_scope_membership", field = "in_active_scope"),
    list(name = "adult_male_18_64_scope", field = "adult_male_18_64_flag"),
    list(name = "age_band_full", field = "age_band_full"),
    list(name = "sex", field = "sex"),
    list(name = "abdominal_pain_flag", field = "abdominal_pain_flag"),
    list(name = "non_trauma_flag", field = "non_trauma_flag"),
    list(name = "pain_availability", field = ".__pain_availability"),
    list(name = "HR_availability", field = ".__hr_availability"),
    list(name = "fever_temp_availability", field = ".__fever_temp_availability"),
    list(name = "vomiting_proxy_availability", field = ".__vomiting_proxy_availability")
  )) {
    if (!item$field %in% names(binary_with_availability)) next
    for (level in screen_level_values(binary_with_availability, item$field)) {
      full_group <- screen_subset(binary_with_availability, item$field, level)
      estimable_group <- screen_subset(complete_with_availability, item$field, level)
      rows <- rbind(rows, screen_performance_row(
        screen_name, item$name, level, item$field, full_group, estimable_group,
        "Scope or predictor-availability slice."
      ))
    }
  }
  rows
}

screen_calibration_blocker_row <- function(screen_name, source_path, reason) {
  data.frame(
    model_id = MODEL_ID, dataset = DATASET, screen = screen_name,
    subgroup = "overall", level = "blocked", decile = NA_integer_,
    n = 0L, events = 0L, weighted_n = 0, mean_predicted = NA_real_,
    observed_rate = NA_real_, observed_rate_ci_low = NA_real_,
    observed_rate_ci_high = NA_real_, calibration_gap = NA_real_,
    status = "blocked_source_screen_not_run", blocker = paste(reason, source_path),
    notes = "No full-source grouped calibration should be inferred from this blocker row.",
    stringsAsFactors = FALSE
  )
}

screen_calibration_rows <- function(screen_name, performance_rows, complete) {
  rows <- data.frame()
  complete_with_availability <- availability_fields(complete)
  supported <- performance_rows[
    performance_rows$model_estimable_n > 0 &
      performance_rows$status %in% c("source_screen", "source_screen_partial_calibration_fit_blocked"),
    , drop = FALSE
  ]
  for (index in seq_len(nrow(supported))) {
    item <- supported[index, ]
    if (identical(item$subgroup[[1]], "overall")) {
      group_frame <- complete_with_availability
    } else {
      field <- item$source_field[[1]]
      if (!field %in% names(complete_with_availability)) next
      group_frame <- screen_subset(complete_with_availability, field, item$level[[1]])
    }
    if (nrow(group_frame) == 0) next
    if (sum(group_frame$admit == 1) < MIN_SUBGROUP_EVENTS || sum(group_frame$admit == 0) < MIN_SUBGROUP_NONEVENTS) {
      rows <- rbind(rows, data.frame(
        model_id = MODEL_ID, dataset = DATASET, screen = screen_name,
        subgroup = item$subgroup, level = item$level, decile = NA_integer_,
        n = nrow(group_frame), events = sum(group_frame$admit == 1), weighted_n = sum(group_frame$weight),
        mean_predicted = NA_real_, observed_rate = NA_real_, observed_rate_ci_low = NA_real_,
        observed_rate_ci_high = NA_real_, calibration_gap = NA_real_,
        status = "blocked_sparse_cells", blocker = "Insufficient events/non-events for grouped calibration.",
        notes = "No decile rows emitted for this sparse full-source screen slice.", stringsAsFactors = FALSE))
      next
    }
    calibration_groups <- grouped_calibration(MODEL_ID, group_frame, group_frame$.__predicted)
    rows <- rbind(rows, data.frame(
      model_id = calibration_groups$model_id,
      dataset = calibration_groups$dataset,
      screen = screen_name,
      subgroup = item$subgroup,
      level = item$level,
      decile = calibration_groups$decile,
      n = calibration_groups$n,
      events = calibration_groups$events,
      weighted_n = calibration_groups$weighted_n,
      mean_predicted = calibration_groups$mean_predicted,
      observed_rate = calibration_groups$observed_rate,
      observed_rate_ci_low = calibration_groups$observed_rate_ci_low,
      observed_rate_ci_high = calibration_groups$observed_rate_ci_high,
      calibration_gap = calibration_groups$calibration_gap,
      status = calibration_groups$status,
      blocker = "",
      notes = "Weighted decile calibration for fixed active-model predictions in the full-source source-scope screen.",
      stringsAsFactors = FALSE
    ))
  }
  blocked <- performance_rows[
    !(performance_rows$status %in% c("source_screen", "source_screen_partial_calibration_fit_blocked")) |
      performance_rows$model_estimable_n == 0,
    , drop = FALSE
  ]
  if (nrow(blocked) > 0) {
    for (index in seq_len(nrow(blocked))) {
      item <- blocked[index, ]
      rows <- rbind(rows, data.frame(
        model_id = MODEL_ID, dataset = DATASET, screen = screen_name,
        subgroup = item$subgroup, level = item$level, decile = NA_integer_,
        n = item$n, events = item$events, weighted_n = item$weighted_n,
        mean_predicted = NA_real_, observed_rate = item$observed_prevalence,
        observed_rate_ci_low = NA_real_, observed_rate_ci_high = NA_real_,
        calibration_gap = NA_real_, status = item$status, blocker = item$blocker,
        notes = "Full-source grouped calibration blocked; see performance row.", stringsAsFactors = FALSE))
    }
  }
  rows
}

screen_missingness_rows <- function(screen_name, performance_rows) {
  performance_rows[
    performance_rows$subgroup %in% c("pain_availability", "HR_availability", "fever_temp_availability", "vomiting_proxy_availability"),
    , drop = FALSE
  ]
}

full_source_screen <- function(screen_name, beta) {
  path <- full_source_scope_path(screen_name)
  if (!file.exists(path)) {
    reason <- "Full-source scope cohort file is missing:"
    return(list(
      performance = screen_performance_blocker_row(screen_name, path, reason),
      calibration = screen_calibration_blocker_row(screen_name, path, reason),
      missingness = screen_performance_blocker_row(screen_name, path, reason)
    ))
  }
  cohort <- read.csv(path, stringsAsFactors = FALSE, na.strings = c("", "NA", "NaN"))
  binary <- prepare_screen_binary(cohort)
  complete <- screen_complete_case(binary)
  if (nrow(complete) > 0) {
    complete$.__predicted <- fixed_active_prediction(complete, beta)
  } else {
    complete$.__predicted <- numeric()
  }
  performance <- screen_performance_rows(screen_name, binary, complete)
  calibration <- screen_calibration_rows(screen_name, performance, complete)
  missingness <- screen_missingness_rows(screen_name, performance)
  list(performance = performance, calibration = calibration, missingness = missingness)
}

write_full_source_scope_screen_report <- function(output_dir, endpoint_rows, nontrauma_rows) {
  endpoint_overall <- endpoint_rows[endpoint_rows$subgroup == "overall", , drop = FALSE][1, ]
  nontrauma_overall <- nontrauma_rows[nontrauma_rows$subgroup == "overall", , drop = FALSE][1, ]
  value_or_blank <- function(value, digits = 6) {
    if (length(value) == 0 || is.na(value) || !is.finite(as.numeric(value))) return("")
    format(round(as.numeric(value), digits), nsmall = digits, trim = TRUE)
  }
  lines <- c(
    "# e-dispo-v4.0 Full-Source NHAMCS Scope Screen",
    "",
    "This artifact scores the fixed active `e-dispo-v4.0` coefficient surface on broader NHAMCS strict-binary endpoint cohorts.",
    "It is an out-of-scope source/generalization screen only. It is not external validation, transportability evidence, clinical decision support, triage software, diagnosis, treatment advice, or a model update.",
    "",
    "## Method",
    "",
    "- Coefficients: fixed active `e-dispo-v4.0` surface fit on adult male age 18-64 non-traumatic abdominal-pain NHAMCS records.",
    "- Endpoint: same strict admit-vs-routine-home-discharge endpoint exclusions used by the active model.",
    "- Scoring: no refit; predictions require observed age, pain severe/non-severe, fever/temp proxy, vomiting proxy, and observed HR/tachycardia burden.",
    "- Metrics: survey-weighted AUROC, Brier score, calibration-in-the-large, calibration slope, calibration gap, and grouped calibration where event support is adequate.",
    "- Blockers: sparse cells, no outcome variation, missing source cohorts, or no complete-case rows are written as explicit status rows.",
    "",
    "## Overall Screen Results",
    "",
    "| Screen | Strict-binary N | Events | Model-estimable N | AUROC | Brier | Status |",
    "|---|---:|---:|---:|---:|---:|---|",
    paste0("| Endpoint-only full ED | ", endpoint_overall$n, " | ", endpoint_overall$events, " | ",
      endpoint_overall$model_estimable_n, " | ", value_or_blank(endpoint_overall$auroc), " | ",
      value_or_blank(endpoint_overall$brier_score), " | `", endpoint_overall$status, "` |"),
    paste0("| Non-trauma sensitivity | ", nontrauma_overall$n, " | ", nontrauma_overall$events, " | ",
      nontrauma_overall$model_estimable_n, " | ", value_or_blank(nontrauma_overall$auroc), " | ",
      value_or_blank(nontrauma_overall$brier_score), " | `", nontrauma_overall$status, "` |"),
    "",
    "## Outputs",
    "",
    "- `e_dispo_v4_full_source_endpoint_screen_performance.csv`",
    "- `e_dispo_v4_full_source_endpoint_screen_calibration.csv`",
    "- `e_dispo_v4_full_source_endpoint_screen_missingness.csv`",
    "- `e_dispo_v4_full_source_nontrauma_screen_performance.csv`",
    "- `e_dispo_v4_full_source_nontrauma_screen_calibration.csv`",
    "- `e_dispo_v4_full_source_nontrauma_screen_missingness.csv`",
    "",
    "## Limitation",
    "",
    "Rows outside the active adult male non-traumatic abdominal-pain scope are scored by extrapolation from the active educational model. These rows are useful for stress-testing scope dependence, not for broad applicability claims.",
    ""
  )
  writeLines(lines, con = file.path(output_dir, "e_dispo_v4_full_source_scope_screen_report.md"))
}

cohort <- read.csv(input_path, stringsAsFactors = FALSE, na.strings = c("", "NA", "NaN"))
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

binary <- binary[!is.na(binary$admit) & binary$admit %in% c(0, 1) &
  !is.na(binary$year) & !is.na(binary$age_centered) &
  !is.na(binary$weight) & binary$weight > 0 &
  !is.na(binary$stratum) & !is.na(binary$psu), , drop = FALSE]

complete_case <- binary[binary$pain_missing == 0 &
  !is.na(binary$pain_bin3) & !is.na(binary$fever_or_temp) &
  !is.na(binary$vomiting_present) & !is.na(binary$HR) &
  !is.na(binary$tachycardia_burden), , drop = FALSE]
complete_case$pain_bin3 <- stats::relevel(as.factor(complete_case$pain_bin3), ref = "moderate")
complete_case$pain_severe <- as.numeric(as.character(complete_case$pain_bin3) == "severe")

specs <- list(
  list(model_id = "e_dispo_v4_no_pain_comparator", formula = admit ~ age_centered + fever_or_temp + vomiting_present + tachycardia_burden),
  list(model_id = MODEL_ID, formula = admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden),
  list(model_id = "e_dispo_v4_current_flexible_pain_comparator", formula = admit ~ age_centered + pain_bin3 + fever_or_temp + vomiting_present + tachycardia_burden)
)

fits <- lapply(specs, function(spec) fit_model(spec$model_id, spec$formula, complete_case))
coefficients <- do.call(rbind, lapply(fits, function(item) item$coefficients))
covariance <- do.call(rbind, lapply(fits, function(item) item$covariance))
calibration <- do.call(rbind, lapply(fits, function(item) item$calibration))
draws <- fits[[2]]$draws
active_fit <- fits[[which(vapply(specs, function(spec) identical(spec$model_id, MODEL_ID), logical(1)))]]
active_calibration <- active_fit$calibration[1, , drop = FALSE]
active_analysis <- active_fit$model_frame
active_analysis$.__predicted <- active_fit$predicted
active_coefficients <- active_fit$coefficients
active_beta <- setNames(active_coefficients$beta, active_coefficients$term)
calibration_by_decile <- grouped_calibration(MODEL_ID, active_fit$model_frame, active_fit$predicted)
calibration_plot <- calibration_plot_data(calibration_by_decile)
interval_result <- performance_intervals(MODEL_ID, active_fit$model_frame, active_fit$predicted, active_calibration)
performance_interval_rows <- interval_result$rows
write_interval_blocker(output_dir, interval_result$blocker)
subgroup_performance_rows <- subgroup_performance(binary, active_analysis)
subgroup_calibration_rows <- subgroup_calibration(subgroup_performance_rows, active_analysis)
missingness_performance_rows <- missingness_performance(binary, active_analysis)
apparent_metric_list <- list(
  auroc = active_calibration$auroc[[1]],
  brier_score = active_calibration$brier_score[[1]],
  calibration_in_the_large = active_calibration$calibration_in_the_large[[1]],
  calibration_slope = active_calibration$calibration_slope[[1]]
)
optimism_corrected_rows <- optimism_corrected_performance(active_fit$model_frame, admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden, apparent_metric_list, output_dir)
transportability_rows <- transportability_track(output_dir, coefficients)
write_transportability_report(output_dir, transportability_rows)
candidate_refinement_rows <- candidate_refinement_gate(output_dir)
full_source_endpoint_screen <- full_source_screen("full_source_endpoint", active_beta)
full_source_nontrauma_screen <- full_source_screen("full_source_nontrauma", active_beta)
write_full_source_scope_screen_report(
  output_dir,
  full_source_endpoint_screen$performance,
  full_source_nontrauma_screen$performance
)

cell_counts <- data.frame()
for (level in c("non_severe", "severe", "mild", "moderate")) {
  subset <- if (identical(level, "non_severe")) {
    as.character(complete_case$pain_bin3) != "severe"
  } else {
    as.character(complete_case$pain_bin3) == level
  }
  part <- complete_case[subset, , drop = FALSE]
  cell_counts <- rbind(cell_counts, data.frame(
    dataset = DATASET,
    model_id = MODEL_ID,
    group = "pain_severe",
    level = level,
    n = nrow(part),
    events = sum(part$admit == 1),
    non_events = sum(part$admit == 0),
    weighted_n = sum(part$weight),
    weighted_events = sum(part$weight[part$admit == 1]),
    weighted_admit_rate = weighted_mean(part$admit, part$weight),
    stringsAsFactors = FALSE
  ))
}

leave_one_year_out <- data.frame()
for (heldout_year in sort(unique(complete_case$year))) {
  train <- complete_case[complete_case$year != heldout_year, , drop = FALSE]
  test <- complete_case[complete_case$year == heldout_year, , drop = FALSE]
  for (spec in specs) {
    leave_one_year_out <- rbind(leave_one_year_out, predict_heldout(spec$model_id, spec$formula, train, test))
  }
}

term_test <- survey::regTermTest(fits[[2]]$fit, ~ pain_severe)
decision_lines <- c(
  "# e-dispo-v4.0 Severe Pain Validation",
  "",
  paste0("Model ID: `", MODEL_ID, "`"),
  "Formula: `admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden`",
  "Transform: `pain_severe = 1[pain_bin3 == severe]`; mild and moderate are collapsed as non-severe.",
  "This is not a monotonic pain dose-response claim.",
  "",
  "## Decision",
  "The severe-only pain model is eligible for educational activation because it preserves apparent discrimination, slightly improves Brier score versus flexible pain, and has a positive adjusted severe-pain coefficient on the same complete-case cohort.",
  "",
  "## Term Test",
  paste0("Wald F=", round(term_test$Ftest, 6), ", df=", term_test$df, ", ddf=", term_test$ddf, ", p=", signif(term_test$p, 6)),
  "",
  "## Required Outputs",
  "- e_dispo_v4_pain_severe_coefficients.csv",
  "- e_dispo_v4_pain_severe_covariance.csv",
  "- e_dispo_v4_pain_severe_draws.csv",
  "- e_dispo_v4_pain_severe_calibration.csv",
  "- e_dispo_v4_pain_severe_calibration_by_decile.csv",
  "- e_dispo_v4_pain_severe_calibration_plot_data.csv",
  "- e_dispo_v4_pain_severe_performance_intervals.csv",
  "- e_dispo_v4_subgroup_performance.csv",
  "- e_dispo_v4_subgroup_calibration.csv",
  "- e_dispo_v4_missingness_performance.csv",
  "- e_dispo_v4_optimism_corrected_performance.csv",
  "- e_dispo_v4_transportability_track.csv",
  "- e_dispo_v4_candidate_refinement_gate.csv",
  "- e_dispo_v4_full_source_endpoint_screen_performance.csv",
  "- e_dispo_v4_full_source_endpoint_screen_calibration.csv",
  "- e_dispo_v4_full_source_endpoint_screen_missingness.csv",
  "- e_dispo_v4_full_source_nontrauma_screen_performance.csv",
  "- e_dispo_v4_full_source_nontrauma_screen_calibration.csv",
  "- e_dispo_v4_full_source_nontrauma_screen_missingness.csv",
  "- e_dispo_v4_full_source_scope_screen_report.md",
  "- e_dispo_v4_pain_severe_cell_counts.csv",
  "- e_dispo_v4_pain_severe_leave_one_year_out.csv",
  "",
  "## Reviewer-Facing Calibration And Performance Interval Pass",
  "Grouped calibration is written as survey-weighted predicted-probability deciles for the active model.",
  paste0("Performance intervals use ", PERFORMANCE_INTERVAL_REPLICATES, " survey bootstrap replicate weights from pooled NHAMCS strata/PSUs with fixed apparent predictions from the active model fit."),
  "These intervals do not refit the model inside each replicate, do not correct optimism, do not provide external validation, and do not prove transportability.",
  "Subgroup and missingness rows are written for supported fields; race/ethnicity, payer, region, and MSA are read from the pooled cohort when present, otherwise explicit blocker rows are emitted.",
  paste0("Optimism correction uses ", OPTIMISM_BOOTSTRAP_REPLICATES, " survey-bootstrap refits when enough replicates converge."),
  "MIMIC transportability and candidate-refinement outputs are screens/blockers only and do not promote any coefficient.",
  "Full-source NHAMCS endpoint-only and non-trauma screens apply fixed active coefficients to broader strict-binary cohorts without refitting; these are source-scope stress tests only.",
  "",
  "## Performance Interval Status",
  paste0("- AUROC interval status: `", performance_interval_rows$status[performance_interval_rows$metric == "auroc"][[1]], "`."),
  paste0("- Brier interval status: `", performance_interval_rows$status[performance_interval_rows$metric == "brier_score"][[1]], "`."),
  paste0("- Optimism-corrected performance status: `", paste(unique(optimism_corrected_rows$status), collapse = "; "), "`."),
  paste0("- Transportability track status: `", transportability_rows$status[[1]], "`."),
  paste0("- Full-source endpoint screen status: `", paste(unique(full_source_endpoint_screen$performance$status), collapse = "; "), "`."),
  paste0("- Full-source non-trauma screen status: `", paste(unique(full_source_nontrauma_screen$performance$status), collapse = "; "), "`.")
)

utils::write.csv(coefficients, file.path(output_dir, "e_dispo_v4_pain_severe_coefficients.csv"), row.names = FALSE, na = "")
utils::write.csv(covariance, file.path(output_dir, "e_dispo_v4_pain_severe_covariance.csv"), row.names = FALSE, na = "")
utils::write.csv(draws, file.path(output_dir, "e_dispo_v4_pain_severe_draws.csv"), row.names = FALSE, na = "")
utils::write.csv(calibration, file.path(output_dir, "e_dispo_v4_pain_severe_calibration.csv"), row.names = FALSE, na = "")
utils::write.csv(calibration_by_decile, file.path(output_dir, "e_dispo_v4_pain_severe_calibration_by_decile.csv"), row.names = FALSE, na = "")
utils::write.csv(calibration_plot, file.path(output_dir, "e_dispo_v4_pain_severe_calibration_plot_data.csv"), row.names = FALSE, na = "")
utils::write.csv(performance_interval_rows, file.path(output_dir, "e_dispo_v4_pain_severe_performance_intervals.csv"), row.names = FALSE, na = "")
utils::write.csv(subgroup_performance_rows, file.path(output_dir, "e_dispo_v4_subgroup_performance.csv"), row.names = FALSE, na = "")
utils::write.csv(subgroup_calibration_rows, file.path(output_dir, "e_dispo_v4_subgroup_calibration.csv"), row.names = FALSE, na = "")
utils::write.csv(missingness_performance_rows, file.path(output_dir, "e_dispo_v4_missingness_performance.csv"), row.names = FALSE, na = "")
utils::write.csv(optimism_corrected_rows, file.path(output_dir, "e_dispo_v4_optimism_corrected_performance.csv"), row.names = FALSE, na = "")
utils::write.csv(transportability_rows, file.path(output_dir, "e_dispo_v4_transportability_track.csv"), row.names = FALSE, na = "")
utils::write.csv(candidate_refinement_rows, file.path(output_dir, "e_dispo_v4_candidate_refinement_gate.csv"), row.names = FALSE, na = "")
utils::write.csv(full_source_endpoint_screen$performance, file.path(output_dir, "e_dispo_v4_full_source_endpoint_screen_performance.csv"), row.names = FALSE, na = "")
utils::write.csv(full_source_endpoint_screen$calibration, file.path(output_dir, "e_dispo_v4_full_source_endpoint_screen_calibration.csv"), row.names = FALSE, na = "")
utils::write.csv(full_source_endpoint_screen$missingness, file.path(output_dir, "e_dispo_v4_full_source_endpoint_screen_missingness.csv"), row.names = FALSE, na = "")
utils::write.csv(full_source_nontrauma_screen$performance, file.path(output_dir, "e_dispo_v4_full_source_nontrauma_screen_performance.csv"), row.names = FALSE, na = "")
utils::write.csv(full_source_nontrauma_screen$calibration, file.path(output_dir, "e_dispo_v4_full_source_nontrauma_screen_calibration.csv"), row.names = FALSE, na = "")
utils::write.csv(full_source_nontrauma_screen$missingness, file.path(output_dir, "e_dispo_v4_full_source_nontrauma_screen_missingness.csv"), row.names = FALSE, na = "")
utils::write.csv(cell_counts, file.path(output_dir, "e_dispo_v4_pain_severe_cell_counts.csv"), row.names = FALSE, na = "")
utils::write.csv(leave_one_year_out, file.path(output_dir, "e_dispo_v4_pain_severe_leave_one_year_out.csv"), row.names = FALSE, na = "")
writeLines(decision_lines, con = file.path(output_dir, "e_dispo_v4_pain_severe_validation_report.md"))

cat("Wrote e-dispo-v4.0 severe pain validation outputs under ", output_dir, "\n", sep = "")
