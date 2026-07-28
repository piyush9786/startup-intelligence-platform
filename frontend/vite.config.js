import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget =
    env.VITE_DEV_PROXY_TARGET || "http://localhost:8000";

  return {
    build: {
      outDir: "dist",
    },
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      strictPort: true,
      watch: {
        usePolling: env.VITE_USE_POLLING === "true",
        interval: 250,
      },
      proxy: {
        "/admin": {
          changeOrigin: true,
          target: proxyTarget,
        },
        "/api": {
          changeOrigin: true,
          target: proxyTarget,
        },
        "/media": {
          changeOrigin: true,
          target: proxyTarget,
        },
        "/static": {
          changeOrigin: true,
          target: proxyTarget,
        },
      },
    },
  };
});
