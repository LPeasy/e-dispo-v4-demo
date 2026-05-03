#!/usr/bin/env python3
"""Shared decision engine for empirical evidence gates."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import calibration  # noqa: E402
import pain_monotonicity  # noqa: E402


PROJECT_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_OUTPUT_DIR = Path("outputs/combined")
SOURCE_DIRS = [Path("outputs/nhamcs"), Path("outputs/mimic")]
POOLED_DATASET = "NHAMCS_2018_2022_POOLED"
POOLED_FEVER_SOURCE_MODEL = "fever_candidate_complete_temp"
POOLED_FEVER_EXPORT_MODEL = "pooled_empirical_v1_age_pain_fever"
POOLED_FEVER_TERMS = {"intercept", "age_centered", "pain_bin3", "pain_missing", "fever_or_temp"}
POOLED_VOMITING_SOURCE_MODEL = "vomiting_candidate_binary_complete_temp"
POOLED_VOMITING_EXPORT_MODEL = "pooled_empirical_v1_age_pain_fever_vomiting"
POOLED_VOMITING_TERMS = {"intercept", "age_centered", "pain_bin3", "pain_missing", "fever_or_temp", "vomiting_present"}
POOLED_HEMATEMESIS_SOURCE_MODEL = "hematemesis_candidate_binary_complete_temp"
POOLED_HEMATEMESIS_EXPORT_MODEL = "pooled_empirical_v1_age_pain_fever_vomiting_hematemesis"
POOLED_HEMATEMESIS_TERMS = {
    "intercept",
    "age_centered",
    "pain_bin3",
    "pain_missing",
    "fever_or_temp",
    "vomiting_present",
    "hematemesis_present",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run shared empirical evidence decisions.")
    parser.add_argument("--nhamcs-dir", default=Path("outputs/nhamcs"), type=Path)
    parser.add_argument("--mimic-dir", default=Path("outputs/mimic"), type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    args = parser.parse_args(argv)

    bundle = load_bundle([args.nhamcs_dir, args.mimic_dir])
    decisions = build_decisions(bundle)
    write_outputs(decisions, args.output_dir)
    print(f"Wrote combined evidence decisions under {args.output_dir}")
    return 0


def load_bundle(source_dirs: list[Path]) -> dict[str, Any]:
    bundle = {
        "pain_rates": [],
        "pain_summary": [],
        "coefficients": [],
        "calibration": [],
        "missingness": [],
        "fever_gate": [],
        "vomiting_gate": [],
        "hematemesis_gate": [],
        "final_gate": [],
        "final_term_decisions": [],
        "codebook_audit": [],
        "metadata": {},
        "artifacts": {},
        "available_sources": [],
        "missing_files": [],
    }
    for source_dir in source_dirs:
        if not source_dir.exists():
            bundle["missing_files"].append(str(source_dir))
            continue
        dataset = dataset_for_source_dir(source_dir)
        bundle["artifacts"][dataset] = artifact_status(source_dir)
        bundle["available_sources"].append(str(source_dir))
        file_map = file_map_for_dataset(dataset)
        for key, filename in file_map.items():
            path = source_dir / filename
            if path.exists():
                rows = read_csv(path)
                if dataset == POOLED_DATASET and key in {"coefficients", "calibration"}:
                    rows = add_pooled_aliases(rows, key)
                bundle[key].extend(rows)
            else:
                bundle["missing_files"].append(str(path))
        if dataset == POOLED_DATASET:
            for key, filename in {
                "coefficients": "vomiting_model_comparison_coefficients.csv",
                "calibration": "vomiting_model_comparison_calibration.csv",
            }.items():
                path = source_dir / filename
                if path.exists():
                    bundle[key].extend(add_pooled_vomiting_aliases(read_csv(path), key))
                else:
                    bundle["missing_files"].append(str(path))
            for key, filename in {
                "coefficients": "hematemesis_model_comparison_coefficients.csv",
                "calibration": "hematemesis_model_comparison_calibration.csv",
            }.items():
                path = source_dir / filename
                if path.exists():
                    bundle[key].extend(add_pooled_hematemesis_aliases(read_csv(path), key))
                else:
                    bundle["missing_files"].append(str(path))
            for key, filename in {
                "pain_summary": "pain_monotonicity.csv",
                "fever_gate": "fever_sparse_cell_gate_decision.csv",
                "vomiting_gate": "vomiting_gate_decision.csv",
                "hematemesis_gate": "hematemesis_gate_decision.csv",
                "final_gate": "final_reduced_model_gate_decision.csv",
                "final_term_decisions": "final_reduced_model_term_decisions.csv",
                "codebook_audit": "codebook_confirmation_audit.csv",
            }.items():
                path = source_dir / filename
                if path.exists():
                    bundle[key].extend(read_csv(path))
                else:
                    bundle["missing_files"].append(str(path))
        metadata_path = source_dir / "model_run_metadata.json"
        if metadata_path.exists():
            bundle["metadata"][str(source_dir)] = json.loads(metadata_path.read_text(encoding="utf-8"))
    return bundle


def file_map_for_dataset(dataset: str) -> dict[str, str]:
    if dataset == POOLED_DATASET:
        return {
            "pain_rates": "pain_unadjusted_rates_by_year.csv",
            "coefficients": "fever_model_comparison_coefficients.csv",
            "calibration": "fever_model_comparison_calibration.csv",
            "missingness": "missingness_by_year_and_endpoint.csv",
        }
    return {
        "pain_rates": "pain_unadjusted_rates.csv",
        "coefficients": "coefficients.csv",
        "calibration": "calibration_metrics.csv",
        "missingness": "missingness_by_endpoint.csv",
    }


def add_pooled_aliases(rows: list[dict[str, str]], key: str) -> list[dict[str, str]]:
    out = list(rows)
    for row in rows:
        if row.get("dataset") != POOLED_DATASET:
            continue
        if row.get("model_id") != POOLED_FEVER_SOURCE_MODEL:
            continue
        alias = dict(row)
        alias["source_model_id"] = POOLED_FEVER_SOURCE_MODEL
        alias["model_id"] = POOLED_FEVER_EXPORT_MODEL
        if key == "coefficients" and alias.get("term") in POOLED_FEVER_TERMS:
            out.append(alias)
        elif key == "calibration":
            out.append(alias)
    return out


def add_pooled_vomiting_aliases(rows: list[dict[str, str]], key: str) -> list[dict[str, str]]:
    out = list(rows)
    for row in rows:
        if row.get("dataset") != POOLED_DATASET:
            continue
        if row.get("model_id") != POOLED_VOMITING_SOURCE_MODEL:
            continue
        alias = dict(row)
        alias["source_model_id"] = POOLED_VOMITING_SOURCE_MODEL
        alias["model_id"] = POOLED_VOMITING_EXPORT_MODEL
        if key == "coefficients" and alias.get("term") in POOLED_VOMITING_TERMS:
            out.append(alias)
        elif key == "calibration":
            out.append(alias)
    return out


def add_pooled_hematemesis_aliases(rows: list[dict[str, str]], key: str) -> list[dict[str, str]]:
    out = list(rows)
    for row in rows:
        if row.get("dataset") != POOLED_DATASET:
            continue
        if row.get("model_id") != POOLED_HEMATEMESIS_SOURCE_MODEL:
            continue
        alias = dict(row)
        alias["source_model_id"] = POOLED_HEMATEMESIS_SOURCE_MODEL
        alias["model_id"] = POOLED_HEMATEMESIS_EXPORT_MODEL
        if key == "coefficients" and alias.get("term") in POOLED_HEMATEMESIS_TERMS:
            out.append(alias)
        elif key == "calibration":
            out.append(alias)
    return out


def dataset_for_source_dir(source_dir: Path) -> str:
    text = str(source_dir).lower()
    if "nhamcs_pooled" in text:
        return POOLED_DATASET
    if "nhamcs" in text:
        return "NHAMCS_2022"
    if "mimic" in text:
        return "MIMIC_IV_ED"
    return source_dir.name


def artifact_status(source_dir: Path) -> dict[str, Any]:
    if dataset_for_source_dir(source_dir) == POOLED_DATASET:
        covariance_path = source_dir / "fever_model_comparison_covariance.csv"
        draws_path = source_dir / "fever_model_comparison_draws.csv"
        vomiting_covariance_path = source_dir / "vomiting_model_comparison_covariance.csv"
        vomiting_draws_path = source_dir / "vomiting_model_comparison_draws.csv"
        hematemesis_covariance_path = source_dir / "hematemesis_model_comparison_covariance.csv"
        hematemesis_draws_path = source_dir / "hematemesis_model_comparison_draws.csv"
        covariance_models = model_ids_in_csv(covariance_path)
        draw_models = model_ids_in_csv(draws_path)
        covariance_models.update(model_ids_in_csv(vomiting_covariance_path))
        draw_models.update(model_ids_in_csv(vomiting_draws_path))
        covariance_models.update(model_ids_in_csv(hematemesis_covariance_path))
        draw_models.update(model_ids_in_csv(hematemesis_draws_path))
        if POOLED_FEVER_SOURCE_MODEL in covariance_models:
            covariance_models.add(POOLED_FEVER_EXPORT_MODEL)
        if POOLED_FEVER_SOURCE_MODEL in draw_models:
            draw_models.add(POOLED_FEVER_EXPORT_MODEL)
        if POOLED_VOMITING_SOURCE_MODEL in covariance_models:
            covariance_models.add(POOLED_VOMITING_EXPORT_MODEL)
        if POOLED_VOMITING_SOURCE_MODEL in draw_models:
            draw_models.add(POOLED_VOMITING_EXPORT_MODEL)
        if POOLED_HEMATEMESIS_SOURCE_MODEL in covariance_models:
            covariance_models.add(POOLED_HEMATEMESIS_EXPORT_MODEL)
        if POOLED_HEMATEMESIS_SOURCE_MODEL in draw_models:
            draw_models.add(POOLED_HEMATEMESIS_EXPORT_MODEL)
        return {
            "cohort": (source_dir / "cohort_flow_by_year.csv").exists(),
            "endpoint": (source_dir / "endpoint_audit_by_year.csv").exists(),
            "mapping": codebook_confirmation_passed(source_dir / "codebook_confirmation_audit.csv"),
            "counts": (source_dir / "fever_sparse_cell_counts_by_year.csv").exists(),
            "vomiting_counts": (source_dir / "vomiting_cell_counts_by_year.csv").exists(),
            "hematemesis_counts": (source_dir / "hematemesis_cell_counts_by_year.csv").exists(),
            "missingness": (source_dir / "missingness_by_year_and_endpoint.csv").exists()
            and (source_dir / "fever_missing_temperature_audit.csv").exists(),
            "coefficients": (source_dir / "fever_model_comparison_coefficients.csv").exists(),
            "calibration": (source_dir / "fever_model_comparison_calibration.csv").exists(),
            "covariance_models": covariance_models,
            "draw_models": draw_models,
            "draw_counts": {
                POOLED_FEVER_SOURCE_MODEL: draw_count_for_model(draws_path, POOLED_FEVER_SOURCE_MODEL),
                POOLED_FEVER_EXPORT_MODEL: draw_count_for_model(draws_path, POOLED_FEVER_SOURCE_MODEL),
                POOLED_VOMITING_SOURCE_MODEL: draw_count_for_model(vomiting_draws_path, POOLED_VOMITING_SOURCE_MODEL),
                POOLED_VOMITING_EXPORT_MODEL: draw_count_for_model(vomiting_draws_path, POOLED_VOMITING_SOURCE_MODEL),
                POOLED_HEMATEMESIS_SOURCE_MODEL: draw_count_for_model(hematemesis_draws_path, POOLED_HEMATEMESIS_SOURCE_MODEL),
                POOLED_HEMATEMESIS_EXPORT_MODEL: draw_count_for_model(hematemesis_draws_path, POOLED_HEMATEMESIS_SOURCE_MODEL),
            },
            "fever_gate_status": fever_gate_status(source_dir / "fever_sparse_cell_gate_decision.csv"),
            "vomiting_gate_status": vomiting_gate_status(source_dir / "vomiting_gate_decision.csv"),
            "hematemesis_gate_status": hematemesis_gate_status(source_dir / "hematemesis_gate_decision.csv"),
            "final_gate_status": final_gate_status(source_dir / "final_reduced_model_gate_decision.csv"),
            "vomiting_mapping": codebook_confirmation_passed(source_dir / "vomiting_codebook_confirmation_audit.csv"),
            "hematemesis_mapping": codebook_confirmation_passed(source_dir / "hematemesis_codebook_confirmation_audit.csv"),
            "missing_temperature_audit": (source_dir / "fever_missing_temperature_audit.csv").exists(),
        }
    source_name = "nhamcs" if "nhamcs" in str(source_dir).lower() else "mimic"
    cohort_path = source_dir / f"cohort_flow_{source_name}.csv"
    endpoint_path = source_dir / f"endpoint_audit_{source_name}.csv"
    coefficient_path = source_dir / "coefficients.csv"
    covariance_path = source_dir / "covariance_matrix.csv"
    draw_paths = [source_dir / "posterior_draws.csv", source_dir / "mvn_coefficient_draws.csv"]
    return {
        "cohort": cohort_path.exists() and cohort_path.stat().st_size > 0,
        "endpoint": endpoint_path.exists() and endpoint_path.stat().st_size > 0,
        "mapping": code_lists_available(source_name),
        "counts": (source_dir / "pain_unadjusted_rates.csv").exists(),
        "missingness": (source_dir / "missingness_by_endpoint.csv").exists(),
        "coefficients": coefficient_path.exists() and coefficient_path.stat().st_size > 0,
        "calibration": (source_dir / "calibration_metrics.csv").exists(),
        "covariance_models": model_ids_in_csv(covariance_path),
        "draw_models": set().union(*(model_ids_in_csv(path) for path in draw_paths if path.exists())),
    }


def codebook_confirmation_passed(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    rows = read_csv(path)
    return bool(rows) and all(str(row.get("passed", "")).lower() == "true" for row in rows)


def fever_gate_status(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return "missing"
    for row in read_csv(path):
        if row.get("gate") == "promotion_suitability":
            return row.get("status", "missing")
    return "missing"


def vomiting_gate_status(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return "missing"
    for row in read_csv(path):
        if row.get("gate") == "promotion_suitability":
            return row.get("status", "missing")
    return "missing"


def hematemesis_gate_status(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return "missing"
    for row in read_csv(path):
        if row.get("gate") == "promotion_suitability":
            return row.get("status", "missing")
    return "missing"


def final_gate_status(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return "missing"
    for row in read_csv(path):
        if row.get("gate") == "activation_suitability":
            return row.get("status", "missing")
    return "missing"


def draw_count_for_model(path: Path, model_id: str) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    draw_ids: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("model_id") == model_id:
                draw_id = row.get("draw_id", "")
                if draw_id:
                    draw_ids.add(draw_id)
    return len(draw_ids)


def code_lists_available(source_name: str) -> bool:
    config_dir = PROJECT_ROOT / "config" / "code_lists"
    common = [
        config_dir / "vomiting_terms.yml",
        config_dir / "fever_terms.yml",
        config_dir / "pain_parsing_rules.yml",
        config_dir / "schema.yml",
    ]
    if source_name == "nhamcs":
        specific = [
            config_dir / "nhamcs_abdominal_pain_rfv.yml",
            config_dir / "nhamcs_vomiting_rfv.yml",
            config_dir / "nhamcs_trauma_exclusions.yml",
            config_dir / "nhamcs_endpoint_flags.yml",
        ]
    else:
        specific = [
            config_dir / "mimic_chief_complaint_abdominal_pain.yml",
            config_dir / "mimic_trauma_exclusions.yml",
        ]
    return all(path.exists() and path.stat().st_size > 0 for path in common + specific)


def model_ids_in_csv(path: Path) -> set[str]:
    if not path.exists() or path.stat().st_size == 0:
        return set()
    ids: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "model_id" not in reader.fieldnames:
            return set()
        for row in reader:
            model_id = str(row.get("model_id", "")).strip()
            if model_id:
                ids.add(model_id)
    return ids


def build_decisions(bundle: dict[str, Any]) -> dict[str, Any]:
    calibration_summary = calibration.summarize_calibration(bundle["calibration"])
    pain_summary = bundle["pain_summary"] or [pain_monotonicity.decide_pain(
        bundle["pain_rates"],
        bundle["coefficients"],
        bundle["calibration"],
        bundle["missingness"],
    )]
    evidence_assignments = assign_evidence_tiers(bundle, pain_summary[0], calibration_summary)
    fever_promotion = fever_promotion_decision(bundle, evidence_assignments)
    vomiting_promotion = vomiting_promotion_decision(bundle, evidence_assignments)
    hematemesis_promotion = hematemesis_promotion_decision(bundle, evidence_assignments)
    final_activation = final_activation_decision(bundle, evidence_assignments)
    vomiting_activation = vomiting_expanded_activation_decision(bundle, evidence_assignments)
    hematemesis_activation = hematemesis_expanded_activation_decision(bundle, evidence_assignments)
    go_no_go = go_no_go_summary(bundle, pain_summary[0], calibration_summary, evidence_assignments)
    return {
        "calibration_summary": calibration_summary,
        "pain_summary": pain_summary,
        "evidence_assignments": evidence_assignments,
        "fever_promotion": fever_promotion,
        "vomiting_promotion": vomiting_promotion,
        "hematemesis_promotion": hematemesis_promotion,
        "final_activation": final_activation,
        "vomiting_activation": vomiting_activation,
        "hematemesis_activation": hematemesis_activation,
        "go_no_go": go_no_go,
    }


def assign_evidence_tiers(
    bundle: dict[str, Any],
    pain: dict[str, Any],
    calibration_summary: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    calibration_failures = {
        (row.get("dataset", ""), row.get("model_id", ""))
        for row in calibration_summary
        if row["calibration_status"] == "fail"
    }
    calibration_models = {
        (row.get("dataset", ""), row.get("model_id", ""))
        for row in calibration_summary
        if row.get("calibration_status") in {"pass", "fail"}
    }

    for coefficient in bundle["coefficients"]:
        term = str(coefficient.get("term", ""))
        dataset = str(coefficient.get("dataset", ""))
        model_id = str(coefficient.get("model_id", ""))
        if dataset == POOLED_DATASET and model_id == POOLED_FEVER_EXPORT_MODEL:
            rows.append(assign_pooled_fever_tier(coefficient, calibration_models, calibration_failures, bundle))
            continue
        if dataset == POOLED_DATASET and model_id == POOLED_VOMITING_EXPORT_MODEL:
            rows.append(assign_pooled_vomiting_tier(coefficient, calibration_models, calibration_failures, bundle))
            continue
        if dataset == POOLED_DATASET and model_id == POOLED_HEMATEMESIS_EXPORT_MODEL:
            rows.append(assign_pooled_hematemesis_tier(coefficient, calibration_models, calibration_failures, bundle))
            continue

        existing = str(coefficient.get("evidence_tier", ""))
        artifacts = bundle.get("artifacts", {}).get(dataset, {})
        blockers: list[str] = []
        if not artifacts.get("cohort"):
            blockers.append("missing_cohort")
        if not artifacts.get("endpoint"):
            blockers.append("missing_endpoint")
        if not artifacts.get("mapping"):
            blockers.append("missing_mapping")
        if not artifacts.get("counts"):
            blockers.append("missing_counts")
        if not coefficient_has_uncertainty(coefficient, artifacts):
            blockers.append("missing_uncertainty")
        if not artifacts.get("missingness"):
            blockers.append("missing_missingness")
        if (dataset, model_id) not in calibration_models:
            blockers.append("missing_calibration")
        if (dataset, model_id) in calibration_failures:
            blockers.append("calibration_failure")
        if existing != "dataset_derived":
            blockers.append(f"source_evidence_not_dataset_derived_{existing or 'blank'}")
        if existing in {"exploratory", "mimic_replication_only", "survey_weighted_candidate", "dataset_derived_candidate"}:
            blockers.append(f"source_output_{existing}")
        if dataset == "MIMIC_IV_ED":
            blockers.append("mimic_replication_not_national_derivation")
        if term in {"pain_bin3", "pain_score", "pain_missing"} and pain["verdict"] != "monotonic_dataset_derived":
            blockers.append(f"pain_verdict_{pain['verdict']}")

        if blockers:
            if existing == "unsupported":
                tier = "unsupported"
            elif existing == "prototype_assumption":
                tier = "prototype_assumption"
            else:
                tier = "unsupported" if term in {"vomiting", "broadPainRegion", "onsetDurationCategory", "constantVsIntermittent"} else "prototype_assumption"
        else:
            tier = "dataset_derived"

        rows.append(
            {
                "dataset": dataset,
                "model_id": model_id,
                "term": term,
                "level": str(coefficient.get("level", "")),
                "assigned_evidence_tier": tier,
                "input_evidence_tier": existing,
                "blockers": "; ".join(sorted(set(blockers))),
            }
        )

    if not rows:
        rows.append(
            {
                "dataset": "",
                "model_id": "",
                "term": "",
                "level": "",
                "assigned_evidence_tier": "unsupported",
                "input_evidence_tier": "",
                "blockers": "no_coefficients_available",
            }
        )
    return rows


def assign_pooled_fever_tier(
    coefficient: dict[str, Any],
    calibration_models: set[tuple[str, str]],
    calibration_failures: set[tuple[str, str]],
    bundle: dict[str, Any],
) -> dict[str, str]:
    term = str(coefficient.get("term", ""))
    dataset = str(coefficient.get("dataset", ""))
    model_id = str(coefficient.get("model_id", ""))
    existing = str(coefficient.get("evidence_tier", ""))
    artifacts = bundle.get("artifacts", {}).get(dataset, {})
    final_decision = final_term_decision(bundle, term, str(coefficient.get("level", "")))
    if final_decision:
        return assign_pooled_final_reduced_tier(coefficient, final_decision, artifacts)

    blockers: list[str] = []

    if not artifacts.get("cohort"):
        blockers.append("missing_cohort")
    if not artifacts.get("endpoint"):
        blockers.append("missing_endpoint")
    if not artifacts.get("mapping"):
        blockers.append("mapping_not_confirmed")
    if not artifacts.get("counts"):
        blockers.append("missing_fever_cell_counts")
    if not artifacts.get("missingness"):
        blockers.append("missing_missingness_or_temperature_audit")
    if not coefficient_has_uncertainty(coefficient, artifacts):
        blockers.append("missing_uncertainty")
    if (dataset, model_id) not in calibration_models:
        blockers.append("missing_calibration")
    if (dataset, model_id) in calibration_failures:
        blockers.append("calibration_failure")
    if not artifacts.get("missing_temperature_audit"):
        blockers.append("missing_temperature_audit")

    beta = to_float_or_none(coefficient.get("beta"))
    if beta is None:
        blockers.append("missing_or_nonfinite_beta")

    if term == "fever_or_temp":
        if artifacts.get("fever_gate_status") != "eligible_for_evidence_promotion":
            blockers.append(f"fever_gate_{artifacts.get('fever_gate_status', 'missing')}")
        if beta is not None and beta <= 0:
            blockers.append("fever_beta_not_positive")
        if artifacts.get("draw_counts", {}).get(model_id, 0) < 10000:
            blockers.append("missing_10000_mvn_draws")

        if not artifacts.get("mapping") and not blockers_without_mapping(blockers):
            tier = "dataset_derived_candidate"
        elif blockers:
            tier = "survey_weighted_candidate"
        else:
            tier = "dataset_derived"
    else:
        if term in {"pain_bin3", "pain_missing"}:
            blockers.append("pain_flexible_nonmonotonic_requires_separate_promotion_review")
        else:
            blockers.append("term_specific_promotion_not_reviewed_in_fever_gate")
        tier = "survey_weighted_candidate"

    return {
        "dataset": dataset,
        "model_id": model_id,
        "source_model_id": str(coefficient.get("source_model_id", POOLED_FEVER_SOURCE_MODEL)),
        "term": term,
        "level": str(coefficient.get("level", "")),
        "assigned_evidence_tier": tier,
        "input_evidence_tier": existing,
        "blockers": "; ".join(sorted(set(blockers))),
    }


def final_term_decision(bundle: dict[str, Any], term: str, level: str) -> dict[str, str] | None:
    normalized_level = "" if level in {"None", "nan"} else level
    for row in bundle.get("final_term_decisions", []):
        if row.get("dataset") != POOLED_DATASET or row.get("model_id") != POOLED_FEVER_EXPORT_MODEL:
            continue
        row_level = row.get("level", "")
        if row.get("term") == term and row_level == normalized_level:
            return row
    return None


def assign_pooled_final_reduced_tier(
    coefficient: dict[str, Any],
    final_decision: dict[str, str],
    artifacts: dict[str, Any],
) -> dict[str, str]:
    term = str(coefficient.get("term", ""))
    level = str(coefficient.get("level", ""))
    existing = str(coefficient.get("evidence_tier", ""))
    blockers = split_blockers(final_decision.get("blockers", ""))
    if not artifacts.get("cohort"):
        blockers.append("missing_cohort")
    if not artifacts.get("endpoint"):
        blockers.append("missing_endpoint")
    if not artifacts.get("mapping"):
        blockers.append("mapping_not_confirmed")
    if not artifacts.get("missingness"):
        blockers.append("missing_missingness_or_temperature_audit")
    if not artifacts.get("counts"):
        blockers.append("missing_cell_counts")
    if artifacts.get("final_gate_status") != "eligible_for_educational_activation":
        blockers.append(f"final_gate_{artifacts.get('final_gate_status', 'missing')}")
    if not coefficient_has_uncertainty(coefficient, artifacts):
        blockers.append("missing_uncertainty")

    final_tier = final_decision.get("assigned_evidence_tier", "")
    if final_tier == "dataset_derived" and not blockers:
        tier = "dataset_derived"
    elif final_tier == "dataset_derived" and blockers == ["mapping_not_confirmed"]:
        tier = "dataset_derived_candidate"
    else:
        tier = "survey_weighted_candidate"
    return {
        "dataset": POOLED_DATASET,
        "model_id": POOLED_FEVER_EXPORT_MODEL,
        "source_model_id": str(coefficient.get("source_model_id", POOLED_FEVER_SOURCE_MODEL)),
        "term": term,
        "level": level,
        "assigned_evidence_tier": tier,
        "input_evidence_tier": existing,
        "blockers": "; ".join(sorted(set(blockers))),
    }


def assign_pooled_vomiting_tier(
    coefficient: dict[str, Any],
    calibration_models: set[tuple[str, str]],
    calibration_failures: set[tuple[str, str]],
    bundle: dict[str, Any],
) -> dict[str, str]:
    term = str(coefficient.get("term", ""))
    level = str(coefficient.get("level", ""))
    existing = str(coefficient.get("evidence_tier", ""))
    artifacts = bundle.get("artifacts", {}).get(POOLED_DATASET, {})
    blockers: list[str] = []

    if not artifacts.get("cohort"):
        blockers.append("missing_cohort")
    if not artifacts.get("endpoint"):
        blockers.append("missing_endpoint")
    if not artifacts.get("mapping"):
        blockers.append("mapping_not_confirmed")
    if not artifacts.get("vomiting_mapping"):
        blockers.append("vomiting_mapping_not_confirmed")
    if not artifacts.get("vomiting_counts"):
        blockers.append("missing_vomiting_cell_counts")
    if not artifacts.get("missingness"):
        blockers.append("missing_missingness_or_temperature_audit")
    if artifacts.get("vomiting_gate_status") != "eligible_for_evidence_promotion":
        blockers.append(f"vomiting_gate_{artifacts.get('vomiting_gate_status', 'missing')}")
    if (POOLED_DATASET, POOLED_VOMITING_EXPORT_MODEL) not in calibration_models:
        blockers.append("missing_calibration")
    if (POOLED_DATASET, POOLED_VOMITING_EXPORT_MODEL) in calibration_failures:
        blockers.append("calibration_failure")
    if not coefficient_has_uncertainty(coefficient, artifacts):
        blockers.append("missing_uncertainty")
    if artifacts.get("draw_counts", {}).get(POOLED_VOMITING_EXPORT_MODEL, 0) < 10000:
        blockers.append("missing_10000_mvn_draws")

    beta = to_float_or_none(coefficient.get("beta"))
    if beta is None:
        blockers.append("missing_or_nonfinite_beta")

    if term == "vomiting_present":
        if beta is not None and beta <= 0:
            blockers.append("vomiting_beta_not_positive")
    elif term in {"intercept", "age_centered", "pain_bin3", "pain_missing", "fever_or_temp"}:
        inherited = final_term_decision(bundle, term, level)
        if not inherited or inherited.get("assigned_evidence_tier") != "dataset_derived":
            blockers.append("base_reduced_term_not_dataset_derived")
    else:
        blockers.append("term_not_in_vomiting_expanded_model")

    if blockers:
        tier = "survey_weighted_candidate"
    else:
        tier = "dataset_derived"
    return {
        "dataset": POOLED_DATASET,
        "model_id": POOLED_VOMITING_EXPORT_MODEL,
        "source_model_id": str(coefficient.get("source_model_id", POOLED_VOMITING_SOURCE_MODEL)),
        "term": term,
        "level": level,
        "assigned_evidence_tier": tier,
        "input_evidence_tier": existing,
        "blockers": "; ".join(sorted(set(blockers))),
    }


def assign_pooled_hematemesis_tier(
    coefficient: dict[str, Any],
    calibration_models: set[tuple[str, str]],
    calibration_failures: set[tuple[str, str]],
    bundle: dict[str, Any],
) -> dict[str, str]:
    term = str(coefficient.get("term", ""))
    level = str(coefficient.get("level", ""))
    existing = str(coefficient.get("evidence_tier", ""))
    artifacts = bundle.get("artifacts", {}).get(POOLED_DATASET, {})
    blockers: list[str] = []

    if not artifacts.get("cohort"):
        blockers.append("missing_cohort")
    if not artifacts.get("endpoint"):
        blockers.append("missing_endpoint")
    if not artifacts.get("mapping"):
        blockers.append("mapping_not_confirmed")
    if not artifacts.get("hematemesis_mapping"):
        blockers.append("hematemesis_mapping_not_confirmed")
    if not artifacts.get("hematemesis_counts"):
        blockers.append("missing_hematemesis_cell_counts")
    if not artifacts.get("missingness"):
        blockers.append("missing_missingness_or_temperature_audit")
    if artifacts.get("hematemesis_gate_status") != "eligible_for_evidence_promotion":
        blockers.append(f"hematemesis_gate_{artifacts.get('hematemesis_gate_status', 'missing')}")
    if (POOLED_DATASET, POOLED_HEMATEMESIS_EXPORT_MODEL) not in calibration_models:
        blockers.append("missing_calibration")
    if (POOLED_DATASET, POOLED_HEMATEMESIS_EXPORT_MODEL) in calibration_failures:
        blockers.append("calibration_failure")
    if not coefficient_has_uncertainty(coefficient, artifacts):
        blockers.append("missing_uncertainty")
    if artifacts.get("draw_counts", {}).get(POOLED_HEMATEMESIS_EXPORT_MODEL, 0) < 10000:
        blockers.append("missing_10000_mvn_draws")

    beta = to_float_or_none(coefficient.get("beta"))
    if beta is None:
        blockers.append("missing_or_nonfinite_beta")

    if term == "hematemesis_present":
        if beta is not None and beta <= 0:
            blockers.append("hematemesis_beta_not_positive")
    elif term == "vomiting_present":
        if artifacts.get("vomiting_gate_status") != "eligible_for_evidence_promotion":
            blockers.append(f"vomiting_gate_{artifacts.get('vomiting_gate_status', 'missing')}")
        if not artifacts.get("vomiting_mapping"):
            blockers.append("vomiting_mapping_not_confirmed")
        if not artifacts.get("vomiting_counts"):
            blockers.append("missing_vomiting_cell_counts")
        if artifacts.get("draw_counts", {}).get(POOLED_VOMITING_EXPORT_MODEL, 0) < 10000:
            blockers.append("missing_vomiting_10000_mvn_draws")
    elif term in {"intercept", "age_centered", "pain_bin3", "pain_missing", "fever_or_temp"}:
        inherited = final_term_decision(bundle, term, level)
        if not inherited or inherited.get("assigned_evidence_tier") != "dataset_derived":
            blockers.append("base_reduced_term_not_dataset_derived")
    else:
        blockers.append("term_not_in_hematemesis_expanded_model")

    if blockers:
        tier = "survey_weighted_candidate"
    else:
        tier = "dataset_derived"
    return {
        "dataset": POOLED_DATASET,
        "model_id": POOLED_HEMATEMESIS_EXPORT_MODEL,
        "source_model_id": str(coefficient.get("source_model_id", POOLED_HEMATEMESIS_SOURCE_MODEL)),
        "term": term,
        "level": level,
        "assigned_evidence_tier": tier,
        "input_evidence_tier": existing,
        "blockers": "; ".join(sorted(set(blockers))),
    }


def split_blockers(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def blockers_without_mapping(blockers: list[str]) -> list[str]:
    return [blocker for blocker in blockers if blocker != "mapping_not_confirmed"]


def coefficient_has_uncertainty(coefficient: dict[str, Any], artifacts: dict[str, Any]) -> bool:
    model_id = str(coefficient.get("model_id", ""))
    source_model_id = str(coefficient.get("source_model_id", ""))
    if math_is_finite(coefficient.get("se")):
        return True
    if model_id and model_id in artifacts.get("covariance_models", set()):
        return True
    if model_id and model_id in artifacts.get("draw_models", set()):
        return True
    if source_model_id and source_model_id in artifacts.get("covariance_models", set()):
        return True
    if source_model_id and source_model_id in artifacts.get("draw_models", set()):
        return True
    return False


def math_is_finite(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number == number and number not in {float("inf"), float("-inf")}


def to_float_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in {float("inf"), float("-inf")}:
        return None
    return number


def fever_promotion_decision(bundle: dict[str, Any], evidence_assignments: list[dict[str, str]]) -> list[dict[str, str]]:
    fever_rows = [
        row for row in evidence_assignments
        if row.get("dataset") == POOLED_DATASET
        and row.get("model_id") == POOLED_FEVER_EXPORT_MODEL
        and row.get("term") == "fever_or_temp"
    ]
    artifacts = bundle.get("artifacts", {}).get(POOLED_DATASET, {})
    assigned = fever_rows[0]["assigned_evidence_tier"] if fever_rows else "unsupported"
    blockers = fever_rows[0]["blockers"] if fever_rows else "no_fever_evidence_assignment"
    return [
        {
            "dataset": POOLED_DATASET,
            "model_id": POOLED_FEVER_EXPORT_MODEL,
            "source_model_id": POOLED_FEVER_SOURCE_MODEL,
            "term": "fever_or_temp",
            "fever_gate_status": str(artifacts.get("fever_gate_status", "missing")),
            "mapping_confirmed": str(bool(artifacts.get("mapping"))).lower(),
            "missing_temperature_audit_present": str(bool(artifacts.get("missing_temperature_audit"))).lower(),
            "draw_count": str(artifacts.get("draw_counts", {}).get(POOLED_FEVER_EXPORT_MODEL, 0)),
            "assigned_evidence_tier": assigned,
            "blockers": blockers,
        }
    ]


def vomiting_promotion_decision(bundle: dict[str, Any], evidence_assignments: list[dict[str, str]]) -> list[dict[str, str]]:
    vomiting_rows = [
        row for row in evidence_assignments
        if row.get("dataset") == POOLED_DATASET
        and row.get("model_id") == POOLED_VOMITING_EXPORT_MODEL
        and row.get("term") == "vomiting_present"
    ]
    artifacts = bundle.get("artifacts", {}).get(POOLED_DATASET, {})
    assigned = vomiting_rows[0]["assigned_evidence_tier"] if vomiting_rows else "unsupported"
    blockers = vomiting_rows[0]["blockers"] if vomiting_rows else "no_vomiting_evidence_assignment"
    return [
        {
            "dataset": POOLED_DATASET,
            "model_id": POOLED_VOMITING_EXPORT_MODEL,
            "source_model_id": POOLED_VOMITING_SOURCE_MODEL,
            "term": "vomiting_present",
            "vomiting_gate_status": str(artifacts.get("vomiting_gate_status", "missing")),
            "mapping_confirmed": str(bool(artifacts.get("vomiting_mapping"))).lower(),
            "draw_count": str(artifacts.get("draw_counts", {}).get(POOLED_VOMITING_EXPORT_MODEL, 0)),
            "assigned_evidence_tier": assigned,
            "blockers": blockers,
        }
    ]


def hematemesis_promotion_decision(bundle: dict[str, Any], evidence_assignments: list[dict[str, str]]) -> list[dict[str, str]]:
    hematemesis_rows = [
        row for row in evidence_assignments
        if row.get("dataset") == POOLED_DATASET
        and row.get("model_id") == POOLED_HEMATEMESIS_EXPORT_MODEL
        and row.get("term") == "hematemesis_present"
    ]
    artifacts = bundle.get("artifacts", {}).get(POOLED_DATASET, {})
    assigned = hematemesis_rows[0]["assigned_evidence_tier"] if hematemesis_rows else "unsupported"
    blockers = hematemesis_rows[0]["blockers"] if hematemesis_rows else "no_hematemesis_evidence_assignment"
    return [
        {
            "dataset": POOLED_DATASET,
            "model_id": POOLED_HEMATEMESIS_EXPORT_MODEL,
            "source_model_id": POOLED_HEMATEMESIS_SOURCE_MODEL,
            "term": "hematemesis_present",
            "hematemesis_gate_status": str(artifacts.get("hematemesis_gate_status", "missing")),
            "mapping_confirmed": str(bool(artifacts.get("hematemesis_mapping"))).lower(),
            "draw_count": str(artifacts.get("draw_counts", {}).get(POOLED_HEMATEMESIS_EXPORT_MODEL, 0)),
            "assigned_evidence_tier": assigned,
            "blockers": blockers,
        }
    ]


def final_activation_decision(bundle: dict[str, Any], evidence_assignments: list[dict[str, str]]) -> list[dict[str, str]]:
    target_rows = target_evidence_rows(evidence_assignments)
    artifacts = bundle.get("artifacts", {}).get(POOLED_DATASET, {})
    activated = bool(target_rows) and all(row.get("assigned_evidence_tier") == "dataset_derived" for row in target_rows)
    blockers = []
    if not target_rows:
        blockers.append("missing_target_model_evidence_assignments")
    blockers.extend(row.get("blockers", "") for row in target_rows if row.get("blockers"))
    if artifacts.get("final_gate_status") != "eligible_for_educational_activation":
        blockers.append(f"final_gate_{artifacts.get('final_gate_status', 'missing')}")
    return [
        {
            "dataset": POOLED_DATASET,
            "model_id": POOLED_FEVER_EXPORT_MODEL,
            "activation_status": "eligible_for_educational_activation" if activated else "blocked",
            "term_count": str(len(target_rows)),
            "dataset_derived_term_count": str(sum(row.get("assigned_evidence_tier") == "dataset_derived" for row in target_rows)),
            "blockers": "; ".join(sorted(set(split_blockers("; ".join(blockers))))),
        }
    ]


def vomiting_expanded_activation_decision(bundle: dict[str, Any], evidence_assignments: list[dict[str, str]]) -> list[dict[str, str]]:
    target_rows = vomiting_target_evidence_rows(evidence_assignments)
    artifacts = bundle.get("artifacts", {}).get(POOLED_DATASET, {})
    activated = bool(target_rows) and all(row.get("assigned_evidence_tier") == "dataset_derived" for row in target_rows)
    blockers = []
    if not target_rows:
        blockers.append("missing_vomiting_expanded_evidence_assignments")
    blockers.extend(row.get("blockers", "") for row in target_rows if row.get("blockers"))
    if artifacts.get("vomiting_gate_status") != "eligible_for_evidence_promotion":
        blockers.append(f"vomiting_gate_{artifacts.get('vomiting_gate_status', 'missing')}")
    return [
        {
            "dataset": POOLED_DATASET,
            "model_id": POOLED_VOMITING_EXPORT_MODEL,
            "activation_status": "eligible_for_educational_activation" if activated else "blocked",
            "term_count": str(len(target_rows)),
            "dataset_derived_term_count": str(sum(row.get("assigned_evidence_tier") == "dataset_derived" for row in target_rows)),
            "blockers": "; ".join(sorted(set(split_blockers("; ".join(blockers))))),
        }
    ]


def hematemesis_expanded_activation_decision(bundle: dict[str, Any], evidence_assignments: list[dict[str, str]]) -> list[dict[str, str]]:
    target_rows = hematemesis_target_evidence_rows(evidence_assignments)
    artifacts = bundle.get("artifacts", {}).get(POOLED_DATASET, {})
    activated = bool(target_rows) and all(row.get("assigned_evidence_tier") == "dataset_derived" for row in target_rows)
    blockers = []
    if not target_rows:
        blockers.append("missing_hematemesis_expanded_evidence_assignments")
    blockers.extend(row.get("blockers", "") for row in target_rows if row.get("blockers"))
    if artifacts.get("hematemesis_gate_status") != "eligible_for_evidence_promotion":
        blockers.append(f"hematemesis_gate_{artifacts.get('hematemesis_gate_status', 'missing')}")
    return [
        {
            "dataset": POOLED_DATASET,
            "model_id": POOLED_HEMATEMESIS_EXPORT_MODEL,
            "activation_status": "eligible_for_educational_activation" if activated else "blocked",
            "term_count": str(len(target_rows)),
            "dataset_derived_term_count": str(sum(row.get("assigned_evidence_tier") == "dataset_derived" for row in target_rows)),
            "blockers": "; ".join(sorted(set(split_blockers("; ".join(blockers))))),
        }
    ]


def target_evidence_rows(evidence_assignments: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row for row in evidence_assignments
        if row.get("dataset") == POOLED_DATASET and row.get("model_id") == POOLED_FEVER_EXPORT_MODEL
    ]


def vomiting_target_evidence_rows(evidence_assignments: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row for row in evidence_assignments
        if row.get("dataset") == POOLED_DATASET and row.get("model_id") == POOLED_VOMITING_EXPORT_MODEL
    ]


def hematemesis_target_evidence_rows(evidence_assignments: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row for row in evidence_assignments
        if row.get("dataset") == POOLED_DATASET and row.get("model_id") == POOLED_HEMATEMESIS_EXPORT_MODEL
    ]


def go_no_go_summary(
    bundle: dict[str, Any],
    pain: dict[str, Any],
    calibration_summary: list[dict[str, str]],
    evidence_assignments: list[dict[str, str]],
) -> str:
    blockers: list[str] = []
    if bundle["missing_files"]:
        blockers.append("Missing files: " + "; ".join(bundle["missing_files"]))
    target_calibration_failures = [
        row for row in calibration_summary
        if row["calibration_status"] == "fail" and row.get("dataset") != "MIMIC_IV_ED"
    ]
    if target_calibration_failures:
        blockers.append("One or more derivation-source calibration rows fail pass/fail criteria.")
    if pain["verdict"] not in {"monotonic_dataset_derived", "nonmonotonic_flexible_only"}:
        blockers.append(f"Pain cannot be promoted: {pain['verdict']} ({pain.get('blockers', '')}).")
    target_rows = target_evidence_rows(evidence_assignments)
    target_activation = bool(target_rows) and all(row["assigned_evidence_tier"] == "dataset_derived" for row in target_rows)
    if not target_activation:
        blockers.append("At least one final reduced-model coefficient remains below dataset_derived.")
    vomiting_rows = vomiting_target_evidence_rows(evidence_assignments)
    vomiting_activation = bool(vomiting_rows) and all(row["assigned_evidence_tier"] == "dataset_derived" for row in vomiting_rows)
    hematemesis_rows = hematemesis_target_evidence_rows(evidence_assignments)
    hematemesis_activation = bool(hematemesis_rows) and all(row["assigned_evidence_tier"] == "dataset_derived" for row in hematemesis_rows)

    reduced_can_activate = "no"
    vomiting_reduced_can_activate = "yes_after_review" if vomiting_activation else "no"
    hematemesis_reduced_can_activate = "yes_after_review" if hematemesis_activation else "no"
    candidate_v4_can_adopt = "no"
    pain_can_promote = flexible_pain_promotion_status(pain, evidence_assignments)
    fever_can_promote = "yes" if any(
        row.get("dataset") == POOLED_DATASET
        and row.get("model_id") == POOLED_FEVER_EXPORT_MODEL
        and row.get("term") == "fever_or_temp"
        and row.get("assigned_evidence_tier") == "dataset_derived"
        for row in evidence_assignments
    ) else "no"
    vomiting_can_promote = "yes" if any(
        row.get("dataset") == POOLED_DATASET
        and row.get("model_id") == POOLED_VOMITING_EXPORT_MODEL
        and row.get("term") == "vomiting_present"
        and row.get("assigned_evidence_tier") == "dataset_derived"
        for row in evidence_assignments
    ) else "no"
    hematemesis_can_promote = "yes" if any(
        row.get("dataset") == POOLED_DATASET
        and row.get("model_id") == POOLED_HEMATEMESIS_EXPORT_MODEL
        and row.get("term") == "hematemesis_present"
        and row.get("assigned_evidence_tier") == "dataset_derived"
        for row in evidence_assignments
    ) else "no"
    if not blockers:
        reduced_can_activate = "yes_after_review"

    lines = [
        "# Combined Go/No-Go Summary",
        "",
        f"- Reduced empirical model can be activated: {reduced_can_activate}",
        f"- Expanded reduced model with vomiting can be activated: {vomiting_reduced_can_activate}",
        f"- Expanded reduced model with hematemesis can be activated: {hematemesis_reduced_can_activate}",
        f"- Candidate v4 can be adopted: {candidate_v4_can_adopt}",
        f"- Pain can be promoted: {pain_can_promote}",
        f"- Objective fever can be promoted: {fever_can_promote}",
        f"- Ordinary vomiting can be promoted: {vomiting_can_promote}",
        f"- Hematemesis can be promoted: {hematemesis_can_promote}",
        f"- Any final reduced-model coefficients remain prototype/unsupported: {'yes' if any(row['assigned_evidence_tier'] != 'dataset_derived' for row in target_rows) else 'no'}",
        "",
        "## Exact Blockers",
    ]
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- None from automated decision engine; human review still required.")
    lines.extend(
        [
            "",
            "## Notes",
            "- This legacy decision file does not control the active `e-dispo-v4.0` app export; the active app model is defined in `src/data/eDispoV4Model.ts`.",
            "- Objective fever promotion is term-specific and does not activate unsupported prototype inputs.",
            "- Ordinary vomiting promotion uses RFV 15300 only; hematemesis RFV 15802 is reviewed only by its separate sparse-cell gate.",
            "- Hematemesis RFV position is documentation prominence, not symptom severity.",
            "- Pain remains flexible/nonmonotonic; this decision does not claim a monotonic pain dose response.",
            "- MIMIC-only evidence is replication/proxy-validation and cannot promote national dataset-derived status alone.",
        ]
    )
    return "\n".join(lines) + "\n"


def flexible_pain_promotion_status(pain: dict[str, Any], evidence_assignments: list[dict[str, str]]) -> str:
    if pain["verdict"] == "monotonic_dataset_derived":
        return "yes_monotonic"
    if pain["verdict"] != "nonmonotonic_flexible_only":
        return "no"

    required = {
        ("pain_bin3", "mild"),
        ("pain_bin3", "severe"),
        ("pain_missing", "1"),
    }
    promoted = {
        (row.get("term", ""), row.get("level", ""))
        for row in target_evidence_rows(evidence_assignments)
        if row.get("assigned_evidence_tier") == "dataset_derived"
    }
    if required.issubset(promoted):
        return "flexible_nonmonotonic_dataset_derived"
    return "flexible_only_pending_separate_review"


def write_outputs(decisions: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "pain_monotonicity_summary.csv", decisions["pain_summary"])
    write_csv(output_dir / "evidence_tier_assignments.csv", decisions["evidence_assignments"])
    write_csv(output_dir / "fever_promotion_decision.csv", decisions["fever_promotion"])
    write_csv(output_dir / "vomiting_promotion_decision.csv", decisions["vomiting_promotion"])
    write_csv(output_dir / "hematemesis_promotion_decision.csv", decisions["hematemesis_promotion"])
    write_csv(output_dir / "final_model_activation_decision.csv", decisions["final_activation"])
    write_csv(output_dir / "vomiting_expanded_model_activation_decision.csv", decisions["vomiting_activation"])
    write_csv(output_dir / "hematemesis_expanded_model_activation_decision.csv", decisions["hematemesis_activation"])
    write_csv(output_dir / "calibration_decision_summary.csv", decisions["calibration_summary"])
    (output_dir / "go_no_go_summary.md").write_text(decisions["go_no_go"], encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
