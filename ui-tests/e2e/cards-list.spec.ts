import type { Page } from '@playwright/test';
import { expect, test, type App } from './app-fixture';

/** Карточки — элементы списка; внутри каждой кнопка раскрытия (с текстом вопроса) и кнопки удаления. */
const cards = (page: Page) => page.getByRole('list').getByRole('listitem');

/** Панель страниц списка (nav, не список). */
const pages = (page: Page) => page.getByRole('navigation', { name: 'Страницы списка' });

/** Вопрос карточки с номером n: «Карточка 07» — с нулём, чтобы «Карточка 1» не находила «Карточка 10». */
const question = (n: number) => `Карточка ${String(n).padStart(2, '0')}`;

/** Создаёт карточки 1…count в порядке номеров. */
async function createCards(app: App, count: number) {
  for (let n = 1; n <= count; n++) {
    await app.createCard(question(n), `Ответ ${n}`);
  }
}

/** Карточки на странице — ровно с номерами from…to и своими вопросами. */
async function expectNumbers(page: Page, from: number, to: number) {
  const numbers = Array.from({ length: to - from + 1 }, (_, i) => from + i);
  await expect(cards(page)).toHaveText(numbers.map((n) => new RegExp(`^\\s*${n}\\.\\s*${question(n)}`)));
}

// Сценарии страницы всех карточек (/cards.html) из openspec/specs/cards-web-ui/spec.md на настоящем приложении.

test.describe('Страница всех карточек', () => {
  test('Открытие страницы: вопросы в порядке добавления, ответы скрыты', async ({ app, page }) => {
    await app.createCard('Первый вопрос', 'Первый ответ');
    await app.createCard('Второй вопрос', 'Второй ответ');
    await app.createCard('Третий вопрос', 'Третий ответ');

    await page.goto('/cards.html');

    await expect(cards(page)).toHaveText([/Первый вопрос/, /Второй вопрос/, /Третий вопрос/]);
    for (const answer of ['Первый ответ', 'Второй ответ', 'Третий ответ']) {
      await expect(page.getByText(answer)).toBeHidden();
    }
  });

  test('Нет карточек: сообщение о пустом списке и ссылка на добавление', async ({ page }) => {
    await page.goto('/cards.html');

    await expect(page.getByText('Карточек пока нет')).toBeVisible();
    await expect(cards(page)).toHaveCount(0);

    await page.getByRole('main').getByRole('link', { name: 'Добавить карточку' }).click();
    await expect(page).toHaveURL(/\/add\.html$/);
  });
});

test.describe('Номера карточек', () => {
  test('Номера карточек: позиция в порядке добавления', async ({ app, page }) => {
    await createCards(app, 3);

    await page.goto('/cards.html');

    await expectNumbers(page, 1, 3);
    await expect(cards(page).getByText(/^\d+\.$/)).toHaveText(['1.', '2.', '3.']);
  });
});

test.describe('Страницы списка карточек', () => {
  test('Первая страница', async ({ app, page }) => {
    await createCards(app, 25);

    await page.goto('/cards.html');

    await expectNumbers(page, 1, 10);
    await expect(pages(page).getByRole('link', { name: '1', exact: true })).toHaveAttribute('aria-current', 'page');
    await expect(pages(page).getByRole('link', { name: 'Назад' })).toHaveAttribute('aria-disabled', 'true');
    await expect(pages(page).getByRole('link', { name: 'Вперёд' })).not.toHaveAttribute('aria-disabled', 'true');
  });

  test('Переход на следующую страницу', async ({ app, page }) => {
    await createCards(app, 25);
    await page.goto('/cards.html');
    await expectNumbers(page, 1, 10);

    await pages(page).getByRole('link', { name: 'Вперёд' }).click();

    await expectNumbers(page, 11, 20);
    await expect(pages(page).getByRole('link', { name: '2', exact: true })).toHaveAttribute('aria-current', 'page');
    await expect(pages(page).getByRole('link', { name: '1', exact: true })).not.toHaveAttribute('aria-current');
    expect(new URL(page.url()).pathname + new URL(page.url()).search).toBe('/cards.html?page=2');
  });

  test('Переход по номеру страницы', async ({ app, page }) => {
    await createCards(app, 25);
    await page.goto('/cards.html');
    await expectNumbers(page, 1, 10);

    await pages(page).getByRole('link', { name: '3', exact: true }).click();

    await expectNumbers(page, 21, 25);
    await expect(pages(page).getByRole('link', { name: 'Вперёд' })).toHaveAttribute('aria-disabled', 'true');
    await expect(pages(page).getByRole('link', { name: 'Назад' })).not.toHaveAttribute('aria-disabled', 'true');
  });

  test('Не больше 10 карточек: панели страниц нет', async ({ app, page }) => {
    await createCards(app, 10);

    await page.goto('/cards.html');

    await expectNumbers(page, 1, 10);
    await expect(pages(page)).toBeHidden();
  });
});

test.describe('Сокращённая панель страниц', () => {
  test('Много страниц', async ({ app, page }) => {
    await createCards(app, 95);

    await page.goto('/cards.html?page=5');

    await expectNumbers(page, 41, 50);
    await expect(pages(page).getByRole('link')).toHaveText(['Назад', '1', '4', '5', '6', '10', 'Вперёд']);
    await expect(pages(page).getByText('…')).toHaveCount(2);
    // «…» стоят между 1 и 4 и между 6 и 10.
    await expect(pages(page)).toHaveText(/^\s*Назад\s*1\s*…\s*4\s*5\s*6\s*…\s*10\s*Вперёд\s*$/);
  });
});

test.describe('Номер страницы в адресе', () => {
  test('Перезагрузка страницы списка', async ({ app, page }) => {
    await createCards(app, 25);
    await page.goto('/cards.html');
    await pages(page).getByRole('link', { name: '2', exact: true }).click();
    await expectNumbers(page, 11, 20);

    await page.reload();

    await expectNumbers(page, 11, 20);
  });

  test('Кнопка «Назад» браузера', async ({ app, page }) => {
    await createCards(app, 25);
    await page.goto('/cards.html');
    await pages(page).getByRole('link', { name: 'Вперёд' }).click();
    await expectNumbers(page, 11, 20);

    await page.goBack();

    await expectNumbers(page, 1, 10);
    await expect(pages(page).getByRole('link', { name: '1', exact: true })).toHaveAttribute('aria-current', 'page');

    await page.goForward();

    await expectNumbers(page, 11, 20);
  });

  test('Номер страницы вне диапазона', async ({ app, page }) => {
    await createCards(app, 25);

    await page.goto('/cards.html?page=9');

    await expectNumbers(page, 21, 25);
    await expect(pages(page).getByRole('link', { name: '3', exact: true })).toHaveAttribute('aria-current', 'page');
    await expect(page).toHaveURL(/\/cards\.html\?page=3$/);
  });

  test('Нечисловой номер страницы', async ({ app, page }) => {
    await createCards(app, 25);

    await page.goto('/cards.html?page=abc');

    await expectNumbers(page, 1, 10);
    await expect(pages(page).getByRole('link', { name: '1', exact: true })).toHaveAttribute('aria-current', 'page');
  });
});

test.describe('Раскрытие ответа', () => {
  test('Показ и скрытие ответа', async ({ app, page }) => {
    await app.createCard('Вопрос 1', 'Ответ 1');
    await app.createCard('Вопрос 2', 'Ответ 2');
    await app.createCard('Вопрос 3', 'Ответ 3');
    await page.goto('/cards.html');

    const second = page.getByRole('button', { name: /Вопрос 2/ });
    await second.click();

    await expect(page.getByText('Ответ 2')).toBeVisible();
    await expect(second).toHaveAttribute('aria-expanded', 'true');
    await expect(page.getByText('Ответ 1')).toBeHidden();
    await expect(page.getByText('Ответ 3')).toBeHidden();

    await second.click();

    await expect(page.getByText('Ответ 2')).toBeHidden();
    await expect(second).toHaveAttribute('aria-expanded', 'false');
  });
});

test.describe('Безопасный вывод текста', () => {
  test('HTML в тексте карточки выводится буквально', async ({ app, page }) => {
    const markup = '<b>жирный</b><script>alert(1)</script>';
    await app.createCard(markup, 'ответ');
    let dialogShown = false;
    page.on('dialog', async (dialog) => {
      dialogShown = true;
      await dialog.dismiss();
    });

    await page.goto('/cards.html');

    const card = cards(page);
    await expect(card.getByText(markup, { exact: true })).toBeVisible();
    await expect(card.locator('b, script')).toHaveCount(0);
    expect(dialogShown).toBe(false);
  });
});

test.describe('Удаление карточки в списке', () => {
  const card = (page: Page, question: string) => cards(page).filter({ hasText: question });

  test('Подтверждение удаления', async ({ app, page }) => {
    await app.createCard('Вопрос 1', 'Ответ 1');
    await page.goto('/cards.html');

    await card(page, 'Вопрос 1').getByRole('button', { name: 'Удалить' }).click();

    await expect(card(page, 'Вопрос 1').getByText('Удалить карточку?')).toBeVisible();
    await expect(card(page, 'Вопрос 1').getByRole('button', { name: 'Да' })).toBeVisible();
    await expect(card(page, 'Вопрос 1').getByRole('button', { name: 'Отмена' })).toBeFocused();
    await expect(card(page, 'Вопрос 1').getByRole('button', { name: 'Удалить', exact: true })).toBeHidden();
    await expect(cards(page)).toHaveCount(1);
    expect((await app.listCards()).map((c) => c.question)).toEqual(['Вопрос 1']);
  });

  test('Удаление после подтверждения', async ({ app, page }) => {
    await app.createCard('Вопрос 1', 'Ответ 1');
    await app.createCard('Вопрос 2', 'Ответ 2');
    await app.createCard('Вопрос 3', 'Ответ 3');
    await page.goto('/cards.html');

    await card(page, 'Вопрос 2').getByRole('button', { name: 'Удалить' }).click();
    await card(page, 'Вопрос 2').getByRole('button', { name: 'Да' }).click();

    await expect(cards(page)).toHaveText([/Вопрос 1/, /Вопрос 3/]);
    expect((await app.listCards()).map((c) => c.question)).toEqual(['Вопрос 1', 'Вопрос 3']);

    await page.reload();
    await expect(cards(page)).toHaveText([/Вопрос 1/, /Вопрос 3/]);
  });

  test('Отмена удаления', async ({ app, page }) => {
    await app.createCard('Вопрос 1', 'Ответ 1');
    await page.goto('/cards.html');

    await card(page, 'Вопрос 1').getByRole('button', { name: 'Удалить' }).click();
    await card(page, 'Вопрос 1').getByRole('button', { name: 'Отмена' }).click();

    await expect(page.getByText('Удалить карточку?')).toBeHidden();
    await expect(card(page, 'Вопрос 1').getByRole('button', { name: 'Удалить' })).toBeFocused();
    await expect(cards(page)).toHaveCount(1);
    expect((await app.listCards()).map((c) => c.question)).toEqual(['Вопрос 1']);
  });

  test('Удалена последняя карточка', async ({ app, page }) => {
    await app.createCard('Вопрос 1', 'Ответ 1');
    await page.goto('/cards.html');

    await card(page, 'Вопрос 1').getByRole('button', { name: 'Удалить' }).click();
    await card(page, 'Вопрос 1').getByRole('button', { name: 'Да' }).click();

    await expect(page.getByText('Карточек пока нет')).toBeVisible();
    await expect(page.getByRole('main').getByRole('link', { name: 'Добавить карточку' })).toBeVisible();
    await expect(cards(page)).toHaveCount(0);
  });

  test('Кнопка удаления не раскрывает ответ', async ({ app, page }) => {
    await app.createCard('Вопрос 1', 'Ответ 1');
    await page.goto('/cards.html');

    await card(page, 'Вопрос 1').getByRole('button', { name: 'Удалить' }).click();
    await expect(page.getByText('Ответ 1')).toBeHidden();
    await card(page, 'Вопрос 1').getByRole('button', { name: 'Отмена' }).click();

    await expect(page.getByText('Ответ 1')).toBeHidden();
    await expect(page.getByRole('button', { name: /Вопрос 1/ })).toHaveAttribute('aria-expanded', 'false');
  });
});

test.describe('Ошибка удаления карточки', () => {
  test('Сервер недоступен при удалении', async ({ app, page }) => {
    await app.createCard('Вопрос 1', 'Ответ 1');
    await page.goto('/cards.html');
    const item = cards(page).filter({ hasText: 'Вопрос 1' });
    await item.getByRole('button', { name: 'Удалить' }).click();

    await app.stop();
    await item.getByRole('button', { name: 'Да' }).click();

    await expect(item.getByRole('alert')).toHaveText(/Не удалось удалить карточку/);
    await expect(cards(page)).toHaveCount(1);
    await expect(item.getByRole('button', { name: 'Удалить' })).toBeEnabled();
    await expect(page.getByText('Удалить карточку?')).toBeHidden();
  });
});

test.describe('Удаление на странице списка', () => {
  const remove = async (page: Page, n: number) => {
    const item = cards(page).filter({ hasText: question(n) });
    await item.getByRole('button', { name: 'Удалить' }).click();
    await item.getByRole('button', { name: 'Да' }).click();
  };

  test('Удаление на первой из нескольких страниц', async ({ app, page }) => {
    await createCards(app, 25);
    await page.goto('/cards.html');
    await expectNumbers(page, 1, 10);

    await remove(page, 3);

    const expected = [1, 2, 4, 5, 6, 7, 8, 9, 10, 11].map(
      (n, i) => new RegExp(`^\\s*${i + 1}\\.\\s*${question(n)}`),
    );
    await expect(cards(page)).toHaveText(expected);
    expect((await app.listCards()).map((c) => c.question)).not.toContain(question(3));
  });

  test('Удалена единственная карточка последней страницы', async ({ app, page }) => {
    await createCards(app, 21);
    await page.goto('/cards.html?page=3');
    await expectNumbers(page, 21, 21);

    await remove(page, 21);

    await expectNumbers(page, 11, 20);
    await expect(pages(page).getByRole('link', { name: '2', exact: true })).toHaveAttribute('aria-current', 'page');
    await expect(pages(page).getByRole('link', { name: '3', exact: true })).toHaveCount(0);
    await expect(page).toHaveURL(/\/cards\.html\?page=2$/);
  });
});
