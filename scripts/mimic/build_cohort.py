#!/usr/bin/env python3
"""Build the MIMIC-IV-ED replication/proxy-validation analytic cohort."""

from __future__ import annotations

import argparse
import csv
import gzip
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
NHAMCS_SCRIPT_DIR = PROJECT_ROOT / "scripts" / "nhamcs"
if str(NHAMCS_SCRIPT_DIR) not in sys.path:
    sys.path.append(str(NHAMCS_SCRIPT_DIR))

import code_lists  # noqa: E402


DEFAULT_DATA_DIR = Path("data/mimic")
DEFAULT_OUTPUT_DIR = Path("outputs/mimic")

REQUIRED_FILES = ["edstays", "triage", "diagnosis"]
OPTIONAL_FILES = ["vitalsign", "patients", "admissions", "age_at_ed"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build MIMIC-IV-ED analytic cohort outputs.")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    args = parser.parse_args(argv)

    files = discover_files(args.data_dir)
    missing = [name for name in REQUIRED_FILES if name not in files]
    if missing:
        write_blocker_report(
            args.output_dir / "blocker_report.md",
            blockers=["Required MIMIC-IV-ED source files are missing."],
            missing_raw_data=expected_paths(args.data_dir, missing),
            outputs_written=[],
            next_action="Place edstays, triage, and diagnosis CSV or CSV.GZ files under data/mimic/ or pass --data-dir.",
        )
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    tables = {name: read_csv(path) for name, path in files.items() if name in REQUIRED_FILES + OPTIONAL_FILES}
    try:
        result = build_outputs(tables, files)
    except ValueError as exc:
        write_blocker_report(
            args.output_dir / "blocker_report.md",
            blockers=[str(exc)],
            outputs_written=[],
            next_action="Provide age/sex linkage and required MIMIC-IV-ED columns, then rerun the pipeline.",
        )
        return 2

    write_outputs(result, args.output_dir)
    print(f"Wrote MIMIC cohort outputs under {args.output_dir}")
    return 0


def discover_files(data_dir: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for name in REQUIRED_FILES + OPTIONAL_FILES:
        for suffix in (".csv", ".csv.gz"):
            path = data_dir / f"{name}{suffix}"
            if path.exists():
                files[name] = path
                break
    return files


def expected_paths(data_dir: Path, names: list[str]) -> list[str]:
    paths: list[str] = []
    for name in names:
        paths.append(str(data_dir / f"{name}.csv"))
        paths.append(str(data_dir / f"{name}.csv.gz"))
    return paths


def read_csv(path: Path) -> pd.DataFrame:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
            return pd.read_csv(handle)
    return pd.read_csv(path)


def build_outputs(tables: dict[str, pd.DataFrame], files: dict[str, Path]) -> dict[str, Any]:
    edstays = normalize_columns(tables["edstays"])
    triage = normalize_columns(tables["triage"])
    diagnosis = normalize_columns(tables["diagnosis"])
    vitalsign = normalize_columns(tables["vitalsign"]) if "vitalsign" in tables else None
    patients = normalize_columns(tables["patients"]) if "patients" in tables else None
    admissions = normalize_columns(tables["admissions"]) if "admissions" in tables else None
    age_table = normalize_columns(tables["age_at_ed"]) if "age_at_ed" in tables else None

    require_columns(edstays, ["subject_id", "stay_id", "disposition"], "edstays")
    require_columns(triage, ["subject_id", "stay_id"], "triage")
    require_columns(diagnosis, ["subject_id", "stay_id"], "diagnosis")

    cohort = edstays.merge(triage, on=["subject_id", "stay_id"], how="left", suffixes=("", "_triage"))
    cohort = add_age_and_sex(cohort, patients, age_table)
    cohort = add_vitals(cohort, vitalsign)
    cohort = add_diagnosis_flags(cohort, diagnosis)

    all_mask = pd.Series(True, index=cohort.index)
    male_age = cohort["sex_normalized"].eq("M") & cohort["age_at_ed"].between(18, 64, inclusive="both")
    abdominal = male_age & cohort["chiefcomplaint"].map(code_lists.detect_abdominal_pain_text).fillna(False)
    trauma_text = cohort["chiefcomplaint"].map(code_lists.detect_trauma_text).fillna(False)
    non_trauma = abdominal & ~trauma_text & ~cohort["trauma_diagnosis_flag"]
    cohort["endpoint_class"] = classify_endpoint(cohort)
    cohort["include_strict_binary"] = cohort["endpoint_class"].isin(["admit", "routine_home_discharge"])
    cohort["admit"] = cohort["endpoint_class"].eq("admit").astype(int)

    analytic = build_model_frame(cohort)
    masks = {
        "all": all_mask,
        "male_age": male_age,
        "abdominal": abdominal,
        "non_trauma": non_trauma,
    }
    filtered = analytic[non_trauma.to_numpy()].copy()
    filtered["include_strict_binary"] = filtered["include_strict_binary"].astype(bool)

    metadata = {
        "run_id": run_id(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_files": {key: str(value) for key, value in files.items()},
        "record_count": int(len(edstays)),
        "age_linkage": age_linkage_status(cohort),
        "diagnosis_sensitivity_status": "trauma diagnosis exclusions applied when diagnosis codes are present; abdominal diagnosis inclusion sensitivity remains blocked pending exact mappings.",
        "cohort_order": [
            "edstays",
            "male_age_18_64",
            "abdominal_pain_chief_complaint",
            "exclude_trauma_text_or_diagnosis",
            "strict_binary_endpoint",
        ],
    }
    return {
        "metadata": metadata,
        "analytic": filtered.reset_index(drop=True),
        "cohort_flow": cohort_flow_rows(cohort, masks, non_trauma),
        "endpoint_audit": endpoint_audit_rows(filtered),
        "missingness": missingness_rows(filtered),
        "pain_rates": pain_rate_rows(filtered),
    }


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    return frame


def require_columns(frame: pd.DataFrame, columns: list[str], table_name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{table_name} missing required columns: {', '.join(missing)}")


def add_age_and_sex(
    cohort: pd.DataFrame,
    patients: pd.DataFrame | None,
    age_table: pd.DataFrame | None,
) -> pd.DataFrame:
    cohort = cohort.copy()
    if "gender" in cohort.columns:
        cohort["sex_normalized"] = cohort["gender"].map(normalize_sex)
    elif patients is not None and "gender" in patients.columns:
        cohort = cohort.merge(patients[["subject_id", "gender"]].drop_duplicates("subject_id"), on="subject_id", how="left")
        cohort["sex_normalized"] = cohort["gender"].map(normalize_sex)
    else:
        raise ValueError("Sex linkage unavailable. Provide edstays.gender or patients.gender.")

    if "age_at_ed" in cohort.columns:
        cohort["age_at_ed"] = pd.to_numeric(cohort["age_at_ed"], errors="coerce")
        cohort["age_source"] = "edstays.age_at_ed"
        return cohort
    if "age" in cohort.columns:
        cohort["age_at_ed"] = pd.to_numeric(cohort["age"], errors="coerce")
        cohort["age_source"] = "edstays.age"
        return cohort
    if age_table is not None:
        age_table = age_table.copy()
        if "age_at_ed" not in age_table.columns and "age" in age_table.columns:
            age_table["age_at_ed"] = age_table["age"]
        if "age_at_ed" not in age_table.columns:
            raise ValueError("Precomputed age table must include age_at_ed or age.")
        keys = ["subject_id", "stay_id"] if "stay_id" in age_table.columns else ["subject_id"]
        cohort = cohort.merge(age_table[keys + ["age_at_ed"]], on=keys, how="left")
        cohort["age_at_ed"] = pd.to_numeric(cohort["age_at_ed"], errors="coerce")
        cohort["age_source"] = "age_at_ed_table"
        return cohort
    if patients is not None and {"subject_id", "anchor_age", "anchor_year"}.issubset(patients.columns) and "intime" in cohort.columns:
        cohort = cohort.merge(
            patients[["subject_id", "anchor_age", "anchor_year"]].drop_duplicates("subject_id"),
            on="subject_id",
            how="left",
        )
        intime_year = pd.to_datetime(cohort["intime"], errors="coerce").dt.year
        cohort["age_at_ed"] = pd.to_numeric(cohort["anchor_age"], errors="coerce") + (
            intime_year - pd.to_numeric(cohort["anchor_year"], errors="coerce")
        )
        cohort["age_source"] = "patients.anchor_age_plus_ed_year_delta"
        return cohort
    raise ValueError("Age linkage unavailable. Provide age_at_ed.csv, edstays age, or patients anchor_age/anchor_year with edstays.intime.")


def normalize_sex(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().upper()
    if text in {"M", "MALE"}:
        return "M"
    if text in {"F", "FEMALE"}:
        return "F"
    return None


def add_vitals(cohort: pd.DataFrame, vitalsign: pd.DataFrame | None) -> pd.DataFrame:
    cohort = cohort.copy()
    if vitalsign is None:
        return cohort
    if not {"subject_id", "stay_id"}.issubset(vitalsign.columns):
        return cohort
    numeric_columns = [column for column in ["temperature", "heartrate", "resprate", "o2sat", "sbp", "dbp"] if column in vitalsign.columns]
    if not numeric_columns:
        return cohort
    summary = vitalsign.groupby(["subject_id", "stay_id"], as_index=False)[numeric_columns].median(numeric_only=True)
    return cohort.merge(summary, on=["subject_id", "stay_id"], how="left", suffixes=("", "_vitalsign"))


def add_diagnosis_flags(cohort: pd.DataFrame, diagnosis: pd.DataFrame) -> pd.DataFrame:
    diagnosis = diagnosis.copy()
    diagnosis["trauma_diagnosis_flag"] = diagnosis.apply(is_trauma_diagnosis, axis=1)
    summary = diagnosis.groupby(["subject_id", "stay_id"], as_index=False)["trauma_diagnosis_flag"].max()
    merged = cohort.merge(summary, on=["subject_id", "stay_id"], how="left")
    merged["trauma_diagnosis_flag"] = merged["trauma_diagnosis_flag"].fillna(False).astype(bool)
    return merged


def is_trauma_diagnosis(row: pd.Series) -> bool:
    code = str(row.get("icd_code", "")).strip().upper().replace(".", "")
    version = str(row.get("icd_version", "")).strip()
    if not code:
        return False
    if version == "10" or code[0:1] in {"S", "T"}:
        return code[0] in {"S", "T"}
    if code[:1] == "E":
        return True
    try:
        numeric = int(code[:3])
    except ValueError:
        return False
    return 800 <= numeric <= 999


def classify_endpoint(frame: pd.DataFrame) -> pd.Series:
    disposition = frame["disposition"].fillna("").astype(str).str.strip().str.upper()
    hadm_present = frame["hadm_id"].notna() & frame["hadm_id"].astype(str).str.strip().ne("") if "hadm_id" in frame.columns else pd.Series(False, index=frame.index)
    endpoint = pd.Series("unknown_missing", index=frame.index, dtype="object")
    endpoint.loc[disposition.eq("ADMITTED")] = "admit"
    endpoint.loc[disposition.eq("HOME")] = "routine_home_discharge"
    endpoint.loc[disposition.isin(["ELOPED"])] = "ELOPED"
    endpoint.loc[disposition.isin(["EXPIRED"])] = "EXPIRED"
    endpoint.loc[disposition.isin(["LEFT AGAINST MEDICAL ADVICE", "AMA"])] = "LEFT_AGAINST_MEDICAL_ADVICE"
    endpoint.loc[disposition.isin(["LEFT WITHOUT BEING SEEN", "LWBS"])] = "LEFT_WITHOUT_BEING_SEEN"
    endpoint.loc[disposition.str.contains("TRANSFER", na=False)] = "TRANSFER"
    endpoint.loc[disposition.isin(["OTHER"])] = "OTHER"
    conflict = (
        (disposition.eq("HOME") & hadm_present)
        | (disposition.eq("ADMITTED") & ~hadm_present)
        | (disposition.eq("") & hadm_present)
        | (endpoint.isin(["ELOPED", "EXPIRED", "LEFT_AGAINST_MEDICAL_ADVICE", "LEFT_WITHOUT_BEING_SEEN", "TRANSFER", "OTHER"]) & hadm_present)
    )
    endpoint.loc[conflict] = "conflict"
    return endpoint


def build_model_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=frame.index)
    out["dataset"] = "MIMIC_IV_ED"
    for column in ["subject_id", "stay_id", "hadm_id"]:
        out[column] = frame[column] if column in frame.columns else ""
    out["endpoint"] = frame["endpoint_class"]
    out["include_strict_binary"] = frame["include_strict_binary"]
    out["admit"] = frame["admit"]
    out["age"] = pd.to_numeric(frame["age_at_ed"], errors="coerce")
    out["age_band"] = out["age"].map(age_band)
    pain_source = first_present(frame, ["pain"])
    out["pain_score"] = pain_source.map(code_lists.parse_pain_score) if pain_source is not None else np.nan
    out["pain_missing"] = out["pain_score"].isna().astype(int)
    out["pain_non_numeric"] = pain_source.map(is_non_numeric_pain).astype(int) if pain_source is not None else 1
    out["pain_bin3"] = out["pain_score"].map(code_lists.assign_pain_bin3).map({"0-3": "mild", "4-6": "moderate", "7-10": "severe"})
    out["pain_bin5"] = out["pain_score"].map(code_lists.assign_pain_bin5)
    complaint = frame["chiefcomplaint"] if "chiefcomplaint" in frame.columns else pd.Series("", index=frame.index)
    out["vomiting"] = complaint.map(code_lists.detect_vomiting_text).astype(int)
    out["fever_text"] = complaint.map(code_lists.detect_fever_text).astype(int)
    out["temp"] = pd.to_numeric(first_present(frame, ["temperature", "temperature_vitalsign"]), errors="coerce")
    temp_c = np.where(out["temp"] > 45, (out["temp"] - 32) * 5 / 9, out["temp"])
    out["temp_c"] = temp_c
    out["fever_or_temp"] = np.where(out["temp"].notna(), (out["temp_c"] >= 38.0).astype(int), out["fever_text"])
    out["acuity"] = pd.to_numeric(first_present(frame, ["acuity"]), errors="coerce")
    out["HR"] = pd.to_numeric(first_present(frame, ["heartrate", "heartrate_vitalsign"]), errors="coerce")
    out["SBP"] = pd.to_numeric(first_present(frame, ["sbp", "sbp_vitalsign"]), errors="coerce")
    out["DBP"] = pd.to_numeric(first_present(frame, ["dbp", "dbp_vitalsign"]), errors="coerce")
    out["RR"] = pd.to_numeric(first_present(frame, ["resprate", "resprate_vitalsign"]), errors="coerce")
    out["O2_sat"] = pd.to_numeric(first_present(frame, ["o2sat", "o2sat_vitalsign"]), errors="coerce")
    return out


def first_present(frame: pd.DataFrame, columns: list[str]) -> pd.Series | None:
    for column in columns:
        if column in frame.columns:
            return frame[column]
    return None


def is_non_numeric_pain(value: object) -> bool:
    if value is None or pd.isna(value):
        return False
    parsed = code_lists.parse_pain_score(value)
    text = str(value).strip()
    if not text:
        return False
    return parsed is None


def age_band(value: Any) -> str | None:
    if pd.isna(value):
        return None
    age = int(value)
    if 18 <= age <= 29:
        return "18_29"
    if 30 <= age <= 44:
        return "30_44"
    if 45 <= age <= 54:
        return "45_54"
    if 55 <= age <= 64:
        return "55_64"
    return None


def cohort_flow_rows(cohort: pd.DataFrame, masks: dict[str, pd.Series], non_trauma: pd.Series) -> list[dict[str, Any]]:
    steps = [
        ("Start with edstays", "all", "all edstays records"),
        ("Restrict to male patients age 18-64", "male_age", "sex male and age_at_ed 18-64"),
        ("Identify abdominal pain using triage chiefcomplaint regex", "abdominal", "primary abdominal pain chief-complaint regex"),
        ("Exclude trauma/injury chief complaints and trauma diagnoses", "non_trauma", "chief complaint trauma regex false and trauma diagnosis flag false"),
    ]
    rows: list[dict[str, Any]] = []
    previous_n = 0
    for i, (step, key, rule) in enumerate(steps):
        n = int(masks[key].sum())
        rows.append(
            {
                "step": step,
                "rule": rule,
                "n": n,
                "excluded_n": 0 if i == 0 else previous_n - n,
                "notes": "",
            }
        )
        previous_n = n
    binary = cohort.loc[non_trauma, "include_strict_binary"]
    rows.append(
        {
            "step": "Keep only strict binary endpoint",
            "rule": "endpoint_class in admit or routine_home_discharge after conflicts/exclusions",
            "n": int(binary.sum()),
            "excluded_n": previous_n - int(binary.sum()),
            "notes": "routine_home_discharge is not computed as 1 - admit until after endpoint exclusions.",
        }
    )
    return rows


def endpoint_audit_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    order = [
        "admit",
        "routine_home_discharge",
        "ELOPED",
        "EXPIRED",
        "LEFT_AGAINST_MEDICAL_ADVICE",
        "LEFT_WITHOUT_BEING_SEEN",
        "TRANSFER",
        "OTHER",
        "unknown_missing",
        "conflict",
    ]
    for endpoint in order:
        subset = frame[frame["endpoint"] == endpoint]
        rows.append(
            {
                "raw_disposition": endpoint,
                "hadm_id_status": "mixed",
                "endpoint_class": endpoint,
                "include_primary_binary": str(endpoint in {"admit", "routine_home_discharge"}).lower(),
                "n": int(len(subset)),
                "admission_events": int(subset["admit"].sum()) if len(subset) else 0,
                "conflict_rule": "disposition_hadm_id_conflict" if endpoint == "conflict" else "",
                "exclusion_reason": "" if endpoint in {"admit", "routine_home_discharge"} else endpoint,
                "notes": "excluded and tabulated" if endpoint == "conflict" else "",
            }
        )
    return rows


def missingness_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    fields = ["age", "age_band", "pain_score", "pain_bin3", "pain_non_numeric", "vomiting", "fever_text", "temp", "fever_or_temp", "acuity", "HR", "SBP", "DBP", "RR", "O2_sat"]
    rows: list[dict[str, Any]] = []
    for endpoint in sorted(frame["endpoint"].dropna().unique()):
        subset = frame[frame["endpoint"] == endpoint]
        for field in fields:
            if field not in subset.columns:
                continue
            n = int(len(subset))
            missing_n = int(subset[field].isna().sum())
            rows.append(
                {
                    "dataset": "MIMIC_IV_ED",
                    "field": field,
                    "endpoint": endpoint,
                    "n": n,
                    "missing_n": missing_n,
                    "missing_pct": percent(missing_n, n),
                    "notes": "",
                }
            )
    return rows


def pain_rate_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    binary = frame[frame["include_strict_binary"]].copy()
    rows: list[dict[str, Any]] = []
    for pain_bin in ["mild", "moderate", "severe"]:
        subset = binary[binary["pain_bin3"] == pain_bin]
        n = int(len(subset))
        events = int(subset["admit"].sum()) if n else 0
        rate = events / n if n else float("nan")
        ci_low, ci_high = normal_ci(rate, n)
        rows.append(
            {
                "dataset": "MIMIC_IV_ED",
                "pain_bin": pain_bin,
                "n": n,
                "events": events,
                "admit_pct": round_or_blank(rate * 100),
                "ci_low": round_or_blank(ci_low * 100),
                "ci_high": round_or_blank(ci_high * 100),
                "notes": "unweighted MIMIC replication/proxy-validation rate",
            }
        )
    return rows


def normal_ci(rate: float, n: int) -> tuple[float, float]:
    if n == 0 or not math.isfinite(rate):
        return float("nan"), float("nan")
    se = math.sqrt(max(rate * (1 - rate), 0.0) / n)
    return max(0.0, rate - 1.96 * se), min(1.0, rate + 1.96 * se)


def percent(numerator: float, denominator: float) -> str:
    if denominator == 0:
        return ""
    return str(round(100 * float(numerator) / float(denominator), 6))


def round_or_blank(value: float) -> str:
    if value is None or not math.isfinite(float(value)):
        return ""
    return str(round(float(value), 6))


def age_linkage_status(cohort: pd.DataFrame) -> dict[str, Any]:
    return {
        "source": str(cohort["age_source"].dropna().iloc[0]) if "age_source" in cohort.columns and cohort["age_source"].notna().any() else "unknown",
        "missing_age_rows": int(cohort["age_at_ed"].isna().sum()) if "age_at_ed" in cohort.columns else len(cohort),
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "cohort_flow_mimic.csv", result["cohort_flow"])
    write_csv(output_dir / "endpoint_audit_mimic.csv", result["endpoint_audit"])
    write_csv(output_dir / "missingness_by_endpoint.csv", result["missingness"])
    write_csv(output_dir / "pain_unadjusted_rates.csv", result["pain_rates"])
    result["analytic"].to_csv(output_dir / "analytic_cohort_mimic.csv", index=False)
    (output_dir / "cohort_metadata.json").write_text(json.dumps(result["metadata"], indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_blocker_report(
    path: Path,
    *,
    blockers: list[str],
    missing_raw_data: list[str] | None = None,
    outputs_written: list[str] | None = None,
    next_action: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Blocker Report",
        "",
        f"Run ID: {run_id()}",
        f"Date: {datetime.now().date().isoformat()}",
        "Source: MIMIC-IV-ED",
        "",
        "## Blockers",
        *[f"- {item}" for item in blockers],
        "",
        "## Missing Raw Data Or Permissions",
        *[f"- {item}" for item in (missing_raw_data or ["None reported."])],
        "",
        "## Unconfirmed Code Lists",
        "- MIMIC abdominal-pain chief complaint regex remains TODO-confirm-source.",
        "- MIMIC trauma diagnosis exclusions remain TODO-confirm-source.",
        "",
        "## Missing Required Columns",
        "- See blockers above.",
        "",
        "## Endpoint Construction Blockers",
        "- Not evaluated when cohort construction is blocked.",
        "",
        "## Calibration Or Fitting Blockers",
        "- Model fitting was not run.",
        "",
        "## Outputs Written",
        *[f"- {item}" for item in (outputs_written or [str(path)])],
        "",
        "## Next Required Action",
        next_action,
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def run_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


if __name__ == "__main__":
    raise SystemExit(main())
