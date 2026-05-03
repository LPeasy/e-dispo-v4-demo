#!/usr/bin/env python3
"""Smoke tests for the MIMIC-IV-ED replication pipeline."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

import build_cohort
import fit_models


def main() -> int:
    test_missing_data_writes_blocker()
    test_pipeline_with_csv_fixture()
    print("MIMIC pipeline smoke tests passed.")
    return 0


def test_missing_data_writes_blocker() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        status = build_cohort.main(["--data-dir", str(root / "data" / "mimic"), "--output-dir", str(root / "outputs" / "mimic")])
        assert status == 2
        blocker = root / "outputs" / "mimic" / "blocker_report.md"
        assert blocker.exists()
        assert "Required MIMIC-IV-ED source files are missing" in blocker.read_text(encoding="utf-8")


def test_pipeline_with_csv_fixture() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        data_dir = root / "data" / "mimic"
        output_dir = root / "outputs" / "mimic"
        data_dir.mkdir(parents=True)
        write_fixture(data_dir)

        assert build_cohort.main(["--data-dir", str(data_dir), "--output-dir", str(output_dir)]) == 0
        assert fit_models.main(["--output-dir", str(output_dir)]) == 0

        required = [
            "cohort_flow_mimic.csv",
            "endpoint_audit_mimic.csv",
            "missingness_by_endpoint.csv",
            "pain_unadjusted_rates.csv",
            "coefficients.csv",
            "covariance_matrix.csv",
            "posterior_draws.csv",
            "calibration_metrics.csv",
            "calibration_by_decile.csv",
            "pain_monotonicity.csv",
            "model_run_metadata.json",
        ]
        for name in required:
            assert (output_dir / name).exists(), name
        coefficients = pd.read_csv(output_dir / "coefficients.csv")
        assert set(coefficients["evidence_tier"]) == {"mimic_replication_only"}
        pain = pd.read_csv(output_dir / "pain_monotonicity.csv")
        assert pain.loc[0, "verdict"] in {
            "nonmonotonic_flexible_only",
            "null_or_unstable",
            "missingness_invalidates_inference",
            "exploratory_only",
        }


def write_fixture(data_dir: Path) -> None:
    ed_rows = []
    triage_rows = []
    dx_rows = []
    for i in range(180):
        admitted = i % 5 == 0
        conflict_home = i == 10
        transfer = i == 11
        disposition = "ADMITTED" if admitted else "HOME"
        if transfer:
            disposition = "TRANSFER"
        hadm_id = 100000 + i if admitted else ""
        if conflict_home:
            disposition = "HOME"
            hadm_id = 200000
        stay_id = 300000 + i
        subject_id = 1000 + (i % 120)
        ed_rows.append(
            {
                "subject_id": subject_id,
                "stay_id": stay_id,
                "hadm_id": hadm_id,
                "intime": "2150-01-01 00:00:00",
                "gender": "M" if i < 170 else "F",
                "disposition": disposition,
            }
        )
        location = ["abdominal pain", "abd. pain", "stomach pain", "RUQ pain"][i % 4]
        if i % 19 == 0:
            location = "fall with abdominal pain"
        triage_rows.append(
            {
                "subject_id": subject_id,
                "stay_id": stay_id,
                "temperature": 98.0 + (i % 5),
                "heartrate": 70 + (i % 45),
                "resprate": 16 + (i % 6),
                "o2sat": 96 + (i % 4),
                "sbp": 105 + (i % 50),
                "dbp": 60 + (i % 20),
                "pain": str(i % 11),
                "acuity": 2 + (i % 4),
                "chiefcomplaint": location + (" nausea/vomiting" if i % 6 == 0 else ""),
            }
        )
        dx_rows.append(
            {
                "subject_id": subject_id,
                "stay_id": stay_id,
                "seq_num": 1,
                "icd_code": "R109" if i % 23 != 0 else "S399",
                "icd_version": 10,
                "icd_title": "Abdominal pain",
            }
        )
    pd.DataFrame(ed_rows).to_csv(data_dir / "edstays.csv", index=False)
    pd.DataFrame(triage_rows).to_csv(data_dir / "triage.csv", index=False)
    pd.DataFrame(dx_rows).to_csv(data_dir / "diagnosis.csv", index=False)
    pd.DataFrame(
        [{"subject_id": 1000 + i, "age_at_ed": 18 + (i % 47)} for i in range(120)]
    ).to_csv(data_dir / "age_at_ed.csv", index=False)


if __name__ == "__main__":
    raise SystemExit(main())
