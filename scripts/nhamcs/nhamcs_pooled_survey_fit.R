#!/usr/bin/env Rscript

# Survey-weighted pooled NHAMCS logistic fitting entry point.
#
# This script writes the canonical NHAMCS model output files using
# survey::svyglm and Taylor linearization. The outputs are candidate evidence
# only; downstream gates decide whether any coefficient can be promoted.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: nhamcs_pooled_survey_fit.R <pooled_analytic_cohort_csv> <output_dir>")
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
environment_status <- nhamcs_configure_r_environment()
package_status <- nhamcs_write_r_environment_report(output_dir, required_packages = c("survey"))

if (!requireNamespace("survey", quietly = TRUE)) {
  stop("R package 'survey' is required for NHAMCS survey-weighted fitting. Set NHAMCS_R_LIBS or install survey into an active R library.")
}

options(survey.lonely.psu = "adjust")
RANDOM_SEED <- 20260428L
DRAW_COUNT <- 10000L
set.seed(RANDOM_SEED)

MODEL_SPECS <- list(
  list(
    model_id = "pooled_primary_reduced",
    formula = "admit ~ age_band + pain_bin3 + pain_missing + fever_or_temp",
    terms = list(
      list(kind = "categorical", field = "age_band", reference = "30_44"),
      list(kind = "categorical", field = "pain_bin3", reference = "moderate"),
      list(kind = "binary", field = "pain_missing", reference = "0"),
      list(kind = "binary", field = "fever_or_temp", reference = "0")
    )
  ),
  list(
    model_id = "pooled_secondary_no_pain",
    formula = "admit ~ age_band + fever_or_temp",
    terms = list(
      list(kind = "categorical", field = "age_band", reference = "30_44"),
      list(kind = "binary", field = "fever_or_temp", reference = "0")
    )
  ),
  list(
    model_id = "pooled_candidate_v4_sensitivity",
    formula = "admit ~ age_band + pain_bin3 + pain_missing + acuity + temp + HR + SBP",
    terms = list(
      list(kind = "categorical", field = "age_band", reference = "30_44"),
      list(kind = "categorical", field = "pain_bin3", reference = "moderate"),
      list(kind = "binary", field = "pain_missing", reference = "0"),
      list(kind = "continuous", field = "temp", reference = "mean_centered_scaled"),
      list(kind = "continuous", field = "acuity", reference = "mean_centered_scaled"),
      list(kind = "continuous", field = "HR", reference = "mean_centered_scaled"),
      list(kind = "continuous", field = "SBP", reference = "mean_centered_scaled")
    )
  ),
  list(
    model_id = "pooled_year_adjusted_reduced",
    formula = "admit ~ age_band + pain_bin3 + pain_missing + fever_or_temp + year_factor",
    terms = list(
      list(kind = "categorical", field = "age_band", reference = "30_44"),
      list(kind = "categorical", field = "pain_bin3", reference = "moderate"),
      list(kind = "binary", field = "pain_missing", reference = "0"),
      list(kind = "binary", field = "fever_or_temp", reference = "0"),
      list(kind = "categorical", field = "year_factor", reference = "2022")
    )
  )
)

cohort <- read.csv(input_path, stringsAsFactors = FALSE, na.strings = c("", "NA", "NaN"))
if ("dataset" %in% names(cohort) && length(unique(cohort$dataset[!is.na(cohort$dataset)])) > 0) {
  DATASET <- unique(cohort$dataset[!is.na(cohort$dataset)])[[1]]
} else {
  DATASET <- "NHAMCS_POOLED"
}
if ("pooled_weight" %in% names(cohort)) {
  cohort$weight <- cohort$pooled_weight
}
if ("pooled_stratum" %in% names(cohort)) {
  cohort$stratum <- cohort$pooled_stratum
}
if ("pooled_psu" %in% names(cohort)) {
  cohort$psu <- cohort$pooled_psu
}
if (!"year_factor" %in% names(cohort) && "year" %in% names(cohort)) {
  cohort$year_factor <- as.character(cohort$year)
}
required <- c("include_strict_binary", "weight", "stratum", "psu", "admit", "age_band", "pain_bin3", "pain_missing", "fever_or_temp", "year_factor")
missing_required <- setdiff(required, names(cohort))
if (length(missing_required) > 0) {
  stop(paste("Missing required columns:", paste(missing_required, collapse = ", ")))
}

truthy <- function(value) {
  tolower(trimws(as.character(value))) %in% c("true", "1", "yes")
}

binary <- cohort[truthy(cohort$include_strict_binary), , drop = FALSE]
if (nrow(binary) == 0) {
  stop("Strict binary analytic cohort is empty.")
}

binary$admit <- as.numeric(binary$admit)
binary$weight <- as.numeric(binary$weight)
binary$stratum <- as.factor(binary$stratum)
binary$psu <- as.factor(binary$psu)
for (field in intersect(c("pain_score", "pain_missing", "temp", "fever_or_temp", "acuity", "HR", "SBP"), names(binary))) {
  binary[[field]] <- as.numeric(binary[[field]])
}

if (any(is.na(binary$admit)) || any(!binary$admit %in% c(0, 1))) {
  stop("admit must be coded 0/1 in the strict binary analytic cohort.")
}
if (any(is.na(binary$weight)) || any(binary$weight <= 0)) {
  stop("weight must be positive and nonmissing for survey-weighted fitting.")
}
if (any(is.na(binary$stratum)) || any(is.na(binary$psu))) {
  stop("stratum and psu must be nonmissing for survey-weighted fitting.")
}
if (length(unique(binary$admit)) < 2) {
  stop("Strict binary analytic cohort has no outcome variation.")
}

empty_coefficients <- function() {
  data.frame(
    model_id = character(),
    dataset = character(),
    term = character(),
    level = character(),
    beta = numeric(),
    se = numeric(),
    odds_ratio = numeric(),
    ci_low = numeric(),
    ci_high = numeric(),
    p_value = numeric(),
    evidence_tier = character(),
    limitation_note = character(),
    stringsAsFactors = FALSE
  )
}

empty_covariance <- function() {
  data.frame(
    model_id = character(),
    dataset = character(),
    row_term = character(),
    column_term = character(),
    covariance = numeric(),
    stringsAsFactors = FALSE
  )
}

empty_draws <- function() {
  data.frame(
    model_id = character(),
    dataset = character(),
    draw_id = integer(),
    term = character(),
    level = character(),
    beta = numeric(),
    seed = integer(),
    stringsAsFactors = FALSE
  )
}

empty_calibration <- function() {
  data.frame(
    model_id = character(),
    dataset = character(),
    n = integer(),
    events = integer(),
    observed_prevalence = numeric(),
    mean_predicted = numeric(),
    calibration_in_the_large = numeric(),
    calibration_slope = numeric(),
    brier_score = numeric(),
    auroc = numeric(),
    pass_fail_status = character(),
    notes = character(),
    stringsAsFactors = FALSE
  )
}

empty_deciles <- function() {
  data.frame(
    model_id = character(),
    dataset = character(),
    decile = integer(),
    n = integer(),
    events = integer(),
    mean_predicted = numeric(),
    observed_rate = numeric(),
    ci_low = numeric(),
    ci_high = numeric(),
    notes = character(),
    stringsAsFactors = FALSE
  )
}

empty_pain <- function() {
  data.frame(
    dataset = character(),
    mild_admit_rate = numeric(),
    moderate_admit_rate = numeric(),
    severe_admit_rate = numeric(),
    nhamcs_unadjusted_nondecreasing = character(),
    pain_missing_fraction = numeric(),
    total_admission_events = integer(),
    verdict = character(),
    reason = character(),
    stringsAsFactors = FALSE
  )
}

weighted_mean <- function(value, weight) {
  ok <- !is.na(value) & !is.na(weight)
  if (!any(ok)) {
    return(NA_real_)
  }
  sum(value[ok] * weight[ok]) / sum(weight[ok])
}

normal_ci <- function(rate, n) {
  if (is.na(rate) || n <= 0) {
    return(c(NA_real_, NA_real_))
  }
  se <- sqrt(max(rate * (1 - rate), 0) / n)
  c(max(0, rate - 1.96 * se), min(1, rate + 1.96 * se))
}

logit <- function(value) {
  value <- pmin(pmax(value, 1e-6), 1 - 1e-6)
  log(value / (1 - value))
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

has_variation <- function(value) {
  length(unique(value[!is.na(value)])) >= 2
}

uses_term <- function(spec, field) {
  any(vapply(spec$terms, function(term) identical(term$field, field), logical(1)))
}

prepare_model_frame <- function(binary, spec) {
  frame <- binary
  valid <- rep(TRUE, nrow(frame))
  active_terms <- character()
  term_info <- list()
  notes <- character()
  transformations <- character()
  pain_missing_in_model <- uses_term(spec, "pain_missing")

  for (term in spec$terms) {
    field <- term$field
    if (!field %in% names(frame)) {
      notes <- c(notes, paste(field, "absent; term removed."))
      next
    }

    values <- frame[[field]]
    if (identical(field, "pain_bin3") && pain_missing_in_model) {
      values[is.na(values)] <- term$reference
      transformations <- c(transformations, "Missing pain_bin3 filled to moderate only with explicit pain_missing term.")
    }
    if (identical(field, "pain_score") && pain_missing_in_model) {
      values <- as.numeric(values)
      values[is.na(values)] <- 0
      transformations <- c(transformations, "Missing pain_score filled to 0 only with explicit pain_missing term.")
    }

    if (identical(term$kind, "categorical")) {
      if (!has_variation(values)) {
        notes <- c(notes, paste(field, "has no usable categorical variation; term removed."))
        next
      }
      valid <- valid & !is.na(values)
      factor_values <- as.factor(values)
      if (term$reference %in% levels(factor_values)) {
        factor_values <- stats::relevel(factor_values, ref = term$reference)
      } else {
        notes <- c(notes, paste(field, "reference", term$reference, "not present; first observed level used."))
      }
      frame[[field]] <- factor_values
      active_terms <- c(active_terms, field)
      term_info[[field]] <- list(kind = term$kind, reference = term$reference)
    } else if (identical(term$kind, "binary")) {
      numeric_values <- as.numeric(values)
      if (!has_variation(numeric_values)) {
        notes <- c(notes, paste(field, "has no usable binary variation; term removed."))
        next
      }
      valid <- valid & !is.na(numeric_values)
      frame[[field]] <- numeric_values
      active_terms <- c(active_terms, field)
      term_info[[field]] <- list(kind = term$kind, reference = "0")
    } else if (identical(term$kind, "continuous")) {
      numeric_values <- as.numeric(values)
      if (!has_variation(numeric_values)) {
        notes <- c(notes, paste(field, "has no usable continuous variation; term removed."))
        next
      }
      valid <- valid & !is.na(numeric_values)
      center <- mean(numeric_values[!is.na(numeric_values)])
      scale <- stats::sd(numeric_values[!is.na(numeric_values)])
      if (is.na(scale) || scale == 0) {
        scale <- 1
      }
      frame[[field]] <- (numeric_values - center) / scale
      transformations <- c(transformations, paste(field, "scaled as (value -", signif(center, 8), ") /", signif(scale, 8)))
      active_terms <- c(active_terms, field)
      term_info[[field]] <- list(kind = term$kind, reference = "mean_centered_scaled")
    }
  }

  model_frame <- frame[valid, , drop = FALSE]
  formula_text <- if (length(active_terms) == 0) {
    "admit ~ 1"
  } else {
    paste("admit ~", paste(active_terms, collapse = " + "))
  }
  list(
    frame = model_frame,
    formula = stats::as.formula(formula_text),
    active_terms = active_terms,
    term_info = term_info,
    notes = notes,
    transformations = transformations
  )
}

parse_coefficient <- function(coef_name, term_info) {
  if (identical(coef_name, "(Intercept)")) {
    return(list(term = "intercept", level = ""))
  }
  term_names <- names(term_info)
  term_names <- term_names[order(nchar(term_names), decreasing = TRUE)]
  for (term_name in term_names) {
    if (startsWith(coef_name, term_name)) {
      suffix <- substring(coef_name, nchar(term_name) + 1)
      kind <- term_info[[term_name]]$kind
      if (identical(kind, "categorical")) {
        return(list(term = term_name, level = suffix))
      }
      if (identical(kind, "continuous")) {
        return(list(term = term_name, level = "scaled"))
      }
      return(list(term = term_name, level = "1"))
    }
  }
  list(term = coef_name, level = "")
}

coefficient_label <- function(parsed) {
  if (identical(parsed$level, "")) {
    return(parsed$term)
  }
  paste0(parsed$term, "[", parsed$level, "]")
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
    seed = RANDOM_SEED,
    stringsAsFactors = FALSE
  )
}

fit_one_model <- function(binary, spec) {
  prepared <- prepare_model_frame(binary, spec)
  model_frame <- prepared$frame
  if (nrow(model_frame) == 0 || length(unique(model_frame$admit)) < 2) {
    return(list(
      coefficients = empty_coefficients(),
      covariance = empty_covariance(),
      draws = empty_draws(),
      calibration = data.frame(
        model_id = spec$model_id,
        dataset = DATASET,
        n = nrow(model_frame),
        events = if (nrow(model_frame) > 0) sum(model_frame$admit) else 0,
        observed_prevalence = NA_real_,
        mean_predicted = NA_real_,
        calibration_in_the_large = NA_real_,
        calibration_slope = NA_real_,
        brier_score = NA_real_,
        auroc = NA_real_,
        pass_fail_status = "blocked",
        notes = "No usable binary outcome variation after model-specific filtering.",
        stringsAsFactors = FALSE
      ),
      deciles = empty_deciles(),
      notes = c(prepared$notes, "No usable binary outcome variation after model-specific filtering."),
      transformations = prepared$transformations
    ))
  }

  design <- survey::svydesign(
    ids = ~psu,
    strata = ~stratum,
    weights = ~weight,
    nest = TRUE,
    data = model_frame
  )
  fit <- survey::svyglm(prepared$formula, design = design, family = quasibinomial())
  coef_table <- summary(fit)$coefficients
  beta <- stats::coef(fit)
  covariance <- stats::vcov(fit)
  parsed_terms <- lapply(names(beta), parse_coefficient, term_info = prepared$term_info)
  labels <- vapply(parsed_terms, coefficient_label, character(1))

  limitation_note <- paste(
    c(
      "Survey-weighted candidate via survey::svyglm; dataset_derived promotion still requires all evidence gates.",
      prepared$notes
    ),
    collapse = " "
  )
  se <- sqrt(pmax(diag(covariance), 0))
  p_values <- coef_table[, ncol(coef_table)]
  coefficients <- data.frame(
    model_id = spec$model_id,
    dataset = DATASET,
    term = vapply(parsed_terms, function(item) item$term, character(1)),
    level = vapply(parsed_terms, function(item) item$level, character(1)),
    beta = as.numeric(beta),
    se = as.numeric(se),
    odds_ratio = exp(as.numeric(beta)),
    ci_low = exp(as.numeric(beta) - 1.96 * as.numeric(se)),
    ci_high = exp(as.numeric(beta) + 1.96 * as.numeric(se)),
    p_value = as.numeric(p_values),
    evidence_tier = "survey_weighted_candidate",
    limitation_note = limitation_note,
    stringsAsFactors = FALSE
  )

  covariance_rows <- empty_covariance()
  for (row_index in seq_along(labels)) {
    for (column_index in seq_along(labels)) {
      covariance_rows <- rbind(
        covariance_rows,
        data.frame(
          model_id = spec$model_id,
          dataset = DATASET,
          row_term = labels[[row_index]],
          column_term = labels[[column_index]],
          covariance = covariance[row_index, column_index],
          stringsAsFactors = FALSE
        )
      )
    }
  }

  predicted <- as.numeric(stats::predict(fit, type = "response"))
  y <- model_frame$admit
  weight <- model_frame$weight
  observed <- weighted_mean(y, weight)
  mean_predicted <- weighted_mean(predicted, weight)
  linear_prediction <- logit(predicted)
  model_frame$.__linear_prediction <- linear_prediction
  model_frame$.__predicted <- predicted
  calibration_design <- survey::svydesign(
    ids = ~psu,
    strata = ~stratum,
    weights = ~weight,
    nest = TRUE,
    data = model_frame
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
    n = nrow(model_frame),
    events = events,
    observed_prevalence = observed,
    mean_predicted = mean_predicted,
    calibration_in_the_large = calibration_intercept,
    calibration_slope = calibration_slope,
    brier_score = brier,
    auroc = auroc,
    pass_fail_status = calibration_status(calibration_slope, observed, mean_predicted, events),
    notes = paste(c("Survey-weighted apparent calibration using Taylor-linearized fit.", prepared$notes), collapse = " "),
    stringsAsFactors = FALSE
  )

  order_index <- order(predicted)
  cumulative_weight <- cumsum(weight[order_index])
  decile <- rep(NA_integer_, length(predicted))
  decile[order_index] <- pmin(10L, pmax(1L, ceiling(cumulative_weight / sum(weight) * 10L)))
  deciles <- empty_deciles()
  for (group in sort(unique(decile))) {
    subset <- decile == group
    observed_rate <- weighted_mean(y[subset], weight[subset])
    ci <- normal_ci(observed_rate, sum(subset))
    deciles <- rbind(
      deciles,
      data.frame(
        model_id = spec$model_id,
        dataset = DATASET,
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
    coefficients = coefficients,
    covariance = covariance_rows,
    draws = mvn_draws(spec$model_id, beta, covariance, parsed_terms),
    calibration = calibration,
    deciles = deciles,
    notes = prepared$notes,
    transformations = prepared$transformations
  )
}

pain_monotonicity <- function(binary) {
  rows <- empty_pain()
  rates <- c(mild = NA_real_, moderate = NA_real_, severe = NA_real_)
  for (level in names(rates)) {
    subset <- binary$pain_bin3 == level
    subset[is.na(subset)] <- FALSE
    if (any(subset)) {
      rates[[level]] <- weighted_mean(binary$admit[subset], binary$weight[subset])
    }
  }
  nondecreasing <- all(is.finite(rates)) && rates[["mild"]] <= rates[["moderate"]] && rates[["moderate"]] <= rates[["severe"]]
  pain_missing_fraction <- mean(as.numeric(binary$pain_missing), na.rm = TRUE)
  total_events <- sum(binary$admit)
  if (total_events < 100) {
    verdict <- "exploratory_only"
    reason <- "Total admission events <100; monotonic pain claim is exploratory only."
  } else if (pain_missing_fraction > 0.40) {
    verdict <- "missingness_invalidates_inference"
    reason <- "Pain missingness exceeds 40% of the analytic cohort."
  } else if (!nondecreasing) {
    verdict <- "nonmonotonic_flexible_only"
    reason <- "Weighted unadjusted pain-bin admission rates are not nondecreasing."
  } else {
    verdict <- "null_or_unstable"
    reason <- "Unadjusted rates are compatible, but full adjusted, calibration, and replication gates are not established by this script alone."
  }
  rbind(
    rows,
    data.frame(
      dataset = DATASET,
      mild_admit_rate = rates[["mild"]],
      moderate_admit_rate = rates[["moderate"]],
      severe_admit_rate = rates[["severe"]],
      nhamcs_unadjusted_nondecreasing = tolower(as.character(nondecreasing)),
      pain_missing_fraction = pain_missing_fraction,
      total_admission_events = total_events,
      verdict = verdict,
      reason = reason,
      stringsAsFactors = FALSE
    )
  )
}

json_escape <- function(value) {
  value <- gsub("\\\\", "\\\\\\\\", value)
  value <- gsub('"', '\\"', value, fixed = TRUE)
  value <- gsub("\n", "\\n", value, fixed = TRUE)
  value
}

to_json <- function(value) {
  if (is.null(value)) {
    return("null")
  }
  if (is.logical(value)) {
    return(ifelse(value, "true", "false"))
  }
  if (is.numeric(value) || is.integer(value)) {
    if (length(value) == 0) {
      return("[]")
    }
    return(paste(ifelse(is.na(value), "null", as.character(value)), collapse = ", "))
  }
  if (is.character(value)) {
    if (length(value) == 1) {
      return(paste0('"', json_escape(value), '"'))
    }
    return(paste0("[", paste(vapply(value, to_json, character(1)), collapse = ", "), "]"))
  }
  if (is.list(value)) {
    if (is.null(names(value))) {
      return(paste0("[", paste(vapply(value, to_json, character(1)), collapse = ", "), "]"))
    }
    pairs <- vapply(
      names(value),
      function(name) paste0('"', json_escape(name), '": ', to_json(value[[name]])),
      character(1)
    )
    return(paste0("{", paste(pairs, collapse = ", "), "}"))
  }
  paste0('"', json_escape(as.character(value)), '"')
}

write_metadata <- function(model_results) {
  metadata <- list(
    run_id = format(Sys.time(), "%Y%m%d%H%M%S"),
    generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
    dataset = DATASET,
    model_status = "survey_weighted_candidate",
    random_seed = RANDOM_SEED,
    draw_count = DRAW_COUNT,
    fitting_method = "survey_weighted_quasibinomial_logistic_svyglm",
    variance_method = "Taylor linearization via R survey::svyglm; options(survey.lonely.psu='adjust')",
    survey_design = list(
      weight = "pooled_weight = PATWT / number_of_years mapped to weight",
      stratum = "pooled_stratum = interaction(year, CSTRATM) mapped to stratum",
      psu = "pooled_psu = interaction(year, CPSUM) mapped to psu",
      variance_method = "Taylor linearization"
    ),
    survey_status = list(
      survey_weighted_primary_status = "completed_candidate_pending_gates",
      r_home = environment_status$r_home,
      r_version = environment_status$r_version,
      survey_version = as.character(utils::packageVersion("survey")),
      active_library_paths = environment_status$active_library_paths
    ),
    software = list(
      r = environment_status$r_version,
      survey = as.character(utils::packageVersion("survey"))
    ),
    model_specs = lapply(MODEL_SPECS, function(spec) list(model_id = spec$model_id, formula = spec$formula)),
    reference_categories = list(age_band = "30_44", pain_bin3 = "moderate"),
    transformations = unique(unlist(lapply(model_results, function(result) result$transformations))),
    sparse_cell_notes = sparse_notes(binary),
    event_count_gate = list(threshold = 100L, events = sum(binary$admit), passed = sum(binary$admit) >= 100),
    no_dataset_derived_promotion = TRUE,
    no_v4_adoption_claim = TRUE
  )
  writeLines(to_json(metadata), file.path(output_dir, "model_run_metadata.json"), useBytes = TRUE)
}

sparse_notes <- function(binary) {
  notes <- character()
  for (field in c("age_band", "pain_bin3")) {
    if (!field %in% names(binary)) {
      next
    }
    levels <- unique(binary[[field]][!is.na(binary[[field]])])
    for (level in levels) {
      subset <- binary[[field]] == level
      subset[is.na(subset)] <- FALSE
      events <- sum(binary$admit[subset])
      if (events < 10) {
        notes <- c(notes, paste(field, "level", level, "has <10 admission events; outputs remain candidate/exploratory for that level."))
      }
    }
  }
  if (sum(binary$admit) < 100) {
    notes <- c(notes, "Total admission events <100; outputs are exploratory candidates, not narrow-SE adoption evidence.")
  }
  notes
}

all_coefficients <- empty_coefficients()
all_covariance <- empty_covariance()
all_draws <- empty_draws()
all_calibration <- empty_calibration()
all_deciles <- empty_deciles()
model_results <- list()

for (spec in MODEL_SPECS) {
  result <- fit_one_model(binary, spec)
  model_results[[spec$model_id]] <- result
  all_coefficients <- rbind(all_coefficients, result$coefficients)
  all_covariance <- rbind(all_covariance, result$covariance)
  all_draws <- rbind(all_draws, result$draws)
  all_calibration <- rbind(all_calibration, result$calibration)
  all_deciles <- rbind(all_deciles, result$deciles)
}

utils::write.csv(all_coefficients, file.path(output_dir, "coefficients.csv"), row.names = FALSE, na = "")
utils::write.csv(all_covariance, file.path(output_dir, "covariance_matrix.csv"), row.names = FALSE, na = "")
utils::write.csv(all_draws, file.path(output_dir, "mvn_coefficient_draws.csv"), row.names = FALSE, na = "")
utils::write.csv(all_calibration, file.path(output_dir, "calibration_metrics.csv"), row.names = FALSE, na = "")
utils::write.csv(all_deciles, file.path(output_dir, "calibration_by_decile.csv"), row.names = FALSE, na = "")
utils::write.csv(pain_monotonicity(binary), file.path(output_dir, "pain_monotonicity.csv"), row.names = FALSE, na = "")
write_metadata(model_results)

cat("Wrote survey-weighted NHAMCS candidate outputs to ", output_dir, "\n", sep = "")


