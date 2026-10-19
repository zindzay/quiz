import type { Page } from '@playwright/test';
import { expect, test } from './app-fixture';

/** Карточки — элементы списка; внутри каждой кнопка раскрытия (с текстом вопроса) и кнопки удаления. */
const cards = (page: Page) => page.getByRole('list').getByRole('listitem');

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
