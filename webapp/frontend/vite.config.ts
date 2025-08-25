import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  
  // Configurazione per integrazione con Flask backend
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/health': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/download': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/static': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000', 
        changeOrigin: true,
        secure: false
      }
    }
  },
  
  // Build output per integrazione con Flask
  build: {
    outDir: '../static/react',
    emptyOutDir: true,
    
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html')
      },
      output: {
        entryFileNames: 'js/[name].[hash].js',
        chunkFileNames: 'js/[name].[hash].js',
        assetFileNames: (assetInfo) => {
          const ext = assetInfo.name?.split('.').pop()
          if (ext === 'css') return 'css/[name].[hash].css'
          if (['png', 'jpg', 'jpeg', 'svg', 'gif'].includes(ext || '')) {
            return 'images/[name].[hash].[ext]'
          }
          return 'assets/[name].[hash].[ext]'
        }
      }
    },
    
    // Chunk optimization
    chunkSizeWarningLimit: 1000,
    
    // Source maps per debugging
    sourcemap: process.env.NODE_ENV === 'development'
  },
  
  // Risoluzione path
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@stores': resolve(__dirname, 'src/stores'),
      '@types': resolve(__dirname, 'src/types'),
      '@utils': resolve(__dirname, 'src/utils'),
      '@api': resolve(__dirname, 'src/api')
    }
  },
  
  // Configurazione CSS
  css: {
    postcss: './postcss.config.js',
    modules: {
      localsConvention: 'camelCase'
    }
  },
  
  // Ottimizzazioni
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString())
  },
  
  // Gestione environment variables
  envPrefix: ['VITE_', 'REACT_APP_']
})
