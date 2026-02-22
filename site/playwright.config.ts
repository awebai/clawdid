import { defineConfig } from '@playwright/test'

const PORT = Number(process.env.SITE_PORT ?? 18114)

export default defineConfig({
  testDir: './tests',
  use: {
    baseURL: `http://localhost:${PORT}`,
  },
  webServer: {
    command: `hugo server --port ${PORT} --bind 127.0.0.1`,
    port: PORT,
    reuseExistingServer: true,
  },
})

