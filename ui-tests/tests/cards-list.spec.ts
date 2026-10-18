import { expect, test, type Page } from '@playwright/test';
import { CARDS, mockCardList, mockNetworkFailure } from './fixtures';

// Страница всех карточек (/cards.html).
async function openWithCards(page: Page) {
  await mockCardList(page, CARDS);
  await page.goto('/cards.html');
  await expect(page.getByText(CARDS[2].question, { exact: true })).toBeVisible();
}

test('список: карточки', async ({ page }) => {
  await openWithCards(page);
  await expect(page).toHaveScreenshot('list.png', { fullPage: true });
});

test('список: пусто', async ({ page }) => {
  await mockCardList(page, []);
  await page.goto('/cards.html');
  await expect(page.getByText('Карточек пока нет')).toBeVisible();
  await expect(page).toHaveScreenshot('list-empty.png', { fullPage: true });
});

test('список: раскрытый ответ', async ({ page }) => {
  await openWithCards(page);
  await page.getByText(CARDS[1].question, { exact: true }).click();
  await expect(page.getByText(/^401 Unauthorized/)).toBeVisible();
  await page.mouse.move(0, 0);
  await expect(page).toHaveScreenshot('list-revealed.png', { fullPage: true });
});

test('список: ошибка загрузки', async ({ page }) => {
  await mockNetworkFailure(page);
  await page.goto('/cards.html');
  await expect(page.getByText('Не удалось загрузить карточки')).toBeVisible();
  await expect(page).toHaveScreenshot('list-error.png', { fullPage: true });
});
