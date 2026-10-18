# quiz-import

Общие инструменты скилов импорта карточек (`/quiz-from-web-page`, `/quiz-from-pdf`).

| Файл | Назначение |
|---|---|
| `card-rules.md` | правила генерации карточек — скилы читают его перед генерацией |
| `post_cards.py` | проверка API и отправка карточек (python3, только стандартная библиотека) |
| `test_post_cards.py` | тесты `post_cards.py` на поддельном API |

## Формат входного JSON

Массив карточек, UTF-8:

```json
[
  {"question": "Какой порт по умолчанию использует HTTPS?", "answer": "443."},
  {"question": "Что такое HTTP?", "answer": "Протокол передачи данных по схеме «запрос — ответ»."}
]
```

## Команды

Приложение должно быть запущено (`./gradlew bootRun`). Адрес API: `--api URL` > `QUIZ_API_URL` > `http://localhost:8080`.

```bash
python3 tools/quiz-import/post_cards.py check          # код 0 — API доступно, 2 — нет
python3 tools/quiz-import/post_cards.py post cards.json
QUIZ_API_URL=http://localhost:9090 python3 tools/quiz-import/post_cards.py post cards.json
```

`post` печатает отчёт:

```json
{
  "added": ["Какой порт по умолчанию использует HTTPS?"],
  "skipped": ["Что такое HTTP?"],
  "failed": [{"question": "…", "error": "Поле «Ответ» длиннее 2000 символов"}]
}
```

- `skipped` — вопрос уже есть в приложении или повторяется в файле (сравнение без учёта регистра и пробелов по краям);
- `failed` — карточка не прошла проверку или API её отклонило; ошибка одной карточки не останавливает отправку остальных.

Коды выхода: `0` — отчёт напечатан, `1` — не удалось прочитать файл, `2` — API недоступно.

## Тесты

```bash
python3 -m unittest discover tools/quiz-import
```
