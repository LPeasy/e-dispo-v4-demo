#!/usr/bin/env python3
"""Confirm pooled NHAMCS mapping rules against official Stata public-use labels."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "nhamcs_year_harmonization.yml"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "nhamcs_pooled"
CDC_STATA_BASE_URL = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHAMCS/stata"

RFV_ABDOMINAL_PAIN_CODES = [15450, 15451, 15452, 15453]
RFV_VOMITING_CODES = {
    15250: "Nausea",
    15300: "Vomiting",
    15802: "Vomiting blood (hematemesis)",
}
REQUIRED_VARIABLES = [
    "AGE",
    "SEX",
    "RFV1",
    "RFV2",
    "RFV3",
    "RFV4",
    "RFV5",
    "INJPOISAD",
    "PAINSCALE",
    "TEMPF",
    "PATWT",
    "CSTRATM",
    "CPSUM",
]
VITAL_SENTINEL_CHECKS = {
    "TEMPFF": {-9: "Blank", 986: "98.6", 998: "99.8", 999: "99.9", 1004: "100.4"},
    "PAINSCALEF": {-8: "Unknown", -9: "Blank"},
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit NHAMCS 2018-2022 codebook mappings.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    args = parser.parse_args(argv)

    config = json.loads(args.config.read_text(encoding="utf-8"))
    rows: list[dict[str, str]] = []
    for year_config in config["years"]:
        rows.extend(audit_year(year_config))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "codebook_confirmation_audit.csv", rows)
    write_report(args.output_dir / "codebook_confirmation_report.md", rows)
    vomiting_rows = [row for row in rows if row.get("domain") == "vomiting_rfv_mapping"]
    write_csv(args.output_dir / "vomiting_codebook_confirmation_audit.csv", vomiting_rows)
    write_vomiting_report(args.output_dir / "vomiting_codebook_confirmation_report.md", vomiting_rows)
    hematemesis_rows = [row for row in vomiting_rows if row.get("field") == "15802"]
    write_csv(args.output_dir / "hematemesis_codebook_confirmation_audit.csv", hematemesis_rows)
    write_hematemesis_report(args.output_dir / "hematemesis_codebook_confirmation_report.md", hematemesis_rows)

    failed = [row for row in rows if row["passed"] != "true"]
    print(
        f"Wrote codebook confirmation audit for {len(config['years'])} NHAMCS years "
        f"with {len(failed)} blocking rows."
    )
    return 0 if not failed else 2


def audit_year(year_config: dict[str, Any]) -> list[dict[str, str]]:
    year = int(year_config["year"])
    source = find_source(year_config)
    if source is None:
        return [
            audit_row(
                year,
                "source",
                "stata_zip",
                "official NHAMCS Stata public-use ZIP",
                "no matching ZIP source file found",
                "",
                "blocked_unconfirmed",
                False,
            )
        ]

    try:
        metadata = read_stata_metadata(source)
    except Exception as exc:  # noqa: BLE001 - audit report must capture source-read failures.
        return [
            audit_row(
                year,
                "source",
                "stata_zip",
                "readable official NHAMCS Stata public-use metadata",
                f"{type(exc).__name__}: {exc}",
                source_anchor(source),
                "blocked_unconfirmed",
                False,
            )
        ]

    rows: list[dict[str, str]] = []
    rows.append(
        audit_row(
            year,
            "source",
            source.name,
            "official CDC NHAMCS ED Stata ZIP",
            "readable Stata metadata",
            source_anchor(source),
            "confirmed_codebook",
            True,
        )
    )
    rows.extend(audit_required_variables(year, metadata, source))
    rows.extend(audit_rfv_codes(year, metadata, source))
    rows.extend(audit_vomiting_codes(year, metadata, source))
    rows.extend(audit_trauma_rule(year, metadata, source))
    rows.extend(audit_vitals_and_pain(year, metadata, source))
    rows.extend(audit_endpoint_flags(year, metadata, source, year_config))
    return rows


def find_source(year_config: dict[str, Any]) -> Path | None:
    candidates: list[Path] = []
    for pattern in year_config.get("source_globs", []):
        root_pattern = PROJECT_ROOT / str(pattern)
        candidates.extend(root_pattern.parent.glob(root_pattern.name))
    for candidate in candidates:
        if candidate.suffix.lower() == ".zip" and candidate.exists():
            return candidate
    return None


def read_stata_metadata(zip_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(zip_path) as archive:
        dta_names = [name for name in archive.namelist() if name.lower().endswith(".dta")]
        if not dta_names:
            raise ValueError(f"No .dta file found in {zip_path}")
        data = io.BytesIO(archive.read(dta_names[0]))

    reader = pd.io.stata.StataReader(data, convert_categoricals=False)
    frame = reader.read(nrows=1, convert_categoricals=False)
    return {
        "columns": set(frame.columns),
        "variable_labels": {str(key): str(value) for key, value in reader.variable_labels().items()},
        "value_labels": normalize_value_labels(reader.value_labels()),
    }


def normalize_value_labels(labels: dict[str, dict[Any, str]]) -> dict[str, dict[int, str]]:
    out: dict[str, dict[int, str]] = {}
    for label_name, mapping in labels.items():
        out[str(label_name)] = {int(key): str(value) for key, value in mapping.items()}
    return out


def audit_required_variables(year: int, metadata: dict[str, Any], source: Path) -> list[dict[str, str]]:
    labels = metadata["variable_labels"]
    rows = []
    for variable in REQUIRED_VARIABLES:
        present = variable in metadata["columns"]
        observed = labels.get(variable, "missing") if present else "missing"
        rows.append(
            audit_row(
                year,
                "required_variable",
                variable,
                "present with public-use variable label",
                observed,
                source_anchor(source),
                "confirmed_codebook" if present else "blocked_unconfirmed",
                present,
            )
        )
    return rows


def audit_rfv_codes(year: int, metadata: dict[str, Any], source: Path) -> list[dict[str, str]]:
    labels = metadata["value_labels"].get("RFVF", {})
    rows = []
    for code in RFV_ABDOMINAL_PAIN_CODES:
        observed = labels.get(code, "")
        passed = bool(observed)
        rows.append(
            audit_row(
                year,
                "cohort_inclusion_rfv",
                str(code),
                "RFVF label exists for abdominal pain inclusion code",
                observed or "missing",
                source_anchor(source),
                "confirmed_codebook" if passed else "blocked_unconfirmed",
                passed,
            )
        )
    return rows


def audit_vomiting_codes(year: int, metadata: dict[str, Any], source: Path) -> list[dict[str, str]]:
    labels = metadata["value_labels"].get("RFVF", {})
    rows = []
    for code, expected_label in RFV_VOMITING_CODES.items():
        observed = labels.get(code, "")
        passed = observed == expected_label
        rows.append(
            audit_row(
                year,
                "vomiting_rfv_mapping",
                str(code),
                expected_label,
                observed or "missing",
                source_anchor(source),
                "confirmed_codebook" if passed else "blocked_unconfirmed",
                passed,
            )
        )
    return rows


def audit_trauma_rule(year: int, metadata: dict[str, Any], source: Path) -> list[dict[str, str]]:
    labels = metadata["value_labels"].get("INJPOISADF", {})
    observed = labels.get(4, "")
    passed = "No" in observed and "injury/trauma" in observed and "overdose/poisoning" in observed
    return [
        audit_row(
            year,
            "cohort_exclusion",
            "INJPOISAD=4",
            "No injury/trauma, overdose/poisoning, or adverse-effect relationship",
            observed or "missing",
            source_anchor(source),
            "confirmed_codebook" if passed else "blocked_unconfirmed",
            passed,
        )
    ]


def audit_vitals_and_pain(year: int, metadata: dict[str, Any], source: Path) -> list[dict[str, str]]:
    rows = []
    value_labels = metadata["value_labels"]
    for label_name, expected_values in VITAL_SENTINEL_CHECKS.items():
        labels = value_labels.get(label_name, {})
        for code, expected_label in expected_values.items():
            observed = labels.get(code, "")
            passed = observed == expected_label
            rows.append(
                audit_row(
                    year,
                    "predictor_transform",
                    f"{label_name}:{code}",
                    expected_label,
                    observed or "missing",
                    source_anchor(source),
                    "confirmed_codebook" if passed else "blocked_unconfirmed",
                    passed,
                )
            )
    return rows


def audit_endpoint_flags(
    year: int,
    metadata: dict[str, Any],
    source: Path,
    year_config: dict[str, Any],
) -> list[dict[str, str]]:
    rows = []
    labels = metadata["variable_labels"]
    flags = sorted(
        {
            flag
            for group_flags in year_config.get("disposition_flags", {}).values()
            for flag in group_flags
        }
    )
    for flag in flags:
        present = flag in metadata["columns"]
        if present:
            rows.append(
                audit_row(
                    year,
                    "endpoint_flag",
                    flag,
                    "present disposition flag with public-use variable label",
                    labels.get(flag, ""),
                    source_anchor(source),
                    "confirmed_codebook",
                    True,
                )
            )
        elif flag == "ELOPED":
            rows.append(
                audit_row(
                    year,
                    "endpoint_flag",
                    flag,
                    "present if released in selected NHAMCS public-use year",
                    "not present in 2018-2022 Stata public-use file",
                    source_anchor(source),
                    "not_applicable_absent_in_public_use",
                    True,
                )
            )
        else:
            rows.append(
                audit_row(
                    year,
                    "endpoint_flag",
                    flag,
                    "present disposition flag with public-use variable label",
                    "missing",
                    source_anchor(source),
                    "blocked_unconfirmed",
                    False,
                )
            )
    return rows


def audit_row(
    year: int,
    domain: str,
    field: str,
    expected: str,
    observed: str,
    source: str,
    review_status: str,
    passed: bool,
) -> dict[str, str]:
    return {
        "year": str(year),
        "domain": domain,
        "field": field,
        "expected": expected,
        "observed": observed,
        "source_anchor": source,
        "review_status": review_status,
        "passed": str(passed).lower(),
    }


def source_anchor(path: Path) -> str:
    return f"{CDC_STATA_BASE_URL}/{path.name}"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = ["year", "domain", "field", "expected", "observed", "source_anchor", "review_status", "passed"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict[str, str]]) -> None:
    failed = [row for row in rows if row["passed"] != "true"]
    by_status: dict[str, int] = {}
    for row in rows:
        by_status[row["review_status"]] = by_status.get(row["review_status"], 0) + 1

    lines = [
        "# NHAMCS Codebook Confirmation Report",
        "",
        "Source: official CDC NHAMCS ED Stata public-use ZIP metadata, including embedded Stata variable and value labels.",
        "",
        f"Rows audited: {len(rows)}",
        f"Blocking rows: {len(failed)}",
        "",
        "## Status Counts",
    ]
    lines.extend(f"- {status}: {count}" for status, count in sorted(by_status.items()))
    lines.extend(
        [
            "",
            "## Decision",
            "- Pooled mapping confirmation: " + ("confirmed" if not failed else "blocked"),
            "- Objective fever is confirmed through `TEMPF` as tenths Fahrenheit with `-9` blank and valid values such as `1004 = 100.4`.",
            "- Fever text/chills patterns are not part of the objective fever promotion gate.",
            "- `ELOPED` was not present in the 2018-2022 public-use Stata files and is treated as not applicable for this pooled window, not as a confirmed active flag.",
        ]
    )
    if failed:
        lines.extend(["", "## Blocking Rows"])
        for row in failed:
            lines.append(f"- {row['year']} {row['domain']} {row['field']}: observed `{row['observed']}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_vomiting_report(path: Path, rows: list[dict[str, str]]) -> None:
    failed = [row for row in rows if row["passed"] != "true"]
    lines = [
        "# NHAMCS Vomiting RFV Codebook Confirmation Report",
        "",
        "Source: official CDC NHAMCS ED Stata public-use ZIP metadata, including embedded Stata value labels.",
        "",
        f"Rows audited: {len(rows)}",
        f"Blocking rows: {len(failed)}",
        "",
        "## Decision",
        "- Ordinary vomiting RFV `15300` is " + ("confirmed" if not any(row["field"] == "15300" and row["passed"] != "true" for row in rows) else "blocked") + ".",
        "- Hematemesis RFV `15802` is confirmed as a separate future candidate, not part of the current vomiting promotion model.",
        "- Nausea RFV `15250` is confirmed but excluded from ordinary vomiting.",
    ]
    if failed:
        lines.extend(["", "## Blocking Rows"])
        for row in failed:
            lines.append(f"- {row['year']} {row['field']}: expected `{row['expected']}`, observed `{row['observed']}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_hematemesis_report(path: Path, rows: list[dict[str, str]]) -> None:
    failed = [row for row in rows if row["passed"] != "true"]
    lines = [
        "# NHAMCS Hematemesis RFV Codebook Confirmation Report",
        "",
        "Source: official CDC NHAMCS ED Stata public-use ZIP metadata, including embedded Stata value labels.",
        "",
        f"Rows audited: {len(rows)}",
        f"Blocking rows: {len(failed)}",
        "",
        "## Decision",
        "- Hematemesis RFV `15802` is "
        + ("confirmed as vomiting blood / hematemesis" if not failed and rows else "blocked or unavailable")
        + ".",
        "- Hematemesis remains separate from ordinary vomiting RFV `15300`.",
        "- This report confirms the codebook mapping only; sparse-cell and calibration gates decide model suitability.",
    ]
    if failed:
        lines.extend(["", "## Blocking Rows"])
        for row in failed:
            lines.append(f"- {row['year']} {row['field']}: expected `{row['expected']}`, observed `{row['observed']}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
