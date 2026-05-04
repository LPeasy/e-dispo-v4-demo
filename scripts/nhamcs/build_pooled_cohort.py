#!/usr/bin/env python3
"""Append harmonized yearly NHAMCS cohorts into a pooled analytic cohort."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

import build_cohort
import build_yearly_cohorts


DEFAULT_CONFIG = build_yearly_cohorts.DEFAULT_CONFIG
DEFAULT_YEARLY_OUTPUT_DIR = build_yearly_cohorts.DEFAULT_OUTPUT_DIR
DEFAULT_OUTPUT_DIR = Path("outputs/nhamcs_pooled")
FULL_SOURCE_SCOPE_FILES = {
    "full_source_endpoint": "full_source_endpoint_cohort_{year}.csv",
    "full_source_nontrauma": "full_source_nontrauma_cohort_{year}.csv",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build pooled NHAMCS analytic cohort.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, type=Path)
    parser.add_argument("--yearly-output-dir", default=DEFAULT_YEARLY_OUTPUT_DIR, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    parser.add_argument("--years", nargs="*", type=int)
    args = parser.parse_args(argv)

    config = build_yearly_cohorts.read_config(args.config)
    years = args.years or [int(year) for year in config["pool"]["years"]]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    missing = [
        str(args.yearly_output_dir / f"analytic_cohort_{year}.csv")
        for year in years
        if not (args.yearly_output_dir / f"analytic_cohort_{year}.csv").exists()
    ]
    if missing:
        build_cohort.write_blocker_report(
            args.output_dir / "blocker_report.md",
            source="NHAMCS 2018-2022 pooled cohort",
            blockers=["One or more yearly harmonized cohort files are missing."],
            missing_raw_data=missing,
            outputs_written=[],
            next_action="Run scripts/nhamcs/build_yearly_cohorts.py for all requested years before pooling.",
        )
        return 2

    pooled = build_pooled_frame(args.yearly_output_dir, years)
    output_path = args.output_dir / pooled_filename(years)
    pooled.to_csv(output_path, index=False)

    write_combined_yearly_outputs(args.yearly_output_dir, args.output_dir, years)
    write_metadata(args.output_dir, config, years, pooled, output_path)
    write_full_source_scope_outputs(args.yearly_output_dir, args.output_dir, years)
    write_pooled_vs_2022(args.output_dir, years, pooled)

    print(f"Wrote pooled NHAMCS cohort to {output_path}")
    return 0


def build_pooled_frame(yearly_output_dir: Path, years: list[int]) -> pd.DataFrame:
    return build_pooled_frame_from_template(yearly_output_dir, years, "analytic_cohort_{year}.csv")


def build_pooled_frame_from_template(yearly_output_dir: Path, years: list[int], template: str) -> pd.DataFrame:
    frames = []
    for year in years:
        path = yearly_output_dir / template.format(year=year)
        frame = pd.read_csv(path)
        if "year" not in frame.columns:
            frame["year"] = year
        frames.append(frame)
    pooled = pd.concat(frames, ignore_index=True)
    year_count = len(years)
    pooled["source_dataset"] = pooled.get("dataset", "")
    pooled["dataset"] = dataset_name(years)
    pooled["PATWT"] = pd.to_numeric(pooled["PATWT"], errors="coerce")
    pooled["pooled_weight"] = pooled["PATWT"] / year_count
    pooled["pooled_stratum"] = pooled["year"].astype(str) + "_" + pooled["CSTRATM"].astype(str)
    pooled["pooled_psu"] = pooled["year"].astype(str) + "_" + pooled["CPSUM"].astype(str)
    pooled["weight"] = pooled["pooled_weight"]
    pooled["stratum"] = pooled["pooled_stratum"]
    pooled["psu"] = pooled["pooled_psu"]
    pooled["year_factor"] = pooled["year"].astype(str)
    pooled["pool_year_count"] = year_count
    pooled["include_strict_binary"] = pooled["include_strict_binary"].map(truthy)
    pooled["admit"] = pd.to_numeric(pooled["admit"], errors="coerce").fillna(0).astype(int)
    return pooled[pooled_column_order(pooled)]


def pooled_column_order(frame: pd.DataFrame) -> list[str]:
    preferred = [
        "year",
        "year_factor",
        "record_id",
        "dataset",
        "source_dataset",
        "source_scope",
        "age",
        "sex",
        "age_band",
        "age_band_full",
        "RACERETH",
        "race_ethnicity",
        "PAYTYPER",
        "payer",
        "REGION",
        "region",
        "MSA",
        "msa_status",
        "IMMEDR",
        "acuity_code",
        "AMBTRANSFER",
        "arrival_transfer_context",
        "adult_male_18_64_flag",
        "abdominal_pain_flag",
        "non_trauma_flag",
        "trauma_exclusion_flag",
        "in_active_scope",
        "endpoint_class",
        "endpoint",
        "include_strict_binary",
        "admit",
        "pain_score",
        "pain_bin3",
        "pain_missing",
        "fever_or_temp",
        "temp",
        "acuity",
        "HR",
        "tachycardia_burden",
        "SBP",
        "hypotension_burden",
        "PATWT",
        "pooled_weight",
        "CSTRATM",
        "CPSUM",
        "pooled_stratum",
        "pooled_psu",
        "weight",
        "stratum",
        "psu",
        "pool_year_count",
        "pain_bin5",
        "vomiting_present",
        "nausea_present",
        "vomiting_rfv_position_tier",
        "hematemesis_present",
        "hematemesis_rfv_position_tier",
        "vomiting",
    ]
    return [column for column in preferred if column in frame.columns] + [
        column for column in frame.columns if column not in preferred
    ]


def write_full_source_scope_outputs(yearly_output_dir: Path, output_dir: Path, years: list[int]) -> None:
    for scope, template in FULL_SOURCE_SCOPE_FILES.items():
        missing = [
            yearly_output_dir / template.format(year=year)
            for year in years
            if not (yearly_output_dir / template.format(year=year)).exists()
        ]
        if missing:
            build_cohort.write_blocker_report(
                output_dir / f"{scope}_cohort_blocker_report.md",
                source=f"NHAMCS pooled {scope} scope cohort",
                blockers=["One or more yearly full-source scope cohort files are missing."],
                missing_raw_data=[str(path) for path in missing],
                outputs_written=[],
                next_action="Run scripts/nhamcs/build_yearly_cohorts.py with the current source-scope cohort builder.",
            )
            continue
        pooled = build_pooled_frame_from_template(yearly_output_dir, years, template)
        output_path = output_dir / full_source_scope_filename(scope, years)
        pooled.to_csv(output_path, index=False)
        write_full_source_scope_metadata(output_dir, scope, years, pooled, output_path)


def full_source_scope_filename(scope: str, years: list[int]) -> str:
    return f"{scope}_cohort_nhamcs_{min(years)}_{max(years)}.csv"


def write_full_source_scope_metadata(
    output_dir: Path,
    scope: str,
    years: list[int],
    pooled: pd.DataFrame,
    output_path: Path,
) -> None:
    binary = pooled[pooled["include_strict_binary"]]
    events = int(binary["admit"].sum())
    weighted_n = float(binary["pooled_weight"].sum()) if len(binary) else float("nan")
    weighted_events = float(binary.loc[binary["admit"] == 1, "pooled_weight"].sum()) if len(binary) else float("nan")
    metadata = {
        "run_id": run_id(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": dataset_name(years),
        "scope": scope,
        "years": years,
        "cohort_file": str(output_path),
        "strict_binary_n": int(len(binary)),
        "strict_binary_admissions": events,
        "weighted_strict_binary_n": round_or_none(weighted_n),
        "weighted_admission_prevalence": round_or_none(weighted_events / weighted_n if weighted_n else float("nan")),
        "method": (
            "Strict admit-vs-routine-home-discharge endpoint classification applied before active model scope filters. "
            "This file is for source-scope screening only and does not update e-dispo-v4.0 coefficients."
        ),
        "no_dataset_derived_promotion": True,
        "no_external_validation_claim": True,
    }
    (output_dir / f"{scope}_cohort_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )


def write_combined_yearly_outputs(yearly_output_dir: Path, output_dir: Path, years: list[int]) -> None:
    combine_yearly_csvs(
        yearly_output_dir,
        output_dir / "cohort_flow_by_year.csv",
        [f"cohort_flow_{year}.csv" for year in years],
    )
    combine_yearly_csvs(
        yearly_output_dir,
        output_dir / "endpoint_audit_by_year.csv",
        [f"endpoint_audit_{year}.csv" for year in years],
    )
    combine_yearly_csvs(
        yearly_output_dir,
        output_dir / "harmonization_audit_by_year.csv",
        [f"harmonization_audit_{year}.csv" for year in years],
    )
    combine_yearly_csvs(
        yearly_output_dir,
        output_dir / "missingness_by_year_and_endpoint.csv",
        [f"missingness_by_endpoint_{year}.csv" for year in years],
    )
    combine_yearly_csvs(
        yearly_output_dir,
        output_dir / "pain_unadjusted_rates_by_year.csv",
        [f"pain_unadjusted_rates_{year}.csv" for year in years],
    )


def combine_yearly_csvs(source_dir: Path, target: Path, names: list[str]) -> None:
    frames = []
    for name in names:
        path = source_dir / name
        if path.exists() and path.stat().st_size > 0:
            frames.append(pd.read_csv(path))
    if frames:
        pd.concat(frames, ignore_index=True).to_csv(target, index=False)
    else:
        target.write_text("", encoding="utf-8")


def write_metadata(
    output_dir: Path,
    config: dict[str, Any],
    years: list[int],
    pooled: pd.DataFrame,
    output_path: Path,
) -> None:
    binary = pooled[pooled["include_strict_binary"]]
    events = int(binary["admit"].sum())
    weighted_n = float(binary["pooled_weight"].sum()) if len(binary) else float("nan")
    weighted_events = float(binary.loc[binary["admit"] == 1, "pooled_weight"].sum()) if len(binary) else float("nan")
    metadata = {
        "run_id": run_id(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": dataset_name(years),
        "years": years,
        "year_count": len(years),
        "analytic_cohort_file": str(output_path),
        "weight_rule": "pooled_weight = PATWT / number_of_years",
        "design_rule": "pooled_stratum = interaction(year, CSTRATM); pooled_psu = interaction(year, CPSUM)",
        "strict_binary_n": int(len(binary)),
        "strict_binary_admissions": events,
        "weighted_strict_binary_n": round_or_none(weighted_n),
        "weighted_admission_prevalence": round_or_none(weighted_events / weighted_n if weighted_n else float("nan")),
        "event_count_gate": {
            "threshold": 100,
            "passed": events >= 100,
            "events": events,
        },
        "mapping_status": config.get("pool", {}).get("mapping_status", "unconfirmed_codebook_review_required"),
        "no_dataset_derived_promotion": True,
        "no_v4_adoption_claim": True,
    }
    (output_dir / "pooled_cohort_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )


def write_pooled_vs_2022(output_dir: Path, years: list[int], pooled: pd.DataFrame) -> None:
    binary = pooled[pooled["include_strict_binary"]]
    pooled_events = int(binary["admit"].sum())
    pooled_weighted_n = float(binary["pooled_weight"].sum()) if len(binary) else float("nan")
    pooled_weighted_events = float(binary.loc[binary["admit"] == 1, "pooled_weight"].sum()) if len(binary) else float("nan")
    year_2022 = binary[binary["year"].astype(str) == "2022"]
    lines = [
        "# Pooled Vs 2022 Comparison",
        "",
        "This file is generated before model fitting. It compares cohort size and endpoint prevalence only; coefficient and calibration comparisons require fitted outputs.",
        "",
        "## Pooled Cohort",
        "",
        f"- Years: {', '.join(str(year) for year in years)}",
        f"- Strict-binary N: {len(binary)}",
        f"- Admission events: {pooled_events}",
        f"- 100-event gate: {'passed' if pooled_events >= 100 else 'not passed'}",
        f"- Weighted admission prevalence: {percent_or_blank(pooled_weighted_events, pooled_weighted_n)}",
        "",
        "## 2022 Rows Inside Pooled Build",
        "",
        f"- Strict-binary N: {len(year_2022)}",
        f"- Admission events: {int(year_2022['admit'].sum()) if len(year_2022) else 0}",
        f"- Weighted admission prevalence using pooled weights: {percent_or_blank(float(year_2022.loc[year_2022['admit'] == 1, 'pooled_weight'].sum()) if len(year_2022) else float('nan'), float(year_2022['pooled_weight'].sum()) if len(year_2022) else float('nan'))}",
        "",
        "## Evidence Guardrails",
        "",
        "- Pooled outputs remain survey_weighted_candidate unless all evidence gates pass.",
        "- Pooling does not establish pain monotonicity by itself.",
        "- Candidate v4 remains a sensitivity model and is not adopted by this pipeline.",
        "",
    ]
    (output_dir / "pooled_vs_2022_comparison.md").write_text("\n".join(lines), encoding="utf-8")


def dataset_name(years: list[int]) -> str:
    return f"NHAMCS_{min(years)}_{max(years)}_POOLED"


def pooled_filename(years: list[int]) -> str:
    return f"analytic_cohort_nhamcs_{min(years)}_{max(years)}.csv"


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def round_or_none(value: float) -> float | None:
    if value is None or not math.isfinite(float(value)):
        return None
    return round(float(value), 8)


def percent_or_blank(numerator: float, denominator: float) -> str:
    if not math.isfinite(float(numerator)) or not math.isfinite(float(denominator)) or denominator == 0:
        return ""
    return f"{round(100 * numerator / denominator, 6)}%"


def run_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


if __name__ == "__main__":
    raise SystemExit(main())
