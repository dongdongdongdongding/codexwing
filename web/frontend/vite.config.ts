import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 개발: /api → FastAPI(8800) 프록시. 운영선 백엔드가 정적빌드 서빙.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8800" },
  },
  build: { outDir: "dist" },
});
