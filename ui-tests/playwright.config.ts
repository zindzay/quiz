import os from 'node:os';
import path from 'node:path';
import { defineConfig, devices } from '@playwright/test';

// Конфиг загружается и в главном процессе, и в воркерах: значения фиксируются через env,
// чтобы все процессы видели один и тот же файл данных.
process.env.QUIZ_UI_DATA_FILE ??= path.join(os.tmpdir(), `quiz-ui-tests-${process.pid}-${Date.now()}.csv`);

const port = Number(process.env.QUIZ_UI_TEST_PORT ?? 18080);
const jar = process.env.QUIZ_JAR ?? path.resolve(__dirname, '../build/libs/quiz-1.0-SNAPSHOT.jar');
const baseURL = `http://localhost:${port}`;

const desktop = { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 };

export default defineConfig({
  testDir: 'tests',
  snapshotPathTemplate: '{testDir}/__screenshots__/{testFilePath}/{arg}-{projectName}-{platform}{ext}',
  globalTeardown: './global-teardown.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL,
    locale: 'ru-RU',
    trace: 'retain-on-failure',
  },
  expect: {
    toHaveScreenshot: {
      animations: 'disabled',
      caret: 'hide',
      maxDiffPixelRatio: 0.001,
    },
  },
  // Тесты помечаются тегами @dark и @mobile; без тега — светлая тема на десктопе.
  projects: [
    { name: 'desktop-light', use: { ...desktop, colorScheme: 'light' }, grepInvert: /@dark|@mobile/ },
    { name: 'desktop-dark', use: { ...desktop, colorScheme: 'dark' }, grep: /@dark/ },
    {
      name: 'mobile',
      use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true, colorScheme: 'light' },
      grep: /@mobile/,
    },
  ],
  webServer: {
    // Аргументы командной строки имеют приоритет над application.properties, данные пользователя не затрагиваются.
    command: `java -jar "${jar}" --server.port=${port} --quiz.data-file="${process.env.QUIZ_UI_DATA_FILE}"`,
    url: `${baseURL}/api/cards`,
    reuseExistingServer: false,
    timeout: 60_000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
});
