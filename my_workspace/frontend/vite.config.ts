import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = env.VITE_BACKEND_URL || 'http://localhost:8000'

  return {
    plugins: [vue(), tailwindcss()],
    resolve: {
      alias: { '@': resolve(__dirname, 'src') },
    },
    server: {
      port: 5173,
      proxy: {
        // MJPEG streams are long-lived — no timeout, no buffering
        '/api/v1/cameras': {
          target: backendUrl,
          changeOrigin: true,
          proxyTimeout: 0,    // never time out camera streams
          timeout: 0,
        },
        '/api': {
          target: backendUrl,
          changeOrigin: true,
          ws: true,           // upgrade WebSocket connections under /api (includes /api/v1/ws)
        },
      },
    },
  }
})
