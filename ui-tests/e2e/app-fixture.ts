import { spawn, type ChildProcess } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { test as base } from '@playwright/test';

export type Card = { id: string; question: string; answer: string };

export type App = {
  baseURL: string;
  /** Создаёт карточку через настоящий API (подготовка данных теста). */
  createCard(question: string, answer: string): Promise<Card>;
  /** Текущее содержимое хранилища через GET /api/cards. */
  listCards(): Promise<Card[]>;
  /** Останавливает приложение (для сценария «сервер недоступен»). Повторный вызов ничего не делает. */
  stop(): Promise<void>;
};

const jar = process.env.QUIZ_JAR ?? path.resolve(__dirname, '../../build/libs/quiz-1.0-SNAPSHOT.jar');
const STARTUP_TIMEOUT_MS = 30_000;

// Страховка от повисших JVM, если воркер Playwright завершится аварийно, минуя teardown.
const running = new Set<ChildProcess>();
process.on('exit', () => running.forEach((proc) => proc.kill('SIGKILL')));

function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on('error', reject);
    server.listen(0, () => {
      const { port } = server.address() as net.AddressInfo;
      server.close(() => resolve(port));
    });
  });
}

async function waitUntilReady(baseURL: string, proc: ChildProcess, stderr: () => string): Promise<void> {
  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (proc.exitCode !== null) {
      throw new Error(`Приложение завершилось при старте (код ${proc.exitCode}):\n${stderr()}`);
    }
    try {
      const response = await fetch(`${baseURL}/api/cards`);
      if (response.ok) return;
    } catch {
      // ещё не слушает порт
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Приложение не ответило за ${STARTUP_TIMEOUT_MS} мс:\n${stderr()}`);
}

function stopProcess(proc: ChildProcess): Promise<void> {
  if (proc.exitCode !== null || proc.signalCode !== null) return Promise.resolve();
  return new Promise((resolve) => {
    const killTimer = setTimeout(() => proc.kill('SIGKILL'), 5_000);
    proc.once('exit', () => {
      clearTimeout(killTimer);
      resolve();
    });
    proc.kill('SIGTERM');
  });
}

export const test = base.extend<{ app: App }>({
  app: async ({}, use, testInfo) => {
    const port = await freePort();
    const baseURL = `http://localhost:${port}`;
    const dataFile = path.join(os.tmpdir(), `quiz-e2e-${process.pid}-${testInfo.testId}-${Date.now()}.csv`);

    // Аргументы командной строки имеют приоритет над application.properties — data/ не затрагивается.
    const proc = spawn('java', ['-jar', jar, `--server.port=${port}`, `--quiz.data-file=${dataFile}`], {
      stdio: ['ignore', 'ignore', 'pipe'],
    });
    running.add(proc);
    proc.once('exit', () => running.delete(proc));
    let stderr = '';
    proc.stderr?.on('data', (chunk) => (stderr += chunk));

    try {
      await waitUntilReady(baseURL, proc, () => stderr);

      await use({
        baseURL,
        async createCard(question, answer) {
          const response = await fetch(`${baseURL}/api/cards`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, answer }),
          });
          if (response.status !== 201) {
            throw new Error(`POST /api/cards вернул ${response.status}: ${await response.text()}`);
          }
          return (await response.json()) as Card;
        },
        async listCards() {
          return (await (await fetch(`${baseURL}/api/cards`)).json()) as Card[];
        },
        stop: () => stopProcess(proc),
      });
    } finally {
      await stopProcess(proc);
      fs.rmSync(dataFile, { force: true });
    }
  },

  // page.goto('/') ведёт на экземпляр приложения этого теста.
  baseURL: async ({ app }, use) => {
    await use(app.baseURL);
  },
});

export { expect } from '@playwright/test';
