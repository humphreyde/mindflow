import assert from "node:assert/strict"
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { test } from "node:test"
import { ignorePatterns } from "../../quartz.ignore"
import { glob } from "./glob"

test("Projects is excluded from Quartz inputs and assets", async (t) => {
  const root = await mkdtemp(path.join(os.tmpdir(), "mindflow-quartz-"))
  t.after(async () => rm(root, { recursive: true, force: true }))

  await mkdir(path.join(root, "Papers"), { recursive: true })
  await mkdir(path.join(root, "assets"), { recursive: true })
  await mkdir(path.join(root, "Projects", "pi", "assets"), { recursive: true })
  await writeFile(path.join(root, "Papers", "keep.md"), "# Keep\n")
  await writeFile(path.join(root, "assets", "keep.png"), "keep")
  await writeFile(path.join(root, "Projects", "pi", "README.md"), "# Exclude\n")
  await writeFile(path.join(root, "Projects", "pi", "assets", "model.bin"), "exclude")

  const inputs = await glob("**/*.*", root, ignorePatterns)
  assert.deepEqual(inputs.sort(), ["Papers/keep.md", "assets/keep.png"])

  const assets = await glob("**", root, ["**/*.md", ...ignorePatterns])
  assert.deepEqual(assets.sort(), ["assets/keep.png"])
})
