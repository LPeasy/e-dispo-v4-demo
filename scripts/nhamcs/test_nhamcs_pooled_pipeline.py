#!/usr/bin/env python3
"""Smoke tests for pooled NHAMCS yearly and pooled workflows."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

import build_pooled_cohort
import build_yearly_cohorts
import run_nhamcs_pooled_pipeline


def main() -> int:
    test_pooled_pipeline_with_csv_fixtures()
    test_missing_year_file_writes_blocker()
    test_endpoint_exclusions_match_strict_binary_logic()
    test_fever_sparse_cell_validation_fixture_if_r_available()
    print("Pooled NHAMCS pipeline smoke tests passed.")
    return 0


def test_pooled_pipeline_with_csv_fixtures() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        config = write_test_config(root, [2018, 2019])
        for year in [2018, 2019]:
            write_csv_fixture(root / "data" / "nhamcs" / str(year), year)

        yearly_dir = root / "outputs" / "nhamcs" / "yearly"
        pooled_dir = root / "outputs" / "nhamcs_pooled"
        status = run_nhamcs_pooled_pipeline.main(
            [
                "--config",
                str(config),
                "--yearly-output-dir",
                str(yearly_dir),
                "--output-dir",
                str(pooled_dir),
                "--years",
                "2018",
                "2019",
                "--survey-mode",
                "off",
            ]
        )
        assert status == 0

        for year in [2018, 2019]:
            assert (yearly_dir / f"cohort_flow_{year}.csv").exists()
            assert (yearly_dir / f"analytic_cohort_{year}.csv").exists()
            assert (yearly_dir / f"harmonization_audit_{year}.csv").exists()

        pooled_path = pooled_dir / "analytic_cohort_nhamcs_2018_2019.csv"
        assert pooled_path.exists()
        pooled = pd.read_csv(pooled_path)
        binary = pooled[pooled["include_strict_binary"].astype(str).str.lower().isin(["true", "1"])]
        assert (pooled["pooled_weight"].round(8) == (pooled["PATWT"] / 2).round(8)).all()
        assert all(
            str(stratum).startswith(f"{year}_")
            for year, stratum in zip(pooled["year"], pooled["pooled_stratum"], strict=True)
        )
        assert all(
            str(psu).startswith(f"{year}_")
            for year, psu in zip(pooled["year"], pooled["pooled_psu"], strict=True)
        )

        coefficients = pd.read_csv(pooled_dir / "coefficients.csv")
        assert "dataset_derived" not in set(coefficients["evidence_tier"])
        assert set(coefficients["dataset"]) == {"NHAMCS_2018_2019_POOLED"}
        assert "pooled_primary_reduced" in set(coefficients["model_id"])
        calibration = pd.read_csv(pooled_dir / "calibration_metrics.csv")
        primary_n = int(calibration.loc[calibration["model_id"] == "pooled_primary_reduced", "n"].iloc[0])
        assert primary_n < len(binary)
        audit = pd.read_csv(pooled_dir / "harmonization_audit_by_year.csv")
        assert {"temp", "fever_or_temp", "acuity", "HR", "tachycardia_burden", "SBP", "nausea_present"}.issubset(set(audit["field"]))
        assert int(audit.loc[audit["field"] == "temp", "raw_sentinel_n"].sum()) > 0

        metadata = json.loads((pooled_dir / "model_run_metadata.json").read_text(encoding="utf-8"))
        assert metadata["no_dataset_derived_promotion"] is True
        assert metadata["no_v4_adoption_claim"] is True
        assert metadata["event_count_gate"]["events"] == int(
            pooled.loc[pooled["include_strict_binary"].astype(str).str.lower().isin(["true", "1"]), "admit"].sum()
        )
        summary = json.loads((pooled_dir / "pooled_pipeline_summary.json").read_text(encoding="utf-8"))
        assert summary["fever_promotion_gate_status"] == "not_run"
        assert summary["final_reduced_model_activation_status"] == "not_run"
        assert summary["vomiting_promotion_gate_status"] == "not_run"
        assert summary["tachycardia_burden_activation_status"] == "not_run"
        assert summary["hematemesis_promotion_gate_status"] == "not_run"

        yearly = pd.read_csv(yearly_dir / "analytic_cohort_2018.csv")
        primary = yearly.loc[yearly["record_id"] == "2018-1"].iloc[0]
        secondary = yearly.loc[yearly["record_id"] == "2018-2"].iloc[0]
        hematemesis = yearly.loc[yearly["record_id"] == "2018-3"].iloc[0]
        primary_hematemesis = yearly.loc[yearly["record_id"] == "2018-4"].iloc[0]
        nausea = yearly.loc[yearly["record_id"] == "2018-5"].iloc[0]
        assert int(primary["vomiting_present"]) == 1
        assert int(primary["nausea_present"]) == 0
        assert primary["vomiting_rfv_position_tier"] == "primary_rfv1"
        assert int(secondary["vomiting_present"]) == 1
        assert secondary["vomiting_rfv_position_tier"] == "secondary_rfv2_5"
        assert int(hematemesis["hematemesis_present"]) == 1
        assert hematemesis["hematemesis_rfv_position_tier"] == "secondary_rfv2_5"
        assert int(hematemesis["vomiting_present"]) == 0
        assert int(primary_hematemesis["hematemesis_present"]) == 1
        assert primary_hematemesis["hematemesis_rfv_position_tier"] == "primary_rfv1"
        assert int(primary_hematemesis["vomiting_present"]) == 0
        assert int(nausea["nausea_present"]) == 1
        assert int(nausea["vomiting_present"]) == 0


def test_missing_year_file_writes_blocker() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        config = write_test_config(root, [2018, 2019])
        write_csv_fixture(root / "data" / "nhamcs" / "2018", 2018)
        yearly_dir = root / "outputs" / "nhamcs" / "yearly"
        pooled_dir = root / "outputs" / "nhamcs_pooled"

        status = run_nhamcs_pooled_pipeline.main(
            [
                "--config",
                str(config),
                "--yearly-output-dir",
                str(yearly_dir),
                "--output-dir",
                str(pooled_dir),
                "--years",
                "2018",
                "2019",
                "--survey-mode",
                "off",
            ]
        )
        assert status == 2
        blocker = pooled_dir / "blocker_report.md"
        assert blocker.exists()
        text = blocker.read_text(encoding="utf-8")
        assert "Yearly cohort construction failed" in text
        assert "No NHAMCS 2019 source data file was found" in text


def test_endpoint_exclusions_match_strict_binary_logic() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        config = write_test_config(root, [2022])
        data_dir = root / "data" / "nhamcs" / "2022"
        data_dir.mkdir(parents=True)
        rows = [
            fixture_row(0, admit=True),
            fixture_row(1, home=True),
            fixture_row(2, home=False, obs=True),
            fixture_row(3, home=False, transfer=True),
            fixture_row(4, home=False, ama=True),
            fixture_row(5, admit=False, home=False, lbtc=True),
            fixture_row(6, home=False, other=True),
            fixture_row(7, admit=True, home=True),
        ]
        pd.DataFrame(rows).to_csv(data_dir / "ed2022.csv", index=False)

        yearly_dir = root / "outputs" / "nhamcs" / "yearly"
        status = build_yearly_cohorts.main(
            [
                "--config",
                str(config),
                "--output-dir",
                str(yearly_dir),
                "--years",
                "2022",
            ]
        )
        assert status == 0
        analytic = pd.read_csv(yearly_dir / "analytic_cohort_2022.csv")
        binary = analytic[analytic["include_strict_binary"].astype(str).str.lower().isin(["true", "1"])]
        assert len(binary) == 2
        assert int(binary["admit"].sum()) == 1
        assert set(analytic["endpoint_class"]) == {
            "admit",
            "routine_home_discharge",
            "observation",
            "transfer",
            "AMA",
            "LWBS_LBTC",
            "other",
            "conflict",
        }


def test_fever_sparse_cell_validation_fixture_if_r_available() -> None:
    rscript = available_rscript_with_survey()
    if not rscript:
        print("Skipping fever sparse-cell R fixture: Rscript with survey is unavailable.")
        return

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        years = [2018, 2019, 2020, 2021, 2022]
        config = write_test_config(root, years)
        for year in years:
            write_fever_validation_fixture(root / "data" / "nhamcs" / str(year), year)

        yearly_dir = root / "outputs" / "nhamcs" / "yearly"
        pooled_dir = root / "outputs" / "nhamcs_pooled"
        status = run_nhamcs_pooled_pipeline.main(
            [
                "--config",
                str(config),
                "--yearly-output-dir",
                str(yearly_dir),
                "--output-dir",
                str(pooled_dir),
                "--years",
                *[str(year) for year in years],
                "--survey-mode",
                "off",
            ]
        )
        assert status == 0

        cohort_path = pooled_dir / "analytic_cohort_nhamcs_2018_2022.csv"
        result = subprocess.run(
            [
                rscript,
                "scripts/nhamcs/nhamcs_fever_sparse_cell_validation.R",
                str(cohort_path),
                str(pooled_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0, result.stderr

        required_outputs = [
            "fever_sparse_cell_counts_by_year.csv",
            "fever_missing_temperature_audit.csv",
            "fever_model_comparison_coefficients.csv",
            "fever_model_comparison_covariance.csv",
            "fever_model_comparison_draws.csv",
            "fever_model_comparison_calibration.csv",
            "fever_model_comparison_deciles.csv",
            "fever_leave_one_year_out_validation.csv",
            "fever_sparse_cell_gate_decision.csv",
            "fever_sparse_cell_validation_report.md",
        ]
        for filename in required_outputs:
            assert (pooled_dir / filename).exists(), filename

        pooled = pd.read_csv(cohort_path)
        binary = pooled[pooled["include_strict_binary"].astype(str).str.lower().isin(["true", "1"])]
        assert (binary.loc[binary["temp"] == 100.4, "fever_or_temp"] == 1).all()
        assert (binary.loc[binary["temp"] == 98.6, "fever_or_temp"] == 0).all()
        assert binary["fever_or_temp"].isna().any()

        audit = pd.read_csv(pooled_dir / "fever_missing_temperature_audit.csv")
        assert "temp_missing" in set(audit["temp_status"])
        coefficients = pd.read_csv(pooled_dir / "fever_model_comparison_coefficients.csv")
        assert "dataset_derived" not in set(coefficients["evidence_tier"])
        assert "fever_candidate_complete_temp" in set(coefficients["model_id"])
        draws = pd.read_csv(pooled_dir / "fever_model_comparison_draws.csv")
        fever_draws = draws[
            (draws["model_id"] == "fever_candidate_complete_temp")
            & (draws["term"] == "fever_or_temp")
        ]
        assert fever_draws["draw_id"].nunique() == 10000
        calibration = pd.read_csv(pooled_dir / "fever_model_comparison_calibration.csv")
        fever_n = int(
            calibration.loc[
                calibration["model_id"] == "fever_candidate_complete_temp",
                "n",
            ].iloc[0]
        )
        assert fever_n < len(binary)
        loo = pd.read_csv(pooled_dir / "fever_leave_one_year_out_validation.csv")
        assert set(loo["heldout_year"]) == set(years)
        assert {"fever_base_complete_temp", "fever_candidate_complete_temp"} == set(loo["model_id"])

        result = subprocess.run(
            [
                rscript,
                "scripts/nhamcs/nhamcs_vomiting_validation.R",
                str(cohort_path),
                str(pooled_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        vomiting_outputs = [
            "vomiting_cell_counts_by_year.csv",
            "vomiting_unadjusted_rates_by_year.csv",
            "vomiting_model_comparison_coefficients.csv",
            "vomiting_model_comparison_covariance.csv",
            "vomiting_model_comparison_draws.csv",
            "vomiting_model_comparison_calibration.csv",
            "vomiting_model_comparison_deciles.csv",
            "vomiting_leave_one_year_out_validation.csv",
            "vomiting_tier_sensitivity.csv",
            "vomiting_gate_decision.csv",
            "vomiting_validation_report.md",
        ]
        for filename in vomiting_outputs:
            assert (pooled_dir / filename).exists(), filename
        vomiting_counts = pd.read_csv(pooled_dir / "vomiting_cell_counts_by_year.csv")
        assert int(
            vomiting_counts.loc[
                (vomiting_counts["year"].astype(str) == "pooled")
                & (vomiting_counts["group"] == "hematemesis_present")
                & (vomiting_counts["level"].astype(str) == "1"),
                "n",
            ].iloc[0]
        ) > 0
        vomiting_coefficients = pd.read_csv(pooled_dir / "vomiting_model_comparison_coefficients.csv")
        assert "dataset_derived" not in set(vomiting_coefficients["evidence_tier"])
        assert "vomiting_candidate_binary_complete_temp" in set(vomiting_coefficients["model_id"])
        vomiting_draws = pd.read_csv(pooled_dir / "vomiting_model_comparison_draws.csv")
        binary_vomiting_draws = vomiting_draws[
            (vomiting_draws["model_id"] == "vomiting_candidate_binary_complete_temp")
            & (vomiting_draws["term"] == "vomiting_present")
        ]
        assert binary_vomiting_draws["draw_id"].nunique() == 10000

        result = subprocess.run(
            [
                rscript,
                "scripts/nhamcs/nhamcs_tachycardia_burden_validation.R",
                str(cohort_path),
                str(pooled_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        tachycardia_outputs = [
            "tachycardia_burden_cell_counts.csv",
            "tachycardia_model_comparison_coefficients.csv",
            "tachycardia_model_comparison_covariance.csv",
            "tachycardia_model_comparison_draws.csv",
            "tachycardia_model_comparison_calibration.csv",
            "tachycardia_model_comparison_deciles.csv",
            "tachycardia_burden_leave_one_year_out_validation.csv",
            "tachycardia_burden_gate_decision.csv",
            "tachycardia_burden_term_decisions.csv",
            "tachycardia_burden_validation_report.md",
        ]
        for filename in tachycardia_outputs:
            assert (pooled_dir / filename).exists(), filename
        pooled = pd.read_csv(cohort_path)
        binary = pooled[pooled["include_strict_binary"].astype(str).str.lower().isin(["true", "1"])]
        complete_tachy = binary[
            (binary["pain_missing"] == 0)
            & binary["pain_bin3"].notna()
            & binary["fever_or_temp"].notna()
            & binary["vomiting_present"].notna()
            & binary["HR"].notna()
            & binary["tachycardia_burden"].notna()
        ]
        tachy_calibration = pd.read_csv(pooled_dir / "tachycardia_model_comparison_calibration.csv")
        tachy_n = int(
            tachy_calibration.loc[
                tachy_calibration["model_id"] == "pooled_empirical_v2_age_pain_fever_vomiting_tachycardia",
                "n",
            ].iloc[0]
        )
        assert tachy_n == len(complete_tachy)
        tachy_coefficients = pd.read_csv(pooled_dir / "tachycardia_model_comparison_coefficients.csv")
        assert "pooled_empirical_v2_age_pain_fever_vomiting_tachycardia" in set(tachy_coefficients["model_id"])
        tachy_draws = pd.read_csv(pooled_dir / "tachycardia_model_comparison_draws.csv")
        burden_draws = tachy_draws[
            (tachy_draws["model_id"] == "pooled_empirical_v2_age_pain_fever_vomiting_tachycardia")
            & (tachy_draws["term"] == "tachycardia_burden")
        ]
        assert burden_draws["draw_id"].nunique() == 10000

        result = subprocess.run(
            [
                rscript,
                "scripts/nhamcs/nhamcs_hematemesis_validation.R",
                str(cohort_path),
                str(pooled_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        hematemesis_outputs = [
            "hematemesis_cell_counts_by_year.csv",
            "hematemesis_unadjusted_rates_by_year.csv",
            "hematemesis_model_comparison_coefficients.csv",
            "hematemesis_model_comparison_covariance.csv",
            "hematemesis_model_comparison_draws.csv",
            "hematemesis_model_comparison_calibration.csv",
            "hematemesis_model_comparison_deciles.csv",
            "hematemesis_leave_one_year_out_validation.csv",
            "hematemesis_tier_sensitivity.csv",
            "hematemesis_gate_decision.csv",
            "hematemesis_validation_report.md",
        ]
        for filename in hematemesis_outputs:
            assert (pooled_dir / filename).exists(), filename
        hematemesis_counts = pd.read_csv(pooled_dir / "hematemesis_cell_counts_by_year.csv")
        assert int(
            hematemesis_counts.loc[
                (hematemesis_counts["year"].astype(str) == "pooled")
                & (hematemesis_counts["group"] == "hematemesis_present")
                & (hematemesis_counts["level"].astype(str) == "1"),
                "n",
            ].iloc[0]
        ) > 0
        hematemesis_decision = pd.read_csv(pooled_dir / "hematemesis_gate_decision.csv")
        hematemesis_status = hematemesis_decision.loc[
            hematemesis_decision["gate"] == "promotion_suitability",
            "status",
        ].iloc[0]
        assert hematemesis_status != "eligible_for_evidence_promotion"
        hematemesis_coefficients = pd.read_csv(pooled_dir / "hematemesis_model_comparison_coefficients.csv")
        assert "dataset_derived" not in set(hematemesis_coefficients["evidence_tier"])

        result = subprocess.run(
            [
                rscript,
                "scripts/nhamcs/nhamcs_nausea_candidate_screen.R",
                str(cohort_path),
                str(pooled_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        nausea_outputs = [
            "nausea_mapping_audit.csv",
            "nausea_model_comparison_metadata.csv",
            "nausea_cell_counts_by_year.csv",
            "nausea_missingness_by_endpoint.csv",
            "nausea_model_comparison_coefficients.csv",
            "nausea_model_comparison_covariance.csv",
            "nausea_model_comparison_draws.csv",
            "nausea_model_comparison_calibration.csv",
            "nausea_leave_one_year_out_validation.csv",
            "nausea_candidate_gate_decision.csv",
            "nausea_candidate_ranked_decision.csv",
            "nausea_candidate_screen_report.md",
        ]
        for filename in nausea_outputs:
            assert (pooled_dir / filename).exists(), filename
        nausea_coefficients = pd.read_csv(pooled_dir / "nausea_model_comparison_coefficients.csv")
        assert "dataset_derived" not in set(nausea_coefficients["evidence_tier"])
        assert "nausea_present" in set(nausea_coefficients["term"])
        nausea_metadata = pd.read_csv(pooled_dir / "nausea_model_comparison_metadata.csv")
        assert {"e_dispo_v4_base_refit_for_nausea_screen", "e_dispo_v4_plus_nausea_candidate"} == set(nausea_metadata["model_id"])
        assert all(nausea_metadata["formula"].str.contains("pain_severe"))
        assert all(nausea_metadata["fitting_method"].str.contains("survey::svyglm"))
        assert all(nausea_metadata["evidence_tier"] == "survey_weighted_candidate")
        nausea_decision = pd.read_csv(pooled_dir / "nausea_candidate_ranked_decision.csv")
        assert str(nausea_decision["recommended_for_active_model_change"].iloc[0]).lower() in {"false", "0"}

        decision = pd.read_csv(pooled_dir / "fever_sparse_cell_gate_decision.csv")
        final_status = decision.loc[decision["gate"] == "promotion_suitability", "status"].iloc[0]
        assert final_status != "eligible_for_evidence_promotion"

        result = subprocess.run(
            [
                rscript,
                "scripts/nhamcs/nhamcs_final_reduced_model_gate.R",
                str(cohort_path),
                str(pooled_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        for filename in [
            "final_reduced_model_cell_counts.csv",
            "final_reduced_model_leave_one_year_out_terms.csv",
            "final_reduced_model_calibration.csv",
            "final_reduced_model_gate_decision.csv",
            "final_reduced_model_term_decisions.csv",
            "final_reduced_model_activation_decision.md",
        ]:
            assert (pooled_dir / filename).exists(), filename
        final_decision = pd.read_csv(pooled_dir / "final_reduced_model_gate_decision.csv")
        activation_status = final_decision.loc[
            final_decision["gate"] == "activation_suitability",
            "status",
        ].iloc[0]
        assert activation_status != "eligible_for_educational_activation"


def available_rscript_with_survey() -> str:
    candidates = [
        os.environ.get("RSCRIPT_PATH", ""),
        r"C:\Program Files\R\R-4.6.0\bin\Rscript.exe",
        "Rscript",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        if candidate == "Rscript" and shutil.which(candidate) is None:
            continue
        if candidate != "Rscript" and not Path(candidate).exists():
            continue
        try:
            result = subprocess.run(
                [
                    candidate,
                    "-e",
                    "source('scripts/nhamcs/r_environment.R'); nhamcs_configure_r_environment(); quit(status=ifelse(requireNamespace('survey', quietly=TRUE), 0, 2))",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except FileNotFoundError:
            continue
        if result.returncode == 0:
            return candidate
    return ""


def write_test_config(root: Path, years: list[int]) -> Path:
    config = {
        "schema_version": "1.0.0",
        "pool": {
            "name": "test_pool",
            "years": years,
            "mapping_status": "fixture_confirmed",
        },
        "codes": {
            "male": [1],
            "nonTrauma": [4],
            "flagTrue": [1, "1", "Y", "YES", True],
        },
        "years": [year_config(root, year) for year in years],
    }
    path = root / "config" / "nhamcs_year_harmonization.yml"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def year_config(root: Path, year: int) -> dict[str, object]:
    source = root / "data" / "nhamcs" / str(year) / f"ed{year}.csv"
    return {
        "year": year,
        "source_file": str(source),
        "source_globs": [str(source)],
        "age_variable": "AGE",
        "sex_variable": "SEX",
        "rfv_variables": ["RFV1", "RFV2", "RFV3", "RFV4", "RFV5"],
        "pain_variable": "PAINSCALE",
        "temperature_variable": "TEMPF",
        "triage_variable": "IMMEDR",
        "heart_rate_variable": "PULSE",
        "systolic_bp_variable": "BPSYS",
        "trauma_variable": "INJPOISAD",
        "patwt_variable": "PATWT",
        "cstratm_variable": "CSTRATM",
        "cpsum_variable": "CPSUM",
        "disposition_flags": {
            "admit": ["ADMITHOS"],
            "observationHospitalized": ["OBSHOS"],
            "homeRelease": ["NOFU", "RETRNED", "RETREFFU"],
            "observationDischarged": ["OBSDIS"],
            "transferAcute": ["TRANOTH"],
            "transferOther": ["TRANNH", "TRANPSYC"],
            "death": ["DOA", "DIEDED"],
            "nonroutineExit": ["LEFTAMA", "LWBS", "LBTC"],
            "otherUnknown": ["OTHDISP", "NODISP"],
        },
        "known_coding_differences": ["fixture"],
    }


def write_csv_fixture(data_dir: Path, year: int) -> None:
    data_dir.mkdir(parents=True)
    rows = []
    for i in range(180):
        if i == 0:
            rows.append(fixture_row(i, rfv1=15300, rfv2=15450))
        elif i == 1:
            rows.append(fixture_row(i, rfv2=15300))
        elif i == 2:
            rows.append(fixture_row(i, rfv2=15802))
        elif i == 3:
            rows.append(fixture_row(i, rfv1=15802, rfv2=15450))
        elif i == 4:
            rows.append(fixture_row(i, rfv2=15250))
        else:
            rows.append(fixture_row(i))
    frame = pd.DataFrame(rows)
    frame.to_csv(data_dir / f"ed{year}.csv", index=False)


def write_fever_validation_fixture(data_dir: Path, year: int) -> None:
    data_dir.mkdir(parents=True)
    rows = []
    for i in range(80):
        fever = i in {0, 1}
        missing_temp = i in {2, 3}
        admit = (fever and i == 0) or (not fever and i % 9 == 0)
        home = not admit
        primary_vomiting = i in {45, 55}
        secondary_vomiting = i % 5 == 0 and not primary_vomiting
        hematemesis = i == 7
        nausea = i % 8 == 0
        rows.append(
            fixture_row(
                i,
                admit=admit,
                home=home,
                temp=-9 if missing_temp else (1004 if fever else 986),
                rfv1=15300 if primary_vomiting else None,
                rfv2=15450 if primary_vomiting else (15300 if secondary_vomiting else -9),
                rfv3=15802 if hematemesis else -9,
                rfv4=15250 if nausea else -9,
            )
        )
    pd.DataFrame(rows).to_csv(data_dir / f"ed{year}.csv", index=False)


def fixture_row(
    i: int,
    *,
    admit: bool | None = None,
    home: bool | None = None,
    temp: int | None = None,
    obs: bool = False,
    transfer: bool = False,
    ama: bool = False,
    lbtc: bool = False,
    other: bool = False,
    rfv1: int | None = None,
    rfv2: int | None = None,
    rfv3: int | None = None,
    rfv4: int | None = None,
    rfv5: int | None = None,
) -> dict[str, object]:
    admit_value = (i % 5 == 0) if admit is None else admit
    home_value = (not admit_value and i % 7 != 0 and i % 11 != 0) if home is None else home
    obs_value = (i % 7 == 0 and not admit_value and home is None) or obs
    transfer_value = (i % 11 == 0 and not admit_value and home is None) or transfer
    return {
        "SEX": 1,
        "AGE": 18 + (i % 47),
        "RFV1": rfv1 if rfv1 is not None else 15450 + (i % 4),
        "RFV2": rfv2 if rfv2 is not None else -9,
        "RFV3": rfv3 if rfv3 is not None else -9,
        "RFV4": rfv4 if rfv4 is not None else -9,
        "RFV5": rfv5 if rfv5 is not None else -9,
        "INJPOISAD": 4,
        "PATWT": 1.0 + (i % 4),
        "CSTRATM": 1 + (i % 5),
        "CPSUM": 1 + (i % 7),
        "PAINSCALE": -8 if i % 19 == 0 else (-9 if i % 23 == 0 else i % 11),
        "TEMPF": temp if temp is not None else (-9 if i % 17 == 0 else (1004 if i % 5 == 0 else 986 + (i % 4))),
        "IMMEDR": -8 if i % 29 == 0 else (-9 if i % 31 == 0 else 2 + (i % 4)),
        "PULSE": 998 if i % 37 == 0 else (-9 if i % 41 == 0 else 70 + (i % 50)),
        "BPSYS": -9 if i % 43 == 0 else 105 + (i % 45),
        "ADMITHOS": 1 if admit_value else 0,
        "OBSHOS": 0,
        "NOFU": 1 if home_value else 0,
        "RETRNED": 0,
        "RETREFFU": 0,
        "OBSDIS": 1 if obs_value else 0,
        "TRANOTH": 1 if transfer_value else 0,
        "TRANNH": 0,
        "TRANPSYC": 0,
        "DOA": 0,
        "DIEDED": 0,
        "LEFTAMA": 1 if ama else 0,
        "LWBS": 0,
        "LBTC": 1 if lbtc else 0,
        "OTHDISP": 1 if other else 0,
        "NODISP": 0,
    }


if __name__ == "__main__":
    raise SystemExit(main())
