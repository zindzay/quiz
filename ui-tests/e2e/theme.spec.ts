import { expect, test } from './app-fixture';

// Требование «Тема оформления по системной настройке» (cards-web-ui) — на каждой странице приложения.
const cases = [
  { scheme: 'dark', background: 'rgb(33, 37, 41)' }, // --bs-body-bg тёмной темы Bootstrap
  { scheme: 'light', background: 'rgb(255, 255, 255)' }, // --bs-body-bg светлой темы
] as const;

const pages = [
  { path: '/', ready: 'Количество вопросов' },
  { path: '/add.html', ready: 'Вопрос' },
  { path: '/cards.html', ready: 'Карточек пока нет' },
];

for (const { scheme, background } of cases) {
  test.describe(`Тема: ${scheme}`, () => {
    test.use({ colorScheme: scheme });

    for (const { path, ready } of pages) {
      test(`${scheme === 'dark' ? 'Тёмная' : 'Светлая'} системная тема: ${path}`, async ({ page }) => {
        await page.goto(path);
        await expect(page.getByText(ready).first()).toBeVisible();

        await expect(page.locator('html')).toHaveAttribute('data-bs-theme', scheme);
        await expect(page.locator('body')).toHaveCSS('background-color', background);
      });
    }
  });
}
