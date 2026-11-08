import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Fonts must NEVER be inlined as data: URIs — the CSP is
    // font-src 'self' (no data:), so an inlined woff2 gets blocked
    // by the browser. Serving them as files keeps the CSP minimal
    // and artifact-faithful. (CSP-vs-build seam, live-reported.)
    assetsInlineLimit: 0,
  },
});
