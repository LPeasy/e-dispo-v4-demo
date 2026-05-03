#!/usr/bin/env python3
"""Build validation artifacts for the endpoint-refined v3 class model.

The script intentionally keeps raw NHAMCS files local and writes only small
review artifacts. It uses pandas/numpy only so it works in the bundled runtime.
The fitted model is a reduced empirical candidate, not a clinical model.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import derive_nhamcs_2022 as derive


DEFAULT_RAW_DIR = Path("data/raw/nhamcs_2022")
DEFAULT_CONFIG = Path("scripts/nhamcs/config.example.json")
DEFAULT_ARTIFACT_DIR = Path("artifacts/nhamcs")
DEFAULT_DOCS_DIR = Path("docs/validation")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate NHAMCS endpoint audit, reduced model fit, and validation reports."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, type=Path)
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR, type=Path)
    parser.add_argument("--artifact-dir", default=DEFAULT_ARTIFACT_DIR, type=Path)
    parser.add_argument("--docs-dir", default=DEFAULT_DOCS_DIR, type=Path)
    args = parser.parse_args()

    config = read_json(args.config)
    dta_path = derive.find_stata_file(args.raw_dir, config.get("stataFile"))
    if dta_path is None:
        print("No NHAMCS .dta file found. Run derive_nhamcs_2022.py --download first.", file=sys.stderr)
        return 2

    df = pd.read_stata(dta_path, convert_categoricals=False)
    validation = build_validation_bundle(df, config, config_hash(args.config))

    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    args.docs_dir.mkdir(parents=True, exist_ok=True)

    write_json(args.artifact_dir / "endpoint-audit-2022.json", validation["endpointAudit"])
    write_json(args.artifact_dir / "model-fit-2022.json", validation["modelFit"])
    write_endpoint_csv(args.artifact_dir / "endpoint-audit-2022.csv", validation["endpointAudit"])
    write_coefficients_csv(args.artifact_dir / "model-fit-2022-coefficients.csv", validation["modelFit"])
    write_performance_report(args.docs_dir / "performance-report.md", validation["modelFit"])
    write_sensitivity_report(args.docs_dir / "sensitivity-report.md", validation["modelFit"])
    print(f"Wrote validation artifacts under {args.artifact_dir}")
    return 0


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def config_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_validation_bundle(df: pd.DataFrame, config: dict[str, Any], hash_value: str) -> dict[str, Any]:
    variables = config["variables"]
    codes = config["codes"]
    validation_config = config.get("validation", {})
    survey = variables["surveyDesign"]
    endpoint_spec_version = validation_config.get("endpointSpecVersion", "endpoint_refined_v3_2026-04-28")
    model_version = validation_config.get("modelVersion", "v3.1-validation-baseline")

    masks = cohort_masks(df, variables, codes)
    cohort = df[masks["non_trauma"]].copy()
    endpoint = derive.recode_endpoint_masks(
        cohort,
        variables["dispositionFlags"],
        codes.get("flagTrue", [1, "1", "Y", "YES", True]),
    )

    endpoint_audit = {
        "schemaVersion": "2.0.0",
        "artifactKind": "nhamcs_endpoint_audit",
        "sourceDataset": "NHAMCS 2022 ED public-use file",
        "derivedAt": date.today().isoformat(),
        "modelVersion": model_version,
        "endpointSpecVersion": endpoint_spec_version,
        "configHash": hash_value,
        "surveyDesign": survey_design_summary(df, survey),
        "cohortFlow": cohort_flow(df, masks, survey["weight"]),
        "endpointCounts": endpoint_counts(cohort, endpoint, survey["weight"]),
        "sensitivityEndpointCounts": sensitivity_counts(cohort, endpoint, survey["weight"]),
        "variableAudit": variable_audit(df, variables),
        "limitations": [
            "Counts are generated from the 2022 NHAMCS ED public-use file.",
            "Weighted counts use PATWT but the current script does not implement full design-based variance estimation.",
            "Endpoint recoding is row-level and excludes conflicting terminal disposition flags from the primary endpoint.",
        ],
    }

    primary_fit = fit_endpoint_model(
        cohort,
        endpoint["primary_admit"],
        endpoint["primary_treat_and_release"],
        survey["weight"],
        config,
        outcome_label="endpoint_primary_v3_refined",
        positive_label="ADMIT",
    )
    sens_a_fit = fit_endpoint_model(
        cohort,
        endpoint["sens_a_admit"],
        endpoint["sens_a_treat_and_release"],
        survey["weight"],
        config,
        outcome_label="endpoint_sens_A_eventual_home",
        positive_label="ADMIT",
    )
    sens_b_fit = fit_endpoint_model(
        cohort,
        endpoint["sens_b_positive"],
        endpoint["sens_b_treat_and_release"],
        survey["weight"],
        config,
        outcome_label="endpoint_sens_B_acute_escalation",
        positive_label="ACUTE_ESCALATION_POSITIVE",
    )

    model_fit = {
        "schemaVersion": "2.0.0",
        "artifactKind": "nhamcs_validation_model_fit",
        "sourceDataset": "NHAMCS 2022 ED public-use file",
        "derivedAt": date.today().isoformat(),
        "modelVersion": model_version,
        "endpointSpecVersion": endpoint_spec_version,
        "configHash": hash_value,
        "generatedBy": "scripts/nhamcs/validate_nhamcs_2022.py",
        "modelName": validation_config.get("primaryModel", "nhamcs_reduced_age_pain_severity"),
        "cohortFlow": endpoint_audit["cohortFlow"],
        "surveyDesign": endpoint_audit["surveyDesign"],
        "endpointCounts": endpoint_audit["endpointCounts"],
        "sensitivityEndpointCounts": endpoint_audit["sensitivityEndpointCounts"],
        "predictorMapping": config["predictorMapping"],
        "coefficients": primary_fit["coefficients"],
        "coefficientCovariance": primary_fit["coefficientCovariance"],
        "performanceMetrics": primary_fit["performanceMetrics"],
        "internalValidation": primary_fit["internalValidation"],
        "sensitivityAnalyses": [
            summarize_sensitivity_fit(primary_fit),
            summarize_sensitivity_fit(sens_a_fit),
            summarize_sensitivity_fit(sens_b_fit),
        ],
        "limitations": [
            "Reduced empirical candidate includes ageBand and painSeverity only.",
            "Current fit is not promoted into the app and must not be described as clinically validated.",
            "Survey weights are used for counts; coefficient fit and performance metrics are unweighted apparent/internal checks.",
            "Full survey-design variance estimation and external validation remain future work.",
        ],
    }

    return {"endpointAudit": endpoint_audit, "modelFit": model_fit}


def cohort_masks(df: pd.DataFrame, variables: dict[str, Any], codes: dict[str, Any]) -> dict[str, pd.Series]:
    all_mask = pd.Series(True, index=df.index)
    male = df[variables["sex"]].isin(codes["male"])
    age = male & df[variables["age"]].between(18, 64, inclusive="both")
    abdominal = age & derive.any_column_matches(
        df,
        variables["reasonForVisit"],
        codes["abdominalPainRfv"],
    )
    trauma_variable = variables.get("trauma")
    if trauma_variable and "nonTrauma" in codes:
        non_trauma = abdominal & df[trauma_variable].isin(codes["nonTrauma"])
    else:
        non_trauma = abdominal
    return {
        "all": all_mask,
        "male": male,
        "age": age,
        "abdominal": abdominal,
        "non_trauma": non_trauma,
    }


def cohort_flow(df: pd.DataFrame, masks: dict[str, pd.Series], weight_col: str) -> list[dict[str, Any]]:
    steps = [
        ("All 2022 NHAMCS ED records", "all"),
        ("Male records", "male"),
        ("Male age 18-64", "age"),
        ("Abdominal pain RFV proxy", "abdominal"),
        ("Non-trauma/non-poisoning/non-adverse-effect proxy", "non_trauma"),
    ]
    return [
        count_row(label, df.loc[masks[key]], weight_col)
        for label, key in steps
    ]


def count_row(label: str, frame: pd.DataFrame, weight_col: str) -> dict[str, Any]:
    return {
        "step": label,
        "count": int(len(frame)),
        "weightedCount": round(weighted_sum(frame, weight_col), 3),
    }


def endpoint_counts(cohort: pd.DataFrame, endpoint: dict[str, pd.Series], weight_col: str) -> dict[str, Any]:
    weighted = {
        "admit": round(weighted_sum(cohort.loc[endpoint["primary_admit"]], weight_col), 3),
        "treatAndRelease": round(weighted_sum(cohort.loc[endpoint["primary_treat_and_release"]], weight_col), 3),
        "excluded": round(weighted_sum(cohort.loc[endpoint["primary_excluded"]], weight_col), 3),
        "excludedObservationDischarged": round(
            weighted_sum(cohort.loc[endpoint["primary_excluded_observation_discharged"]], weight_col),
            3,
        ),
        "excludedTransfer": round(weighted_sum(cohort.loc[endpoint["primary_excluded_transfer"]], weight_col), 3),
        "excludedSentinelDeath": round(
            weighted_sum(cohort.loc[endpoint["primary_excluded_sentinel_death"]], weight_col),
            3,
        ),
        "excludedNonroutineExit": round(
            weighted_sum(cohort.loc[endpoint["primary_excluded_nonroutine_exit"]], weight_col),
            3,
        ),
        "excludedOtherUnknown": round(
            weighted_sum(cohort.loc[endpoint["primary_excluded_other_unknown"]], weight_col),
            3,
        ),
        "excludedConflict": round(weighted_sum(cohort.loc[endpoint["primary_excluded_conflict"]], weight_col), 3),
    }
    return {
        "admit": int(endpoint["primary_admit"].sum()),
        "treatAndRelease": int(endpoint["primary_treat_and_release"].sum()),
        "excluded": int(endpoint["primary_excluded"].sum()),
        "excludedObservationDischarged": int(endpoint["primary_excluded_observation_discharged"].sum()),
        "excludedTransfer": int(endpoint["primary_excluded_transfer"].sum()),
        "excludedSentinelDeath": int(endpoint["primary_excluded_sentinel_death"].sum()),
        "excludedNonroutineExit": int(endpoint["primary_excluded_nonroutine_exit"].sum()),
        "excludedOtherUnknown": int(endpoint["primary_excluded_other_unknown"].sum()),
        "excludedConflict": int(endpoint["primary_excluded_conflict"].sum()),
        "weighted": weighted,
    }


def sensitivity_counts(cohort: pd.DataFrame, endpoint: dict[str, pd.Series], weight_col: str) -> dict[str, Any]:
    return {
        "endpointSensAEventualHome": {
            "admit": int(endpoint["sens_a_admit"].sum()),
            "treatAndRelease": int(endpoint["sens_a_treat_and_release"].sum()),
            "excluded": int(endpoint["sens_a_excluded"].sum()),
            "weighted": {
                "admit": round(weighted_sum(cohort.loc[endpoint["sens_a_admit"]], weight_col), 3),
                "treatAndRelease": round(weighted_sum(cohort.loc[endpoint["sens_a_treat_and_release"]], weight_col), 3),
                "excluded": round(weighted_sum(cohort.loc[endpoint["sens_a_excluded"]], weight_col), 3),
            },
        },
        "endpointSensBAcuteEscalation": {
            "acuteEscalationPositive": int(endpoint["sens_b_positive"].sum()),
            "treatAndRelease": int(endpoint["sens_b_treat_and_release"].sum()),
            "excluded": int(endpoint["sens_b_excluded"].sum()),
            "weighted": {
                "acuteEscalationPositive": round(weighted_sum(cohort.loc[endpoint["sens_b_positive"]], weight_col), 3),
                "treatAndRelease": round(weighted_sum(cohort.loc[endpoint["sens_b_treat_and_release"]], weight_col), 3),
                "excluded": round(weighted_sum(cohort.loc[endpoint["sens_b_excluded"]], weight_col), 3),
            },
        },
    }


def variable_audit(df: pd.DataFrame, variables: dict[str, Any]) -> list[dict[str, Any]]:
    expected: list[str] = [
        variables["sex"],
        variables["age"],
        variables["trauma"],
        *variables["reasonForVisit"],
        *variables["surveyDesign"].values(),
        *variables["applicability"].values(),
        *variables["predictors"].values(),
    ]
    for names in variables["dispositionFlags"].values():
        expected.extend(names)
    return [
        {
            "variable": name,
            "present": name in df.columns,
            "nonMissingCount": int(df[name].notna().sum()) if name in df.columns else 0,
        }
        for name in sorted(set(expected))
    ]


def survey_design_summary(df: pd.DataFrame, survey: dict[str, str]) -> dict[str, Any]:
    weight_col = survey["weight"]
    return {
        "weightVariable": weight_col,
        "strataVariable": survey["strata"],
        "psuVariable": survey["psu"],
        "recordCount": int(len(df)),
        "weightedCount": round(weighted_sum(df, weight_col), 3),
        "effectiveSampleSizeApprox": round(effective_sample_size(df[weight_col]), 3),
        "varianceImplementation": "Weighted counts only; full survey-design variance is not implemented in this validation script.",
    }


def weighted_sum(frame: pd.DataFrame, weight_col: str) -> float:
    if weight_col not in frame.columns:
        return float("nan")
    return float(frame[weight_col].sum())


def effective_sample_size(weights: pd.Series) -> float:
    values = weights.astype(float).to_numpy()
    denominator = np.sum(values ** 2)
    if denominator <= 0:
        return float("nan")
    return float((np.sum(values) ** 2) / denominator)


def fit_endpoint_model(
    cohort: pd.DataFrame,
    positive_mask: pd.Series,
    negative_mask: pd.Series,
    weight_col: str,
    config: dict[str, Any],
    outcome_label: str,
    positive_label: str,
) -> dict[str, Any]:
    binary_mask = positive_mask | negative_mask
    frame = cohort.loc[binary_mask].copy()
    y_all = positive_mask.loc[binary_mask].astype(int).to_numpy()
    design = build_design_matrix(frame, config["variables"])
    fit_mask = design["fitMask"].to_numpy()
    x = design["matrix"][fit_mask]
    y = y_all[fit_mask]

    fit = logistic_fit(x, y)
    p = logistic_np(x @ fit["beta"])
    metrics = performance_metrics(y, p)
    calibration = calibration_metrics(y, p)
    metrics.update(calibration)
    metrics.update(
        {
            "outcome": outcome_label,
            "positiveLabel": positive_label,
            "sampleSize": int(len(y)),
            "excludedForMissingPredictors": int((~fit_mask).sum()),
            "eventCount": int(y.sum()),
            "nonEventCount": int((1 - y).sum()),
            "outcomePrevalence": round(float(y.mean()) if len(y) else float("nan"), 6),
            "weightedBinaryCount": round(weighted_sum(frame, weight_col), 3),
        }
    )

    return {
        "outcome": outcome_label,
        "coefficients": coefficients(design["columns"], fit),
        "coefficientCovariance": covariance_payload(design["columns"], fit["covariance"]),
        "performanceMetrics": metrics,
        "internalValidation": bootstrap_validation(x, y, config.get("validation", {})),
    }


def build_design_matrix(frame: pd.DataFrame, variables: dict[str, Any]) -> dict[str, Any]:
    age_band = frame[variables["age"]].map(age_band_value)
    pain = frame[variables["predictors"]["painScale"]].map(pain_severity_value)
    feature_frame = pd.DataFrame({"ageBand": age_band, "painSeverity": pain}, index=frame.index)
    fit_mask = feature_frame.notna().all(axis=1)

    columns = [
        "intercept",
        "ageBand.18_29",
        "ageBand.45_54",
        "ageBand.55_64",
        "painSeverity.mild",
        "painSeverity.severe",
    ]
    x = np.ones((len(frame), len(columns)), dtype=float)
    x[:, 1] = (feature_frame["ageBand"] == "18_29").astype(float)
    x[:, 2] = (feature_frame["ageBand"] == "45_54").astype(float)
    x[:, 3] = (feature_frame["ageBand"] == "55_64").astype(float)
    x[:, 4] = (feature_frame["painSeverity"] == "mild").astype(float)
    x[:, 5] = (feature_frame["painSeverity"] == "severe").astype(float)
    return {"columns": columns, "matrix": x, "fitMask": fit_mask}


def age_band_value(age: Any) -> str | None:
    if pd.isna(age):
        return None
    age = int(age)
    if 18 <= age <= 29:
        return "18_29"
    if 30 <= age <= 44:
        return "30_44"
    if 45 <= age <= 54:
        return "45_54"
    if 55 <= age <= 64:
        return "55_64"
    return None


def pain_severity_value(value: Any) -> str | None:
    if pd.isna(value):
        return None
    value = int(value)
    if value < 0:
        return None
    if value <= 3:
        return "mild"
    if value <= 6:
        return "moderate"
    if value <= 10:
        return "severe"
    return None


def logistic_fit(x: np.ndarray, y: np.ndarray, ridge: float = 1e-6, max_iter: int = 100) -> dict[str, Any]:
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
        if np.max(np.abs(step)) < 1e-7:
            break
    p = logistic_np(x @ beta)
    w = np.clip(p * (1 - p), 1e-8, None)
    hessian = (x.T * w) @ x + ridge * identity
    covariance = np.linalg.pinv(hessian)
    return {"beta": beta, "covariance": covariance}


def logistic_np(value: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-np.clip(value, -35, 35)))


def coefficients(columns: list[str], fit: dict[str, Any]) -> list[dict[str, Any]]:
    beta = fit["beta"]
    se = np.sqrt(np.diag(fit["covariance"]))
    return [
        {
            "key": columns[i],
            "mean": round(float(beta[i]), 8),
            "standardError": round(float(se[i]), 8),
            "ci95Low": round(float(beta[i] - 1.96 * se[i]), 8),
            "ci95High": round(float(beta[i] + 1.96 * se[i]), 8),
            "source": "nhamcs_2022",
        }
        for i in range(len(columns))
    ]


def covariance_payload(columns: list[str], covariance: np.ndarray) -> dict[str, Any]:
    return {
        "columns": columns,
        "matrix": [[round(float(value), 10) for value in row] for row in covariance.tolist()],
    }


def performance_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, Any]:
    return {
        "auc": round(auc_score(y, p), 6),
        "brierScore": round(float(np.mean((p - y) ** 2)), 6),
    }


def calibration_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, Any]:
    logit_p = np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1))
    intercept = calibration_intercept(y, logit_p)
    x_slope = np.column_stack([np.ones(len(y)), logit_p])
    slope_fit = logistic_fit(x_slope, y)
    return {
        "calibrationIntercept": clean_round(intercept, 6),
        "calibrationSlope": clean_round(slope_fit["beta"][1], 6),
    }


def clean_round(value: float, digits: int) -> float:
    rounded = round(float(value), digits)
    return 0.0 if rounded == 0 else rounded


def calibration_intercept(y: np.ndarray, offset: np.ndarray) -> float:
    intercept = 0.0
    for _ in range(50):
        p = logistic_np(offset + intercept)
        gradient = float(np.sum(y - p))
        hessian = float(np.sum(p * (1 - p)))
        if hessian <= 0:
            break
        step = gradient / hessian
        intercept = intercept + step
        if abs(step) < 1e-9:
            break
    return intercept


def auc_score(y: np.ndarray, p: np.ndarray) -> float:
    positives = p[y == 1]
    negatives = p[y == 0]
    if len(positives) == 0 or len(negatives) == 0:
        return float("nan")
    comparisons = positives[:, None] - negatives[None, :]
    return float((np.sum(comparisons > 0) + 0.5 * np.sum(comparisons == 0)) / comparisons.size)


def bootstrap_validation(x: np.ndarray, y: np.ndarray, validation_config: dict[str, Any]) -> dict[str, Any]:
    iterations = int(validation_config.get("bootstrapIterations", 100))
    seed = int(validation_config.get("randomSeed", 20260428))
    rng = np.random.default_rng(seed)
    aucs: list[float] = []
    briers: list[float] = []
    n = len(y)
    for _ in range(iterations):
        sample = rng.integers(0, n, size=n)
        if len(np.unique(y[sample])) < 2:
            continue
        fit = logistic_fit(x[sample], y[sample])
        p = logistic_np(x @ fit["beta"])
        aucs.append(auc_score(y, p))
        briers.append(float(np.mean((p - y) ** 2)))
    return {
        "method": "bootstrap_apparent_refit_on_original",
        "iterationsRequested": iterations,
        "iterationsCompleted": len(aucs),
        "randomSeed": seed,
        "aucMedian": round(float(np.median(aucs)), 6) if aucs else float("nan"),
        "aucP025": round(float(np.quantile(aucs, 0.025)), 6) if aucs else float("nan"),
        "aucP975": round(float(np.quantile(aucs, 0.975)), 6) if aucs else float("nan"),
        "brierMedian": round(float(np.median(briers)), 6) if briers else float("nan"),
        "brierP025": round(float(np.quantile(briers, 0.025)), 6) if briers else float("nan"),
        "brierP975": round(float(np.quantile(briers, 0.975)), 6) if briers else float("nan"),
        "limitation": "Bootstrap is lightweight and does not implement NHAMCS survey-design variance.",
    }


def summarize_sensitivity_fit(fit: dict[str, Any]) -> dict[str, Any]:
    metrics = fit["performanceMetrics"]
    return {
        "outcome": fit["outcome"],
        "sampleSize": metrics["sampleSize"],
        "eventCount": metrics["eventCount"],
        "outcomePrevalence": metrics["outcomePrevalence"],
        "auc": metrics["auc"],
        "brierScore": metrics["brierScore"],
        "calibrationIntercept": metrics["calibrationIntercept"],
        "calibrationSlope": metrics["calibrationSlope"],
    }


def write_endpoint_csv(path: Path, endpoint_audit: dict[str, Any]) -> None:
    rows = []
    counts = endpoint_audit["endpointCounts"]
    for key, label in [
        ("admit", "Primary admit"),
        ("treatAndRelease", "Primary treat_and_release"),
        ("excluded", "Primary excluded"),
        ("excludedObservationDischarged", "Excluded observation -> discharged"),
        ("excludedTransfer", "Excluded transfer"),
        ("excludedSentinelDeath", "Excluded sentinel death"),
        ("excludedNonroutineExit", "Excluded nonroutine exit"),
        ("excludedOtherUnknown", "Excluded other/unknown"),
        ("excludedConflict", "Excluded conflict"),
    ]:
        rows.append({"endpoint": label, "count": counts[key], "weightedCount": counts.get("weighted", {}).get(key, "")})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["endpoint", "count", "weightedCount"])
        writer.writeheader()
        writer.writerows(rows)


def write_coefficients_csv(path: Path, model_fit: dict[str, Any]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["key", "mean", "standardError", "ci95Low", "ci95High", "source"])
        writer.writeheader()
        writer.writerows(model_fit["coefficients"])


def write_performance_report(path: Path, model_fit: dict[str, Any]) -> None:
    metrics = model_fit["performanceMetrics"]
    path.write_text(
        "\n".join(
            [
                "# NHAMCS 2022 Reduced Model Performance Report",
                "",
                "This report summarizes the reduced empirical candidate fit. It is not activated in the app.",
                "",
                "## Model Status",
                "",
                f"- Model version: `{model_fit['modelVersion']}`",
                f"- Endpoint spec: `{model_fit['endpointSpecVersion']}`",
                "- Empirical activation: blocked pending review.",
                "- Reduced predictors: ageBand and painSeverity.",
                "",
                "## Apparent Performance",
                "",
                f"- Sample size: {metrics['sampleSize']}",
                f"- Event count: {metrics['eventCount']}",
                f"- Outcome prevalence: {metrics['outcomePrevalence']}",
                f"- AUC/C-statistic: {metrics['auc']}",
                f"- Brier score: {metrics['brierScore']}",
                f"- Calibration intercept: {metrics['calibrationIntercept']}",
                f"- Calibration slope: {metrics['calibrationSlope']}",
                "",
                "## Internal Validation",
                "",
                f"- Method: {model_fit['internalValidation']['method']}",
                f"- Bootstrap iterations completed: {model_fit['internalValidation']['iterationsCompleted']}",
                f"- AUC median: {model_fit['internalValidation']['aucMedian']}",
                f"- Brier median: {model_fit['internalValidation']['brierMedian']}",
                "",
                "## Limitations",
                "",
                "- Full survey-design variance is not implemented.",
                "- No external validation is performed.",
                "- The model remains educational until the validation dossier is reviewed.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_sensitivity_report(path: Path, model_fit: dict[str, Any]) -> None:
    lines = [
        "# NHAMCS 2022 Sensitivity Report",
        "",
        "This report compares the primary endpoint with report-only sensitivity endpoints.",
        "",
        "| Outcome | N | Events | Prevalence | AUC | Brier | Calibration intercept | Calibration slope |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in model_fit["sensitivityAnalyses"]:
        lines.append(
            f"| {row['outcome']} | {row['sampleSize']} | {row['eventCount']} | {row['outcomePrevalence']} | {row['auc']} | {row['brierScore']} | {row['calibrationIntercept']} | {row['calibrationSlope']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Sensitivity A includes observation -> discharged as eventual home release. Sensitivity B includes acute transfer as acute-care escalation. These outputs are not active app predictions.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
