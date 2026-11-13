#!/usr/bin/env node
// `npm run check`: everything that needs no browser, the same in Linux and PowerShell.
// Stops at the first failure; `npm run check -- --keep-going` runs every step and lists all failures.
// Exit codes: 0 all good · 1 something failed · 2 something missing in the environment (says what).
import { existsSync } from 'node:fs';
import path from 'node:path';

import { findForbidden } from './check-forbidden.mjs';
import { BACKEND, FRONTEND } from './lib/paths.mjs';
import { run } from './lib/proc.mjs';
import { backendPython } from './lib/python.mjs';

const keepGoing = process.argv.includes('--keep-going');
const node = process.execPath;
const bin = (...parts) => path.join(FRONTEND, 'node_modules', ...parts);

const envProblems = [];
if (!existsSync(bin('.bin')) && !existsSync(bin('typescript'))) envProblems.push('frontend/node_modules is missing: run `npm ci` in frontend/.');
const python = await backendPython();
if (!python) envProblems.push('No Python 3.12+ for the backend (set BACKEND_PYTHON or create backend/.venv; see README).');
if (envProblems.length) {
  for (const p of envProblems) console.error(`ENVIRONMENT: ${p}`);
  process.exit(2);
}

const fe = (args) => ({ cmd: node, args, cwd: FRONTEND });
const py = (args) => ({ cmd: python.cmd, args, cwd: BACKEND });

const steps = [
  { name: 'forbidden patterns', fn: () => findForbidden() },
  { name: 'design tokens', ...fe(['style-dictionary.config.mjs']) },
  { name: 'eslint', ...fe([bin('eslint', 'bin', 'eslint.js'), '.', '--max-warnings', '0']) },
  { name: 'ruff check', ...py(['-m', 'ruff', 'check', '.']) },
  { name: 'ruff format', ...py(['-m', 'ruff', 'format', '--check', '.']) },
  { name: 'tsc', ...fe([bin('typescript', 'bin', 'tsc'), '-b']) },
  { name: 'mypy (strict, app/)', ...py(['-m', 'mypy']) },
  { name: 'vite build', ...fe([bin('vite', 'bin', 'vite.js'), 'build', '--logLevel', 'warn']) },
  { name: 'vitest', ...fe([bin('vitest', 'vitest.mjs'), 'run']) },
  { name: 'test database', ...py(['scripts/check_test_db.py']), envOnExit2: true },
  { name: 'pytest', ...py(['-m', 'pytest', '-q']), envOnExit2: true },
];

const results = [];
let envMissing = false;
for (const step of steps) {
  const started = Date.now();
  console.log(`\n── ${step.name} ──`);
  let code;
  if (step.fn) {
    const problems = step.fn();
    for (const p of problems) console.error(`  ${p}`);
    code = problems.length ? 1 : 0;
  } else {
    ({ code } = await run(step.cmd, step.args, { cwd: step.cwd }));
  }
  const status = code === 0 ? 'ok' : step.envOnExit2 && code === 2 ? 'environment' : 'FAILED';
  results.push({ name: step.name, status, seconds: ((Date.now() - started) / 1000).toFixed(1) });
  if (status === 'environment') envMissing = true;
  if (status !== 'ok' && !keepGoing) break;
}

console.log('\n══ check summary ══');
console.log(`python: ${python.executable} (${python.origin})`);
for (const r of results) console.log(`  ${r.status.padEnd(11)} ${r.name} (${r.seconds}s)`);
const skipped = steps.length - results.length;
if (skipped) console.log(`  (${skipped} step(s) not run: stopped at the first failure; use -- --keep-going)`);
const failed = results.filter((r) => r.status === 'FAILED');
if (failed.length) {
  console.log(`RESULT: FAILED (${failed.map((r) => r.name).join(', ')})`);
  process.exit(1);
}
if (envMissing) {
  console.log('RESULT: ENVIRONMENT INCOMPLETE (see the messages above; not an app failure, but not everything was checked)');
  process.exit(2);
}
console.log('RESULT: OK');
process.exit(0);
