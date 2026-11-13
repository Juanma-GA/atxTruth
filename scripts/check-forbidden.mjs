#!/usr/bin/env node
// Blocks forbidden patterns (AACF G1). Used by `npm run check` and the pre-commit hook.
//  - HR1: localStorage / sessionStorage in frontend/src or backend/app.
//  - `from __future__ import annotations` in FastAPI route files.
//  - Colours written by hand in the frontend (hex, rgb(), hsl(), oklch()) outside the tokens.
//  - HR15: visible text in JSX that does not go through i18n (JSX text and text attributes).
//  - Windows safety in scripts/: /tmp paths, .venv/bin, shell-only programs.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import { BACKEND, FRONTEND, ROOT } from './lib/paths.mjs';

function walk(dir, exts, skip = []) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (skip.some((s) => full.includes(s))) continue;
    if (statSync(full).isDirectory()) out.push(...walk(full, exts, skip));
    else if (exts.some((e) => name.endsWith(e))) out.push(full);
  }
  return out;
}

const rel = (file) => path.relative(ROOT, file).split(path.sep).join('/');
const text = (file) => readFileSync(file, 'utf8');

export function findForbidden() {
  const problems = [];
  const report = (file, line, message) => problems.push(`${rel(file)}:${line}  ${message}`);
  const lineOf = (source, index) => source.slice(0, index).split('\n').length;

  const generated = path.join('src', 'styles', 'generated');
  const frontendFiles = walk(path.join(FRONTEND, 'src'), ['.ts', '.tsx', '.css'], [generated]);
  const backendFiles = walk(path.join(BACKEND, 'app'), ['.py']);

  for (const file of [...frontendFiles, ...backendFiles]) {
    const source = text(file);
    for (const match of source.matchAll(/\b(localStorage|sessionStorage)\b/g)) {
      report(file, lineOf(source, match.index), `HR1: ${match[1]} is not allowed (Postgres is the source of truth)`);
    }
  }

  for (const file of walk(path.join(BACKEND, 'app', 'api', 'routes'), ['.py'])) {
    const source = text(file);
    const match = /^from __future__ import annotations/m.exec(source);
    if (match) report(file, lineOf(source, match.index), 'from __future__ import annotations breaks FastAPI routes');
  }

  const colour = /(#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\s*\()/g;
  for (const file of frontendFiles) {
    if (file.includes(`${path.sep}test${path.sep}`)) continue;
    const source = text(file);
    for (const match of source.matchAll(colour)) {
      report(file, lineOf(source, match.index), `colour written by hand (${match[1]}); use a design token`);
    }
  }

  // JSX text that bypasses i18n, via the TypeScript AST.
  const require = createRequire(pathToFileURL(path.join(FRONTEND, 'package.json')));
  const ts = require('typescript');
  const TEXT_ATTRS = new Set(['aria-label', 'title', 'placeholder', 'alt', 'label', 'aria-description']);
  const hasWords = (s) => /\p{L}{2,}/u.test(s);
  for (const file of frontendFiles.filter((f) => f.endsWith('.tsx') && !f.includes(`${path.sep}test${path.sep}`))) {
    const source = text(file);
    const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    const visit = (node) => {
      if (ts.isJsxText(node) && hasWords(node.getText())) {
        report(file, lineOf(source, node.getStart()), `HR15: visible text without i18n: "${node.getText().trim()}"`);
      }
      if (ts.isJsxAttribute(node) && TEXT_ATTRS.has(node.name.getText()) && node.initializer && ts.isStringLiteral(node.initializer) && hasWords(node.initializer.text)) {
        report(file, lineOf(source, node.getStart()), `HR15: ${node.name.getText()}="${node.initializer.text}" without i18n`);
      }
      ts.forEachChild(node, visit);
    };
    visit(sf);
  }

  for (const file of walk(path.join(ROOT, 'scripts'), ['.mjs'])) {
    if (path.basename(file) === 'check-forbidden.mjs') continue;
    const source = text(file);
    for (const [re, why] of [
      [/['"`]\/tmp\b/g, 'fixed /tmp path (use the artifacts folder or os.tmpdir())'],
      [/\.venv\/bin/g, '.venv/bin is Linux-only (use scripts/lib/python.mjs)'],
      [/shell:\s*true/g, 'shell: true behaves differently on Windows'],
    ]) {
      for (const match of source.matchAll(re)) report(file, lineOf(source, match.index), `Windows safety: ${why}`);
    }
  }
  return problems;
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const problems = findForbidden();
  if (problems.length) {
    console.error(`Forbidden patterns found (${problems.length}):`);
    for (const p of problems) console.error(`  ${p}`);
    process.exit(1);
  }
  console.log('check-forbidden: no forbidden patterns.');
}
