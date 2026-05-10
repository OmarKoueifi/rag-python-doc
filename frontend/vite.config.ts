import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, same-origin /api calls are proxied to the FastAPI backend so
// cookies work without any CORS/SameSite ceremony. In prod, the frontend
// is deployed on Vercel and /api is rewritten to the Render backend
// (see vercel.json).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/healthz": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    sourcemap: true,
    chunkSizeWarningLimit: 1000,
  },
});
