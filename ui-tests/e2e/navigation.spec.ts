import { expect, test } from './app-fixture';

// Требование «Навигация между страницами» (cards-web-ui).
const pages = [
  { path: '/', current: 'Тест' },
  { path: '/add.html', current: 'Добавить' },
  { path: '/cards.html', current: 'Все карточки' },
];
const nav = (page: import('@playwright/test').Page) => page.getByRole('navigation', { name: 'Разделы' });

test.describe('Навигация между страницами', () => {
  for (const { path, current } of pages) {
    test(`Ссылки и текущая страница: ${path}`, async ({ page }) => {
      await page.goto(path);

      await expect(nav(page).getByRole('link')).toHaveText(['Тест', 'Добавить', 'Все карточки']);
      await expect(nav(page).getByRole('link', { name: current })).toHaveAttribute('aria-current', 'page');
      await expect(nav(page).locator('[aria-current]')).toHaveCount(1);
    });
  }

  test('Переход между страницами: «Тест» → «Добавить»', async ({ page }) => {
    await page.goto('/');

    await nav(page).getByRole('link', { name: 'Добавить' }).click();

    await expect(page).toHaveURL(/\/add\.html$/);
    await expect(page.getByLabel('Вопрос')).toBeVisible();
    await expect(nav(page).getByRole('link', { name: 'Добавить' })).toHaveAttribute('aria-current', 'page');
  });
});
