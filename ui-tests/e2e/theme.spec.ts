import { expect, test } from './app-fixture';

// Требование «Тема оформления по системной настройке» (cards-web-ui).
const cases = [
  { scheme: 'dark', background: 'rgb(33, 37, 41)' }, // --bs-body-bg тёмной темы Bootstrap
  { scheme: 'light', background: 'rgb(255, 255, 255)' }, // --bs-body-bg светлой темы
] as const;

for (const { scheme, background } of cases) {
  test.describe(`Тема: ${scheme}`, () => {
    test.use({ colorScheme: scheme });

    test(`${scheme === 'dark' ? 'Тёмная' : 'Светлая'} системная тема`, async ({ page }) => {
      await page.goto('/');
      await expect(page.getByText('Карточек пока нет')).toBeVisible();

      await expect(page.locator('html')).toHaveAttribute('data-bs-theme', scheme);
      await expect(page.locator('body')).toHaveCSS('background-color', background);
    });
  });
}
