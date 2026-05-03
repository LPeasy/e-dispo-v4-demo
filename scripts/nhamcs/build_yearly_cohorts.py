#!/usr/bin/env python3
"""Build harmonized annual NHAMCS ED cohorts before pooled analysis."""

from __future__ import annotations

import argparse
import csv
import glob
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

import build_cohort


DEFAULT_CONFIG = Path("config/nhamcs_year_harmonization.yml")
DEFAULT_OUTPUT_DIR = Path("outputs/nhamcs/yearly")
OPTIONAL_DISPOSITION_COLUMNS = {"ELOPED"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build yearly NHAMCS cohorts for pooled analysis.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    parser.add_argument("--years", nargs="*", type=int)
    args = parser.parse_args(argv)

    config = read_config(args.config)
    years = args.years or [int(year) for year in config["pool"]["years"]]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    built_years: list[int] = []
    blockers: list[str] = []
    for year in years:
        year_config = year_config_for(config, year)
        if year_config is None:
            blockers.append(f"{year}: no harmonization entry was found.")
            write_year_blocker(
                args.output_dir,
                year,
                [f"No harmonization entry was found for {year}."],
                next_action="Add the year to config/nhamcs_year_harmonization.yml before pooling.",
            )
            continue

        source = find_year_source(year_config)
        if source is None:
            missing = source_candidates(year_config)
            blockers.append(f"{year}: source file missing.")
            write_year_blocker(
                args.output_dir,
                year,
                [f"No NHAMCS {year} source data file was found."],
                missing_raw_data=missing,
                next_action=f"Place the NHAMCS {year} ED public-use file under data/nhamcs/{year}/ or update the harmonization config.",
            )
            continue

        try:
            result = build_year_outputs(year, source, year_config, config, args.output_dir)
        except (FileNotFoundError, ValueError) as exc:
            blockers.append(f"{year}: {exc}")
            write_year_blocker(
                args.output_dir,
                year,
                [str(exc)],
                next_action=f"Correct the NHAMCS {year} source file or harmonization mapping, then rerun.",
            )
            continue

        write_year_outputs(result, args.output_dir)
        built_years.append(year)

    write_run_metadata(args.output_dir, config, years, built_years, blockers)
    if blockers:
        write_combined_blocker(args.output_dir, years, built_years, blockers)
        return 2

    print(f"Wrote yearly NHAMCS cohorts under {args.output_dir}")
    return 0


def read_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = read_yaml_config(text, path)
    if not isinstance(payload, dict):
        raise ValueError(f"Harmonization config must contain an object: {path}")
    return payload


def read_yaml_config(text: str, path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise ValueError(f"{path} is not JSON-compatible YAML, and PyYAML is unavailable.") from exc
    payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError(f"Harmonization config must contain an object: {path}")
    return payload


def year_config_for(config: dict[str, Any], year: int) -> dict[str, Any] | None:
    for item in config.get("years", []):
        if int(item["year"]) == int(year):
            return item
    return None


def find_year_source(year_config: dict[str, Any]) -> Path | None:
    configured = year_config.get("source_file")
    if isinstance(configured, str) and Path(configured).exists():
        return Path(configured)
    for pattern in year_config.get("source_globs", []):
        matches = sorted(Path(path) for path in glob.glob(str(pattern)))
        files = [path for path in matches if path.is_file()]
        if files:
            return files[0]
    return None


def source_candidates(year_config: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    source_file = year_config.get("source_file")
    if isinstance(source_file, str):
        candidates.append(source_file)
    candidates.extend(str(item) for item in year_config.get("source_globs", []))
    return candidates


def build_year_outputs(
    year: int,
    source: Path,
    year_config: dict[str, Any],
    pooled_config: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    df = build_cohort.read_source_file(source, output_dir / f"_source_extract_{year}")
    missing = missing_required_columns(df, year_config)
    if missing:
        raise ValueError(
            "Required NHAMCS columns are absent for "
            f"{year}: {', '.join(missing)}"
        )

    df = with_canonical_columns(df, year_config)
    config = build_cohort_config(year_config, pooled_config)
    weights = build_cohort.weight_series(df)
    masks = build_cohort.cohort_masks(df, config)
    endpoint_frame = df.loc[masks["non_trauma"]].copy()
    endpoint_frame["endpoint_class"] = build_cohort.classify_endpoint(endpoint_frame, config)
    endpoint_frame["admit"] = endpoint_frame["endpoint_class"].eq("admit").astype(int)
    endpoint_frame["include_strict_binary"] = endpoint_frame["endpoint_class"].isin(
        ["admit", "routine_home_discharge"]
    )

    analytic = build_cohort.build_model_frame(endpoint_frame, config)
    analytic = add_year_columns(analytic, endpoint_frame, year, year_config)
    flow = add_year_to_rows(
        year,
        relabel_2022_rows(build_cohort.cohort_flow_rows(df, masks, endpoint_frame, weights), year),
    )
    endpoint_audit = add_year_to_rows(year, build_cohort.endpoint_audit_rows(endpoint_frame))
    harmonization_audit = add_year_to_rows(
        year,
        relabel_dataset_rows(build_cohort.harmonization_audit_rows(endpoint_frame, analytic, config), f"NHAMCS_{year}"),
    )
    missingness = add_year_to_rows(
        year,
        relabel_dataset_rows(build_cohort.missingness_rows(analytic), f"NHAMCS_{year}"),
    )
    pain_rates = add_year_to_rows(
        year,
        relabel_dataset_rows(build_cohort.pain_rate_rows(analytic), f"NHAMCS_{year}"),
    )

    metadata = {
        "run_id": run_id(),
        "year": year,
        "dataset": f"NHAMCS_{year}",
        "source_file": str(source),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "record_count": int(len(df)),
        "strict_binary_n": int(analytic["include_strict_binary"].sum()),
        "strict_binary_admissions": int(analytic.loc[analytic["include_strict_binary"], "admit"].sum()),
        "mapping_status": pooled_config["pool"].get("mapping_status", "unconfirmed_codebook_review_required"),
        "known_coding_differences": year_config.get("known_coding_differences", []),
        "predictor_transform_metadata": pooled_config["pool"].get(
            "predictor_transforms",
            build_cohort.NHAMCS_SENTINEL_RULES,
        ),
        "survey_columns_present": {
            "PATWT": "PATWT" in df.columns,
            "CSTRATM": "CSTRATM" in df.columns,
            "CPSUM": "CPSUM" in df.columns,
        },
    }
    return {
        "year": year,
        "analytic": analytic,
        "cohort_flow": flow,
        "endpoint_audit": endpoint_audit,
        "harmonization_audit": harmonization_audit,
        "missingness": missingness,
        "pain_rates": pain_rates,
        "metadata": metadata,
    }


def build_cohort_config(year_config: dict[str, Any], pooled_config: dict[str, Any]) -> dict[str, Any]:
    return {
        "variables": {
            "sex": year_config["sex_variable"],
            "age": year_config["age_variable"],
            "reasonForVisit": year_config["rfv_variables"],
            "trauma": year_config["trauma_variable"],
            "surveyDesign": {
                "weight": year_config["patwt_variable"],
                "strata": year_config["cstratm_variable"],
                "psu": year_config["cpsum_variable"],
            },
            "predictors": {
                "painScale": year_config.get("pain_variable", "PAINSCALE"),
                "temperature": year_config.get("temperature_variable", "TEMPF"),
            },
            "dispositionFlags": year_config["disposition_flags"],
        },
        "codes": pooled_config["codes"],
    }


def missing_required_columns(df: pd.DataFrame, year_config: dict[str, Any]) -> list[str]:
    required = [
        year_config["sex_variable"],
        year_config["age_variable"],
        year_config["trauma_variable"],
        year_config["patwt_variable"],
        year_config["cstratm_variable"],
        year_config["cpsum_variable"],
    ]
    required.extend(year_config["rfv_variables"])
    for columns in year_config["disposition_flags"].values():
        required.extend(column for column in columns if column not in OPTIONAL_DISPOSITION_COLUMNS)
    missing = sorted({column for column in required if column not in df.columns})
    return missing


def with_canonical_columns(df: pd.DataFrame, year_config: dict[str, Any]) -> pd.DataFrame:
    out = df.copy()
    canonical_pairs = {
        year_config["patwt_variable"]: "PATWT",
        year_config["cstratm_variable"]: "CSTRATM",
        year_config["cpsum_variable"]: "CPSUM",
        year_config.get("pain_variable", "PAINSCALE"): "PAINSCALE",
        year_config.get("temperature_variable", "TEMPF"): "TEMPF",
        year_config.get("triage_variable", "IMMEDR"): "IMMEDR",
        year_config.get("heart_rate_variable", "PULSE"): "PULSE",
        year_config.get("systolic_bp_variable", "BPSYS"): "BPSYS",
    }
    for source, target in canonical_pairs.items():
        if source in out.columns and target not in out.columns:
            out[target] = out[source]
    return out


def add_year_columns(
    analytic: pd.DataFrame,
    endpoint_frame: pd.DataFrame,
    year: int,
    year_config: dict[str, Any],
) -> pd.DataFrame:
    out = analytic.copy()
    out["year"] = int(year)
    out["dataset"] = f"NHAMCS_{year}"
    out["record_id"] = [f"{year}-{i + 1}" for i in range(len(out))]
    out["sex"] = endpoint_frame[year_config["sex_variable"]].reset_index(drop=True)
    out["abdominal_pain_flag"] = True
    out["trauma_exclusion_flag"] = False
    out["endpoint_class"] = out["endpoint"]
    out["PATWT"] = out["weight"]
    out["CSTRATM"] = out["stratum"]
    out["CPSUM"] = out["psu"]
    ordered = [
        "year",
        "record_id",
        "dataset",
        "age",
        "sex",
        "age_band",
        "abdominal_pain_flag",
        "trauma_exclusion_flag",
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
        "PATWT",
        "CSTRATM",
        "CPSUM",
        "weight",
        "stratum",
        "psu",
        "pain_bin5",
        "vomiting_present",
        "nausea_present",
        "vomiting_rfv_position_tier",
        "hematemesis_present",
        "hematemesis_rfv_position_tier",
        "vomiting",
    ]
    return out[[column for column in ordered if column in out.columns]].reset_index(drop=True)


def add_year_to_rows(year: int, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append({"year": year, **row})
    return out


def relabel_2022_rows(rows: list[dict[str, Any]], year: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        if "step" in copy:
            copy["step"] = str(copy["step"]).replace("2022", str(year))
        out.append(copy)
    return out


def relabel_dataset_rows(rows: list[dict[str, Any]], dataset: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        if "dataset" in copy:
            copy["dataset"] = dataset
        out.append(copy)
    return out


def write_year_outputs(result: dict[str, Any], output_dir: Path) -> None:
    year = int(result["year"])
    write_csv(output_dir / f"cohort_flow_{year}.csv", result["cohort_flow"])
    write_csv(output_dir / f"endpoint_audit_{year}.csv", result["endpoint_audit"])
    write_csv(output_dir / f"harmonization_audit_{year}.csv", result["harmonization_audit"])
    write_csv(output_dir / f"missingness_by_endpoint_{year}.csv", result["missingness"])
    write_csv(output_dir / f"pain_unadjusted_rates_{year}.csv", result["pain_rates"])
    result["analytic"].to_csv(output_dir / f"analytic_cohort_{year}.csv", index=False)
    (output_dir / f"cohort_metadata_{year}.json").write_text(
        json.dumps(result["metadata"], indent=2),
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_year_blocker(
    output_dir: Path,
    year: int,
    blockers: list[str],
    *,
    missing_raw_data: list[str] | None = None,
    next_action: str,
) -> None:
    build_cohort.write_blocker_report(
        output_dir / f"blocker_report_{year}.md",
        source=f"NHAMCS {year}",
        blockers=blockers,
        missing_raw_data=missing_raw_data,
        outputs_written=[],
        next_action=next_action,
    )


def write_combined_blocker(
    output_dir: Path,
    requested_years: list[int],
    built_years: list[int],
    blockers: list[str],
) -> None:
    build_cohort.write_blocker_report(
        output_dir / "blocker_report.md",
        source="NHAMCS pooled yearly cohort construction",
        blockers=blockers,
        outputs_written=[str(output_dir / f"analytic_cohort_{year}.csv") for year in built_years],
        next_action=(
            "Resolve missing or unmapped annual public-use files before pooling. "
            f"Requested years: {', '.join(str(year) for year in requested_years)}."
        ),
    )


def write_run_metadata(
    output_dir: Path,
    config: dict[str, Any],
    requested_years: list[int],
    built_years: list[int],
    blockers: list[str],
) -> None:
    metadata = {
        "run_id": run_id(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "requested_years": requested_years,
        "built_years": built_years,
        "blockers": blockers,
        "pool": config.get("pool", {}),
        "no_dataset_derived_promotion": True,
    }
    (output_dir / "yearly_run_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )


def run_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


if __name__ == "__main__":
    raise SystemExit(main())
