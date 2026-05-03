#!/usr/bin/env python3
"""Run the NHAMCS cohort-building and model-fitting workflow."""

from __future__ import annotations

import argparse
from pathlib import Path

import build_cohort
import fit_models


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run NHAMCS 2022 empirical pipeline.")
    parser.add_argument("--data-dir", default=build_cohort.DEFAULT_DATA_DIR, type=Path)
    parser.add_argument("--legacy-data-dir", default=build_cohort.DEFAULT_LEGACY_DATA_DIR, type=Path)
    parser.add_argument("--output-dir", default=build_cohort.DEFAULT_OUTPUT_DIR, type=Path)
    parser.add_argument("--config", default=build_cohort.DEFAULT_CONFIG, type=Path)
    parser.add_argument("--survey-mode", choices=["auto", "require", "off"], default="auto")
    parser.add_argument("--rscript", default="")
    args = parser.parse_args(argv)

    cohort_status = build_cohort.main(
        [
            "--data-dir",
            str(args.data_dir),
            "--legacy-data-dir",
            str(args.legacy_data_dir),
            "--output-dir",
            str(args.output_dir),
            "--config",
            str(args.config),
        ]
    )
    if cohort_status != 0:
        return cohort_status

    fit_args = ["--output-dir", str(args.output_dir), "--survey-mode", args.survey_mode]
    if args.rscript:
        fit_args.extend(["--rscript", args.rscript])
    return fit_models.main(fit_args)


if __name__ == "__main__":
    raise SystemExit(main())
