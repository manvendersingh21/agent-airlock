import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30000,
  use: {
    baseURL: 'http://127.0.0.1:8000',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'cd .. && .venv/bin/python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000',
    url: 'http://127.0.0.1:8000/healthz',
    reuseExistingServer: !process.env.CI,
    timeout: 15000,
  },
});
