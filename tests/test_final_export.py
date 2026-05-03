#!/usr/bin/env python3
"""Smoke tests for final empirical export/reporting layer."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "modeling"))

import final_export  # noqa: E402


def valid_export() -> dict:
    return {
        "model_version": "test",
        "model_id": "A_reduced_categorical",
        "status": "v4_candidate_not_adopted",
        "model_activation_status": "blocked_pending_full_reduced_model_gates",
        "coefficient_source": "nhamcs_2022",
        "fever_promotion_gate_status": "not_reviewed",
        "population": "adult men 18-64, ED, non-traumatic abdominal pain",
        "endpoint": "same-hospital admission vs routine home discharge after exclusions",
        "dataset_sources": ["NHAMCS_2022"],
        "cohort_counts": {"NHAMCS_2022": {"strict_binary_unweighted_n": 10}},
        "predictors": [
            {
                "term": "intercept",
                "level": "",
                "reference": False,
                "center_beta": -1.0,
                "se_or_sd": 0.2,
                "distribution": "normal_approximation_exploratory",
                "evidence_tier": "prototype_assumption",
                "source": "NHAMCS_2022",
                "limitation_note": "exploratory fixture",
            }
        ],
        "predictor_evidence_tiers": [],
        "covariance_matrix_path": "outputs/nhamcs/covariance_matrix.csv",
        "posterior_draws_path": None,
        "calibration": {
            "intercept": 0.0,
            "slope": 1.0,
            "observed_prevalence": 0.2,
            "mean_predicted": 0.2,
            "brier_score": 0.1,
            "auroc": 0.7,
        },
        "pain_monotonicity_verdict": "null_or_unstable",
        "allowed_use": "educational only; not clinical decision support",
        "generated_at": "2026-04-28T00:00:00Z",
        "run_id": "test",
    }


class FinalExportTests(unittest.TestCase):
    def test_app_export_schema_accepts_valid_payload(self) -> None:
        final_export.validate_app_export(valid_export())

    def test_dataset_derived_requires_uncertainty_output(self) -> None:
        payload = valid_export()
        payload["covariance_matrix_path"] = None
        payload["posterior_draws_path"] = None
        payload["predictors"][0]["evidence_tier"] = "dataset_derived"
        with self.assertRaises(ValueError):
            final_export.validate_app_export(payload)

    def test_status_blocks_when_coefficients_are_absent(self) -> None:
        status = final_export.determine_export_status("Reduced empirical model can be activated: no", [])
        self.assertEqual(status, "prototype_v3")

    def test_status_keeps_v4_unadopted_when_gates_fail(self) -> None:
        status = final_export.determine_export_status("Candidate v4 can be adopted: no", [{"term": "intercept"}])
        self.assertEqual(status, "v4_candidate_not_adopted")

    def test_status_marks_reduced_empirical_blocked_when_full_gate_fails(self) -> None:
        status = final_export.determine_export_status(
            "Reduced empirical model can be activated: no",
            [{"term": "fever_or_temp"}],
        )
        self.assertEqual(status, "reduced_empirical_blocked")

    def test_status_marks_reduced_empirical_candidate_when_full_gate_passes(self) -> None:
        status = final_export.determine_export_status(
            "Reduced empirical model can be activated: yes_after_review",
            [{"term": "intercept"}],
        )
        self.assertEqual(status, "reduced_empirical_candidate")

    def test_flexible_pain_status_passes_when_all_pain_terms_dataset_derived(self) -> None:
        predictors = [
            {"term": "pain_bin3", "level": "mild", "evidence_tier": "dataset_derived"},
            {"term": "pain_bin3", "level": "severe", "evidence_tier": "dataset_derived"},
        ]
        self.assertEqual(
            final_export.pain_promotion_status("nonmonotonic_flexible_only", predictors),
            "flexible_nonmonotonic_observed_pain_dataset_derived",
        )

    def test_selected_model_prefers_tachycardia_when_activation_gate_passes(self) -> None:
        nhamcs = {
            "dataset": final_export.POOLED_DATASET,
            "tachycardia_gate": [
                {"gate": "activation_suitability", "status": "eligible_for_educational_activation"}
            ],
        }
        selected = final_export.selected_model_id_for_source(
            nhamcs,
            {
                "hematemesis_activation": [{"activation_status": "eligible_for_educational_activation"}],
                "vomiting_activation": [{"activation_status": "eligible_for_educational_activation"}],
            },
        )
        self.assertEqual(selected, final_export.POOLED_TACHYCARDIA_EXPORT_MODEL)

    def test_selected_model_prefers_hematemesis_only_after_activation_gate(self) -> None:
        nhamcs = {"dataset": final_export.POOLED_DATASET}
        selected = final_export.selected_model_id_for_source(
            nhamcs,
            {
                "hematemesis_activation": [{"activation_status": "eligible_for_educational_activation"}],
                "vomiting_activation": [{"activation_status": "eligible_for_educational_activation"}],
            },
        )
        self.assertEqual(selected, final_export.POOLED_HEMATEMESIS_EXPORT_MODEL)

        selected_without_hematemesis = final_export.selected_model_id_for_source(
            nhamcs,
            {
                "hematemesis_activation": [{"activation_status": "blocked"}],
                "vomiting_activation": [{"activation_status": "eligible_for_educational_activation"}],
            },
        )
        self.assertEqual(selected_without_hematemesis, final_export.POOLED_VOMITING_EXPORT_MODEL)


if __name__ == "__main__":
    unittest.main()
