#!/usr/bin/env python3
"""Build a limited-evidence NHCS 2022 ED validation-dossier audit."""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

import build_cohort


DEFAULT_RAW_DIR = Path("data/raw/nhcs_2022")
DEFAULT_OUTPUT_DIR = Path("outputs/nhcs_2022")
DEFAULT_NHAMCS_POOLED_DIR = Path("outputs/nhamcs_pooled")
NHCS_DATA_FILE = "nhcs2022ed_stata.dta"
NHCS_CODEBOOK_FILE = "2022-NHCS-PUF-ED-CODEBOOK.pdf"
NHCS_TECH_DOC_FILE = "2022-NHCS-Tech-Doc.pdf"

EXPECTED_ED_TOTAL = 128_909_418.0
EXPECTED_ED_SE = 2_305_402.0
NORMAL_95 = 1.96

BASE_WEIGHT = "PUF_ENCWGT_BASE"
REPLICATE_WEIGHTS = [f"PUF_ENCWGT_{index}" for index in range(1, 101)]
DX_COLUMNS = [f"DX{index}" for index in range(1, 31)]
CCSR_SUMMARY_COLUMNS = [
    "CCSR_SYM004",
    "CCSR_CIR012",
    "CCSR_CIR019",
    "CCSR_END005",
    "CCSR_END011",
    "CCSR_INJ017",
]
REQUIRED_DATA_COLUMNS = [
    "PUF_ID",
    "year",
    "age",
    "sex",
    "newborn",
    "DISCHARGE_STATUS",
    "CCSR_SYM006",
    *CCSR_SUMMARY_COLUMNS,
    *DX_COLUMNS,
    BASE_WEIGHT,
    *REPLICATE_WEIGHTS,
]

STATUS_LABELS = {
    -9: "Missing",
    1: "Routine to home",
    2: "Left against medical advice",
    3: "Transfer to short-term facility",
    4: "Transfer to long-term facility",
    5: "Home health care",
    6: "Hospice care - home or medical facility",
    7: "Other",
    8: "Dead",
}
NONROUTINE_STATUS_CODES = {2, 3, 4, 5, 6, 7, 8}
ACUTE_ESCALATION_PROXY_CODES = {3, 4, 5, 6, 8}

SOURCE_URLS = {
    "cdc_nhcs_data_page": "https://www.cdc.gov/nchs/nhcs/data/index.html",
    "tech_doc": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHCS/2022/2022-NHCS-Tech-Doc.pdf",
    "ed_codebook": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHCS/2022/2022-NHCS-PUF-ED-CODEBOOK.pdf",
    "nchs_proportions": "https://www.cdc.gov/nchs/data/series/sr_02/sr02_175.pdf",
    "nchs_rates_counts": "https://www.cdc.gov/nchs/data/series/sr_02/sr02-200.pdf",
    "pricssa": "https://academic.oup.com/jssam/article/11/4/743/7136601",
    "tripod_ai": "https://www.bmj.com/content/385/bmj-2023-078378",
    "probast_ai": "https://www.bmj.com/content/388/bmj-2024-082505",
    "ahrq_ccsr": "https://hcup-us.ahrq.gov/toolssoftware/ccsr/dxccsr.jsp",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build NHCS 2022 ED public-use audit outputs.")
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    parser.add_argument("--nhamcs-pooled-dir", default=DEFAULT_NHAMCS_POOLED_DIR, type=Path)
    args = parser.parse_args(argv)

    data_path = args.raw_dir / NHCS_DATA_FILE
    required_raw_files = [
        data_path,
        args.raw_dir / NHCS_CODEBOOK_FILE,
        args.raw_dir / NHCS_TECH_DOC_FILE,
    ]
    missing_files = [str(path) for path in required_raw_files if not path.exists()]
    if missing_files:
        write_blocker(
            args.output_dir,
            blockers=["Required NHCS 2022 ED public-use input files are missing."],
            missing_raw_data=missing_files,
            next_action="Download the NHCS 2022 ED Stata file, ED codebook, and technical documentation into data/raw/nhcs_2022/.",
        )
        return 2

    try:
        all_columns = read_stata_columns(data_path)
    except (ValueError, OSError) as exc:
        write_blocker(
            args.output_dir,
            blockers=[f"Unable to read NHCS Stata metadata: {exc}"],
            next_action="Confirm nhcs2022ed_stata.dta is readable and was fully downloaded.",
        )
        return 2

    missing_columns = [column for column in REQUIRED_DATA_COLUMNS if column not in all_columns]
    if missing_columns:
        write_blocker(
            args.output_dir,
            blockers=["Required NHCS 2022 ED columns are absent."],
            missing_required_columns=missing_columns,
            next_action="Confirm the input file is the 2022 NHCS ED public-use Stata file.",
        )
        return 2

    try:
        frame = pd.read_stata(data_path, columns=REQUIRED_DATA_COLUMNS, convert_categoricals=False)
    except (ValueError, OSError) as exc:
        write_blocker(
            args.output_dir,
            blockers=[f"Unable to read NHCS Stata data: {exc}"],
            next_action="Confirm nhcs2022ed_stata.dta is readable and was fully downloaded.",
        )
        return 2

    result = build_outputs(frame, all_columns=all_columns, nhamcs_pooled_dir=args.nhamcs_pooled_dir)
    write_outputs(result, args.output_dir)
    print(f"Wrote NHCS 2022 ED audit outputs under {args.output_dir}")
    return 0


def read_stata_columns(path: Path) -> list[str]:
    reader = pd.read_stata(path, chunksize=1, convert_categoricals=False)
    try:
        first = next(reader)
    except StopIteration as exc:
        raise ValueError("NHCS Stata file has no rows.") from exc
    return list(first.columns)


def write_blocker(
    output_dir: Path,
    *,
    blockers: list[str],
    missing_raw_data: list[str] | None = None,
    missing_required_columns: list[str] | None = None,
    next_action: str,
) -> None:
    build_cohort.write_blocker_report(
        output_dir / "blocker_report.md",
        source="NHCS 2022 ED public-use audit",
        blockers=blockers,
        missing_raw_data=missing_raw_data,
        missing_required_columns=missing_required_columns,
        outputs_written=[],
        calibration_or_fitting_blockers=[
            "No model fitting is part of the NHCS public-use audit.",
            "The NHCS ED public-use file lacks active e-dispo-v4.0 predictors and the strict endpoint.",
        ],
        next_action=next_action,
    )


def build_outputs(
    frame: pd.DataFrame,
    *,
    all_columns: list[str] | None = None,
    nhamcs_pooled_dir: Path | None = None,
    replicate_weights: list[str] | None = None,
) -> dict[str, Any]:
    rep_cols = replicate_weights or [column for column in REPLICATE_WEIGHTS if column in frame.columns]
    required_present = [column for column in REQUIRED_DATA_COLUMNS if column in frame.columns]
    all_columns = all_columns or list(frame.columns)

    working = frame.copy()
    working["adult_male_18_64_not_newborn"] = adult_male_18_64_not_newborn(working)
    working["abdominal_proxy"] = working["adult_male_18_64_not_newborn"] & numeric_eq(working["CCSR_SYM006"], 1)
    working["injury_trauma_proxy"] = injury_trauma_proxy(working)
    working["abdominal_proxy_noninjury_sensitivity"] = working["abdominal_proxy"] & ~working["injury_trauma_proxy"]
    working["abdominal_proxy_known_discharge"] = working["abdominal_proxy"] & ~numeric_eq(working["DISCHARGE_STATUS"], -9)

    outputs = {
        "metadata": metadata(rep_cols),
        "schema_inventory": schema_inventory(working, all_columns, required_present),
        "weight_validation": weight_validation(working, rep_cols),
        "cohort_flow": cohort_flow(working, rep_cols),
        "discharge_status_summary": discharge_status_summary(working, rep_cols),
        "proxy_endpoint_sensitivity": proxy_endpoint_sensitivity(working, rep_cols),
        "top_diagnoses_abdominal_proxy": top_diagnoses_and_ccsr_flags(working, rep_cols),
    }
    outputs["nhcs_vs_nhamcs_2022_comparison"] = nhcs_vs_nhamcs_2022_comparison(
        outputs["cohort_flow"],
        nhamcs_pooled_dir or DEFAULT_NHAMCS_POOLED_DIR,
    )
    outputs["validation_dossier"] = validation_dossier(outputs)
    return outputs


def metadata(rep_cols: list[str]) -> dict[str, Any]:
    return {
        "run_id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "NHCS 2022 ED public-use file",
        "replicate_weight_method": "delete-a-group jackknife with JKCOEFS=1",
        "replicate_weight_count": len(rep_cols),
        "evidence_promotion_allowed": False,
        "external_validation_claim": False,
        "active_model_changed": False,
    }


def adult_male_18_64_not_newborn(frame: pd.DataFrame) -> pd.Series:
    age = pd.to_numeric(frame["age"], errors="coerce")
    return numeric_eq(frame["sex"], 1) & age.between(18, 64, inclusive="both") & numeric_eq(frame["newborn"], 2)


def injury_trauma_proxy(frame: pd.DataFrame) -> pd.Series:
    dx_cols = [column for column in DX_COLUMNS if column in frame.columns]
    if dx_cols:
        dx_flag = pd.DataFrame(
            {
                column: frame[column].astype("string").str.upper().str.match(r"^[ST]", na=False)
                for column in dx_cols
            }
        ).any(axis=1)
    else:
        dx_flag = pd.Series(False, index=frame.index)
    ccsr_flag = numeric_eq(frame["CCSR_INJ017"], 1) if "CCSR_INJ017" in frame.columns else pd.Series(False, index=frame.index)
    return dx_flag | ccsr_flag


def numeric_eq(series: pd.Series, value: int | float) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").eq(value)


def schema_inventory(frame: pd.DataFrame, all_columns: list[str], required_present: list[str]) -> list[dict[str, Any]]:
    rows = []
    row_count = len(frame)
    selected = set(frame.columns)
    for column in all_columns:
        rows.append(
            {
                "column": column,
                "present": True,
                "required_for_audit": column in REQUIRED_DATA_COLUMNS,
                "required_role": required_role(column),
                "row_count": row_count,
                "missing_count": missing_count(frame[column]) if column in selected else "",
                "notes": schema_note(column),
            }
        )
    for column in REQUIRED_DATA_COLUMNS:
        if column not in all_columns:
            rows.append(
                {
                    "column": column,
                    "present": False,
                    "required_for_audit": True,
                    "required_role": required_role(column),
                    "row_count": row_count,
                    "missing_count": "",
                    "notes": "required column absent",
                }
            )
    missing_required = sorted(set(REQUIRED_DATA_COLUMNS) - set(required_present))
    if missing_required:
        rows.append(
            {
                "column": "__missing_required_columns__",
                "present": False,
                "required_for_audit": True,
                "required_role": "audit_guardrail",
                "row_count": row_count,
                "missing_count": "",
                "notes": "; ".join(missing_required),
            }
        )
    return rows


def required_role(column: str) -> str:
    if column == "PUF_ID":
        return "identifier"
    if column in {"year", "age", "sex", "newborn"}:
        return "demographic_scope"
    if column == "DISCHARGE_STATUS":
        return "proxy_discharge_status"
    if column == "CCSR_SYM006":
        return "diagnosis_coded_abdominal_proxy"
    if column in CCSR_SUMMARY_COLUMNS:
        return "diagnosis_coded_context_flag"
    if column in DX_COLUMNS:
        return "diagnosis_code"
    if column == BASE_WEIGHT:
        return "base_weight"
    if column in REPLICATE_WEIGHTS:
        return "replicate_weight"
    return "not_used_by_audit"


def schema_note(column: str) -> str:
    if column == "CCSR_SYM006":
        return "Diagnosis-coded abdominal symptom proxy; not a chief-complaint substitute."
    if column == "DISCHARGE_STATUS":
        return "Discharge-status proxy only; not the strict same-hospital admission endpoint."
    if column in REPLICATE_WEIGHTS:
        return "NHCS ED replicate weight for delete-a-group jackknife variance."
    return ""


def missing_count(series: pd.Series) -> int:
    if pd.api.types.is_numeric_dtype(series):
        return int(series.isna().sum() + pd.to_numeric(series, errors="coerce").eq(-9).sum())
    return int(series.isna().sum() + series.astype("string").eq("-9").sum())


def weight_validation(frame: pd.DataFrame, rep_cols: list[str]) -> list[dict[str, Any]]:
    estimate = count_estimate(frame, pd.Series(True, index=frame.index), rep_cols)
    return [
        {
            "metric": "ed_total_visits",
            "estimate": round_float(estimate["estimate"]),
            "standard_error": round_float(estimate["standard_error"]),
            "published_estimate": int(EXPECTED_ED_TOTAL),
            "published_standard_error": int(EXPECTED_ED_SE),
            "estimate_difference": round_float(estimate["estimate"] - EXPECTED_ED_TOTAL),
            "standard_error_difference": round_float(estimate["standard_error"] - EXPECTED_ED_SE),
            "pass": abs(estimate["estimate"] - EXPECTED_ED_TOTAL) < 1.0
            and abs(estimate["standard_error"] - EXPECTED_ED_SE) < 1.0,
            "method": "PUF_ENCWGT_BASE total; PUF_ENCWGT_1-PUF_ENCWGT_100 delete-a-group jackknife with JKCOEFS=1.",
        }
    ]


def cohort_flow(frame: pd.DataFrame, rep_cols: list[str]) -> list[dict[str, Any]]:
    all_ed = pd.Series(True, index=frame.index)
    adult_male = frame["adult_male_18_64_not_newborn"]
    abdominal = frame["abdominal_proxy"]
    injury = abdominal & frame["injury_trauma_proxy"]
    noninjury = frame["abdominal_proxy_noninjury_sensitivity"]
    known_discharge = frame["abdominal_proxy_known_discharge"]
    rows = [
        flow_row(frame, rep_cols, "all_ed_records", "Start with all NHCS 2022 ED PUF records", all_ed, None),
        flow_row(frame, rep_cols, "adult_male_18_64_not_newborn", "Restrict to male patients age 18-64 and not newborn", adult_male, all_ed),
        flow_row(frame, rep_cols, "adult_male_abdominal_proxy", "Identify diagnosis-coded abdominal symptom proxy with CCSR_SYM006 = 1", abdominal, adult_male),
        flow_row(frame, rep_cols, "possible_injury_trauma_proxy", "Flag possible injury/trauma proxy in adult-male abdominal slice", injury, abdominal),
        flow_row(frame, rep_cols, "noninjury_sensitivity_slice", "Adult-male abdominal proxy excluding possible injury/trauma proxy", noninjury, abdominal),
        flow_row(frame, rep_cols, "known_discharge_status", "Adult-male abdominal proxy with DISCHARGE_STATUS not missing", known_discharge, abdominal),
    ]
    return rows


def flow_row(
    frame: pd.DataFrame,
    rep_cols: list[str],
    step: str,
    rule: str,
    mask: pd.Series,
    parent_mask: pd.Series | None,
) -> dict[str, Any]:
    estimate = count_estimate(frame, mask, rep_cols)
    reliability = reliability_for_count(int(mask.sum()), estimate["estimate"], estimate["standard_error"])
    if parent_mask is None:
        excluded_n = 0
        weighted_excluded = 0.0
    else:
        excluded = parent_mask & ~mask
        excluded_n = int(excluded.sum())
        weighted_excluded = count_estimate(frame, excluded, rep_cols)["estimate"]
    return {
        "step": step,
        "rule": rule,
        "unweighted_n": int(mask.sum()),
        "weighted_n": round_float(estimate["estimate"]),
        "standard_error": round_float(estimate["standard_error"]),
        "ci_low": round_float(estimate["ci_low"]),
        "ci_high": round_float(estimate["ci_high"]),
        "excluded_from_parent_n": excluded_n,
        "weighted_excluded_from_parent": round_float(weighted_excluded),
        "reliability_status": reliability["status"],
        "reliability_reasons": reliability["reasons"],
        "notes": evidence_boundary_note(step),
    }


def evidence_boundary_note(step: str) -> str:
    if step == "adult_male_abdominal_proxy":
        return "CCSR_SYM006 is diagnosis-coded abdominal symptom context, not a chief complaint."
    if step == "known_discharge_status":
        return "DISCHARGE_STATUS is proxy context, not the strict active endpoint."
    return ""


def discharge_status_summary(frame: pd.DataFrame, rep_cols: list[str]) -> list[dict[str, Any]]:
    domain = frame["abdominal_proxy"]
    rows = []
    for code, label in STATUS_LABELS.items():
        event = domain & numeric_eq(frame["DISCHARGE_STATUS"], code)
        rows.append(proportion_row(frame, rep_cols, "adult_male_abdominal_proxy", f"discharge_status_{code}", label, domain, event))
    return rows


def proxy_endpoint_sensitivity(frame: pd.DataFrame, rep_cols: list[str]) -> list[dict[str, Any]]:
    domain = frame["abdominal_proxy"]
    known = domain & ~numeric_eq(frame["DISCHARGE_STATUS"], -9)
    rows = [
        proportion_row(
            frame,
            rep_cols,
            "adult_male_abdominal_proxy_known_discharge",
            "routine_home_proxy",
            "Routine to home among known discharge status",
            known,
            known & numeric_eq(frame["DISCHARGE_STATUS"], 1),
        ),
        proportion_row(
            frame,
            rep_cols,
            "adult_male_abdominal_proxy_known_discharge",
            "nonroutine_discharge_proxy",
            "Any non-routine discharge status among known discharge status",
            known,
            known & numeric_in(frame["DISCHARGE_STATUS"], NONROUTINE_STATUS_CODES),
        ),
        proportion_row(
            frame,
            rep_cols,
            "adult_male_abdominal_proxy_known_discharge",
            "acute_escalation_proxy",
            "Transfer, home health, hospice, or death among known discharge status",
            known,
            known & numeric_in(frame["DISCHARGE_STATUS"], ACUTE_ESCALATION_PROXY_CODES),
        ),
        proportion_row(
            frame,
            rep_cols,
            "adult_male_abdominal_proxy",
            "missing_discharge_status",
            "Missing DISCHARGE_STATUS in adult-male abdominal proxy slice",
            domain,
            domain & numeric_eq(frame["DISCHARGE_STATUS"], -9),
        ),
    ]
    for row in rows:
        row["validation_claim"] = "not_external_validation"
        row["endpoint_caveat"] = "DISCHARGE_STATUS does not encode the active same-hospital admission vs routine ED discharge endpoint."
    return rows


def numeric_in(series: pd.Series, values: set[int]) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").isin(values)


def proportion_row(
    frame: pd.DataFrame,
    rep_cols: list[str],
    domain_name: str,
    metric: str,
    label: str,
    denominator_mask: pd.Series,
    numerator_mask: pd.Series,
) -> dict[str, Any]:
    count = count_estimate(frame, numerator_mask, rep_cols)
    prop = proportion_estimate(frame, denominator_mask, numerator_mask, rep_cols)
    count_reliability = reliability_for_count(int(numerator_mask.sum()), count["estimate"], count["standard_error"])
    prop_reliability = reliability_for_proportion(
        denominator_n=int(denominator_mask.sum()),
        event_n=int(numerator_mask.sum()),
        proportion=prop["estimate"],
        standard_error=prop["standard_error"],
        replicate_df=max(len(rep_cols) - 1, 0),
    )
    return {
        "domain": domain_name,
        "metric": metric,
        "label": label,
        "unweighted_denominator_n": int(denominator_mask.sum()),
        "unweighted_numerator_n": int(numerator_mask.sum()),
        "weighted_denominator": round_float(prop["denominator"]),
        "weighted_count": round_float(count["estimate"]),
        "count_standard_error": round_float(count["standard_error"]),
        "weighted_proportion": round_float(prop["estimate"]),
        "proportion_standard_error": round_float(prop["standard_error"]),
        "proportion_ci_low": round_float(prop["ci_low"]),
        "proportion_ci_high": round_float(prop["ci_high"]),
        "effective_denominator_n": round_float(prop_reliability["effective_n"]),
        "count_reliability_status": count_reliability["status"],
        "count_reliability_reasons": count_reliability["reasons"],
        "proportion_reliability_status": prop_reliability["status"],
        "proportion_reliability_reasons": prop_reliability["reasons"],
    }


def top_diagnoses_and_ccsr_flags(frame: pd.DataFrame, rep_cols: list[str], limit: int = 20) -> list[dict[str, Any]]:
    domain = frame["abdominal_proxy"]
    rows = []
    dx1 = frame["DX1"].astype("string").fillna("Missing")
    for code in dx1[domain].value_counts().head(limit).index:
        mask = domain & dx1.eq(code)
        rows.append(category_summary_row(frame, rep_cols, "DX1", str(code), f"DX1 {code}", domain, mask))

    for column in [col for col in CCSR_SUMMARY_COLUMNS if col in frame.columns]:
        mask = domain & numeric_eq(frame[column], 1)
        rows.append(category_summary_row(frame, rep_cols, "CCSR", column, ccsr_label(column), domain, mask))
    rows.sort(key=lambda row: (row["category_type"] != "DX1", -float(row["weighted_count"])))
    return rows


def category_summary_row(
    frame: pd.DataFrame,
    rep_cols: list[str],
    category_type: str,
    code: str,
    label: str,
    domain: pd.Series,
    mask: pd.Series,
) -> dict[str, Any]:
    row = proportion_row(frame, rep_cols, "adult_male_abdominal_proxy", code, label, domain, mask)
    row["category_type"] = category_type
    row["code"] = code
    return row


def ccsr_label(column: str) -> str:
    return {
        "CCSR_SYM004": "Nausea and vomiting diagnosis-coded context",
        "CCSR_CIR012": "Nonspecific chest pain diagnosis-coded context",
        "CCSR_CIR019": "Heart failure diagnosis-coded context",
        "CCSR_END005": "Type 2 diabetes diagnosis-coded context",
        "CCSR_END011": "Fluid and electrolyte disorders diagnosis-coded context",
        "CCSR_INJ017": "Superficial injury/contusion diagnosis-coded context",
    }.get(column, column)


def nhcs_vs_nhamcs_2022_comparison(cohort_rows: list[dict[str, Any]], nhamcs_pooled_dir: Path) -> list[dict[str, Any]]:
    nhcs_by_step = {row["step"]: row for row in cohort_rows}
    rows = [
        comparison_row(
            "all_ed_records",
            "All ED records",
            nhcs_by_step.get("all_ed_records"),
            nhamcs_step(nhamcs_pooled_dir, "Start with 2022 NHAMCS ED records"),
            "NHCS PUF total is validated against CDC technical documentation.",
        ),
        comparison_row(
            "adult_male_18_64",
            "Male patients age 18-64",
            nhcs_by_step.get("adult_male_18_64_not_newborn"),
            nhamcs_step(nhamcs_pooled_dir, "Restrict to male patients age 18-64"),
            "NHCS additionally excludes newborn records for consistency.",
        ),
        comparison_row(
            "abdominal_proxy_vs_rfv",
            "Abdominal pain/source proxy",
            nhcs_by_step.get("adult_male_abdominal_proxy"),
            nhamcs_step(nhamcs_pooled_dir, "Identify abdominal pain using RFV1-RFV5 code list"),
            "NHCS uses diagnosis-coded CCSR_SYM006; NHAMCS uses reason-for-visit chief-complaint codes.",
        ),
        comparison_row(
            "noninjury_sensitivity",
            "Non-injury sensitivity slice",
            nhcs_by_step.get("noninjury_sensitivity_slice"),
            nhamcs_step(nhamcs_pooled_dir, "Exclude trauma/injury/poisoning/adverse-effect presentations"),
            "NHCS injury proxy is diagnosis-based and not equivalent to NHAMCS INJPOISAD exclusion.",
        ),
    ]
    return rows


def nhamcs_step(nhamcs_pooled_dir: Path, step_name: str) -> dict[str, Any] | None:
    path = nhamcs_pooled_dir / "cohort_flow_by_year.csv"
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    match = frame[(pd.to_numeric(frame["year"], errors="coerce") == 2022) & frame["step"].eq(step_name)]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def comparison_row(
    metric: str,
    label: str,
    nhcs: dict[str, Any] | None,
    nhamcs: dict[str, Any] | None,
    notes: str,
) -> dict[str, Any]:
    nhcs_weighted = float(nhcs["weighted_n"]) if nhcs else math.nan
    nhamcs_weighted = float(nhamcs["weighted_n"]) if nhamcs else math.nan
    ratio = nhcs_weighted / nhamcs_weighted if math.isfinite(nhcs_weighted) and nhamcs_weighted else math.nan
    return {
        "metric": metric,
        "label": label,
        "nhcs_unweighted_n": int(nhcs["unweighted_n"]) if nhcs else "",
        "nhcs_weighted_n": round_float(nhcs_weighted),
        "nhamcs_2022_unweighted_n": int(nhamcs["unweighted_n"]) if nhamcs else "",
        "nhamcs_2022_weighted_n": round_float(nhamcs_weighted),
        "nhcs_to_nhamcs_weighted_ratio": round_float(ratio),
        "nhamcs_available": nhamcs is not None,
        "comparison_caveat": notes,
    }


def count_estimate(frame: pd.DataFrame, mask: pd.Series, rep_cols: list[str]) -> dict[str, float]:
    indicator = mask.astype(float)
    estimate = float((pd.to_numeric(frame[BASE_WEIGHT], errors="coerce").fillna(0.0) * indicator).sum())
    replicate_estimates = [
        float((pd.to_numeric(frame[column], errors="coerce").fillna(0.0) * indicator).sum()) for column in rep_cols
    ]
    se = jackknife_standard_error(estimate, replicate_estimates)
    return {
        "estimate": estimate,
        "standard_error": se,
        "ci_low": max(0.0, estimate - NORMAL_95 * se),
        "ci_high": estimate + NORMAL_95 * se,
    }


def proportion_estimate(
    frame: pd.DataFrame,
    denominator_mask: pd.Series,
    numerator_mask: pd.Series,
    rep_cols: list[str],
) -> dict[str, float]:
    base_weight = pd.to_numeric(frame[BASE_WEIGHT], errors="coerce").fillna(0.0)
    denominator_indicator = denominator_mask.astype(float)
    numerator_indicator = numerator_mask.astype(float)
    denominator = float((base_weight * denominator_indicator).sum())
    numerator = float((base_weight * numerator_indicator).sum())
    estimate = numerator / denominator if denominator else math.nan
    replicate_estimates = []
    for column in rep_cols:
        rep_weight = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
        rep_denominator = float((rep_weight * denominator_indicator).sum())
        rep_numerator = float((rep_weight * numerator_indicator).sum())
        replicate_estimates.append(rep_numerator / rep_denominator if rep_denominator else math.nan)
    se = jackknife_standard_error(estimate, replicate_estimates)
    return {
        "estimate": estimate,
        "standard_error": se,
        "ci_low": max(0.0, estimate - NORMAL_95 * se) if math.isfinite(estimate) else math.nan,
        "ci_high": min(1.0, estimate + NORMAL_95 * se) if math.isfinite(estimate) else math.nan,
        "denominator": denominator,
        "numerator": numerator,
    }


def jackknife_standard_error(estimate: float, replicate_estimates: list[float], jkcoef: float = 1.0) -> float:
    valid = [value for value in replicate_estimates if math.isfinite(value)]
    if not math.isfinite(estimate) or not valid:
        return math.nan
    return math.sqrt(jkcoef * sum((value - estimate) ** 2 for value in valid))


def reliability_for_count(unweighted_n: int, estimate: float, standard_error: float) -> dict[str, Any]:
    reasons = []
    severity = "present"
    if unweighted_n < 30:
        reasons.append("unweighted_n_below_30")
        severity = "suppress"
    rse = standard_error / estimate if estimate > 0 and math.isfinite(standard_error) else math.nan
    if math.isfinite(rse) and rse > 0.30:
        reasons.append("relative_standard_error_above_30_percent")
        severity = max_status(severity, "flag")
    if estimate <= 0:
        reasons.append("zero_weighted_count")
        severity = max_status(severity, "flag")
    return {
        "status": severity,
        "reasons": "; ".join(reasons) if reasons else "none",
        "rse": rse,
    }


def reliability_for_proportion(
    *,
    denominator_n: int,
    event_n: int,
    proportion: float,
    standard_error: float,
    replicate_df: int,
) -> dict[str, Any]:
    reasons = []
    severity = "present"
    effective_n = effective_sample_size(denominator_n, proportion, standard_error)
    complement_n = denominator_n - event_n
    ci_low = max(0.0, proportion - NORMAL_95 * standard_error) if math.isfinite(proportion) else math.nan
    ci_high = min(1.0, proportion + NORMAL_95 * standard_error) if math.isfinite(proportion) else math.nan
    ci_width = ci_high - ci_low if math.isfinite(ci_high) and math.isfinite(ci_low) else math.nan
    relative_width = ci_width / proportion if math.isfinite(ci_width) and proportion > 0 else math.nan

    if denominator_n < 30:
        reasons.append("denominator_n_below_30")
        severity = "suppress"
    if math.isfinite(effective_n) and effective_n < 30:
        reasons.append("effective_denominator_n_below_30")
        severity = "suppress"
    if event_n == 0 or complement_n == 0:
        reasons.append("zero_event_or_complement")
        severity = max_status(severity, "flag")
    elif event_n < 30 or complement_n < 30:
        reasons.append("sparse_event_or_complement_below_30")
        severity = max_status(severity, "flag")
    if math.isfinite(ci_width) and ci_width >= 0.30:
        reasons.append("absolute_ci_width_at_least_0_30")
        severity = "suppress"
    elif math.isfinite(ci_width) and ci_width > 0.05 and math.isfinite(relative_width) and relative_width > 1.30:
        reasons.append("relative_ci_width_above_130_percent")
        severity = "suppress"
    if replicate_df and replicate_df < 8:
        reasons.append("replicate_degrees_of_freedom_below_8")
        severity = max_status(severity, "flag")

    return {
        "status": severity,
        "reasons": "; ".join(reasons) if reasons else "none",
        "effective_n": effective_n,
        "ci_width": ci_width,
        "relative_width": relative_width,
    }


def effective_sample_size(denominator_n: int, proportion: float, standard_error: float) -> float:
    if denominator_n <= 0:
        return math.nan
    if not math.isfinite(proportion) or not math.isfinite(standard_error):
        return math.nan
    if proportion in {0.0, 1.0} or standard_error == 0:
        return float(denominator_n)
    value = proportion * (1.0 - proportion) / (standard_error**2)
    return min(float(denominator_n), value)


def max_status(left: str, right: str) -> str:
    order = {"present": 0, "flag": 1, "suppress": 2}
    return left if order[left] >= order[right] else right


def validation_dossier(outputs: dict[str, Any]) -> str:
    weight = outputs["weight_validation"][0]
    flow = {row["step"]: row for row in outputs["cohort_flow"]}
    comparison = {
        row["metric"]: row for row in outputs["nhcs_vs_nhamcs_2022_comparison"]
    }
    abdominal = flow["adult_male_abdominal_proxy"]
    nhamcs_abdominal = comparison.get("abdominal_proxy_vs_rfv", {})
    return "\n".join(
        [
            "# NHCS 2022 ED Validation-Dossier Audit",
            "",
            f"Generated at: {outputs['metadata']['generated_at']}",
            "",
            "## Method Summary",
            "",
            "- Source: CDC NHCS 2022 ED public-use file.",
            "- Weights: `PUF_ENCWGT_BASE` with `PUF_ENCWGT_1` through `PUF_ENCWGT_100` delete-a-group jackknife replicate weights.",
            "- Reliability screening: NCHS presentation-standard inspired sample-size, effective-sample-size, CI-width, and RSE flags.",
            "- Domain analyses are computed with full-file indicators rather than dropping non-domain records before variance estimation.",
            "",
            "## Weight Validation",
            "",
            f"- ED total estimate: {weight['estimate']}; published CDC total: {weight['published_estimate']}.",
            f"- ED total standard error: {weight['standard_error']}; published CDC standard error: {weight['published_standard_error']}.",
            f"- Validation pass: {weight['pass']}.",
            "",
            "## Most Useful NHCS Contributions",
            "",
            "1. Confirms the downloaded NHCS ED PUF and replicate-weight method are usable for national descriptive audit work.",
            "2. Quantifies a diagnosis-coded abdominal-symptom proxy slice for adult men age 18-64.",
            "3. Provides discharge-status proxy sensitivity checks that can inform the validation dossier but do not validate the active endpoint.",
            "4. Documents why this public-use file cannot validate active `e-dispo-v4.0` predictions: it lacks pain severity, temperature/fever, vomiting as a presenting symptom, tachycardia burden, free text, and the strict same-hospital admission endpoint.",
            "",
            "## Key Counts",
            "",
            f"- Adult male age 18-64 non-newborn records: {flow['adult_male_18_64_not_newborn']['unweighted_n']} unweighted; {flow['adult_male_18_64_not_newborn']['weighted_n']} weighted.",
            f"- Adult male `CCSR_SYM006` abdominal proxy records: {abdominal['unweighted_n']} unweighted; {abdominal['weighted_n']} weighted.",
            f"- NHAMCS 2022 RFV abdominal-pain comparator weighted count: {nhamcs_abdominal.get('nhamcs_2022_weighted_n', '')}.",
            f"- NHCS/NHAMCS weighted abdominal-scope ratio: {nhamcs_abdominal.get('nhcs_to_nhamcs_weighted_ratio', '')}.",
            "",
            "## Evidence Boundary",
            "",
            "- `CCSR_SYM006` is diagnosis-coded abdominal symptom context, not a chief complaint.",
            "- `DISCHARGE_STATUS` is discharge context, not the strict active model endpoint.",
            "- No NHCS-derived coefficient, app parameter, or app export is produced by this audit.",
            "- NHCS public-use results should remain validation-dossier context only.",
            "",
            "## Sources",
            "",
            *[f"- {key}: {url}" for key, url in SOURCE_URLS.items()],
            "",
        ]
    )


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "schema_inventory.csv", result["schema_inventory"])
    write_csv(output_dir / "weight_validation.csv", result["weight_validation"])
    write_csv(output_dir / "cohort_flow.csv", result["cohort_flow"])
    write_csv(output_dir / "discharge_status_summary.csv", result["discharge_status_summary"])
    write_csv(output_dir / "proxy_endpoint_sensitivity.csv", result["proxy_endpoint_sensitivity"])
    write_csv(output_dir / "nhcs_vs_nhamcs_2022_comparison.csv", result["nhcs_vs_nhamcs_2022_comparison"])
    write_csv(output_dir / "top_diagnoses_abdominal_proxy.csv", result["top_diagnoses_abdominal_proxy"])
    (output_dir / "nhcs_2022_ed_validation_dossier.md").write_text(result["validation_dossier"], encoding="utf-8")
    (output_dir / "audit_metadata.json").write_text(json.dumps(result["metadata"], indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def round_float(value: object, digits: int = 6) -> object:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(number):
        return ""
    return round(number, digits)


if __name__ == "__main__":
    raise SystemExit(main())
