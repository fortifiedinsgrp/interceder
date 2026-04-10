import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../src/interceder/gateway/static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/ws': {
        target: 'ws://127.0.0.1:7878',
        ws: true,
      },
      '/health': 'http://127.0.0.1:7878',
    },
  },
})
