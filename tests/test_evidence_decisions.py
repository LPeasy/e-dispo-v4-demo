#!/usr/bin/env python3
"""Synthetic tests for shared evidence decision rules."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "modeling"))

import evidence_decisions  # noqa: E402
import pain_monotonicity  # noqa: E402


def pain_rates(values: tuple[float, float, float], dataset: str = "NHAMCS_2022") -> list[dict[str, str]]:
    return [
        {"dataset": dataset, "pain_bin": "0-3", "n": "100", "events": str(int(values[0] * 100)), "admit_pct": str(values[0])},
        {"dataset": dataset, "pain_bin": "4-6", "n": "100", "events": str(int(values[1] * 100)), "admit_pct": str(values[1])},
        {"dataset": dataset, "pain_bin": "7-10", "n": "100", "events": str(int(values[2] * 100)), "admit_pct": str(values[2])},
    ]


def coefficients(mild: float = -0.2, severe: float = 0.5, continuous: float = 0.4, acuity: float = 0.2) -> list[dict[str, str]]:
    return [
        {"dataset": "NHAMCS_2022", "model_id": "A_reduced_categorical", "term": "pain_bin3", "level": "mild", "beta": str(mild), "se": "0.1", "ci_low": "0.8", "ci_high": "1.0", "evidence_tier": "dataset_derived"},
        {"dataset": "NHAMCS_2022", "model_id": "A_reduced_categorical", "term": "pain_bin3", "level": "severe", "beta": str(severe), "se": "0.1", "ci_low": "1.1", "ci_high": "1.8", "evidence_tier": "dataset_derived"},
        {"dataset": "NHAMCS_2022", "model_id": "C_continuous_pain_exploratory", "term": "pain_score", "level": "scaled", "beta": str(continuous), "se": "0.1", "evidence_tier": "dataset_derived"},
        {"dataset": "NHAMCS_2022", "model_id": "B_reduced_plus_acuity_vitals", "term": "pain_score", "level": "scaled", "beta": str(acuity), "se": "0.1", "evidence_tier": "dataset_derived"},
    ]


def calibration_rows(slope: float = 1.0, brier: float = 0.10) -> list[dict[str, str]]:
    return [
        {"dataset": "NHAMCS_2022", "model_id": "A_reduced_categorical", "observed_prevalence": "0.2", "mean_predicted": "0.2", "calibration_slope": str(slope), "brier_score": str(brier)},
        {"dataset": "NHAMCS_2022", "model_id": "D_no_pain_comparator", "observed_prevalence": "0.2", "mean_predicted": "0.2", "calibration_slope": "1.0", "brier_score": "0.12"},
        {"dataset": "NHAMCS_2022", "model_id": "C_continuous_pain_exploratory", "observed_prevalence": "0.2", "mean_predicted": "0.2", "calibration_slope": "1.0", "brier_score": "0.11"},
    ]


def missingness(percent: float = 10.0) -> list[dict[str, str]]:
    return [
        {"dataset": "NHAMCS_2022", "field": "pain_score", "endpoint": "admit", "n": "100", "missing_n": str(percent), "missing_pct": str(percent)},
        {"dataset": "NHAMCS_2022", "field": "pain_score", "endpoint": "routine_home_discharge", "n": "100", "missing_n": str(percent), "missing_pct": str(percent)},
    ]


def pooled_fever_artifacts(
    *,
    mapping: bool = True,
    gate_status: str = "eligible_for_evidence_promotion",
    final_gate_status: str = "eligible_for_educational_activation",
    draw_count: int = 10000,
    covariance: bool = True,
) -> dict:
    return {
        "cohort": True,
        "endpoint": True,
        "mapping": mapping,
        "counts": True,
        "vomiting_counts": True,
        "missingness": True,
        "covariance_models": {evidence_decisions.POOLED_FEVER_EXPORT_MODEL} if covariance else set(),
        "draw_models": {evidence_decisions.POOLED_FEVER_EXPORT_MODEL} if draw_count else set(),
        "draw_counts": {evidence_decisions.POOLED_FEVER_EXPORT_MODEL: draw_count},
        "fever_gate_status": gate_status,
        "vomiting_gate_status": "missing",
        "final_gate_status": final_gate_status,
        "vomiting_mapping": True,
        "missing_temperature_audit": True,
    }


def pooled_fever_bundle(artifacts: dict | None = None) -> dict:
    return {
        "coefficients": [
            {
                "dataset": evidence_decisions.POOLED_DATASET,
                "model_id": evidence_decisions.POOLED_FEVER_EXPORT_MODEL,
                "source_model_id": evidence_decisions.POOLED_FEVER_SOURCE_MODEL,
                "term": "fever_or_temp",
                "level": "1",
                "beta": "1.2",
                "se": "0.5",
                "evidence_tier": "survey_weighted_candidate",
            },
            {
                "dataset": evidence_decisions.POOLED_DATASET,
                "model_id": evidence_decisions.POOLED_FEVER_EXPORT_MODEL,
                "source_model_id": evidence_decisions.POOLED_FEVER_SOURCE_MODEL,
                "term": "pain_bin3",
                "level": "severe",
                "beta": "0.7",
                "se": "0.2",
                "evidence_tier": "survey_weighted_candidate",
            },
            {
                "dataset": evidence_decisions.POOLED_DATASET,
                "model_id": "unsupported_symptom_model",
                "term": "vomiting",
                "level": "1",
                "beta": "0.5",
                "se": "0.2",
                "evidence_tier": "dataset_derived",
            },
        ],
        "artifacts": {
            evidence_decisions.POOLED_DATASET: artifacts or pooled_fever_artifacts(),
        },
    }


def pooled_final_model_bundle() -> dict:
    terms = [
        ("intercept", "", "-2.4", "0.18"),
        ("age_centered", "per_1_year_centered_at_42", "0.04", "0.006"),
        ("pain_bin3", "mild", "0.2", "0.3"),
        ("pain_bin3", "severe", "0.7", "0.2"),
        ("pain_missing", "1", "0.7", "0.2"),
        ("fever_or_temp", "1", "1.2", "0.5"),
    ]
    return {
        "coefficients": [
            {
                "dataset": evidence_decisions.POOLED_DATASET,
                "model_id": evidence_decisions.POOLED_FEVER_EXPORT_MODEL,
                "source_model_id": evidence_decisions.POOLED_FEVER_SOURCE_MODEL,
                "term": term,
                "level": level,
                "beta": beta,
                "se": se,
                "evidence_tier": "survey_weighted_candidate",
            }
            for term, level, beta, se in terms
        ],
        "final_term_decisions": [
            {
                "dataset": evidence_decisions.POOLED_DATASET,
                "model_id": evidence_decisions.POOLED_FEVER_EXPORT_MODEL,
                "source_model_id": evidence_decisions.POOLED_FEVER_SOURCE_MODEL,
                "term": term,
                "level": level,
                "assigned_evidence_tier": "dataset_derived",
                "blockers": "",
            }
            for term, level, _beta, _se in terms
        ],
        "artifacts": {
            evidence_decisions.POOLED_DATASET: pooled_fever_artifacts(),
        },
    }


def pooled_vomiting_artifacts(
    *,
    mapping: bool = True,
    vomiting_mapping: bool = True,
    gate_status: str = "eligible_for_evidence_promotion",
    draw_count: int = 10000,
    covariance: bool = True,
) -> dict:
    artifacts = pooled_fever_artifacts(mapping=mapping)
    if covariance:
        artifacts["covariance_models"] = {
            evidence_decisions.POOLED_FEVER_EXPORT_MODEL,
            evidence_decisions.POOLED_VOMITING_EXPORT_MODEL,
        }
    else:
        artifacts["covariance_models"] = set()
    artifacts["draw_models"] = {evidence_decisions.POOLED_VOMITING_EXPORT_MODEL} if draw_count else set()
    artifacts["draw_counts"] = {evidence_decisions.POOLED_VOMITING_EXPORT_MODEL: draw_count}
    artifacts["vomiting_gate_status"] = gate_status
    artifacts["vomiting_mapping"] = vomiting_mapping
    artifacts["vomiting_counts"] = True
    return artifacts


def pooled_vomiting_bundle(artifacts: dict | None = None, vomiting_beta: float = 0.4) -> dict:
    base_terms = [
        ("intercept", "", "-2.4", "0.18"),
        ("age_centered", "per_1_year_centered_at_42", "0.04", "0.006"),
        ("pain_bin3", "mild", "0.2", "0.3"),
        ("pain_bin3", "severe", "0.7", "0.2"),
        ("pain_missing", "1", "0.7", "0.2"),
        ("fever_or_temp", "1", "1.2", "0.5"),
        ("vomiting_present", "1", str(vomiting_beta), "0.1"),
    ]
    final_terms = [term for term in base_terms if term[0] != "vomiting_present"]
    return {
        "coefficients": [
            {
                "dataset": evidence_decisions.POOLED_DATASET,
                "model_id": evidence_decisions.POOLED_VOMITING_EXPORT_MODEL,
                "source_model_id": evidence_decisions.POOLED_VOMITING_SOURCE_MODEL,
                "term": term,
                "level": level,
                "beta": beta,
                "se": se,
                "evidence_tier": "survey_weighted_candidate",
            }
            for term, level, beta, se in base_terms
        ],
        "final_term_decisions": [
            {
                "dataset": evidence_decisions.POOLED_DATASET,
                "model_id": evidence_decisions.POOLED_FEVER_EXPORT_MODEL,
                "source_model_id": evidence_decisions.POOLED_FEVER_SOURCE_MODEL,
                "term": term,
                "level": level,
                "assigned_evidence_tier": "dataset_derived",
                "blockers": "",
            }
            for term, level, _beta, _se in final_terms
        ],
        "artifacts": {
            evidence_decisions.POOLED_DATASET: artifacts or pooled_vomiting_artifacts(),
        },
    }


def pooled_hematemesis_artifacts(
    *,
    mapping: bool = True,
    hematemesis_mapping: bool = True,
    gate_status: str = "eligible_for_evidence_promotion",
    draw_count: int = 10000,
    covariance: bool = True,
) -> dict:
    artifacts = pooled_vomiting_artifacts(mapping=mapping)
    if covariance:
        artifacts["covariance_models"] = {
            evidence_decisions.POOLED_FEVER_EXPORT_MODEL,
            evidence_decisions.POOLED_VOMITING_EXPORT_MODEL,
            evidence_decisions.POOLED_HEMATEMESIS_EXPORT_MODEL,
        }
    else:
        artifacts["covariance_models"] = set()
    artifacts["draw_models"] = {evidence_decisions.POOLED_HEMATEMESIS_EXPORT_MODEL} if draw_count else set()
    artifacts["draw_counts"] = {
        evidence_decisions.POOLED_VOMITING_EXPORT_MODEL: 10000,
        evidence_decisions.POOLED_HEMATEMESIS_EXPORT_MODEL: draw_count,
    }
    artifacts["hematemesis_gate_status"] = gate_status
    artifacts["hematemesis_mapping"] = hematemesis_mapping
    artifacts["hematemesis_counts"] = True
    return artifacts


def pooled_hematemesis_bundle(artifacts: dict | None = None, hematemesis_beta: float = 0.8) -> dict:
    terms = [
        ("intercept", "", "-2.4", "0.18"),
        ("age_centered", "per_1_year_centered_at_42", "0.04", "0.006"),
        ("pain_bin3", "mild", "0.2", "0.3"),
        ("pain_bin3", "severe", "0.7", "0.2"),
        ("pain_missing", "1", "0.7", "0.2"),
        ("fever_or_temp", "1", "1.2", "0.5"),
        ("vomiting_present", "1", "0.4", "0.1"),
        ("hematemesis_present", "1", str(hematemesis_beta), "0.4"),
    ]
    final_terms = [term for term in terms if term[0] not in {"vomiting_present", "hematemesis_present"}]
    return {
        "coefficients": [
            {
                "dataset": evidence_decisions.POOLED_DATASET,
                "model_id": evidence_decisions.POOLED_HEMATEMESIS_EXPORT_MODEL,
                "source_model_id": evidence_decisions.POOLED_HEMATEMESIS_SOURCE_MODEL,
                "term": term,
                "level": level,
                "beta": beta,
                "se": se,
                "evidence_tier": "survey_weighted_candidate",
            }
            for term, level, beta, se in terms
        ],
        "final_term_decisions": [
            {
                "dataset": evidence_decisions.POOLED_DATASET,
                "model_id": evidence_decisions.POOLED_FEVER_EXPORT_MODEL,
                "source_model_id": evidence_decisions.POOLED_FEVER_SOURCE_MODEL,
                "term": term,
                "level": level,
                "assigned_evidence_tier": "dataset_derived",
                "blockers": "",
            }
            for term, level, _beta, _se in final_terms
        ],
        "artifacts": {
            evidence_decisions.POOLED_DATASET: artifacts or pooled_hematemesis_artifacts(),
        },
    }


class EvidenceDecisionTests(unittest.TestCase):
    def decide(self, rates, coeffs=None, cal=None, miss=None):
        return pain_monotonicity.decide_pain(
            rates,
            coeffs if coeffs is not None else coefficients(),
            cal if cal is not None else calibration_rows(),
            miss if miss is not None else missingness(),
        )

    def test_monotonic_rates_positive_coefficients_passes(self) -> None:
        result = self.decide(pain_rates((0.10, 0.15, 0.25)))
        self.assertEqual(result["verdict"], "monotonic_dataset_derived")

    def test_nonmonotonic_rates_fail(self) -> None:
        result = self.decide(pain_rates((0.20, 0.10, 0.25)))
        self.assertEqual(result["verdict"], "nonmonotonic_flexible_only")

    def test_nhamcs_rates_prefer_weighted_counts_when_available(self) -> None:
        rows = pain_rates((0.20, 0.10, 0.25))
        weighted = [(10, 100), (15, 100), (25, 100)]
        for row, (events, total) in zip(rows, weighted):
            row["weighted_events"] = str(events)
            row["weighted_n"] = str(total)
        result = self.decide(rows)
        self.assertEqual(result["nhamcs_pain_rates_status"], "nondecreasing")

    def test_positive_unadjusted_negative_adjusted_is_confounded_or_unstable(self) -> None:
        result = self.decide(pain_rates((0.10, 0.15, 0.25)), coeffs=coefficients(continuous=0.4, acuity=-0.2))
        self.assertEqual(result["verdict"], "dataset_derived_weak_severity_proxy")

    def test_severe_less_than_moderate_fails_monotonic_claim(self) -> None:
        result = self.decide(pain_rates((0.10, 0.15, 0.25)), coeffs=coefficients(severe=-0.1))
        self.assertEqual(result["verdict"], "nonmonotonic_flexible_only")

    def test_nhamcs_adjusted_order_ignores_mimic_coefficients(self) -> None:
        coeffs = coefficients()
        coeffs.append(
            {
                "dataset": "MIMIC_IV_ED",
                "model_id": "A_reduced_categorical",
                "term": "pain_bin3",
                "level": "severe",
                "beta": "-2.0",
                "se": "0.1",
                "evidence_tier": "mimic_replication_only",
            }
        )
        result = self.decide(pain_rates((0.10, 0.15, 0.25)), coeffs=coeffs)
        self.assertEqual(result["adjusted_order_ok"], "true")

    def test_missingness_too_high_blocks_promotion(self) -> None:
        result = self.decide(pain_rates((0.10, 0.15, 0.25)), miss=missingness(60.0))
        self.assertEqual(result["verdict"], "missingness_invalidates_inference")

    def test_bad_calibration_blocks_promotion(self) -> None:
        result = self.decide(pain_rates((0.10, 0.15, 0.25)), cal=calibration_rows(slope=0.6))
        self.assertEqual(result["verdict"], "null_or_unstable")

    def test_evidence_tier_requires_uncertainty_for_dataset_derived(self) -> None:
        bundle = {
            "coefficients": [
                {
                    "dataset": "NHAMCS_2022",
                    "model_id": "A_reduced_categorical",
                    "term": "age_band",
                    "level": "45_54",
                    "beta": "0.2",
                    "se": "",
                    "evidence_tier": "dataset_derived",
                }
            ],
            "artifacts": {
                "NHAMCS_2022": {
                    "cohort": True,
                    "endpoint": True,
                    "mapping": True,
                    "counts": True,
                    "missingness": True,
                    "covariance_models": set(),
                    "draw_models": set(),
                }
            },
        }
        assignments = evidence_decisions.assign_evidence_tiers(
            bundle,
            {"verdict": "monotonic_dataset_derived"},
            [{"dataset": "NHAMCS_2022", "model_id": "A_reduced_categorical", "calibration_status": "pass"}],
        )
        self.assertNotEqual(assignments[0]["assigned_evidence_tier"], "dataset_derived")
        self.assertIn("missing_uncertainty", assignments[0]["blockers"])

    def test_evidence_tier_preserves_dataset_derived_only_after_gates(self) -> None:
        bundle = {
            "coefficients": [
                {
                    "dataset": "NHAMCS_2022",
                    "model_id": "A_reduced_categorical",
                    "term": "age_band",
                    "level": "45_54",
                    "beta": "0.2",
                    "se": "0.1",
                    "evidence_tier": "dataset_derived",
                }
            ],
            "artifacts": {
                "NHAMCS_2022": {
                    "cohort": True,
                    "endpoint": True,
                    "mapping": True,
                    "counts": True,
                    "missingness": True,
                    "covariance_models": set(),
                    "draw_models": set(),
                }
            },
        }
        assignments = evidence_decisions.assign_evidence_tiers(
            bundle,
            {"verdict": "monotonic_dataset_derived"},
            [{"dataset": "NHAMCS_2022", "model_id": "A_reduced_categorical", "calibration_status": "pass"}],
        )
        self.assertEqual(assignments[0]["assigned_evidence_tier"], "dataset_derived")

    def test_pooled_fever_gate_promotes_only_objective_fever(self) -> None:
        assignments = evidence_decisions.assign_evidence_tiers(
            pooled_fever_bundle(),
            {"verdict": "nonmonotonic_flexible_only"},
            [
                {
                    "dataset": evidence_decisions.POOLED_DATASET,
                    "model_id": evidence_decisions.POOLED_FEVER_EXPORT_MODEL,
                    "calibration_status": "pass",
                }
            ],
        )
        fever = next(row for row in assignments if row["term"] == "fever_or_temp")
        pain = next(row for row in assignments if row["term"] == "pain_bin3")
        vomiting = next(row for row in assignments if row["term"] == "vomiting")
        self.assertEqual(fever["assigned_evidence_tier"], "dataset_derived")
        self.assertEqual(pain["assigned_evidence_tier"], "survey_weighted_candidate")
        self.assertNotEqual(vomiting["assigned_evidence_tier"], "dataset_derived")

    def test_pooled_fever_mapping_block_yields_candidate_only(self) -> None:
        assignments = evidence_decisions.assign_evidence_tiers(
            pooled_fever_bundle(pooled_fever_artifacts(mapping=False)),
            {"verdict": "nonmonotonic_flexible_only"},
            [
                {
                    "dataset": evidence_decisions.POOLED_DATASET,
                    "model_id": evidence_decisions.POOLED_FEVER_EXPORT_MODEL,
                    "calibration_status": "pass",
                }
            ],
        )
        fever = next(row for row in assignments if row["term"] == "fever_or_temp")
        self.assertEqual(fever["assigned_evidence_tier"], "dataset_derived_candidate")
        self.assertIn("mapping_not_confirmed", fever["blockers"])

    def test_pooled_fever_gate_or_missing_draws_blocks_promotion(self) -> None:
        for artifacts in [
            pooled_fever_artifacts(gate_status="sensitivity_only"),
            pooled_fever_artifacts(draw_count=0, covariance=False),
        ]:
            assignments = evidence_decisions.assign_evidence_tiers(
                pooled_fever_bundle(artifacts),
                {"verdict": "nonmonotonic_flexible_only"},
                [
                    {
                        "dataset": evidence_decisions.POOLED_DATASET,
                        "model_id": evidence_decisions.POOLED_FEVER_EXPORT_MODEL,
                        "calibration_status": "pass",
                    }
                ],
            )
            fever = next(row for row in assignments if row["term"] == "fever_or_temp")
            self.assertNotEqual(fever["assigned_evidence_tier"], "dataset_derived")

    def test_pooled_final_gate_promotes_flexible_pain_and_activation(self) -> None:
        bundle = pooled_final_model_bundle()
        assignments = evidence_decisions.assign_evidence_tiers(
            bundle,
            {"verdict": "nonmonotonic_flexible_only"},
            [
                {
                    "dataset": evidence_decisions.POOLED_DATASET,
                    "model_id": evidence_decisions.POOLED_FEVER_EXPORT_MODEL,
                    "calibration_status": "pass",
                }
            ],
        )
        target = evidence_decisions.target_evidence_rows(assignments)
        self.assertEqual(len(target), 6)
        self.assertTrue(all(row["assigned_evidence_tier"] == "dataset_derived" for row in target))
        self.assertEqual(
            evidence_decisions.flexible_pain_promotion_status(
                {"verdict": "nonmonotonic_flexible_only"},
                assignments,
            ),
            "flexible_nonmonotonic_dataset_derived",
        )
        activation = evidence_decisions.final_activation_decision(bundle, assignments)[0]
        self.assertEqual(activation["activation_status"], "eligible_for_educational_activation")

    def test_pooled_vomiting_gate_promotes_binary_vomiting_and_activation(self) -> None:
        bundle = pooled_vomiting_bundle()
        assignments = evidence_decisions.assign_evidence_tiers(
            bundle,
            {"verdict": "nonmonotonic_flexible_only"},
            [
                {
                    "dataset": evidence_decisions.POOLED_DATASET,
                    "model_id": evidence_decisions.POOLED_VOMITING_EXPORT_MODEL,
                    "calibration_status": "pass",
                }
            ],
        )
        vomiting = next(row for row in assignments if row["term"] == "vomiting_present")
        self.assertEqual(vomiting["assigned_evidence_tier"], "dataset_derived")
        target = evidence_decisions.vomiting_target_evidence_rows(assignments)
        self.assertEqual(len(target), 7)
        self.assertTrue(all(row["assigned_evidence_tier"] == "dataset_derived" for row in target))
        activation = evidence_decisions.vomiting_expanded_activation_decision(bundle, assignments)[0]
        self.assertEqual(activation["activation_status"], "eligible_for_educational_activation")

    def test_pooled_vomiting_gate_blocks_sensitivity_only_or_mapping_gap(self) -> None:
        for artifacts, expected_blocker in [
            (pooled_vomiting_artifacts(gate_status="sensitivity_only"), "vomiting_gate_sensitivity_only"),
            (pooled_vomiting_artifacts(vomiting_mapping=False), "vomiting_mapping_not_confirmed"),
            (pooled_vomiting_artifacts(draw_count=0, covariance=False), "missing_10000_mvn_draws"),
        ]:
            assignments = evidence_decisions.assign_evidence_tiers(
                pooled_vomiting_bundle(artifacts),
                {"verdict": "nonmonotonic_flexible_only"},
                [
                    {
                        "dataset": evidence_decisions.POOLED_DATASET,
                        "model_id": evidence_decisions.POOLED_VOMITING_EXPORT_MODEL,
                        "calibration_status": "pass",
                    }
                ],
            )
            vomiting = next(row for row in assignments if row["term"] == "vomiting_present")
            self.assertNotEqual(vomiting["assigned_evidence_tier"], "dataset_derived")
            self.assertIn(expected_blocker, vomiting["blockers"])

    def test_pooled_vomiting_negative_beta_blocks_promotion(self) -> None:
        assignments = evidence_decisions.assign_evidence_tiers(
            pooled_vomiting_bundle(vomiting_beta=-0.1),
            {"verdict": "nonmonotonic_flexible_only"},
            [
                {
                    "dataset": evidence_decisions.POOLED_DATASET,
                    "model_id": evidence_decisions.POOLED_VOMITING_EXPORT_MODEL,
                    "calibration_status": "pass",
                }
            ],
        )
        vomiting = next(row for row in assignments if row["term"] == "vomiting_present")
        self.assertIn("vomiting_beta_not_positive", vomiting["blockers"])

    def test_pooled_hematemesis_gate_promotes_only_when_all_gates_pass(self) -> None:
        assignments = evidence_decisions.assign_evidence_tiers(
            pooled_hematemesis_bundle(),
            {"verdict": "nonmonotonic_flexible_only"},
            [
                {
                    "dataset": evidence_decisions.POOLED_DATASET,
                    "model_id": evidence_decisions.POOLED_HEMATEMESIS_EXPORT_MODEL,
                    "calibration_status": "pass",
                }
            ],
        )
        hematemesis = next(row for row in assignments if row["term"] == "hematemesis_present")
        self.assertEqual(hematemesis["assigned_evidence_tier"], "dataset_derived")
        target = evidence_decisions.hematemesis_target_evidence_rows(assignments)
        self.assertEqual(len(target), 8)
        self.assertTrue(all(row["assigned_evidence_tier"] == "dataset_derived" for row in target))
        activation = evidence_decisions.hematemesis_expanded_activation_decision(pooled_hematemesis_bundle(), assignments)[0]
        self.assertEqual(activation["activation_status"], "eligible_for_educational_activation")

    def test_pooled_hematemesis_gate_blocks_sparse_or_mapping_gap(self) -> None:
        for artifacts, expected_blocker in [
            (pooled_hematemesis_artifacts(gate_status="sensitivity_only"), "hematemesis_gate_sensitivity_only"),
            (pooled_hematemesis_artifacts(hematemesis_mapping=False), "hematemesis_mapping_not_confirmed"),
            (pooled_hematemesis_artifacts(draw_count=0, covariance=False), "missing_10000_mvn_draws"),
        ]:
            assignments = evidence_decisions.assign_evidence_tiers(
                pooled_hematemesis_bundle(artifacts),
                {"verdict": "nonmonotonic_flexible_only"},
                [
                    {
                        "dataset": evidence_decisions.POOLED_DATASET,
                        "model_id": evidence_decisions.POOLED_HEMATEMESIS_EXPORT_MODEL,
                        "calibration_status": "pass",
                    }
                ],
            )
            hematemesis = next(row for row in assignments if row["term"] == "hematemesis_present")
            self.assertNotEqual(hematemesis["assigned_evidence_tier"], "dataset_derived")
            self.assertIn(expected_blocker, hematemesis["blockers"])

    def test_pooled_hematemesis_negative_beta_blocks_promotion(self) -> None:
        assignments = evidence_decisions.assign_evidence_tiers(
            pooled_hematemesis_bundle(hematemesis_beta=-0.1),
            {"verdict": "nonmonotonic_flexible_only"},
            [
                {
                    "dataset": evidence_decisions.POOLED_DATASET,
                    "model_id": evidence_decisions.POOLED_HEMATEMESIS_EXPORT_MODEL,
                    "calibration_status": "pass",
                }
            ],
        )
        hematemesis = next(row for row in assignments if row["term"] == "hematemesis_present")
        self.assertIn("hematemesis_beta_not_positive", hematemesis["blockers"])


if __name__ == "__main__":
    unittest.main()
