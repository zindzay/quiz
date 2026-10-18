import type { Page } from '@playwright/test';
import { expect, test } from './app-fixture';

/** Карточки: у элементов списка роль button (они раскрывают ответ), поэтому ищем кнопки внутри списка. */
const cards = (page: Page) => page.getByRole('list').getByRole('button');

// Сценарии openspec/specs/cards-web-ui/spec.md на настоящем приложении.
// Элементы ищутся по ролям, подписям и текстам, а не по CSS-классам.

test.describe('Главная страница', () => {
  test('Открытие страницы: вопросы в порядке добавления, ответы скрыты', async ({ app, page }) => {
    await app.createCard('Первый вопрос', 'Первый ответ');
    await app.createCard('Второй вопрос', 'Второй ответ');
    await app.createCard('Третий вопрос', 'Третий ответ');

    await page.goto('/');

    await expect(cards(page)).toHaveText([/Первый вопрос/, /Второй вопрос/, /Третий вопрос/]);
    for (const answer of ['Первый ответ', 'Второй ответ', 'Третий ответ']) {
      await expect(page.getByText(answer)).toBeHidden();
    }
  });

  test('Нет карточек: сообщение о пустом списке', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByText('Карточек пока нет')).toBeVisible();
    await expect(cards(page)).toHaveCount(0);
  });
});

test.describe('Раскрытие ответа', () => {
  test('Показ и скрытие ответа', async ({ app, page }) => {
    await app.createCard('Вопрос 1', 'Ответ 1');
    await app.createCard('Вопрос 2', 'Ответ 2');
    await app.createCard('Вопрос 3', 'Ответ 3');
    await page.goto('/');

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

test.describe('Форма добавления карточки', () => {
  test('Успешное добавление', async ({ app, page }) => {
    await app.createCard('Существующий вопрос', 'Существующий ответ');
    await page.goto('/');
    await expect(page.getByText('Существующий вопрос')).toBeVisible();

    await page.getByLabel('Вопрос').fill('Сколько будет 2+2?');
    await page.getByLabel('Ответ').fill('4');
    await page.getByRole('button', { name: 'Добавить' }).click();

    await expect(cards(page).last()).toContainText('Сколько будет 2+2?');
    await expect(cards(page)).toHaveCount(2);
    await expect(page.getByLabel('Вопрос')).toHaveValue('');
    await expect(page.getByLabel('Ответ')).toHaveValue('');

    expect((await app.listCards()).map((card) => card.question)).toEqual(['Существующий вопрос', 'Сколько будет 2+2?']);

    await page.reload();
    await expect(cards(page).last()).toContainText('Сколько будет 2+2?');
  });
});

test.describe('Ошибки при добавлении', () => {
  test('Пустое поле: ошибка, ответ сохранён, карточка не добавлена', async ({ app, page }) => {
    await page.goto('/');
    await expect(page.getByText('Карточек пока нет')).toBeVisible();

    await page.getByLabel('Вопрос').fill('   ');
    await page.getByLabel('Ответ').fill('4');
    await page.getByRole('button', { name: 'Добавить' }).click();

    await expect(page.getByRole('alert')).toContainText('Вопрос');
    await expect(page.getByLabel('Ответ')).toHaveValue('4');
    await expect(cards(page)).toHaveCount(0);
    expect(await app.listCards()).toEqual([]);
  });

  test('Сервер недоступен: сообщение об ошибке, введённый текст сохранён', async ({ app, page }) => {
    await page.goto('/');
    await expect(page.getByText('Карточек пока нет')).toBeVisible();

    await app.stop();
    await page.getByLabel('Вопрос').fill('Вопрос при остановленном сервере');
    await page.getByLabel('Ответ').fill('Ответ при остановленном сервере');
    await page.getByRole('button', { name: 'Добавить' }).click();

    await expect(page.getByRole('alert')).toContainText('Сервер недоступен');
    await expect(page.getByLabel('Вопрос')).toHaveValue('Вопрос при остановленном сервере');
    await expect(page.getByLabel('Ответ')).toHaveValue('Ответ при остановленном сервере');
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

    await page.goto('/');

    const card = cards(page);
    await expect(card.getByText(markup, { exact: true })).toBeVisible();
    await expect(card.locator('b, script')).toHaveCount(0);
    expect(dialogShown).toBe(false);
  });
});
