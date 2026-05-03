#!/usr/bin/env python3
"""Fixture checks for NHAMCS endpoint recoding and validation artifact counts."""

from __future__ import annotations

import pandas as pd

import derive_nhamcs_2022 as derive
import validate_nhamcs_2022 as validate


def main() -> int:
    config = validate.read_json(validate.DEFAULT_CONFIG)
    frame = pd.DataFrame(
        [
            row(ADMITHOS=1, PATWT=1),
            row(NOFU=1, PATWT=2),
            row(OBSDIS=1, PATWT=3),
            row(TRANOTH=1, PATWT=4),
            row(TRANNH=1, PATWT=5),
            row(DIEDED=1, ADMITHOS=1, PATWT=6),
            row(LEFTAMA=1, PATWT=7),
            row(OTHDISP=1, PATWT=8),
            row(ADMITHOS=1, NOFU=1, PATWT=9),
        ]
    )

    masks = validate.cohort_masks(frame, config["variables"], config["codes"])
    cohort = frame.loc[masks["non_trauma"]].copy()
    endpoint = derive.recode_endpoint_masks(
        cohort,
        config["variables"]["dispositionFlags"],
        config["codes"]["flagTrue"],
    )

    primary = validate.endpoint_counts(cohort, endpoint, "PATWT")
    sensitivity = validate.sensitivity_counts(cohort, endpoint, "PATWT")

    assert primary["admit"] == 1
    assert primary["treatAndRelease"] == 1
    assert primary["excluded"] == 7
    assert primary["excludedObservationDischarged"] == 1
    assert primary["excludedTransfer"] == 2
    assert primary["excludedSentinelDeath"] == 1
    assert primary["excludedNonroutineExit"] == 1
    assert primary["excludedOtherUnknown"] == 1
    assert primary["excludedConflict"] == 1
    assert primary["weighted"]["admit"] == 1
    assert primary["weighted"]["treatAndRelease"] == 2
    assert primary["weighted"]["excluded"] == 42
    assert primary["weighted"]["excludedConflict"] == 9

    assert sensitivity["endpointSensAEventualHome"]["admit"] == 1
    assert sensitivity["endpointSensAEventualHome"]["treatAndRelease"] == 2
    assert sensitivity["endpointSensAEventualHome"]["excluded"] == 6
    assert sensitivity["endpointSensBAcuteEscalation"]["acuteEscalationPositive"] == 2
    assert sensitivity["endpointSensBAcuteEscalation"]["treatAndRelease"] == 2
    assert sensitivity["endpointSensBAcuteEscalation"]["excluded"] == 5

    print("NHAMCS validation fixture tests passed.")
    return 0


def row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "SEX": 1,
        "AGE": 40,
        "RFV1": 15450,
        "RFV2": -9,
        "RFV3": -9,
        "RFV4": -9,
        "RFV5": -9,
        "INJPOISAD": 4,
        "PATWT": 1,
        "EDWT": 1,
        "CSTRATM": 1,
        "CPSUM": 1,
        "RACERETH": 1,
        "PAYTYPER": 1,
        "REGION": 1,
        "MSA": 1,
        "PAINSCALE": 5,
        "TEMPF": 98.6,
        "ADMITHOS": 0,
        "OBSHOS": 0,
        "NOFU": 0,
        "RETRNED": 0,
        "RETREFFU": 0,
        "OBSDIS": 0,
        "TRANOTH": 0,
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
    base.update(overrides)
    return base


if __name__ == "__main__":
    raise SystemExit(main())
