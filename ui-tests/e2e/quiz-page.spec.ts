import type { Page } from '@playwright/test';
import { expect, test, type App } from './app-fixture';

// Сценарии openspec/changes/add-quiz-mode-pages/specs/quiz-session/spec.md на настоящем приложении.
// Элементы ищутся по ролям, подписям и текстам, а не по CSS-классам.

/** Карточка теста — первая видимая кнопка в main (кнопки скрытых экранов в роли не попадают). */
const quizCard = (page: Page) => page.getByRole('main').getByRole('button').first();
/** Текст вопроса — первый абзац карточки. */
const questionOf = (page: Page) => quizCard(page).getByRole('paragraph').first();
const knownButton = (page: Page) => page.getByRole('button', { name: 'Знал', exact: true });
const unknownButton = (page: Page) => page.getByRole('button', { name: 'Не знал', exact: true });

async function createCards(app: App, count: number) {
  const cards = [];
  for (let i = 1; i <= count; i++) {
    cards.push(await app.createCard(`Вопрос ${i}?`, `Ответ ${i}`));
  }
  return cards;
}

/**
 * Начинает тест и ждёт первую карточку: пока виден экран выбора, «первая кнопка в main» — это «Начать тест».
 * waitForQuestion = false — для сценариев, где тест не начинается.
 */
async function startTest(page: Page, count: number, waitForQuestion = true) {
  await page.goto('/');
  await page.getByLabel('Количество вопросов').fill(String(count));
  await page.getByRole('button', { name: 'Начать тест' }).click();
  if (waitForQuestion) {
    await expect(page.getByText(/^Вопрос 1 из \d+$/)).toBeVisible();
  }
}

/** Проходит текущий тест, отвечая по списку решений; возвращает вопросы в порядке показа. */
async function answerAll(page: Page, decisions: boolean[]) {
  const questions: string[] = [];
  for (let i = 0; i < decisions.length; i++) {
    await expect(page.getByText(`Вопрос ${i + 1} из ${decisions.length}`)).toBeVisible();
    questions.push((await questionOf(page).textContent()) ?? '');
    await quizCard(page).click();
    await (decisions[i] ? knownButton(page) : unknownButton(page)).click();
  }
  return questions;
}

test.describe('Страница теста', () => {
  test('Открытие главной страницы', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByLabel('Количество вопросов')).toHaveValue('10');
    await expect(page.getByRole('button', { name: 'Начать тест' })).toBeVisible();
  });
});

test.describe('Количество вопросов', () => {
  for (const count of ['0', '101']) {
    test(`Неверное количество: ${count}`, async ({ app, page }) => {
      await createCards(app, 3);
      await page.goto('/');

      await page.getByLabel('Количество вопросов').fill(count);
      await page.getByRole('button', { name: 'Начать тест' }).click();

      await expect(page.getByRole('alert')).toContainText('от 1 до 100');
      await expect(page.getByText(/Вопрос \d+ из/)).toBeHidden();
      await expect(page.getByLabel('Количество вопросов')).toBeVisible();
    });
  }
});

test.describe('Случайный набор карточек', () => {
  test('Выбор заданного количества: 10 разных карточек из 30', async ({ app, page }) => {
    const all = (await createCards(app, 30)).map((card) => card.question);

    await startTest(page, 10);
    const questions = await answerAll(page, Array(10).fill(true));

    expect(new Set(questions).size).toBe(10);
    for (const question of questions) {
      expect(all).toContain(question);
    }
  });

  test('Карточек меньше, чем запрошено: в тесте все 4', async ({ app, page }) => {
    await createCards(app, 4);

    await startTest(page, 10);

    await expect(page.getByText('В тесте 4 вопроса')).toBeVisible();
    await expect(page.getByText('Вопрос 1 из 4')).toBeVisible();
    const questions = await answerAll(page, [true, true, true, true]);
    expect(new Set(questions).size).toBe(4);
  });

  test('Нет карточек: сообщение и ссылка на добавление', async ({ page }) => {
    await startTest(page, 10, false);

    await expect(page.getByText('Карточек пока нет')).toBeVisible();
    await page.getByRole('main').getByRole('link', { name: 'Добавить карточки' }).click();
    await expect(page).toHaveURL(/\/add\.html$/);
  });
});

test.describe('Показ карточки', () => {
  test('Первая карточка: одна квадратная карточка, «Вопрос 1 из 10», ответ скрыт', async ({ app, page }) => {
    await createCards(app, 12);

    await startTest(page, 10);

    await expect(page.getByText('Вопрос 1 из 10')).toBeVisible();
    await expect(questionOf(page)).toHaveText(/^Вопрос \d+\?$/);
    await expect(page.getByText(/^Ответ \d+$/)).toBeHidden();
    const box = await quizCard(page).boundingBox();
    expect(box).not.toBeNull();
    expect(Math.abs(box!.width - box!.height)).toBeLessThanOrEqual(1);
  });
});

test.describe('Показ правильного ответа', () => {
  test('Нажатие на карточку показывает ответ и кнопки', async ({ app, page }) => {
    await app.createCard('Столица Франции?', 'Париж');
    await startTest(page, 10);

    await quizCard(page).click();

    await expect(page.getByText('Париж')).toBeVisible();
    await expect(quizCard(page)).toHaveAttribute('aria-expanded', 'true');
    await expect(knownButton(page)).toBeVisible();
    await expect(unknownButton(page)).toBeVisible();
  });

  test('Ответ открывается клавишей Enter', async ({ app, page }) => {
    await app.createCard('Столица Франции?', 'Париж');
    await startTest(page, 10);

    await quizCard(page).focus();
    await page.keyboard.press('Enter');

    await expect(page.getByText('Париж')).toBeVisible();
    await expect(knownButton(page)).toBeVisible();
  });
});

test.describe('Последовательное прохождение', () => {
  test('Ответ не открыт: кнопок «Знал» и «Не знал» нет', async ({ app, page }) => {
    await createCards(app, 3);

    await startTest(page, 3);

    await expect(page.getByText('Вопрос 1 из 3')).toBeVisible();
    await expect(knownButton(page)).toHaveCount(0);
    await expect(unknownButton(page)).toHaveCount(0);
  });

  test('Переход к следующему вопросу', async ({ app, page }) => {
    await createCards(app, 12);
    await startTest(page, 10);
    const first = await questionOf(page).textContent();

    await quizCard(page).click();
    await knownButton(page).click();

    await expect(page.getByText('Вопрос 2 из 10')).toBeVisible();
    await expect(questionOf(page)).not.toHaveText(first ?? '');
    await expect(page.getByText(/^Ответ \d+$/)).toBeHidden();
    await expect(knownButton(page)).toHaveCount(0);
  });
});

test.describe('Итог теста', () => {
  test('Завершение теста: «Знал 2 из 3»', async ({ app, page }) => {
    await createCards(app, 3);
    await startTest(page, 3);

    await answerAll(page, [true, false, true]);

    await expect(page.getByText('Знал 2 из 3')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Новый тест' })).toBeVisible();
  });

  test('Новый тест возвращает к выбору количества', async ({ app, page }) => {
    await createCards(app, 2);
    await startTest(page, 2);
    await answerAll(page, [true, true]);

    await page.getByRole('button', { name: 'Новый тест' }).click();

    await expect(page.getByLabel('Количество вопросов')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Начать тест' })).toBeVisible();
    await expect(page.getByText('Знал 2 из 2')).toBeHidden();
  });
});

test.describe('Ошибка загрузки теста', () => {
  test('Сервер недоступен при начале теста', async ({ app, page }) => {
    await createCards(app, 3);
    await page.goto('/');

    await app.stop();
    await page.getByRole('button', { name: 'Начать тест' }).click();

    await expect(page.getByRole('alert')).toContainText('Сервер недоступен');
    await expect(page.getByLabel('Количество вопросов')).toBeEditable();
  });
});

test.describe('Безопасный вывод текста в тесте', () => {
  test('HTML в карточке теста выводится буквально', async ({ app, page }) => {
    const markup = '<b>жирный</b><script>alert(1)</script>';
    await app.createCard(markup, '<i>ответ</i>');
    let dialogShown = false;
    page.on('dialog', async (dialog) => {
      dialogShown = true;
      await dialog.dismiss();
    });

    await startTest(page, 1);
    await quizCard(page).click();

    await expect(quizCard(page).getByText(markup, { exact: true })).toBeVisible();
    await expect(quizCard(page).getByText('<i>ответ</i>', { exact: true })).toBeVisible();
    await expect(quizCard(page).locator('b, i, script')).toHaveCount(0);
    expect(dialogShown).toBe(false);
  });
});

/** Проходит тест из n вопросов; decide(вопрос) — true для «Знал». Возвращает показанные вопросы. */
async function answerBy(page: Page, n: number, decide: (question: string) => boolean) {
  const questions: string[] = [];
  for (let i = 0; i < n; i++) {
    await expect(page.getByText(`Вопрос ${i + 1} из ${n}`)).toBeVisible();
    const question = (await questionOf(page).textContent()) ?? '';
    questions.push(question);
    await quizCard(page).click();
    await (decide(question) ? knownButton(page) : unknownButton(page)).click();
  }
  await expect(page.getByText(new RegExp(`^Знал \\d+ из ${n}$`))).toBeVisible();
  return questions;
}

async function nextTest(page: Page, count: number) {
  await page.getByRole('button', { name: 'Новый тест' }).click();
  await page.getByLabel('Количество вопросов').fill(String(count));
  await page.getByRole('button', { name: 'Начать тест' }).click();
  await expect(page.getByText(/^Вопрос 1 из \d+$/)).toBeVisible();
}

const reviewOf = async (app: App, question: string) =>
  (await app.listCards()).find((card) => card.question === question)?.review;

test.describe('Повторение вопросов «Не знал»', () => {
  test('«Не знал» возвращает вопрос в следующий тест', async ({ app, page }) => {
    await createCards(app, 30);
    await startTest(page, 5);
    const first = (await questionOf(page).textContent()) ?? '';

    await answerBy(page, 5, (question) => question !== first);
    expect(await reviewOf(app, first)).toBe(true);

    await nextTest(page, 5);
    expect(await answerBy(page, 5, () => true)).toContain(first);
  });

  test('Вопрос возвращается, пока не ответили «Знал»', async ({ app, page }) => {
    await createCards(app, 30);
    await startTest(page, 3);
    const hard = (await questionOf(page).textContent()) ?? '';

    await answerBy(page, 3, (question) => question !== hard);
    await nextTest(page, 3);
    expect(await answerBy(page, 3, (question) => question !== hard)).toContain(hard);
    await nextTest(page, 3);

    expect(await answerBy(page, 3, () => true)).toContain(hard);
    expect(await reviewOf(app, hard)).toBe(false);
  });

  test('«Знал» снимает вопрос с повторения', async ({ app, page }) => {
    const cards = await createCards(app, 5);
    await app.setReview(cards[2].id, true);

    await startTest(page, 1);
    await expect(questionOf(page)).toHaveText(cards[2].question);
    await expect(quizCard(page).getByText('На повторении')).toBeVisible();
    await answerBy(page, 1, () => true);

    expect(await reviewOf(app, cards[2].question)).toBe(false);
  });

  test('Тест прерван: отметка «Не знал» сохраняется', async ({ app, page }) => {
    await createCards(app, 30);
    await startTest(page, 5);
    const first = (await questionOf(page).textContent()) ?? '';
    await quizCard(page).click();
    await unknownButton(page).click();
    await expect(page.getByText('Вопрос 2 из 5')).toBeVisible();

    await page.reload();

    expect(await reviewOf(app, first)).toBe(true);
    await startTest(page, 5);
    expect(await answerBy(page, 5, () => true)).toContain(first);
  });

  test('Пометка «На повторении» только у карточек на повторении', async ({ app, page }) => {
    const [plain, hard] = await createCards(app, 2);
    await app.setReview(hard.id, true);

    await startTest(page, 2);
    for (let i = 0; i < 2; i++) {
      await expect(page.getByText(`Вопрос ${i + 1} из 2`)).toBeVisible();
      const question = await questionOf(page).textContent();
      const badge = quizCard(page).getByText('На повторении');
      if (question === hard.question) {
        await expect(badge).toBeVisible();
      } else {
        expect(question).toBe(plain.question);
        await expect(badge).toBeHidden();
      }
      await quizCard(page).click();
      await knownButton(page).click();
    }
  });

  test('Вопросы на повторении попадают в тест на 10 из 30', async ({ app, page }) => {
    const cards = await createCards(app, 30);
    const hard = [cards[3], cards[17], cards[29]];
    for (const card of hard) {
      await app.setReview(card.id, true);
    }

    await startTest(page, 10);
    const questions = await answerBy(page, 10, () => true);

    expect(new Set(questions).size).toBe(10);
    for (const card of hard) {
      expect(questions).toContain(card.question);
    }
  });
});

test.describe('Ошибка сохранения ответа', () => {
  test('Сервер недоступен при ответе: ошибка, тот же вопрос, кнопки доступны', async ({ app, page }) => {
    await createCards(app, 3);
    await startTest(page, 3);
    const question = await questionOf(page).textContent();
    await quizCard(page).click();

    await app.stop();
    await unknownButton(page).click();

    await expect(page.getByRole('alert')).toContainText('Не удалось сохранить ответ');
    await expect(page.getByText('Вопрос 1 из 3')).toBeVisible();
    await expect(questionOf(page)).toHaveText(question ?? '');
    await expect(knownButton(page)).toBeEnabled();
    await expect(unknownButton(page)).toBeEnabled();
  });
});
