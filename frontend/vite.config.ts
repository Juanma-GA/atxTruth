import path from 'node:path';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

// Production CSP for `vite preview`; the production web server (nginx/IIS) must send the same
// header (see README → Producción). The dev server cannot use it: Vite injects inline scripts.
const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  // sonner and Radix (scroll lock) insert <style> elements at runtime: see docs/decisiones.md.
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join('; ');

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.ATX_API_URL || 'http://localhost:8000';
  return {
    plugins: [react(), tailwindcss()],
    resolve: { alias: { '@': path.resolve(import.meta.dirname, 'src') } },
    server: {
      port: Number(env.ATX_WEB_PORT || 5173),
      strictPort: true,
      proxy: { '/api': { target: apiTarget, changeOrigin: false } },
    },
    preview: {
      port: Number(env.ATX_WEB_PORT || 5173),
      strictPort: true,
      proxy: { '/api': { target: apiTarget, changeOrigin: false } },
      headers: {
        'Content-Security-Policy': CSP,
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer',
        'X-Frame-Options': 'DENY',
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            react: ['react', 'react-dom', 'react-router-dom'],
            data: ['@tanstack/react-query', '@tanstack/react-table', 'zustand', 'zod', 'react-hook-form'],
            ui: ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu', '@radix-ui/react-tabs', 'sonner', 'lucide-react'],
            i18n: ['i18next', 'react-i18next'],
          },
        },
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      css: false,
    },
  };
});
