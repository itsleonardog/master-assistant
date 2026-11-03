import { fileURLToPath, URL } from 'node:url'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // The SPA is served from "/" by FastAPI in production, so assets resolve
  // from "/assets/..." and no base path prefix is needed.
  base: '/',
  resolve: {
    // Mirrors the "@/*" -> "./src/*" alias declared in tsconfig.app.json.
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    // Build straight into the directory FastAPI mounts as static files.
    // emptyOutDir must be explicit because the target lives outside the root,
    // and it removes the legacy index.html/app.js/style.css on first build.
    outDir: '../backend/master_assistant/api/static',
    emptyOutDir: true,
  },
  server: {
    // Dev server on :5173 forwards API calls to uvicorn on :8000.
    proxy: {
      '/analyze': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
