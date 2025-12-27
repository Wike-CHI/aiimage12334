import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// 从环境变量读取 API 地址，如果没有设置则报错
const API_URL = process.env.VITE_API_URL || 'http://localhost:8001';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: Number(process.env.VITE_PORT) || 8080,
    proxy: {
      "/api": {
        target: API_URL,
        changeOrigin: true,
      },
      "/uploads": {
        target: API_URL,
        changeOrigin: true,
      },
      "/results": {
        target: API_URL,
        changeOrigin: true,
      },
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
