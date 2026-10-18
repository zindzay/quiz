import { expect, test, type Page } from '@playwright/test';
import { CARDS, mockCardList, mockCreateError, mockNetworkFailure } from './fixtures';

// Перед каждым снимком дожидаемся конечного состояния по видимому элементу, а не по таймауту.
async function openWithCards(page: Page) {
  await mockCardList(page, CARDS);
  await page.goto('/');
  await expect(page.getByText(CARDS[2].question, { exact: true })).toBeVisible();
}

test('пустой список', async ({ page }) => {
  await mockCardList(page, []);
  await page.goto('/');
  await expect(page.getByText('Карточек пока нет')).toBeVisible();
  await expect(page).toHaveScreenshot('empty.png', { fullPage: true });
});

test('список карточек', async ({ page }) => {
  await openWithCards(page);
  await expect(page).toHaveScreenshot('list.png', { fullPage: true });
});

test('список карточек, тёмная тема @dark', async ({ page }) => {
  await openWithCards(page);
  await expect(page).toHaveScreenshot('list.png', { fullPage: true });
});

test('список карточек, мобильный вид @mobile', async ({ page }) => {
  await openWithCards(page);
  await expect(page).toHaveScreenshot('list.png', { fullPage: true });
});

test('раскрытый ответ', async ({ page }) => {
  await openWithCards(page);
  await page.getByText(CARDS[1].question, { exact: true }).click();
  await expect(page.getByText(/^401 Unauthorized/)).toBeVisible();
  // Курсор уводим с карточки, чтобы на снимок не попало состояние наведения.
  await page.mouse.move(0, 0);
  await expect(page).toHaveScreenshot('revealed.png', { fullPage: true });
});

test('ошибка валидации формы', async ({ page }) => {
  await mockCardList(page, []);
  await mockCreateError(page, 'Поле «Вопрос» не может быть пустым');
  await page.goto('/');
  await expect(page.getByText('Карточек пока нет')).toBeVisible();
  await page.getByLabel('Ответ').fill('4');
  await page.getByRole('button', { name: 'Добавить' }).click();
  await expect(page.getByRole('alert')).toHaveText('Поле «Вопрос» не может быть пустым');
  await page.getByLabel('Ответ').blur();
  await expect(page).toHaveScreenshot('form-error.png', { fullPage: true });
});

test('ошибка загрузки списка', async ({ page }) => {
  await mockNetworkFailure(page);
  await page.goto('/');
  await expect(page.getByText('Не удалось загрузить карточки')).toBeVisible();
  await expect(page).toHaveScreenshot('load-error.png', { fullPage: true });
});
