#!/usr/bin/env python3
"""Build a small derived NHAMCS 2022 artifact for the static app.

Raw NHAMCS files stay local. The output JSON is intentionally small and must
pass the app-side schema gate before the UI can label coefficients as
NHAMCS-derived.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import zipfile
from datetime import date
from pathlib import Path
from typing import Any


STATA_ZIP_URL = (
    "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/"
    "Dataset_Documentation/NHAMCS/stata/ed2022-stata.zip"
)
DEFAULT_RAW_DIR = Path("data/raw/nhamcs_2022")
DEFAULT_OUTPUT = Path("artifacts/nhamcs/nhamcs-2022-derived.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate derived NHAMCS 2022 cohort and endpoint artifact."
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT, type=Path)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--fit", action="store_true")
    args = parser.parse_args()

    config = read_json(args.config)
    raw_dir = args.raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)

    if args.download:
        download_stata_archive(raw_dir)

    dta_path = find_stata_file(raw_dir, config.get("stataFile"))
    if dta_path is None:
        print(
            "No .dta file found. Run with --download or place the extracted "
            "CDC Stata .dta under the raw directory.",
            file=sys.stderr,
        )
        return 2

    try:
        import pandas as pd
    except ImportError:
        print("pandas is required to read NHAMCS Stata files.", file=sys.stderr)
        return 2

    df = pd.read_stata(dta_path, convert_categoricals=False)
    artifact = build_artifact(df, config, fit=args.fit)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote derived artifact: {args.output}")
    return 0


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def download_stata_archive(raw_dir: Path) -> None:
    zip_path = raw_dir / "ed2022-stata.zip"
    if not zip_path.exists():
        print(f"Downloading {STATA_ZIP_URL}")
        urllib.request.urlretrieve(STATA_ZIP_URL, zip_path)

    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(raw_dir)


def find_stata_file(raw_dir: Path, configured_name: Any) -> Path | None:
    if isinstance(configured_name, str):
        configured_path = raw_dir / configured_name
        if configured_path.exists():
            return configured_path

    dta_files = sorted(raw_dir.rglob("*.dta"))
    return dta_files[0] if dta_files else None


def build_artifact(df: Any, config: dict[str, Any], fit: bool) -> dict[str, Any]:
    variables = config["variables"]
    codes = config["codes"]
    initial_count = int(len(df))

    male_mask = df[variables["sex"]].isin(codes["male"])
    age_mask = df[variables["age"]].between(18, 64, inclusive="both")
    abdominal_mask = any_column_matches(df, variables["reasonForVisit"], codes["abdominalPainRfv"])

    cohort = df[male_mask & age_mask & abdominal_mask].copy()
    flow = [
        {"step": "All 2022 NHAMCS ED records", "count": initial_count},
        {"step": "Male", "count": int(male_mask.sum())},
        {"step": "Age 18-64", "count": int((male_mask & age_mask).sum())},
        {
            "step": "Abdominal pain reason-for-visit proxy",
            "count": int(len(cohort)),
        },
    ]

    trauma_variable = variables.get("trauma")
    if trauma_variable:
        if "nonTrauma" in codes:
            non_trauma_mask = cohort[trauma_variable].isin(codes["nonTrauma"])
        else:
            non_trauma_mask = ~cohort[trauma_variable].isin(codes.get("traumaExclude", []))
        cohort = cohort[non_trauma_mask].copy()
        flow.append({"step": "Non-trauma proxy", "count": int(len(cohort))})

    endpoint = recode_endpoint_masks(
        cohort,
        variables["dispositionFlags"],
        codes.get("flagTrue", [1, "1", "Y", "YES", True]),
    )
    binary_mask = endpoint["primary_admit"] | endpoint["primary_treat_and_release"]
    binary_cohort = cohort[binary_mask].copy()
    binary_y = endpoint["primary_admit"][binary_mask].astype(int)

    flow.append(
        {
            "step": "Endpoint-refined primary binary disposition",
            "count": int(len(binary_cohort)),
        }
    )

    coefficients = []
    limitations = list(config.get("limitations", []))

    if fit and len(binary_cohort) > 0:
        coefficients, fit_limitations = fit_logistic_model(
            binary_cohort,
            binary_y,
            config.get("modelColumns", []),
        )
        limitations.extend(fit_limitations)
    else:
        limitations.append(
            "Coefficient fitting was not requested or no binary cohort was available."
        )

    if not coefficients:
        limitations.append(
            "No empirical coefficients are emitted; the app should keep prototype labels active."
        )

    return {
        "schemaVersion": "1.0.0",
        "sourceDataset": "NHAMCS 2022 ED public-use file",
        "derivedAt": date.today().isoformat(),
        "cohortFlow": flow,
        "endpointCounts": {
            "admit": count_true(endpoint["primary_admit"]),
            "treatAndRelease": count_true(endpoint["primary_treat_and_release"]),
            "excluded": count_true(endpoint["primary_excluded"]),
            "excludedObservationDischarged": count_true(
                endpoint["primary_excluded_observation_discharged"]
            ),
            "excludedTransfer": count_true(endpoint["primary_excluded_transfer"]),
            "excludedSentinelDeath": count_true(
                endpoint["primary_excluded_sentinel_death"]
            ),
            "excludedNonroutineExit": count_true(
                endpoint["primary_excluded_nonroutine_exit"]
            ),
            "excludedOtherUnknown": count_true(
                endpoint["primary_excluded_other_unknown"]
            ),
            "excludedConflict": count_true(endpoint["primary_excluded_conflict"]),
        },
        "sensitivityEndpointCounts": {
            "endpointSensAEventualHome": {
                "admit": count_true(endpoint["sens_a_admit"]),
                "treatAndRelease": count_true(endpoint["sens_a_treat_and_release"]),
                "excluded": count_true(endpoint["sens_a_excluded"]),
            },
            "endpointSensBAcuteEscalation": {
                "acuteEscalationPositive": count_true(endpoint["sens_b_positive"]),
                "treatAndRelease": count_true(endpoint["sens_b_treat_and_release"]),
                "excluded": count_true(endpoint["sens_b_excluded"]),
            },
        },
        "coefficients": coefficients,
        "predictorMapping": config["predictorMapping"],
        "limitations": limitations,
    }


def any_column_matches(df: Any, columns: list[str], values: list[Any]) -> Any:
    available_columns = [column for column in columns if column in df.columns]
    if not available_columns:
        return false_mask(df)

    masks = [
        df[column].astype(str).str.strip().isin([str(value) for value in values])
        for column in available_columns
    ]
    combined = masks[0]
    for mask in masks[1:]:
        combined = combined | mask
    return combined


def recode_endpoint_masks(
    df: Any,
    disposition_flags: dict[str, list[str]],
    true_values: list[Any],
) -> dict[str, Any]:
    admit = flag_mask(df, disposition_flags.get("admit", []), true_values)
    obs_hos = flag_mask(
        df,
        disposition_flags.get("observationHospitalized", []),
        true_values,
    )
    home = flag_mask(df, disposition_flags.get("homeRelease", []), true_values)
    obs_dis = flag_mask(
        df,
        disposition_flags.get("observationDischarged", []),
        true_values,
    )
    transfer_acute = flag_mask(
        df,
        disposition_flags.get("transferAcute", []),
        true_values,
    )
    transfer_other = flag_mask(
        df,
        disposition_flags.get("transferOther", []),
        true_values,
    )
    death = flag_mask(df, disposition_flags.get("death", []), true_values)
    nonroutine = flag_mask(
        df,
        disposition_flags.get("nonroutineExit", []),
        true_values,
    )
    other_unknown = flag_mask(
        df,
        disposition_flags.get("otherUnknown", []),
        true_values,
    )

    admit_or_obshos = admit | obs_hos
    transfer_any = transfer_acute | transfer_other
    terminal_classes = {
        "admit_or_obshos": admit_or_obshos,
        "home": home,
        "obs_dis": obs_dis,
        "transfer_any": transfer_any,
        "nonroutine": nonroutine,
        "other_unknown": other_unknown,
    }
    terminal_count = false_mask(df).astype(int)
    for mask in terminal_classes.values():
        terminal_count = terminal_count + mask.astype(int)

    remaining = ~death
    conflict = remaining & (terminal_count > 1)
    remaining = remaining & ~conflict
    primary_transfer = remaining & transfer_any
    remaining = remaining & ~primary_transfer
    primary_nonroutine = remaining & nonroutine
    remaining = remaining & ~primary_nonroutine
    primary_admit = remaining & admit_or_obshos
    remaining = remaining & ~primary_admit
    primary_release = remaining & home
    remaining = remaining & ~primary_release
    primary_obs_dis = remaining & obs_dis
    remaining = remaining & ~primary_obs_dis
    primary_other_unknown = remaining

    primary_excluded = (
        death
        | conflict
        | primary_transfer
        | primary_nonroutine
        | primary_obs_dis
        | primary_other_unknown
    )

    sens_a_ineligible = death | conflict | transfer_any | nonroutine | other_unknown
    sens_a_admit = ~sens_a_ineligible & admit_or_obshos
    sens_a_release = ~sens_a_ineligible & (home | obs_dis)
    sens_a_excluded = ~(sens_a_admit | sens_a_release)

    sens_b_ineligible = death | conflict | transfer_other | nonroutine | other_unknown
    sens_b_positive = ~sens_b_ineligible & (admit_or_obshos | transfer_acute)
    sens_b_release = ~sens_b_ineligible & (home | obs_dis)
    sens_b_excluded = ~(sens_b_positive | sens_b_release)

    return {
        "primary_admit": primary_admit,
        "primary_treat_and_release": primary_release,
        "primary_excluded": primary_excluded,
        "primary_excluded_observation_discharged": primary_obs_dis,
        "primary_excluded_transfer": primary_transfer,
        "primary_excluded_sentinel_death": death,
        "primary_excluded_nonroutine_exit": primary_nonroutine,
        "primary_excluded_other_unknown": primary_other_unknown,
        "primary_excluded_conflict": conflict,
        "sens_a_admit": sens_a_admit,
        "sens_a_treat_and_release": sens_a_release,
        "sens_a_excluded": sens_a_excluded,
        "sens_b_positive": sens_b_positive,
        "sens_b_treat_and_release": sens_b_release,
        "sens_b_excluded": sens_b_excluded,
    }


def flag_mask(df: Any, columns: list[str], true_values: list[Any]) -> Any:
    available_columns = [column for column in columns if column in df.columns]
    if not available_columns:
        return false_mask(df)

    true_string_values = {str(value).strip().upper() for value in true_values}
    combined = false_mask(df)
    for column in available_columns:
        values = df[column]
        combined = combined | values.isin(true_values)
        combined = combined | values.astype(str).str.strip().str.upper().isin(
            true_string_values
        )
    return combined


def false_mask(df: Any) -> Any:
    return df.index.to_series(index=df.index).isin([])


def count_true(mask: Any) -> int:
    return int(mask.sum())


def fit_logistic_model(df: Any, y: Any, model_columns: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    if not model_columns:
        return [], ["No modelColumns were configured for empirical coefficient fitting."]

    try:
        import pandas as pd
        import statsmodels.api as sm
    except ImportError:
        return [], ["statsmodels is required for empirical coefficient fitting."]

    missing_columns = [column for column in model_columns if column not in df.columns]
    if missing_columns:
        return [], [f"Missing configured model columns: {', '.join(missing_columns)}."]

    x = pd.get_dummies(df[model_columns].astype("category"), drop_first=True)
    x = sm.add_constant(x, has_constant="add")
    fit = sm.Logit(y, x).fit(disp=False)

    coefficients = []
    for key, mean in fit.params.items():
        coefficients.append(
            {
                "key": str(key),
                "mean": float(mean),
                "standardError": float(fit.bse[key]),
                "source": "nhamcs_2022",
            }
        )

    return coefficients, []


if __name__ == "__main__":
    raise SystemExit(main())
