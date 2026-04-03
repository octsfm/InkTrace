import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  base: './',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9527',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('element-plus')) return 'ui-element-plus'
          if (id.includes('@element-plus/icons-vue')) return 'ui-element-icons'
          if (id.includes('vue-router')) return 'vendor-vue-router'
          if (id.includes('pinia')) return 'vendor-pinia'
          if (id.includes('axios')) return 'vendor-axios'
          if (id.includes('/vue/')) return 'vendor-vue-core'
        }
      }
    }
  }
})
