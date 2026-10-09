import { resolve } from "node:path";

import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [vue()],
  server: {
    // Same-origin in dev too: the browser talks to Vite, Vite forwards /api
    // to the local backend, so no CORS configuration is needed anywhere.
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(import.meta.dirname, "index.html"),
        // Separate entry so the silent-renew iframe (see src/silent-renew.ts)
        // loads a minimal script instead of bootstrapping the whole SPA.
        "silent-renew": resolve(import.meta.dirname, "silent-renew.html"),
      },
    },
  },
});
