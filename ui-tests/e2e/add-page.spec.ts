import { expect, test } from './app-fixture';

// Сценарии страницы добавления (/add.html) из openspec/specs/cards-web-ui/spec.md на настоящем приложении.
// Элементы ищутся по ролям, подписям и текстам, а не по CSS-классам.

test.describe('Форма добавления карточки', () => {
  test('Успешное добавление', async ({ app, page }) => {
    await app.createCard('Существующий вопрос', 'Существующий ответ');
    await page.goto('/add.html');

    await page.getByLabel('Вопрос').fill('Сколько будет 2+2?');
    await page.getByLabel('Ответ').fill('4');
    await page.getByRole('button', { name: 'Добавить' }).click();

    await expect(page.getByRole('status')).toHaveText('Карточка добавлена');
    await expect(page.getByLabel('Вопрос')).toHaveValue('');
    await expect(page.getByLabel('Ответ')).toHaveValue('');
    expect((await app.listCards()).map((card) => card.question)).toEqual(['Существующий вопрос', 'Сколько будет 2+2?']);
  });

  test('Новая карточка видна в списке', async ({ app, page }) => {
    await app.createCard('Существующий вопрос', 'Существующий ответ');
    await page.goto('/add.html');
    await page.getByLabel('Вопрос').fill('Сколько будет 2+2?');
    await page.getByLabel('Ответ').fill('4');
    await page.getByRole('button', { name: 'Добавить' }).click();
    await expect(page.getByRole('status')).toHaveText('Карточка добавлена');

    await page.goto('/cards.html');

    const cards = page.getByRole('list').getByRole('listitem');
    await expect(cards).toHaveCount(2);
    await expect(cards.last()).toContainText('Сколько будет 2+2?');
  });
});

test.describe('Ошибки при добавлении', () => {
  test('Пустое поле: ошибка, ответ сохранён, карточка не добавлена', async ({ app, page }) => {
    await page.goto('/add.html');

    await page.getByLabel('Вопрос').fill('   ');
    await page.getByLabel('Ответ').fill('4');
    await page.getByRole('button', { name: 'Добавить' }).click();

    await expect(page.getByRole('alert')).toContainText('Вопрос');
    await expect(page.getByRole('status')).toBeHidden();
    await expect(page.getByLabel('Ответ')).toHaveValue('4');
    expect(await app.listCards()).toEqual([]);
  });

  test('Сервер недоступен: сообщение об ошибке, введённый текст сохранён', async ({ app, page }) => {
    await page.goto('/add.html');

    await app.stop();
    await page.getByLabel('Вопрос').fill('Вопрос при остановленном сервере');
    await page.getByLabel('Ответ').fill('Ответ при остановленном сервере');
    await page.getByRole('button', { name: 'Добавить' }).click();

    await expect(page.getByRole('alert')).toContainText('Сервер недоступен');
    await expect(page.getByLabel('Вопрос')).toHaveValue('Вопрос при остановленном сервере');
    await expect(page.getByLabel('Ответ')).toHaveValue('Ответ при остановленном сервере');
  });
});
