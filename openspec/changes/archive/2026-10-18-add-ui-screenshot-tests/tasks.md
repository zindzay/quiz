# Tasks

## 1. Инфраструктура Playwright

- [x] 1.1 Создать `ui-tests/` с `package.json` (точная версия `@playwright/test` 1.64.x, `"private": true`), `package-lock.json` и `tsconfig.json`; добавить в `.gitignore` `ui-tests/node_modules/`, `ui-tests/test-results/`, `ui-tests/playwright-report/`, `.gradle/nodejs/`; проверить: `npm ci` в `ui-tests/` проходит без ошибок, а `git status` не показывает `node_modules`
- [x] 1.2 Подключить в `build.gradle.kts` плагин `com.github.node-gradle.node` (`download = true`, Node 24.22.0, `nodeProjectDir = ui-tests`) и задачу `playwrightInstall` (`playwright install chromium`); проверить: `./gradlew playwrightInstall` скачивает Node и Chromium, повторный запуск проходит быстро
- [x] 1.3 Написать `ui-tests/playwright.config.ts`: `webServer` с `java -jar $QUIZ_JAR --server.port=<QUIZ_UI_TEST_PORT|18080> --quiz.data-file=<уникальный файл в os.tmpdir()>`, ожидание `GET /api/cards`, `baseURL`, проекты `desktop-light` (1280×800), `desktop-dark` (тёмная тема), `mobile` (390×844), `locale: ru-RU`, `deviceScaleFactor: 1`, `expect.toHaveScreenshot` с `animations: "disabled"`, `caret: "hide"`, `maxDiffPixelRatio: 0.001`; проверить: пробный тест, открывающий `/`, проходит, а после прогона в `data/` нет новых файлов

## 2. Скриншотные тесты

- [x] 2.1 Создать `ui-tests/tests/fixtures.ts` с хелперами `page.route` для `/api/cards` (список, пустой список, ответ 400 с `error`, обрыв сети) и фикстурой из 3 карточек: короткая, длинная многострочная, с текстом `<b>жирный</b><script>alert(1)</script>`; проверить: `npx tsc --noEmit` в `ui-tests/` проходит
- [x] 2.2 Написать `ui-tests/tests/cards-page.spec.ts` со скриншотами всех состояний из таблицы в `design.md` (пустой список, список, тёмная тема, раскрытый ответ, ошибка валидации, ошибка загрузки, мобильный вид); каждый тест дожидается конечного состояния по видимому элементу; проверить: тесты стабильно проходят на трёх прогонах подряд (`--repeat-each=3`)
- [x] 2.3 Сгенерировать эталоны `./gradlew screenshotUpdate`, просмотреть каждый PNG (вёрстка соответствует странице, HTML-текст карточки виден буквально, тёмная тема применена) и закоммитить `__screenshots__`; проверить: после генерации `./gradlew screenshotTest` проходит

## 3. Интеграция в Gradle

- [x] 3.1 Добавить задачи `screenshotTest` (зависит от `bootJar` и `playwrightInstall`, передаёт `QUIZ_JAR`, объявляет входы `static/**`, `ui-tests/tests/**`, конфиг, lock-файл и jar, а выход — маркер в `build/`) и `screenshotUpdate`; подключить `check.dependsOn(screenshotTest)`; проверить: `./gradlew build` запускает скриншотные тесты, а повторный `./gradlew build` без изменений помечает `screenshotTest` как UP-TO-DATE
- [x] 3.2 Проверить обнаружение регрессии: временно поменять цвет `--accent` в `styles.css`, затем `./gradlew build` падает с сообщением, где указаны отчёт и diff-изображения в `ui-tests/test-results/`; вернуть изменение, и сборка снова проходит

## 4. Хук Claude Code

- [x] 4.1 Создать `.claude/hooks/screenshot-check.sh` (исполняемый): разбор `tool_input.file_path` через `jq`, выход 0 для путей вне `src/main/resources/static/`, запуск `./gradlew screenshotTest -q`, при падении — сводка в stderr и код 2; проверить, подав на вход JSON: путь вне `static/` даёт код 0 без запуска Gradle; путь в `static/` при эталонном CSS даёт код 0; при изменённом `--accent` — код 2 и сводку в stderr
- [x] 4.2 Добавить в `.claude/settings.json` хук `PostToolUse` (matcher `Edit|Write|MultiEdit`, команда `"$CLAUDE_PROJECT_DIR"/.claude/hooks/screenshot-check.sh`, timeout 300); проверить в живой сессии: правка комментария в `styles.css` запускает хук и проходит, а правка `--accent` возвращает Claude сообщение о расхождении скриншотов

## 5. Документация и итоговая проверка

- [x] 5.1 Добавить в `CLAUDE.md` раздел «Скриншотные тесты»: команды `screenshotTest` и `screenshotUpdate`, где смотреть отчёт и diff, правило обновления эталонов (только при намеренном изменении внешнего вида и после подтверждения пользователя), платформенные эталоны (только macOS), описание хука; проверить, что описанные команды выполняются как написано
- [x] 5.2 Выполнить `./gradlew clean build` и убедиться, что проходят и JUnit-тесты, и скриншотные тесты

## Workflow follow-up

- После ревью заархивировать через `/opsx:archive add-ui-screenshot-tests`.
