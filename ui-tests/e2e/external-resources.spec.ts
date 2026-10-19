import { expect, test } from './app-fixture';

// Требование «Работа без внешних ресурсов» (cards-web-ui) — на каждой странице приложения. Покрывает и сценарий
// «Работа без доступа в интернет»: без сторонних запросов отсутствие сети на странице не сказывается.
test('Нет запросов к сторонним доменам', async ({ app, page }) => {
  await app.createCard('Столица Франции?', 'Париж');
  const requested: string[] = [];
  page.on('request', (request) => requested.push(request.url()));

  // Тест: прохождение одного вопроса.
  await page.goto('/');
  await page.getByLabel('Количество вопросов').fill('1');
  await page.getByRole('button', { name: 'Начать тест' }).click();
  await page.getByRole('main').getByRole('button', { name: /Столица Франции/ }).click();
  await page.getByRole('button', { name: 'Не знал', exact: true }).click();
  await expect(page.getByText('Знал 0 из 1')).toBeVisible();

  // Добавление.
  await page.goto('/add.html');
  await page.getByLabel('Вопрос').fill('Новый вопрос');
  await page.getByLabel('Ответ').fill('Новый ответ');
  await page.getByRole('button', { name: 'Добавить' }).click();
  await expect(page.getByRole('status')).toHaveText('Карточка добавлена');

  // Все карточки.
  await page.goto('/cards.html');
  await page.getByRole('list').getByRole('button', { name: /Столица Франции/ }).click();
  await expect(page.getByText('Париж', { exact: true })).toBeVisible();
  await expect(page.getByRole('list').getByRole('listitem')).toHaveCount(2);

  const appOrigin = new URL(app.baseURL).origin;
  expect(requested.length).toBeGreaterThan(0);
  expect(requested.filter((url) => new URL(url).origin !== appOrigin)).toEqual([]);
});
