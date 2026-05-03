#!/usr/bin/env python3
"""Run pooled NHAMCS yearly build, append, and survey fitting workflow."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

import build_cohort
import build_pooled_cohort
import build_yearly_cohorts
import fit_models


DEFAULT_SURVEY_SCRIPT = Path("scripts/nhamcs/nhamcs_pooled_survey_fit.R")
DEFAULT_FEVER_GATE_SCRIPT = Path("scripts/nhamcs/nhamcs_fever_sparse_cell_validation.R")
DEFAULT_FINAL_REDUCED_GATE_SCRIPT = Path("scripts/nhamcs/nhamcs_final_reduced_model_gate.R")
DEFAULT_VOMITING_GATE_SCRIPT = Path("scripts/nhamcs/nhamcs_vomiting_validation.R")
DEFAULT_TACHYCARDIA_GATE_SCRIPT = Path("scripts/nhamcs/nhamcs_tachycardia_burden_validation.R")
DEFAULT_HEMATEMESIS_GATE_SCRIPT = Path("scripts/nhamcs/nhamcs_hematemesis_validation.R")
POOLED_MODEL_SPECS: list[dict[str, Any]] = [
    {
        "model_id": "pooled_primary_reduced",
        "formula": "admit ~ age_band + pain_bin3 + pain_missing + fever_or_temp",
        "terms": [
            ("categorical", "age_band", "30_44"),
            ("categorical", "pain_bin3", "moderate"),
            ("binary", "pain_missing", None),
            ("binary", "fever_or_temp", None),
        ],
    },
    {
        "model_id": "pooled_secondary_no_pain",
        "formula": "admit ~ age_band + fever_or_temp",
        "terms": [
            ("categorical", "age_band", "30_44"),
            ("binary", "fever_or_temp", None),
        ],
    },
    {
        "model_id": "pooled_candidate_v4_sensitivity",
        "formula": "admit ~ age_band + pain_bin3 + pain_missing + acuity + temp + HR + SBP",
        "terms": [
            ("categorical", "age_band", "30_44"),
            ("categorical", "pain_bin3", "moderate"),
            ("binary", "pain_missing", None),
            ("continuous", "temp", None),
            ("continuous", "acuity", None),
            ("continuous", "HR", None),
            ("continuous", "SBP", None),
        ],
    },
    {
        "model_id": "pooled_year_adjusted_reduced",
        "formula": "admit ~ age_band + pain_bin3 + pain_missing + fever_or_temp + year_factor",
        "terms": [
            ("categorical", "age_band", "30_44"),
            ("categorical", "pain_bin3", "moderate"),
            ("binary", "pain_missing", None),
            ("binary", "fever_or_temp", None),
            ("categorical", "year_factor", "2022"),
        ],
    },
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run pooled NHAMCS 2018-2022 empirical pipeline.")
    parser.add_argument("--config", default=build_yearly_cohorts.DEFAULT_CONFIG, type=Path)
    parser.add_argument("--yearly-output-dir", default=build_yearly_cohorts.DEFAULT_OUTPUT_DIR, type=Path)
    parser.add_argument("--output-dir", default=build_pooled_cohort.DEFAULT_OUTPUT_DIR, type=Path)
    parser.add_argument("--years", nargs="*", type=int)
    parser.add_argument("--survey-mode", choices=["auto", "require", "off"], default="auto")
    parser.add_argument("--rscript", default="")
    args = parser.parse_args(argv)

    config = build_yearly_cohorts.read_config(args.config)
    years = args.years or [int(year) for year in config["pool"]["years"]]

    yearly_status = build_yearly_cohorts.main(
        [
            "--config",
            str(args.config),
            "--output-dir",
            str(args.yearly_output_dir),
            "--years",
            *[str(year) for year in years],
        ]
    )
    if yearly_status != 0:
        write_pipeline_blocker_from_yearly(args.output_dir, args.yearly_output_dir)
        return yearly_status

    pooled_status = build_pooled_cohort.main(
        [
            "--config",
            str(args.config),
            "--yearly-output-dir",
            str(args.yearly_output_dir),
            "--output-dir",
            str(args.output_dir),
            "--years",
            *[str(year) for year in years],
        ]
    )
    if pooled_status != 0:
        return pooled_status

    cohort_path = args.output_dir / build_pooled_cohort.pooled_filename(years)
    fit_status = run_pooled_fit(
        cohort_path=cohort_path,
        output_dir=args.output_dir,
        years=years,
        survey_mode=args.survey_mode,
        rscript_override=args.rscript,
    )
    write_pipeline_summary(args.output_dir, cohort_path, years)
    return fit_status


def run_pooled_fit(
    *,
    cohort_path: Path,
    output_dir: Path,
    years: list[int],
    survey_mode: str,
    rscript_override: str,
) -> int:
    if not cohort_path.exists():
        build_cohort.write_blocker_report(
            output_dir / "blocker_report.md",
            source="NHAMCS pooled survey-weighted fitting",
            blockers=[f"Pooled analytic cohort file is missing: {cohort_path}"],
            outputs_written=[],
            next_action="Run scripts/nhamcs/build_pooled_cohort.py before fitting.",
        )
        return 2

    frame = pd.read_csv(cohort_path)
    dataset = build_pooled_cohort.dataset_name(years)
    fallback_results = pooled_fallback_results(frame, output_dir, dataset, years, rscript_override)
    fit_models.write_model_outputs(fallback_results, output_dir, write_blocker=False)

    survey_status = fit_models.survey_status_for_run(frame, rscript_override=rscript_override)
    if survey_mode == "off":
        fallback_results["metadata"]["survey_status"] = {
            **survey_status,
            "survey_weighted_primary_status": "survey_mode_off_running_exploratory_unweighted",
        }
        fallback_results["survey_blocker"] = True
        fit_models.write_model_outputs(fallback_results, output_dir, write_blocker=False)
        write_pooled_survey_blocker(output_dir, fallback_results["metadata"]["survey_status"])
        return 0

    if survey_status["survey_weighted_primary_status"] != "available":
        fallback_results["metadata"]["survey_status"] = survey_status
        fallback_results["survey_blocker"] = True
        fit_models.write_model_outputs(fallback_results, output_dir, write_blocker=False)
        write_pooled_survey_blocker(output_dir, survey_status)
        return 2 if survey_mode == "require" else 0

    fit_models.preserve_exploratory_outputs(output_dir)
    survey_result = run_survey_fit(cohort_path, output_dir, survey_status["rscript_path"])
    if survey_result.returncode == 0:
        fever_result = run_fever_gate(cohort_path, output_dir, survey_status["rscript_path"])
        if fever_result.returncode != 0:
            write_fever_gate_blocker(output_dir, fever_result)
            return 2 if survey_mode == "require" else 0
        final_gate_result = run_final_reduced_gate(cohort_path, output_dir, survey_status["rscript_path"])
        if final_gate_result.returncode != 0:
            write_final_reduced_gate_blocker(output_dir, final_gate_result)
            return 2 if survey_mode == "require" else 0
        vomiting_result = run_vomiting_gate(cohort_path, output_dir, survey_status["rscript_path"])
        if vomiting_result.returncode != 0:
            write_vomiting_gate_blocker(output_dir, vomiting_result)
            return 2 if survey_mode == "require" else 0
        tachycardia_result = run_tachycardia_gate(cohort_path, output_dir, survey_status["rscript_path"])
        if tachycardia_result.returncode != 0:
            write_tachycardia_gate_blocker(output_dir, tachycardia_result)
            return 2 if survey_mode == "require" else 0
        hematemesis_result = run_hematemesis_gate(cohort_path, output_dir, survey_status["rscript_path"])
        if hematemesis_result.returncode != 0:
            write_hematemesis_gate_blocker(output_dir, hematemesis_result)
            return 2 if survey_mode == "require" else 0
        fit_models.remove_stale_blocker(output_dir)
        return 0

    fit_models.restore_exploratory_outputs(output_dir)
    failure_status = {
        **survey_status,
        "survey_weighted_primary_status": "blocked_survey_fit_failed_running_exploratory_unweighted",
        "survey_fit_stdout": survey_result.stdout.strip()[-2000:],
        "survey_fit_stderr": survey_result.stderr.strip()[-4000:],
    }
    fallback_results["metadata"]["survey_status"] = failure_status
    fallback_results["survey_blocker"] = True
    fit_models.write_model_outputs(fallback_results, output_dir, write_blocker=False)
    write_pooled_survey_blocker(output_dir, failure_status)
    return 2 if survey_mode == "require" else 0


def pooled_fallback_results(
    frame: pd.DataFrame,
    output_dir: Path,
    dataset: str,
    years: list[int],
    rscript_override: str,
) -> dict[str, Any]:
    original_specs = fit_models.MODEL_SPECS
    try:
        fit_models.MODEL_SPECS = POOLED_MODEL_SPECS
        results = fit_models.fit_all_models(frame, output_dir, rscript_override=rscript_override)
    finally:
        fit_models.MODEL_SPECS = original_specs
    relabel_dataset(results, dataset)
    annotate_pooled_metadata(results, frame, dataset, years)
    return results


def relabel_dataset(results: dict[str, Any], dataset: str) -> None:
    for key in [
        "coefficients",
        "covariance_rows",
        "draw_rows",
        "calibration_metrics",
        "calibration_deciles",
        "pain_monotonicity",
    ]:
        for row in results.get(key, []):
            if "dataset" in row:
                row["dataset"] = dataset
    metadata = results.setdefault("metadata", {})
    metadata["dataset"] = dataset


def annotate_pooled_metadata(results: dict[str, Any], frame: pd.DataFrame, dataset: str, years: list[int]) -> None:
    binary = frame[frame["include_strict_binary"].astype(str).str.lower().isin(["true", "1"])]
    events = int(pd.to_numeric(binary["admit"], errors="coerce").fillna(0).sum())
    metadata = results.setdefault("metadata", {})
    metadata.update(
        {
            "dataset": dataset,
            "years": years,
            "model_status": metadata.get("model_status", "exploratory_unweighted_only"),
            "primary_model": "pooled_primary_reduced",
            "sensitivity_models": [
                "pooled_secondary_no_pain",
                "pooled_candidate_v4_sensitivity",
                "pooled_year_adjusted_reduced",
            ],
            "event_count_gate": {
                "threshold": 100,
                "passed": events >= 100,
                "events": events,
            },
            "weight_rule": "pooled_weight = PATWT / number_of_years",
            "design_rule": "pooled_stratum = interaction(year, CSTRATM); pooled_psu = interaction(year, CPSUM)",
            "no_dataset_derived_promotion": True,
            "no_v4_adoption_claim": True,
        }
    )


def run_survey_fit(cohort_path: Path, output_dir: Path, rscript: str) -> subprocess.CompletedProcess[str]:
    if not DEFAULT_SURVEY_SCRIPT.exists():
        return subprocess.CompletedProcess(
            args=[rscript, str(DEFAULT_SURVEY_SCRIPT), str(cohort_path), str(output_dir)],
            returncode=2,
            stdout="",
            stderr=f"Survey fitting script is missing: {DEFAULT_SURVEY_SCRIPT}",
        )
    return subprocess.run(
        [rscript, str(DEFAULT_SURVEY_SCRIPT), str(cohort_path), str(output_dir)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def run_fever_gate(cohort_path: Path, output_dir: Path, rscript: str) -> subprocess.CompletedProcess[str]:
    if not DEFAULT_FEVER_GATE_SCRIPT.exists():
        return subprocess.CompletedProcess(
            args=[rscript, str(DEFAULT_FEVER_GATE_SCRIPT), str(cohort_path), str(output_dir)],
            returncode=2,
            stdout="",
            stderr=f"Fever sparse-cell validation script is missing: {DEFAULT_FEVER_GATE_SCRIPT}",
        )
    return subprocess.run(
        [rscript, str(DEFAULT_FEVER_GATE_SCRIPT), str(cohort_path), str(output_dir)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def run_final_reduced_gate(cohort_path: Path, output_dir: Path, rscript: str) -> subprocess.CompletedProcess[str]:
    if not DEFAULT_FINAL_REDUCED_GATE_SCRIPT.exists():
        return subprocess.CompletedProcess(
            args=[rscript, str(DEFAULT_FINAL_REDUCED_GATE_SCRIPT), str(cohort_path), str(output_dir)],
            returncode=2,
            stdout="",
            stderr=f"Final reduced-model validation script is missing: {DEFAULT_FINAL_REDUCED_GATE_SCRIPT}",
        )
    return subprocess.run(
        [rscript, str(DEFAULT_FINAL_REDUCED_GATE_SCRIPT), str(cohort_path), str(output_dir)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def run_vomiting_gate(cohort_path: Path, output_dir: Path, rscript: str) -> subprocess.CompletedProcess[str]:
    if not DEFAULT_VOMITING_GATE_SCRIPT.exists():
        return subprocess.CompletedProcess(
            args=[rscript, str(DEFAULT_VOMITING_GATE_SCRIPT), str(cohort_path), str(output_dir)],
            returncode=2,
            stdout="",
            stderr=f"Vomiting validation script is missing: {DEFAULT_VOMITING_GATE_SCRIPT}",
        )
    return subprocess.run(
        [rscript, str(DEFAULT_VOMITING_GATE_SCRIPT), str(cohort_path), str(output_dir)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def run_tachycardia_gate(cohort_path: Path, output_dir: Path, rscript: str) -> subprocess.CompletedProcess[str]:
    if not DEFAULT_TACHYCARDIA_GATE_SCRIPT.exists():
        return subprocess.CompletedProcess(
            args=[rscript, str(DEFAULT_TACHYCARDIA_GATE_SCRIPT), str(cohort_path), str(output_dir)],
            returncode=2,
            stdout="",
            stderr=f"Tachycardia burden validation script is missing: {DEFAULT_TACHYCARDIA_GATE_SCRIPT}",
        )
    return subprocess.run(
        [rscript, str(DEFAULT_TACHYCARDIA_GATE_SCRIPT), str(cohort_path), str(output_dir)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def run_hematemesis_gate(cohort_path: Path, output_dir: Path, rscript: str) -> subprocess.CompletedProcess[str]:
    if not DEFAULT_HEMATEMESIS_GATE_SCRIPT.exists():
        return subprocess.CompletedProcess(
            args=[rscript, str(DEFAULT_HEMATEMESIS_GATE_SCRIPT), str(cohort_path), str(output_dir)],
            returncode=2,
            stdout="",
            stderr=f"Hematemesis validation script is missing: {DEFAULT_HEMATEMESIS_GATE_SCRIPT}",
        )
    return subprocess.run(
        [rscript, str(DEFAULT_HEMATEMESIS_GATE_SCRIPT), str(cohort_path), str(output_dir)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def write_fever_gate_blocker(output_dir: Path, fever_result: subprocess.CompletedProcess[str]) -> None:
    build_cohort.write_blocker_report(
        output_dir / "fever_sparse_cell_blocker_report.md",
        source="NHAMCS pooled fever sparse-cell validation",
        blockers=["Fever sparse-cell validation gate did not complete."],
        outputs_written=[
            str(output_dir / "coefficients.csv"),
            str(output_dir / "calibration_metrics.csv"),
        ],
        calibration_or_fitting_blockers=[
            fever_result.stdout.strip()[-2000:],
            fever_result.stderr.strip()[-4000:],
        ],
        next_action="Resolve the fever validation error, then rerun scripts/nhamcs/run_nhamcs_pooled_pipeline.py.",
    )


def write_final_reduced_gate_blocker(output_dir: Path, final_gate_result: subprocess.CompletedProcess[str]) -> None:
    build_cohort.write_blocker_report(
        output_dir / "final_reduced_model_blocker_report.md",
        source="NHAMCS pooled final reduced-model activation gate",
        blockers=["Final reduced-model activation gate did not complete."],
        outputs_written=[
            str(output_dir / "fever_model_comparison_coefficients.csv"),
            str(output_dir / "fever_model_comparison_calibration.csv"),
        ],
        calibration_or_fitting_blockers=[
            final_gate_result.stdout.strip()[-2000:],
            final_gate_result.stderr.strip()[-4000:],
        ],
        next_action="Resolve the final reduced-model validation error, then rerun scripts/nhamcs/run_nhamcs_pooled_pipeline.py.",
    )


def write_vomiting_gate_blocker(output_dir: Path, vomiting_result: subprocess.CompletedProcess[str]) -> None:
    build_cohort.write_blocker_report(
        output_dir / "vomiting_gate_blocker_report.md",
        source="NHAMCS pooled vomiting validation gate",
        blockers=["Vomiting validation gate did not complete."],
        outputs_written=[
            str(output_dir / "final_reduced_model_gate_decision.csv"),
            str(output_dir / "final_reduced_model_term_decisions.csv"),
        ],
        calibration_or_fitting_blockers=[
            vomiting_result.stdout.strip()[-2000:],
            vomiting_result.stderr.strip()[-4000:],
        ],
        next_action="Resolve the vomiting validation error, then rerun scripts/nhamcs/run_nhamcs_pooled_pipeline.py.",
    )


def write_tachycardia_gate_blocker(output_dir: Path, tachycardia_result: subprocess.CompletedProcess[str]) -> None:
    build_cohort.write_blocker_report(
        output_dir / "tachycardia_burden_blocker_report.md",
        source="NHAMCS pooled tachycardia burden validation gate",
        blockers=["Tachycardia burden validation gate did not complete."],
        outputs_written=[
            str(output_dir / "vomiting_gate_decision.csv"),
            str(output_dir / "vomiting_model_comparison_coefficients.csv"),
        ],
        calibration_or_fitting_blockers=[
            tachycardia_result.stdout.strip()[-2000:],
            tachycardia_result.stderr.strip()[-4000:],
        ],
        next_action="Resolve the tachycardia burden validation error, then rerun scripts/nhamcs/run_nhamcs_pooled_pipeline.py.",
    )


def write_hematemesis_gate_blocker(output_dir: Path, hematemesis_result: subprocess.CompletedProcess[str]) -> None:
    build_cohort.write_blocker_report(
        output_dir / "hematemesis_gate_blocker_report.md",
        source="NHAMCS pooled hematemesis validation gate",
        blockers=["Hematemesis validation gate did not complete."],
        outputs_written=[
            str(output_dir / "vomiting_gate_decision.csv"),
            str(output_dir / "vomiting_model_comparison_coefficients.csv"),
        ],
        calibration_or_fitting_blockers=[
            hematemesis_result.stdout.strip()[-2000:],
            hematemesis_result.stderr.strip()[-4000:],
        ],
        next_action="Resolve the hematemesis validation error, then rerun scripts/nhamcs/run_nhamcs_pooled_pipeline.py.",
    )


def write_pooled_survey_blocker(output_dir: Path, survey_status: dict[str, Any]) -> None:
    build_cohort.write_blocker_report(
        output_dir / "blocker_report.md",
        source="NHAMCS pooled survey-weighted fitting",
        blockers=["Primary pooled survey-weighted logistic regression was not run."],
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
            "Survey-weighted pooled model fitting was not run.",
            "Exploratory unweighted model outputs were written and labeled exploratory.",
        ],
        next_action=fit_models.survey_next_action(survey_status),
    )


def write_pipeline_blocker_from_yearly(output_dir: Path, yearly_output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    yearly_blocker = yearly_output_dir / "blocker_report.md"
    details = []
    if yearly_blocker.exists():
        details.append(yearly_blocker.read_text(encoding="utf-8")[:2000])
    for per_year in sorted(yearly_output_dir.glob("blocker_report_*.md")):
        details.append(per_year.read_text(encoding="utf-8")[:1000])
    if not details:
        details.append("See yearly output directory for per-year blocker reports.")
    build_cohort.write_blocker_report(
        output_dir / "blocker_report.md",
        source="NHAMCS pooled pipeline",
        blockers=["Yearly cohort construction failed; pooling and fitting were not run.", *details],
        outputs_written=[str(yearly_blocker)] if yearly_blocker.exists() else [],
        next_action="Resolve yearly cohort blockers, then rerun scripts/nhamcs/run_nhamcs_pooled_pipeline.py.",
    )


def write_pipeline_summary(output_dir: Path, cohort_path: Path, years: list[int]) -> None:
    if not cohort_path.exists():
        return
    frame = pd.read_csv(cohort_path)
    binary = frame[frame["include_strict_binary"].astype(str).str.lower().isin(["true", "1"])]
    weighted_n = float(pd.to_numeric(binary["pooled_weight"], errors="coerce").fillna(0).sum())
    weighted_events = float(
        pd.to_numeric(binary.loc[pd.to_numeric(binary["admit"], errors="coerce") == 1, "pooled_weight"], errors="coerce")
        .fillna(0)
        .sum()
    )
    events = int(pd.to_numeric(binary["admit"], errors="coerce").fillna(0).sum())
    pain_verdict = read_pain_verdict(output_dir / "pain_monotonicity.csv")
    summary = {
        "run_id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": build_pooled_cohort.dataset_name(years),
        "years": years,
        "pooled_strict_binary_n": int(len(binary)),
        "pooled_admission_events": events,
        "weighted_admission_prevalence": weighted_events / weighted_n if weighted_n else None,
        "event_count_gate_passed": events >= 100,
        "pain_monotonicity_verdict": pain_verdict,
        "fever_promotion_gate_status": read_fever_gate_status(output_dir / "fever_sparse_cell_gate_decision.csv"),
        "final_reduced_model_activation_status": read_final_reduced_gate_status(output_dir / "final_reduced_model_gate_decision.csv"),
        "vomiting_promotion_gate_status": read_vomiting_gate_status(output_dir / "vomiting_gate_decision.csv"),
        "tachycardia_burden_activation_status": read_final_reduced_gate_status(output_dir / "tachycardia_burden_gate_decision.csv"),
        "hematemesis_promotion_gate_status": read_hematemesis_gate_status(output_dir / "hematemesis_gate_decision.csv"),
        "no_dataset_derived_promotion": True,
        "no_v4_adoption_claim": True,
    }
    (output_dir / "pooled_pipeline_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )


def read_pain_verdict(path: Path) -> str:
    if not path.exists():
        return "not_evaluated"
    frame = pd.read_csv(path)
    if frame.empty or "verdict" not in frame.columns:
        return "not_evaluated"
    return str(frame.loc[0, "verdict"])


def read_fever_gate_status(path: Path) -> str:
    if not path.exists():
        return "not_run"
    frame = pd.read_csv(path)
    if frame.empty or "gate" not in frame.columns or "status" not in frame.columns:
        return "not_evaluated"
    rows = frame.loc[frame["gate"] == "promotion_suitability", "status"]
    if rows.empty:
        return "not_evaluated"
    return str(rows.iloc[0])


def read_final_reduced_gate_status(path: Path) -> str:
    if not path.exists():
        return "not_run"
    frame = pd.read_csv(path)
    if frame.empty or "gate" not in frame.columns or "status" not in frame.columns:
        return "not_evaluated"
    rows = frame.loc[frame["gate"] == "activation_suitability", "status"]
    if rows.empty:
        return "not_evaluated"
    return str(rows.iloc[0])


def read_vomiting_gate_status(path: Path) -> str:
    if not path.exists():
        return "not_run"
    frame = pd.read_csv(path)
    if frame.empty or "gate" not in frame.columns or "status" not in frame.columns:
        return "not_evaluated"
    rows = frame.loc[frame["gate"] == "promotion_suitability", "status"]
    if rows.empty:
        return "not_evaluated"
    return str(rows.iloc[0])


def read_hematemesis_gate_status(path: Path) -> str:
    if not path.exists():
        return "not_run"
    frame = pd.read_csv(path)
    if frame.empty or "gate" not in frame.columns or "status" not in frame.columns:
        return "not_evaluated"
    rows = frame.loc[frame["gate"] == "promotion_suitability", "status"]
    if rows.empty:
        return "not_evaluated"
    return str(rows.iloc[0])


if __name__ == "__main__":
    raise SystemExit(main())
