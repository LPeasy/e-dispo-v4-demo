/*
 * Metadata and loader helpers for the generated joint coefficient draws.
 * Draw values live beside this module and are resolved through Vite's asset
 * graph so the worker can load them as data without bundling them into app JS.
 */

export const pooledEmpiricalCoefficientDrawAssetUrl = new URL(
  "./pooled-empirical-coefficient-draws.csv",
  import.meta.url
).href

export type PooledEmpiricalCoefficientVector = {
  intercept: number
  age_centered: number
  pain_severe: number
  fever_or_temp: number
  vomiting_present: number
  tachycardia_burden: number
}

export const pooledEmpiricalCoefficientDrawMetadata = {
  modelId: "e-dispo-v4.0",
  source: "NHAMCS_2018_2022_POOLED",
  seed: 20260428,
  drawCount: 10000,
  sourcePath: "outputs/nhamcs_pooled/e_dispo_v4_pain_severe_draws.csv",
  assetPath: pooledEmpiricalCoefficientDrawAssetUrl,
} as const

const expectedCoefficientDrawHeader =
  "draw_id,intercept,age_centered,pain_severe,fever_or_temp,vomiting_present,tachycardia_burden,seed"

const expectedCoefficientKeys = [
  "intercept",
  "age_centered",
  "pain_severe",
  "fever_or_temp",
  "vomiting_present",
  "tachycardia_burden",
] as const

const defaultCoefficientDrawAssetTimeoutMs = 15_000

export type PooledEmpiricalCoefficientDraw = {
  drawId: number
  source: typeof pooledEmpiricalCoefficientDrawMetadata.source
  modelId: typeof pooledEmpiricalCoefficientDrawMetadata.modelId
  seed: typeof pooledEmpiricalCoefficientDrawMetadata.seed
  coefficients: PooledEmpiricalCoefficientVector
}

type DrawFetch = (input: string) => Promise<{
  ok: boolean
  status: number
  text: () => Promise<string>
}>

export type CoefficientDrawAssetErrorCode =
  | "missing_fetch"
  | "fetch_failed"
  | "fetch_timeout"
  | "http_error"
  | "read_timeout"
  | "empty_asset"
  | "schema_mismatch"
  | "row_count_mismatch"
  | "invalid_row"
  | "invalid_metadata"
  | "invalid_number"

export class CoefficientDrawAssetError extends Error {
  readonly code: CoefficientDrawAssetErrorCode

  constructor(code: CoefficientDrawAssetErrorCode, message: string) {
    super(message)
    this.name = "CoefficientDrawAssetError"
    this.code = code
  }
}

export type LoadPooledEmpiricalCoefficientDrawsOptions = {
  assetPath?: string
  fetchDraws?: DrawFetch
  timeoutMs?: number
}

let coefficientDrawCache: PooledEmpiricalCoefficientDraw[] | null = null

export async function loadPooledEmpiricalCoefficientDraws(
  options: LoadPooledEmpiricalCoefficientDrawsOptions = {}
): Promise<PooledEmpiricalCoefficientDraw[]> {
  if (coefficientDrawCache !== null) {
    return coefficientDrawCache
  }

  const fetchDraws = options.fetchDraws ?? globalThis.fetch
  if (typeof fetchDraws !== "function") {
    throw new CoefficientDrawAssetError(
      "missing_fetch",
      "A fetch implementation is required to load coefficient draws."
    )
  }

  const assetPath = options.assetPath ?? pooledEmpiricalCoefficientDrawAssetUrl
  const timeoutMs =
    options.timeoutMs ?? defaultCoefficientDrawAssetTimeoutMs
  const response = await withAssetTimeout(
    () => fetchDraws(assetPath),
    timeoutMs,
    "fetch_timeout",
    "Timed out while loading coefficient draws."
  )
  if (!response.ok) {
    throw new CoefficientDrawAssetError(
      "http_error",
      `Coefficient draw load failed with HTTP ${response.status}.`
    )
  }

  const csvText = await withAssetTimeout(
    () => response.text(),
    timeoutMs,
    "read_timeout",
    "Timed out while reading coefficient draws."
  )
  coefficientDrawCache = parsePooledEmpiricalCoefficientDrawCsv(
    csvText
  )
  return coefficientDrawCache
}

export function clearPooledEmpiricalCoefficientDrawCache() {
  coefficientDrawCache = null
}

export function parsePooledEmpiricalCoefficientDrawCsv(
  text: string
): PooledEmpiricalCoefficientDraw[] {
  if (text.trim().length === 0) {
    throw new CoefficientDrawAssetError(
      "empty_asset",
      "Coefficient draw CSV is empty."
    )
  }

  const lines = text
    .trim()
    .split(/\r?\n/)
    .filter((line) => line.length > 0)

  const [header, ...rows] = lines
  if (header !== expectedCoefficientDrawHeader) {
    throw new CoefficientDrawAssetError(
      "schema_mismatch",
      "Coefficient draw CSV header does not match the app schema."
    )
  }

  const draws = rows.map(parseCoefficientDrawRow)
  validatePooledEmpiricalCoefficientDraws(draws)

  return draws
}

export function validatePooledEmpiricalCoefficientDraws(
  draws: PooledEmpiricalCoefficientDraw[]
) {
  if (draws.length === 0) {
    throw new CoefficientDrawAssetError(
      "empty_asset",
      "Coefficient draw CSV has no draw rows."
    )
  }

  if (draws.length !== pooledEmpiricalCoefficientDrawMetadata.drawCount) {
    throw new CoefficientDrawAssetError(
      "row_count_mismatch",
      `Expected ${pooledEmpiricalCoefficientDrawMetadata.drawCount.toLocaleString()} coefficient draws, found ${draws.length.toLocaleString()}.`
    )
  }

  const drawIds = new Set<number>()
  for (const draw of draws) {
    if (draw.source !== pooledEmpiricalCoefficientDrawMetadata.source) {
      throw new CoefficientDrawAssetError(
        "invalid_metadata",
        `Unexpected coefficient draw source: ${draw.source}.`
      )
    }
    if (draw.modelId !== pooledEmpiricalCoefficientDrawMetadata.modelId) {
      throw new CoefficientDrawAssetError(
        "invalid_metadata",
        `Unexpected coefficient draw model ID: ${draw.modelId}.`
      )
    }
    if (draw.seed !== pooledEmpiricalCoefficientDrawMetadata.seed) {
      throw new CoefficientDrawAssetError(
        "invalid_metadata",
        `Unexpected coefficient draw seed: ${draw.seed}.`
      )
    }
    if (!Number.isInteger(draw.drawId) || draw.drawId < 0) {
      throw new CoefficientDrawAssetError(
        "invalid_row",
        `Invalid coefficient draw ID: ${draw.drawId}.`
      )
    }
    if (drawIds.has(draw.drawId)) {
      throw new CoefficientDrawAssetError(
        "invalid_row",
        `Duplicate coefficient draw ID: ${draw.drawId}.`
      )
    }
    drawIds.add(draw.drawId)

    for (const key of expectedCoefficientKeys) {
      const coefficient = draw.coefficients[key]
      if (!Number.isFinite(coefficient)) {
        throw new CoefficientDrawAssetError(
          "invalid_number",
          `Coefficient draw field is not finite: ${key}.`
        )
      }
    }
  }
}

function parseCoefficientDrawRow(row: string): PooledEmpiricalCoefficientDraw {
  const [
    drawId,
    intercept,
    ageCentered,
    painSevere,
    feverOrTemp,
    vomitingPresent,
    tachycardiaBurden,
    seed,
  ] = row.split(",")

  if (row.split(",").length !== 8) {
    throw new CoefficientDrawAssetError(
      "invalid_row",
      "Coefficient draw CSV row does not match the app schema."
    )
  }

  const parsedSeed = Number(seed)
  if (parsedSeed !== pooledEmpiricalCoefficientDrawMetadata.seed) {
    throw new CoefficientDrawAssetError(
      "invalid_metadata",
      `Unexpected coefficient draw seed: ${seed}.`
    )
  }

  return {
    drawId: finiteNumber(drawId, "draw_id"),
    source: pooledEmpiricalCoefficientDrawMetadata.source,
    modelId: pooledEmpiricalCoefficientDrawMetadata.modelId,
    seed: pooledEmpiricalCoefficientDrawMetadata.seed,
    coefficients: {
      intercept: finiteNumber(intercept, "intercept"),
      age_centered: finiteNumber(ageCentered, "age_centered"),
      pain_severe: finiteNumber(painSevere, "pain_severe"),
      fever_or_temp: finiteNumber(feverOrTemp, "fever_or_temp"),
      vomiting_present: finiteNumber(vomitingPresent, "vomiting_present"),
      tachycardia_burden: finiteNumber(
        tachycardiaBurden,
        "tachycardia_burden"
      ),
    },
  }
}

function finiteNumber(value: string | undefined, label: string): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    throw new CoefficientDrawAssetError(
      "invalid_number",
      `Coefficient draw field is not finite: ${label}.`
    )
  }
  return parsed
}

async function withAssetTimeout<T>(
  operation: () => Promise<T>,
  timeoutMs: number,
  timeoutCode: CoefficientDrawAssetErrorCode,
  timeoutMessage: string
): Promise<T> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(new CoefficientDrawAssetError(timeoutCode, timeoutMessage))
    }, timeoutMs)
  })

  try {
    return await Promise.race([operation(), timeout])
  } catch (error) {
    if (error instanceof CoefficientDrawAssetError) {
      throw error
    }
    throw new CoefficientDrawAssetError(
      "fetch_failed",
      "Coefficient draw asset could not be loaded."
    )
  } finally {
    clearTimeout(timeoutId)
  }
}
