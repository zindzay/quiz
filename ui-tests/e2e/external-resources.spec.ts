import { expect, test } from './app-fixture';

// Требование «Работа без внешних ресурсов» (cards-web-ui). Покрывает и сценарий
// «Работа без доступа в интернет»: без сторонних запросов отсутствие сети на странице не сказывается.
test('Нет запросов к сторонним доменам', async ({ app, page }) => {
  await app.createCard('Столица Франции?', 'Париж');
  const requested: string[] = [];
  page.on('request', (request) => requested.push(request.url()));

  await page.goto('/');
  await page.getByRole('list').getByRole('button', { name: /Столица Франции/ }).click();
  await expect(page.getByText('Париж', { exact: true })).toBeVisible();
  await page.getByLabel('Вопрос').fill('Новый вопрос');
  await page.getByLabel('Ответ').fill('Новый ответ');
  await page.getByRole('button', { name: 'Добавить' }).click();
  await expect(page.getByRole('list').getByRole('button')).toHaveCount(2);

  const appOrigin = new URL(app.baseURL).origin;
  expect(requested.length).toBeGreaterThan(0);
  expect(requested.filter((url) => new URL(url).origin !== appOrigin)).toEqual([]);
});
