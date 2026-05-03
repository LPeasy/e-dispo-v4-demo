#!/usr/bin/env python3
"""Build the NHAMCS 2022 strict binary analytic cohort and audit outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import code_lists


DEFAULT_DATA_DIR = Path("data/nhamcs")
DEFAULT_LEGACY_DATA_DIR = Path("data/raw/nhamcs_2022")
DEFAULT_OUTPUT_DIR = Path("outputs/nhamcs")
DEFAULT_BLOCKER_REPORT = Path("outputs/blocker_report.md")
DEFAULT_CONFIG = Path("scripts/nhamcs/config.example.json")

CORE_REQUIRED_COLUMNS = [
    "SEX",
    "AGE",
    "RFV1",
    "RFV2",
    "RFV3",
    "RFV4",
    "RFV5",
    "INJPOISAD",
    "ADMITHOS",
    "OBSHOS",
    "NOFU",
    "RETRNED",
    "RETREFFU",
    "OBSDIS",
    "TRANOTH",
    "TRANNH",
    "TRANPSYC",
    "DOA",
    "DIEDED",
    "LEFTAMA",
    "LWBS",
    "LBTC",
    "OTHDISP",
    "NODISP",
]

SURVEY_COLUMNS = ["PATWT", "CSTRATM", "CPSUM"]
MODEL_OPTIONAL_COLUMNS = ["PAINSCALE", "TEMPF", "IMMEDR", "PULSE", "BPSYS"]

NHAMCS_SENTINEL_RULES = {
    "pain_score": {
        "source_column": "PAINSCALE",
        "sentinels": [-8, -9],
        "notes": "-8 unknown; -9 blank; valid values are 0-10.",
    },
    "temp": {
        "source_column": "TEMPF",
        "sentinels": [-9],
        "scale": "tenths_fahrenheit",
        "units": "degrees_fahrenheit",
        "notes": "-9 blank; numeric values are stored in tenths of degrees F; 998 and 999 are 99.8 and 99.9 F.",
    },
    "acuity": {
        "source_column": "IMMEDR",
        "sentinels": [-8, -9],
        "notes": "-8 unknown; -9 blank.",
    },
    "HR": {
        "source_column": "PULSE",
        "sentinels": [-9, 998],
        "notes": "-9 blank; 998 DOPP/DOPPLER.",
    },
    "tachycardia_burden": {
        "source_column": "PULSE",
        "sentinels": [-9, 998],
        "scale": "derived_from_recoded_heart_rate",
        "units": "10_bpm_over_100",
        "notes": "max(HR - 100, 0) / 10 after PULSE sentinel recoding; missing when HR is missing.",
    },
    "SBP": {
        "source_column": "BPSYS",
        "sentinels": [-9],
        "notes": "-9 blank.",
    },
}

VOMITING_RFV_CODE = 15300
NAUSEA_RFV_CODE = 15250
HEMATEMESIS_RFV_CODE = 15802


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build NHAMCS 2022 analytic cohort outputs.")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR, type=Path)
    parser.add_argument("--legacy-data-dir", default=DEFAULT_LEGACY_DATA_DIR, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    parser.add_argument("--config", default=DEFAULT_CONFIG, type=Path)
    args = parser.parse_args(argv)

    source = find_source_file([args.data_dir, args.legacy_data_dir])
    if source is None:
        write_blocker_report(
            DEFAULT_BLOCKER_REPORT,
            source="NHAMCS 2022",
            blockers=[
                "No NHAMCS 2022 source data file was found.",
            ],
            missing_raw_data=[
                str(args.data_dir / "ed2022.dta"),
                str(args.data_dir / "ed2022-stata.zip"),
                str(args.data_dir / "*.sas7bdat"),
                str(args.data_dir / "*.csv"),
                str(args.legacy_data_dir / "*.dta"),
                str(args.legacy_data_dir / "*.zip"),
            ],
            outputs_written=[],
            next_action="Place NHAMCS 2022 data under data/nhamcs/ or data/raw/nhamcs_2022/, then rerun scripts/nhamcs/run_nhamcs_pipeline.py.",
        )
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = read_json(args.config)
    try:
        df = read_source_file(source, args.output_dir)
    except (ValueError, FileNotFoundError, zipfile.BadZipFile) as exc:
        write_blocker_report(
            args.output_dir / "blocker_report.md",
            source="NHAMCS 2022",
            blockers=[str(exc)],
            outputs_written=[],
            next_action="Provide a readable NHAMCS 2022 .dta, .sas7bdat, .csv, or Stata zip file.",
        )
        return 2

    missing_core = [column for column in CORE_REQUIRED_COLUMNS if column not in df.columns]
    if missing_core:
        write_blocker_report(
            args.output_dir / "blocker_report.md",
            source="NHAMCS 2022",
            blockers=["Required NHAMCS columns are absent."],
            missing_required_columns=missing_core,
            outputs_written=[],
            next_action="Confirm the input file is the NHAMCS 2022 ED public-use file or update the mapping config.",
        )
        return 2

    result = build_outputs(df, config, source)
    write_cohort_outputs(result, args.output_dir)
    print(f"Wrote NHAMCS cohort outputs under {args.output_dir}")
    return 0


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_source_file(data_dirs: list[Path]) -> Path | None:
    exact_names = ["ed2022.dta"]
    for data_dir in data_dirs:
        for name in exact_names:
            path = data_dir / name
            if path.exists():
                return path
        for pattern in ("*.dta", "*.sas7bdat", "*.csv"):
            matches = sorted(data_dir.glob(pattern))
            if matches:
                return matches[0]
        zip_path = data_dir / "ed2022-stata.zip"
        if zip_path.exists():
            return zip_path
        matches = sorted(data_dir.glob("*.zip"))
        if matches:
            return matches[0]
    return None


def read_source_file(path: Path, output_dir: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".zip":
        extract_dir = output_dir / "_source_extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as archive:
            members = [
                name
                for name in archive.namelist()
                if name.lower().endswith((".dta", ".csv", ".sas7bdat"))
            ]
            if not members:
                raise ValueError(f"No .dta, .csv, or .sas7bdat file found inside {path}")
            member = sorted(members)[0]
            archive.extract(member, extract_dir)
            return read_source_file(extract_dir / member, output_dir)
    if suffix == ".dta":
        return pd.read_stata(path, convert_categoricals=False)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".sas7bdat":
        return pd.read_sas(path, format="sas7bdat")
    raise ValueError(f"Unsupported NHAMCS input file type: {path}")


def build_outputs(df: pd.DataFrame, config: dict[str, Any], source_path: Path) -> dict[str, Any]:
    weights = weight_series(df)
    masks = cohort_masks(df, config)
    endpoint_frame = df.loc[masks["non_trauma"]].copy()
    endpoint_frame["endpoint_class"] = classify_endpoint(endpoint_frame, config)
    endpoint_frame["admit"] = endpoint_frame["endpoint_class"].eq("admit").astype(int)
    endpoint_frame["include_strict_binary"] = endpoint_frame["endpoint_class"].isin(
        ["admit", "routine_home_discharge"]
    )

    analytic = build_model_frame(endpoint_frame, config)
    flow = cohort_flow_rows(df, masks, endpoint_frame, weights)
    endpoint_audit = endpoint_audit_rows(endpoint_frame)
    missingness = missingness_rows(analytic)
    pain_rates = pain_rate_rows(analytic)
    harmonization_audit = harmonization_audit_rows(endpoint_frame, analytic, config)

    metadata = {
        "run_id": run_id(),
        "source_file": str(source_path),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "record_count": int(len(df)),
        "survey_columns_present": {column: column in df.columns for column in SURVEY_COLUMNS},
        "survey_design_columns_present": all(column in df.columns for column in SURVEY_COLUMNS),
        "survey_design_confirmed_from_codebook": False,
        "diagnosis_sensitivity_status": "not_built_no_confirmed_diagnosis_mapping",
        "predictor_transform_metadata": NHAMCS_SENTINEL_RULES,
        "cohort_order": [
            "all_records",
            "male_age_18_64",
            "abdominal_pain_rfv",
            "non_trauma_non_poisoning_non_adverse_effect",
            "strict_binary_endpoint",
        ],
    }
    return {
        "metadata": metadata,
        "analytic": analytic,
        "cohort_flow": flow,
        "endpoint_audit": endpoint_audit,
        "missingness": missingness,
        "pain_rates": pain_rates,
        "harmonization_audit": harmonization_audit,
    }


def cohort_masks(df: pd.DataFrame, config: dict[str, Any]) -> dict[str, pd.Series]:
    variables = config["variables"]
    codes = config["codes"]
    all_records = pd.Series(True, index=df.index)
    male_age = df[variables["sex"]].isin(codes["male"]) & df[variables["age"]].between(
        18, 64, inclusive="both"
    )
    abdominal = male_age & any_column_matches(
        df,
        variables["reasonForVisit"],
        [row["stored_code"] for row in code_lists.load_code_list("nhamcs_abdominal_pain_rfv")["codes"]],
    )
    non_trauma = abdominal & df[variables["trauma"]].isin(codes["nonTrauma"])
    return {
        "all_records": all_records,
        "male_age_18_64": male_age,
        "abdominal_pain_rfv": abdominal,
        "non_trauma": non_trauma,
    }


def any_column_matches(df: pd.DataFrame, columns: list[str], values: list[Any]) -> pd.Series:
    value_strings = {str(value).strip() for value in values}
    combined = pd.Series(False, index=df.index)
    for column in columns:
        if column not in df.columns:
            continue
        combined = combined | df[column].astype(str).str.strip().isin(value_strings)
    return combined


def classify_endpoint(df: pd.DataFrame, config: dict[str, Any]) -> pd.Series:
    true_values = config["codes"].get("flagTrue", [1, "1", "Y", "YES", True])
    flags = config["variables"]["dispositionFlags"]
    classes = pd.DataFrame(index=df.index)
    classes["admit"] = flag_mask(df, flags.get("admit", []) + flags.get("observationHospitalized", []), true_values)
    classes["routine_home_discharge"] = flag_mask(df, flags.get("homeRelease", []), true_values)
    classes["observation"] = flag_mask(df, flags.get("observationDischarged", []), true_values)
    classes["transfer"] = flag_mask(df, flags.get("transferAcute", []) + flags.get("transferOther", []), true_values)
    classes["death"] = flag_mask(df, flags.get("death", []), true_values)
    classes["AMA"] = flag_mask(df, ["LEFTAMA"], true_values)
    classes["LWBS_LBTC"] = flag_mask(df, ["LWBS", "LBTC", "ELOPED"], true_values)
    classes["other"] = flag_mask(df, ["OTHDISP"], true_values)
    classes["unknown_missing"] = flag_mask(df, ["NODISP"], true_values)

    active_count = classes.astype(int).sum(axis=1)
    endpoint = pd.Series("unknown_missing", index=df.index, dtype="object")
    for name in classes.columns:
        endpoint.loc[(active_count == 1) & classes[name]] = name
    endpoint.loc[active_count > 1] = "conflict"
    endpoint.loc[active_count == 0] = "unknown_missing"
    return endpoint


def flag_mask(df: pd.DataFrame, columns: list[str], true_values: list[Any]) -> pd.Series:
    true_strings = {str(value).strip().upper() for value in true_values}
    combined = pd.Series(False, index=df.index)
    for column in columns:
        if column not in df.columns:
            continue
        combined = combined | df[column].isin(true_values)
        combined = combined | df[column].astype(str).str.strip().str.upper().isin(true_strings)
    return combined


def build_model_frame(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    variables = config["variables"]
    predictors = variables.get("predictors", {})
    out = pd.DataFrame(index=frame.index)
    out["dataset"] = "NHAMCS_2022"
    out["endpoint"] = frame["endpoint_class"]
    out["include_strict_binary"] = frame["include_strict_binary"]
    out["admit"] = frame["admit"]
    out["weight"] = numeric_or_nan(frame.get("PATWT"))
    out["stratum"] = frame["CSTRATM"] if "CSTRATM" in frame.columns else np.nan
    out["psu"] = frame["CPSUM"] if "CPSUM" in frame.columns else np.nan
    out["age"] = numeric_or_nan(frame[variables["age"]])
    out["age_band"] = out["age"].map(age_band)

    pain_col = predictors.get("painScale", "PAINSCALE")
    if pain_col in frame.columns:
        out["pain_score"] = recode_nhamcs_pain_score(frame[pain_col])
    else:
        out["pain_score"] = np.nan
    out["pain_missing"] = out["pain_score"].isna().astype(int)
    out["pain_bin3"] = out["pain_score"].map(code_lists.assign_pain_bin3).map(
        {"0-3": "mild", "4-6": "moderate", "7-10": "severe"}
    )
    out["pain_bin5"] = out["pain_score"].map(code_lists.assign_pain_bin5)

    temp_col = predictors.get("temperature", "TEMPF")
    out["temp"] = recode_nhamcs_temperature_f(frame[temp_col]) if temp_col in frame.columns else np.nan
    fever_config = code_lists.load_code_list("fever_terms")
    threshold_f = float(fever_config["objective_thresholds"]["fever_temp_f"])
    out["fever_or_temp"] = np.where(out["temp"].notna(), (out["temp"] >= threshold_f).astype(int), np.nan)

    rfv_columns = variables.get("reasonForVisit", ["RFV1", "RFV2", "RFV3", "RFV4", "RFV5"])
    out["vomiting_present"] = any_column_matches(frame, rfv_columns, [VOMITING_RFV_CODE]).astype(int)
    out["nausea_present"] = any_column_matches(frame, rfv_columns, [NAUSEA_RFV_CODE]).astype(int)
    out["hematemesis_present"] = any_column_matches(frame, rfv_columns, [HEMATEMESIS_RFV_CODE]).astype(int)
    primary_vomiting = any_column_matches(frame, rfv_columns[:1], [VOMITING_RFV_CODE])
    secondary_vomiting = out["vomiting_present"].eq(1) & ~primary_vomiting
    out["vomiting_rfv_position_tier"] = np.select(
        [primary_vomiting, secondary_vomiting],
        ["primary_rfv1", "secondary_rfv2_5"],
        default="none",
    )
    primary_hematemesis = any_column_matches(frame, rfv_columns[:1], [HEMATEMESIS_RFV_CODE])
    secondary_hematemesis = out["hematemesis_present"].eq(1) & ~primary_hematemesis
    out["hematemesis_rfv_position_tier"] = np.select(
        [primary_hematemesis, secondary_hematemesis],
        ["primary_rfv1", "secondary_rfv2_5"],
        default="none",
    )
    out["vomiting"] = out["vomiting_present"]
    out["acuity"] = recode_nhamcs_numeric(frame["IMMEDR"], [-8, -9]) if "IMMEDR" in frame.columns else np.nan
    out["HR"] = recode_nhamcs_numeric(frame["PULSE"], [-9, 998]) if "PULSE" in frame.columns else np.nan
    out["tachycardia_burden"] = tachycardia_burden_from_hr(out["HR"])
    out["SBP"] = recode_nhamcs_numeric(frame["BPSYS"], [-9]) if "BPSYS" in frame.columns else np.nan
    return out.reset_index(drop=True)


def numeric_or_nan(values: Any) -> pd.Series:
    if values is None:
        return pd.Series(dtype="float64")
    return pd.to_numeric(values, errors="coerce")


def recode_nhamcs_pain_score(values: Any) -> pd.Series:
    return pd.Series(values).map(code_lists.parse_pain_score)


def recode_nhamcs_temperature_f(values: Any) -> pd.Series:
    numeric = numeric_or_nan(values).astype("float64")
    numeric = numeric.mask(numeric.isin(NHAMCS_SENTINEL_RULES["temp"]["sentinels"]))
    return numeric / 10.0


def recode_nhamcs_numeric(values: Any, sentinels: list[int | float]) -> pd.Series:
    numeric = numeric_or_nan(values).astype("float64")
    return numeric.mask(numeric.isin(sentinels))


def tachycardia_burden_from_hr(values: Any) -> pd.Series:
    numeric = numeric_or_nan(values).astype("float64")
    burden = (numeric - 100.0).clip(lower=0.0) / 10.0
    return burden.mask(numeric.isna())


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


def cohort_flow_rows(
    df: pd.DataFrame,
    masks: dict[str, pd.Series],
    endpoint_frame: pd.DataFrame,
    weights: pd.Series | None,
) -> list[dict[str, Any]]:
    steps = [
        ("Start with 2022 NHAMCS ED records", "all_records", "all records"),
        ("Restrict to male patients age 18-64", "male_age_18_64", "SEX in male codes and AGE 18-64"),
        ("Identify abdominal pain using RFV1-RFV5 code list", "abdominal_pain_rfv", "RFV1-RFV5 in 1545.0-1545.3 stored codes"),
        ("Exclude trauma/injury/poisoning/adverse-effect presentations", "non_trauma", "INJPOISAD == 4"),
    ]
    rows: list[dict[str, Any]] = []
    previous = pd.Series(False, index=df.index)
    previous_count = 0
    previous_weight = 0.0
    for i, (step, key, rule) in enumerate(steps):
        mask = masks[key]
        count = int(mask.sum())
        weighted = weighted_sum(weights, mask)
        if i == 0:
            excluded = 0
            weighted_excluded = 0.0
        else:
            excluded = previous_count - count
            weighted_excluded = previous_weight - weighted
        rows.append(
            {
                "step": step,
                "rule": rule,
                "unweighted_n": count,
                "weighted_n": round_or_blank(weighted),
                "excluded_n": excluded,
                "weighted_excluded_n": round_or_blank(weighted_excluded),
                "notes": "",
            }
        )
        previous = mask
        previous_count = count
        previous_weight = weighted

    binary = endpoint_frame["include_strict_binary"]
    binary_count = int(binary.sum())
    binary_weight = float(endpoint_frame.loc[binary, "PATWT"].sum()) if "PATWT" in endpoint_frame.columns else float("nan")
    rows.append(
        {
            "step": "Keep only strict binary endpoint",
            "rule": "endpoint_class in admit or routine_home_discharge after exclusions/conflicts",
            "unweighted_n": binary_count,
            "weighted_n": round_or_blank(binary_weight),
            "excluded_n": previous_count - binary_count,
            "weighted_excluded_n": round_or_blank(previous_weight - binary_weight),
            "notes": "routine_home_discharge is not computed as 1 - admit until after this denominator is fixed.",
        }
    )
    _ = previous
    return rows


def endpoint_audit_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    order = [
        "admit",
        "routine_home_discharge",
        "observation",
        "transfer",
        "death",
        "AMA",
        "LWBS_LBTC",
        "other",
        "unknown_missing",
        "conflict",
    ]
    for endpoint_class in order:
        subset = frame[frame["endpoint_class"] == endpoint_class]
        include = endpoint_class in {"admit", "routine_home_discharge"}
        rows.append(
            {
                "raw_disposition_class": endpoint_class,
                "unweighted_n": int(len(subset)),
                "weighted_n": round_or_blank(float(subset["PATWT"].sum()) if "PATWT" in subset.columns else float("nan")),
                "analytic_action": "include_strict_binary" if include else "exclude_from_strict_binary",
                "conflict_flag": "true" if endpoint_class == "conflict" else "false",
                "notes": "tabulated conflict; excluded before binary denominator" if endpoint_class == "conflict" else "",
            }
        )
    return rows


def harmonization_audit_rows(
    raw_frame: pd.DataFrame,
    analytic: pd.DataFrame,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    predictors = config["variables"].get("predictors", {})
    field_sources = {
        "pain_score": predictors.get("painScale", "PAINSCALE"),
        "temp": predictors.get("temperature", "TEMPF"),
        "acuity": "IMMEDR",
        "HR": "PULSE",
        "tachycardia_burden": "PULSE",
        "SBP": "BPSYS",
    }
    rows = []
    for field, source_column in field_sources.items():
        rule = NHAMCS_SENTINEL_RULES[field]
        raw = numeric_or_nan(raw_frame[source_column]) if source_column in raw_frame.columns else pd.Series(dtype="float64")
        recoded = analytic[field] if field in analytic.columns else pd.Series(dtype="float64")
        rows.append(harmonization_audit_row(field, source_column, raw, recoded, rule))

    fever = analytic["fever_or_temp"] if "fever_or_temp" in analytic.columns else pd.Series(dtype="float64")
    rows.append(
        harmonization_audit_row(
            "fever_or_temp",
            field_sources["temp"],
            numeric_or_nan(raw_frame[field_sources["temp"]]) if field_sources["temp"] in raw_frame.columns else pd.Series(dtype="float64"),
            fever,
            {
                "sentinels": NHAMCS_SENTINEL_RULES["temp"]["sentinels"],
                "scale": "derived_from_scaled_temperature",
                "units": "binary",
                "notes": "1 when scaled temperature >=100.4 F; 0 when valid scaled temperature <100.4 F; missing when temperature is missing.",
            },
        )
    )
    for field, note in {
        "vomiting_present": "1 when RFV1-RFV5 contains 15300 (Vomiting); 0 means not documented in RFV1-RFV5.",
        "nausea_present": "1 when RFV1-RFV5 contains 15250 (Nausea); kept separate from ordinary vomiting code 15300.",
        "hematemesis_present": "1 when RFV1-RFV5 contains 15802 (Vomiting blood/hematemesis); reserved for separate workflow.",
    }.items():
        if field not in analytic.columns:
            continue
        recoded = pd.to_numeric(analytic[field], errors="coerce")
        valid = recoded.dropna()
        rows.append(
            {
                "dataset": "NHAMCS_2022",
                "field": field,
                "source_column": "RFV1-RFV5",
                "raw_n": int(len(raw_frame)),
                "raw_missing_n": 0,
                "raw_sentinel_values": "",
                "raw_sentinel_n": 0,
                "post_recode_missing_n": int(recoded.isna().sum()),
                "valid_n": int(recoded.notna().sum()),
                "min": round_or_blank(float(valid.min())) if len(valid) else "",
                "median": round_or_blank(float(valid.median())) if len(valid) else "",
                "max": round_or_blank(float(valid.max())) if len(valid) else "",
                "scale": "rfv_binary_documentation",
                "units": "binary",
                "notes": note,
            }
        )
    return rows


def harmonization_audit_row(
    field: str,
    source_column: str,
    raw: pd.Series,
    recoded: pd.Series,
    rule: dict[str, Any],
) -> dict[str, Any]:
    sentinels = rule.get("sentinels", [])
    raw_numeric = pd.to_numeric(raw, errors="coerce")
    recoded_numeric = pd.to_numeric(recoded, errors="coerce")
    valid = recoded_numeric.dropna()
    return {
        "dataset": "NHAMCS_2022",
        "field": field,
        "source_column": source_column,
        "raw_n": int(len(raw_numeric)),
        "raw_missing_n": int(raw_numeric.isna().sum()),
        "raw_sentinel_values": ";".join(str(value) for value in sentinels),
        "raw_sentinel_n": int(raw_numeric.isin(sentinels).sum()) if len(raw_numeric) else 0,
        "post_recode_missing_n": int(recoded_numeric.isna().sum()),
        "valid_n": int(recoded_numeric.notna().sum()),
        "min": round_or_blank(float(valid.min())) if len(valid) else "",
        "median": round_or_blank(float(valid.median())) if len(valid) else "",
        "max": round_or_blank(float(valid.max())) if len(valid) else "",
        "scale": rule.get("scale", ""),
        "units": rule.get("units", ""),
        "notes": rule.get("notes", ""),
    }


def missingness_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    fields = [
        "age",
        "age_band",
        "pain_score",
        "pain_bin3",
        "vomiting",
        "vomiting_present",
        "nausea_present",
        "vomiting_rfv_position_tier",
        "hematemesis_present",
        "hematemesis_rfv_position_tier",
        "fever_or_temp",
        "temp",
        "acuity",
        "HR",
        "tachycardia_burden",
        "SBP",
    ]
    rows: list[dict[str, Any]] = []
    for endpoint in sorted(frame["endpoint"].dropna().unique()):
        subset = frame[frame["endpoint"] == endpoint]
        weights = subset["weight"] if "weight" in subset else None
        for field in fields:
            if field not in subset.columns:
                continue
            missing = subset[field].isna()
            n = int(len(subset))
            missing_n = int(missing.sum())
            weighted_n = float(weights.sum()) if weights is not None else float("nan")
            weighted_missing = float(weights[missing].sum()) if weights is not None else float("nan")
            rows.append(
                {
                    "dataset": "NHAMCS_2022",
                    "field": field,
                    "endpoint": endpoint,
                    "n": n,
                    "missing_n": missing_n,
                    "missing_pct": percent(missing_n, n),
                    "weighted_n": round_or_blank(weighted_n),
                    "weighted_missing_n": round_or_blank(weighted_missing),
                    "weighted_missing_pct": percent(weighted_missing, weighted_n),
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
        weighted_n = float(subset["weight"].sum()) if n else 0.0
        weighted_events = float(subset.loc[subset["admit"] == 1, "weight"].sum()) if n else 0.0
        rate = events / n if n else float("nan")
        ci_low, ci_high = normal_ci(rate, n)
        rows.append(
            {
                "dataset": "NHAMCS_2022",
                "pain_bin": pain_bin,
                "n": n,
                "events": events,
                "weighted_n": round_or_blank(weighted_n),
                "weighted_events": round_or_blank(weighted_events),
                "admit_pct": round_or_blank(rate * 100),
                "ci_low": round_or_blank(ci_low * 100),
                "ci_high": round_or_blank(ci_high * 100),
                "notes": "unweighted CI; weighted counts use PATWT when available",
            }
        )
    return rows


def normal_ci(rate: float, n: int) -> tuple[float, float]:
    if n == 0 or not math.isfinite(rate):
        return float("nan"), float("nan")
    se = math.sqrt(max(rate * (1 - rate), 0.0) / n)
    return max(0.0, rate - 1.96 * se), min(1.0, rate + 1.96 * se)


def weight_series(df: pd.DataFrame) -> pd.Series | None:
    if "PATWT" not in df.columns:
        return None
    return pd.to_numeric(df["PATWT"], errors="coerce").fillna(0.0)


def weighted_sum(weights: pd.Series | None, mask: pd.Series) -> float:
    if weights is None:
        return float("nan")
    return float(weights.loc[mask].sum())


def percent(numerator: float, denominator: float) -> str:
    if denominator is None or not math.isfinite(float(denominator)) or float(denominator) == 0:
        return ""
    return str(round(100 * float(numerator) / float(denominator), 6))


def round_or_blank(value: float) -> str:
    if value is None or not math.isfinite(float(value)):
        return ""
    return str(round(float(value), 6))


def write_cohort_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "cohort_flow_nhamcs.csv", result["cohort_flow"])
    write_csv(output_dir / "endpoint_audit_nhamcs.csv", result["endpoint_audit"])
    write_csv(output_dir / "missingness_by_endpoint.csv", result["missingness"])
    write_csv(output_dir / "pain_unadjusted_rates.csv", result["pain_rates"])
    write_csv(output_dir / "harmonization_audit.csv", result["harmonization_audit"])
    result["analytic"].to_csv(output_dir / "analytic_cohort_nhamcs.csv", index=False)
    (output_dir / "cohort_metadata.json").write_text(
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


def write_blocker_report(
    path: Path,
    *,
    source: str,
    blockers: list[str],
    missing_raw_data: list[str] | None = None,
    missing_required_columns: list[str] | None = None,
    outputs_written: list[str] | None = None,
    calibration_or_fitting_blockers: list[str] | None = None,
    next_action: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Blocker Report",
        "",
        f"Run ID: {run_id()}",
        f"Date: {datetime.now().date().isoformat()}",
        f"Source: {source}",
        "",
        "## Blockers",
        *[f"- {item}" for item in blockers],
        "",
        "## Missing Raw Data Or Permissions",
        *[f"- {item}" for item in (missing_raw_data or ["None reported."])],
        "",
        "## Unconfirmed Code Lists",
        "- NHAMCS abdominal pain RFV exact labels remain TODO-confirm-source.",
        "- NHAMCS trauma/injury/adverse-effect exclusion coding remains TODO-confirm-source.",
        "",
        "## Missing Required Columns",
        *[f"- {item}" for item in (missing_required_columns or ["None reported."])],
        "",
        "## Survey Design Confirmation",
        "- Required primary survey variables: PATWT, CSTRATM, CPSUM.",
        "",
        "## Endpoint Construction Blockers",
        "- None beyond blockers listed above.",
        "",
        "## Sparse Cell Or Event Blockers",
        "- Not evaluated when cohort construction is blocked.",
        "",
        "## Missingness Blockers",
        "- Not evaluated when cohort construction is blocked.",
        "",
        "## Calibration Or Fitting Blockers",
        *[f"- {item}" for item in (calibration_or_fitting_blockers or ["Model fitting was not run."])],
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
