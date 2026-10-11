import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Served from https://haitheredavid.github.io/bless/ (override with BLESS_BASE).
export default defineConfig({
  base: process.env.BLESS_BASE ?? "/bless/",
  plugins: [react()],
  build: { chunkSizeWarningLimit: 1200 }, // the lazy Viewer chunk is three.js
});
