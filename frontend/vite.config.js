import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

const DEV_BACKEND_PORT = Number(process.env.VITE_BACKEND_PORT) || 18700

export default defineConfig({
  plugins: [vue()],
  base: '/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@icon': path.resolve(__dirname, '../icon')
    }
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      '/api': {
        target: `http://localhost:${DEV_BACKEND_PORT}`,
        changeOrigin: true
      }
    }
  }
})
