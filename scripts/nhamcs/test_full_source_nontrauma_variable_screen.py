#!/usr/bin/env python3
"""Fixture tests for the full-source non-trauma variable screen."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

import build_pooled_cohort
import build_yearly_cohorts
import full_source_nontrauma_variable_screen
import test_nhamcs_pooled_pipeline


def main() -> int:
    test_variable_screen_writes_rows_or_blockers_for_analytic_and_raw_fields()
    print("Full-source non-trauma variable screen smoke tests passed.")
    return 0


def test_variable_screen_writes_rows_or_blockers_for_analytic_and_raw_fields() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        years = [2018, 2019]
        config = test_nhamcs_pooled_pipeline.write_test_config(root, years)
        for year in years:
            data_dir = root / "data" / "nhamcs" / str(year)
            test_nhamcs_pooled_pipeline.write_csv_fixture(data_dir, year)
            add_screen_fixture_columns(data_dir / f"ed{year}.csv", year)

        yearly_dir = root / "outputs" / "nhamcs" / "yearly"
        pooled_dir = root / "outputs" / "nhamcs_pooled"
        assert (
            build_yearly_cohorts.main(
                [
                    "--config",
                    str(config),
                    "--output-dir",
                    str(yearly_dir),
                    "--years",
                    *[str(year) for year in years],
                ]
            )
            == 0
        )
        assert (
            build_pooled_cohort.main(
                [
                    "--config",
                    str(config),
                    "--yearly-output-dir",
                    str(yearly_dir),
                    "--output-dir",
                    str(pooled_dir),
                    "--years",
                    *[str(year) for year in years],
                ]
            )
            == 0
        )

        analytic_path = pooled_dir / "full_source_nontrauma_cohort_nhamcs_2018_2019.csv"
        status = full_source_nontrauma_variable_screen.main(
            [
                "--config",
                str(config),
                "--analytic-cohort",
                str(analytic_path),
                "--output-dir",
                str(pooled_dir),
                "--years",
                *[str(year) for year in years],
            ]
        )
        assert status == 0

        analytic = pd.read_csv(analytic_path)
        analytic_rows = pd.read_csv(pooled_dir / "full_source_nontrauma_analytic_variable_correlations.csv")
        raw_rows = pd.read_csv(pooled_dir / "full_source_nontrauma_raw_variable_correlations.csv")
        transfer_rows = pd.read_csv(pooled_dir / "full_source_nontrauma_transfer_variable_correlations.csv")

        assert set(analytic.columns).issubset(set(analytic_rows["variable"]))
        assert {"AGE", "PAINSCALE", "RAW_UNIQUE_TEXT", "RAW_ALL_MISSING"}.issubset(set(raw_rows["variable"]))
        assert not analytic_rows["status"].isna().any()
        assert not raw_rows["status"].isna().any()
        assert not transfer_rows["status"].isna().any()

        endpoint_rows = analytic_rows[analytic_rows["variable"] == "endpoint_class"]
        assert set(endpoint_rows["status"]) == {"excluded_leakage_design_or_identifier"}
        disposition_rows = raw_rows[raw_rows["variable"] == "ADMITHOS"]
        assert set(disposition_rows["status"]) == {"excluded_leakage_design_or_identifier"}
        weight_rows = raw_rows[raw_rows["variable"] == "PATWT"]
        assert set(weight_rows["status"]) == {"excluded_leakage_design_or_identifier"}

        raw_age = raw_rows[(raw_rows["variable"] == "AGE") & (raw_rows["row_type"] == "continuous")]
        assert not raw_age.empty
        assert set(raw_age["status"]) == {"ok"}
        assert raw_age["estimate"].notna().all()

        high_cardinality = raw_rows[raw_rows["variable"] == "RAW_UNIQUE_TEXT"]
        assert "blocked_high_cardinality_or_unordered" in set(high_cardinality["status"])
        all_missing = raw_rows[raw_rows["variable"] == "RAW_ALL_MISSING"]
        assert "blocked_all_missing" in set(all_missing["status"])

        assert {"analytic", "raw"} == set(transfer_rows["source_layer"])
        assert set(transfer_rows["target"]) == {"transfer_vs_home"}
        transfer_age = transfer_rows[(transfer_rows["variable"] == "AGE") & (transfer_rows["source_layer"] == "raw")]
        assert not transfer_age.empty
        assert int(transfer_age["denominator_events"].iloc[0]) > 0

        report = (pooled_dir / "full_source_nontrauma_variable_screen_report.md").read_text(encoding="utf-8")
        assert "screening point estimates" in report.lower()
        assert "not combined into the admission model" in report


def add_screen_fixture_columns(path: Path, year: int) -> None:
    frame = pd.read_csv(path)
    frame["RAW_UNIQUE_TEXT"] = [f"{year}_unique_{index}" for index in range(len(frame))]
    frame["RAW_ALL_MISSING"] = pd.NA
    frame["RAW_BINARY_FLAG"] = [index % 2 for index in range(len(frame))]
    frame.to_csv(path, index=False)


if __name__ == "__main__":
    raise SystemExit(main())
