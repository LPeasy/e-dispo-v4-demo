/*
 * Metadata and loader helpers for the generated joint coefficient draws.
 * Draw values live beside this module and are resolved through Vite's asset
 * graph so the worker can load them as data without bundling them into app JS.
 */

export const pooledEmpiricalCoefficientDrawAssetUrl = new URL(
  "./pooled-empirical-coefficient-draws.csv",
  import.meta.url
).href

export const generalEDispoCoefficientDrawAssetUrl = new URL(
  "./general-e-dispo-coefficient-draws.csv",
  import.meta.url
).href

export type PooledEmpiricalCoefficientVector = {
  intercept: number
  age_centered: number
  pain_severe: number
  fever_or_temp: number
  vomiting_present: number
  tachycardia_burden: number
  high_acuity_proxy?: number
  age_centered_40?: number
  sex_2?: number
  acuity_code_blank?: number
  acuity_code_unknown?: number
  acuity_code_no_triage_esa_conducts_triage?: number
  acuity_code_immediate?: number
  acuity_code_emergent?: number
  acuity_code_semi_urgent?: number
  acuity_code_nonurgent?: number
  acuity_code_no_nursing_triage_esa?: number
  arrival_transfer_context_blank?: number
  arrival_transfer_context_unknown?: number
  arrival_transfer_context_not_applicable?: number
  arrival_transfer_context_yes_transferred_from_hospital_or_urgent_care?: number
  hypotension_burden?: number
  [key: string]: number | undefined
}

export const pooledEmpiricalCoefficientDrawMetadata = {
  modelId: "e-dispo-v4.1-pas5-high-acuity-surrogate",
  source: "NHAMCS_2018_2022_POOLED",
  seed: 20260504,
  drawCount: 10000,
  sourcePath: "outputs/nhamcs_pooled/pas5_acuity_draws_app.csv",
  assetPath: pooledEmpiricalCoefficientDrawAssetUrl,
} as const

export const generalEDispoCoefficientDrawMetadata = {
  modelId: "general-E-Dispo-model-v1-sex-adjusted",
  source: "NHAMCS_2018_2022_POOLED",
  seed: 20260429,
  drawCount: 10000,
  sourcePath:
    "outputs/nhamcs_pooled/general_e_dispo_model_v1_plus_sex_covariance.csv",
  assetPath: generalEDispoCoefficientDrawAssetUrl,
} as const

const eDispoV40CoefficientDrawHeader =
  "draw_id,intercept,age_centered,pain_severe,fever_or_temp,vomiting_present,tachycardia_burden,seed"
const eDispoV41Pas5CoefficientDrawHeader =
  "draw_id,intercept,age_centered,pain_severe,fever_or_temp,vomiting_present,tachycardia_burden,high_acuity_proxy,seed"
const generalEDispoCoefficientDrawHeader =
  "draw_id,intercept,age_centered_40,sex_2,acuity_code_blank,acuity_code_unknown,acuity_code_no_triage_esa_conducts_triage,acuity_code_immediate,acuity_code_emergent,acuity_code_semi_urgent,acuity_code_nonurgent,acuity_code_no_nursing_triage_esa,arrival_transfer_context_blank,arrival_transfer_context_unknown,arrival_transfer_context_not_applicable,arrival_transfer_context_yes_transferred_from_hospital_or_urgent_care,fever_or_temp,tachycardia_burden,hypotension_burden,seed"

const expectedCoefficientKeys = [
  "intercept",
  "age_centered",
  "pain_severe",
  "fever_or_temp",
  "vomiting_present",
  "tachycardia_burden",
] as const

const generalExpectedCoefficientKeys = [
  "intercept",
  "age_centered_40",
  "sex_2",
  "acuity_code_blank",
  "acuity_code_unknown",
  "acuity_code_no_triage_esa_conducts_triage",
  "acuity_code_immediate",
  "acuity_code_emergent",
  "acuity_code_semi_urgent",
  "acuity_code_nonurgent",
  "acuity_code_no_nursing_triage_esa",
  "arrival_transfer_context_blank",
  "arrival_transfer_context_unknown",
  "arrival_transfer_context_not_applicable",
  "arrival_transfer_context_yes_transferred_from_hospital_or_urgent_care",
  "fever_or_temp",
  "tachycardia_burden",
  "hypotension_burden",
] as const

type CoefficientDrawSchema =
  | "e-dispo-v4.0"
  | "e-dispo-v4.1-pas5-high-acuity-surrogate"
  | "general-E-Dispo-model-v1-sex-adjusted"

export type CoefficientDrawModelId = CoefficientDrawSchema

const defaultCoefficientDrawAssetTimeoutMs = 15_000

export type PooledEmpiricalCoefficientDraw = {
  drawId: number
  source: "NHAMCS_2018_2022_POOLED"
  modelId: CoefficientDrawSchema
  seed: number
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

const coefficientDrawCacheByModelId = new Map<
  CoefficientDrawModelId,
  PooledEmpiricalCoefficientDraw[]
>()

export async function loadPooledEmpiricalCoefficientDraws(
  options: LoadPooledEmpiricalCoefficientDrawsOptions = {}
): Promise<PooledEmpiricalCoefficientDraw[]> {
  return loadCoefficientDrawsForModel(
    pooledEmpiricalCoefficientDrawMetadata.modelId,
    options
  )
}

export async function loadCoefficientDrawsForModel(
  modelId: CoefficientDrawModelId,
  options: LoadPooledEmpiricalCoefficientDrawsOptions = {}
): Promise<PooledEmpiricalCoefficientDraw[]> {
  const cachedDraws = coefficientDrawCacheByModelId.get(modelId)
  if (cachedDraws) {
    return cachedDraws
  }

  const fetchDraws = options.fetchDraws ?? globalThis.fetch
  if (typeof fetchDraws !== "function") {
    throw new CoefficientDrawAssetError(
      "missing_fetch",
      "A fetch implementation is required to load coefficient draws."
    )
  }

  const metadata = coefficientDrawMetadataForModel(modelId)
  const assetPath = options.assetPath ?? metadata.assetPath
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
  const draws = parsePooledEmpiricalCoefficientDrawCsv(csvText, modelId)
  coefficientDrawCacheByModelId.set(modelId, draws)
  return draws
}

export function clearPooledEmpiricalCoefficientDrawCache() {
  coefficientDrawCacheByModelId.clear()
}

export function parsePooledEmpiricalCoefficientDrawCsv(
  text: string,
  expectedModelId?: CoefficientDrawModelId
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
  const schema = coefficientDrawSchemaForHeader(header)
  if (schema === null) {
    throw new CoefficientDrawAssetError(
      "schema_mismatch",
      "Coefficient draw CSV header does not match the app schema."
    )
  }

  if (expectedModelId && schema !== expectedModelId) {
    throw new CoefficientDrawAssetError(
      "schema_mismatch",
      "Coefficient draw CSV header does not match the requested model."
    )
  }

  const draws = rows.map((row) => parseCoefficientDrawRow(row, schema))
  validatePooledEmpiricalCoefficientDraws(draws, expectedModelId ?? schema)

  return draws
}

export function validatePooledEmpiricalCoefficientDraws(
  draws: PooledEmpiricalCoefficientDraw[],
  expectedModelId: CoefficientDrawModelId = pooledEmpiricalCoefficientDrawMetadata.modelId
) {
  if (draws.length === 0) {
    throw new CoefficientDrawAssetError(
      "empty_asset",
      "Coefficient draw CSV has no draw rows."
    )
  }

  const metadata = coefficientDrawMetadataForModel(expectedModelId)
  if (draws.length !== metadata.drawCount) {
    throw new CoefficientDrawAssetError(
      "row_count_mismatch",
      `Expected ${metadata.drawCount.toLocaleString()} coefficient draws, found ${draws.length.toLocaleString()}.`
    )
  }

  const drawIds = new Set<number>()
  for (const draw of draws) {
    if (draw.source !== metadata.source) {
      throw new CoefficientDrawAssetError(
        "invalid_metadata",
        `Unexpected coefficient draw source: ${draw.source}.`
      )
    }
    if (draw.modelId !== metadata.modelId) {
      throw new CoefficientDrawAssetError(
        "invalid_metadata",
        `Unexpected coefficient draw model ID: ${draw.modelId}.`
      )
    }
    if (draw.seed !== metadata.seed) {
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

    const requiredKeys =
      expectedModelId === "general-E-Dispo-model-v1-sex-adjusted"
        ? generalExpectedCoefficientKeys
        : expectedCoefficientKeys
    for (const key of requiredKeys) {
      const coefficient = draw.coefficients[key]
      if (!Number.isFinite(coefficient)) {
        throw new CoefficientDrawAssetError(
          "invalid_number",
          `Coefficient draw field is not finite: ${key}.`
        )
      }
    }

    if (draw.modelId === "e-dispo-v4.1-pas5-high-acuity-surrogate") {
      const coefficient = draw.coefficients.high_acuity_proxy
      if (!Number.isFinite(coefficient)) {
        throw new CoefficientDrawAssetError(
          "invalid_number",
          "Coefficient draw field is not finite: high_acuity_proxy."
        )
      }
    }
  }
}

function parseCoefficientDrawRow(
  row: string,
  schema: CoefficientDrawSchema
): PooledEmpiricalCoefficientDraw {
  const cells = row.split(",")
  const expectedCellCount = expectedCellCountForSchema(schema)

  if (cells.length !== expectedCellCount) {
    throw new CoefficientDrawAssetError(
      "invalid_row",
      "Coefficient draw CSV row does not match the app schema."
    )
  }

  if (schema === "general-E-Dispo-model-v1-sex-adjusted") {
    return parseGeneralCoefficientDrawRow(cells)
  }

  const [
    drawId,
    intercept,
    ageCentered,
    painSevere,
    feverOrTemp,
    vomitingPresent,
    tachycardiaBurden,
  ] = cells
  const highAcuity =
    schema === "e-dispo-v4.1-pas5-high-acuity-surrogate" ? cells[7] : undefined
  const seed =
    schema === "e-dispo-v4.1-pas5-high-acuity-surrogate" ? cells[8] : cells[7]
  const parsedSeed = Number(seed)
  const metadata = coefficientDrawMetadataForModel(schema)
  if (parsedSeed !== metadata.seed) {
    throw new CoefficientDrawAssetError(
      "invalid_metadata",
      `Unexpected coefficient draw seed: ${seed}.`
    )
  }

  return {
    drawId: finiteNumber(drawId, "draw_id"),
    source: metadata.source,
    modelId: schema,
    seed: metadata.seed,
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
      ...(schema === "e-dispo-v4.1-pas5-high-acuity-surrogate"
        ? {
            high_acuity_proxy: finiteNumber(
              highAcuity,
              "high_acuity_proxy"
            ),
          }
        : {}),
    },
  }
}

function parseGeneralCoefficientDrawRow(
  cells: string[]
): PooledEmpiricalCoefficientDraw {
  const metadata = coefficientDrawMetadataForModel(
    "general-E-Dispo-model-v1-sex-adjusted"
  )
  const [drawId, ...coefficientAndSeed] = cells
  const seed = coefficientAndSeed[coefficientAndSeed.length - 1]
  const parsedSeed = Number(seed)
  if (parsedSeed !== metadata.seed) {
    throw new CoefficientDrawAssetError(
      "invalid_metadata",
      `Unexpected coefficient draw seed: ${seed}.`
    )
  }

  const coefficients = Object.fromEntries(
    generalExpectedCoefficientKeys.map((key, index) => [
      key,
      finiteNumber(coefficientAndSeed[index], key),
    ])
  ) as PooledEmpiricalCoefficientVector

  return {
    drawId: finiteNumber(drawId, "draw_id"),
    source: metadata.source,
    modelId: metadata.modelId,
    seed: metadata.seed,
    coefficients,
  }
}

function coefficientDrawSchemaForHeader(
  header: string
): CoefficientDrawSchema | null {
  const normalizedHeader = header.replaceAll('"', "")

  if (normalizedHeader === eDispoV40CoefficientDrawHeader) {
    return "e-dispo-v4.0"
  }

  if (normalizedHeader === eDispoV41Pas5CoefficientDrawHeader) {
    return "e-dispo-v4.1-pas5-high-acuity-surrogate"
  }

  if (normalizedHeader === generalEDispoCoefficientDrawHeader) {
    return "general-E-Dispo-model-v1-sex-adjusted"
  }

  return null
}

function expectedCellCountForSchema(schema: CoefficientDrawSchema): number {
  if (schema === "general-E-Dispo-model-v1-sex-adjusted") {
    return generalExpectedCoefficientKeys.length + 2
  }

  return schema === "e-dispo-v4.1-pas5-high-acuity-surrogate" ? 9 : 8
}

function coefficientDrawMetadataForModel(modelId: CoefficientDrawModelId) {
  if (modelId === "general-E-Dispo-model-v1-sex-adjusted") {
    return generalEDispoCoefficientDrawMetadata
  }

  return {
    ...pooledEmpiricalCoefficientDrawMetadata,
    modelId,
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
