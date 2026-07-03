import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// A unified configuration combining both the React and Tailwind v4 engine plugins
export default defineConfig({
  plugins: [
    react(),
    tailwindcss()
  ],
})