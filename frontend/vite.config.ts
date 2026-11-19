import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

// Operator-only routes live under /internal and must never be reachable from the
// browser, so answer 404 here instead of falling through to the SPA index page.
const blockInternal: Plugin = {
  name: "block-internal",
  configureServer(server) {
    server.middlewares.use("/internal", (_req, res) => {
      res.statusCode = 404;
      res.end("Not found");
    });
  },
};

export default defineConfig({
  plugins: [react(), blockInternal],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": "http://backend:8000",
    },
  },
});
