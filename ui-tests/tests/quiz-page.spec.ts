import { expect, test, type Page } from '@playwright/test';
import { CARDS, LONG_CARD, mockQuiz, mockQuizNetworkFailure } from './fixtures';

// Страница теста (/). Перед каждым снимком дожидаемся конечного состояния по видимому элементу.
const quizCard = (page: Page) => page.getByRole('main').getByRole('button').first();

async function start(page: Page, cards = CARDS, count = '3') {
  await mockQuiz(page, cards);
  await page.goto('/');
  await page.getByLabel('Количество вопросов').fill(count);
  await page.getByRole('button', { name: 'Начать тест' }).click();
  await expect(page.getByText(/^Вопрос 1 из \d+$/)).toBeVisible();
  // Курсор уводим, чтобы на снимок не попало состояние наведения.
  await page.mouse.move(0, 0);
}

test('тест: выбор количества', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByLabel('Количество вопросов')).toHaveValue('10');
  await expect(page).toHaveScreenshot('quiz-setup.png', { fullPage: true });
});

test('тест: вопрос', async ({ page }) => {
  await start(page);
  await expect(page).toHaveScreenshot('quiz-question.png', { fullPage: true });
});

test('тест: вопрос, тёмная тема @dark', async ({ page }) => {
  await start(page);
  await expect(page).toHaveScreenshot('quiz-question.png', { fullPage: true });
});

test('тест: вопрос, мобильный вид @mobile', async ({ page }) => {
  await start(page);
  await expect(page).toHaveScreenshot('quiz-question.png', { fullPage: true });
});

test('тест: вопрос на повторении, ответ показан', async ({ page }) => {
  await start(page, [CARDS[1], CARDS[0]], '2');
  await quizCard(page).click();
  await expect(page.getByRole('button', { name: 'Не знал', exact: true })).toBeVisible();
  await page.mouse.move(0, 0);
  await expect(page).toHaveScreenshot('quiz-revealed.png', { fullPage: true });
});

test('тест: карточек меньше, чем запрошено', async ({ page }) => {
  await start(page, CARDS, '10');
  await expect(page.getByText('В тесте 3 вопроса')).toBeVisible();
  await expect(page).toHaveScreenshot('quiz-fewer.png', { fullPage: true });
});

test('тест: длинный вопрос', async ({ page }) => {
  await start(page, [LONG_CARD], '1');
  await expect(page).toHaveScreenshot('quiz-long.png', { fullPage: true });
});

test('тест: итог', async ({ page }) => {
  await start(page);
  for (const button of ['Знал', 'Не знал', 'Знал']) {
    await quizCard(page).click();
    await page.getByRole('button', { name: button, exact: true }).click();
  }
  await expect(page.getByText('Знал 2 из 3')).toBeVisible();
  await page.mouse.move(0, 0);
  await expect(page).toHaveScreenshot('quiz-result.png', { fullPage: true });
});

test('тест: нет карточек', async ({ page }) => {
  await mockQuiz(page, []);
  await page.goto('/');
  await page.getByRole('button', { name: 'Начать тест' }).click();
  await expect(page.getByText('Карточек пока нет')).toBeVisible();
  await page.mouse.move(0, 0);
  await expect(page).toHaveScreenshot('quiz-empty.png', { fullPage: true });
});

test('тест: ошибка загрузки', async ({ page }) => {
  await mockQuizNetworkFailure(page);
  await page.goto('/');
  await page.getByRole('button', { name: 'Начать тест' }).click();
  await expect(page.getByRole('alert')).toContainText('Сервер недоступен');
  await page.mouse.move(0, 0);
  await expect(page).toHaveScreenshot('quiz-error.png', { fullPage: true });
});
