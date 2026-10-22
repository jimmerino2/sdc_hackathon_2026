import path from 'path';
import vue from '@vitejs/plugin-vue';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, 'src') } },
  server: {
    port: Number(process.env.PORT ?? 5173),
    host: '0.0.0.0',
    allowedHosts: true,
    // Dev only: the browser calls /api on this same origin and Vite forwards it to the backend,
    // so the Replit preview link works without CORS or exposing port 8000.
    proxy: {
      '/api': {
        target: process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
  preview: { port: Number(process.env.PORT ?? 5173), host: '0.0.0.0', allowedHosts: true },
});
