import { expect, test } from '@playwright/test';
import { mockCreateError, mockCreateSuccess } from './fixtures';

// Страница добавления (/add.html).

test('добавление: форма', async ({ page }) => {
  await page.goto('/add.html');
  await expect(page.getByLabel('Вопрос')).toBeVisible();
  await expect(page).toHaveScreenshot('add-form.png', { fullPage: true });
});

test('добавление: ошибка проверки', async ({ page }) => {
  await mockCreateError(page, 'Поле «Вопрос» не может быть пустым');
  await page.goto('/add.html');
  await page.getByLabel('Ответ').fill('4');
  await page.getByRole('button', { name: 'Добавить' }).click();
  await expect(page.getByRole('alert')).toHaveText('Поле «Вопрос» не может быть пустым');
  await page.getByLabel('Ответ').blur();
  await page.mouse.move(0, 0);
  await expect(page).toHaveScreenshot('add-error.png', { fullPage: true });
});

test('добавление: успех', async ({ page }) => {
  await mockCreateSuccess(page);
  await page.goto('/add.html');
  await page.getByLabel('Вопрос').fill('Сколько будет 2+2?');
  await page.getByLabel('Ответ').fill('4');
  await page.getByRole('button', { name: 'Добавить' }).click();
  await expect(page.getByRole('status')).toHaveText('Карточка добавлена');
  await page.getByLabel('Вопрос').blur();
  await page.mouse.move(0, 0);
  await expect(page).toHaveScreenshot('add-success.png', { fullPage: true });
});
