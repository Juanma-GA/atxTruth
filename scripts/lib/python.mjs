// Finds the backend's Python: $BACKEND_PYTHON, then backend/.venv (Scripts\python.exe on Windows,
// bin/python elsewhere), then python3 / python on the PATH.
import { existsSync } from 'node:fs';
import path from 'node:path';

import { BACKEND } from './paths.mjs';
import { run } from './proc.mjs';

export async function backendPython() {
  const candidates = [];
  if (process.env.BACKEND_PYTHON) candidates.push({ cmd: process.env.BACKEND_PYTHON, origin: '$BACKEND_PYTHON' });
  const venv = process.platform === 'win32'
    ? path.join(BACKEND, '.venv', 'Scripts', 'python.exe')
    : path.join(BACKEND, '.venv', 'bin', 'python');
  if (existsSync(venv)) candidates.push({ cmd: venv, origin: 'backend/.venv' });
  candidates.push({ cmd: 'python3', origin: 'PATH' }, { cmd: 'python', origin: 'PATH' });
  for (const candidate of candidates) {
    const probe = await run(candidate.cmd, ['-c', 'import sys; print(sys.executable); print(sys.version_info >= (3, 12))'], { echo: false });
    if (probe.code === 0 && probe.output.trim().endsWith('True')) {
      return { ...candidate, executable: probe.output.trim().split(/\r?\n/)[0] };
    }
  }
  return null;
}
