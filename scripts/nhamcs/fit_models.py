#!/usr/bin/env python3
"""Fit exploratory NHAMCS logistic models from the analytic cohort output."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import build_cohort


DEFAULT_OUTPUT_DIR = Path("outputs/nhamcs")
RANDOM_SEED = 20260428
DRAW_COUNT = 1000
SURVEY_SCRIPT = Path("scripts/nhamcs/nhamcs_survey_fit.R")
SURVEY_OUTPUTS = [
    "coefficients.csv",
    "covariance_matrix.csv",
    "mvn_coefficient_draws.csv",
    "calibration_metrics.csv",
    "calibration_by_decile.csv",
    "pain_monotonicity.csv",
    "model_run_metadata.json",
]


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
        "model_id": "B_reduced_plus_acuity_vitals",
        "formula": "admit ~ age_band + pain_bin3 + pain_missing + vomiting + temp + acuity + HR + SBP",
        "terms": [
            ("categorical", "age_band", "30_44"),
            ("categorical", "pain_bin3", "moderate"),
            ("binary", "pain_missing", None),
            ("binary", "vomiting", None),
            ("continuous", "temp", None),
            ("continuous", "acuity", None),
            ("continuous", "HR", None),
            ("continuous", "SBP", None),
        ],
    },
    {
        "model_id": "C_continuous_pain_exploratory",
        "formula": "admit ~ age_band + pain_score + pain_missing + vomiting + fever_or_temp",
        "terms": [
            ("categorical", "age_band", "30_44"),
            ("continuous", "pain_score", None),
            ("binary", "pain_missing", None),
            ("binary", "vomiting", None),
            ("binary", "fever_or_temp", None),
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
    parser = argparse.ArgumentParser(description="Fit NHAMCS exploratory logistic models.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    parser.add_argument("--survey-mode", choices=["auto", "require", "off"], default="auto")
    parser.add_argument("--rscript", default="")
    args = parser.parse_args(argv)

    cohort_path = args.output_dir / "analytic_cohort_nhamcs.csv"
    if not cohort_path.exists():
        build_cohort.write_blocker_report(
            args.output_dir / "blocker_report.md",
            source="NHAMCS 2022",
            blockers=[f"Analytic cohort file is missing: {cohort_path}"],
            outputs_written=[],
            next_action="Run scripts/nhamcs/build_cohort.py before scripts/nhamcs/fit_models.py.",
        )
        return 2

    frame = pd.read_csv(cohort_path)
    results = fit_all_models(frame, args.output_dir, rscript_override=args.rscript)
    write_model_outputs(results, args.output_dir, write_blocker=False)

    status = handle_survey_mode(
        frame=frame,
        cohort_path=cohort_path,
        output_dir=args.output_dir,
        survey_mode=args.survey_mode,
        rscript_override=args.rscript,
        fallback_results=results,
    )
    if status != 0:
        return status

    print(f"Wrote NHAMCS model outputs under {args.output_dir}")
    return 0


def fit_all_models(frame: pd.DataFrame, output_dir: Path, rscript_override: str = "") -> dict[str, Any]:
    binary = frame[frame["include_strict_binary"].astype(str).str.lower().isin(["true", "1"])].copy()
    if binary.empty:
        build_cohort.write_blocker_report(
            output_dir / "blocker_report.md",
            source="NHAMCS 2022",
            blockers=["Strict binary analytic cohort is empty."],
            outputs_written=[],
            next_action="Review endpoint mapping and cohort filters.",
        )
        return empty_results("empty_binary_cohort")

    survey_status = survey_status_for_run(frame, rscript_override=rscript_override)
    sparse_notes = sparse_cell_notes(binary)
    total_events = int(binary["admit"].sum())
    pain_missing_fraction = float(binary["pain_missing"].mean()) if "pain_missing" in binary else float("nan")
    run_status = "exploratory_unweighted_only"
    if total_events < 100:
        sparse_notes.append("Total admission events <100; all fitted outputs are exploratory.")
    if pain_missing_fraction > 0.40:
        sparse_notes.append("Pain missingness exceeds 40%; complete-case pain analysis is sensitivity only.")

    coefficients: list[dict[str, Any]] = []
    covariance_rows: list[dict[str, Any]] = []
    draw_rows: list[dict[str, Any]] = []
    calibration_metrics: list[dict[str, Any]] = []
    calibration_deciles: list[dict[str, Any]] = []
    fitted_models: dict[str, dict[str, Any]] = {}

    for spec in MODEL_SPECS:
        fit_result = fit_model(binary, spec, sparse_notes, run_status)
        fitted_models[spec["model_id"]] = fit_result
        coefficients.extend(fit_result["coefficients"])
        covariance_rows.extend(fit_result["covariance_rows"])
        draw_rows.extend(fit_result["draw_rows"])
        calibration_metrics.append(fit_result["calibration_metrics"])
        calibration_deciles.extend(fit_result["calibration_deciles"])

    pain_monotonicity = pain_monotonicity_rows(binary, fitted_models, pain_missing_fraction, total_events, run_status)
    metadata = {
        "run_id": run_id(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": "NHAMCS_2022",
        "model_status": run_status,
        "survey_status": survey_status,
        "random_seed": RANDOM_SEED,
        "draw_count": DRAW_COUNT,
        "fitting_method": "ridge_penalized_unweighted_logistic_irls",
        "software": {
            "python": "standard runtime",
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "rscript_available": bool(survey_status.get("rscript_path")),
        },
        "model_specs": [
            {"model_id": spec["model_id"], "formula": spec["formula"]} for spec in MODEL_SPECS
        ],
        "sparse_cell_notes": sparse_notes,
        "reference_categories": {
            "age_band": "30_44",
            "pain_bin3": "moderate",
        },
        "transformations": [
            "pain_missing is explicit.",
            "Missing pain_bin3 is filled to the pain reference level only when pain_missing is included.",
            "Missing pain_score is filled to 0 only when pain_missing is included.",
            "Predictors with all values missing, no variation, or no confirmed mapping are removed and documented.",
        ],
    }
    return {
        "coefficients": coefficients,
        "covariance_rows": covariance_rows,
        "draw_rows": draw_rows,
        "calibration_metrics": calibration_metrics,
        "calibration_deciles": calibration_deciles,
        "pain_monotonicity": pain_monotonicity,
        "metadata": metadata,
        "survey_blocker": survey_status["survey_weighted_primary_status"] != "available",
    }


def empty_results(reason: str) -> dict[str, Any]:
    return {
        "coefficients": [],
        "covariance_rows": [],
        "draw_rows": [],
        "calibration_metrics": [],
        "calibration_deciles": [],
        "pain_monotonicity": [{"dataset": "NHAMCS_2022", "verdict": "exploratory_only", "reason": reason}],
        "metadata": {"model_status": "blocked", "reason": reason},
        "survey_blocker": True,
    }


def handle_survey_mode(
    frame: pd.DataFrame,
    cohort_path: Path,
    output_dir: Path,
    survey_mode: str,
    rscript_override: str,
    fallback_results: dict[str, Any],
) -> int:
    survey_status = survey_status_for_run(frame, rscript_override=rscript_override)
    if survey_mode == "off":
        fallback_results["metadata"]["survey_status"] = {
            **survey_status,
            "survey_weighted_primary_status": "survey_mode_off_running_exploratory_unweighted",
        }
        fallback_results["metadata"]["model_status"] = "exploratory_unweighted_only"
        fallback_results["survey_blocker"] = True
        write_model_outputs(fallback_results, output_dir, write_blocker=True)
        return 0

    if survey_status["survey_weighted_primary_status"] != "available":
        fallback_results["metadata"]["survey_status"] = survey_status
        fallback_results["survey_blocker"] = True
        write_model_outputs(fallback_results, output_dir, write_blocker=True)
        return 2 if survey_mode == "require" else 0

    preserve_exploratory_outputs(output_dir)
    survey_result = run_survey_fit(
        cohort_path=cohort_path,
        output_dir=output_dir,
        rscript=survey_status["rscript_path"],
    )
    if survey_result.returncode == 0:
        remove_stale_blocker(output_dir)
        return 0

    restore_exploratory_outputs(output_dir)
    failure_status = {
        **survey_status,
        "survey_weighted_primary_status": "blocked_survey_fit_failed_running_exploratory_unweighted",
        "survey_fit_stdout": survey_result.stdout.strip()[-2000:],
        "survey_fit_stderr": survey_result.stderr.strip()[-4000:],
    }
    fallback_results["metadata"]["survey_status"] = failure_status
    fallback_results["survey_blocker"] = True
    write_model_outputs(fallback_results, output_dir, write_blocker=True)
    return 2 if survey_mode == "require" else 0


def run_survey_fit(cohort_path: Path, output_dir: Path, rscript: str) -> subprocess.CompletedProcess[str]:
    script_path = SURVEY_SCRIPT
    if not script_path.exists():
        return subprocess.CompletedProcess(
            args=[rscript, str(script_path), str(cohort_path), str(output_dir)],
            returncode=2,
            stdout="",
            stderr=f"Survey fitting script is missing: {script_path}",
        )
    return subprocess.run(
        [rscript, str(script_path), str(cohort_path), str(output_dir)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def preserve_exploratory_outputs(output_dir: Path) -> None:
    for name in SURVEY_OUTPUTS:
        source = output_dir / name
        if not source.exists():
            continue
        suffix = source.suffix
        target = output_dir / f"{source.stem}_exploratory_unweighted{suffix}"
        shutil.copyfile(source, target)


def restore_exploratory_outputs(output_dir: Path) -> None:
    for name in SURVEY_OUTPUTS:
        target = output_dir / name
        suffix = target.suffix
        source = output_dir / f"{target.stem}_exploratory_unweighted{suffix}"
        if source.exists():
            shutil.copyfile(source, target)


def remove_stale_blocker(output_dir: Path) -> None:
    blocker = output_dir / "blocker_report.md"
    if blocker.exists():
        blocker.unlink()


def survey_status_for_run(frame: pd.DataFrame, rscript_override: str = "") -> dict[str, Any]:
    present = {
        "PATWT": bool("weight" in frame.columns and frame["weight"].notna().any()),
        "CSTRATM": bool("stratum" in frame.columns and frame["stratum"].notna().any()),
        "CPSUM": bool("psu" in frame.columns and frame["psu"].notna().any()),
    }
    rscript = find_rscript(rscript_override)
    library_paths = configured_r_library_paths()
    survey_available = False
    survey_check_error = ""
    if rscript:
        survey_available, survey_check_error = r_package_available(rscript, "survey", library_paths)

    if all(present.values()) and rscript and survey_available:
        status = "available"
    elif all(present.values()):
        if rscript:
            status = "blocked_survey_package_unavailable_running_exploratory_unweighted"
        else:
            status = "blocked_rscript_unavailable_running_exploratory_unweighted"
    else:
        status = "blocked_missing_survey_columns_running_exploratory_unweighted"
    return {
        "survey_columns_present": present,
        "rscript_path": rscript or "",
        "r_library_paths": library_paths,
        "survey_package_available": survey_available,
        "survey_package_check_error": survey_check_error,
        "survey_weighted_primary_status": status,
        "notes": "Python workflow writes exploratory unweighted fits unless survey-mode runs R survey::svyglm successfully.",
    }


def find_rscript(override: str = "") -> str:
    if override.strip():
        candidate = Path(override.strip())
        if candidate.exists():
            return str(candidate.resolve())
        return ""
    for key in ("RSCRIPT_PATH", "RSCRIPT"):
        value = os.environ.get(key, "").strip()
        if value and Path(value).exists():
            return str(Path(value))
    for name in ("Rscript", "Rscript.exe"):
        found = shutil.which(name)
        if found:
            return found
    candidates: list[Path] = []
    program_files = [Path("C:/Program Files/R"), Path("C:/Program Files (x86)/R")]
    for base in program_files:
        if base.exists():
            candidates.extend(base.glob("R-*/bin/Rscript.exe"))
            candidates.extend(base.glob("R-*/bin/x64/Rscript.exe"))
    return str(sorted(candidates)[-1]) if candidates else ""


def configured_r_library_paths() -> list[str]:
    paths: list[str] = []
    for key in ("NHAMCS_R_LIBS", "R_LIBS_USER"):
        raw = os.environ.get(key, "")
        for item in raw.split(os.pathsep):
            if item.strip():
                paths.append(item.strip())
    paths.extend(
        [
            "r-lib",
            "scripts/nhamcs/r-lib",
            "C:/Users/lawto/OneDrive/Documents/R/win-library/4.6",
        ]
    )
    resolved: list[str] = []
    for item in paths:
        path = Path(item)
        if path.exists():
            text = str(path.resolve())
            if text not in resolved:
                resolved.append(text)
    return resolved


def r_package_available(rscript: str, package: str, library_paths: list[str]) -> tuple[bool, str]:
    path_expr = "c(" + ", ".join(r_string(path) for path in library_paths) + ")"
    expression = (
        f"if (length({path_expr}) > 0) .libPaths(unique(c({path_expr}, .libPaths()))); "
        f"quit(status = ifelse(requireNamespace({r_string(package)}, quietly = TRUE), 0, 1))"
    )
    try:
        completed = subprocess.run(
            [rscript, "-e", expression],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if completed.returncode == 0:
        return True, ""
    message = (completed.stderr or completed.stdout or "").strip()
    return False, message[:500]


def r_string(value: str) -> str:
    return '"' + value.replace("\\", "/").replace('"', '\\"') + '"'


def sparse_cell_notes(binary: pd.DataFrame) -> list[str]:
    notes: list[str] = []
    for field in ["age_band", "pain_bin3"]:
        if field not in binary.columns:
            continue
        for level, subset in binary.groupby(field, dropna=False):
            events = int(subset["admit"].sum())
            if events < 10:
                notes.append(f"{field} level {level} has <10 admission events; ridge penalization used and model labeled exploratory.")
    if model_specs_use_field("vomiting"):
        vomiting_positive = binary[binary.get("vomiting", pd.Series(np.nan, index=binary.index)) == 1]
        if len(vomiting_positive) == 0:
            notes.append("Vomiting mapping unavailable or sparse; vomiting term removed where it has no usable variation.")
    fever_positive = binary[binary.get("fever_or_temp", pd.Series(np.nan, index=binary.index)) == 1]
    if len(fever_positive) > 0 and int(fever_positive["admit"].sum()) < 10:
        notes.append("Fever positives have <10 admission events; ridge penalization used and model labeled exploratory.")
    return notes


def model_specs_use_field(field: str) -> bool:
    return any(term[1] == field for spec in MODEL_SPECS for term in spec["terms"])


def fit_model(
    binary: pd.DataFrame,
    spec: dict[str, Any],
    global_notes: list[str],
    run_status: str,
) -> dict[str, Any]:
    design = build_design(binary, spec)
    y = binary.loc[design["row_mask"], "admit"].astype(float).to_numpy()
    x = design["matrix"]
    if len(y) == 0 or len(np.unique(y)) < 2:
        return blocked_model_result(spec, "No usable binary outcome variation after model-specific missingness filtering.")

    fit = logistic_fit(x, y)
    predicted = logistic_np(x @ fit["beta"])
    terms = design["terms"]
    covariance = fit["covariance"]
    evidence_tier = "exploratory"
    limitation = "; ".join(design["notes"] + global_notes + ["Survey-design fitting unavailable in this Python fallback."])

    coefficients = coefficient_rows(spec, terms, fit, evidence_tier, limitation)
    covariance_rows = covariance_long_rows(spec["model_id"], terms, covariance)
    draw_rows = mvn_draw_rows(spec["model_id"], terms, fit["beta"], covariance)
    calibration_metrics = calibration_metric_row(spec["model_id"], y, predicted, run_status, limitation)
    calibration_deciles = calibration_decile_rows(spec["model_id"], y, predicted)
    return {
        "coefficients": coefficients,
        "covariance_rows": covariance_rows,
        "draw_rows": draw_rows,
        "calibration_metrics": calibration_metrics,
        "calibration_deciles": calibration_deciles,
        "terms": terms,
        "beta": fit["beta"],
        "predicted": predicted,
        "row_mask": design["row_mask"],
        "notes": design["notes"],
    }


def blocked_model_result(spec: dict[str, Any], reason: str) -> dict[str, Any]:
    row = {
        "model_id": spec["model_id"],
        "dataset": "NHAMCS_2022",
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
    return {
        "coefficients": [],
        "covariance_rows": [],
        "draw_rows": [],
        "calibration_metrics": row,
        "calibration_deciles": [],
        "terms": [],
        "beta": np.array([]),
        "predicted": np.array([]),
        "row_mask": pd.Series(False),
        "notes": [reason],
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
            numeric = pd.to_numeric(values, errors="coerce")
            if numeric.nunique(dropna=True) < 2:
                notes.append(f"{field} has no usable variation; term removed.")
                continue
            row_mask = row_mask & numeric.notna()
            centered = numeric - numeric.loc[numeric.notna()].mean()
            scaled = centered / (numeric.loc[numeric.notna()].std() or 1.0)
            columns.append(scaled.fillna(0).astype(float).to_numpy())
            terms.append({"term": field, "level": "scaled", "reference_level": "mean_centered"})

    matrix_all = np.column_stack(columns)
    return {
        "matrix": matrix_all[row_mask.to_numpy()],
        "terms": terms,
        "row_mask": row_mask,
        "notes": notes,
    }


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
    covariance = np.linalg.pinv(hessian)
    return {"beta": beta, "covariance": covariance}


def logistic_np(value: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-np.clip(value, -35, 35)))


def coefficient_rows(
    spec: dict[str, Any],
    terms: list[dict[str, str]],
    fit: dict[str, np.ndarray],
    evidence_tier: str,
    limitation: str,
) -> list[dict[str, Any]]:
    beta = fit["beta"]
    se = np.sqrt(np.clip(np.diag(fit["covariance"]), 0, None))
    rows: list[dict[str, Any]] = []
    for i, term in enumerate(terms):
        low = beta[i] - 1.96 * se[i]
        high = beta[i] + 1.96 * se[i]
        rows.append(
            {
                "model_id": spec["model_id"],
                "dataset": "NHAMCS_2022",
                "term": term["term"],
                "level": term["level"],
                "beta": round_float(beta[i]),
                "se": round_float(se[i]),
                "odds_ratio": round_float(math.exp(float(beta[i]))),
                "ci_low": round_float(math.exp(float(low))),
                "ci_high": round_float(math.exp(float(high))),
                "p_value": "",
                "evidence_tier": evidence_tier,
                "limitation_note": limitation,
            }
        )
    return rows


def covariance_long_rows(model_id: str, terms: list[dict[str, str]], covariance: np.ndarray) -> list[dict[str, Any]]:
    names = [coefficient_name(term) for term in terms]
    rows: list[dict[str, Any]] = []
    for i, row_term in enumerate(names):
        for j, column_term in enumerate(names):
            rows.append(
                {
                    "model_id": model_id,
                    "dataset": "NHAMCS_2022",
                    "row_term": row_term,
                    "column_term": column_term,
                    "covariance": round_float(covariance[i, j]),
                }
            )
    return rows


def mvn_draw_rows(model_id: str, terms: list[dict[str, str]], beta: np.ndarray, covariance: np.ndarray) -> list[dict[str, Any]]:
    rng = np.random.default_rng(RANDOM_SEED)
    covariance = nearest_stable_covariance(covariance)
    draws = rng.multivariate_normal(beta, covariance, size=DRAW_COUNT)
    rows: list[dict[str, Any]] = []
    for draw_id, draw in enumerate(draws, start=1):
        for i, term in enumerate(terms):
            rows.append(
                {
                    "model_id": model_id,
                    "dataset": "NHAMCS_2022",
                    "draw_id": draw_id,
                    "term": term["term"],
                    "level": term["level"],
                    "beta": round_float(draw[i]),
                    "seed": RANDOM_SEED,
                }
            )
    return rows


def nearest_stable_covariance(covariance: np.ndarray) -> np.ndarray:
    symmetric = (covariance + covariance.T) / 2
    return symmetric + np.eye(symmetric.shape[0]) * 1e-8


def calibration_metric_row(
    model_id: str,
    y: np.ndarray,
    predicted: np.ndarray,
    run_status: str,
    notes: str,
) -> dict[str, Any]:
    prevalence = float(y.mean())
    mean_predicted = float(predicted.mean())
    calibration_intercept = fit_calibration_intercept(y, predicted)
    calibration_slope = fit_calibration_slope(y, predicted)
    brier = float(np.mean((predicted - y) ** 2))
    auc = auc_score(y, predicted)
    pass_fail = calibration_verdict(calibration_slope, prevalence, mean_predicted, run_status)
    return {
        "model_id": model_id,
        "dataset": "NHAMCS_2022",
        "n": int(len(y)),
        "events": int(y.sum()),
        "observed_prevalence": round_float(prevalence),
        "mean_predicted": round_float(mean_predicted),
        "calibration_in_the_large": round_float(calibration_intercept),
        "calibration_slope": round_float(calibration_slope),
        "brier_score": round_float(brier),
        "auroc": round_float(auc),
        "pass_fail_status": pass_fail,
        "notes": notes,
    }


def calibration_decile_rows(model_id: str, y: np.ndarray, predicted: np.ndarray) -> list[dict[str, Any]]:
    frame = pd.DataFrame({"y": y, "p": predicted})
    try:
        frame["decile"] = pd.qcut(frame["p"], q=10, labels=False, duplicates="drop") + 1
    except ValueError:
        frame["decile"] = 1
    rows: list[dict[str, Any]] = []
    for decile, subset in frame.groupby("decile"):
        n = int(len(subset))
        events = int(subset["y"].sum())
        rate = float(subset["y"].mean()) if n else float("nan")
        ci_low, ci_high = normal_ci(rate, n)
        rows.append(
            {
                "model_id": model_id,
                "dataset": "NHAMCS_2022",
                "decile": int(decile),
                "n": n,
                "events": events,
                "mean_predicted": round_float(float(subset["p"].mean())),
                "observed_rate": round_float(rate),
                "ci_low": round_float(ci_low),
                "ci_high": round_float(ci_high),
                "notes": "unweighted exploratory decile calibration",
            }
        )
    return rows


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


def calibration_verdict(slope: float, observed: float, predicted: float, run_status: str) -> str:
    if run_status != "survey_weighted_primary":
        return "exploratory_only"
    if not math.isfinite(slope):
        return "fail_calibration_unavailable"
    if abs(predicted - observed) > 0.02 or abs(predicted - observed) / max(observed, 1e-6) > 0.10:
        return "fail_recalibrate_intercept"
    if slope < 0.8:
        return "fail_likely_overfit"
    if slope > 1.2:
        return "fail_likely_underfit"
    return "pass_candidate_range"


def pain_monotonicity_rows(
    binary: pd.DataFrame,
    fitted_models: dict[str, dict[str, Any]],
    pain_missing_fraction: float,
    total_events: int,
    run_status: str,
) -> list[dict[str, Any]]:
    rates = []
    for level in ["mild", "moderate", "severe"]:
        subset = binary[binary["pain_bin3"] == level]
        rates.append(float(subset["admit"].mean()) if len(subset) else float("nan"))
    nondecreasing = all(
        math.isfinite(rates[i]) and math.isfinite(rates[i + 1]) and rates[i] <= rates[i + 1]
        for i in range(len(rates) - 1)
    )
    if run_status != "survey_weighted_primary" or total_events < 100:
        verdict = "exploratory_only"
        reason = "Survey-weighted primary fit unavailable or total admission events <100."
    elif pain_missing_fraction > 0.40:
        verdict = "missingness_invalidates_inference"
        reason = "Pain missingness exceeds 40%."
    elif not nondecreasing:
        verdict = "nonmonotonic_flexible_only"
        reason = "Unadjusted pain-bin admission rates are not nondecreasing."
    else:
        verdict = "null_or_unstable"
        reason = "Protocol criteria beyond NHAMCS unadjusted trend were not all satisfied."
    _ = fitted_models
    return [
        {
            "dataset": "NHAMCS_2022",
            "mild_admit_rate": round_float(rates[0]),
            "moderate_admit_rate": round_float(rates[1]),
            "severe_admit_rate": round_float(rates[2]),
            "nhamcs_unadjusted_nondecreasing": str(nondecreasing).lower(),
            "pain_missing_fraction": round_float(pain_missing_fraction),
            "total_admission_events": total_events,
            "verdict": verdict,
            "reason": reason,
        }
    ]


def coefficient_name(term: dict[str, str]) -> str:
    return term["term"] if not term["level"] else f"{term['term']}[{term['level']}]"


def normal_ci(rate: float, n: int) -> tuple[float, float]:
    if n == 0 or not math.isfinite(rate):
        return float("nan"), float("nan")
    se = math.sqrt(max(rate * (1 - rate), 0.0) / n)
    return max(0.0, rate - 1.96 * se), min(1.0, rate + 1.96 * se)


def round_float(value: Any) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(number):
        return ""
    return str(round(number, 8))


def write_model_outputs(results: dict[str, Any], output_dir: Path, write_blocker: bool = True) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "coefficients.csv", results["coefficients"], coefficient_header())
    write_csv(output_dir / "covariance_matrix.csv", results["covariance_rows"], ["model_id", "dataset", "row_term", "column_term", "covariance"])
    write_csv(output_dir / "mvn_coefficient_draws.csv", results["draw_rows"], ["model_id", "dataset", "draw_id", "term", "level", "beta", "seed"])
    write_csv(output_dir / "calibration_metrics.csv", results["calibration_metrics"], calibration_header())
    write_csv(output_dir / "calibration_by_decile.csv", results["calibration_deciles"], ["model_id", "dataset", "decile", "n", "events", "mean_predicted", "observed_rate", "ci_low", "ci_high", "notes"])
    write_csv(output_dir / "pain_monotonicity.csv", results["pain_monotonicity"], list(results["pain_monotonicity"][0].keys()) if results["pain_monotonicity"] else ["dataset", "verdict", "reason"])
    (output_dir / "model_run_metadata.json").write_text(json.dumps(results["metadata"], indent=2), encoding="utf-8")
    if write_blocker and results.get("survey_blocker"):
        build_cohort.write_blocker_report(
            output_dir / "blocker_report.md",
            source="NHAMCS 2022 survey-weighted fitting",
            blockers=["Primary survey-weighted logistic regression was not run."],
            outputs_written=[
                str(output_dir / "coefficients.csv"),
                str(output_dir / "covariance_matrix.csv"),
                str(output_dir / "mvn_coefficient_draws.csv"),
                str(output_dir / "calibration_metrics.csv"),
                str(output_dir / "calibration_by_decile.csv"),
                str(output_dir / "pain_monotonicity.csv"),
                str(output_dir / "model_run_metadata.json"),
            ],
            calibration_or_fitting_blockers=[
                "Survey-weighted primary model fitting was not run.",
                "Exploratory unweighted model outputs were written and labeled exploratory.",
            ],
            next_action=survey_next_action(results["metadata"].get("survey_status", {})),
        )


def survey_next_action(survey_status: dict[str, Any]) -> str:
    status = survey_status.get("survey_weighted_primary_status", "")
    if status == "blocked_rscript_unavailable_running_exploratory_unweighted":
        return "Install R so Rscript.exe is available, or set RSCRIPT_PATH to the Rscript.exe location. The OneDrive R folder is a package library, not an R runtime."
    if status == "blocked_survey_package_unavailable_running_exploratory_unweighted":
        paths = "; ".join(survey_status.get("r_library_paths", []))
        return f"Install the R package 'survey' into an active R library or set NHAMCS_R_LIBS. Checked library paths: {paths or 'none'}."
    if status == "blocked_missing_survey_columns_running_exploratory_unweighted":
        return "Confirm PATWT, CSTRATM, and CPSUM are present and mapped before survey-weighted fitting."
    if status == "blocked_survey_fit_failed_running_exploratory_unweighted":
        stderr = survey_status.get("survey_fit_stderr", "")
        return f"Review and fix the R survey fitting failure, then rerun with --survey-mode require. R stderr: {stderr or 'none captured'}"
    if status == "survey_mode_off_running_exploratory_unweighted":
        return "Rerun with --survey-mode auto or --survey-mode require to execute survey-weighted fitting."
    if status == "available":
        return "Run with --survey-mode auto or --survey-mode require so scripts/nhamcs/nhamcs_survey_fit.R writes the survey-weighted candidate outputs, then review full protocol gates before promotion."
    return "Run scripts/nhamcs/nhamcs_survey_fit.R for design-based fitting, then review full protocol gates before promotion."


def coefficient_header() -> list[str]:
    return [
        "model_id",
        "dataset",
        "term",
        "level",
        "beta",
        "se",
        "odds_ratio",
        "ci_low",
        "ci_high",
        "p_value",
        "evidence_tier",
        "limitation_note",
    ]


def calibration_header() -> list[str]:
    return [
        "model_id",
        "dataset",
        "n",
        "events",
        "observed_prevalence",
        "mean_predicted",
        "calibration_in_the_large",
        "calibration_slope",
        "brier_score",
        "auroc",
        "pass_fail_status",
        "notes",
    ]


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
