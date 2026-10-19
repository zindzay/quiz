# Proposal

## Why

Сейчас тесты запускаются только локально: `./gradlew build` у разработчика и хук Claude Code после правок `static/`. Репозиторий уже на GitHub (`zindzay/quiz`), но ничто не мешает влить в `master` код, на котором сборка падает, — проверку легко пропустить, а у пулл-реквеста не видно, проходят ли тесты. Нужен CI, который сам прогоняет тесты на каждое изменение `master` и на каждый пулл-реквест.

## What Changes

- Workflow GitHub Actions `.github/workflows/ci.yml`, который запускается:
  - при пуше в `master` (в том числе при мерже пулл-реквеста — мерж приходит в `master` пушем);
  - при создании пулл-реквеста в `master` и при каждом новом коммите в нём (`opened`, `synchronize`, `reopened`).
- Workflow на раннере `ubuntu-latest` выполняет:
  - `./gradlew build -x screenshotTest` — компиляция, JUnit-тесты и e2e-тесты Playwright;
  - `python3 -m unittest discover tools/quiz-import` — тесты скриптов импорта.
- Скриншотные тесты в CI **не** запускаются: эталоны сняты только на macOS (`-darwin`), на Linux их нет. Они остаются локальной проверкой (хук и `./gradlew build` на macOS).
- При падении в результаты запуска выкладываются отчёты (JUnit, Playwright e2e с трейсами), чтобы разобраться без локального воспроизведения.
- `playwrightInstall` в CI ставит Chromium вместе с системными библиотеками (`--with-deps`): на чистом Linux-раннере без них браузер не стартует. Локально поведение не меняется.
- Тесты `split_pdf.swift` пропускаются не только без `swift`, но и не на macOS: на `ubuntu-latest` `swift` установлен, но PDFKit нет, и тесты упали бы.
- `CLAUDE.md` и `README.md`: короткий раздел про CI.

Вне рамок этого изменения:
- скриншотные тесты в CI и эталоны для Linux;
- защита ветки `master` (обязательная проверка перед мержем) — настраивается в GitHub вручную, в разделе CI будет подсказка;
- сборка и публикация артефактов, деплой;
- матрица ОС и версий Java.

## Capabilities

### New Capabilities

Нет.

### Modified Capabilities

Нет. Поведение приложения и скилов не меняется — меняется только то, где и когда запускаются тесты, поэтому для изменения установлен `skip_specs: true` (как в `add-ui-e2e-tests` и `add-ui-screenshot-tests`).

## Impact

- Новый файл `.github/workflows/ci.yml`.
- `build.gradle.kts`: `playwrightInstall` добавляет `--with-deps`, если задана переменная окружения `CI` (GitHub Actions задаёт `CI=true`). Новых зависимостей нет.
- `tools/quiz-import/test_split_pdf.py`: условие пропуска учитывает платформу.
- `CLAUDE.md`, `README.md`: раздел про CI.
- Используются стандартные actions: `actions/checkout`, `actions/setup-java` (Temurin 27), `gradle/actions/setup-gradle` (кеш Gradle), `actions/setup-python`, `actions/upload-artifact`.
- Время одного прогона — ориентировочно 5–10 минут (скачивание JDK, Node и Chromium кешируется частично).
