#!/usr/bin/env python3
"""Fixture tests for the NHCS 2022 ED audit pipeline."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

import build_nhcs_2022_ed_audit as audit


def main() -> int:
    test_missing_file_writes_blocker()
    test_missing_columns_write_blocker()
    test_cohort_flow_status_and_trauma_flags()
    test_jackknife_standard_error_matches_manual_calculation()
    test_reliability_flags()
    test_outputs_do_not_write_app_export_or_promote_evidence()
    print("NHCS 2022 ED audit fixture tests passed.")
    return 0


def test_missing_file_writes_blocker() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        status = audit.main(["--raw-dir", str(root / "raw"), "--output-dir", str(root / "outputs")])
        blocker = root / "outputs" / "blocker_report.md"
        assert status == 2
        assert blocker.exists()
        text = blocker.read_text(encoding="utf-8")
        assert "Required NHCS 2022 ED public-use input files are missing." in text


def test_missing_columns_write_blocker() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        raw = root / "raw"
        raw.mkdir()
        (raw / audit.NHCS_CODEBOOK_FILE).write_text("fixture", encoding="utf-8")
        (raw / audit.NHCS_TECH_DOC_FILE).write_text("fixture", encoding="utf-8")
        pd.DataFrame([{"PUF_ID": "one"}]).to_stata(raw / audit.NHCS_DATA_FILE, write_index=False)

        status = audit.main(["--raw-dir", str(raw), "--output-dir", str(root / "outputs")])
        blocker = root / "outputs" / "blocker_report.md"
        assert status == 2
        text = blocker.read_text(encoding="utf-8")
        assert "Required NHCS 2022 ED columns are absent." in text
        assert "DISCHARGE_STATUS" in text


def test_cohort_flow_status_and_trauma_flags() -> None:
    frame = fixture_frame()
    outputs = audit.build_outputs(frame, replicate_weights=fixture_replicates())
    flow = {row["step"]: row for row in outputs["cohort_flow"]}
    assert flow["all_ed_records"]["unweighted_n"] == 9
    assert flow["adult_male_18_64_not_newborn"]["unweighted_n"] == 7
    assert flow["adult_male_abdominal_proxy"]["unweighted_n"] == 6
    assert flow["possible_injury_trauma_proxy"]["unweighted_n"] == 2
    assert flow["noninjury_sensitivity_slice"]["unweighted_n"] == 4

    status_rows = {row["metric"]: row for row in outputs["discharge_status_summary"]}
    assert status_rows["discharge_status_1"]["unweighted_numerator_n"] == 1
    assert status_rows["discharge_status_2"]["unweighted_numerator_n"] == 1
    assert status_rows["discharge_status_3"]["unweighted_numerator_n"] == 1
    assert status_rows["discharge_status_-9"]["unweighted_numerator_n"] == 1

    proxy_rows = {row["metric"]: row for row in outputs["proxy_endpoint_sensitivity"]}
    assert proxy_rows["nonroutine_discharge_proxy"]["unweighted_numerator_n"] == 4
    assert proxy_rows["acute_escalation_proxy"]["unweighted_numerator_n"] == 2
    assert proxy_rows["nonroutine_discharge_proxy"]["validation_claim"] == "not_external_validation"


def test_jackknife_standard_error_matches_manual_calculation() -> None:
    estimate = 60.0
    replicates = [59.0, 61.0]
    observed = audit.jackknife_standard_error(estimate, replicates)
    assert round(observed, 6) == round(2**0.5, 6)


def test_reliability_flags() -> None:
    small = audit.reliability_for_count(20, 100.0, 1.0)
    assert small["status"] == "suppress"
    assert "unweighted_n_below_30" in small["reasons"]

    noisy = audit.reliability_for_count(50, 100.0, 40.0)
    assert noisy["status"] == "flag"
    assert "relative_standard_error_above_30_percent" in noisy["reasons"]

    sparse = audit.reliability_for_proportion(
        denominator_n=100,
        event_n=5,
        proportion=0.05,
        standard_error=0.01,
        replicate_df=99,
    )
    assert sparse["status"] == "flag"
    assert "sparse_event_or_complement_below_30" in sparse["reasons"]

    wide = audit.reliability_for_proportion(
        denominator_n=100,
        event_n=50,
        proportion=0.5,
        standard_error=0.1,
        replicate_df=99,
    )
    assert wide["status"] == "suppress"
    assert "absolute_ci_width_at_least_0_30" in wide["reasons"]


def test_outputs_do_not_write_app_export_or_promote_evidence() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        outputs = audit.build_outputs(fixture_frame(), replicate_weights=fixture_replicates())
        audit.write_outputs(outputs, root)
        assert not (root / "app_export.json").exists()
        for path in root.iterdir():
            if path.is_file():
                assert "dataset_derived" not in path.read_text(encoding="utf-8")


def fixture_replicates() -> list[str]:
    return ["PUF_ENCWGT_1", "PUF_ENCWGT_2"]


def fixture_frame() -> pd.DataFrame:
    rows = [
        row("r1", 30, 1, 2, 1, 1, "R109", sym004=1),
        row("r2", 40, 1, 2, 1, 2, "R101"),
        row("r3", 55, 1, 2, 1, 3, "R103"),
        row("r4", 45, 1, 2, 1, -9, "R108"),
        row("r5", 35, 1, 2, 0, 1, "R079"),
        row("r6", 35, 2, 2, 1, 1, "R109"),
        row("r7", 70, 1, 2, 1, 1, "R109"),
        row("r8", 25, 1, 2, 1, 7, "R109", inj017=1),
        row("r9", 28, 1, 2, 1, 8, "K529", dx2="S099"),
    ]
    return pd.DataFrame(rows)


def row(
    puf_id: str,
    age: int,
    sex: int,
    newborn: int,
    sym006: int,
    discharge_status: int,
    dx1: str,
    *,
    dx2: str = "-9",
    sym004: int = 0,
    inj017: int = 0,
) -> dict[str, object]:
    base: dict[str, object] = {
        "PUF_ID": puf_id,
        "year": 2022,
        "age": age,
        "sex": sex,
        "newborn": newborn,
        "DISCHARGE_STATUS": discharge_status,
        "CCSR_SYM006": sym006,
        "CCSR_SYM004": sym004,
        "CCSR_CIR012": 0,
        "CCSR_CIR019": 0,
        "CCSR_END005": 0,
        "CCSR_END011": 0,
        "CCSR_INJ017": inj017,
        "PUF_ENCWGT_BASE": 10.0,
        "PUF_ENCWGT_1": 9.0,
        "PUF_ENCWGT_2": 11.0,
    }
    for index in range(1, 31):
        base[f"DX{index}"] = "-9"
    base["DX1"] = dx1
    base["DX2"] = dx2
    return base


if __name__ == "__main__":
    raise SystemExit(main())
