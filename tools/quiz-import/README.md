# quiz-import

Общие инструменты скилов импорта карточек (`/quiz-from-web-page`, `/quiz-from-pdf`).

| Файл | Назначение |
|---|---|
| `card-rules.md` | правила генерации карточек — скилы читают его перед генерацией |
| `fetch_page.py` | полный основной текст веб-страницы по частям и квоты карточек по разделам |
| `post_cards.py` | проверка API и отправка карточек |
| `test_fetch_page.py`, `fixtures/` | тесты `fetch_page.py` на HTML-фикстурах и локальном сервере |
| `test_post_cards.py` | тесты `post_cards.py` на поддельном API |

Скрипты — python3, только стандартная библиотека.

## fetch_page.py — текст страницы

```bash
python3 tools/quiz-import/fetch_page.py https://ru.wikipedia.org/wiki/HTTP --count 10 --out /tmp/page-http
```

- `URL` — `http://` или `https://`, кириллица в адресе допустима;
- `--count N` — сколько карточек распределить по разделам, 1–50;
- `--out DIR` — каталог для результата (создаётся).

Скрипт загружает HTML (`User-Agent: quiz-import/1.0`, кодировка из `Content-Type` или `<meta charset>`) и выделяет основной текст в Markdown без пересказа:
- корень — `<main>`, иначе самый объёмный `<article>`, иначе `<body>`;
- выбрасываются скрипты, стили, формы, `nav`, `header`, `footer`, `aside`, элементы с `role` navigation/banner/contentinfo/search, `hidden` и `aria-hidden`, а также элементы, у которых в `class`/`id` есть слово `nav`, `menu`, `footer`, `sidebar`, `cookie`, `comments`, `breadcrumb`, `toc`, `mw-editsection`, `reference` (по словам, а не подстрокам);
- заголовки → `#`, списки → `-` / `1.`, таблицы → строки с ` | `, `<pre>` → блоки кода.

Текст делится на **крупные разделы** (по `<h2>`, без них — по `<h1>`; текст до первого заголовка — «Введение») и упаковывается в **части** до ~12 000 символов; абзацы и блоки кода не разрываются. Справочные разделы («Примечания», «Литература», «Ссылки», «См. также», «References», «See also», «External links», «Notes», «Further reading») и разделы короче 300 символов получают квоту 0. Остальные делят `N`: если `N` не меньше числа разделов — каждому по 1, остаток пропорционально объёму; иначе `N` разделов, равномерно разнесённых по странице, по 1. Сумма квот всегда равна `N`.

Лимит — 500 000 символов основного текста: сверх него обрабатывается начало страницы (`truncated: true`).

Результат в `DIR`:
- `chunk-01.md`, `chunk-02.md`, … — текст частей; их склейка через пустую строку равна обработанному тексту;
- `meta.json`:

```json
{
  "url": "https://ru.wikipedia.org/wiki/HTTP",
  "title": "HTTP — Википедия",
  "count": 10,
  "total_chars": 41437,
  "processed_chars": 41437,
  "truncated": false,
  "sections": [
    {"id": "s1", "title": "Введение", "chars": 1074, "chunks": [1], "quota": 1, "skipped_reason": null},
    {"id": "s10", "title": "Ссылки", "chars": 1153, "chunks": [5], "quota": 0, "skipped_reason": "справочный раздел"}
  ],
  "chunks": [
    {"file": "chunk-01.md", "chars": 11993, "sections": ["s1", "s2", "s3", "s4"]}
  ]
}
```

Коды выхода:
- `0` — готово, в stdout краткая сводка;
- `1` — неверные аргументы;
- `3` — основного текста меньше 500 символов (страница собирается JavaScript) — скил переходит на запасной путь через WebFetch;
- `4` — HTTP-ошибка, недоступный хост или ответ не HTML; сообщение в stderr.

## post_cards.py — отправка карточек

### Формат входного JSON

Массив карточек, UTF-8:

```json
[
  {"question": "Какой порт по умолчанию использует HTTPS?", "answer": "443."},
  {"question": "Что такое HTTP?", "answer": "Протокол передачи данных по схеме «запрос — ответ»."}
]
```

### Команды

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
