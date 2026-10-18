import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The Python API (perceived_oversight.explorer) runs on 127.0.0.1:8765; the app calls /api/*.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8765', rewrite: (path) => path.replace(/^\/api/, '') },
    },
  },
})
