#!/usr/bin/env Rscript

# Full-source non-trauma admission model candidate.
#
# This is a reviewer/development artifact only. It fits the compact
# e-dispo-style predictor surface on the broader non-trauma NHAMCS source
# cohort. It does not replace or update active e-dispo-v4.0.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: nhamcs_full_source_nontrauma_admit_model.R <full_source_nontrauma_cohort_csv> <output_dir>")
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
MODEL_ID <- "e-dispo-v4.1-full-source-nontrauma-admit"
AGE_CENTER <- 42

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

parse_coefficient <- function(name) {
  if (identical(name, "(Intercept)")) return(list(term = "intercept", level = ""))
  if (identical(name, "age_centered")) return(list(term = "age_centered", level = "per_1_year_centered_at_42"))
  if (identical(name, "pain_severe")) return(list(term = "pain_severe", level = "1"))
  if (identical(name, "fever_or_temp")) return(list(term = "fever_or_temp", level = "1"))
  if (identical(name, "vomiting_present")) return(list(term = "vomiting_present", level = "1"))
  if (identical(name, "tachycardia_burden")) return(list(term = "tachycardia_burden", level = "per_10_bpm_over_100"))
  list(term = name, level = "")
}

coefficient_label <- function(parsed) {
  if (identical(parsed$level, "")) parsed$term else paste0(parsed$term, "[", parsed$level, "]")
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
    model_id = MODEL_ID, dataset = DATASET, target = "admit_vs_home",
    source_scope = "full_source_nontrauma", n = input_n, events = input_events,
    non_events = input_n - input_events, model_estimable_n = 0L,
    model_estimable_events = 0L, weighted_n = NA_real_,
    weighted_events = NA_real_, observed_prevalence = NA_real_,
    mean_predicted = NA_real_, auroc = NA_real_, brier_score = NA_real_,
    formula = "admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden",
    method = "blocked", status = "blocked_not_fit", limitation = reason,
    stringsAsFactors = FALSE
  )
  calibration <- data.frame(
    model_id = MODEL_ID, dataset = DATASET, target = "admit_vs_home",
    source_scope = "full_source_nontrauma", n = input_n, events = input_events,
    observed_prevalence = NA_real_, mean_predicted = NA_real_,
    calibration_in_the_large = NA_real_, calibration_slope = NA_real_,
    method = "blocked", status = "blocked_not_fit", limitation = reason,
    stringsAsFactors = FALSE
  )
  utils::write.csv(coefficients, file.path(output_dir, "full_source_nontrauma_admit_model_coefficients.csv"), row.names = FALSE, na = "")
  utils::write.csv(covariance, file.path(output_dir, "full_source_nontrauma_admit_model_covariance.csv"), row.names = FALSE, na = "")
  utils::write.csv(performance, file.path(output_dir, "full_source_nontrauma_admit_model_performance.csv"), row.names = FALSE, na = "")
  utils::write.csv(calibration, file.path(output_dir, "full_source_nontrauma_admit_model_calibration.csv"), row.names = FALSE, na = "")
  writeLines(c(
    "# Full-Source Non-Trauma Admission Candidate Model",
    "",
    paste0("Status: `blocked_not_fit`."),
    "",
    "## Blocker",
    paste0("- ", reason),
    "",
    "No coefficient or performance estimate should be inferred from blocked rows.",
    ""
  ), con = file.path(output_dir, "full_source_nontrauma_admit_model_report.md"))
}

cohort <- read.csv(input_path, stringsAsFactors = FALSE, na.strings = c("", "NA", "NaN"))
required <- c("endpoint_class", "admit", "year", "age", "pain_bin3", "pain_missing",
              "fever_or_temp", "vomiting_present", "HR", "tachycardia_burden",
              "pooled_weight", "pooled_stratum", "pooled_psu")
missing_required <- setdiff(required, names(cohort))
if (length(missing_required) > 0) {
  write_blocker_outputs(paste("Missing required columns:", paste(missing_required, collapse = ", ")))
  quit(status = 2)
}

binary <- cohort[cohort$endpoint_class %in% c("admit", "routine_home_discharge"), , drop = FALSE]
binary$admit <- as.numeric(binary$endpoint_class == "admit")
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

input_n <- nrow(binary)
input_events <- sum(binary$admit == 1)
if (input_n == 0 || input_events == 0 || sum(binary$admit == 0) == 0) {
  write_blocker_outputs("No usable admit-vs-home denominator after full-source non-trauma endpoint filtering.", input_n, input_events)
  quit(status = 2)
}

complete_case <- binary[binary$pain_missing == 0 &
  !is.na(binary$pain_bin3) & !is.na(binary$fever_or_temp) &
  !is.na(binary$vomiting_present) & !is.na(binary$HR) &
  !is.na(binary$tachycardia_burden), , drop = FALSE]

if (nrow(complete_case) == 0 || sum(complete_case$admit == 1) == 0 || sum(complete_case$admit == 0) == 0) {
  write_blocker_outputs("No usable complete-case rows with both outcomes for the compact predictor surface.", input_n, input_events)
  quit(status = 2)
}

complete_case$pain_severe <- as.numeric(as.character(complete_case$pain_bin3) == "severe")
formula <- admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden
design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = complete_case)
fit <- survey::svyglm(formula, design = design, family = quasibinomial())
beta <- stats::coef(fit)
covariance_matrix <- stats::vcov(fit)
se <- sqrt(pmax(diag(covariance_matrix), 0))
coef_table <- summary(fit)$coefficients
parsed_terms <- lapply(names(beta), parse_coefficient)
labels <- vapply(parsed_terms, coefficient_label, character(1))
predicted <- as.numeric(stats::predict(fit, type = "response"))

calibration_frame <- complete_case
calibration_frame$.__linear_prediction <- logit(predicted)
calibration_design <- survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = calibration_frame)
intercept_fit <- survey::svyglm(admit ~ 1 + offset(.__linear_prediction), design = calibration_design, family = quasibinomial())
slope_fit <- survey::svyglm(admit ~ .__linear_prediction, design = calibration_design, family = quasibinomial())

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
  evidence_tier = "survey_weighted_candidate",
  limitation_note = "Full-source non-trauma NHAMCS candidate model; reviewer/development artifact only, not active e-dispo-v4.0 and not external validation.",
  stringsAsFactors = FALSE
)

covariance_rows <- data.frame()
for (row_index in seq_along(labels)) {
  for (column_index in seq_along(labels)) {
    covariance_rows <- rbind(covariance_rows, data.frame(
      model_id = MODEL_ID,
      dataset = DATASET,
      row_term = labels[[row_index]],
      column_term = labels[[column_index]],
      covariance = covariance_matrix[row_index, column_index],
      stringsAsFactors = FALSE
    ))
  }
}

observed_prevalence <- weighted_mean(complete_case$admit, complete_case$weight)
mean_predicted <- weighted_mean(predicted, complete_case$weight)
performance <- data.frame(
  model_id = MODEL_ID,
  dataset = DATASET,
  target = "admit_vs_home",
  source_scope = "full_source_nontrauma",
  n = input_n,
  events = input_events,
  non_events = input_n - input_events,
  model_estimable_n = nrow(complete_case),
  model_estimable_events = sum(complete_case$admit == 1),
  weighted_n = sum(binary$weight),
  weighted_events = sum(binary$weight[binary$admit == 1]),
  observed_prevalence = observed_prevalence,
  mean_predicted = mean_predicted,
  auroc = weighted_auc(complete_case$admit, predicted, complete_case$weight),
  brier_score = weighted_mean((predicted - complete_case$admit) ^ 2, complete_case$weight),
  formula = "admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden",
  method = "survey::svyglm_quasibinomial_full_source_nontrauma_complete_case",
  status = "survey_weighted_candidate",
  limitation = "Candidate model on broader NHAMCS non-trauma source scope; no replacement of e-dispo-v4.0, no clinical-use claim, and no external-validation claim.",
  stringsAsFactors = FALSE
)

calibration <- data.frame(
  model_id = MODEL_ID,
  dataset = DATASET,
  target = "admit_vs_home",
  source_scope = "full_source_nontrauma",
  n = nrow(complete_case),
  events = sum(complete_case$admit == 1),
  observed_prevalence = observed_prevalence,
  mean_predicted = mean_predicted,
  calibration_in_the_large = as.numeric(stats::coef(intercept_fit)[[1]]),
  calibration_slope = as.numeric(stats::coef(slope_fit)[[".__linear_prediction"]]),
  method = "survey::svyglm_calibration_on_candidate_model_predictions",
  status = "survey_weighted_candidate",
  limitation = "Apparent calibration for candidate model only; no external validation or transportability claim.",
  stringsAsFactors = FALSE
)

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
  sex_lines <- c(
    sex_lines,
    paste0("- Rows that also satisfy the original adult-male age 18-64 flag: ", adult_male_count)
  )
}

utils::write.csv(coefficients, file.path(output_dir, "full_source_nontrauma_admit_model_coefficients.csv"), row.names = FALSE, na = "")
utils::write.csv(covariance_rows, file.path(output_dir, "full_source_nontrauma_admit_model_covariance.csv"), row.names = FALSE, na = "")
utils::write.csv(performance, file.path(output_dir, "full_source_nontrauma_admit_model_performance.csv"), row.names = FALSE, na = "")
utils::write.csv(calibration, file.path(output_dir, "full_source_nontrauma_admit_model_calibration.csv"), row.names = FALSE, na = "")

report <- c(
  "# Full-Source Non-Trauma Admission Candidate Model",
  "",
  paste0("Model ID: `", MODEL_ID, "`"),
  "Status: `survey_weighted_candidate`.",
  "",
  "## Method",
  "",
  "- Cohort: full-source NHAMCS 2018-2022 non-trauma ED records; no sex, age, or abdominal-pain gate is applied.",
  "- Target: same-hospital admission versus routine home discharge.",
  "- Formula: `admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden`.",
  "- Fit: survey-weighted quasibinomial logistic regression with pooled weights, strata, and PSUs.",
  "- Evidence boundary: reviewer/development artifact only; it does not replace active `e-dispo-v4.0`.",
  "",
  "## Counts",
  "",
  paste0("- Admit-vs-home denominator N: ", input_n),
  paste0("- Admission events before complete-case restriction: ", input_events),
  paste0("- Complete-case N: ", nrow(complete_case)),
  paste0("- Complete-case admission events: ", sum(complete_case$admit == 1)),
  sex_lines,
  "",
  "## Apparent Candidate Performance",
  "",
  paste0("- AUROC: ", round(performance$auroc[[1]], 6)),
  paste0("- Brier score: ", round(performance$brier_score[[1]], 6)),
  paste0("- Observed prevalence: ", round(observed_prevalence, 6)),
  paste0("- Mean predicted: ", round(mean_predicted, 6)),
  paste0("- Calibration-in-the-large: ", round(calibration$calibration_in_the_large[[1]], 6)),
  paste0("- Calibration slope: ", round(calibration$calibration_slope[[1]], 6)),
  "",
  "## Limitation",
  "",
  "This candidate model uses a broader all-sex/all-age NHAMCS non-trauma source scope and remains internal to NHAMCS. It is not external validation, transportability evidence, clinical decision support, or an active app model.",
  ""
)
writeLines(report, con = file.path(output_dir, "full_source_nontrauma_admit_model_report.md"))

cat("Wrote full-source non-trauma admission candidate model outputs under ", output_dir, "\n", sep = "")
