import { defineConfig, devices } from '@playwright/test';

// Поведенческие тесты сценариев cards-web-ui на настоящем API.
// Без webServer: каждый тест поднимает собственный экземпляр приложения (фикстура app в e2e/app-fixture.ts).
export default defineConfig({
  testDir: 'e2e',
  outputDir: 'test-results-e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report-e2e' }]],
  use: {
    ...devices['Desktop Chrome'],
    viewport: { width: 1280, height: 800 },
    locale: 'ru-RU',
    trace: 'retain-on-failure',
  },
});
