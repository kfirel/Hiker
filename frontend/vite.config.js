import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Don't use base in dev - causes 404. Only for production build.
  base: process.env.NODE_ENV === 'production' ? '/admin/' : '/',
  server: {
    port: 3000,
    open: true,  // Auto-open browser
    proxy: {
      // Proxy all API requests to backend
      '/a': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        timeout: 60000  // 60 seconds
      },
      // Also proxy webhooks if testing locally
      '/webhook': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        timeout: 60000  // 60 seconds
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    // Force hash in filenames for cache busting
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]'
      }
    }
  }
})

