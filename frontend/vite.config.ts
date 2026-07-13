import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "GyanVriksh — Tree of Knowledge",
        short_name: "GyanVriksh",
        description: "AI-Powered Industrial Knowledge Intelligence",
        theme_color: "#0A1628",
        background_color: "#0A1628",
        display: "standalone",
        icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }],
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: /\/api\/v1\/copilot\/history/,
            handler: "NetworkFirst",
            options: { cacheName: "copilot-cache", expiration: { maxEntries: 50 } },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      // Use 127.0.0.1 (not "localhost") — on Windows localhost resolves to IPv6
      // (::1) first, but uvicorn binds IPv4 127.0.0.1, so proxied API requests
      // silently fail to connect. 127.0.0.1 forces IPv4 and reaches the backend.
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:8000", ws: true, changeOrigin: true },
    },
  },
});
