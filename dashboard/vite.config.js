import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 0.0.0.0 listens on all interfaces (required for tunnels)
    host: '0.0.0.0', 
    // Allow localtunnel domains
    allowedHosts: ['.loca.lt', 'localhost', '127.0.0.1'],
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/videos': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
})
