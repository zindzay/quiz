import type { Page, Route } from '@playwright/test';

export type Card = { id: string; question: string; answer: string; review: boolean };

// Фиксированные данные: скриншоты не зависят от содержимого хранилища и случайных id.
export const CARDS: Card[] = [
  {
    id: '00000000-0000-4000-8000-000000000001',
    question: 'Что такое HTTP?',
    answer: 'Протокол прикладного уровня для передачи данных по схеме «запрос — ответ».',
    review: false,
  },
  {
    id: '00000000-0000-4000-8000-000000000002',
    question:
      'Чем отличаются коды ответа 401 и 403, и в каких ситуациях сервер должен возвращать каждый из них? Приведите пример для каждого случая.',
    answer:
      '401 Unauthorized — клиент не аутентифицирован: нужно передать учётные данные.\n' +
      '403 Forbidden — клиент известен, но прав на ресурс у него нет.\n' +
      'Пример: запрос без токена → 401; пользователь без роли администратора открывает админку → 403.',
    review: true,
  },
  {
    id: '00000000-0000-4000-8000-000000000003',
    question: '<b>жирный</b><script>alert(1)</script>',
    answer: 'Разметка в тексте карточки выводится буквально.',
    review: false,
  },
];

/** Вопрос предельной длины для проверки прокрутки внутри квадратной карточки теста. */
export const LONG_CARD: Card = {
  id: '00000000-0000-4000-8000-000000000004',
  question: Array.from({ length: 24 }, (_, i) => `Длинный вопрос, строка ${i + 1}: проверка прокрутки внутри карточки.`).join(' '),
  answer: 'Ответ на длинный вопрос.',
  review: false,
};

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

/** GET /api/cards/random отдаёт заданный набор (вместо случайного), PUT .../review подтверждает отметку. */
export async function mockQuiz(page: Page, cards: Card[]): Promise<void> {
  await page.route((url) => url.pathname === '/api/cards/random', (route) => route.fulfill({ json: cards }));
  await page.route('**/api/cards/*/review', (route) => {
    const id = new URL(route.request().url()).pathname.split('/')[3];
    const card = cards.find((c) => c.id === id);
    return route.fulfill({ json: { ...card, review: route.request().postDataJSON().review } });
  });
}

/** Запрос набора для теста обрывается сетевой ошибкой. */
export async function mockQuizNetworkFailure(page: Page): Promise<void> {
  await page.route((url) => url.pathname === '/api/cards/random', (route) => route.abort('connectionrefused'));
}

/** POST /api/cards отвечает 201 с созданной карточкой. */
export async function mockCreateSuccess(page: Page): Promise<void> {
  await page.route('**/api/cards', (route: Route) =>
    route.request().method() === 'POST'
      ? route.fulfill({ status: 201, json: { ...CARDS[0], ...route.request().postDataJSON() } })
      : route.fallback(),
  );
}

/** DELETE /api/cards/{id} обрывается сетевой ошибкой. */
export async function mockDeleteFailure(page: Page): Promise<void> {
  await page.route('**/api/cards/*', (route) =>
    route.request().method() === 'DELETE' ? route.abort('connectionrefused') : route.fallback(),
  );
}
