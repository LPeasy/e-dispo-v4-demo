from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


MODEL_ID = "general-E-Dispo-model-v1-plus-sex"
DATASET = "NHAMCS_2018_2022_POOLED"
SEED = 20260429
DRAW_COUNT = 10_000

DRAW_KEYS = [
    "intercept",
    "age_centered_40",
    "sex_2",
    "acuity_code_blank",
    "acuity_code_unknown",
    "acuity_code_no_triage_esa_conducts_triage",
    "acuity_code_immediate",
    "acuity_code_emergent",
    "acuity_code_semi_urgent",
    "acuity_code_nonurgent",
    "acuity_code_no_nursing_triage_esa",
    "arrival_transfer_context_blank",
    "arrival_transfer_context_unknown",
    "arrival_transfer_context_not_applicable",
    "arrival_transfer_context_yes_transferred_from_hospital_or_urgent_care",
    "fever_or_temp",
    "tachycardia_burden",
    "hypotension_burden",
]

TERM_TO_KEY = {
    "intercept": "intercept",
    "age_centered_40[per_1_year_centered_at_40]": "age_centered_40",
    "sex[2]": "sex_2",
    "acuity_code[blank]": "acuity_code_blank",
    "acuity_code[unknown]": "acuity_code_unknown",
    "acuity_code[no_triage_esa_conducts_triage]": "acuity_code_no_triage_esa_conducts_triage",
    "acuity_code[immediate]": "acuity_code_immediate",
    "acuity_code[emergent]": "acuity_code_emergent",
    "acuity_code[semi_urgent]": "acuity_code_semi_urgent",
    "acuity_code[nonurgent]": "acuity_code_nonurgent",
    "acuity_code[no_nursing_triage_esa]": "acuity_code_no_nursing_triage_esa",
    "arrival_transfer_context[blank]": "arrival_transfer_context_blank",
    "arrival_transfer_context[unknown]": "arrival_transfer_context_unknown",
    "arrival_transfer_context[not_applicable]": "arrival_transfer_context_not_applicable",
    "arrival_transfer_context[yes_transferred_from_hospital_or_urgent_care]": "arrival_transfer_context_yes_transferred_from_hospital_or_urgent_care",
    "fever_or_temp[1]": "fever_or_temp",
    "tachycardia_burden[per_10_bpm_over_100]": "tachycardia_burden",
    "hypotension_burden[per_10_mmhg_below_100]": "hypotension_burden",
}


def coefficient_key(term: str, level: str) -> str:
    if term == "intercept":
      return "intercept"
    if term == "age_centered_40":
      return "age_centered_40"
    if term == "sex" and level == "2":
      return "sex_2"
    if term == "acuity_code":
      return f"acuity_code_{level}"
    if term == "arrival_transfer_context":
      return f"arrival_transfer_context_{level}"
    if term == "fever_or_temp":
      return "fever_or_temp"
    if term == "tachycardia_burden":
      return "tachycardia_burden"
    if term == "hypotension_burden":
      return "hypotension_burden"
    raise ValueError(f"Unsupported coefficient row: {term}[{level}]")


def read_coefficients(path: Path) -> np.ndarray:
    values: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["model_id"] != MODEL_ID or row["dataset"] != DATASET:
                raise ValueError("Coefficient artifact metadata does not match the expected general model.")
            key = coefficient_key(row["term"], row["level"])
            values[key] = float(row["beta"])

    missing = [key for key in DRAW_KEYS if key not in values]
    if missing:
        raise ValueError(f"Coefficient artifact is missing fields: {', '.join(missing)}")

    return np.array([values[key] for key in DRAW_KEYS], dtype=float)


def read_covariance(path: Path) -> np.ndarray:
    covariance = np.zeros((len(DRAW_KEYS), len(DRAW_KEYS)), dtype=float)
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["model_id"] != MODEL_ID or row["dataset"] != DATASET:
                raise ValueError("Covariance artifact metadata does not match the expected general model.")
            row_key = TERM_TO_KEY[row["row_term"]]
            column_key = TERM_TO_KEY[row["column_term"]]
            row_index = DRAW_KEYS.index(row_key)
            column_index = DRAW_KEYS.index(column_key)
            covariance[row_index, column_index] = float(row["covariance"])

    if np.any(np.diag(covariance) <= 0):
        raise ValueError("Covariance artifact has non-positive diagonal entries.")

    return stabilize_covariance(covariance)


def stabilize_covariance(covariance: np.ndarray) -> np.ndarray:
    symmetric = (covariance + covariance.T) / 2
    eigenvalues, eigenvectors = np.linalg.eigh(symmetric)
    floor = max(float(np.max(eigenvalues)) * 1e-10, 1e-12)
    clipped = np.clip(eigenvalues, floor, None)
    return (eigenvectors * clipped) @ eigenvectors.T


def write_draws(output_path: Path, draws: np.ndarray) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["draw_id", *DRAW_KEYS, "seed"])
        for draw_id, draw in enumerate(draws):
            writer.writerow([draw_id, *[f"{value:.17g}" for value in draw], SEED])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--coefficients",
        type=Path,
        default=Path("outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_coefficients.csv"),
    )
    parser.add_argument(
        "--covariance",
        type=Path,
        default=Path("outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_covariance.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("src/data/general-e-dispo-coefficient-draws.csv"),
    )
    args = parser.parse_args()

    coefficients = read_coefficients(args.coefficients)
    covariance = read_covariance(args.covariance)
    rng = np.random.default_rng(SEED)
    draws = rng.multivariate_normal(coefficients, covariance, size=DRAW_COUNT)
    write_draws(args.output, draws)


if __name__ == "__main__":
    main()
