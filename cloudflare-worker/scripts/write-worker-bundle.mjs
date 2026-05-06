import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const inputPath = resolve(root, "dist", "index.js");
const outputPath = resolve(root, "_worker.js");

const bundled = readFileSync(inputPath, "utf8").replace(
  /\n\/\/# sourceMappingURL=index\.js\.map\s*$/,
  ""
);

const header = `// Cloudflare Workers console deployment file.
// Paste this whole file into the Cloudflare Worker editor.
// Source of truth lives in src/*.ts; run \`npm run build:worker\` after changing it.

`;

writeFileSync(outputPath, `${header}${bundled}\n`, "utf8");
