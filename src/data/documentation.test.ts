import assert from "node:assert/strict"
import test from "node:test"

import {
  containsProhibitedClinicalClaim,
  demoBoundaryCopy,
  documentationPages,
  modelCardRows,
} from "./documentation"
import { activeEmpiricalModel } from "./eDispoV4Model"
import {
  coefficientArtifactStatus,
  shouldUsePooledEmpiricalModel,
  shouldUseEmpiricalCoefficients,
  validateCoefficientArtifact,
  validatePooledEmpiricalModelArtifact,
} from "./empiricalArtifacts"
import type { NhamcsCoefficientArtifact } from "./empiricalArtifacts"
import { pooledEmpiricalModel } from "./pooledEmpiricalModel"
import { literatureSources } from "./sources"
import { endpointRows } from "../model/endpoint"

const requiredDocumentationPages = [
  "overview",
  "model-card",
  "parameter-evidence",
  "endpoint-recoding",
  "nhamcs-appendix",
  "uncertainty-method",
  "bias-applicability",
  "reporting-checklist",
  "qa-evidence",
  "sources",
]

test("documentation section exposes the required page inventory", () => {
  assert.deepEqual(
    documentationPages.map((page) => page.id),
    requiredDocumentationPages
  )
  assert.ok(documentationPages.every((page) => page.label.length > 0))
  assert.ok(documentationPages.every((page) => page.description.length > 0))
})

test("source links are present and externally navigable", () => {
  assert.ok(literatureSources.length >= 6)

  for (const source of literatureSources) {
    const url = new URL(source.url)
    assert.match(url.protocol, /^https?:$/)
    assert.ok(source.label.length > 0)
    assert.ok(source.note.length > 0)
  }
})

test("coefficient artifact schema validates a derived NHAMCS artifact", () => {
  const validArtifact: NhamcsCoefficientArtifact = {
    schemaVersion: "2.0.0",
    artifactKind: "nhamcs_validation_model_fit",
    sourceDataset: "NHAMCS 2018-2022 pooled ED public-use files",
    derivedAt: "2026-04-28",
    modelVersion: "v3.1-validation-baseline",
    endpointSpecVersion: "endpoint_refined_v3_2026-04-28",
    configHash: "abc123",
    generatedBy: "scripts/modeling/final_export.py",
    modelName: "pooled_empirical_v1_age_pain_fever",
    cohortFlow: [{ step: "Eligible ED visits", count: 1000, weightedCount: 9000 }],
    surveyDesign: {
      weightVariable: "PATWT",
      strataVariable: "CSTRATM",
      psuVariable: "CPSUM",
      recordCount: 1000,
      weightedCount: 9000,
      effectiveSampleSizeApprox: 700,
      varianceImplementation: "Weighted counts only.",
    },
    endpointCounts: {
      admit: 220,
      treatAndRelease: 700,
      excluded: 80,
      excludedObservationDischarged: 15,
      excludedTransfer: 20,
      excludedSentinelDeath: 2,
      excludedNonroutineExit: 18,
      excludedOtherUnknown: 17,
      excludedConflict: 8,
      weighted: {
        admit: 1980,
        treatAndRelease: 6300,
        excluded: 720,
        excludedObservationDischarged: 135,
        excludedTransfer: 180,
        excludedSentinelDeath: 18,
        excludedNonroutineExit: 162,
        excludedOtherUnknown: 153,
        excludedConflict: 72,
      },
    },
    sensitivityEndpointCounts: {
      endpointSensAEventualHome: {
        admit: 220,
        treatAndRelease: 715,
        excluded: 65,
        weighted: {
          admit: 1980,
          treatAndRelease: 6435,
          excluded: 585,
        },
      },
      endpointSensBAcuteEscalation: {
        acuteEscalationPositive: 240,
        treatAndRelease: 715,
        excluded: 45,
        weighted: {
          acuteEscalationPositive: 2160,
          treatAndRelease: 6435,
          excluded: 405,
        },
      },
    },
    coefficients: [
      {
        key: "intercept",
        mean: -1.25,
        standardError: 0.18,
        ci95Low: -1.6,
        ci95High: -0.9,
        source: "nhamcs_pooled_2018_2022",
      },
    ],
    coefficientCovariance: {
      columns: ["intercept"],
      matrix: [[0.0324]],
    },
    performanceMetrics: {
      auc: 0.7,
      brierScore: 0.16,
      calibrationIntercept: 0,
      calibrationSlope: 1,
      outcome: "endpoint_primary_v3_refined",
      positiveLabel: "ADMIT",
      sampleSize: 100,
      excludedForMissingPredictors: 5,
      eventCount: 20,
      nonEventCount: 80,
      outcomePrevalence: 0.2,
      weightedBinaryCount: 900,
    },
    internalValidation: {
      method: "bootstrap_apparent_refit_on_original",
      iterationsRequested: 100,
      iterationsCompleted: 100,
      randomSeed: 20260428,
      aucMedian: 0.69,
      aucP025: 0.6,
      aucP975: 0.77,
      brierMedian: 0.17,
      brierP025: 0.15,
      brierP975: 0.2,
      limitation: "Does not implement full survey-design variance.",
    },
    sensitivityAnalyses: [
      {
        outcome: "endpoint_primary_v3_refined",
        sampleSize: 100,
        eventCount: 20,
        outcomePrevalence: 0.2,
        auc: 0.7,
        brierScore: 0.16,
        calibrationIntercept: 0,
        calibrationSlope: 1,
      },
      {
        outcome: "endpoint_sens_A_eventual_home",
        sampleSize: 105,
        eventCount: 20,
        outcomePrevalence: 0.190476,
        auc: 0.7,
        brierScore: 0.16,
        calibrationIntercept: 0,
        calibrationSlope: 1,
      },
      {
        outcome: "endpoint_sens_B_acute_escalation",
        sampleSize: 110,
        eventCount: 25,
        outcomePrevalence: 0.227273,
        auc: 0.71,
        brierScore: 0.17,
        calibrationIntercept: 0,
        calibrationSlope: 1,
      },
    ],
    predictorMapping: [
      {
        variable: "age",
        support: "direct",
        fitStatus: "included_in_reduced_empirical_fit",
        note: "Exact age is available as a direct public-use field.",
      },
      {
        variable: "broadPainRegion",
        support: "weak_proxy",
        fitStatus: "excluded_from_reduced_empirical_fit",
        note: "RFV supports abdominal pain but not detailed region.",
      },
      {
        variable: "painSeverity",
        support: "direct",
        fitStatus: "included_in_reduced_empirical_fit",
        note: "PAINSCALE can be grouped into severity bands.",
      },
      {
        variable: "onsetDurationCategory",
        support: "unavailable",
        fitStatus: "prototype_only",
        note: "Not available in the public-use file.",
      },
      {
        variable: "constantVsIntermittent",
        support: "unavailable",
        fitStatus: "prototype_only",
        note: "Not available in the public-use file.",
      },
      {
        variable: "vomiting",
        support: "proxy",
        fitStatus: "excluded_from_reduced_empirical_fit",
        note: "Requires explicit symptom proxy mapping.",
      },
      {
        variable: "fever",
        support: "proxy",
        fitStatus: "excluded_from_reduced_empirical_fit",
        note: "Requires explicit symptom proxy mapping.",
      },
    ],
    limitations: ["Some symptom predictors remain proxy-based or unavailable."],
  }

  const result = validateCoefficientArtifact(validArtifact)
  assert.equal(result.valid, true)
  assert.equal(result.label, "NHAMCS-derived coefficients active")
})

test("pooled empirical app export validates and activates", () => {
  const result = validatePooledEmpiricalModelArtifact(activeEmpiricalModel)

  assert.equal(result.valid, true)
  assert.equal(result.label, "Pooled NHAMCS-derived coefficients active")
  assert.equal(shouldUseEmpiricalCoefficients(activeEmpiricalModel), true)
  assert.equal(shouldUsePooledEmpiricalModel(activeEmpiricalModel), true)
  assert.deepEqual(
    activeEmpiricalModel.performance_intervals?.map((row) => row.metric).sort(),
    ["auroc", "brier_score"]
  )
  assert.ok(
    activeEmpiricalModel.performance_intervals?.every(
      (row) =>
        row.method ===
          "survey_bootstrap_replicate_weights_fixed_apparent_predictions" &&
        row.limitation.includes("does not refit")
    )
  )
})

test("prior v2 pooled empirical export remains valid as archived evidence", () => {
  const result = validatePooledEmpiricalModelArtifact(pooledEmpiricalModel)

  assert.equal(result.valid, true)
  assert.equal(shouldUsePooledEmpiricalModel(pooledEmpiricalModel), true)
})

test("coefficient artifact gate rejects incomplete empirical artifacts", () => {
  const incompleteArtifact = {
    schemaVersion: "1.0.0",
    sourceDataset: "NHAMCS 2022 ED public-use file",
    derivedAt: "2026-04-28",
    cohortFlow: [{ step: "Eligible ED visits", count: 1000 }],
    endpointCounts: {
      admit: 220,
      treatAndRelease: 700,
      excluded: 80,
      excludedObservationDischarged: 15,
      excludedTransfer: 20,
      excludedSentinelDeath: 2,
      excludedNonroutineExit: 18,
      excludedOtherUnknown: 17,
      excludedConflict: 8,
    },
    coefficients: [
      {
        key: "intercept",
        mean: -1.25,
        standardError: 0.18,
        source: "nhamcs_2022",
      },
    ],
    predictorMapping: [],
    limitations: ["Missing validation-grade fields."],
  }

  const result = validateCoefficientArtifact(incompleteArtifact)
  assert.equal(result.valid, false)
  assert.equal(result.label, "Prototype assumptions active")
  assert.ok(result.issues.some((issue) => issue.includes("schemaVersion")))
  assert.equal(shouldUseEmpiricalCoefficients(incompleteArtifact), false)
})

test("missing or invalid pooled empirical app exports block activation", () => {
  assert.equal(shouldUsePooledEmpiricalModel(null), false)
  assert.equal(
    shouldUsePooledEmpiricalModel({
      ...activeEmpiricalModel,
      model_id: "wrong_model",
    }),
    false
  )
  assert.equal(
    shouldUsePooledEmpiricalModel({
      ...activeEmpiricalModel,
      predictors: activeEmpiricalModel.predictors.filter(
        (row) => row.term !== "tachycardia_burden"
      ),
    }),
    false
  )
  assert.equal(
    shouldUsePooledEmpiricalModel({
      ...activeEmpiricalModel,
      performance_intervals: activeEmpiricalModel.performance_intervals?.map((row) =>
        row.metric === "auroc" ? { ...row, ci_low: row.estimate + 0.01 } : row
      ),
    }),
    false
  )
  assert.equal(
    shouldUsePooledEmpiricalModel({
      ...activeEmpiricalModel,
      predictor_evidence_tiers: [
        ...activeEmpiricalModel.predictor_evidence_tiers,
        {
          blockers: "",
          evidence_tier: "dataset_derived",
          level: "1",
          term: "pain_missing",
        },
      ],
    }),
    false
  )
})

test("app defaults to the validated pooled empirical labels", () => {
  assert.equal(coefficientArtifactStatus.valid, true)
  assert.equal(
    coefficientArtifactStatus.label,
    "Pooled NHAMCS-derived coefficients active"
  )
  assert.equal(shouldUseEmpiricalCoefficients(), true)
})

test("demo boundary copy avoids positive clinical-validity claims", () => {
  const combinedCopy = demoBoundaryCopy.join(" ")
  assert.equal(containsProhibitedClinicalClaim(combinedCopy), false)
})

test("endpoint-refined v3 language is present in documentation data", () => {
  const modelCardText = modelCardRows.map((row) => row.value).join(" ")
  assert.match(modelCardText, /same-hospital hospitalization\/admission/)
  assert.match(modelCardText, /Observation -> discharged/)
  assert.match(modelCardText, /conflicting dispositions/)

  const endpointTableText = endpointRows
    .map((row) => `${row.source} ${row.model} ${row.action}`)
    .join(" ")
  assert.match(endpointTableText, /observation -> hospitalized/i)
  assert.match(endpointTableText, /Sensitivity A\/B/)
})
