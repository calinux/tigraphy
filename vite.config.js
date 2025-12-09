import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    lib: {
      // Entry point for the library
      entry: resolve(__dirname, 'src/index.js'),
      name: 'Tigraphy',
      // Output file names for different formats
      fileName: (format) => `tigraphy.${format === 'es' ? 'js' : 'umd.cjs'}`
    },
    rollupOptions: {
      // Externalize peer dependencies
      external: ['react', 'react-dom'],
      output: {
        // Global variables to use in UMD build for externalized deps
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM'
        }
      }
    }
  }
})
