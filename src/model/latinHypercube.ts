import { logistic } from "./logisticModel";
import { modelMetadata } from "./modelParameters";
import type { PooledEmpiricalCoefficientDraw } from "@/data/pooledEmpiricalCoefficientDraws";
import {
  type GeneralHomeModelId,
  isGeneralEDispoModelId,
} from "@/data/generalEDispoModel";
import type {
  GeneralModelInputs,
  HistogramBin,
  LogisticTerm,
  ModelInputs,
  RunnableModelId,
  SensitivityResult,
  SimulationResult,
} from "./types";
import {
  activeGeneralEDispoTermsForInputs,
  hypotensionBurdenFromSbp,
} from "./generalEDispoPrediction";
import {
  activePooledEmpiricalTermsForInputs,
  tachycardiaBurdenFromHeartRate,
  toPooledEmpiricalPredictionInputs,
  type PooledEmpiricalPredictionInputs,
} from "./pooledEmpiricalPrediction";

interface SampledTerm {
  label: string;
  values: number[];
}

type SimulationCoefficientInputs =
  | {
      modelId: "e-dispo-v4.1-pas5-high-acuity-surrogate";
      pooledInputs: PooledEmpiricalPredictionInputs;
      generalInputs?: never;
    }
  | {
      modelId: GeneralHomeModelId;
      pooledInputs?: never;
      generalInputs: GeneralModelInputs;
    };

type RunLatinHypercubeSimulationOptions = {
  modelId?: RunnableModelId;
  generalInputs?: GeneralModelInputs;
};

export function runLatinHypercubeSimulation(
  inputs: ModelInputs,
  sampleCount = modelMetadata.sampleCount,
  seed = modelMetadata.seed,
  age = 42,
  heartRateBpm: number | null = 88,
  coefficientDraws: PooledEmpiricalCoefficientDraw[] = [],
  options: RunLatinHypercubeSimulationOptions = {},
): SimulationResult {
  if (options.modelId && isGeneralEDispoModelId(options.modelId)) {
    if (!options.generalInputs) {
      throw new Error("General model inputs are required for the general E-Dispo simulation.");
    }

    const activeTerms = activeGeneralEDispoTermsForInputs(options.generalInputs);
    if (coefficientDraws.length > 0) {
      return runJointCoefficientDrawSimulation(
        activeTerms,
        {
          modelId: options.modelId,
          generalInputs: options.generalInputs,
        },
        sampleCount,
        seed,
        coefficientDraws,
      );
    }

    return runIndependentNormalApproximationSimulation(
      activeTerms,
      sampleCount,
      seed,
    );
  }

  const pooledInputs = toPooledEmpiricalPredictionInputs(
    inputs,
    age,
    heartRateBpm,
  );
  const activeTerms = activePooledEmpiricalTermsForInputs(pooledInputs);

  if (coefficientDraws.length > 0) {
    return runJointCoefficientDrawSimulation(
      activeTerms,
      {
        modelId: "e-dispo-v4.1-pas5-high-acuity-surrogate",
        pooledInputs,
      },
      sampleCount,
      seed,
      coefficientDraws,
    );
  }

  return runIndependentNormalApproximationSimulation(
    activeTerms,
    sampleCount,
    seed,
  );
}

function runJointCoefficientDrawSimulation(
  activeTerms: LogisticTerm[],
  inputs: SimulationCoefficientInputs,
  sampleCount: number,
  seed: number,
  coefficientDraws: PooledEmpiricalCoefficientDraw[],
): SimulationResult {
  const sampledDraws = sampleCoefficientDraws(coefficientDraws, sampleCount, seed);
  const sampledTerms = activeTerms.map((term) => ({
    label: term.label,
    values: sampledDraws.map((draw) =>
      coefficientContributionForTerm(term, draw, inputs),
    ),
  }));

  return buildSimulationResult(sampledTerms, sampleCount, seed);
}

// Fallback only: this exploratory approximation ignores coefficient covariance.
function runIndependentNormalApproximationSimulation(
  activeTerms: LogisticTerm[],
  sampleCount: number,
  seed: number,
): SimulationResult {
  const sampledTerms = activeTerms.map((term, index) =>
    sampleTerm(term, sampleCount, seed + index * 7919),
  );

  return buildSimulationResult(sampledTerms, sampleCount, seed);
}

function buildSimulationResult(
  sampledTerms: SampledTerm[],
  sampleCount: number,
  seed: number,
): SimulationResult {
  const probabilities = Array.from(
    { length: sampleCount },
    (_, sampleIndex) => {
      const logit = sampledTerms.reduce(
        (sum, term) => sum + term.values[sampleIndex],
        0,
      );
      return logistic(logit);
    },
  );

  const sorted = [...probabilities].sort((a, b) => a - b);

  return {
    sampleCount,
    seed,
    samples: sorted,
    median: quantileSorted(sorted, 0.5),
    p10: quantileSorted(sorted, 0.1),
    p90: quantileSorted(sorted, 0.9),
    p025: quantileSorted(sorted, 0.025),
    p975: quantileSorted(sorted, 0.975),
    histogram: buildHistogram(probabilities, 16),
    sensitivity: buildSensitivity(sampledTerms, probabilities),
  };
}

function sampleCoefficientDraws(
  draws: PooledEmpiricalCoefficientDraw[],
  sampleCount: number,
  seed: number,
): PooledEmpiricalCoefficientDraw[] {
  if (draws.length === 0) {
    return [];
  }

  const random = mulberry32(seed);
  const strata = Array.from({ length: sampleCount }, (_, index) => {
    const percentile = (index + random()) / sampleCount;
    const drawIndex = Math.min(
      draws.length - 1,
      Math.floor(percentile * draws.length),
    );
    return draws[drawIndex];
  });

  return shuffle(strata, random);
}

function coefficientContributionForTerm(
  term: LogisticTerm,
  draw: PooledEmpiricalCoefficientDraw,
  inputs: SimulationCoefficientInputs,
): number {
  switch (term.key) {
    case "intercept":
      return draw.coefficients.intercept;
    case "age_centered":
      if (isGeneralEDispoModelId(inputs.modelId)) {
        throw new Error("Pooled model inputs are required for age_centered.");
      }
      return draw.coefficients.age_centered * (pooledInputsForDraws(inputs).age - 42);
    case "age_centered_40": {
      if (!isGeneralEDispoModelId(inputs.modelId)) {
        throw new Error("General model inputs are required for age_centered_40.");
      }
      const ageGeneralInputs = generalInputsForDraws(inputs);
      return (
        requiredDrawCoefficient(draw, "age_centered_40", "age_centered_40") *
        (ageGeneralInputs.age - 40)
      );
    }
    case "tachycardia_burden":
      if (heartRateBpmForCoefficientInputs(inputs) === null) {
        throw new Error("Observed heart rate is required for coefficient draws.");
      }
      return (
        draw.coefficients.tachycardia_burden *
        tachycardiaBurdenFromHeartRate(
          heartRateBpmForCoefficientInputs(inputs) as number,
        )
      );
    case "hypotension_burden": {
      if (!isGeneralEDispoModelId(inputs.modelId)) {
        throw new Error("General model inputs are required for hypotension_burden.");
      }
      const sbpGeneralInputs = generalInputsForDraws(inputs);
      return (
        requiredDrawCoefficient(
          draw,
          "hypotension_burden",
          "hypotension_burden",
        ) *
        hypotensionBurdenFromSbp(sbpGeneralInputs.systolicBloodPressure as number)
      );
    }
    case "pain_severe":
      return draw.coefficients.pain_severe;
    case "fever_or_temp":
      return draw.coefficients.fever_or_temp;
    case "vomiting_present":
      return draw.coefficients.vomiting_present;
    case "high_acuity_proxy":
      return requiredDrawCoefficient(
        draw,
        "high_acuity_proxy",
        "high_acuity_proxy",
      );
    case "sex_2":
      return requiredDrawCoefficient(draw, term.key, term.key);
    case "fever_or_temp.unknown_not_activated":
    case "vomiting_present.unknown_not_activated":
      return 0;
    default:
      throw new Error(`No coefficient draw mapping for active term: ${term.key}`);
  }
}

function requiredDrawCoefficient(
  draw: PooledEmpiricalCoefficientDraw,
  key: string,
  label: string,
): number {
  const value = draw.coefficients[key];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`Missing coefficient draw mapping for active term: ${label}`);
  }
  return value;
}

function heartRateBpmForCoefficientInputs(
  inputs: SimulationCoefficientInputs,
): number | null {
  if (isGeneralEDispoModelId(inputs.modelId)) {
    return generalInputsForDraws(inputs).heartRateBpm;
  }

  return pooledInputsForDraws(inputs).heartRateBpm;
}

function generalInputsForDraws(
  inputs: SimulationCoefficientInputs,
): GeneralModelInputs {
  if (!isGeneralEDispoModelId(inputs.modelId) || !inputs.generalInputs) {
    throw new Error("General model inputs are required for coefficient draws.");
  }

  return inputs.generalInputs;
}

function pooledInputsForDraws(
  inputs: SimulationCoefficientInputs,
): PooledEmpiricalPredictionInputs {
  if (isGeneralEDispoModelId(inputs.modelId) || !inputs.pooledInputs) {
    throw new Error("Pooled model inputs are required for coefficient draws.");
  }

  return inputs.pooledInputs;
}

function sampleTerm(
  term: LogisticTerm,
  sampleCount: number,
  seed: number,
): SampledTerm {
  if (term.standardError === 0) {
    return {
      label: term.label,
      values: Array.from({ length: sampleCount }, () => term.mean),
    };
  }

  const random = mulberry32(seed);
  const strata = Array.from({ length: sampleCount }, (_, index) => {
    const percentile = (index + random()) / sampleCount;
    return term.mean + inverseNormal(percentile) * term.standardError;
  });

  return {
    label: term.label,
    values: shuffle(strata, random),
  };
}

function buildHistogram(values: number[], binCount: number): HistogramBin[] {
  const bins = Array.from({ length: binCount }, (_, index) => {
    const lower = index / binCount;
    const upper = (index + 1) / binCount;
    return {
      range: `${Math.round(lower * 100)}-${Math.round(upper * 100)}%`,
      midpoint: (lower + upper) / 2,
      count: 0,
    };
  });

  for (const value of values) {
    const index = Math.min(binCount - 1, Math.floor(value * binCount));
    bins[index].count += 1;
  }

  return bins;
}

function buildSensitivity(
  sampledTerms: SampledTerm[],
  probabilities: number[],
): SensitivityResult[] {
  const probabilityRanks = rank(probabilities);

  return sampledTerms
    .map((term) => {
      const uniqueValues = new Set(term.values).size;
      const correlation =
        uniqueValues <= 1
          ? 0
          : pearsonCorrelation(rank(term.values), probabilityRanks);

      return {
        parameter: term.label,
        correlation,
        absoluteCorrelation: Math.abs(correlation),
      };
    })
    .sort((a, b) => b.absoluteCorrelation - a.absoluteCorrelation);
}

function quantileSorted(sortedValues: number[], percentile: number): number {
  if (sortedValues.length === 0) {
    return 0;
  }

  const index = (sortedValues.length - 1) * percentile;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index - lower;

  if (lower === upper) {
    return sortedValues[lower];
  }

  return sortedValues[lower] * (1 - weight) + sortedValues[upper] * weight;
}

function shuffle<T>(values: T[], random: () => number): T[] {
  const shuffled = [...values];

  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    [shuffled[index], shuffled[swapIndex]] = [
      shuffled[swapIndex],
      shuffled[index],
    ];
  }

  return shuffled;
}

function rank(values: number[]): number[] {
  return values
    .map((value, index) => ({ value, index }))
    .sort((a, b) => a.value - b.value)
    .reduce<number[]>((ranks, item, position) => {
      ranks[item.index] = position + 1;
      return ranks;
    }, []);
}

function pearsonCorrelation(left: number[], right: number[]): number {
  const count = Math.min(left.length, right.length);
  const leftMean = left.reduce((sum, value) => sum + value, 0) / count;
  const rightMean = right.reduce((sum, value) => sum + value, 0) / count;
  let numerator = 0;
  let leftVariance = 0;
  let rightVariance = 0;

  for (let index = 0; index < count; index += 1) {
    const leftDelta = left[index] - leftMean;
    const rightDelta = right[index] - rightMean;
    numerator += leftDelta * rightDelta;
    leftVariance += leftDelta ** 2;
    rightVariance += rightDelta ** 2;
  }

  const denominator = Math.sqrt(leftVariance * rightVariance);
  return denominator === 0 ? 0 : numerator / denominator;
}

function mulberry32(seed: number): () => number {
  let state = seed >>> 0;

  return () => {
    state += 0x6d2b79f5;
    let value = Math.imul(state ^ (state >>> 15), 1 | state);
    value ^= value + Math.imul(value ^ (value >>> 7), 61 | value);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function inverseNormal(probability: number): number {
  const a = [
    -3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2,
    1.38357751867269e2, -3.066479806614716e1, 2.506628277459239,
  ];
  const b = [
    -5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2,
    6.680131188771972e1, -1.328068155288572e1,
  ];
  const c = [
    -7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838,
    -2.549732539343734, 4.374664141464968, 2.938163982698783,
  ];
  const d = [
    7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996,
    3.754408661907416,
  ];
  const lower = 0.02425;
  const upper = 1 - lower;

  if (probability <= 0 || probability >= 1) {
    throw new Error("Probability must be inside (0, 1).");
  }

  if (probability < lower) {
    const q = Math.sqrt(-2 * Math.log(probability));
    return (
      (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    );
  }

  if (probability > upper) {
    const q = Math.sqrt(-2 * Math.log(1 - probability));
    return (
      -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    );
  }

  const q = probability - 0.5;
  const r = q * q;
  return (
    ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) *
      q) /
    (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
  );
}
