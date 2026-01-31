import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    host: true,
  },
  preview: {
    port: 3001,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  define: {
    // Allow runtime environment variable injection
    'import.meta.env.VITE_BACKEND_URL': JSON.stringify(process.env.VITE_BACKEND_URL || ''),
  },
})
