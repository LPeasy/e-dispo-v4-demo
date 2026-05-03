#!/usr/bin/env python3
"""Fixture checks for empirical code-list helpers."""

from __future__ import annotations

import code_lists


def main() -> int:
    test_load_code_lists()
    test_pain_parser()
    test_pain_bins()
    test_abdominal_pain_detection()
    test_vomiting_detection()
    test_fever_detection()
    test_trauma_detection()
    print("Code-list helper fixture tests passed.")
    return 0


def test_load_code_lists() -> None:
    expected_names = [
        "schema",
        "nhamcs_abdominal_pain_rfv",
        "nhamcs_vomiting_rfv",
        "nhamcs_trauma_exclusions",
        "nhamcs_endpoint_flags",
        "mimic_chief_complaint_abdominal_pain",
        "mimic_trauma_exclusions",
        "vomiting_terms",
        "fever_terms",
        "pain_parsing_rules",
    ]
    for name in expected_names:
        payload = code_lists.load_code_list(name)
        assert payload["name"] == name
        assert payload["source_anchors"]

    schema = code_lists.load_code_list("schema")
    assert schema["format"] == "json_compatible_yaml"

    abdominal = code_lists.load_code_list("nhamcs_abdominal_pain_rfv")
    assert [row["stored_code"] for row in abdominal["codes"]] == [15450, 15451, 15452, 15453]
    assert all(row["review_status"] == "confirmed_codebook" for row in abdominal["codes"])

    vomiting = code_lists.load_code_list("nhamcs_vomiting_rfv")
    vomiting_codes = {row["stored_code"]: row for row in vomiting["codes"]}
    assert vomiting_codes[15300]["include_exclude"] == "include"
    assert vomiting_codes[15802]["include_exclude"] == "separate_candidate"
    assert vomiting_codes[15250]["include_exclude"] == "exclude"
    assert all(row["review_status"] == "confirmed_codebook" for row in vomiting["codes"])

    trauma = code_lists.load_code_list("nhamcs_trauma_exclusions")
    assert trauma["primary_rule"]["field"] == "INJPOISAD"
    assert trauma["primary_rule"]["keep_codes"] == [4]
    assert trauma["primary_rule"]["review_status"] == "confirmed_codebook"

    endpoint = code_lists.load_code_list("nhamcs_endpoint_flags")
    all_flags = {flag for group in endpoint["groups"] for flag in group["flags"]}
    assert {"ADMITHOS", "OBSHOS", "NOFU", "RETREFFU", "OBSDIS", "TRANOTH", "DOA", "DIEDED", "LEFTAMA", "LWBS", "LBTC", "OTHDISP", "NODISP"} <= all_flags


def test_pain_parser() -> None:
    assert code_lists.parse_pain_score(0) == 0
    assert code_lists.parse_pain_score(7) == 7
    assert code_lists.parse_pain_score("10/10") == 10
    assert code_lists.parse_pain_score("0/10") == 0
    assert code_lists.parse_pain_score("8 out of 10 for 2 days") == 8
    assert code_lists.parse_pain_score("denies pain") == 0
    assert code_lists.parse_pain_score("no pain, 0/10") == 0

    assert code_lists.parse_pain_score(None) is None
    assert code_lists.parse_pain_score("") is None
    assert code_lists.parse_pain_score("unable to assess") is None
    assert code_lists.parse_pain_score("refused") is None
    assert code_lists.parse_pain_score("uta") is None
    assert code_lists.parse_pain_score("nonverbal") is None
    assert code_lists.parse_pain_score("12/10") is None
    assert code_lists.parse_pain_score("-1") is None
    assert code_lists.parse_pain_score("pain 7 and 8") is None
    assert code_lists.parse_pain_score("denies pain but also says 7/10") is None


def test_pain_bins() -> None:
    assert code_lists.assign_pain_bin3(0) == "0-3"
    assert code_lists.assign_pain_bin3(3) == "0-3"
    assert code_lists.assign_pain_bin3(4) == "4-6"
    assert code_lists.assign_pain_bin3(7) == "7-10"
    assert code_lists.assign_pain_bin3("unable") is None

    assert code_lists.assign_pain_bin5(0) == "0"
    assert code_lists.assign_pain_bin5(1) == "1-3"
    assert code_lists.assign_pain_bin5(6) == "4-6"
    assert code_lists.assign_pain_bin5(8) == "7-8"
    assert code_lists.assign_pain_bin5(9) == "9-10"


def test_abdominal_pain_detection() -> None:
    positives = [
        "abdominal pain",
        "abd pain",
        "abd. pain",
        "stomach pain",
        "epigastric pain",
        "RUQ pain",
        "right upper quadrant pain",
        "RLQ pain",
        "right lower quadrant pain",
        "LLQ pain",
        "left lower quadrant pain",
        "LUQ pain",
        "left upper quadrant pain",
        "suprapubic pain",
    ]
    for text in positives:
        assert code_lists.detect_abdominal_pain_text(text), text

    assert not code_lists.detect_abdominal_pain_text("flank pain")
    assert code_lists.detect_abdominal_pain_text("flank pain", include_sensitivity=True)
    assert not code_lists.detect_abdominal_pain_text("chest pain")


def test_vomiting_detection() -> None:
    positives = [
        "vomiting",
        "vomited twice",
        "emesis",
        "nausea/vomiting",
        "nausea and vomiting",
        "N/V",
        "NV",
        "vomit",
    ]
    for text in positives:
        assert code_lists.detect_vomiting_text(text), text

    assert not code_lists.detect_vomiting_text("nausea")
    assert not code_lists.detect_vomiting_text("")


def test_fever_detection() -> None:
    assert code_lists.detect_fever_text("fever")
    assert code_lists.detect_fever_text("febrile at home")
    assert code_lists.detect_fever_text("chills")
    assert not code_lists.detect_fever_text("afebrile")
    assert not code_lists.detect_fever_text("abdominal pain")


def test_trauma_detection() -> None:
    positives = [
        "trauma",
        "injury",
        "fall",
        "MVC",
        "motor vehicle crash",
        "assault",
        "laceration",
        "stab wound",
        "gunshot wound",
        "fracture",
        "burn",
        "accident",
        "hit by car",
        "struck by vehicle",
        "blunt trauma",
    ]
    for text in positives:
        assert code_lists.detect_trauma_text(text), text

    assert not code_lists.detect_trauma_text("nontraumatic abdominal pain")


if __name__ == "__main__":
    raise SystemExit(main())
