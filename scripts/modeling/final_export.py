#!/usr/bin/env python3
"""Build final app export and empirical reporting artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NHAMCS_DIR = PROJECT_ROOT / "outputs" / "nhamcs"
DEFAULT_MIMIC_DIR = PROJECT_ROOT / "outputs" / "mimic"
DEFAULT_COMBINED_DIR = PROJECT_ROOT / "outputs" / "combined"
POOLED_DATASET = "NHAMCS_2018_2022_POOLED"
POOLED_FEVER_SOURCE_MODEL = "fever_candidate_complete_temp"
POOLED_FEVER_EXPORT_MODEL = "pooled_empirical_v1_age_pain_fever"
POOLED_VOMITING_SOURCE_MODEL = "vomiting_candidate_binary_complete_temp"
POOLED_VOMITING_EXPORT_MODEL = "pooled_empirical_v1_age_pain_fever_vomiting"
POOLED_TACHYCARDIA_EXPORT_MODEL = "pooled_empirical_v2_age_pain_fever_vomiting_tachycardia"
POOLED_HEMATEMESIS_SOURCE_MODEL = "hematemesis_candidate_binary_complete_temp"
POOLED_HEMATEMESIS_EXPORT_MODEL = "pooled_empirical_v1_age_pain_fever_vomiting_hematemesis"
ALLOWED_EXPORT_STATUSES = {
    "prototype_v3",
    "reduced_empirical_blocked",
    "reduced_empirical_candidate",
    "v4_candidate_not_adopted",
    "v4_adopted",
}
APP_EXPORT_REQUIRED_KEYS = {
    "model_version",
    "model_id",
    "status",
    "model_activation_status",
    "coefficient_source",
    "fever_promotion_gate_status",
    "population",
    "endpoint",
    "dataset_sources",
    "cohort_counts",
    "predictors",
    "predictor_evidence_tiers",
    "covariance_matrix_path",
    "posterior_draws_path",
    "calibration",
    "pain_monotonicity_verdict",
    "allowed_use",
    "generated_at",
    "run_id",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write final empirical model export and reports.")
    parser.add_argument("--nhamcs-dir", default=DEFAULT_NHAMCS_DIR, type=Path)
    parser.add_argument("--mimic-dir", default=DEFAULT_MIMIC_DIR, type=Path)
    parser.add_argument("--combined-dir", default=DEFAULT_COMBINED_DIR, type=Path)
    parser.add_argument("--output-dir", default=DEFAULT_COMBINED_DIR, type=Path)
    args = parser.parse_args(argv)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    run_id = "final_export_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    bundle = load_bundle(args.nhamcs_dir, args.mimic_dir, args.combined_dir)
    artifacts = build_artifacts(bundle, args.output_dir, generated_at, run_id)
    write_artifacts(artifacts, args.output_dir)
    print(f"Wrote final export and reports under {args.output_dir}")
    return 0


def load_bundle(nhamcs_dir: Path, mimic_dir: Path, combined_dir: Path) -> dict[str, Any]:
    return {
        "paths": {
            "nhamcs": nhamcs_dir,
            "mimic": mimic_dir,
            "combined": combined_dir,
        },
        "nhamcs": load_source_outputs(nhamcs_dir, "nhamcs"),
        "mimic": load_source_outputs(mimic_dir, "mimic"),
        "combined": {
            "pain": read_csv(combined_dir / "pain_monotonicity_summary.csv"),
            "evidence": read_csv(combined_dir / "evidence_tier_assignments.csv"),
            "fever": read_csv(combined_dir / "fever_promotion_decision.csv"),
            "vomiting": read_csv(combined_dir / "vomiting_promotion_decision.csv"),
            "hematemesis": read_csv(combined_dir / "hematemesis_promotion_decision.csv"),
            "final_activation": read_csv(combined_dir / "final_model_activation_decision.csv"),
            "vomiting_activation": read_csv(combined_dir / "vomiting_expanded_model_activation_decision.csv"),
            "hematemesis_activation": read_csv(combined_dir / "hematemesis_expanded_model_activation_decision.csv"),
            "calibration_decisions": read_csv(combined_dir / "calibration_decision_summary.csv"),
            "go_no_go": read_text(combined_dir / "go_no_go_summary.md"),
        },
    }


def load_source_outputs(source_dir: Path, source_key: str) -> dict[str, Any]:
    if source_key == "nhamcs" and is_pooled_nhamcs_dir(source_dir):
        metadata_path = source_dir / "model_run_metadata.json"
        coefficients = add_pooled_fever_aliases(read_csv(source_dir / "fever_model_comparison_coefficients.csv"))
        calibration_metrics = add_pooled_fever_aliases(read_csv(source_dir / "fever_model_comparison_calibration.csv"))
        coefficients.extend(add_pooled_vomiting_aliases(read_csv(source_dir / "vomiting_model_comparison_coefficients.csv")))
        calibration_metrics.extend(add_pooled_vomiting_aliases(read_csv(source_dir / "vomiting_model_comparison_calibration.csv")))
        coefficients.extend(read_csv(source_dir / "tachycardia_model_comparison_coefficients.csv"))
        calibration_metrics.extend(read_csv(source_dir / "tachycardia_model_comparison_calibration.csv"))
        coefficients.extend(add_pooled_hematemesis_aliases(read_csv(source_dir / "hematemesis_model_comparison_coefficients.csv")))
        calibration_metrics.extend(add_pooled_hematemesis_aliases(read_csv(source_dir / "hematemesis_model_comparison_calibration.csv")))
        return {
            "dataset": POOLED_DATASET,
            "cohort_flow": read_csv(source_dir / "cohort_flow_by_year.csv"),
            "endpoint_audit": read_csv(source_dir / "endpoint_audit_by_year.csv"),
            "missingness": read_csv(source_dir / "missingness_by_year_and_endpoint.csv"),
            "pain_rates": read_csv(source_dir / "pain_unadjusted_rates_by_year.csv"),
            "coefficients": coefficients,
            "calibration_metrics": calibration_metrics,
            "covariance_path": first_existing([source_dir / "fever_model_comparison_covariance.csv"]),
            "draws_path": first_existing([source_dir / "fever_model_comparison_draws.csv"]),
            "vomiting_covariance_path": first_existing([source_dir / "vomiting_model_comparison_covariance.csv"]),
            "vomiting_draws_path": first_existing([source_dir / "vomiting_model_comparison_draws.csv"]),
            "tachycardia_covariance_path": first_existing([source_dir / "tachycardia_model_comparison_covariance.csv"]),
            "tachycardia_draws_path": first_existing([source_dir / "tachycardia_model_comparison_draws.csv"]),
            "tachycardia_gate": read_csv(source_dir / "tachycardia_burden_gate_decision.csv"),
            "hematemesis_covariance_path": first_existing([source_dir / "hematemesis_model_comparison_covariance.csv"]),
            "hematemesis_draws_path": first_existing([source_dir / "hematemesis_model_comparison_draws.csv"]),
            "calibration_by_decile_path": first_existing([source_dir / "fever_model_comparison_deciles.csv"]),
            "metadata": json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {},
            "pooled_summary": json.loads((source_dir / "pooled_pipeline_summary.json").read_text(encoding="utf-8"))
            if (source_dir / "pooled_pipeline_summary.json").exists()
            else {},
            "transportability_report": read_text(source_dir / "transportability_report.md"),
            "blocker_report": read_text(source_dir / "blocker_report.md"),
        }

    flow_name = f"cohort_flow_{source_key}.csv"
    endpoint_name = f"endpoint_audit_{source_key}.csv"
    metadata_path = source_dir / "model_run_metadata.json"
    return {
        "dataset": "NHAMCS_2022" if source_key == "nhamcs" else "MIMIC_IV_ED",
        "cohort_flow": read_csv(source_dir / flow_name),
        "endpoint_audit": read_csv(source_dir / endpoint_name),
        "missingness": read_csv(source_dir / "missingness_by_endpoint.csv"),
        "pain_rates": read_csv(source_dir / "pain_unadjusted_rates.csv"),
        "coefficients": read_csv(source_dir / "coefficients.csv"),
        "calibration_metrics": read_csv(source_dir / "calibration_metrics.csv"),
        "covariance_path": first_existing([source_dir / "covariance_matrix.csv"]),
        "draws_path": first_existing([source_dir / "posterior_draws.csv", source_dir / "mvn_coefficient_draws.csv"]),
        "calibration_by_decile_path": first_existing([source_dir / "calibration_by_decile.csv"]),
        "metadata": json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {},
        "pooled_summary": {},
        "transportability_report": read_text(source_dir / "transportability_report.md"),
        "blocker_report": read_text(source_dir / "blocker_report.md"),
    }


def is_pooled_nhamcs_dir(source_dir: Path) -> bool:
    return "nhamcs_pooled" in str(source_dir).lower() or (source_dir / "pooled_pipeline_summary.json").exists()


def add_pooled_fever_aliases(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = list(rows)
    for row in rows:
        if row.get("dataset") != POOLED_DATASET or row.get("model_id") != POOLED_FEVER_SOURCE_MODEL:
            continue
        alias = dict(row)
        alias["source_model_id"] = POOLED_FEVER_SOURCE_MODEL
        alias["model_id"] = POOLED_FEVER_EXPORT_MODEL
        out.append(alias)
    return out


def add_pooled_vomiting_aliases(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = list(rows)
    for row in rows:
        if row.get("dataset") != POOLED_DATASET or row.get("model_id") != POOLED_VOMITING_SOURCE_MODEL:
            continue
        alias = dict(row)
        alias["source_model_id"] = POOLED_VOMITING_SOURCE_MODEL
        alias["model_id"] = POOLED_VOMITING_EXPORT_MODEL
        out.append(alias)
    return out


def add_pooled_hematemesis_aliases(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = list(rows)
    for row in rows:
        if row.get("dataset") != POOLED_DATASET or row.get("model_id") != POOLED_HEMATEMESIS_SOURCE_MODEL:
            continue
        alias = dict(row)
        alias["source_model_id"] = POOLED_HEMATEMESIS_SOURCE_MODEL
        alias["model_id"] = POOLED_HEMATEMESIS_EXPORT_MODEL
        out.append(alias)
    return out


def build_artifacts(bundle: dict[str, Any], output_dir: Path, generated_at: str, run_id: str) -> dict[str, Any]:
    app_export = build_app_export(bundle, generated_at, run_id)
    validate_app_export(app_export)
    report = build_empirical_report(bundle, app_export)
    checklist = build_tripods_probast_checklist(bundle, app_export)
    final_decision = build_final_decision(bundle, app_export)
    manifest = build_run_manifest(bundle, app_export, output_dir, generated_at, run_id)
    return {
        "app_export": app_export,
        "empirical_model_report": report,
        "tripods_probast_checklist": checklist,
        "run_manifest": manifest,
        "final_decision": final_decision,
    }


def build_app_export(bundle: dict[str, Any], generated_at: str, run_id: str) -> dict[str, Any]:
    nhamcs = bundle["nhamcs"]
    combined = bundle["combined"]
    selected_model_id = selected_model_id_for_source(nhamcs, combined)
    selected_dataset = nhamcs.get("dataset", "NHAMCS_2022")
    selected_coefficients = [
        row for row in nhamcs["coefficients"]
        if row.get("dataset") == selected_dataset and row.get("model_id") == selected_model_id
    ]
    if not selected_coefficients:
        selected_coefficients = [row for row in nhamcs["coefficients"] if row.get("dataset") == selected_dataset]

    status = determine_export_status(combined.get("go_no_go", ""), selected_coefficients)
    evidence_lookup = build_evidence_lookup(combined["evidence"])
    predictors = [
        export_predictor(row, evidence_lookup)
        for row in selected_coefficients
        if finite_or_none(row.get("beta")) is not None
    ]

    calibration = select_calibration(nhamcs["calibration_metrics"], selected_model_id, selected_dataset)
    pain_verdict = first_value(combined["pain"], "verdict", "not_evaluated")
    dataset_sources = dataset_sources_available(bundle)
    covariance_path = selected_uncertainty_path(nhamcs, selected_model_id, "covariance")
    draws_path = selected_uncertainty_path(nhamcs, selected_model_id, "draws")
    fever_status = first_value(combined["fever"], "assigned_evidence_tier", "not_reviewed")

    return {
        "model_version": f"ed_disposition_empirical_reporting_{run_id}",
        "model_id": selected_model_id,
        "status": status,
        "model_activation_status": model_activation_status(status),
        "coefficient_source": coefficient_source_name(selected_dataset),
        "fever_promotion_gate_status": fever_status,
        "population": "adult men 18-64, ED, non-traumatic abdominal pain",
        "endpoint": "same-hospital admission vs routine home discharge after exclusions",
        "dataset_sources": dataset_sources,
        "cohort_counts": cohort_counts(bundle),
        "predictors": predictors,
        "predictor_evidence_tiers": predictor_evidence_tiers(
            combined["evidence"],
            selected_coefficients,
            selected_dataset,
            selected_model_id,
        ),
        "covariance_matrix_path": covariance_path,
        "posterior_draws_path": draws_path,
        "calibration": {
            "intercept": calibration.get("calibration_in_the_large"),
            "slope": calibration.get("calibration_slope"),
            "observed_prevalence": calibration.get("observed_prevalence"),
            "mean_predicted": calibration.get("mean_predicted"),
            "brier_score": calibration.get("brier_score"),
            "auroc": calibration.get("auroc"),
        },
        "pain_monotonicity_verdict": pain_verdict,
        "allowed_use": "educational only; not clinical decision support",
        "generated_at": generated_at,
        "run_id": run_id,
    }


def selected_model_id_for_source(nhamcs: dict[str, Any], combined: dict[str, Any]) -> str:
    if nhamcs.get("dataset") == POOLED_DATASET:
        if tachycardia_activation_status(nhamcs) == "eligible_for_educational_activation":
            return POOLED_TACHYCARDIA_EXPORT_MODEL
        if first_value(combined.get("hematemesis_activation", []), "activation_status", "") == "eligible_for_educational_activation":
            return POOLED_HEMATEMESIS_EXPORT_MODEL
        if first_value(combined.get("vomiting_activation", []), "activation_status", "") == "eligible_for_educational_activation":
            return POOLED_VOMITING_EXPORT_MODEL
        return POOLED_FEVER_EXPORT_MODEL
    return "A_reduced_categorical"


def tachycardia_activation_status(nhamcs: dict[str, Any]) -> str:
    for row in nhamcs.get("tachycardia_gate", []):
        if row.get("gate") == "activation_suitability":
            return str(row.get("status", ""))
    return ""


def selected_uncertainty_path(nhamcs: dict[str, Any], model_id: str, kind: str) -> str | None:
    if model_id == POOLED_TACHYCARDIA_EXPORT_MODEL:
        return path_or_none(nhamcs.get("tachycardia_covariance_path" if kind == "covariance" else "tachycardia_draws_path"))
    if model_id == POOLED_HEMATEMESIS_EXPORT_MODEL:
        return path_or_none(nhamcs.get("hematemesis_covariance_path" if kind == "covariance" else "hematemesis_draws_path"))
    if model_id == POOLED_VOMITING_EXPORT_MODEL:
        return path_or_none(nhamcs.get("vomiting_covariance_path" if kind == "covariance" else "vomiting_draws_path"))
    return path_or_none(nhamcs.get("covariance_path" if kind == "covariance" else "draws_path"))


def coefficient_source_name(dataset: str) -> str:
    if dataset == POOLED_DATASET:
        return "nhamcs_pooled_2018_2022"
    if dataset == "NHAMCS_2022":
        return "nhamcs_2022"
    return dataset.lower()


def model_activation_status(status: str) -> str:
    if status == "reduced_empirical_candidate":
        return "eligible_for_educational_activation_after_review"
    if status == "v4_adopted":
        return "v4_eligible_for_educational_activation_after_review"
    return "blocked_pending_full_reduced_model_gates"


def determine_export_status(go_no_go: str, coefficients: list[dict[str, Any]]) -> str:
    if not coefficients:
        return "prototype_v3"
    lower = go_no_go.lower()
    if "candidate v4 can be adopted: yes" in lower:
        return "v4_adopted"
    if "reduced empirical model can be activated: yes" in lower or "yes_after_review" in lower:
        return "reduced_empirical_candidate"
    if "reduced empirical model can be activated: no" in lower:
        return "reduced_empirical_blocked"
    return "v4_candidate_not_adopted"


def export_predictor(row: dict[str, Any], evidence_lookup: dict[tuple[str, str, str, str], dict[str, str]]) -> dict[str, Any]:
    key = (
        str(row.get("dataset", "")),
        str(row.get("model_id", "")),
        str(row.get("term", "")),
        str(row.get("level", "")),
    )
    evidence = evidence_lookup.get(key, {})
    assigned_tier = evidence.get("assigned_evidence_tier") or row.get("evidence_tier", "") or "unsupported"
    beta = finite_or_none(row.get("beta"))
    se = finite_or_none(row.get("se"))
    return {
        "term": str(row.get("term", "")),
        "level": str(row.get("level", "")),
        "reference": False,
        "center_beta": beta,
        "se_or_sd": se,
        "distribution": "normal_approximation_exploratory" if se is not None else "point_estimate_only",
        "evidence_tier": assigned_tier,
        "source": str(row.get("dataset", "")),
        "limitation_note": limitation_note(row, evidence),
    }


def limitation_note(row: dict[str, Any], evidence: dict[str, str]) -> str:
    notes = []
    source_note = str(row.get("limitation_note", "")).strip()
    if source_note and not (
        evidence.get("assigned_evidence_tier") == "dataset_derived"
        and "no coefficient promotion or app activation" in source_note.lower()
    ):
        notes.append(source_note)
    if evidence.get("blockers"):
        notes.append("Evidence-tier blockers: " + str(evidence["blockers"]))
    if evidence.get("assigned_evidence_tier") == "dataset_derived":
        notes.append(
            "Dataset-derived from pooled NHAMCS evidence gates for educational use only; not clinical decision support."
        )
    return " ".join(notes).strip()


def select_calibration(rows: list[dict[str, str]], model_id: str, dataset: str) -> dict[str, float | None]:
    selected = next((row for row in rows if row.get("model_id") == model_id and row.get("dataset") == dataset), None)
    if selected is None:
        selected = rows[0] if rows else {}
    fields = [
        "calibration_in_the_large",
        "calibration_slope",
        "observed_prevalence",
        "mean_predicted",
        "brier_score",
        "auroc",
    ]
    return {field: finite_or_none(selected.get(field)) for field in fields}


def cohort_counts(bundle: dict[str, Any]) -> dict[str, Any]:
    nhamcs_endpoint = bundle["nhamcs"]["endpoint_audit"]
    mimic_endpoint = bundle["mimic"]["endpoint_audit"]
    nhamcs_flow = bundle["nhamcs"]["cohort_flow"]
    mimic_flow = bundle["mimic"]["cohort_flow"]
    counts = {
        "MIMIC_IV_ED": {
            "start_n": numeric_from_flow(mimic_flow, 0, "n"),
            "strict_binary_n": numeric_from_flow(mimic_flow, -1, "n"),
            "admission_events": endpoint_count(mimic_endpoint, "endpoint_class", "admit", "n"),
            "routine_home_discharge": endpoint_count(mimic_endpoint, "endpoint_class", "routine_home_discharge", "n"),
        },
    }
    if bundle["nhamcs"].get("dataset") == POOLED_DATASET:
        summary = bundle["nhamcs"].get("pooled_summary", {})
        counts[POOLED_DATASET] = {
            "strict_binary_unweighted_n": number_for_json(summary.get("pooled_strict_binary_n")),
            "admission_events": number_for_json(summary.get("pooled_admission_events")),
            "weighted_admission_prevalence": number_for_json(summary.get("weighted_admission_prevalence")),
            "event_count_gate_passed": bool(summary.get("event_count_gate_passed")),
        }
    else:
        counts["NHAMCS_2022"] = {
            "start_unweighted_n": numeric_from_flow(nhamcs_flow, 0, "unweighted_n"),
            "strict_binary_unweighted_n": numeric_from_flow(nhamcs_flow, -1, "unweighted_n"),
            "strict_binary_weighted_n": numeric_from_flow(nhamcs_flow, -1, "weighted_n"),
            "admission_events": endpoint_count(nhamcs_endpoint, "raw_disposition_class", "admit", "unweighted_n"),
            "routine_home_discharge": endpoint_count(nhamcs_endpoint, "raw_disposition_class", "routine_home_discharge", "unweighted_n"),
        }
    return counts


def dataset_sources_available(bundle: dict[str, Any]) -> list[str]:
    sources = []
    if bundle["nhamcs"]["cohort_flow"] or bundle["nhamcs"]["coefficients"]:
        sources.append(bundle["nhamcs"].get("dataset", "NHAMCS_2022"))
    if bundle["mimic"]["cohort_flow"] or bundle["mimic"]["coefficients"]:
        sources.append("MIMIC_IV_ED")
    return sources


def build_empirical_report(bundle: dict[str, Any], app_export: dict[str, Any]) -> str:
    combined = bundle["combined"]
    nhamcs = bundle["nhamcs"]
    mimic = bundle["mimic"]
    evidence_counts = Counter(row.get("assigned_evidence_tier", "") for row in combined["evidence"])
    nhamcs_dataset = nhamcs.get("dataset", "NHAMCS_2022")
    lines = [
        "# Empirical Model Report",
        "",
        f"Generated: {app_export['generated_at']}",
        f"Run ID: `{app_export['run_id']}`",
        f"Export status: `{app_export['status']}`",
        "",
        "This report covers an educational/statistical ED disposition model. It is not clinical decision support.",
        "",
        "## Cohort Flow Summary",
        render_table(nhamcs["cohort_flow"], ["step", "unweighted_n", "weighted_n", "excluded_n", "notes"], limit=20),
        "",
        render_table(mimic["cohort_flow"], ["step", "n", "excluded_n", "notes"], limit=20),
        "",
        "## Endpoint Audit Summary",
        render_table(nhamcs["endpoint_audit"], ["raw_disposition_class", "unweighted_n", "weighted_n", "analytic_action", "conflict_flag"], limit=20),
        "",
        render_table(mimic["endpoint_audit"], ["endpoint_class", "include_primary_binary", "n", "admission_events", "exclusion_reason", "conflict_rule"], limit=20),
        "",
        "## Missingness Summary",
        render_table(strict_binary_missingness(nhamcs["missingness"], nhamcs_dataset), ["dataset", "field", "endpoint", "n", "missing_n", "missing_pct", "weighted_missing_pct"], limit=30),
        "",
        render_table(strict_binary_missingness(mimic["missingness"], "MIMIC_IV_ED"), ["dataset", "field", "endpoint", "n", "missing_n", "missing_pct"], limit=30),
        "",
        "## Coefficient Table",
        f"Primary export table uses `{app_export['model_id']}` rows when present. Survey-weighted candidate rows remain inactive unless assigned `dataset_derived` by the evidence gate.",
        render_predictor_table(app_export["predictors"]),
        "",
        "## Pain Severity Findings",
        render_table(combined["pain"], ["verdict", "nhamcs_pain_rates_status", "mimic_pain_rates_status", "adjusted_order_ok", "missingness_pct", "blockers"], limit=5),
        "",
        "Pain severity is not described as monotonic because the automated criteria did not pass.",
        "",
        "## Calibration Findings",
        render_table(combined["calibration_decisions"], ["dataset", "model_id", "calibration_status", "slope_status", "intercept_status", "blockers"], limit=30),
        "",
        "NHAMCS calibration for the reduced model is exported for review; failed NHAMCS or MIMIC rows block promotion/adoption.",
        "",
        "## NHAMCS/MIMIC Transportability Notes",
        transportability_note(mimic),
        "",
        "## Evidence-Tier Assignments",
        ", ".join(f"{tier or 'blank'}={count}" for tier, count in sorted(evidence_counts.items())),
        "",
        render_table(combined["evidence"], ["dataset", "model_id", "term", "level", "assigned_evidence_tier", "blockers"], limit=30),
        "",
        "## Go/No-Go Recommendation",
        combined["go_no_go"].strip() if combined["go_no_go"] else "No combined go/no-go file was available.",
        "",
        "## Limitations",
        f"- {nhamcs_modeling_limitation(nhamcs)}",
        "- MIMIC outputs are replication/proxy-validation only and cannot promote national dataset-derived status alone.",
        "- Full app activation remains blocked unless intercept, continuous age, flexible pain, pain missingness, fever, and any expanded symptom terms pass their own gates together.",
        "- App export values must not be used for clinical decision support.",
        "",
    ]
    return "\n".join(lines)


def nhamcs_modeling_limitation(nhamcs: dict[str, Any]) -> str:
    pooled_summary = nhamcs.get("pooled_summary", {})
    if pooled_summary.get("final_reduced_model_activation_status") == "eligible_for_educational_activation":
        return "Pooled NHAMCS reduced model cleared final evidence gates for educational use; candidate v4 remains inactive."
    metadata = nhamcs.get("metadata", {})
    model_status = str(metadata.get("model_status", ""))
    survey_status = metadata.get("survey_status", {})
    primary_status = str(survey_status.get("survey_weighted_primary_status", ""))
    if model_status == "survey_weighted_candidate" or primary_status == "completed_candidate_pending_gates":
        return "NHAMCS survey-weighted logistic outputs are candidate evidence only; evidence gates still block automatic dataset-derived promotion."
    return "Fitted NHAMCS outputs are exploratory because the primary survey-weighted fit was blocked, unavailable, or intentionally off."


def build_tripods_probast_checklist(bundle: dict[str, Any], app_export: dict[str, Any]) -> str:
    cohort = app_export["cohort_counts"]
    pain = first_value(bundle["combined"]["pain"], "verdict", "not_evaluated")
    nhamcs_key = POOLED_DATASET if POOLED_DATASET in cohort else "NHAMCS_2022"
    activated = app_export["status"] == "reduced_empirical_candidate"
    performance_status = "Complete for educational activation" if activated else "Blocked for adoption"
    applicability_status = "Eligible for educational use after review" if activated else "Blocked for adoption"
    predictor_evidence = (
        "Reduced predictors cleared dataset-derived evidence gates; unsupported prototype inputs remain inactive."
        if activated
        else "Candidate predictors are mapped in version-controlled code lists; sparse/unsupported terms remain blocked or prototype."
    )
    validation_evidence = (
        "Leave-one-year-out and pooled calibration evidence are included; MIMIC remains proxy-validation only."
        if activated
        else "MIMIC is proxy-validation/replication only; transport recalibration is blocked until NHAMCS coefficients are dataset-derived."
    )
    return "\n".join(
        [
            "# TRIPOD+AI / PROBAST+AI Checklist",
            "",
            "| Domain | Status | Evidence |",
            "|---|---|---|",
            f"| Participants/source data | Partial | Sources: {', '.join(app_export['dataset_sources']) or 'none'}; target population: {app_export['population']}. |",
            f"| Predictors | Partial | {predictor_evidence} |",
            f"| Outcome | Complete for available outputs | Endpoint: {app_export['endpoint']}. Conflicts/exclusions are tabulated. |",
            f"| Sample size/events | Partial | NHAMCS strict binary N={cohort[nhamcs_key].get('strict_binary_unweighted_n')}, admissions={cohort[nhamcs_key].get('admission_events')}; MIMIC strict binary N={cohort['MIMIC_IV_ED'].get('strict_binary_n')}, admissions={cohort['MIMIC_IV_ED'].get('admission_events')}. |",
            "| Missing data | Partial | Missingness by endpoint is written; high or differential missingness remains an adoption blocker where applicable. |",
            f"| Modeling method | Partial | {nhamcs_modeling_limitation(bundle['nhamcs'])} |",
            f"| Performance/calibration | {performance_status} | Calibration decisions and reduced-model activation gates are written. |",
            f"| Validation | Partial | {validation_evidence} |",
            f"| Applicability | {applicability_status} | Current status: `{app_export['status']}`; pain verdict: `{pain}`. |",
            "| Educational-use boundary | Complete | App export states educational only; not clinical decision support. |",
            "",
        ]
    )


def build_final_decision(bundle: dict[str, Any], app_export: dict[str, Any]) -> str:
    pain = bundle["combined"]["pain"][0] if bundle["combined"]["pain"] else {}
    vomiting = bundle["combined"]["vomiting"][0] if bundle["combined"].get("vomiting") else {}
    vomiting_activation = bundle["combined"]["vomiting_activation"][0] if bundle["combined"].get("vomiting_activation") else {}
    hematemesis = bundle["combined"]["hematemesis"][0] if bundle["combined"].get("hematemesis") else {}
    hematemesis_activation = bundle["combined"]["hematemesis_activation"][0] if bundle["combined"].get("hematemesis_activation") else {}
    tachycardia_activation = tachycardia_activation_status(bundle["nhamcs"]) or "not_reviewed"
    go_no_go = bundle["combined"]["go_no_go"].strip()
    blockers = blockers_from_go_no_go(go_no_go)
    decision = "BLOCK reduced empirical activation and REJECT candidate v4 adoption"
    if app_export["status"] == "reduced_empirical_candidate":
        decision = "ACTIVATE reduced empirical candidate for educational use after review"
    elif app_export["status"] == "v4_adopted":
        decision = "ACTIVATE v4 for educational use after review"
    elif app_export["status"] == "prototype_v3":
        decision = "KEEP prototype_v3; empirical export is blocked"

    lines = [
        "# Final Blocker or Activation Decision",
        "",
        f"Decision: **{decision}.**",
        "",
        f"App export status: `{app_export['status']}`",
        f"Exported model ID: `{app_export['model_id']}`",
        f"Pain monotonicity verdict: `{app_export['pain_monotonicity_verdict']}`",
        f"Objective fever evidence tier: `{app_export['fever_promotion_gate_status']}`",
        f"Ordinary vomiting evidence tier: `{vomiting.get('assigned_evidence_tier', 'not_reviewed')}`",
        f"Expanded vomiting model activation: `{vomiting_activation.get('activation_status', 'not_reviewed')}`",
        f"Tachycardia burden model activation: `{tachycardia_activation}`",
        f"Hematemesis evidence tier: `{hematemesis.get('assigned_evidence_tier', 'not_reviewed')}`",
        f"Expanded hematemesis model activation: `{hematemesis_activation.get('activation_status', 'not_reviewed')}`",
        f"Model activation status: `{app_export['model_activation_status']}`",
        f"Allowed use: {app_export['allowed_use']}",
        "",
        "## Required Answers",
        f"- Reduced empirical model can be activated: {'yes' if app_export['status'] == 'reduced_empirical_candidate' else 'no'}",
        f"- Candidate v4 can be adopted: {'yes' if app_export['status'] == 'v4_adopted' else 'no'}",
        f"- Pain can be promoted: {pain_promotion_status(app_export['pain_monotonicity_verdict'], app_export['predictors'])}",
        f"- Objective fever can be promoted: {'yes' if app_export['fever_promotion_gate_status'] == 'dataset_derived' else 'no'}",
        f"- Ordinary vomiting can be promoted: {'yes' if vomiting.get('assigned_evidence_tier') == 'dataset_derived' else 'no'}",
        f"- Expanded reduced model with vomiting can be activated: {'yes' if vomiting_activation.get('activation_status') == 'eligible_for_educational_activation' else 'no'}",
        f"- Tachycardia burden v2 can be activated: {'yes' if app_export['model_id'] == POOLED_TACHYCARDIA_EXPORT_MODEL and app_export['status'] == 'reduced_empirical_candidate' else 'no'}",
        f"- Hematemesis can be promoted: {'yes' if hematemesis.get('assigned_evidence_tier') == 'dataset_derived' else 'no'}",
        f"- Expanded reduced model with hematemesis can be activated: {'yes' if hematemesis_activation.get('activation_status') == 'eligible_for_educational_activation' else 'no'}",
        f"- Any coefficients remain prototype/unsupported: {'yes' if any(p['evidence_tier'] != 'dataset_derived' for p in app_export['predictors']) else 'no'}",
        "",
        "## Exact Blockers",
    ]
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- None from automated report layer.")
    if pain.get("blockers"):
        lines.append(f"- Pain-specific blockers: {pain['blockers']}")
    lines.extend(["", "## Activation Conditions"])
    lines.extend(f"- {condition}" for condition in activation_conditions(bundle, app_export))
    lines.append("")
    return "\n".join(lines)


def activation_conditions(bundle: dict[str, Any], app_export: dict[str, Any]) -> list[str]:
    conditions: list[str] = []
    nhamcs = bundle["nhamcs"]
    metadata = nhamcs.get("metadata", {})
    survey_status = metadata.get("survey_status", {})
    if app_export["status"] == "reduced_empirical_candidate":
        if app_export["model_id"] == POOLED_TACHYCARDIA_EXPORT_MODEL:
            conditions.append(
                "Tachycardia burden v2 activation gate passed for intercept, continuous age, observed flexible pain, objective fever, ordinary RFV vomiting, and tachycardia_burden."
            )
        elif app_export["model_id"] == POOLED_HEMATEMESIS_EXPORT_MODEL:
            conditions.append(
                "Expanded reduced empirical activation gate passed for intercept, continuous age, flexible pain, pain missingness, objective fever, ordinary RFV vomiting, and hematemesis RFV 15802."
            )
        elif app_export["model_id"] == POOLED_VOMITING_EXPORT_MODEL:
            conditions.append(
                "Expanded reduced empirical activation gate passed for intercept, continuous age, flexible pain, pain missingness, objective fever, and ordinary RFV vomiting."
            )
        else:
            conditions.append("Reduced empirical activation gate passed for intercept, continuous age, flexible pain, pain missingness, and objective fever.")
    elif survey_status.get("survey_weighted_primary_status") == "completed_candidate_pending_gates":
        conditions.append("Review survey-weighted NHAMCS candidate outputs against codebook confirmation, sparse-event rules, calibration, and evidence gates.")
    else:
        conditions.append("Complete NHAMCS survey-weighted fitting or document an accepted alternative.")
    if app_export["status"] == "reduced_empirical_candidate":
        if app_export["model_id"] == POOLED_TACHYCARDIA_EXPORT_MODEL:
            inactive_terms = "Keep acuity, SBP, hematemesis, broad pain region, onset/duration, constant/intermittent pain, and AAP-3 inactive unless they pass separate gates."
        elif app_export["model_id"] == POOLED_HEMATEMESIS_EXPORT_MODEL:
            inactive_terms = "Keep v4 vitals, broad pain region, onset/duration, and constant/intermittent pain inactive unless they pass separate gates."
        elif app_export["model_id"] == POOLED_VOMITING_EXPORT_MODEL:
            inactive_terms = "Keep hematemesis, v4 vitals, broad pain region, onset/duration, and constant/intermittent pain inactive unless they pass separate gates."
        else:
            inactive_terms = "Keep v4 vitals, vomiting, hematemesis, broad pain region, onset/duration, and constant/intermittent pain inactive unless they pass separate gates."
        conditions.extend(
            [
                inactive_terms,
                "Treat hematemesis RFV position as documentation prominence/order, not symptom severity.",
                "Use pain only as flexible/nonmonotonic; do not claim a monotonic pain dose response.",
                "Retain educational-use labeling and do not describe the model as clinical decision support.",
            ]
        )
    else:
        conditions.extend(
            [
                "Resolve sparse cell/event blockers or keep affected terms descriptive/proxy-only.",
                "Pass calibration and transportability checks.",
                "Promote no coefficient to `dataset_derived` unless cohort, endpoint, mapping, counts, uncertainty, missingness, and calibration are documented.",
                "Use pain only as flexible/nonmonotonic unless a separate pain promotion gate passes.",
            ]
        )
    return conditions


def pain_promotion_status(verdict: str, predictors: list[dict[str, Any]] | None = None) -> str:
    if verdict == "monotonic_dataset_derived":
        return "yes_monotonic"
    if verdict == "nonmonotonic_flexible_only":
        observed_pain_required = {
            ("pain_bin3", "mild"),
            ("pain_bin3", "severe"),
        }
        legacy_missing_indicator = {("pain_missing", "1")}
        promoted = {
            (str(predictor.get("term", "")), str(predictor.get("level", "")))
            for predictor in (predictors or [])
            if predictor.get("evidence_tier") == "dataset_derived"
        }
        if observed_pain_required.issubset(promoted):
            if legacy_missing_indicator.issubset(promoted):
                return "flexible_nonmonotonic_dataset_derived"
            return "flexible_nonmonotonic_observed_pain_dataset_derived"
        return "flexible_only_pending_separate_review"
    return "no"


def build_run_manifest(bundle: dict[str, Any], app_export: dict[str, Any], output_dir: Path, generated_at: str, run_id: str) -> dict[str, Any]:
    nhamcs_paths = nhamcs_manifest_input_paths(bundle["paths"]["nhamcs"], bundle["nhamcs"].get("dataset", "NHAMCS_2022"))
    input_paths = [
        *nhamcs_paths,
        bundle["paths"]["mimic"] / "cohort_flow_mimic.csv",
        bundle["paths"]["mimic"] / "endpoint_audit_mimic.csv",
        bundle["paths"]["mimic"] / "missingness_by_endpoint.csv",
        bundle["paths"]["mimic"] / "coefficients.csv",
        bundle["paths"]["mimic"] / "covariance_matrix.csv",
        bundle["paths"]["mimic"] / "posterior_draws.csv",
        bundle["paths"]["mimic"] / "calibration_metrics.csv",
        bundle["paths"]["combined"] / "pain_monotonicity_summary.csv",
        bundle["paths"]["combined"] / "evidence_tier_assignments.csv",
        bundle["paths"]["combined"] / "fever_promotion_decision.csv",
        bundle["paths"]["combined"] / "vomiting_promotion_decision.csv",
        bundle["paths"]["combined"] / "hematemesis_promotion_decision.csv",
        bundle["paths"]["combined"] / "final_model_activation_decision.csv",
        bundle["paths"]["combined"] / "vomiting_expanded_model_activation_decision.csv",
        bundle["paths"]["combined"] / "hematemesis_expanded_model_activation_decision.csv",
        bundle["paths"]["combined"] / "calibration_decision_summary.csv",
        bundle["paths"]["combined"] / "go_no_go_summary.md",
    ]
    output_paths = [
        output_dir / "app_export.json",
        output_dir / "empirical_model_report.md",
        output_dir / "tripods_probast_checklist.md",
        output_dir / "run_manifest.json",
        output_dir / "final_blocker_or_activation_decision.md",
    ]
    return {
        "run_id": run_id,
        "generated_at": generated_at,
        "status": app_export["status"],
        "python": sys.version,
        "platform": platform.platform(),
        "script": relpath(Path(__file__)),
        "input_files": [file_record(path) for path in input_paths],
        "output_files": [file_record(path, hash_if_exists=False) for path in output_paths],
        "source_metadata": {
            "nhamcs": bundle["nhamcs"]["metadata"],
            "mimic": bundle["mimic"]["metadata"],
        },
        "app_export_schema_validated": True,
    }


def write_artifacts(artifacts: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = {
        "app_export": output_dir / "app_export.json",
        "empirical_model_report": output_dir / "empirical_model_report.md",
        "tripods_probast_checklist": output_dir / "tripods_probast_checklist.md",
        "run_manifest": output_dir / "run_manifest.json",
        "final_decision": output_dir / "final_blocker_or_activation_decision.md",
    }
    write_json(output_paths["app_export"], artifacts["app_export"])
    output_paths["empirical_model_report"].write_text(artifacts["empirical_model_report"], encoding="utf-8")
    output_paths["tripods_probast_checklist"].write_text(artifacts["tripods_probast_checklist"], encoding="utf-8")
    output_paths["final_decision"].write_text(artifacts["final_decision"], encoding="utf-8")
    artifacts["run_manifest"]["output_files"] = [
        file_record(output_paths["app_export"], hash_if_exists=False),
        file_record(output_paths["empirical_model_report"], hash_if_exists=False),
        file_record(output_paths["tripods_probast_checklist"], hash_if_exists=False),
        file_record(output_paths["run_manifest"], hash_if_exists=False),
        file_record(output_paths["final_decision"], hash_if_exists=False),
    ]
    write_json(output_paths["run_manifest"], artifacts["run_manifest"])
    artifacts["run_manifest"]["output_files"] = [
        file_record(output_paths["app_export"], hash_if_exists=False),
        file_record(output_paths["empirical_model_report"], hash_if_exists=False),
        file_record(output_paths["tripods_probast_checklist"], hash_if_exists=False),
        file_record(output_paths["run_manifest"], hash_if_exists=False),
        file_record(output_paths["final_decision"], hash_if_exists=False),
    ]
    write_json(output_paths["run_manifest"], artifacts["run_manifest"])


def validate_app_export(export: dict[str, Any]) -> None:
    missing = sorted(APP_EXPORT_REQUIRED_KEYS - set(export))
    extra = sorted(set(export) - APP_EXPORT_REQUIRED_KEYS)
    if missing:
        raise ValueError(f"app_export.json missing required keys: {missing}")
    if extra:
        raise ValueError(f"app_export.json contains unsupported keys: {extra}")
    if export["status"] not in ALLOWED_EXPORT_STATUSES:
        raise ValueError(f"invalid app export status: {export['status']}")
    if not isinstance(export["model_id"], str) or not export["model_id"]:
        raise ValueError("model_id must be a non-empty string")
    if export["model_activation_status"] not in {
        "eligible_for_educational_activation_after_review",
        "v4_eligible_for_educational_activation_after_review",
        "blocked_pending_full_reduced_model_gates",
    }:
        raise ValueError("invalid model_activation_status")
    if not isinstance(export["coefficient_source"], str) or not export["coefficient_source"]:
        raise ValueError("coefficient_source must be a non-empty string")
    if export["fever_promotion_gate_status"] not in {
        "not_reviewed",
        "unsupported",
        "survey_weighted_candidate",
        "dataset_derived_candidate",
        "dataset_derived",
    }:
        raise ValueError("invalid fever_promotion_gate_status")
    if export["population"] != "adult men 18-64, ED, non-traumatic abdominal pain":
        raise ValueError("invalid population string")
    if export["endpoint"] != "same-hospital admission vs routine home discharge after exclusions":
        raise ValueError("invalid endpoint string")
    if export["allowed_use"] != "educational only; not clinical decision support":
        raise ValueError("invalid allowed_use string")
    if not isinstance(export["dataset_sources"], list):
        raise ValueError("dataset_sources must be a list")
    if not isinstance(export["cohort_counts"], dict):
        raise ValueError("cohort_counts must be an object")
    if not isinstance(export["predictors"], list):
        raise ValueError("predictors must be a list")
    if not isinstance(export["predictor_evidence_tiers"], list):
        raise ValueError("predictor_evidence_tiers must be a list")
    for predictor in export["predictors"]:
        validate_predictor(predictor)
    validate_calibration(export["calibration"])
    if any(p["evidence_tier"] == "dataset_derived" for p in export["predictors"]):
        if not export["covariance_matrix_path"] and not export["posterior_draws_path"]:
            raise ValueError("dataset_derived predictors require covariance or draw output")


def validate_predictor(predictor: dict[str, Any]) -> None:
    required = {
        "term",
        "level",
        "reference",
        "center_beta",
        "se_or_sd",
        "distribution",
        "evidence_tier",
        "source",
        "limitation_note",
    }
    if set(predictor) != required:
        raise ValueError(f"invalid predictor keys: {sorted(set(predictor))}")
    if not isinstance(predictor["term"], str):
        raise ValueError("predictor term must be a string")
    if not isinstance(predictor["reference"], bool):
        raise ValueError("predictor reference must be boolean")
    if predictor["center_beta"] is not None and not isinstance(predictor["center_beta"], (int, float)):
        raise ValueError("predictor center_beta must be numeric or null")
    if predictor["se_or_sd"] is not None and not isinstance(predictor["se_or_sd"], (int, float)):
        raise ValueError("predictor se_or_sd must be numeric or null")
    if predictor["evidence_tier"] == "dataset_derived" and not predictor["limitation_note"]:
        raise ValueError("dataset_derived predictor must retain a limitation/source note")


def validate_calibration(calibration: dict[str, Any]) -> None:
    expected = {"intercept", "slope", "observed_prevalence", "mean_predicted", "brier_score", "auroc"}
    if set(calibration) != expected:
        raise ValueError("invalid calibration keys")
    for value in calibration.values():
        if value is not None and not isinstance(value, (int, float)):
            raise ValueError("calibration values must be numeric or null")


def predictor_evidence_tiers(
    rows: list[dict[str, str]],
    coefficients: list[dict[str, Any]],
    dataset: str,
    model_id: str,
) -> list[dict[str, str]]:
    selected = [
        {
            "term": row.get("term", ""),
            "level": row.get("level", ""),
            "evidence_tier": row.get("assigned_evidence_tier", ""),
            "blockers": row.get("blockers", ""),
        }
        for row in rows
        if row.get("dataset") == dataset and row.get("model_id") == model_id
    ]
    if selected:
        return selected

    return [
        {
            "term": str(row.get("term", "")),
            "level": str(row.get("level", "")),
            "evidence_tier": str(row.get("evidence_tier", "")),
            "blockers": "",
        }
        for row in coefficients
        if str(row.get("dataset", "")) == dataset and str(row.get("model_id", "")) == model_id
    ]


def nhamcs_manifest_input_paths(source_dir: Path, dataset: str) -> list[Path]:
    if dataset == POOLED_DATASET:
        return [
            source_dir / "cohort_flow_by_year.csv",
            source_dir / "endpoint_audit_by_year.csv",
            source_dir / "missingness_by_year_and_endpoint.csv",
            source_dir / "codebook_confirmation_audit.csv",
            source_dir / "vomiting_codebook_confirmation_audit.csv",
            source_dir / "hematemesis_codebook_confirmation_audit.csv",
            source_dir / "fever_sparse_cell_gate_decision.csv",
            source_dir / "fever_model_comparison_coefficients.csv",
            source_dir / "fever_model_comparison_covariance.csv",
            source_dir / "fever_model_comparison_draws.csv",
            source_dir / "fever_model_comparison_calibration.csv",
            source_dir / "vomiting_gate_decision.csv",
            source_dir / "vomiting_cell_counts_by_year.csv",
            source_dir / "vomiting_unadjusted_rates_by_year.csv",
            source_dir / "vomiting_model_comparison_coefficients.csv",
            source_dir / "vomiting_model_comparison_covariance.csv",
            source_dir / "vomiting_model_comparison_draws.csv",
            source_dir / "vomiting_model_comparison_calibration.csv",
            source_dir / "vomiting_leave_one_year_out_validation.csv",
            source_dir / "vomiting_tier_sensitivity.csv",
            source_dir / "tachycardia_burden_gate_decision.csv",
            source_dir / "tachycardia_burden_term_decisions.csv",
            source_dir / "tachycardia_burden_cell_counts.csv",
            source_dir / "tachycardia_model_comparison_coefficients.csv",
            source_dir / "tachycardia_model_comparison_covariance.csv",
            source_dir / "tachycardia_model_comparison_draws.csv",
            source_dir / "tachycardia_model_comparison_calibration.csv",
            source_dir / "tachycardia_burden_leave_one_year_out_validation.csv",
            source_dir / "hematemesis_gate_decision.csv",
            source_dir / "hematemesis_cell_counts_by_year.csv",
            source_dir / "hematemesis_unadjusted_rates_by_year.csv",
            source_dir / "hematemesis_model_comparison_coefficients.csv",
            source_dir / "hematemesis_model_comparison_covariance.csv",
            source_dir / "hematemesis_model_comparison_draws.csv",
            source_dir / "hematemesis_model_comparison_calibration.csv",
            source_dir / "hematemesis_leave_one_year_out_validation.csv",
            source_dir / "hematemesis_tier_sensitivity.csv",
            source_dir / "final_reduced_model_cell_counts.csv",
            source_dir / "final_reduced_model_leave_one_year_out_terms.csv",
            source_dir / "final_reduced_model_calibration.csv",
            source_dir / "final_reduced_model_gate_decision.csv",
            source_dir / "final_reduced_model_term_decisions.csv",
        ]
    return [
        source_dir / "cohort_flow_nhamcs.csv",
        source_dir / "endpoint_audit_nhamcs.csv",
        source_dir / "missingness_by_endpoint.csv",
        source_dir / "coefficients.csv",
        source_dir / "covariance_matrix.csv",
        source_dir / "mvn_coefficient_draws.csv",
        source_dir / "calibration_metrics.csv",
    ]


def build_evidence_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    return {
        (row.get("dataset", ""), row.get("model_id", ""), row.get("term", ""), row.get("level", "")): row
        for row in rows
    }


def strict_binary_missingness(rows: list[dict[str, str]], dataset: str) -> list[dict[str, str]]:
    keep = []
    for row in rows:
        if row.get("dataset") != dataset:
            continue
        if row.get("endpoint") not in {"admit", "routine_home_discharge"}:
            continue
        if row.get("field") in {
            "age",
            "age_band",
            "pain_score",
            "pain_bin3",
            "vomiting",
            "vomiting_present",
            "vomiting_rfv_position_tier",
            "hematemesis_present",
            "hematemesis_rfv_position_tier",
            "fever_or_temp",
            "temp",
            "acuity",
            "HR",
            "tachycardia_burden",
            "SBP",
        }:
            keep.append(row)
    return keep


def render_predictor_table(predictors: list[dict[str, Any]]) -> str:
    rows = [
        {
            "term": predictor["term"],
            "level": predictor["level"],
            "beta": format_value(predictor["center_beta"]),
            "se_or_sd": format_value(predictor["se_or_sd"]),
            "evidence_tier": predictor["evidence_tier"],
            "source": predictor["source"],
        }
        for predictor in predictors
    ]
    return render_table(rows, ["term", "level", "beta", "se_or_sd", "evidence_tier", "source"], limit=50)


def render_table(rows: list[dict[str, Any]], columns: list[str], limit: int = 20) -> str:
    if not rows:
        return "_No rows available._"
    selected_rows = rows[:limit]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in selected_rows:
        body.append("| " + " | ".join(markdown_cell(row.get(column, "")) for column in columns) + " |")
    if len(rows) > limit:
        body.append("| " + " | ".join(["..."] + [""] * (len(columns) - 1)) + " |")
    return "\n".join([header, separator, *body])


def transportability_note(mimic: dict[str, Any]) -> str:
    if mimic["transportability_report"]:
        return mimic["transportability_report"].strip()
    return "Transportability report was not available. Source-specific calibration only."


def blockers_from_go_no_go(text: str) -> list[str]:
    blockers = []
    in_blockers = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "## Exact Blockers":
            in_blockers = True
            continue
        if in_blockers and stripped.startswith("## "):
            break
        if in_blockers and stripped.startswith("- "):
            blockers.append(stripped[2:])
    return blockers


def endpoint_count(rows: list[dict[str, str]], class_field: str, value: str, count_field: str) -> int | float | None:
    for row in rows:
        if row.get(class_field) == value:
            return number_for_json(row.get(count_field))
    return None


def numeric_from_flow(rows: list[dict[str, str]], index: int, field: str) -> int | float | None:
    if not rows:
        return None
    try:
        return number_for_json(rows[index].get(field))
    except IndexError:
        return None


def first_value(rows: list[dict[str, str]], field: str, default: str) -> str:
    if not rows:
        return default
    value = rows[0].get(field)
    return value if value not in {None, ""} else default


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def number_for_json(value: Any) -> int | float | None:
    number = finite_or_none(value)
    if number is None:
        return None
    if abs(number - int(number)) < 1e-9:
        return int(number)
    return number


def path_or_none(path: Path | None) -> str | None:
    return relpath(path) if path is not None else None


def relpath(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def file_record(path: Path, hash_if_exists: bool = True) -> dict[str, Any]:
    exists = path.exists()
    record: dict[str, Any] = {
        "path": relpath(path),
        "exists": exists,
        "bytes": path.stat().st_size if exists else None,
    }
    if hash_if_exists and exists:
        record["sha256"] = sha256_file(path)
    return record


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def markdown_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\n", " ").replace("|", "\\|")
    if len(text) > 180:
        text = text[:177] + "..."
    return text


def format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return f"{value:.6g}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
