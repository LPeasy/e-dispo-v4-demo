from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


DATASET = "NHAMCS_2018_2022_POOLED"
SEED = 20260504
DRAW_COUNT = 10_000


@dataclass(frozen=True)
class DrawSpec:
    model_id: str
    coefficient_path: Path
    covariance_path: Path
    output_path: Path
    draw_keys: tuple[str, ...]


BASE_KEYS = (
    "intercept",
    "age_centered_40",
    "sex_2",
    "high_acuity_proxy",
    "fever_or_temp",
    "tachycardia_burden",
)

MEASURED_SBP_KEYS = (*BASE_KEYS, "hypotension_burden")

SPECS = {
    "home": DrawSpec(
        model_id="general-E-Dispo-home-v1",
        coefficient_path=Path("outputs/nhamcs_pooled/general_e_dispo_home_v1_coefficients.csv"),
        covariance_path=Path("outputs/nhamcs_pooled/general_e_dispo_home_v1_covariance.csv"),
        output_path=Path("src/data/general-e-dispo-home-coefficient-draws.csv"),
        draw_keys=BASE_KEYS,
    ),
    "measured_sbp": DrawSpec(
        model_id="general-E-Dispo-home-v1-measured-sbp",
        coefficient_path=Path("outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_coefficients.csv"),
        covariance_path=Path("outputs/nhamcs_pooled/general_e_dispo_home_v1_measured_sbp_covariance.csv"),
        output_path=Path("src/data/general-e-dispo-home-measured-sbp-coefficient-draws.csv"),
        draw_keys=MEASURED_SBP_KEYS,
    ),
}


def coefficient_key(term: str, level: str) -> str:
    if term == "intercept":
        return "intercept"
    if term == "age_centered_40":
        return "age_centered_40"
    if term == "sex" and level == "2":
        return "sex_2"
    if term == "high_acuity_proxy" and level == "1":
        return "high_acuity_proxy"
    if term == "fever_or_temp":
        return "fever_or_temp"
    if term == "tachycardia_burden":
        return "tachycardia_burden"
    if term == "hypotension_burden":
        return "hypotension_burden"
    raise ValueError(f"Unsupported coefficient row: {term}[{level}]")


def term_to_key(label: str) -> str:
    mapping = {
        "intercept": "intercept",
        "age_centered_40[per_1_year_centered_at_40]": "age_centered_40",
        "sex[2]": "sex_2",
        "high_acuity_proxy[1]": "high_acuity_proxy",
        "fever_or_temp[1]": "fever_or_temp",
        "tachycardia_burden[per_10_bpm_over_100]": "tachycardia_burden",
        "hypotension_burden[per_10_mmhg_below_100]": "hypotension_burden",
    }
    try:
        return mapping[label]
    except KeyError as error:
        raise ValueError(f"Unsupported covariance term label: {label}") from error


def read_coefficients(spec: DrawSpec) -> np.ndarray:
    values: dict[str, float] = {}
    with spec.coefficient_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["model_id"] != spec.model_id or row["dataset"] != DATASET:
                raise ValueError(f"Coefficient metadata does not match {spec.model_id}.")
            key = coefficient_key(row["term"], row["level"])
            values[key] = float(row["beta"])

    missing = [key for key in spec.draw_keys if key not in values]
    if missing:
        raise ValueError(f"{spec.model_id} coefficient artifact is missing fields: {', '.join(missing)}")

    return np.array([values[key] for key in spec.draw_keys], dtype=float)


def read_covariance(spec: DrawSpec) -> np.ndarray:
    covariance = np.zeros((len(spec.draw_keys), len(spec.draw_keys)), dtype=float)
    with spec.covariance_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["model_id"] != spec.model_id or row["dataset"] != DATASET:
                raise ValueError(f"Covariance metadata does not match {spec.model_id}.")
            row_key = term_to_key(row["row_term"])
            column_key = term_to_key(row["column_term"])
            row_index = spec.draw_keys.index(row_key)
            column_index = spec.draw_keys.index(column_key)
            covariance[row_index, column_index] = float(row["covariance"])

    if np.any(np.diag(covariance) <= 0):
        raise ValueError(f"{spec.model_id} covariance artifact has non-positive diagonal entries.")

    return stabilize_covariance(covariance)


def stabilize_covariance(covariance: np.ndarray) -> np.ndarray:
    symmetric = (covariance + covariance.T) / 2
    eigenvalues, eigenvectors = np.linalg.eigh(symmetric)
    floor = max(float(np.max(eigenvalues)) * 1e-10, 1e-12)
    clipped = np.clip(eigenvalues, floor, None)
    return (eigenvectors * clipped) @ eigenvectors.T


def write_draws(spec: DrawSpec, draws: np.ndarray) -> None:
    spec.output_path.parent.mkdir(parents=True, exist_ok=True)
    with spec.output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["draw_id", *spec.draw_keys, "seed"])
        for draw_id, draw in enumerate(draws):
            writer.writerow([draw_id, *[f"{value:.17g}" for value in draw], SEED])


def write_spec(spec: DrawSpec) -> None:
    coefficients = read_coefficients(spec)
    covariance = read_covariance(spec)
    rng = np.random.default_rng(SEED)
    draws = rng.multivariate_normal(coefficients, covariance, size=DRAW_COUNT)
    write_draws(spec, draws)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        choices=["all", *SPECS.keys()],
        default="all",
        help="Draw asset to generate. Default writes both home-facing public branches.",
    )
    args = parser.parse_args()

    specs = SPECS.values() if args.model == "all" else [SPECS[args.model]]
    for spec in specs:
        write_spec(spec)


if __name__ == "__main__":
    main()
