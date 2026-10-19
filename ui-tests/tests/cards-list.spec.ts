import { expect, test, type Page } from '@playwright/test';
import { CARDS, manyCards, mockCardList, mockDeleteFailure, mockNetworkFailure } from './fixtures';

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

test('список: подтверждение удаления', async ({ page }) => {
  await openWithCards(page);
  const card = page.getByRole('listitem').filter({ hasText: CARDS[0].question });
  await card.getByRole('button', { name: 'Удалить' }).click();
  await expect(card.getByText('Удалить карточку?')).toBeVisible();
  await page.mouse.move(0, 0);
  await expect(page).toHaveScreenshot('list-delete-confirm.png', { fullPage: true });
});

test('список: ошибка удаления', async ({ page }) => {
  await openWithCards(page);
  await mockDeleteFailure(page);
  const card = page.getByRole('listitem').filter({ hasText: CARDS[0].question });
  await card.getByRole('button', { name: 'Удалить' }).click();
  await card.getByRole('button', { name: 'Да' }).click();
  await expect(card.getByRole('alert')).toBeVisible();
  await page.mouse.move(0, 0);
  await expect(page).toHaveScreenshot('list-delete-error.png', { fullPage: true });
});

// Вторая из трёх страниц: номера 11–20 и панель страниц.
async function openSecondPage(page: Page) {
  await mockCardList(page, manyCards(25));
  await page.goto('/cards.html?page=2');
  await expect(page.getByRole('navigation', { name: 'Страницы списка' })).toBeVisible();
}

test('список: страницы', async ({ page }) => {
  await openSecondPage(page);
  await expect(page).toHaveScreenshot('list-pages.png', { fullPage: true });
});

test('список: страницы, тёмная тема @dark', async ({ page }) => {
  await openSecondPage(page);
  await expect(page).toHaveScreenshot('list-pages-dark.png', { fullPage: true });
});

test('список: страницы, мобильный вид @mobile', async ({ page }) => {
  await openSecondPage(page);
  await expect(page).toHaveScreenshot('list-pages-mobile.png', { fullPage: true });
});
