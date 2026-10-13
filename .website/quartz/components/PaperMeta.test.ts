import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import { dirname } from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"
import { build } from "esbuild"

const componentDir = dirname(fileURLToPath(import.meta.url))
const bundle = await build({
  stdin: {
    contents: `
      import renderToString from "preact-render-to-string"
      import PaperMeta from "./PaperMeta"

      export function renderPaperMeta(frontmatter) {
        const Component = PaperMeta(undefined)
        return renderToString(
          <Component fileData={{ slug: "Papers/example", frontmatter }} />,
        )
      }
    `,
    loader: "tsx",
    resolveDir: componentDir,
    sourcefile: "PaperMeta.test-entry.tsx",
  },
  bundle: true,
  format: "esm",
  jsx: "automatic",
  jsxImportSource: "preact",
  platform: "node",
  write: false,
  plugins: [
    {
      name: "inline-script-as-text",
      setup(build) {
        build.onLoad({ filter: /\.inline\.(ts|js)$/ }, async ({ path }) => ({
          contents: await readFile(path, "utf8"),
          loader: "text",
        }))
      },
    },
  ],
})

const moduleUrl = `data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`
const { renderPaperMeta } = (await import(moduleUrl)) as {
  renderPaperMeta: (frontmatter: Record<string, unknown>) => string
}

const cases = [
  {
    name: "renders plural institutes before the legacy singular field",
    frontmatter: {
      institutes: ["Plural University", "Plural Lab"],
      institute: ["Legacy Institute"],
    },
    expected: "Plural University, Plural Lab",
    unexpected: "Legacy Institute",
  },
  {
    name: "normalizes a scalar plural institute",
    frontmatter: { institutes: "Scalar Institute" },
    expected: "Scalar Institute",
  },
  {
    name: "falls back to the legacy singular institute",
    frontmatter: { institute: ["Legacy Institute"] },
    expected: "Legacy Institute",
  },
]

for (const { name, frontmatter, expected, unexpected } of cases) {
  test(name, () => {
    const html = renderPaperMeta(frontmatter)

    assert.match(html, /class="paper-institute"/)
    assert.ok(html.includes(expected), `expected rendered institute to include "${expected}"`)
    if (unexpected) assert.ok(!html.includes(unexpected), `did not expect "${unexpected}"`)
  })
}
