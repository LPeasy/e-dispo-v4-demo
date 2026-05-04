import { spawnSync } from "node:child_process"
import { existsSync } from "node:fs"
import { join } from "node:path"

const variants = new Map([
  ["e_dispo_v4", "dist/e-dispo-v4-demo"],
  ["general_e_dispo", "dist/general-e-dispo-demo"],
])

const [variant, outDirOverride] = process.argv.slice(2)
const outDir = outDirOverride ?? variants.get(variant)

if (!variant || !variants.has(variant) || !outDir) {
  console.error(
    "Usage: node scripts/build_site_variant.mjs <e_dispo_v4|general_e_dispo> [outDir]",
  )
  process.exit(1)
}

const localVite = join(
  process.cwd(),
  "node_modules",
  ".bin",
  process.platform === "win32" ? "vite.cmd" : "vite",
)
const command = existsSync(localVite) ? localVite : "vite"
const result = spawnSync(command, ["build", "--outDir", outDir], {
  env: {
    ...process.env,
    VITE_APP_VARIANT: variant,
  },
  shell: process.platform === "win32",
  stdio: "inherit",
})

if (result.error) {
  console.error(result.error.message)
}

process.exit(result.status ?? 1)
