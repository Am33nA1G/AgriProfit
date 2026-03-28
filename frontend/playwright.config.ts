import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:3000',
    // Headless by default; set HEADED=1 env var to run headed for debugging
    headless: process.env.HEADED !== '1' && process.env.HEADED !== 'true',
    screenshot: 'only-on-failure',
    video: 'off',
    // Wait up to 10s for API responses (backend + ML serving)
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // Do NOT start a dev server automatically — tests assume servers are already running.
  // Start them manually: backend uvicorn + frontend npm run dev
});
