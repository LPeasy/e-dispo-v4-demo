#!/usr/bin/env python3
"""Shared calibration pass/fail decisions for empirical model outputs."""

from __future__ import annotations

import math
from typing import Any


ACCEPTABLE_SLOPE_LOW = 0.8
ACCEPTABLE_SLOPE_HIGH = 1.2
INTERCEPT_ABS_THRESHOLD = 0.02
INTERCEPT_REL_THRESHOLD = 0.10


def to_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return number if math.isfinite(number) else float("nan")


def calibration_decision(row: dict[str, Any]) -> dict[str, str]:
    """Classify one calibration_metrics.csv row."""

    observed = to_float(row.get("observed_prevalence"))
    predicted = to_float(row.get("mean_predicted"))
    slope = to_float(row.get("calibration_slope"))
    brier = to_float(row.get("brier_score"))
    blockers: list[str] = []
    warnings: list[str] = []

    if not math.isfinite(slope):
        blockers.append("calibration_slope_missing")
        slope_status = "missing"
    elif slope < ACCEPTABLE_SLOPE_LOW:
        blockers.append("calibration_slope_below_0.8_overfit_or_extreme_predictions")
        slope_status = "overfit_or_extreme_predictions"
    elif slope > ACCEPTABLE_SLOPE_HIGH:
        blockers.append("calibration_slope_above_1.2_underfit_or_weak_predictions")
        slope_status = "underfit_or_weak_predictions"
    else:
        slope_status = "acceptable_candidate_range"

    if not math.isfinite(observed) or not math.isfinite(predicted):
        blockers.append("observed_or_mean_predicted_missing")
        intercept_status = "missing"
    else:
        absolute_error = abs(predicted - observed)
        relative_error = absolute_error / max(abs(observed), 1e-9)
        if absolute_error > INTERCEPT_ABS_THRESHOLD or relative_error > INTERCEPT_REL_THRESHOLD:
            blockers.append("mean_predicted_differs_from_observed_recalibrate_intercept")
            intercept_status = "needs_intercept_recalibration"
        else:
            intercept_status = "acceptable"

    if not math.isfinite(brier):
        warnings.append("brier_score_missing")

    status = "pass" if not blockers else "fail"
    return {
        "model_id": str(row.get("model_id", "")),
        "dataset": str(row.get("dataset", "")),
        "validation_scope": str(row.get("validation_scope", "apparent")),
        "calibration_status": status,
        "slope_status": slope_status,
        "intercept_status": intercept_status,
        "blockers": "; ".join(blockers),
        "warnings": "; ".join(warnings),
    }


def summarize_calibration(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [calibration_decision(row) for row in rows]


def model_metric(rows: list[dict[str, Any]], model_id: str, field: str) -> float:
    for row in rows:
        if str(row.get("model_id")) == model_id:
            return to_float(row.get(field))
    return float("nan")


def pain_worsens_calibration(rows: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """Detect whether pain model is worse than flexible or no-pain alternatives."""

    reasons: list[str] = []
    pain_brier = model_metric(rows, "A_reduced_categorical", "brier_score")
    pain_slope = model_metric(rows, "A_reduced_categorical", "calibration_slope")
    no_pain_brier = model_metric(rows, "D_no_pain_comparator", "brier_score")
    no_pain_slope = model_metric(rows, "D_no_pain_comparator", "calibration_slope")

    flexible_brier = model_metric(rows, "C_flexible_v4_exploratory", "brier_score")
    if not math.isfinite(flexible_brier):
        flexible_brier = model_metric(rows, "C_continuous_pain_exploratory", "brier_score")

    if math.isfinite(pain_brier) and math.isfinite(no_pain_brier) and pain_brier > no_pain_brier + 0.002:
        reasons.append("pain_model_brier_worse_than_no_pain")
    if math.isfinite(pain_brier) and math.isfinite(flexible_brier) and pain_brier > flexible_brier + 0.002:
        reasons.append("pain_model_brier_worse_than_flexible")
    if math.isfinite(pain_slope) and math.isfinite(no_pain_slope):
        if abs(pain_slope - 1.0) > abs(no_pain_slope - 1.0) + 0.05:
            reasons.append("pain_model_calibration_slope_worse_than_no_pain")
    return bool(reasons), reasons

