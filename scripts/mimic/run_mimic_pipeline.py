#!/usr/bin/env python3
"""Run the MIMIC-IV-ED replication/proxy-validation pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

import build_cohort
import fit_models


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run MIMIC-IV-ED empirical pipeline.")
    parser.add_argument("--data-dir", default=build_cohort.DEFAULT_DATA_DIR, type=Path)
    parser.add_argument("--output-dir", default=build_cohort.DEFAULT_OUTPUT_DIR, type=Path)
    args = parser.parse_args(argv)

    cohort_status = build_cohort.main(["--data-dir", str(args.data_dir), "--output-dir", str(args.output_dir)])
    if cohort_status != 0:
        return cohort_status
    return fit_models.main(["--output-dir", str(args.output_dir)])


if __name__ == "__main__":
    raise SystemExit(main())
