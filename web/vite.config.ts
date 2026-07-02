import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    modulePreload: {
      resolveDependencies(_filename, deps) {
        return deps.filter((dep) => !dep.includes('deck-gl'))
      }
    },
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (
            id.includes('/@deck.gl/') ||
            id.includes('/@luma.gl/') ||
            id.includes('/@loaders.gl/') ||
            id.includes('/@math.gl/') ||
            id.includes('/@probe.gl/')
          ) {
            return 'deck-gl'
          }
          if (id.includes('/maplibre-gl/')) return 'maplibre'
          if (id.includes('/naive-ui/') || id.includes('/@css-render/') || id.includes('/vueuc/')) return 'ui'
          if (id.includes('/lucide-vue-next/')) return 'icons'
          if (id.includes('/vue/') || id.includes('/pinia/')) return 'vue-vendor'
          return 'vendor'
        }
      }
    }
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: false
  },
  test: {
    environment: 'jsdom',
    globals: true
  }
})
