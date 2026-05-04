#!/usr/bin/env python3
"""Screen full-source non-trauma NHAMCS variables against admit and transfer targets."""

from __future__ import annotations

import argparse
import csv
import math
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import build_cohort
import build_yearly_cohorts


DEFAULT_CONFIG = build_yearly_cohorts.DEFAULT_CONFIG
DEFAULT_OUTPUT_DIR = Path("outputs/nhamcs_pooled")
DEFAULT_ANALYTIC_COHORT = DEFAULT_OUTPUT_DIR / "full_source_nontrauma_cohort_nhamcs_2018_2022.csv"
MODEL_ID = "e-dispo-v4.1-full-source-nontrauma-admit"
DATASET = "NHAMCS_2018_2022_POOLED"
MAX_CATEGORICAL_LEVELS = 25
MIN_COMPLETE_PAIRS = 20

OUTPUT_COLUMNS = [
    "screen_id",
    "dataset",
    "target",
    "source_layer",
    "variable",
    "variable_label",
    "row_type",
    "level",
    "method",
    "status",
    "exclusion_reason",
    "denominator_n",
    "denominator_events",
    "denominator_non_events",
    "weighted_denominator_n",
    "weighted_denominator_events",
    "n",
    "events",
    "non_events",
    "weighted_n",
    "weighted_events",
    "missing_n",
    "missing_pct",
    "weighted_missing_n",
    "weighted_missing_pct",
    "unique_nonmissing",
    "estimate",
    "unweighted_estimate",
    "abs_estimate",
    "weighted_value_mean_event",
    "weighted_value_mean_non_event",
    "unweighted_value_mean_event",
    "unweighted_value_mean_non_event",
    "level_n",
    "level_events",
    "level_non_events",
    "level_weighted_n",
    "level_weighted_events",
    "notes",
]

ANALYTIC_CONTINUOUS = {
    "age",
    "pain_score",
    "temp",
    "acuity",
    "HR",
    "tachycardia_burden",
    "SBP",
}

RAW_CONTINUOUS = {
    "AGE",
    "AGEDAYS",
    "AGEFL",
    "PAINSCALE",
    "TEMPF",
    "PULSE",
    "BPSYS",
    "BPDIAS",
    "WAITTIME",
    "LOV",
    "LOVEM",
    "HTIN",
    "WTLB",
    "BMI",
}

ANALYTIC_EXCLUDED = {
    "endpoint",
    "endpoint_class",
    "include_strict_binary",
    "admit",
    "record_id",
    "dataset",
    "source_dataset",
    "source_scope",
    "year",
    "year_factor",
    "pool_year_count",
    "PATWT",
    "pooled_weight",
    "CSTRATM",
    "CPSUM",
    "pooled_stratum",
    "pooled_psu",
    "weight",
    "stratum",
    "psu",
}

RAW_EXCLUDED_BASE = {
    "PATWT",
    "CSTRATM",
    "CPSUM",
    "YEAR",
    "VMONTH",
    "HOSPCODE",
    "ADISP",
    "ADMIT",
    "ADMTPHYS",
    "HDSTAT",
    "LOS",
    "STAY24",
}
RAW_EXCLUDED_PREFIXES = ("HDDIAG",)

TRUE_VALUES = {"1", "true", "t", "yes", "y"}
FALSE_VALUES = {"0", "false", "f", "no", "n"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build full-source non-trauma NHAMCS variable association screens."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, type=Path)
    parser.add_argument("--analytic-cohort", default=DEFAULT_ANALYTIC_COHORT, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    parser.add_argument("--years", nargs="*", type=int)
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = build_yearly_cohorts.read_config(args.config)
    years = args.years or [int(year) for year in config["pool"]["years"]]

    if not args.analytic_cohort.exists():
        write_blocker_outputs(
            args.output_dir,
            f"Analytic full-source non-trauma cohort is missing: {args.analytic_cohort}",
        )
        return 2

    analytic = pd.read_csv(args.analytic_cohort)
    if "endpoint_class" not in analytic.columns or "pooled_weight" not in analytic.columns:
        write_blocker_outputs(
            args.output_dir,
            "Analytic cohort must contain endpoint_class and pooled_weight.",
        )
        return 2

    analytic = analytic.copy()
    analytic[".__screen_weight"] = pd.to_numeric(analytic["pooled_weight"], errors="coerce")
    analytic_variables = [column for column in analytic.columns if not column.startswith(".__")]

    raw_read = read_raw_nontrauma_frame(config, years, args.output_dir)
    if raw_read["blockers"]:
        write_blocker_outputs(args.output_dir, "; ".join(raw_read["blockers"]))
        return 2

    raw_frame = raw_read["frame"]
    raw_variables = raw_read["variables"]
    raw_labels = raw_read["labels"]
    raw_excluded = RAW_EXCLUDED_BASE | disposition_columns(config) | raw_leakage_columns(raw_variables)

    analytic_admit = screen_variables(
        frame=analytic,
        variables=analytic_variables,
        labels={},
        source_layer="analytic",
        target="admit_vs_home",
        event_class="admit",
        reference_class="routine_home_discharge",
        excluded=ANALYTIC_EXCLUDED,
        continuous=ANALYTIC_CONTINUOUS,
    )
    raw_admit = screen_variables(
        frame=raw_frame,
        variables=raw_variables,
        labels=raw_labels,
        source_layer="raw",
        target="admit_vs_home",
        event_class="admit",
        reference_class="routine_home_discharge",
        excluded=raw_excluded,
        continuous=RAW_CONTINUOUS,
    )
    analytic_transfer = screen_variables(
        frame=analytic,
        variables=analytic_variables,
        labels={},
        source_layer="analytic",
        target="transfer_vs_home",
        event_class="transfer",
        reference_class="routine_home_discharge",
        excluded=ANALYTIC_EXCLUDED,
        continuous=ANALYTIC_CONTINUOUS,
    )
    raw_transfer = screen_variables(
        frame=raw_frame,
        variables=raw_variables,
        labels=raw_labels,
        source_layer="raw",
        target="transfer_vs_home",
        event_class="transfer",
        reference_class="routine_home_discharge",
        excluded=raw_excluded,
        continuous=RAW_CONTINUOUS,
    )

    write_rows(args.output_dir / "full_source_nontrauma_analytic_variable_correlations.csv", analytic_admit)
    write_rows(args.output_dir / "full_source_nontrauma_raw_variable_correlations.csv", raw_admit)
    write_rows(
        args.output_dir / "full_source_nontrauma_transfer_variable_correlations.csv",
        [*analytic_transfer, *raw_transfer],
    )
    write_report(
        args.output_dir,
        analytic=analytic,
        raw=raw_frame,
        analytic_admit=analytic_admit,
        raw_admit=raw_admit,
        analytic_transfer=analytic_transfer,
        raw_transfer=raw_transfer,
        years=years,
    )
    print(f"Wrote full-source non-trauma variable screens under {args.output_dir}")
    return 0


def read_raw_nontrauma_frame(
    config: dict[str, Any],
    years: list[int],
    output_dir: Path,
) -> dict[str, Any]:
    frames: list[pd.DataFrame] = []
    variables: list[str] = []
    labels: dict[str, str] = {}
    blockers: list[str] = []
    year_count = len(years)

    for year in years:
        year_config = build_yearly_cohorts.year_config_for(config, year)
        if year_config is None:
            blockers.append(f"{year}: no harmonization entry was found.")
            continue
        source = build_yearly_cohorts.find_year_source(year_config)
        if source is None:
            blockers.append(f"{year}: source file missing.")
            continue

        try:
            frame = build_cohort.read_source_file(source, output_dir / f"_raw_screen_source_extract_{year}")
        except (FileNotFoundError, ValueError, zipfile.BadZipFile) as exc:
            blockers.append(f"{year}: {exc}")
            continue

        labels.update(read_variable_labels(source, output_dir / f"_raw_screen_label_extract_{year}"))
        original_columns = list(frame.columns)
        for column in original_columns:
            if column not in variables:
                variables.append(column)

        cohort_config = build_yearly_cohorts.build_cohort_config(year_config, config)
        try:
            masks = build_cohort.cohort_masks(frame, cohort_config)
            scoped = frame.loc[masks["non_trauma_all"]].copy()
            scoped["endpoint_class"] = build_cohort.classify_endpoint(scoped, cohort_config)
        except KeyError as exc:
            blockers.append(f"{year}: required restriction or endpoint column is missing: {exc}")
            continue

        weight_column = str(year_config["patwt_variable"])
        if weight_column not in scoped.columns:
            blockers.append(f"{year}: weight column is missing: {weight_column}")
            continue
        scoped[".__screen_weight"] = pd.to_numeric(scoped[weight_column], errors="coerce") / year_count
        scoped[".__source_year"] = int(year)
        frames.append(scoped)

    if frames:
        raw = pd.concat(frames, ignore_index=True, sort=False)
    else:
        raw = pd.DataFrame()
    return {"frame": raw, "variables": variables, "labels": labels, "blockers": blockers}


def read_variable_labels(source: Path, extract_dir: Path) -> dict[str, str]:
    suffix = source.suffix.lower()
    dta_path: Path | None = None
    if suffix == ".dta":
        dta_path = source
    elif suffix == ".zip":
        try:
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(source) as archive:
                members = sorted(name for name in archive.namelist() if name.lower().endswith(".dta"))
                if not members:
                    return {}
                member = members[0]
                archive.extract(member, extract_dir)
                dta_path = extract_dir / member
        except (OSError, zipfile.BadZipFile):
            return {}
    if dta_path is None:
        return {}
    try:
        with pd.io.stata.StataReader(dta_path) as reader:
            return {str(key): str(value) for key, value in reader.variable_labels().items()}
    except (OSError, ValueError):
        return {}


def disposition_columns(config: dict[str, Any]) -> set[str]:
    columns: set[str] = set()
    for year_config in config.get("years", []):
        for values in year_config.get("disposition_flags", {}).values():
            columns.update(str(value) for value in values)
    return columns


def raw_leakage_columns(variables: Iterable[str]) -> set[str]:
    return {
        variable
        for variable in variables
        if any(variable.startswith(prefix) for prefix in RAW_EXCLUDED_PREFIXES)
    }


def screen_variables(
    *,
    frame: pd.DataFrame,
    variables: list[str],
    labels: dict[str, str],
    source_layer: str,
    target: str,
    event_class: str,
    reference_class: str,
    excluded: set[str],
    continuous: set[str],
) -> list[dict[str, Any]]:
    if frame.empty:
        return [
            base_row(
                target=target,
                source_layer=source_layer,
                variable="blocked",
                variable_label="",
                row_type="blocker",
                method="blocked",
                status="blocked_no_source_rows",
                exclusion_reason="No source rows were available for this screen.",
                denominator=empty_denominator(),
            )
        ]

    subset = frame[frame["endpoint_class"].isin([event_class, reference_class])].copy()
    subset[".__target"] = subset["endpoint_class"].eq(event_class).astype(int)
    denominator = denominator_stats(subset)
    rows: list[dict[str, Any]] = []

    for variable in variables:
        variable_label = labels.get(variable, "")
        if variable in excluded:
            rows.append(
                base_row(
                    target=target,
                    source_layer=source_layer,
                    variable=variable,
                    variable_label=variable_label,
                    row_type="excluded",
                    method="not_screened",
                    status="excluded_leakage_design_or_identifier",
                    exclusion_reason="Outcome, disposition, survey design, source identifier, or record identifier column.",
                    denominator=denominator,
                )
            )
            continue
        if variable not in subset.columns:
            rows.append(
                base_row(
                    target=target,
                    source_layer=source_layer,
                    variable=variable,
                    variable_label=variable_label,
                    row_type="blocker",
                    method="not_screened",
                    status="blocked_field_absent_after_pooling",
                    exclusion_reason="Column is absent from the pooled target frame.",
                    denominator=denominator,
                )
            )
            continue
        rows.extend(
            screen_one_variable(
                subset=subset,
                variable=variable,
                variable_label=variable_label,
                source_layer=source_layer,
                target=target,
                denominator=denominator,
                continuous=continuous,
            )
        )
    return rows


def screen_one_variable(
    *,
    subset: pd.DataFrame,
    variable: str,
    variable_label: str,
    source_layer: str,
    target: str,
    denominator: dict[str, Any],
    continuous: set[str],
) -> list[dict[str, Any]]:
    y = pd.to_numeric(subset[".__target"], errors="coerce")
    weight = pd.to_numeric(subset[".__screen_weight"], errors="coerce")
    series = subset[variable]
    if denominator["denominator_events"] == 0 or denominator["denominator_non_events"] == 0:
        return [
            blocker_row(
                target,
                source_layer,
                variable,
                variable_label,
                denominator,
                "blocked_no_target_variation",
                "Target denominator does not contain both event and reference rows.",
            )
        ]

    if variable in continuous:
        return screen_continuous(
            series,
            y,
            weight,
            target,
            source_layer,
            variable,
            variable_label,
            denominator,
        )

    normalized = normalize_series(series)
    nonmissing = normalized.notna()
    if int(nonmissing.sum()) == 0:
        return [
            blocker_row(
                target,
                source_layer,
                variable,
                variable_label,
                denominator,
                "blocked_all_missing",
                "All values are missing in the target denominator.",
                missing=missing_stats(series, weight),
                unique_nonmissing=0,
            )
        ]

    levels = sorted(normalized.loc[nonmissing].unique(), key=level_sort_key)
    if is_binary_levels(levels):
        positive = choose_positive_level(levels)
        binary = normalized.eq(positive).astype(float).where(nonmissing, np.nan)
        return [
            association_row(
                x=binary,
                y=y,
                weight=weight,
                target=target,
                source_layer=source_layer,
                variable=variable,
                variable_label=variable_label,
                row_type="binary",
                level=positive,
                method="weighted_phi_point_biserial",
                denominator=denominator,
                missing=missing_stats(series, weight),
                unique_nonmissing=len(levels),
                notes="Binary variable screened as one-vs-reference indicator.",
            )
        ]

    if len(levels) == 1:
        return [
            blocker_row(
                target,
                source_layer,
                variable,
                variable_label,
                denominator,
                "blocked_no_variable_variation",
                "Only one nonmissing value is present in the target denominator.",
                missing=missing_stats(series, weight),
                unique_nonmissing=1,
            )
        ]

    if len(levels) > MAX_CATEGORICAL_LEVELS:
        return [
            blocker_row(
                target,
                source_layer,
                variable,
                variable_label,
                denominator,
                "blocked_high_cardinality_or_unordered",
                f"{len(levels)} nonmissing levels exceed the {MAX_CATEGORICAL_LEVELS}-level categorical screen cap.",
                missing=missing_stats(series, weight),
                unique_nonmissing=len(levels),
            )
        ]

    rows = [
        categorical_overall_row(
            normalized,
            y,
            weight,
            target,
            source_layer,
            variable,
            variable_label,
            denominator,
            missing_stats(series, weight),
            len(levels),
        )
    ]
    for level in levels:
        indicator = normalized.eq(level).astype(float).where(nonmissing, np.nan)
        rows.append(
            association_row(
                x=indicator,
                y=y,
                weight=weight,
                target=target,
                source_layer=source_layer,
                variable=variable,
                variable_label=variable_label,
                row_type="categorical_level",
                level=level,
                method="weighted_one_vs_rest_point_biserial",
                denominator=denominator,
                missing=missing_stats(series, weight),
                unique_nonmissing=len(levels),
                notes="Categorical level screened one-vs-rest; not a model coefficient.",
            )
        )
    return rows


def screen_continuous(
    series: pd.Series,
    y: pd.Series,
    weight: pd.Series,
    target: str,
    source_layer: str,
    variable: str,
    variable_label: str,
    denominator: dict[str, Any],
) -> list[dict[str, Any]]:
    x = pd.to_numeric(series, errors="coerce")
    nonmissing = x.notna()
    unique = int(x.loc[nonmissing].nunique(dropna=True))
    missing = missing_stats(x, weight)
    if unique == 0:
        return [
            blocker_row(
                target,
                source_layer,
                variable,
                variable_label,
                denominator,
                "blocked_all_missing",
                "All values are missing in the target denominator.",
                missing=missing,
                unique_nonmissing=0,
            )
        ]
    if unique == 1:
        return [
            blocker_row(
                target,
                source_layer,
                variable,
                variable_label,
                denominator,
                "blocked_no_variable_variation",
                "Only one nonmissing value is present in the target denominator.",
                missing=missing,
                unique_nonmissing=1,
            )
        ]
    return [
        association_row(
            x=x,
            y=y,
            weight=weight,
            target=target,
            source_layer=source_layer,
            variable=variable,
            variable_label=variable_label,
            row_type="continuous",
            level="",
            method="weighted_pearson_point_biserial",
            denominator=denominator,
            missing=missing,
            unique_nonmissing=unique,
            notes="Continuous/numeric variable screened with weighted and unweighted point-biserial correlation.",
        )
    ]


def association_row(
    *,
    x: pd.Series,
    y: pd.Series,
    weight: pd.Series,
    target: str,
    source_layer: str,
    variable: str,
    variable_label: str,
    row_type: str,
    level: str,
    method: str,
    denominator: dict[str, Any],
    missing: dict[str, Any],
    unique_nonmissing: int,
    notes: str,
) -> dict[str, Any]:
    valid = valid_pair_mask(x, y, weight)
    if int(valid.sum()) < MIN_COMPLETE_PAIRS:
        row = blocker_row(
            target,
            source_layer,
            variable,
            variable_label,
            denominator,
            "blocked_insufficient_complete_pairs",
            f"Fewer than {MIN_COMPLETE_PAIRS} complete variable-target-weight pairs.",
            missing=missing,
            unique_nonmissing=unique_nonmissing,
        )
        row.update({"row_type": row_type, "level": level, "method": method})
        return row

    complete_y = y.loc[valid].astype(int)
    if complete_y.nunique() < 2:
        row = blocker_row(
            target,
            source_layer,
            variable,
            variable_label,
            denominator,
            "blocked_no_target_variation_after_missingness",
            "Variable-specific complete cases do not contain both target classes.",
            missing=missing,
            unique_nonmissing=unique_nonmissing,
        )
        row.update({"row_type": row_type, "level": level, "method": method})
        return row
    complete_x = pd.to_numeric(x.loc[valid], errors="coerce")
    if complete_x.nunique(dropna=True) < 2:
        row = blocker_row(
            target,
            source_layer,
            variable,
            variable_label,
            denominator,
            "blocked_no_variable_variation_after_missingness",
            "Variable-specific complete cases contain no usable variable variation.",
            missing=missing,
            unique_nonmissing=unique_nonmissing,
        )
        row.update({"row_type": row_type, "level": level, "method": method})
        return row

    estimate = weighted_corr(complete_x, complete_y, weight.loc[valid])
    unweighted = unweighted_corr(complete_x, complete_y)
    stats = complete_stats(complete_x, complete_y, weight.loc[valid])
    return {
        **base_row(
            target=target,
            source_layer=source_layer,
            variable=variable,
            variable_label=variable_label,
            row_type=row_type,
            level=level,
            method=method,
            status="ok",
            exclusion_reason="",
            denominator=denominator,
            missing=missing,
            unique_nonmissing=unique_nonmissing,
        ),
        **stats,
        "estimate": round_or_blank(estimate),
        "unweighted_estimate": round_or_blank(unweighted),
        "abs_estimate": round_or_blank(abs(estimate) if math.isfinite(estimate) else float("nan")),
        "notes": notes,
    }


def categorical_overall_row(
    values: pd.Series,
    y: pd.Series,
    weight: pd.Series,
    target: str,
    source_layer: str,
    variable: str,
    variable_label: str,
    denominator: dict[str, Any],
    missing: dict[str, Any],
    unique_nonmissing: int,
) -> dict[str, Any]:
    valid = values.notna() & y.notna() & weight.notna() & (weight > 0)
    if int(valid.sum()) < MIN_COMPLETE_PAIRS:
        return blocker_row(
            target,
            source_layer,
            variable,
            variable_label,
            denominator,
            "blocked_insufficient_complete_pairs",
            f"Fewer than {MIN_COMPLETE_PAIRS} complete variable-target-weight pairs.",
            missing=missing,
            unique_nonmissing=unique_nonmissing,
        )
    estimate = weighted_cramers_v(values.loc[valid], y.loc[valid], weight.loc[valid])
    unweighted = unweighted_cramers_v(values.loc[valid], y.loc[valid])
    complete_y = y.loc[valid].astype(int)
    stats = complete_stats(pd.Series(np.nan, index=complete_y.index), complete_y, weight.loc[valid])
    return {
        **base_row(
            target=target,
            source_layer=source_layer,
            variable=variable,
            variable_label=variable_label,
            row_type="categorical_overall",
            level="",
            method="weighted_cramers_v",
            status="ok",
            exclusion_reason="",
            denominator=denominator,
            missing=missing,
            unique_nonmissing=unique_nonmissing,
        ),
        **stats,
        "estimate": round_or_blank(estimate),
        "unweighted_estimate": round_or_blank(unweighted),
        "abs_estimate": round_or_blank(abs(estimate) if math.isfinite(estimate) else float("nan")),
        "notes": "Categorical association screen using Cramer's V; level rows are one-vs-rest screens.",
    }


def complete_stats(x: pd.Series, y: pd.Series, weight: pd.Series) -> dict[str, Any]:
    y_numeric = pd.to_numeric(y, errors="coerce").astype(int)
    weights = pd.to_numeric(weight, errors="coerce").fillna(0.0)
    n = int(len(y_numeric))
    event = y_numeric.eq(1)
    events = int(event.sum())
    weighted_n = float(weights.sum())
    weighted_events = float(weights.loc[event].sum())
    if x.notna().any():
        event_x = x.loc[event]
        nonevent_x = x.loc[~event]
        return {
            "n": n,
            "events": events,
            "non_events": n - events,
            "weighted_n": round_or_blank(weighted_n),
            "weighted_events": round_or_blank(weighted_events),
            "weighted_value_mean_event": round_or_blank(weighted_mean(event_x, weights.loc[event])),
            "weighted_value_mean_non_event": round_or_blank(weighted_mean(nonevent_x, weights.loc[~event])),
            "unweighted_value_mean_event": round_or_blank(float(event_x.mean()) if len(event_x) else float("nan")),
            "unweighted_value_mean_non_event": round_or_blank(float(nonevent_x.mean()) if len(nonevent_x) else float("nan")),
            "level_n": int((x == 1).sum()) if set(pd.Series(x.dropna()).unique()).issubset({0.0, 1.0}) else "",
            "level_events": int(((x == 1) & event).sum()) if set(pd.Series(x.dropna()).unique()).issubset({0.0, 1.0}) else "",
            "level_non_events": int(((x == 1) & ~event).sum()) if set(pd.Series(x.dropna()).unique()).issubset({0.0, 1.0}) else "",
            "level_weighted_n": round_or_blank(float(weights.loc[x == 1].sum())) if set(pd.Series(x.dropna()).unique()).issubset({0.0, 1.0}) else "",
            "level_weighted_events": round_or_blank(float(weights.loc[(x == 1) & event].sum())) if set(pd.Series(x.dropna()).unique()).issubset({0.0, 1.0}) else "",
        }
    return {
        "n": n,
        "events": events,
        "non_events": n - events,
        "weighted_n": round_or_blank(weighted_n),
        "weighted_events": round_or_blank(weighted_events),
    }


def blocker_row(
    target: str,
    source_layer: str,
    variable: str,
    variable_label: str,
    denominator: dict[str, Any],
    status: str,
    reason: str,
    *,
    missing: dict[str, Any] | None = None,
    unique_nonmissing: int | str = "",
) -> dict[str, Any]:
    return base_row(
        target=target,
        source_layer=source_layer,
        variable=variable,
        variable_label=variable_label,
        row_type="blocker",
        method="not_estimated",
        status=status,
        exclusion_reason=reason,
        denominator=denominator,
        missing=missing,
        unique_nonmissing=unique_nonmissing,
        notes=reason,
    )


def base_row(
    *,
    target: str,
    source_layer: str,
    variable: str,
    variable_label: str,
    row_type: str,
    method: str,
    status: str,
    exclusion_reason: str,
    denominator: dict[str, Any],
    level: str = "",
    missing: dict[str, Any] | None = None,
    unique_nonmissing: int | str = "",
    notes: str = "",
) -> dict[str, Any]:
    row = {
        "screen_id": MODEL_ID,
        "dataset": DATASET,
        "target": target,
        "source_layer": source_layer,
        "variable": variable,
        "variable_label": variable_label,
        "row_type": row_type,
        "level": level,
        "method": method,
        "status": status,
        "exclusion_reason": exclusion_reason,
        **denominator,
        "n": "",
        "events": "",
        "non_events": "",
        "weighted_n": "",
        "weighted_events": "",
        "missing_n": "",
        "missing_pct": "",
        "weighted_missing_n": "",
        "weighted_missing_pct": "",
        "unique_nonmissing": unique_nonmissing,
        "estimate": "",
        "unweighted_estimate": "",
        "abs_estimate": "",
        "weighted_value_mean_event": "",
        "weighted_value_mean_non_event": "",
        "unweighted_value_mean_event": "",
        "unweighted_value_mean_non_event": "",
        "level_n": "",
        "level_events": "",
        "level_non_events": "",
        "level_weighted_n": "",
        "level_weighted_events": "",
        "notes": notes,
    }
    if missing:
        row.update(missing)
    return row


def denominator_stats(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return empty_denominator()
    y = pd.to_numeric(frame[".__target"], errors="coerce").fillna(0).astype(int)
    weight = pd.to_numeric(frame[".__screen_weight"], errors="coerce").fillna(0.0)
    event = y.eq(1)
    return {
        "denominator_n": int(len(frame)),
        "denominator_events": int(event.sum()),
        "denominator_non_events": int((~event).sum()),
        "weighted_denominator_n": round_or_blank(float(weight.sum())),
        "weighted_denominator_events": round_or_blank(float(weight.loc[event].sum())),
    }


def empty_denominator() -> dict[str, Any]:
    return {
        "denominator_n": 0,
        "denominator_events": 0,
        "denominator_non_events": 0,
        "weighted_denominator_n": "",
        "weighted_denominator_events": "",
    }


def missing_stats(series: pd.Series, weight: pd.Series) -> dict[str, Any]:
    missing = missing_like(series)
    weights = pd.to_numeric(weight, errors="coerce").fillna(0.0)
    total_weight = float(weights.sum())
    missing_weight = float(weights.loc[missing].sum())
    return {
        "missing_n": int(missing.sum()),
        "missing_pct": round_or_blank(100 * int(missing.sum()) / len(series) if len(series) else float("nan")),
        "weighted_missing_n": round_or_blank(missing_weight),
        "weighted_missing_pct": round_or_blank(100 * missing_weight / total_weight if total_weight else float("nan")),
    }


def normalize_series(series: pd.Series) -> pd.Series:
    out = series.astype("object").copy()
    out = out.mask(missing_like(out))
    return out.map(normalize_value)


def normalize_value(value: Any) -> str | float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (np.floating, float)):
        if not math.isfinite(float(value)):
            return None
        if float(value).is_integer():
            return str(int(value))
        return str(round(float(value), 10)).rstrip("0").rstrip(".")
    text = str(value).strip()
    if text == "":
        return None
    return text


def missing_like(series: pd.Series) -> pd.Series:
    if len(series) == 0:
        return pd.Series(dtype=bool)
    text = series.astype("object").map(lambda value: "" if value is None or pd.isna(value) else str(value).strip())
    return series.isna() | text.isin({"", "NA", "NaN", "nan", "None"})


def is_binary_levels(levels: list[Any]) -> bool:
    if len(levels) > 2:
        return False
    normalized = {str(level).strip().lower() for level in levels}
    return normalized.issubset(TRUE_VALUES | FALSE_VALUES) and bool(normalized & TRUE_VALUES) and bool(normalized & FALSE_VALUES)


def choose_positive_level(levels: list[Any]) -> str:
    for level in levels:
        if str(level).strip().lower() in TRUE_VALUES:
            return str(level)
    return str(levels[-1])


def level_sort_key(value: Any) -> tuple[int, float | str]:
    text = str(value)
    try:
        return (0, float(text))
    except ValueError:
        return (1, text)


def valid_pair_mask(x: pd.Series, y: pd.Series, weight: pd.Series) -> pd.Series:
    x_num = pd.to_numeric(x, errors="coerce")
    y_num = pd.to_numeric(y, errors="coerce")
    w_num = pd.to_numeric(weight, errors="coerce")
    return x_num.notna() & y_num.isin([0, 1]) & w_num.notna() & (w_num > 0)


def weighted_corr(x: pd.Series, y: pd.Series, weight: pd.Series) -> float:
    x_num = pd.to_numeric(x, errors="coerce").astype(float)
    y_num = pd.to_numeric(y, errors="coerce").astype(float)
    w = pd.to_numeric(weight, errors="coerce").astype(float)
    valid = x_num.notna() & y_num.notna() & w.notna() & (w > 0)
    if int(valid.sum()) < 2:
        return float("nan")
    x_num = x_num.loc[valid]
    y_num = y_num.loc[valid]
    w = w.loc[valid]
    total = float(w.sum())
    if total <= 0:
        return float("nan")
    x_mean = float((x_num * w).sum() / total)
    y_mean = float((y_num * w).sum() / total)
    cov = float(((x_num - x_mean) * (y_num - y_mean) * w).sum() / total)
    x_var = float((((x_num - x_mean) ** 2) * w).sum() / total)
    y_var = float((((y_num - y_mean) ** 2) * w).sum() / total)
    if x_var <= 0 or y_var <= 0:
        return float("nan")
    return cov / math.sqrt(x_var * y_var)


def unweighted_corr(x: pd.Series, y: pd.Series) -> float:
    x_num = pd.to_numeric(x, errors="coerce")
    y_num = pd.to_numeric(y, errors="coerce")
    valid = x_num.notna() & y_num.notna()
    if int(valid.sum()) < 2:
        return float("nan")
    if x_num.loc[valid].nunique(dropna=True) < 2 or y_num.loc[valid].nunique(dropna=True) < 2:
        return float("nan")
    return float(x_num.loc[valid].corr(y_num.loc[valid]))


def weighted_cramers_v(values: pd.Series, y: pd.Series, weight: pd.Series) -> float:
    table = weighted_table(values, y, weight)
    return cramers_from_table(table)


def unweighted_cramers_v(values: pd.Series, y: pd.Series) -> float:
    table = pd.crosstab(values, y).astype(float)
    return cramers_from_table(table)


def weighted_table(values: pd.Series, y: pd.Series, weight: pd.Series) -> pd.DataFrame:
    data = pd.DataFrame({"value": values.astype(str), "target": y.astype(int), "weight": weight.astype(float)})
    return data.pivot_table(index="value", columns="target", values="weight", aggfunc="sum", fill_value=0.0)


def cramers_from_table(table: pd.DataFrame) -> float:
    if table.empty or table.shape[0] < 2 or table.shape[1] < 2:
        return float("nan")
    observed = table.to_numpy(dtype=float)
    total = float(observed.sum())
    if total <= 0:
        return float("nan")
    row_sum = observed.sum(axis=1, keepdims=True)
    col_sum = observed.sum(axis=0, keepdims=True)
    expected = row_sum @ col_sum / total
    valid = expected > 0
    chi_square = float((((observed - expected) ** 2) / np.where(valid, expected, np.nan))[valid].sum())
    denom = min(observed.shape[0] - 1, observed.shape[1] - 1)
    if denom <= 0:
        return float("nan")
    return math.sqrt(max(chi_square / total / denom, 0.0))


def weighted_mean(value: pd.Series, weight: pd.Series) -> float:
    valid = value.notna() & weight.notna() & (weight > 0)
    if int(valid.sum()) == 0:
        return float("nan")
    total = float(weight.loc[valid].sum())
    if total <= 0:
        return float("nan")
    return float((value.loc[valid] * weight.loc[valid]).sum() / total)


def round_or_blank(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(numeric):
        return ""
    return str(round(numeric, 8))


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in OUTPUT_COLUMNS})


def write_blocker_outputs(output_dir: Path, reason: str) -> None:
    rows = [
        base_row(
            target="admit_vs_home",
            source_layer="analytic",
            variable="blocked",
            variable_label="",
            row_type="blocker",
            method="blocked",
            status="blocked_screen_not_run",
            exclusion_reason=reason,
            denominator=empty_denominator(),
            notes=reason,
        )
    ]
    for filename in [
        "full_source_nontrauma_analytic_variable_correlations.csv",
        "full_source_nontrauma_raw_variable_correlations.csv",
        "full_source_nontrauma_transfer_variable_correlations.csv",
    ]:
        write_rows(output_dir / filename, rows)
    (output_dir / "full_source_nontrauma_variable_screen_report.md").write_text(
        "\n".join(
            [
                "# Full-Source Non-Trauma Variable Screen",
                "",
                "Status: `blocked_screen_not_run`.",
                "",
                "## Blocker",
                "",
                f"- {reason}",
                "",
                "No variable association estimate should be inferred from blocked rows.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_report(
    output_dir: Path,
    *,
    analytic: pd.DataFrame,
    raw: pd.DataFrame,
    analytic_admit: list[dict[str, Any]],
    raw_admit: list[dict[str, Any]],
    analytic_transfer: list[dict[str, Any]],
    raw_transfer: list[dict[str, Any]],
    years: list[int],
) -> None:
    admit_denom = target_counts(analytic, "admit", "routine_home_discharge")
    transfer_denom = target_counts(analytic, "transfer", "routine_home_discharge")
    lines = [
        "# Full-Source Non-Trauma Variable Screen",
        "",
        f"Screen ID: `{MODEL_ID}`",
        "Status: `screening_point_estimates`.",
        "",
        "## Method",
        "",
        f"- Years: {', '.join(str(year) for year in years)}.",
        "- Cohort: full-source NHAMCS non-trauma records; no sex, age, or abdominal-pain gate is applied.",
        "- Admission target: `endpoint_class == admit` versus `routine_home_discharge`.",
        "- Transfer target: `endpoint_class == transfer` versus `routine_home_discharge`; transfer is report-only and is not combined into the admission model.",
        "- Analytic variables are screened from the generated full-source non-trauma cohort.",
        "- Raw variables are screened from the 2018-2022 public-use source files after applying the same non-trauma restriction and endpoint classifier.",
        "- Weights use `pooled_weight = PATWT / number_of_years`.",
        "- Continuous/numeric variables use weighted Pearson/point-biserial correlation plus an unweighted comparator.",
        "- Binary variables use weighted phi/point-biserial correlation plus event/reference prevalence columns.",
        "- Categorical variables use weighted Cramer's V overall plus one-vs-rest rows for levels when level count is within the screen cap.",
        "- Outcome, disposition, survey-design, source-identifier, and record-identifier columns are excluded with explicit status rows.",
        "",
        "## Denominators",
        "",
        f"- Admit-vs-home denominator: {admit_denom['n']} rows; admission events: {admit_denom['events']}.",
        f"- Transfer-vs-home denominator: {transfer_denom['n']} rows; transfer events: {transfer_denom['events']}.",
        f"- Analytic source rows before target restriction: {len(analytic)}.",
        f"- Raw source rows before target restriction: {len(raw)}.",
        "",
        "## Outputs",
        "",
        "- `full_source_nontrauma_analytic_variable_correlations.csv`",
        "- `full_source_nontrauma_raw_variable_correlations.csv`",
        "- `full_source_nontrauma_transfer_variable_correlations.csv`",
        "",
        "## Row Counts",
        "",
        f"- Analytic admit rows: {len(analytic_admit)}.",
        f"- Raw admit rows: {len(raw_admit)}.",
        f"- Analytic transfer rows: {len(analytic_transfer)}.",
        f"- Raw transfer rows: {len(raw_transfer)}.",
        "",
        "## Limitations",
        "",
        "- These are exploratory screening point estimates, not fitted model coefficients, causal effects, validated predictors, external validation, or transportability evidence.",
        "- High-cardinality raw coded fields are blocked rather than forced into uninterpretable linear correlations.",
        "- Raw medication, treatment, and workflow variables can be downstream process markers; strong associations in those rows are not automatically valid pre-disposition predictors.",
        "- No variable is promoted to `dataset_derived` from this screen alone.",
        "- The active GitHub Pages model remains `e-dispo-v4.0`; this artifact does not change active coefficients or app behavior.",
        "",
    ]
    (output_dir / "full_source_nontrauma_variable_screen_report.md").write_text("\n".join(lines), encoding="utf-8")


def target_counts(frame: pd.DataFrame, event_class: str, reference_class: str) -> dict[str, int]:
    subset = frame[frame["endpoint_class"].isin([event_class, reference_class])]
    return {"n": int(len(subset)), "events": int(subset["endpoint_class"].eq(event_class).sum())}


if __name__ == "__main__":
    raise SystemExit(main())
