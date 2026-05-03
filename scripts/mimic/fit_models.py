#!/usr/bin/env python3
"""Fit MIMIC-IV-ED replication/proxy-validation models."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import build_cohort  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("outputs/mimic")
RANDOM_SEED = 20260428
DRAW_COUNT = 10000

MODEL_SPECS: list[dict[str, Any]] = [
    {
        "model_id": "A_reduced_categorical",
        "formula": "admit ~ age_band + pain_bin3 + pain_missing + vomiting + fever_or_temp",
        "terms": [
            ("categorical", "age_band", "30_44"),
            ("categorical", "pain_bin3", "moderate"),
            ("binary", "pain_missing", None),
            ("binary", "vomiting", None),
            ("binary", "fever_or_temp", None),
        ],
    },
    {
        "model_id": "B_objective_severity",
        "formula": "admit ~ age + acuity + pain_score + pain_missing + temp + HR + SBP + vomiting",
        "terms": [
            ("continuous", "age", None),
            ("continuous", "acuity", None),
            ("continuous", "pain_score", None),
            ("binary", "pain_missing", None),
            ("continuous", "temp", None),
            ("continuous", "HR", None),
            ("continuous", "SBP", None),
            ("binary", "vomiting", None),
        ],
    },
    {
        "model_id": "C_flexible_v4_exploratory",
        "formula": "admit ~ spline(age) + acuity + spline(pain_score) + pain_missing + spline(temp) + HR + SBP + vomiting",
        "terms": [
            ("spline", "age", None),
            ("continuous", "acuity", None),
            ("spline", "pain_score", None),
            ("binary", "pain_missing", None),
            ("spline", "temp", None),
            ("continuous", "HR", None),
            ("continuous", "SBP", None),
            ("binary", "vomiting", None),
        ],
    },
    {
        "model_id": "D_no_pain_comparator",
        "formula": "admit ~ age_band + vomiting + fever_or_temp",
        "terms": [
            ("categorical", "age_band", "30_44"),
            ("binary", "vomiting", None),
            ("binary", "fever_or_temp", None),
        ],
    },
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fit MIMIC-IV-ED replication models.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    args = parser.parse_args(argv)

    cohort_path = args.output_dir / "analytic_cohort_mimic.csv"
    if not cohort_path.exists():
        build_cohort.write_blocker_report(
            args.output_dir / "blocker_report.md",
            blockers=[f"Analytic cohort file is missing: {cohort_path}"],
            outputs_written=[],
            next_action="Run scripts/mimic/build_cohort.py before scripts/mimic/fit_models.py.",
        )
        return 2

    frame = pd.read_csv(cohort_path)
    results = fit_all_models(frame, args.output_dir)
    write_outputs(results, args.output_dir)
    print(f"Wrote MIMIC model outputs under {args.output_dir}")
    return 0


def fit_all_models(frame: pd.DataFrame, output_dir: Path) -> dict[str, Any]:
    binary = frame[frame["include_strict_binary"].astype(str).str.lower().isin(["true", "1"])].copy()
    if binary.empty:
        build_cohort.write_blocker_report(
            output_dir / "blocker_report.md",
            blockers=["Strict binary MIMIC analytic cohort is empty."],
            outputs_written=[],
            next_action="Review chief complaint, trauma, and endpoint mappings.",
        )
        return empty_results("empty_binary_cohort")

    run_status = "mimic_replication_not_national_derivation"
    sparse_notes = sparse_notes_for(binary)
    if int(binary["admit"].sum()) < 100:
        sparse_notes.append("Total admission events <100; outputs are exploratory.")
    if float(binary["pain_missing"].mean()) > 0.40:
        sparse_notes.append("Pain missingness exceeds 40%; complete-case pain analysis is sensitivity only.")

    coefficients: list[dict[str, Any]] = []
    covariance_rows: list[dict[str, Any]] = []
    draw_rows: list[dict[str, Any]] = []
    calibration_metrics: list[dict[str, Any]] = []
    calibration_deciles: list[dict[str, Any]] = []
    fitted_models: dict[str, dict[str, Any]] = {}

    for spec in MODEL_SPECS:
        fit_result = fit_model(binary, spec, sparse_notes)
        fitted_models[spec["model_id"]] = fit_result
        coefficients.extend(fit_result["coefficients"])
        covariance_rows.extend(fit_result["covariance_rows"])
        draw_rows.extend(fit_result["draw_rows"])
        calibration_metrics.extend(fit_result["calibration_metrics"])
        calibration_deciles.extend(fit_result["calibration_deciles"])

    pain_rows = pain_monotonicity_rows(binary)
    transportability = transportability_report(binary, output_dir)
    metadata = {
        "run_id": run_id(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": "MIMIC_IV_ED",
        "model_status": run_status,
        "random_seed": RANDOM_SEED,
        "draw_count": DRAW_COUNT,
        "draw_method": "normal_approximation_from_unweighted_covariance_not_bayesian_posterior",
        "fitting_method": "ridge_penalized_unweighted_logistic_irls",
        "uncertainty_note": "Patient-level split validation is written when feasible. Coefficient draws are covariance-normal approximations, not dataset-derived national coefficients.",
        "sparse_cell_notes": sparse_notes,
        "reference_categories": {"age_band": "30_44", "pain_bin3": "moderate"},
        "model_specs": [{"model_id": spec["model_id"], "formula": spec["formula"]} for spec in MODEL_SPECS],
        "transportability": transportability,
        "no_v4_adoption_claim": True,
    }
    return {
        "coefficients": coefficients,
        "covariance_rows": covariance_rows,
        "draw_rows": draw_rows,
        "calibration_metrics": calibration_metrics,
        "calibration_deciles": calibration_deciles,
        "pain_monotonicity": pain_rows,
        "metadata": metadata,
    }


def empty_results(reason: str) -> dict[str, Any]:
    return {
        "coefficients": [],
        "covariance_rows": [],
        "draw_rows": [],
        "calibration_metrics": [],
        "calibration_deciles": [],
        "pain_monotonicity": [{"dataset": "MIMIC_IV_ED", "verdict": "exploratory_only", "reason": reason}],
        "metadata": {"model_status": "blocked", "reason": reason},
    }


def sparse_notes_for(binary: pd.DataFrame) -> list[str]:
    notes: list[str] = []
    for field in ["age_band", "pain_bin3"]:
        if field in binary.columns:
            for level, subset in binary.groupby(field, dropna=False):
                if int(subset["admit"].sum()) < 10:
                    notes.append(f"{field} level {level} has <10 admission events; ridge penalization used and output labeled exploratory.")
    for field in ["vomiting", "fever_or_temp"]:
        if field in binary.columns:
            positives = binary[binary[field] == 1]
            if len(positives) > 0 and int(positives["admit"].sum()) < 10:
                notes.append(f"{field} positives have <10 admission events; term is descriptive/proxy-only.")
    return notes


def fit_model(binary: pd.DataFrame, spec: dict[str, Any], sparse_notes: list[str]) -> dict[str, Any]:
    design = build_design(binary, spec)
    y = binary.loc[design["row_mask"], "admit"].astype(float).to_numpy()
    subjects = binary.loc[design["row_mask"], "subject_id"].astype(str).to_numpy()
    x = design["matrix"]
    if len(y) == 0 or len(np.unique(y)) < 2:
        return blocked_model_result(spec, "No usable outcome variation.")
    fit = logistic_fit(x, y)
    predicted = logistic_np(x @ fit["beta"])
    limitation = "; ".join(design["notes"] + sparse_notes + ["MIMIC is replication/proxy-validation only and cannot promote national dataset-derived status alone."])
    coefficients = coefficient_rows(spec["model_id"], design["terms"], fit, limitation)
    covariance_rows = covariance_long_rows(spec["model_id"], design["terms"], fit["covariance"])
    draw_rows = coefficient_draw_rows(spec["model_id"], design["terms"], fit["beta"], fit["covariance"])
    metrics = [
        calibration_metric_row(spec["model_id"], "apparent", y, predicted, limitation)
    ]
    split_metric = patient_split_metric(binary.loc[design["row_mask"]].copy(), spec, subjects)
    if split_metric:
        metrics.append(split_metric)
    deciles = calibration_decile_rows(spec["model_id"], y, predicted)
    return {
        "coefficients": coefficients,
        "covariance_rows": covariance_rows,
        "draw_rows": draw_rows,
        "calibration_metrics": metrics,
        "calibration_deciles": deciles,
        "terms": design["terms"],
        "beta": fit["beta"],
        "covariance": fit["covariance"],
    }


def blocked_model_result(spec: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "coefficients": [],
        "covariance_rows": [],
        "draw_rows": [],
        "calibration_metrics": [
            {
                "model_id": spec["model_id"],
                "dataset": "MIMIC_IV_ED",
                "validation_scope": "blocked",
                "n": 0,
                "events": 0,
                "observed_prevalence": "",
                "mean_predicted": "",
                "calibration_in_the_large": "",
                "calibration_slope": "",
                "brier_score": "",
                "auroc": "",
                "pass_fail_status": "blocked",
                "notes": reason,
            }
        ],
        "calibration_deciles": [],
        "terms": [],
        "beta": np.array([]),
        "covariance": np.array([[]]),
    }


def build_design(binary: pd.DataFrame, spec: dict[str, Any]) -> dict[str, Any]:
    frame = binary.copy()
    notes: list[str] = []
    columns = [np.ones(len(frame))]
    terms = [{"term": "intercept", "level": "", "reference_level": ""}]
    row_mask = pd.Series(True, index=frame.index)
    uses_pain_missing = any(term[1] == "pain_missing" for term in spec["terms"])

    for kind, field, reference in spec["terms"]:
        if field not in frame.columns:
            notes.append(f"{field} absent; term removed.")
            continue
        values = frame[field].copy()
        if field == "pain_bin3" and uses_pain_missing:
            values = values.fillna(reference)
        if field == "pain_score" and uses_pain_missing:
            values = pd.to_numeric(values, errors="coerce").fillna(0.0)
        if values.isna().all():
            notes.append(f"{field} all missing; term removed.")
            continue

        if kind == "categorical":
            nonmissing = values.notna()
            levels = sorted(str(level) for level in values[nonmissing].unique() if str(level) != str(reference))
            if not levels:
                notes.append(f"{field} has no non-reference variation; term removed.")
                continue
            row_mask = row_mask & nonmissing
            for level in levels:
                columns.append((values.astype(str) == level).astype(float).to_numpy())
                terms.append({"term": field, "level": level, "reference_level": str(reference)})
        elif kind == "binary":
            numeric = pd.to_numeric(values, errors="coerce")
            if numeric.nunique(dropna=True) < 2:
                notes.append(f"{field} has no usable variation; term removed.")
                continue
            row_mask = row_mask & numeric.notna()
            columns.append(numeric.fillna(0).astype(float).to_numpy())
            terms.append({"term": field, "level": "1", "reference_level": "0"})
        elif kind == "continuous":
            result = scaled_column(values)
            if result is None:
                notes.append(f"{field} has no usable continuous variation; term removed.")
                continue
            row_mask = row_mask & result["mask"]
            columns.append(result["values"])
            terms.append({"term": field, "level": "scaled", "reference_level": "mean_centered"})
        elif kind == "spline":
            spline = spline_columns(values)
            if spline is None:
                notes.append(f"{field} spline unavailable; term removed.")
                continue
            row_mask = row_mask & spline["mask"]
            for label, values_out in spline["columns"]:
                columns.append(values_out)
                terms.append({"term": field, "level": label, "reference_level": "spline_basis"})

    matrix_all = np.column_stack(columns)
    return {"matrix": matrix_all[row_mask.to_numpy()], "terms": terms, "row_mask": row_mask, "notes": notes}


def scaled_column(values: pd.Series) -> dict[str, Any] | None:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.nunique(dropna=True) < 2:
        return None
    center = numeric.loc[numeric.notna()].mean()
    scale = numeric.loc[numeric.notna()].std() or 1.0
    return {"mask": numeric.notna(), "values": ((numeric - center) / scale).fillna(0).astype(float).to_numpy()}


def spline_columns(values: pd.Series) -> dict[str, Any] | None:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.nunique(dropna=True) < 4:
        return scaled_column(values)
    mask = numeric.notna()
    observed = numeric[mask]
    center = observed.mean()
    scale = observed.std() or 1.0
    scaled = ((numeric - center) / scale).fillna(0).astype(float)
    knots = np.quantile(observed, [0.33, 0.66])
    columns = [("linear_scaled", scaled.to_numpy())]
    for knot in knots:
        basis = np.maximum(pd.to_numeric(values, errors="coerce") - knot, 0).fillna(0)
        basis_scale = basis[mask].std() or 1.0
        columns.append((f"hinge_{round(float(knot), 4)}", ((basis - basis[mask].mean()) / basis_scale).to_numpy()))
    return {"mask": mask, "columns": columns}


def logistic_fit(x: np.ndarray, y: np.ndarray, ridge: float = 1e-4, max_iter: int = 100) -> dict[str, np.ndarray]:
    beta = np.zeros(x.shape[1])
    identity = np.eye(x.shape[1])
    identity[0, 0] = 0
    for _ in range(max_iter):
        p = logistic_np(x @ beta)
        w = np.clip(p * (1 - p), 1e-8, None)
        gradient = x.T @ (y - p) - ridge * identity @ beta
        hessian = (x.T * w) @ x + ridge * identity
        step = np.linalg.solve(hessian, gradient)
        beta = beta + step
        if float(np.max(np.abs(step))) < 1e-7:
            break
    p = logistic_np(x @ beta)
    w = np.clip(p * (1 - p), 1e-8, None)
    hessian = (x.T * w) @ x + ridge * identity
    return {"beta": beta, "covariance": np.linalg.pinv(hessian)}


def logistic_np(value: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-np.clip(value, -35, 35)))


def coefficient_rows(model_id: str, terms: list[dict[str, str]], fit: dict[str, np.ndarray], limitation: str) -> list[dict[str, Any]]:
    beta = fit["beta"]
    se = np.sqrt(np.clip(np.diag(fit["covariance"]), 0, None))
    rows: list[dict[str, Any]] = []
    for i, term in enumerate(terms):
        low = beta[i] - 1.96 * se[i]
        high = beta[i] + 1.96 * se[i]
        rows.append(
            {
                "model_id": model_id,
                "dataset": "MIMIC_IV_ED",
                "term": term["term"],
                "level": term["level"],
                "beta": round_float(beta[i]),
                "se": round_float(se[i]),
                "odds_ratio": round_float(math.exp(float(beta[i]))),
                "ci_low": round_float(math.exp(float(low))),
                "ci_high": round_float(math.exp(float(high))),
                "p_value": "",
                "evidence_tier": "mimic_replication_only",
                "limitation_note": limitation,
            }
        )
    return rows


def covariance_long_rows(model_id: str, terms: list[dict[str, str]], covariance: np.ndarray) -> list[dict[str, Any]]:
    names = [coefficient_name(term) for term in terms]
    rows: list[dict[str, Any]] = []
    for i, row_term in enumerate(names):
        for j, column_term in enumerate(names):
            rows.append({"model_id": model_id, "dataset": "MIMIC_IV_ED", "row_term": row_term, "column_term": column_term, "covariance": round_float(covariance[i, j])})
    return rows


def coefficient_draw_rows(model_id: str, terms: list[dict[str, str]], beta: np.ndarray, covariance: np.ndarray) -> list[dict[str, Any]]:
    rng = np.random.default_rng(RANDOM_SEED)
    stable = (covariance + covariance.T) / 2 + np.eye(covariance.shape[0]) * 1e-8
    draws = rng.multivariate_normal(beta, stable, size=DRAW_COUNT)
    rows: list[dict[str, Any]] = []
    for draw_id, draw in enumerate(draws, start=1):
        for i, term in enumerate(terms):
            rows.append(
                {
                    "model_id": model_id,
                    "dataset": "MIMIC_IV_ED",
                    "draw_id": draw_id,
                    "term": term["term"],
                    "level": term["level"],
                    "beta": round_float(draw[i]),
                    "draw_method": "normal_approximation_from_covariance",
                    "seed": RANDOM_SEED,
                }
            )
    return rows


def calibration_metric_row(model_id: str, scope: str, y: np.ndarray, predicted: np.ndarray, notes: str) -> dict[str, Any]:
    prevalence = float(y.mean())
    mean_predicted = float(predicted.mean())
    slope = fit_calibration_slope(y, predicted)
    intercept = fit_calibration_intercept(y, predicted)
    return {
        "model_id": model_id,
        "dataset": "MIMIC_IV_ED",
        "validation_scope": scope,
        "n": int(len(y)),
        "events": int(y.sum()),
        "observed_prevalence": round_float(prevalence),
        "mean_predicted": round_float(mean_predicted),
        "calibration_in_the_large": round_float(intercept),
        "calibration_slope": round_float(slope),
        "brier_score": round_float(float(np.mean((predicted - y) ** 2))),
        "auroc": round_float(auc_score(y, predicted)),
        "pass_fail_status": calibration_verdict(slope, prevalence, mean_predicted),
        "notes": notes,
    }


def patient_split_metric(frame: pd.DataFrame, spec: dict[str, Any], subjects: np.ndarray) -> dict[str, Any] | None:
    unique_subjects = np.unique(subjects)
    if len(unique_subjects) < 20:
        return None
    rng = np.random.default_rng(RANDOM_SEED)
    rng.shuffle(unique_subjects)
    cutoff = max(1, int(len(unique_subjects) * 0.7))
    train_subjects = set(unique_subjects[:cutoff])
    train = frame[frame["subject_id"].astype(str).isin(train_subjects)].copy()
    test = frame[~frame["subject_id"].astype(str).isin(train_subjects)].copy()
    train_design = build_design(train, spec)
    test_design = build_design(test, spec)
    if train_design["matrix"].shape[1] != test_design["matrix"].shape[1]:
        return None
    y_train = train.loc[train_design["row_mask"], "admit"].astype(float).to_numpy()
    y_test = test.loc[test_design["row_mask"], "admit"].astype(float).to_numpy()
    if len(y_train) == 0 or len(y_test) == 0 or len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
        return None
    fit = logistic_fit(train_design["matrix"], y_train)
    predicted = logistic_np(test_design["matrix"] @ fit["beta"])
    return calibration_metric_row(spec["model_id"], "patient_level_split_test", y_test, predicted, "patient-level split validation")


def calibration_decile_rows(model_id: str, y: np.ndarray, predicted: np.ndarray) -> list[dict[str, Any]]:
    frame = pd.DataFrame({"y": y, "p": predicted})
    try:
        frame["decile"] = pd.qcut(frame["p"], q=10, labels=False, duplicates="drop") + 1
    except ValueError:
        frame["decile"] = 1
    rows: list[dict[str, Any]] = []
    for decile, subset in frame.groupby("decile"):
        n = int(len(subset))
        rate = float(subset["y"].mean()) if n else float("nan")
        ci_low, ci_high = normal_ci(rate, n)
        rows.append(
            {
                "model_id": model_id,
                "dataset": "MIMIC_IV_ED",
                "decile": int(decile),
                "n": n,
                "events": int(subset["y"].sum()),
                "mean_predicted": round_float(float(subset["p"].mean())),
                "observed_rate": round_float(rate),
                "ci_low": round_float(ci_low),
                "ci_high": round_float(ci_high),
                "notes": "apparent unweighted decile calibration",
            }
        )
    return rows


def pain_monotonicity_rows(binary: pd.DataFrame) -> list[dict[str, Any]]:
    rates = []
    for level in ["mild", "moderate", "severe"]:
        subset = binary[binary["pain_bin3"] == level]
        rates.append(float(subset["admit"].mean()) if len(subset) else float("nan"))
    nondecreasing = all(math.isfinite(rates[i]) and math.isfinite(rates[i + 1]) and rates[i] <= rates[i + 1] for i in range(2))
    if float(binary["pain_missing"].mean()) > 0.40:
        verdict = "missingness_invalidates_inference"
        reason = "Pain missingness exceeds 40%."
    elif not nondecreasing:
        verdict = "nonmonotonic_flexible_only"
        reason = "MIMIC unadjusted pain-bin admission rates show material reversal or missing bins."
    elif int(binary["admit"].sum()) < 100:
        verdict = "exploratory_only"
        reason = "MIMIC alone cannot promote pain to dataset_derived for the national model, and admission events are <100."
    else:
        verdict = "exploratory_only"
        reason = "MIMIC shows compatible unadjusted direction only; MIMIC alone is replication support and cannot promote pain to dataset_derived for the national model."
    return [
        {
            "dataset": "MIMIC_IV_ED",
            "mild_admit_rate": round_float(rates[0]),
            "moderate_admit_rate": round_float(rates[1]),
            "severe_admit_rate": round_float(rates[2]),
            "mimic_unadjusted_nondecreasing": str(nondecreasing).lower(),
            "pain_missing_fraction": round_float(float(binary["pain_missing"].mean())),
            "total_admission_events": int(binary["admit"].sum()),
            "verdict": verdict,
            "reason": reason,
        }
    ]


def transportability_report(binary: pd.DataFrame, output_dir: Path) -> dict[str, Any]:
    report_path = output_dir / "transportability_report.md"
    nhamcs_coefficients = Path("outputs/nhamcs/coefficients.csv")
    if not nhamcs_coefficients.exists():
        text = "NHAMCS coefficient export not found. Transport recalibration was not run.\n"
        report_path.write_text("# MIMIC Transportability Report\n\n" + text, encoding="utf-8")
        return {"status": "blocked_missing_nhamcs_coefficients", "report": str(report_path)}
    coeffs = pd.read_csv(nhamcs_coefficients)
    if "evidence_tier" in coeffs.columns and not coeffs["evidence_tier"].eq("dataset_derived").any():
        text = "NHAMCS coefficient export exists but is not dataset_derived. Transport recalibration was not run.\n"
        report_path.write_text("# MIMIC Transportability Report\n\n" + text, encoding="utf-8")
        return {"status": "blocked_nhamcs_not_dataset_derived", "report": str(report_path)}
    report_path.write_text(
        "# MIMIC Transportability Report\n\nNHAMCS coefficients are present, but automatic harmonized transport application is not yet implemented.\n",
        encoding="utf-8",
    )
    _ = binary
    return {"status": "blocked_harmonized_application_not_implemented", "report": str(report_path)}


def fit_calibration_intercept(y: np.ndarray, predicted: np.ndarray) -> float:
    offset = logit(predicted)
    intercept = 0.0
    for _ in range(50):
        p = logistic_np(offset + intercept)
        gradient = float(np.sum(y - p))
        hessian = float(np.sum(p * (1 - p)))
        if hessian <= 0:
            break
        step = gradient / hessian
        intercept += step
        if abs(step) < 1e-9:
            break
    return intercept


def fit_calibration_slope(y: np.ndarray, predicted: np.ndarray) -> float:
    x = np.column_stack([np.ones(len(y)), logit(predicted)])
    fit = logistic_fit(x, y)
    return float(fit["beta"][1])


def logit(values: np.ndarray) -> np.ndarray:
    p = np.clip(values, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def auc_score(y: np.ndarray, predicted: np.ndarray) -> float:
    positives = predicted[y == 1]
    negatives = predicted[y == 0]
    if len(positives) == 0 or len(negatives) == 0:
        return float("nan")
    comparisons = positives[:, None] - negatives[None, :]
    return float((np.sum(comparisons > 0) + 0.5 * np.sum(comparisons == 0)) / comparisons.size)


def calibration_verdict(slope: float, observed: float, predicted: float) -> str:
    if not math.isfinite(slope):
        return "fail_calibration_unavailable"
    if abs(predicted - observed) > 0.02 or abs(predicted - observed) / max(observed, 1e-6) > 0.10:
        return "recalibrate_intercept"
    if slope < 0.8:
        return "likely_overfit"
    if slope > 1.2:
        return "likely_underfit"
    return "acceptable_replication_candidate"


def normal_ci(rate: float, n: int) -> tuple[float, float]:
    if n == 0 or not math.isfinite(rate):
        return float("nan"), float("nan")
    se = math.sqrt(max(rate * (1 - rate), 0.0) / n)
    return max(0.0, rate - 1.96 * se), min(1.0, rate + 1.96 * se)


def coefficient_name(term: dict[str, str]) -> str:
    return term["term"] if not term["level"] else f"{term['term']}[{term['level']}]"


def round_float(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(number):
        return ""
    return str(round(number, 8))


def write_outputs(results: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "coefficients.csv", results["coefficients"], coefficient_header())
    write_csv(output_dir / "covariance_matrix.csv", results["covariance_rows"], ["model_id", "dataset", "row_term", "column_term", "covariance"])
    write_csv(output_dir / "posterior_draws.csv", results["draw_rows"], ["model_id", "dataset", "draw_id", "term", "level", "beta", "draw_method", "seed"])
    write_csv(output_dir / "calibration_metrics.csv", results["calibration_metrics"], calibration_header())
    write_csv(output_dir / "calibration_by_decile.csv", results["calibration_deciles"], ["model_id", "dataset", "decile", "n", "events", "mean_predicted", "observed_rate", "ci_low", "ci_high", "notes"])
    write_csv(output_dir / "pain_monotonicity.csv", results["pain_monotonicity"], list(results["pain_monotonicity"][0].keys()) if results["pain_monotonicity"] else ["dataset", "verdict", "reason"])
    (output_dir / "model_run_metadata.json").write_text(json.dumps(results["metadata"], indent=2), encoding="utf-8")


def coefficient_header() -> list[str]:
    return ["model_id", "dataset", "term", "level", "beta", "se", "odds_ratio", "ci_low", "ci_high", "p_value", "evidence_tier", "limitation_note"]


def calibration_header() -> list[str]:
    return ["model_id", "dataset", "validation_scope", "n", "events", "observed_prevalence", "mean_predicted", "calibration_in_the_large", "calibration_slope", "brier_score", "auroc", "pass_fail_status", "notes"]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def run_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


if __name__ == "__main__":
    raise SystemExit(main())
