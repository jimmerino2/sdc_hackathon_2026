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
  },
  preview: { port: Number(process.env.PORT ?? 5173), host: '0.0.0.0', allowedHosts: true },
});
