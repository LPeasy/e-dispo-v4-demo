#!/usr/bin/env python3
"""Smoke tests for the NHAMCS 2022 cohort and model pipeline."""

from __future__ import annotations

import tempfile
import os
from pathlib import Path

import pandas as pd

import build_cohort
import fit_models


def main() -> int:
    test_missing_data_writes_blocker()
    test_r_library_path_environment_is_explicit()
    test_nhamcs_predictor_recoding()
    test_survey_mode_auto_writes_blocker_when_r_unavailable()
    test_survey_mode_require_fails_when_r_unavailable()
    test_pipeline_with_csv_fixture()
    print("NHAMCS pipeline smoke tests passed.")
    return 0


def test_missing_data_writes_blocker() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        data_dir = root / "data" / "nhamcs"
        legacy_dir = root / "data" / "raw" / "nhamcs_2022"
        output_dir = root / "outputs" / "nhamcs"
        status = build_cohort.main(
            [
                "--data-dir",
                str(data_dir),
                "--legacy-data-dir",
                str(legacy_dir),
                "--output-dir",
                str(output_dir),
            ]
        )
        assert status == 2
        blocker = Path("outputs/blocker_report.md")
        assert blocker.exists()
        text = blocker.read_text(encoding="utf-8")
        assert "No NHAMCS 2022 source data file was found" in text
        blocker.unlink()


def test_r_library_path_environment_is_explicit() -> None:
    previous = os.environ.get("NHAMCS_R_LIBS")
    with tempfile.TemporaryDirectory() as temp:
        try:
            os.environ["NHAMCS_R_LIBS"] = temp
            paths = fit_models.configured_r_library_paths()
            assert str(Path(temp).resolve()) in paths
        finally:
            if previous is None:
                os.environ.pop("NHAMCS_R_LIBS", None)
            else:
                os.environ["NHAMCS_R_LIBS"] = previous
    next_action = fit_models.survey_next_action(
        {"survey_weighted_primary_status": "blocked_rscript_unavailable_running_exploratory_unweighted"}
    )
    assert "Rscript.exe" in next_action
    assert "package library" in next_action


def test_pipeline_with_csv_fixture() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        data_dir = root / "data" / "nhamcs"
        output_dir = root / "outputs" / "nhamcs"
        write_csv_fixture(data_dir)
        assert build_fixture_cohort(root, data_dir, output_dir) == 0
        fit_status = fit_models.main(["--output-dir", str(output_dir), "--survey-mode", "off"])
        assert fit_status == 0

        required = [
            "cohort_flow_nhamcs.csv",
            "endpoint_audit_nhamcs.csv",
            "harmonization_audit.csv",
            "missingness_by_endpoint.csv",
            "pain_unadjusted_rates.csv",
            "coefficients.csv",
            "covariance_matrix.csv",
            "mvn_coefficient_draws.csv",
            "calibration_metrics.csv",
            "calibration_by_decile.csv",
            "pain_monotonicity.csv",
            "model_run_metadata.json",
        ]
        for name in required:
            assert (output_dir / name).exists(), name

        coefficients = pd.read_csv(output_dir / "coefficients.csv")
        assert set(coefficients["evidence_tier"]) == {"exploratory"}
        pain = pd.read_csv(output_dir / "pain_monotonicity.csv")
        assert pain.loc[0, "verdict"] in {
            "exploratory_only",
            "nonmonotonic_flexible_only",
            "missingness_invalidates_inference",
            "null_or_unstable",
        }
        audit = pd.read_csv(output_dir / "harmonization_audit.csv")
        assert {"temp", "fever_or_temp", "acuity", "HR", "tachycardia_burden", "SBP"}.issubset(set(audit["field"]))


def test_nhamcs_predictor_recoding() -> None:
    frame = pd.DataFrame(
        [
            model_row(temp=986, pain=5, acuity=3, pulse=80, sbp=120),
            model_row(temp=1004, pain=-8, acuity=-8, pulse=998, sbp=-9),
            model_row(temp=-9, pain=-9, acuity=-9, pulse=-9, sbp=130),
            model_row(temp=999, pain=10, acuity=2, pulse=100, sbp=140),
            model_row(temp=986, pain=4, acuity=3, pulse=110, sbp=120),
            model_row(temp=986, pain=6, acuity=3, pulse=120, sbp=120),
        ]
    )
    config = build_cohort.read_json(build_cohort.DEFAULT_CONFIG)
    model = build_cohort.build_model_frame(frame, config)
    assert model.loc[0, "temp"] == 98.6
    assert model.loc[0, "fever_or_temp"] == 0
    assert model.loc[1, "temp"] == 100.4
    assert model.loc[1, "fever_or_temp"] == 1
    assert pd.isna(model.loc[2, "temp"])
    assert pd.isna(model.loc[2, "fever_or_temp"])
    assert model.loc[3, "temp"] == 99.9
    assert model.loc[3, "fever_or_temp"] == 0
    assert pd.isna(model.loc[1, "pain_score"])
    assert pd.isna(model.loc[2, "pain_score"])
    assert pd.isna(model.loc[1, "acuity"])
    assert pd.isna(model.loc[2, "acuity"])
    assert pd.isna(model.loc[1, "HR"])
    assert pd.isna(model.loc[2, "HR"])
    assert model.loc[0, "tachycardia_burden"] == 0
    assert pd.isna(model.loc[1, "tachycardia_burden"])
    assert pd.isna(model.loc[2, "tachycardia_burden"])
    assert model.loc[3, "tachycardia_burden"] == 0
    assert model.loc[4, "tachycardia_burden"] == 1
    assert model.loc[5, "tachycardia_burden"] == 2
    assert pd.isna(model.loc[1, "SBP"])
    audit = build_cohort.harmonization_audit_rows(frame, model, config)
    temp_audit = next(row for row in audit if row["field"] == "temp")
    assert temp_audit["raw_sentinel_n"] == 1
    assert temp_audit["post_recode_missing_n"] == 1
    assert temp_audit["median"] == "98.6"


def test_survey_mode_auto_writes_blocker_when_r_unavailable() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        data_dir = root / "data" / "nhamcs"
        output_dir = root / "outputs" / "nhamcs"
        write_csv_fixture(data_dir)
        assert build_fixture_cohort(root, data_dir, output_dir) == 0
        missing_rscript = root / "missing_Rscript.exe"
        status = fit_models.main(
            [
                "--output-dir",
                str(output_dir),
                "--survey-mode",
                "auto",
                "--rscript",
                str(missing_rscript),
            ]
        )
        assert status == 0
        blocker = output_dir / "blocker_report.md"
        assert blocker.exists()
        assert "Primary survey-weighted logistic regression was not run" in blocker.read_text(encoding="utf-8")


def test_survey_mode_require_fails_when_r_unavailable() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        data_dir = root / "data" / "nhamcs"
        output_dir = root / "outputs" / "nhamcs"
        write_csv_fixture(data_dir)
        assert build_fixture_cohort(root, data_dir, output_dir) == 0
        missing_rscript = root / "missing_Rscript.exe"
        status = fit_models.main(
            [
                "--output-dir",
                str(output_dir),
                "--survey-mode",
                "require",
                "--rscript",
                str(missing_rscript),
            ]
        )
        assert status == 2
        blocker = output_dir / "blocker_report.md"
        assert blocker.exists()
        assert "Rscript.exe" in blocker.read_text(encoding="utf-8")


def write_csv_fixture(data_dir: Path) -> None:
    data_dir.mkdir(parents=True)
    frame = pd.DataFrame([row(i) for i in range(160)])
    frame.to_csv(data_dir / "ed2022.csv", index=False)


def build_fixture_cohort(root: Path, data_dir: Path, output_dir: Path) -> int:
    return build_cohort.main(
        [
            "--data-dir",
            str(data_dir),
            "--legacy-data-dir",
            str(root / "missing"),
            "--output-dir",
            str(output_dir),
        ]
    )


def model_row(temp: int, pain: int, acuity: int, pulse: int, sbp: int) -> dict[str, object]:
    return {
        "endpoint_class": "admit",
        "include_strict_binary": True,
        "admit": 1,
        "SEX": 1,
        "AGE": 45,
        "PATWT": 1.0,
        "CSTRATM": 1,
        "CPSUM": 1,
        "PAINSCALE": pain,
        "TEMPF": temp,
        "IMMEDR": acuity,
        "PULSE": pulse,
        "BPSYS": sbp,
    }


def row(i: int) -> dict[str, object]:
    admit = i % 5 == 0
    home = not admit and i % 7 != 0 and i % 11 != 0
    obs = i % 7 == 0 and not admit
    transfer = i % 11 == 0 and not admit
    pain = i % 11
    if i % 17 == 0:
        temp = -9
    elif i % 5 == 0:
        temp = 1004
    else:
        temp = 986 + (i % 4)
    pain_value = -8 if i % 19 == 0 else (-9 if i % 23 == 0 else pain)
    acuity = -8 if i % 29 == 0 else (-9 if i % 31 == 0 else 2 + (i % 4))
    pulse = 998 if i % 37 == 0 else (-9 if i % 41 == 0 else 70 + (i % 50))
    sbp = -9 if i % 43 == 0 else 105 + (i % 45)
    return {
        "SEX": 1 if i < 150 else 2,
        "AGE": 18 + (i % 47),
        "RFV1": 15450 + (i % 4),
        "RFV2": -9,
        "RFV3": -9,
        "RFV4": -9,
        "RFV5": -9,
        "INJPOISAD": 4 if i % 13 != 0 else 1,
        "PATWT": 1.0 + (i % 3),
        "CSTRATM": 1 + (i % 4),
        "CPSUM": 1 + (i % 6),
        "PAINSCALE": pain_value,
        "TEMPF": temp,
        "IMMEDR": acuity,
        "PULSE": pulse,
        "BPSYS": sbp,
        "ADMITHOS": 1 if admit else 0,
        "OBSHOS": 0,
        "NOFU": 1 if home else 0,
        "RETRNED": 0,
        "RETREFFU": 0,
        "OBSDIS": 1 if obs else 0,
        "TRANOTH": 1 if transfer else 0,
        "TRANNH": 0,
        "TRANPSYC": 0,
        "DOA": 0,
        "DIEDED": 0,
        "LEFTAMA": 0,
        "LWBS": 0,
        "LBTC": 0,
        "OTHDISP": 0,
        "NODISP": 0,
    }


if __name__ == "__main__":
    raise SystemExit(main())
