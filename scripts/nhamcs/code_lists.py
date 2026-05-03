#!/usr/bin/env python3
"""Load empirical protocol code lists and provide small mapping helpers."""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CODE_LIST_DIR = PROJECT_ROOT / "config" / "code_lists"


@lru_cache(maxsize=None)
def load_code_list(name: str) -> dict[str, Any]:
    """Load a JSON-compatible YAML code-list file by base name."""

    safe_name = name.removesuffix(".yml").removesuffix(".yaml")
    path = CODE_LIST_DIR / f"{safe_name}.yml"
    if not path.exists():
        raise FileNotFoundError(f"Code-list file not found: {path}")

    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = _load_with_optional_yaml(text, path)

    if not isinstance(payload, dict):
        raise ValueError(f"Code-list file must contain an object: {path}")
    for key in ("schema_version", "name", "review_status", "source_anchors"):
        if key not in payload:
            raise ValueError(f"Code-list file missing required key {key!r}: {path}")
    return payload


def parse_pain_score(value: object) -> float | None:
    """Parse a 0-10 pain score, preserving unknown/invalid values as missing."""

    rules = load_code_list("pain_parsing_rules")
    min_value = float(rules["numeric_range"]["min"])
    max_value = float(rules["numeric_range"]["max"])

    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, int | float):
        number = float(value)
        return _valid_score_or_none(number, min_value, max_value)

    text = str(value).strip()
    if not text:
        return None

    if _matches_any(text, rules["missing_phrase_patterns"]):
        return None

    has_zero_phrase = _matches_any(text, rules["zero_phrase_patterns"])
    fraction_matches = _fraction_matches(text, rules["explicit_fraction_patterns"])

    if len(fraction_matches) == 1:
        score = fraction_matches[0]
        if has_zero_phrase and score != 0:
            return None
        return _valid_score_or_none(score, min_value, max_value)
    if len(fraction_matches) > 1:
        return None

    numbers = [float(match.group(0)) for match in re.finditer(rules["standalone_number_pattern"], text)]
    if len(numbers) == 1:
        if has_zero_phrase and numbers[0] != 0:
            return None
        return _valid_score_or_none(numbers[0], min_value, max_value)
    if len(numbers) > 1:
        return None

    if has_zero_phrase:
        return 0.0
    return None


def assign_pain_bin3(score: object) -> str | None:
    """Assign primary 3-level pain bin: 0-3, 4-6, or 7-10."""

    return _assign_bin(score, load_code_list("pain_parsing_rules")["bin3"])


def assign_pain_bin5(score: object) -> str | None:
    """Assign sensitivity 5-level pain bin: 0, 1-3, 4-6, 7-8, or 9-10."""

    return _assign_bin(score, load_code_list("pain_parsing_rules")["bin5"])


def detect_abdominal_pain_text(text: object, include_sensitivity: bool = False) -> bool:
    """Detect MIMIC chief-complaint abdominal pain text."""

    config = load_code_list("mimic_chief_complaint_abdominal_pain")
    return _matches_config_patterns(text, config["patterns"], include_sensitivity=include_sensitivity)


def detect_vomiting_text(text: object) -> bool:
    """Detect vomiting text without treating isolated nausea as vomiting."""

    config = load_code_list("vomiting_terms")
    return _matches_config_patterns(text, config["patterns"], include_sensitivity=False)


def detect_fever_text(text: object, include_sensitivity: bool = True) -> bool:
    """Detect fever text terms. Objective temperature is handled separately."""

    config = load_code_list("fever_terms")
    return _matches_config_patterns(text, config["patterns"], include_sensitivity=include_sensitivity)


def detect_trauma_text(text: object) -> bool:
    """Detect MIMIC chief-complaint trauma exclusion text."""

    config = load_code_list("mimic_trauma_exclusions")
    return _matches_config_patterns(text, config["patterns"], include_sensitivity=False)


def _load_with_optional_yaml(text: str, path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise ValueError(
            f"{path} is not JSON-compatible YAML, and PyYAML is unavailable."
        ) from exc

    payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError(f"Code-list file must contain an object: {path}")
    return payload


def _valid_score_or_none(score: float, min_value: float, max_value: float) -> float | None:
    if not math.isfinite(score):
        return None
    if score < min_value or score > max_value:
        return None
    return score


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _fraction_matches(text: str, patterns: list[str]) -> list[float]:
    matches: list[float] = []
    for pattern in patterns:
        matches.extend(float(match.group(1)) for match in re.finditer(pattern, text, flags=re.IGNORECASE))
    return matches


def _assign_bin(score: object, bins: list[dict[str, Any]]) -> str | None:
    parsed = parse_pain_score(score)
    if parsed is None:
        return None
    for pain_bin in bins:
        if float(pain_bin["min"]) <= parsed <= float(pain_bin["max"]):
            return str(pain_bin["label"])
    return None


def _matches_config_patterns(
    text: object,
    patterns: list[dict[str, Any]],
    *,
    include_sensitivity: bool,
) -> bool:
    if text is None:
        return False
    normalized = str(text).strip()
    if not normalized:
        return False

    for item in patterns:
        use = item.get("use", "primary")
        if use == "sensitivity_only" and not include_sensitivity:
            continue
        if use in {"excluded", "rejected"}:
            continue
        if re.search(str(item["regex"]), normalized, flags=re.IGNORECASE):
            return True
    return False

