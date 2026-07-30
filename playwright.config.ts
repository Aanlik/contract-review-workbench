import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    headless: true,
  },
  webServer: [
    {
      command: ".venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend",
      port: 8000,
      reuseExistingServer: true,
      timeout: 30000,
    },
    {
      command: "cd frontend && npm run dev",
      port: 5173,
      reuseExistingServer: true,
      timeout: 30000,
    },
  ],
});
