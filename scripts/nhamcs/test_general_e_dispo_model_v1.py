#!/usr/bin/env python3
"""Fixture tests for general-E-Dispo-model-v1 source fields and artifacts."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

import build_pooled_cohort
import build_yearly_cohorts
import test_nhamcs_pooled_pipeline


def main() -> int:
    test_general_source_fields_are_carried_and_recoded()
    test_general_model_r_script_writes_artifacts_or_blocker_if_r_available()
    print("general-E-Dispo-model-v1 fixture tests passed.")
    return 0


def test_general_source_fields_are_carried_and_recoded() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        years = [2018, 2019]
        config = test_nhamcs_pooled_pipeline.write_test_config(root, years)
        for year in years:
            test_nhamcs_pooled_pipeline.write_csv_fixture(root / "data" / "nhamcs" / str(year), year)

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

        yearly = pd.read_csv(yearly_dir / "full_source_nontrauma_cohort_2018.csv")
        pooled = pd.read_csv(pooled_dir / "full_source_nontrauma_cohort_nhamcs_2018_2019.csv")
        audit = pd.read_csv(pooled_dir / "harmonization_audit_by_year.csv")
        required = {"IMMEDR", "acuity_code", "AMBTRANSFER", "arrival_transfer_context", "hypotension_burden"}
        assert required.issubset(set(yearly.columns))
        assert required.issubset(set(pooled.columns))
        assert {"acuity_code", "arrival_transfer_context", "hypotension_burden"}.issubset(set(audit["field"]))
        arrival_audit = audit[audit["field"] == "arrival_transfer_context"]
        assert arrival_audit["notes"].str.contains("AMBTRANF").all()
        assert arrival_audit["notes"].str.contains("unexpected_codes=").all()
        assert "not_applicable" in set(pooled["arrival_transfer_context"])
        assert "yes_transferred_from_hospital_or_urgent_care" in set(pooled["arrival_transfer_context"])
        assert "no_not_transferred_from_hospital_or_urgent_care" in set(pooled["arrival_transfer_context"])
        assert {"blank", "unknown"}.issubset(set(pooled["acuity_code"]))

        with_sbp = pooled[pooled["SBP"].notna()].iloc[0]
        expected = max(100.0 - float(with_sbp["SBP"]), 0.0) / 10.0
        assert abs(float(with_sbp["hypotension_burden"]) - expected) < 1e-9


def test_general_model_r_script_writes_artifacts_or_blocker_if_r_available() -> None:
    rscript = test_nhamcs_pooled_pipeline.available_rscript_with_survey()
    if not rscript:
        print("Skipping general-E-Dispo-model-v1 R fixture: Rscript with survey is unavailable.")
        return

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        years = [2018, 2019]
        config = test_nhamcs_pooled_pipeline.write_test_config(root, years)
        for year in years:
            test_nhamcs_pooled_pipeline.write_csv_fixture(root / "data" / "nhamcs" / str(year), year)

        yearly_dir = root / "outputs" / "nhamcs" / "yearly"
        pooled_dir = root / "outputs" / "nhamcs_pooled"
        assert build_yearly_cohorts.main(["--config", str(config), "--output-dir", str(yearly_dir), "--years", *[str(year) for year in years]]) == 0
        assert build_pooled_cohort.main(["--config", str(config), "--yearly-output-dir", str(yearly_dir), "--output-dir", str(pooled_dir), "--years", *[str(year) for year in years]]) == 0

        cohort_path = pooled_dir / "full_source_nontrauma_cohort_nhamcs_2018_2019.csv"
        env = os.environ.copy()
        env["GENERAL_E_DISPO_PERFORMANCE_INTERVAL_REPLICATES"] = "10"
        env["GENERAL_E_DISPO_OPTIMISM_BOOTSTRAP_REPLICATES"] = "10"
        result = subprocess.run(
            [
                rscript,
                "scripts/nhamcs/nhamcs_general_e_dispo_model_v1.R",
                str(cohort_path),
                str(pooled_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            env=env,
        )
        assert result.returncode == 0, result.stderr
        for filename in [
            "general_e_dispo_model_v1_coefficients.csv",
            "general_e_dispo_model_v1_covariance.csv",
            "general_e_dispo_model_v1_performance.csv",
            "general_e_dispo_model_v1_calibration.csv",
            "general_e_dispo_model_v1_calibration_by_decile.csv",
            "general_e_dispo_model_v1_performance_intervals.csv",
            "general_e_dispo_model_v1_optimism_corrected_performance.csv",
            "general_e_dispo_model_v1_subgroup_performance.csv",
            "general_e_dispo_model_v1_subgroup_calibration.csv",
            "general_e_dispo_model_v1_missingness.csv",
            "general_e_dispo_model_v1_model_spec.json",
            "general_e_dispo_model_v1_report.md",
        ]:
            assert (pooled_dir / filename).exists(), filename

        coefficients = pd.read_csv(pooled_dir / "general_e_dispo_model_v1_coefficients.csv")
        assert set(coefficients["model_id"]) == {"general-E-Dispo-model-v1"}
        assert "survey_weighted_parallel_model" in set(coefficients["evidence_tier"])
        assert "sex" not in set(coefficients["term"])
        assert "payer" not in set(coefficients["term"])
        assert "race_ethnicity" not in set(coefficients["term"])
        performance = pd.read_csv(pooled_dir / "general_e_dispo_model_v1_performance.csv")
        assert int(performance["n"].iloc[0]) > 0
        assert str(performance["status"].iloc[0]) == "survey_weighted_parallel_model"
        subgroup = pd.read_csv(pooled_dir / "general_e_dispo_model_v1_subgroup_performance.csv")
        assert {"sex", "race_ethnicity", "payer", "region", "msa_status"}.issubset(set(subgroup["subgroup"]))

        plus_sex_result = subprocess.run(
            [
                rscript,
                "scripts/nhamcs/nhamcs_general_e_dispo_model_v1_plus_sex.R",
                str(cohort_path),
                str(pooled_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            env=env,
        )
        assert plus_sex_result.returncode == 0, plus_sex_result.stderr
        for filename in [
            "general_e_dispo_model_v1_plus_sex_coefficients.csv",
            "general_e_dispo_model_v1_plus_sex_covariance.csv",
            "general_e_dispo_model_v1_plus_sex_performance.csv",
            "general_e_dispo_model_v1_plus_sex_calibration.csv",
            "general_e_dispo_model_v1_plus_sex_calibration_by_decile.csv",
            "general_e_dispo_model_v1_plus_sex_performance_intervals.csv",
            "general_e_dispo_model_v1_plus_sex_optimism_corrected_performance.csv",
            "general_e_dispo_model_v1_plus_sex_subgroup_performance.csv",
            "general_e_dispo_model_v1_plus_sex_subgroup_calibration.csv",
            "general_e_dispo_model_v1_plus_sex_missingness.csv",
            "general_e_dispo_model_v1_plus_sex_model_spec.json",
            "general_e_dispo_model_v1_plus_sex_report.md",
            "general_e_dispo_model_v1_sex_sensitivity_comparison.csv",
        ]:
            assert (pooled_dir / filename).exists(), filename

        plus_coefficients = pd.read_csv(pooled_dir / "general_e_dispo_model_v1_plus_sex_coefficients.csv")
        assert set(plus_coefficients["model_id"]) == {"general-E-Dispo-model-v1-plus-sex"}
        assert "survey_weighted_parallel_sensitivity_model" in set(plus_coefficients["evidence_tier"])
        assert "sex" in set(plus_coefficients["term"])
        assert "payer" not in set(plus_coefficients["term"])
        assert "race_ethnicity" not in set(plus_coefficients["term"])
        assert "region" not in set(plus_coefficients["term"])
        assert "msa_status" not in set(plus_coefficients["term"])
        comparison = pd.read_csv(pooled_dir / "general_e_dispo_model_v1_sex_sensitivity_comparison.csv")
        assert {"base_general_model", "plus_sex_sensitivity", "plus_sex_minus_base"}.issubset(
            set(comparison["comparison_role"])
        )
        assert {
            "auroc",
            "brier_score",
            "calibration_in_the_large",
            "calibration_slope",
            "optimism_corrected_auroc",
            "optimism_corrected_brier_score",
            "n",
            "events",
            "model_estimable_n",
            "model_estimable_events",
            "status",
        }.issubset(set(comparison.columns))

        blocked_missing_sex_path = pooled_dir / "blocked_missing_sex.csv"
        blocked_missing_sex = pd.read_csv(cohort_path).drop(columns=["sex"])
        blocked_missing_sex.to_csv(blocked_missing_sex_path, index=False)
        blocked_missing_sex_dir = root / "blocked_missing_sex_output"
        blocked_missing_sex_dir.mkdir()
        blocked_missing_sex_result = subprocess.run(
            [
                rscript,
                "scripts/nhamcs/nhamcs_general_e_dispo_model_v1_plus_sex.R",
                str(blocked_missing_sex_path),
                str(blocked_missing_sex_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            env=env,
        )
        assert blocked_missing_sex_result.returncode == 2
        blocked_missing_sex_performance = pd.read_csv(
            blocked_missing_sex_dir / "general_e_dispo_model_v1_plus_sex_performance.csv"
        )
        assert set(blocked_missing_sex_performance["status"]) == {"blocked_not_fit"}
        assert "sex" in str(blocked_missing_sex_performance["limitation"].iloc[0])

        blocked_path = pooled_dir / "blocked_missing_arrival.csv"
        blocked = pd.read_csv(cohort_path).drop(columns=["arrival_transfer_context"])
        blocked.to_csv(blocked_path, index=False)
        blocked_dir = root / "blocked_output"
        blocked_dir.mkdir()
        blocked_result = subprocess.run(
            [
                rscript,
                "scripts/nhamcs/nhamcs_general_e_dispo_model_v1.R",
                str(blocked_path),
                str(blocked_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            env=env,
        )
        assert blocked_result.returncode == 2
        blocked_performance = pd.read_csv(blocked_dir / "general_e_dispo_model_v1_performance.csv")
        assert set(blocked_performance["status"]) == {"blocked_not_fit"}
        assert "arrival_transfer_context" in str(blocked_performance["limitation"].iloc[0])


if __name__ == "__main__":
    raise SystemExit(main())
