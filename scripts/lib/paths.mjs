// Repository paths, built with path.join so they work the same on Windows and Linux.
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const FRONTEND = path.join(ROOT, 'frontend');
export const BACKEND = path.join(ROOT, 'backend');
export const ARTIFACTS = path.join(ROOT, 'artifacts');
