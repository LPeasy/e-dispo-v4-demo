#!/usr/bin/env python3
"""Shared pain monotonicity decision logic."""

from __future__ import annotations

import math
from typing import Any

import calibration


LOW = "0-3"
MODERATE = "4-6"
SEVERE = "7-10"
PAIN_ORDER = [LOW, MODERATE, SEVERE]
MATERIAL_REVERSAL = 0.02
TRIVIAL_COEFFICIENT_VIOLATION = 0.05
MISSINGNESS_BLOCK = 40.0


def normalize_pain_bin(value: Any) -> str:
    text = str(value).strip().lower()
    mapping = {
        "0-3": LOW,
        "low": LOW,
        "mild": LOW,
        "4-6": MODERATE,
        "moderate": MODERATE,
        "7-10": SEVERE,
        "severe": SEVERE,
        "high": SEVERE,
    }
    return mapping.get(text, text)


def to_float(value: Any) -> float:
    return calibration.to_float(value)


def dataset_rates(rows: list[dict[str, Any]], dataset: str) -> dict[str, float]:
    rates: dict[str, float] = {}
    for row in rows:
        if dataset and str(row.get("dataset")) != dataset:
            continue
        pain_bin = normalize_pain_bin(row.get("pain_bin"))
        if pain_bin not in PAIN_ORDER:
            continue
        weighted_events = to_float(row.get("weighted_events"))
        weighted_n = to_float(row.get("weighted_n"))
        if dataset == "NHAMCS_2022" and math.isfinite(weighted_events) and math.isfinite(weighted_n) and weighted_n > 0:
            rate = weighted_events / weighted_n
        else:
            rate = to_float(row.get("admit_pct"))
            if math.isfinite(rate):
                rate = rate / 100.0 if rate > 1 else rate
            else:
                events = to_float(row.get("events"))
                n = to_float(row.get("n"))
                rate = events / n if math.isfinite(events) and math.isfinite(n) and n > 0 else float("nan")
        rates[pain_bin] = rate
    return rates


def nondecreasing(rates: dict[str, float], tolerance: float = 0.0) -> bool:
    if not all(math.isfinite(rates.get(level, float("nan"))) for level in PAIN_ORDER):
        return False
    return rates[LOW] <= rates[MODERATE] + tolerance and rates[MODERATE] <= rates[SEVERE] + tolerance


def material_reversal_absent(rates: dict[str, float]) -> bool:
    if not all(math.isfinite(rates.get(level, float("nan"))) for level in PAIN_ORDER):
        return False
    return rates[LOW] <= rates[MODERATE] + MATERIAL_REVERSAL and rates[MODERATE] <= rates[SEVERE] + MATERIAL_REVERSAL


def rate_sequence_status(rates: dict[str, float], allow_material_tolerance: bool = False) -> str:
    finite_levels = [level for level in PAIN_ORDER if math.isfinite(rates.get(level, float("nan")))]
    if not finite_levels:
        return "no_data"
    if len(finite_levels) < len(PAIN_ORDER):
        return "insufficient_bins"
    if allow_material_tolerance:
        return "no_material_reversal" if material_reversal_absent(rates) else "material_reversal"
    return "nondecreasing" if nondecreasing(rates) else "not_nondecreasing"


def adjusted_pain_order(
    coefficients: list[dict[str, Any]],
    model_id: str = "A_reduced_categorical",
    dataset: str = "NHAMCS_2022",
) -> dict[str, Any]:
    """Check moderate/reference/severe adjusted ordering for categorical pain."""

    moderate_beta = 0.0
    moderate_low = 0.0
    moderate_high = 0.0
    severe = None
    mild = None
    for row in coefficients:
        if dataset and str(row.get("dataset")) != dataset:
            continue
        if str(row.get("model_id")) != model_id or str(row.get("term")) != "pain_bin3":
            continue
        level = str(row.get("level", "")).lower()
        item = {
            "beta": to_float(row.get("beta")),
            "low": to_float(row.get("ci_low")),
            "high": to_float(row.get("ci_high")),
            "se": to_float(row.get("se")),
        }
        if level in {"severe", "7-10", "high"}:
            severe = item
        elif level in {"mild", "low", "0-3"}:
            mild = item

    if severe is None:
        return {"ok": False, "status": "missing_severe_coefficient", "severe_beta": "", "moderate_beta": 0.0}

    severe_beta = severe["beta"]
    if not math.isfinite(severe_beta):
        return {"ok": False, "status": "invalid_severe_coefficient", "severe_beta": "", "moderate_beta": 0.0}

    severe_vs_moderate_ok = severe_beta >= moderate_beta
    severe_overlap = False
    if math.isfinite(severe.get("low", float("nan"))):
        # ci_low/ci_high in current files are odds-ratio CI. Fall back to beta +/- 1.96 SE when SE exists.
        pass
    if math.isfinite(severe.get("se", float("nan"))):
        severe_low_beta = severe_beta - 1.96 * severe["se"]
        severe_overlap = severe_low_beta <= moderate_high

    trivial = severe_beta >= moderate_beta - TRIVIAL_COEFFICIENT_VIOLATION and severe_overlap
    mild_ok = True
    mild_status = "missing_low_coefficient_allowed"
    if mild is not None and math.isfinite(mild["beta"]):
        mild_ok = mild["beta"] <= moderate_beta + TRIVIAL_COEFFICIENT_VIOLATION
        mild_status = "ok" if mild_ok else "low_above_reference"

    ok = (severe_vs_moderate_ok or trivial) and mild_ok
    status = "ok" if ok else "adjusted_order_violation"
    return {
        "ok": ok,
        "status": status,
        "mild_status": mild_status,
        "severe_beta": severe_beta,
        "moderate_beta": moderate_beta,
    }


def continuous_pain_signal(coefficients: list[dict[str, Any]], model_id: str) -> dict[str, Any]:
    for row in coefficients:
        if str(row.get("model_id")) == model_id and str(row.get("term")) == "pain_score":
            beta = to_float(row.get("beta"))
            se = to_float(row.get("se"))
            if not math.isfinite(beta):
                return {"present": False, "positive": False, "beta": ""}
            if math.isfinite(se):
                return {"present": True, "positive": beta > 0 and beta + 1.96 * se > 0, "beta": beta}
            return {"present": True, "positive": beta > 0, "beta": beta}
    return {"present": False, "positive": False, "beta": ""}


def pain_missingness_blocks(rows: list[dict[str, Any]], dataset: str = "") -> tuple[bool, float]:
    numerator = 0.0
    denominator = 0.0
    weighted_numerator = 0.0
    weighted_denominator = 0.0
    explicit_percentages: list[float] = []
    for row in rows:
        if dataset and str(row.get("dataset")) != dataset:
            continue
        field = str(row.get("field", ""))
        endpoint = str(row.get("endpoint", ""))
        if field not in {"pain_score", "pain_bin3"}:
            continue
        if endpoint not in {"admit", "routine_home_discharge", ""}:
            continue
        n = to_float(row.get("n"))
        missing = to_float(row.get("missing_n"))
        if math.isfinite(n) and math.isfinite(missing):
            denominator += n
            numerator += missing
        weighted_n = to_float(row.get("weighted_n"))
        weighted_missing = to_float(row.get("weighted_missing_n"))
        if math.isfinite(weighted_n) and math.isfinite(weighted_missing):
            weighted_denominator += weighted_n
            weighted_numerator += weighted_missing
        explicit_pct = to_float(row.get("weighted_missing_pct"))
        if not math.isfinite(explicit_pct):
            explicit_pct = to_float(row.get("missing_pct"))
        if math.isfinite(explicit_pct):
            explicit_percentages.append(explicit_pct)

    candidate_percentages: list[float] = []
    if denominator > 0:
        candidate_percentages.append(100.0 * numerator / denominator)
    if weighted_denominator > 0:
        candidate_percentages.append(100.0 * weighted_numerator / weighted_denominator)
    candidate_percentages.extend(explicit_percentages)
    finite_percentages = [value for value in candidate_percentages if math.isfinite(value)]
    if not finite_percentages:
        return False, float("nan")
    missing_pct = max(finite_percentages)
    return missing_pct > MISSINGNESS_BLOCK, missing_pct


def decide_pain(
    pain_rates: list[dict[str, Any]],
    coefficients: list[dict[str, Any]],
    calibration_rows: list[dict[str, Any]],
    missingness_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    nhamcs_rates = dataset_rates(pain_rates, "NHAMCS_2022")
    mimic_rates = dataset_rates(pain_rates, "MIMIC_IV_ED")
    nhamcs_status = rate_sequence_status(nhamcs_rates)
    mimic_status = rate_sequence_status(mimic_rates, allow_material_tolerance=True)
    nhamcs_ok = nhamcs_status == "nondecreasing"
    mimic_ok = mimic_status in {"no_data", "no_material_reversal"}
    adjusted = adjusted_pain_order(coefficients)
    symptom_signal = continuous_pain_signal(coefficients, "C_continuous_pain_exploratory")
    if not symptom_signal["present"]:
        symptom_signal = continuous_pain_signal(coefficients, "B_objective_severity")
    acuity_signal = continuous_pain_signal(coefficients, "B_reduced_plus_acuity_vitals")
    if not acuity_signal["present"]:
        acuity_signal = continuous_pain_signal(coefficients, "B_objective_severity")

    missing_block, missing_pct = pain_missingness_blocks(missingness_rows)
    calibration_decisions = calibration.summarize_calibration(calibration_rows)
    calibration_blocks = [row for row in calibration_decisions if row["calibration_status"] == "fail"]
    pain_worse, pain_worse_reasons = calibration.pain_worsens_calibration(calibration_rows)

    blockers: list[str] = []
    if not nhamcs_ok:
        blockers.append(f"nhamcs_unadjusted_rates_{nhamcs_status}")
    if not mimic_ok:
        blockers.append(f"mimic_{mimic_status}")
    if not adjusted["ok"]:
        blockers.append(str(adjusted["status"]))
    if not symptom_signal["positive"]:
        blockers.append("pain_no_positive_signal_after_age_vomiting_fever_temp")
    if missing_block:
        blockers.append("pain_missingness_exceeds_40_percent")
    if calibration_blocks:
        blockers.append("calibration_failure")
    if pain_worse:
        blockers.extend(pain_worse_reasons)

    if missing_block:
        verdict = "missingness_invalidates_inference"
    elif calibration_blocks or pain_worse:
        verdict = "null_or_unstable"
    elif not nhamcs_ok or not mimic_ok or not adjusted["ok"]:
        verdict = "nonmonotonic_flexible_only"
    elif not symptom_signal["positive"]:
        verdict = "null_or_unstable"
    elif symptom_signal["positive"] and acuity_signal["present"] and not acuity_signal["positive"]:
        verdict = "dataset_derived_weak_severity_proxy"
    else:
        verdict = "monotonic_dataset_derived"

    return {
        "predictor": "pain",
        "verdict": verdict,
        "nhamcs_unadjusted_nondecreasing": str(nhamcs_ok).lower(),
        "nhamcs_pain_rates_status": nhamcs_status,
        "mimic_no_material_reversal": str(mimic_ok).lower(),
        "mimic_pain_rates_status": mimic_status,
        "adjusted_order_ok": str(adjusted["ok"]).lower(),
        "pain_signal_after_symptom_context": str(symptom_signal["positive"]).lower(),
        "pain_signal_after_acuity_vitals": str(acuity_signal["positive"]).lower() if acuity_signal["present"] else "not_evaluated",
        "missingness_pct": "" if not math.isfinite(missing_pct) else str(round(missing_pct, 6)),
        "calibration_blocks": str(bool(calibration_blocks or pain_worse)).lower(),
        "blockers": "; ".join(blockers),
    }
