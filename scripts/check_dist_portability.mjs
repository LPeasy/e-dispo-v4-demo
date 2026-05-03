#!/usr/bin/env node

import { createServer } from "node:http"
import { readFile } from "node:fs/promises"
import { existsSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)))
const distDir = path.join(root, "dist")
const assetsDir = path.join(distDir, "assets")

const failures = []

function fail(message) {
  failures.push(message)
}

function assert(condition, message) {
  if (!condition) {
    fail(message)
  }
}

async function main() {
  assert(existsSync(distDir), "dist/ is missing. Run npm run build first.")
  assert(existsSync(assetsDir), "dist/assets/ is missing.")

  const indexHtml = await readText(path.join(distDir, "index.html"))
  assert(indexHtml !== null, "dist/index.html is missing.")

  if (indexHtml !== null) {
    assert(
      !/\b(?:src|href)="\/(?:assets|favicon\.svg|icons\.svg)/.test(indexHtml),
      "dist/index.html contains root-absolute asset paths."
    )
    assert(
      /\b(?:src|href)="\.\/assets\//.test(indexHtml),
      "dist/index.html does not reference relative ./assets/ URLs."
    )
  }

  const distFiles = await listFiles(distDir)
  const assetFiles = distFiles.filter((file) =>
    path.relative(assetsDir, file).startsWith("..") === false
  )
  const coefficientFiles = assetFiles.filter((file) =>
    /^pooled-empirical-coefficient-draws-.*\.csv$/.test(path.basename(file))
  )
  const workerFiles = assetFiles.filter((file) =>
    /^simulationWorker-.*\.js$/.test(path.basename(file))
  )
  const mainFiles = assetFiles.filter((file) =>
    /^index-.*\.js$/.test(path.basename(file))
  )

  assert(
    coefficientFiles.length === 1,
    `Expected one hashed coefficient draw CSV, found ${coefficientFiles.length}.`
  )
  assert(
    workerFiles.length === 1,
    `Expected one simulation worker JS asset, found ${workerFiles.length}.`
  )
  assert(
    mainFiles.length === 1,
    `Expected one main app JS asset, found ${mainFiles.length}.`
  )

  if (coefficientFiles.length === 1 && workerFiles.length === 1) {
    const workerText = await readText(workerFiles[0])
    assert(
      workerText?.includes(path.basename(coefficientFiles[0])) === true,
      "simulation worker does not reference the hashed coefficient CSV."
    )
  }

  if (coefficientFiles.length === 1) {
    const csvText = await readText(coefficientFiles[0])
    const firstDataRow = csvText?.split(/\r?\n/).find((line, index) => {
      return index > 0 && line.trim().length > 0
    })

    assert(
      csvText?.startsWith(
        "draw_id,intercept,age_centered,pain_severe,fever_or_temp,vomiting_present,tachycardia_burden,seed"
      ) === true,
      "coefficient CSV header is missing or malformed."
    )

    if (firstDataRow) {
      for (const mainFile of mainFiles) {
        const mainText = await readText(mainFile)
        assert(
          mainText?.includes(firstDataRow) === false,
          `${path.basename(mainFile)} embeds coefficient draw rows.`
        )
      }
    }
  }

  await checkNestedHttpServing(distFiles)

  if (failures.length > 0) {
    console.error("dist portability check failed:")
    for (const failure of failures) {
      console.error(`- ${failure}`)
    }
    process.exitCode = 1
    return
  }

  console.log("dist portability check passed.")
}

async function readText(filePath) {
  try {
    return await readFile(filePath, "utf-8")
  } catch {
    return null
  }
}

async function listFiles(directory) {
  const { readdir } = await import("node:fs/promises")
  const entries = await readdir(directory, { withFileTypes: true })
  const files = []

  for (const entry of entries) {
    const entryPath = path.join(directory, entry.name)
    if (entry.isDirectory()) {
      files.push(...(await listFiles(entryPath)))
    } else if (entry.isFile()) {
      files.push(entryPath)
    }
  }

  return files
}

async function checkNestedHttpServing(distFiles) {
  const server = createStaticServer(root)

  await new Promise((resolve) => {
    server.listen(0, "127.0.0.1", resolve)
  })

  const address = server.address()
  const port = typeof address === "object" && address !== null ? address.port : 0
  const baseUrl = `http://127.0.0.1:${port}/dist`

  try {
    const requiredFiles = distFiles.filter((file) => {
      const relative = path.relative(distDir, file).replaceAll(path.sep, "/")
      return (
        relative === "index.html" ||
        relative === "favicon.svg" ||
        relative === "icons.svg" ||
        relative.startsWith("assets/")
      )
    })

    for (const file of requiredFiles) {
      const relative = path.relative(distDir, file).replaceAll(path.sep, "/")
      const url = relative === "index.html" ? `${baseUrl}/` : `${baseUrl}/${relative}`
      const response = await fetch(url)
      assert(response.ok, `${url} returned HTTP ${response.status}.`)
      await response.arrayBuffer()
    }
  } finally {
    await new Promise((resolve) => server.close(resolve))
  }
}

function createStaticServer(serverRoot) {
  return createServer(async (request, response) => {
    try {
      const requestUrl = new URL(request.url ?? "/", "http://127.0.0.1")
      const decodedPath = decodeURIComponent(requestUrl.pathname)
      const safePath = path
        .normalize(decodedPath)
        .replace(/^(\.\.(?:\/|\\|$))+/, "")
        .replace(/^[/\\]+/, "")
      let filePath = path.join(serverRoot, safePath)

      if (!filePath.startsWith(serverRoot)) {
        response.writeHead(403)
        response.end("Forbidden")
        return
      }

      if (filePath.endsWith(path.sep) || requestUrl.pathname.endsWith("/")) {
        filePath = path.join(filePath, "index.html")
      }

      const body = await readFile(filePath)
      response.writeHead(200, {
        "content-type": contentTypeFor(filePath),
      })
      response.end(body)
    } catch {
      response.writeHead(404)
      response.end("Not found")
    }
  })
}

function contentTypeFor(filePath) {
  switch (path.extname(filePath)) {
    case ".html":
      return "text/html; charset=utf-8"
    case ".js":
      return "application/javascript; charset=utf-8"
    case ".css":
      return "text/css; charset=utf-8"
    case ".csv":
      return "text/csv; charset=utf-8"
    case ".svg":
      return "image/svg+xml"
    case ".woff2":
      return "font/woff2"
    default:
      return "application/octet-stream"
  }
}

await main()
