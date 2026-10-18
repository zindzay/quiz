import type { Page, Route } from '@playwright/test';

export type Card = { id: string; question: string; answer: string };

// Фиксированные данные: скриншоты не зависят от содержимого хранилища и случайных id.
export const CARDS: Card[] = [
  {
    id: '00000000-0000-4000-8000-000000000001',
    question: 'Что такое HTTP?',
    answer: 'Протокол прикладного уровня для передачи данных по схеме «запрос — ответ».',
  },
  {
    id: '00000000-0000-4000-8000-000000000002',
    question:
      'Чем отличаются коды ответа 401 и 403, и в каких ситуациях сервер должен возвращать каждый из них? Приведите пример для каждого случая.',
    answer:
      '401 Unauthorized — клиент не аутентифицирован: нужно передать учётные данные.\n' +
      '403 Forbidden — клиент известен, но прав на ресурс у него нет.\n' +
      'Пример: запрос без токена → 401; пользователь без роли администратора открывает админку → 403.',
  },
  {
    id: '00000000-0000-4000-8000-000000000003',
    question: '<b>жирный</b><script>alert(1)</script>',
    answer: 'Разметка в тексте карточки выводится буквально.',
  },
];

/** GET /api/cards отдаёт заданный список. */
export async function mockCardList(page: Page, cards: Card[]): Promise<void> {
  await page.route('**/api/cards', (route) =>
    route.request().method() === 'GET' ? route.fulfill({ json: cards }) : route.fallback(),
  );
}

/** POST /api/cards отвечает 400 с заданным сообщением. */
export async function mockCreateError(page: Page, error: string): Promise<void> {
  await page.route('**/api/cards', (route: Route) =>
    route.request().method() === 'POST' ? route.fulfill({ status: 400, json: { error } }) : route.fallback(),
  );
}

/** Любой запрос к /api/cards обрывается сетевой ошибкой. */
export async function mockNetworkFailure(page: Page): Promise<void> {
  await page.route('**/api/cards', (route) => route.abort('connectionrefused'));
}
