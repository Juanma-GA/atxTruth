#!/usr/bin/env node
// Backend helpers that work the same in PowerShell and bash:
//   node scripts/backend.mjs serve            uvicorn on :8000 (BACKEND_PORT to change it)
//   node scripts/backend.mjs migrate          alembic upgrade head
//   node scripts/backend.mjs pytest [args]    backend tests (own test database)
//   node scripts/backend.mjs create-test-db   create + migrate the test database
//   node scripts/backend.mjs ruff             ruff check + ruff format --check
//   node scripts/backend.mjs secret-scan      scripts/secret_scan.py (new secrets only)
import path from 'node:path';

import { BACKEND } from './lib/paths.mjs';
import { run } from './lib/proc.mjs';
import { backendPython } from './lib/python.mjs';

const [command, ...rest] = process.argv.slice(2);
const python = await backendPython();
if (!python) {
  console.error('No Python 3.12+ found (set BACKEND_PYTHON or create backend/.venv). See README.');
  process.exit(2);
}

const commands = {
  serve: ['-m', 'uvicorn', 'app.main:app', '--port', process.env.BACKEND_PORT ?? '8000', ...rest],
  migrate: ['-m', 'alembic', 'upgrade', 'head'],
  pytest: ['-m', 'pytest', ...rest],
  'create-test-db': ['scripts/create_test_db.py'],
  'secret-scan': [path.join('..', 'scripts', 'secret_scan.py')],
};
if (command === 'ruff') {
  const lint = await run(python.cmd, ['-m', 'ruff', 'check', '.'], { cwd: BACKEND });
  const format = await run(python.cmd, ['-m', 'ruff', 'format', '--check', '.'], { cwd: BACKEND });
  process.exit(lint.code || format.code);
}
if (!commands[command]) {
  console.error(`Unknown command "${command}". Use one of: ${Object.keys(commands).join(', ')}`);
  process.exit(2);
}
const result = await run(python.cmd, commands[command], { cwd: BACKEND });
process.exit(result.code);
