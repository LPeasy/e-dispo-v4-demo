import assert from "node:assert/strict"
import test from "node:test"

import {
  allParameterDefinitions,
  parameterOrder,
  parameterRegistry,
} from "./parameterRegistry"
import type { DoseResponse } from "./parameterRegistry"
import { fieldLabels } from "./worksheet"

test("every model input has a parameter definition", () => {
  assert.deepEqual(
    parameterOrder.toSorted(),
    Object.keys(fieldLabels).toSorted()
  )
  assert.equal(allParameterDefinitions().length, Object.keys(fieldLabels).length)
})

test("every selectable parameter value has a finite effect distribution", () => {
  for (const definition of allParameterDefinitions()) {
    for (const value of valuesForDoseResponse(definition.doseResponse)) {
      const distribution = definition.distributions[value]
      assert.ok(distribution, `${definition.id}.${value} is missing`)
      assert.equal(distribution.family, "normal")
      assert.equal(Number.isFinite(distribution.mean), true)
      assert.equal(Number.isFinite(distribution.standardError), true)
      assert.ok(distribution.standardError >= 0)
      assert.ok(distribution.sourceIds.length > 0)
    }
  }
})

test("ordinal increasing dose-response parameters are monotonic", () => {
  for (const definition of allParameterDefinitions()) {
    if (
      definition.doseResponse.kind !== "ordinal" ||
      definition.doseResponse.monotonic !== "increasing"
    ) {
      continue
    }

    const means = definition.doseResponse.levels.map(
      (level) => parameterRegistry[definition.id].distributions[level].mean
    )

    for (let index = 1; index < means.length; index += 1) {
      assert.ok(
        means[index] >= means[index - 1],
        `${definition.id} is not monotonic increasing`
      )
    }
  }
})

function valuesForDoseResponse(response: DoseResponse): string[] {
  if (response.kind === "binary") {
    return [response.reference, response.positive, response.unknown].filter(
      (value): value is string => typeof value === "string"
    )
  }

  return response.levels
}
