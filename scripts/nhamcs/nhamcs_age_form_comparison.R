#!/usr/bin/env Rscript

# Compare categorical age bands against continuous age forms for the pooled
# NHAMCS empirical candidate. This is assessment-only output; it does not
# promote coefficients or change app behavior.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: nhamcs_age_form_comparison.R <pooled_analytic_cohort_csv> <output_dir>")
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
if (!requireNamespace("splines", quietly = TRUE)) {
  stop("R package 'splines' is required.")
}

options(survey.lonely.psu = "adjust")

DATASET <- "NHAMCS_2018_2022_POOLED"
AGE_CENTER <- 42
MATERIAL_BRIER_IMPROVEMENT <- 0.002
MATERIAL_AUROC_IMPROVEMENT <- 0.01
MATERIAL_RISK_DIFFERENCE <- 0.02
SUSTAINED_AGE_COUNT <- 3L

cohort <- read.csv(input_path, stringsAsFactors = FALSE, na.strings = c("", "NA", "NaN"))
if ("dataset" %in% names(cohort) && length(unique(cohort$dataset[!is.na(cohort$dataset)])) > 0) {
  DATASET <- unique(cohort$dataset[!is.na(cohort$dataset)])[[1]]
}

truthy <- function(value) {
  tolower(trimws(as.character(value))) %in% c("true", "1", "yes")
}

required <- c(
  "include_strict_binary",
  "admit",
  "year",
  "age",
  "age_band",
  "pain_bin3",
  "pain_missing",
  "pooled_weight",
  "pooled_stratum",
  "pooled_psu"
)
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
binary$pain_missing[is.na(binary$pain_missing)] <- ifelse(is.na(binary$pain_bin3[is.na(binary$pain_missing)]), 1, 0)
binary$pain_bin3[is.na(binary$pain_bin3)] <- "moderate"
binary$pain_bin3 <- stats::relevel(as.factor(binary$pain_bin3), ref = "moderate")
binary$age_band <- stats::relevel(as.factor(binary$age_band), ref = "30_44")

valid <- !is.na(binary$admit) &
  binary$admit %in% c(0, 1) &
  !is.na(binary$year) &
  !is.na(binary$age) &
  !is.na(binary$age_band) &
  !is.na(binary$pain_bin3) &
  !is.na(binary$pain_missing) &
  !is.na(binary$weight) &
  binary$weight > 0 &
  !is.na(binary$stratum) &
  !is.na(binary$psu)
binary <- binary[valid, , drop = FALSE]

if (nrow(binary) == 0 || length(unique(binary$admit)) < 2) {
  stop("No usable strict-binary records with outcome variation after age-form filtering.")
}

MODEL_SPECS <- list(
  list(
    model_id = "pooled_empirical_age_band_candidate",
    formula = admit ~ age_band + pain_bin3 + pain_missing,
    age_form = "age_band"
  ),
  list(
    model_id = "pooled_empirical_age_linear_candidate",
    formula = admit ~ age_centered + pain_bin3 + pain_missing,
    age_form = "linear_age_per_year_centered_at_42"
  ),
  list(
    model_id = "pooled_empirical_age_spline_sensitivity",
    formula = admit ~ splines::ns(age, df = 3) + pain_bin3 + pain_missing,
    age_form = "natural_spline_age_df3"
  )
)

weighted_mean <- function(value, weight) {
  sum(value * weight, na.rm = TRUE) / sum(weight[!is.na(value)], na.rm = TRUE)
}

logit <- function(value) {
  clipped <- pmin(pmax(value, 1e-6), 1 - 1e-6)
  log(clipped / (1 - clipped))
}

normal_ci <- function(rate, n) {
  if (is.na(rate) || n <= 0) {
    return(c(NA_real_, NA_real_))
  }
  se <- sqrt(rate * (1 - rate) / n)
  c(max(0, rate - 1.96 * se), min(1, rate + 1.96 * se))
}

weighted_auc <- function(y, predicted, weight) {
  positive <- which(y == 1)
  negative <- which(y == 0)
  if (length(positive) == 0 || length(negative) == 0) {
    return(NA_real_)
  }
  pos_pred <- predicted[positive]
  neg_pred <- predicted[negative]
  pos_weight <- weight[positive]
  neg_weight <- weight[negative]
  comparisons <- outer(pos_pred, neg_pred, "-")
  weight_pairs <- outer(pos_weight, neg_weight, "*")
  numerator <- sum(weight_pairs[comparisons > 0]) + 0.5 * sum(weight_pairs[comparisons == 0])
  denominator <- sum(pos_weight) * sum(neg_weight)
  numerator / denominator
}

calibration_status <- function(slope, observed, predicted, events) {
  if (events < 100) {
    return("survey_weighted_candidate_exploratory_event_count_lt_100")
  }
  if (is.na(slope)) {
    return("fail_calibration_unavailable")
  }
  absolute_gap <- abs(predicted - observed)
  relative_gap <- absolute_gap / max(observed, 1e-6)
  if (absolute_gap > 0.02 || relative_gap > 0.10) {
    return("fail_recalibrate_intercept")
  }
  if (slope < 0.8) {
    return("fail_likely_overfit")
  }
  if (slope > 1.2) {
    return("fail_likely_underfit")
  }
  "pass_candidate_range"
}

parse_coefficient <- function(name) {
  if (identical(name, "(Intercept)")) {
    return(list(term = "intercept", level = ""))
  }
  if (startsWith(name, "age_band")) {
    return(list(term = "age_band", level = substring(name, nchar("age_band") + 1)))
  }
  if (identical(name, "age_centered")) {
    return(list(term = "age_centered", level = "per_1_year_centered_at_42"))
  }
  if (startsWith(name, "splines::ns(age, df = 3)")) {
    suffix <- substring(name, nchar("splines::ns(age, df = 3)") + 1)
    return(list(term = "age_spline_ns_df3", level = paste0("basis_", suffix)))
  }
  if (startsWith(name, "pain_bin3")) {
    return(list(term = "pain_bin3", level = substring(name, nchar("pain_bin3") + 1)))
  }
  if (identical(name, "pain_missing")) {
    return(list(term = "pain_missing", level = "1"))
  }
  list(term = name, level = "")
}

coefficient_label <- function(parsed) {
  if (identical(parsed$level, "")) {
    return(parsed$term)
  }
  paste0(parsed$term, "[", parsed$level, "]")
}

fit_one_model <- function(spec, frame) {
  design <- survey::svydesign(
    ids = ~psu,
    strata = ~stratum,
    weights = ~weight,
    nest = TRUE,
    data = frame
  )
  fit <- survey::svyglm(spec$formula, design = design, family = quasibinomial())
  coef_table <- summary(fit)$coefficients
  beta <- stats::coef(fit)
  covariance <- stats::vcov(fit)
  se <- sqrt(pmax(diag(covariance), 0))
  p_values <- coef_table[, ncol(coef_table)]
  parsed_terms <- lapply(names(beta), parse_coefficient)

  coefficients <- data.frame(
    model_id = spec$model_id,
    dataset = DATASET,
    age_form = spec$age_form,
    term = vapply(parsed_terms, function(item) item$term, character(1)),
    level = vapply(parsed_terms, function(item) item$level, character(1)),
    beta = as.numeric(beta),
    se = as.numeric(se),
    odds_ratio = exp(as.numeric(beta)),
    ci_low = exp(as.numeric(beta) - 1.96 * as.numeric(se)),
    ci_high = exp(as.numeric(beta) + 1.96 * as.numeric(se)),
    p_value = as.numeric(p_values),
    evidence_tier = "survey_weighted_candidate",
    limitation_note = "Age-form assessment only; no coefficient promotion or app activation.",
    stringsAsFactors = FALSE
  )

  predicted <- as.numeric(stats::predict(fit, type = "response"))
  y <- frame$admit
  weight <- frame$weight
  observed <- weighted_mean(y, weight)
  mean_predicted <- weighted_mean(predicted, weight)
  frame$.__linear_prediction <- logit(predicted)
  frame$.__predicted <- predicted
  calibration_design <- survey::svydesign(
    ids = ~psu,
    strata = ~stratum,
    weights = ~weight,
    nest = TRUE,
    data = frame
  )
  intercept_fit <- survey::svyglm(admit ~ 1 + offset(.__linear_prediction), design = calibration_design, family = quasibinomial())
  slope_fit <- survey::svyglm(admit ~ .__linear_prediction, design = calibration_design, family = quasibinomial())
  calibration_intercept <- as.numeric(stats::coef(intercept_fit)[[1]])
  calibration_slope <- as.numeric(stats::coef(slope_fit)[[".__linear_prediction"]])
  brier <- weighted_mean((predicted - y) ^ 2, weight)
  auroc <- weighted_auc(y, predicted, weight)
  events <- sum(y)

  calibration <- data.frame(
    model_id = spec$model_id,
    dataset = DATASET,
    age_form = spec$age_form,
    n = nrow(frame),
    events = events,
    observed_prevalence = observed,
    mean_predicted = mean_predicted,
    calibration_in_the_large = calibration_intercept,
    calibration_slope = calibration_slope,
    brier_score = brier,
    auroc = auroc,
    pass_fail_status = calibration_status(calibration_slope, observed, mean_predicted, events),
    notes = "Survey-weighted apparent calibration for age-form assessment.",
    stringsAsFactors = FALSE
  )

  order_index <- order(predicted)
  cumulative_weight <- cumsum(weight[order_index])
  decile <- rep(NA_integer_, length(predicted))
  decile[order_index] <- pmin(10L, pmax(1L, ceiling(cumulative_weight / sum(weight) * 10L)))
  deciles <- data.frame()
  for (group in sort(unique(decile))) {
    subset <- decile == group
    observed_rate <- weighted_mean(y[subset], weight[subset])
    ci <- normal_ci(observed_rate, sum(subset))
    deciles <- rbind(
      deciles,
      data.frame(
        model_id = spec$model_id,
        dataset = DATASET,
        age_form = spec$age_form,
        decile = group,
        n = sum(subset),
        events = sum(y[subset]),
        mean_predicted = weighted_mean(predicted[subset], weight[subset]),
        observed_rate = observed_rate,
        ci_low = ci[[1]],
        ci_high = ci[[2]],
        notes = "Survey-weighted decile calibration; CI is approximate unweighted normal interval.",
        stringsAsFactors = FALSE
      )
    )
  }

  list(
    fit = fit,
    coefficients = coefficients,
    calibration = calibration,
    deciles = deciles
  )
}

age_band_for_age <- function(age) {
  ifelse(
    age <= 29,
    "18_29",
    ifelse(age <= 44, "30_44", ifelse(age <= 54, "45_54", "55_64"))
  )
}

prediction_grid <- function() {
  ages <- 18:64
  data.frame(
    age = ages,
    age_centered = ages - AGE_CENTER,
    age_band = factor(age_band_for_age(ages), levels = levels(binary$age_band)),
    pain_bin3 = factor(rep("moderate", length(ages)), levels = levels(binary$pain_bin3)),
    pain_missing = rep(0, length(ages)),
    stringsAsFactors = FALSE
  )
}

prediction_rows <- function(result, spec) {
  grid <- prediction_grid()
  predicted <- as.numeric(stats::predict(result$fit, newdata = grid, type = "response"))
  data.frame(
    model_id = spec$model_id,
    dataset = DATASET,
    age_form = spec$age_form,
    age = grid$age,
    age_centered = grid$age_centered,
    age_band = as.character(grid$age_band),
    pain_bin3 = "moderate",
    pain_missing = 0,
    predicted_admission_probability = predicted,
    absolute_difference_from_age_band = NA_real_,
    stringsAsFactors = FALSE
  )
}

heldout_metric_row <- function(spec, train, test, heldout_year) {
  if (nrow(train) == 0 || nrow(test) == 0 || length(unique(train$admit)) < 2) {
    return(data.frame(
      heldout_year = heldout_year,
      model_id = spec$model_id,
      dataset = DATASET,
      age_form = spec$age_form,
      train_n = nrow(train),
      train_events = if (nrow(train) > 0) sum(train$admit) else 0,
      train_weighted_n = if (nrow(train) > 0) sum(train$weight) else NA_real_,
      heldout_n = nrow(test),
      heldout_events = if (nrow(test) > 0) sum(test$admit) else 0,
      heldout_weighted_n = if (nrow(test) > 0) sum(test$weight) else NA_real_,
      observed_prevalence = NA_real_,
      mean_predicted = NA_real_,
      calibration_in_the_large = NA_real_,
      calibration_slope = NA_real_,
      brier_score = NA_real_,
      auroc = NA_real_,
      pass_fail_status = "blocked_no_train_or_test_outcome_variation",
      evidence_tier = "survey_weighted_candidate",
      notes = "Leave-one-year-out age-form validation.",
      stringsAsFactors = FALSE
    ))
  }

  result <- fit_one_model(spec, train)
  predicted <- as.numeric(stats::predict(result$fit, newdata = test, type = "response"))
  y <- test$admit
  weight <- test$weight
  observed <- weighted_mean(y, weight)
  mean_predicted <- weighted_mean(predicted, weight)
  brier <- weighted_mean((predicted - y) ^ 2, weight)
  auroc <- weighted_auc(y, predicted, weight)
  linear_prediction <- logit(predicted)
  calibration_intercept <- NA_real_
  calibration_slope <- NA_real_

  if (length(unique(y)) >= 2 && length(unique(linear_prediction)) >= 2) {
    calibration_frame <- test
    calibration_frame$.__linear_prediction <- linear_prediction
    calibration_design <- survey::svydesign(
      ids = ~psu,
      strata = ~stratum,
      weights = ~weight,
      nest = TRUE,
      data = calibration_frame
    )
    intercept_fit <- survey::svyglm(admit ~ 1 + offset(.__linear_prediction), design = calibration_design, family = quasibinomial())
    slope_fit <- survey::svyglm(admit ~ .__linear_prediction, design = calibration_design, family = quasibinomial())
    calibration_intercept <- as.numeric(stats::coef(intercept_fit)[[1]])
    calibration_slope <- as.numeric(stats::coef(slope_fit)[[".__linear_prediction"]])
  }

  data.frame(
    heldout_year = heldout_year,
    model_id = spec$model_id,
    dataset = DATASET,
    age_form = spec$age_form,
    train_n = nrow(train),
    train_events = sum(train$admit),
    train_weighted_n = sum(train$weight),
    heldout_n = nrow(test),
    heldout_events = sum(test$admit),
    heldout_weighted_n = sum(test$weight),
    observed_prevalence = observed,
    mean_predicted = mean_predicted,
    calibration_in_the_large = calibration_intercept,
    calibration_slope = calibration_slope,
    brier_score = brier,
    auroc = auroc,
    pass_fail_status = calibration_status(calibration_slope, observed, mean_predicted, sum(y)),
    evidence_tier = "survey_weighted_candidate",
    notes = "Leave-one-year-out age-form validation.",
    stringsAsFactors = FALSE
  )
}

leave_one_year_out_rows <- function(frame) {
  validation_specs <- MODEL_SPECS[vapply(
    MODEL_SPECS,
    function(spec) spec$model_id %in% c(
      "pooled_empirical_age_linear_candidate",
      "pooled_empirical_age_spline_sensitivity"
    ),
    logical(1)
  )]
  rows <- data.frame()
  for (heldout_year in sort(unique(frame$year))) {
    train <- frame[frame$year != heldout_year, , drop = FALSE]
    test <- frame[frame$year == heldout_year, , drop = FALSE]
    for (spec in validation_specs) {
      rows <- rbind(rows, heldout_metric_row(spec, train, test, heldout_year))
    }
  }
  rows
}

curve_comparison_rows <- function(prediction_frame) {
  linear_curve <- prediction_frame[
    prediction_frame$model_id == "pooled_empirical_age_linear_candidate",
    c("age", "predicted_admission_probability")
  ]
  names(linear_curve)[[2]] <- "linear_predicted_admission_probability"
  spline_curve <- prediction_frame[
    prediction_frame$model_id == "pooled_empirical_age_spline_sensitivity",
    c("age", "predicted_admission_probability")
  ]
  names(spline_curve)[[2]] <- "spline_predicted_admission_probability"
  curve <- merge(linear_curve, spline_curve, by = "age", sort = TRUE)
  curve$dataset <- DATASET
  curve$age_centered <- curve$age - AGE_CENTER
  curve$pain_bin3 <- "moderate"
  curve$pain_missing <- 0
  curve$absolute_difference <- abs(
    curve$spline_predicted_admission_probability - curve$linear_predicted_admission_probability
  )
  curve$material_difference <- curve$absolute_difference >= MATERIAL_RISK_DIFFERENCE
  runs <- rle(curve$material_difference)
  run_ids <- rep(seq_along(runs$lengths), runs$lengths)
  curve$sustained_material_difference <- curve$material_difference & runs$lengths[run_ids] >= SUSTAINED_AGE_COUNT
  curve$sustained_range_id <- ifelse(curve$sustained_material_difference, run_ids, NA_integer_)
  curve$evidence_tier <- "survey_weighted_candidate"
  curve[
    ,
    c(
      "dataset",
      "age",
      "age_centered",
      "pain_bin3",
      "pain_missing",
      "linear_predicted_admission_probability",
      "spline_predicted_admission_probability",
      "absolute_difference",
      "material_difference",
      "sustained_material_difference",
      "sustained_range_id",
      "evidence_tier"
    )
  ]
}

likelihood_style_comparison <- function(frame) {
  linear_glm <- stats::glm(
    admit ~ age_centered + pain_bin3 + pain_missing,
    data = frame,
    family = stats::binomial()
  )
  spline_glm <- stats::glm(
    admit ~ splines::ns(age, df = 3) + pain_bin3 + pain_missing,
    data = frame,
    family = stats::binomial()
  )
  df_delta <- stats::df.residual(linear_glm) - stats::df.residual(spline_glm)
  deviance_delta <- stats::deviance(linear_glm) - stats::deviance(spline_glm)
  p_value <- stats::pchisq(deviance_delta, df = df_delta, lower.tail = FALSE)
  data.frame(
    comparison = "unweighted_binomial_likelihood_style_linear_vs_spline",
    dataset = DATASET,
    linear_residual_df = stats::df.residual(linear_glm),
    spline_residual_df = stats::df.residual(spline_glm),
    df_delta = df_delta,
    linear_deviance = stats::deviance(linear_glm),
    spline_deviance = stats::deviance(spline_glm),
    deviance_delta = deviance_delta,
    p_value = p_value,
    linear_aic = stats::AIC(linear_glm),
    spline_aic = stats::AIC(spline_glm),
    notes = "Unweighted binomial likelihood-style comparison only; survey::svyglm quasibinomial does not provide a decisive nested likelihood test.",
    stringsAsFactors = FALSE
  )
}

summarize_loo <- function(rows) {
  linear_rows <- rows[rows$model_id == "pooled_empirical_age_linear_candidate", , drop = FALSE]
  spline_rows <- rows[rows$model_id == "pooled_empirical_age_spline_sensitivity", , drop = FALSE]
  merged <- merge(
    linear_rows,
    spline_rows,
    by = "heldout_year",
    suffixes = c("_linear", "_spline"),
    sort = TRUE
  )
  weights <- merged$heldout_n_linear
  brier_improvement <- merged$brier_score_linear - merged$brier_score_spline
  auroc_improvement <- merged$auroc_spline - merged$auroc_linear
  data.frame(
    mean_brier_improvement = weighted_mean(brier_improvement, weights),
    mean_auroc_improvement = weighted_mean(auroc_improvement, weights),
    max_brier_improvement = max(brier_improvement, na.rm = TRUE),
    max_auroc_improvement = max(auroc_improvement, na.rm = TRUE),
    years_with_spline_brier_better = sum(brier_improvement > 0, na.rm = TRUE),
    years_with_spline_auroc_better = sum(auroc_improvement > 0, na.rm = TRUE),
    years_with_material_spline_gain = sum(
      brier_improvement >= MATERIAL_BRIER_IMPROVEMENT |
        auroc_improvement >= MATERIAL_AUROC_IMPROVEMENT,
      na.rm = TRUE
    ),
    stringsAsFactors = FALSE
  )
}

results <- lapply(MODEL_SPECS, fit_one_model, frame = binary)
names(results) <- vapply(MODEL_SPECS, function(spec) spec$model_id, character(1))

coefficients <- do.call(rbind, lapply(results, function(item) item$coefficients))
calibration <- do.call(rbind, lapply(results, function(item) item$calibration))
deciles <- do.call(rbind, lapply(results, function(item) item$deciles))
predictions <- do.call(rbind, Map(prediction_rows, results, MODEL_SPECS))

baseline_predictions <- predictions[
  predictions$model_id == "pooled_empirical_age_band_candidate",
  c("age", "predicted_admission_probability"),
]
names(baseline_predictions)[[2]] <- "age_band_prediction"
predictions <- merge(predictions, baseline_predictions, by = "age", all.x = TRUE, sort = FALSE)
predictions$absolute_difference_from_age_band <- abs(
  predictions$predicted_admission_probability - predictions$age_band_prediction
)
predictions <- predictions[
  order(match(predictions$model_id, vapply(MODEL_SPECS, function(spec) spec$model_id, character(1))), predictions$age),
  setdiff(names(predictions), "age_band_prediction"),
]
leave_one_year_out <- leave_one_year_out_rows(binary)
curve_comparison <- curve_comparison_rows(predictions)
likelihood_comparison <- likelihood_style_comparison(binary)
loo_summary <- summarize_loo(leave_one_year_out)

utils::write.csv(
  coefficients,
  file.path(output_dir, "age_form_comparison_coefficients.csv"),
  row.names = FALSE,
  na = ""
)
utils::write.csv(
  calibration,
  file.path(output_dir, "age_form_comparison_calibration.csv"),
  row.names = FALSE,
  na = ""
)
utils::write.csv(
  deciles,
  file.path(output_dir, "age_form_comparison_deciles.csv"),
  row.names = FALSE,
  na = ""
)
utils::write.csv(
  predictions,
  file.path(output_dir, "age_form_comparison_predictions_by_age.csv"),
  row.names = FALSE,
  na = ""
)
utils::write.csv(
  leave_one_year_out,
  file.path(output_dir, "age_form_leave_one_year_out.csv"),
  row.names = FALSE,
  na = ""
)
utils::write.csv(
  curve_comparison,
  file.path(output_dir, "age_form_curve_comparison.csv"),
  row.names = FALSE,
  na = ""
)
utils::write.csv(
  likelihood_comparison,
  file.path(output_dir, "age_form_likelihood_style_comparison.csv"),
  row.names = FALSE,
  na = ""
)

metric_row <- function(model_id) {
  calibration[calibration$model_id == model_id, , drop = FALSE][1, , drop = FALSE]
}

coefficient_row <- function(model_id, term) {
  rows <- coefficients[coefficients$model_id == model_id & coefficients$term == term, , drop = FALSE]
  if (nrow(rows) == 0) {
    return(NULL)
  }
  rows[1, , drop = FALSE]
}

band <- metric_row("pooled_empirical_age_band_candidate")
linear <- metric_row("pooled_empirical_age_linear_candidate")
spline <- metric_row("pooled_empirical_age_spline_sensitivity")
linear_age <- coefficient_row("pooled_empirical_age_linear_candidate", "age_centered")

linear_brier_delta <- band$brier_score - linear$brier_score
linear_auroc_delta <- linear$auroc - band$auroc
spline_brier_delta <- linear$brier_score - spline$brier_score
spline_auroc_delta <- spline$auroc - linear$auroc
linear_max_age_diff <- max(
  predictions$absolute_difference_from_age_band[predictions$model_id == "pooled_empirical_age_linear_candidate"],
  na.rm = TRUE
)
spline_max_linear_diff <- {
  linear_predictions <- predictions[
    predictions$model_id == "pooled_empirical_age_linear_candidate",
    c("age", "predicted_admission_probability")
  ]
  names(linear_predictions)[[2]] <- "linear_prediction"
  spline_predictions <- predictions[
    predictions$model_id == "pooled_empirical_age_spline_sensitivity",
    c("age", "predicted_admission_probability")
  ]
  merged <- merge(spline_predictions, linear_predictions, by = "age", sort = FALSE)
  max(abs(merged$predicted_admission_probability - merged$linear_prediction), na.rm = TRUE)
}

linear_stable <- !is.null(linear_age) &&
  is.finite(linear_age$beta) &&
  is.finite(linear_age$se) &&
  linear_age$se > 0 &&
  abs(linear_age$beta / linear_age$se) >= 1
linear_material_gain <- linear_brier_delta >= MATERIAL_BRIER_IMPROVEMENT || linear_auroc_delta >= MATERIAL_AUROC_IMPROVEMENT
linear_calibration_ok <- identical(as.character(linear$pass_fail_status), "pass_candidate_range")
spline_material_gain <- spline_brier_delta >= MATERIAL_BRIER_IMPROVEMENT || spline_auroc_delta >= MATERIAL_AUROC_IMPROVEMENT
spline_nonlinearity <- spline_max_linear_diff >= MATERIAL_RISK_DIFFERENCE
heldout_spline_brier_improvement <- loo_summary$mean_brier_improvement[[1]]
heldout_spline_auroc_improvement <- loo_summary$mean_auroc_improvement[[1]]
heldout_spline_material_gain <- heldout_spline_brier_improvement >= MATERIAL_BRIER_IMPROVEMENT ||
  heldout_spline_auroc_improvement >= MATERIAL_AUROC_IMPROVEMENT
sustained_curve_material <- any(curve_comparison$sustained_material_difference, na.rm = TRUE)
nonlinearity_decision <- if (heldout_spline_material_gain && sustained_curve_material) {
  "spline_age_requires_review"
} else {
  "linear_continuous_age_adequate"
}

recommendation <- if (linear_calibration_ok && linear_stable) {
  "use_linear_continuous_age_primary_with_age_band_sensitivity"
} else {
  "keep_age_band_primary"
}
if (recommendation == "keep_age_band_primary") {
  sensitivity_note <- "Continuous age did not clear stability and material-improvement criteria for primary use."
} else {
  sensitivity_note <- "Linear continuous age cleared stability and calibration checks and is the preferred slider-compatible primary form."
}
spline_note <- if (spline_material_gain && spline_nonlinearity) {
  "Spline age suggests possible nonlinearity, but should remain sensitivity-only unless a later validation gate supports the extra complexity."
} else if (heldout_spline_material_gain && sustained_curve_material) {
  "Leave-one-year-out validation and the age curve suggest spline nonlinearity may matter; review before adopting spline complexity."
} else {
  "Spline age does not provide enough held-out or sustained curve improvement to justify primary use."
}

format_number <- function(value, digits = 4) {
  if (is.na(value) || !is.finite(value)) {
    return("")
  }
  format(round(value, digits), nsmall = digits, trim = TRUE)
}

markdown_metric_table <- function(rows) {
  lines <- c(
    "| Model | N | Events | Observed prevalence | Mean predicted | Calibration intercept | Calibration slope | Brier | AUROC | Status |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"
  )
  for (index in seq_len(nrow(rows))) {
    row <- rows[index, ]
    lines <- c(
      lines,
      paste0(
        "| `", row$model_id, "` | ",
        row$n, " | ",
        row$events, " | ",
        format_number(row$observed_prevalence), " | ",
        format_number(row$mean_predicted), " | ",
        format_number(row$calibration_in_the_large, 6), " | ",
        format_number(row$calibration_slope), " | ",
        format_number(row$brier_score), " | ",
        format_number(row$auroc), " | `",
        row$pass_fail_status, "` |"
      )
    )
  }
  lines
}

markdown_loo_table <- function(rows) {
  lines <- c(
    "| Held-out year | Model | Train N | Train events | Held-out N | Held-out events | Brier | AUROC | Calibration intercept | Calibration slope | Status |",
    "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"
  )
  for (index in seq_len(nrow(rows))) {
    row <- rows[index, ]
    lines <- c(
      lines,
      paste0(
        "| ", row$heldout_year, " | `",
        row$model_id, "` | ",
        row$train_n, " | ",
        row$train_events, " | ",
        row$heldout_n, " | ",
        row$heldout_events, " | ",
        format_number(row$brier_score), " | ",
        format_number(row$auroc), " | ",
        format_number(row$calibration_in_the_large, 6), " | ",
        format_number(row$calibration_slope), " | `",
        row$pass_fail_status, "` |"
      )
    )
  }
  lines
}

linear_beta_text <- if (is.null(linear_age)) {
  "- Linear age coefficient was not estimated."
} else {
  paste0(
    "- Linear age coefficient per 1 year centered at 42: beta ",
    format_number(linear_age$beta, 4),
    ", SE ",
    format_number(linear_age$se, 4),
    ", OR ",
    format_number(linear_age$odds_ratio, 3),
    "; OR per 10 years ",
    format_number(exp(linear_age$beta * 10), 3),
    "."
  )
}

decision_report <- c(
  "# Age Nonlinearity Decision",
  "",
  paste0("Dataset: `", DATASET, "`"),
  "",
  paste0("Decision: `", nonlinearity_decision, "`."),
  "",
  "## Decision Rule",
  "",
  paste0("- Spline must improve held-out Brier by at least ", MATERIAL_BRIER_IMPROVEMENT, " or AUROC by at least ", MATERIAL_AUROC_IMPROVEMENT, "."),
  paste0("- Spline curve must differ from linear age by at least ", MATERIAL_RISK_DIFFERENCE, " absolute risk over at least ", SUSTAINED_AGE_COUNT, " consecutive ages."),
  "- Coefficients remain `survey_weighted_candidate`; no `dataset_derived` promotion occurs here.",
  "",
  "## Leave-One-Year-Out Summary",
  "",
  paste0("- Mean held-out Brier improvement from spline vs linear: ", format_number(heldout_spline_brier_improvement, 6), "."),
  paste0("- Mean held-out AUROC improvement from spline vs linear: ", format_number(heldout_spline_auroc_improvement, 6), "."),
  paste0("- Years with material spline gain: ", loo_summary$years_with_material_spline_gain[[1]], "."),
  "",
  "## Curve Summary",
  "",
  paste0("- Maximum apparent spline-vs-linear absolute risk difference across ages 18-64: ", format_number(spline_max_linear_diff, 4), "."),
  paste0("- Sustained material curve difference present: `", tolower(as.character(sustained_curve_material)), "`."),
  "",
  "## Likelihood-Style Check",
  "",
  paste0("- Deviance improvement for spline vs linear: ", format_number(likelihood_comparison$deviance_delta[[1]], 4), "."),
  paste0("- Approximate unweighted p-value: ", format_number(likelihood_comparison$p_value[[1]], 6), "."),
  "- This is not decisive because the primary fitted models use survey-weighted quasibinomial `survey::svyglm`.",
  "",
  "## Recommendation",
  "",
  if (identical(nonlinearity_decision, "linear_continuous_age_adequate")) {
    "Use linear continuous age as the primary slider-compatible age form; keep spline age as sensitivity only."
  } else {
    "Do not adopt linear age without review; spline age may be capturing meaningful nonlinearity."
  }
)

writeLines(decision_report, con = file.path(output_dir, "age_form_nonlinearity_decision.md"))

report <- c(
  "# Continuous Age Form Assessment",
  "",
  paste0("Dataset: `", DATASET, "`"),
  "",
  "This is an assessment-only run. It does not promote coefficients, change the app UI, or claim clinical validity.",
  "",
  "## Recommendation",
  "",
  paste0("Recommendation: `", recommendation, "`."),
  "",
  paste0("- ", sensitivity_note),
  paste0("- ", spline_note),
  "- Age bands remain a comparison model only; this assessment does not change app behavior.",
  "",
  "## Model Comparison",
  "",
  markdown_metric_table(calibration),
  "",
  "## Continuous Age Signal",
  "",
  linear_beta_text,
  paste0("- Linear age Brier improvement vs age bands: ", format_number(linear_brier_delta, 6), "."),
  paste0("- Linear age AUROC change vs age bands: ", format_number(linear_auroc_delta, 6), "."),
  paste0("- Maximum absolute predicted-risk difference between linear age and age bands across ages 18-64: ", format_number(linear_max_age_diff, 4), "."),
  "",
  "## Spline Sensitivity",
  "",
  paste0("- Spline Brier improvement vs linear age: ", format_number(spline_brier_delta, 6), "."),
  paste0("- Spline AUROC change vs linear age: ", format_number(spline_auroc_delta, 6), "."),
  paste0("- Maximum absolute predicted-risk difference between spline and linear age across ages 18-64: ", format_number(spline_max_linear_diff, 4), "."),
  "",
  "## Leave-One-Year-Out Validation",
  "",
  markdown_loo_table(leave_one_year_out),
  "",
  "## Nonlinearity Decision",
  "",
  paste0("- Decision: `", nonlinearity_decision, "`."),
  paste0("- Mean held-out Brier improvement from spline vs linear: ", format_number(heldout_spline_brier_improvement, 6), "."),
  paste0("- Mean held-out AUROC improvement from spline vs linear: ", format_number(heldout_spline_auroc_improvement, 6), "."),
  paste0("- Sustained material curve difference present: `", tolower(as.character(sustained_curve_material)), "`."),
  "",
  "## Output Files",
  "",
  "- `age_form_comparison_coefficients.csv`",
  "- `age_form_comparison_calibration.csv`",
  "- `age_form_comparison_deciles.csv`",
  "- `age_form_comparison_predictions_by_age.csv`",
  "- `age_form_leave_one_year_out.csv`",
  "- `age_form_curve_comparison.csv`",
  "- `age_form_likelihood_style_comparison.csv`",
  "- `age_form_nonlinearity_decision.md`",
  "",
  "## Boundary",
  "",
  "- Keep all coefficients labeled `survey_weighted_candidate` after this assessment.",
  "- Do not adopt spline age as primary from this run.",
  "- Do not change app inputs until the dataset-derived evidence gate is separately implemented."
)

writeLines(report, con = file.path(output_dir, "age_form_comparison_report.md"))

cat("Wrote age-form comparison outputs under ", output_dir, "\n", sep = "")
