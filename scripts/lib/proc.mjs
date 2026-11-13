// Run a program without a shell (same behaviour in PowerShell and bash).
import { spawn } from 'node:child_process';

/** Resolves with { code, output }. Output is streamed to the console when `echo` is true. */
export function run(command, args, { cwd, env, echo = true } = {}) {
  return new Promise((resolve) => {
    const child = spawn(command, args, { cwd, env: { ...process.env, ...env }, shell: false });
    let output = '';
    const onData = (stream) => (chunk) => {
      output += chunk.toString();
      if (echo) stream.write(chunk);
    };
    child.stdout.on('data', onData(process.stdout));
    child.stderr.on('data', onData(process.stderr));
    child.on('error', (error) => resolve({ code: -1, output: String(error) }));
    child.on('close', (code) => resolve({ code: code ?? -1, output }));
  });
}
