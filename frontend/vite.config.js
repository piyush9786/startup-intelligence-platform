import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget =
    env.VITE_DEV_PROXY_TARGET || "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
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
