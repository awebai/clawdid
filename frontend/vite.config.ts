import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const port = Number(process.env.VITE_PORT ?? 18113)

export default defineConfig({
  plugins: [react()],
  server: {
    port,
  },
})

