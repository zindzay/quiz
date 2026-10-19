# Design

## Context

- Сборка: Gradle 9.8 (wrapper), toolchain Java 27. `./gradlew build` = компиляция + JUnit + `check` → `screenshotTest` и `e2eTest`.
- UI-тесты: Node 24 скачивает Node-плагин в `.gradle/nodejs`, `playwrightInstall` — `npx playwright install chromium`. E2e-фикстура запускает jar через `java` из `PATH`, скриншотные тесты — на порту 18080.
- Эталоны скриншотов — только `*-darwin.png` (`snapshotPathTemplate` содержит `{platform}`). На Linux `toHaveScreenshot` не найдёт эталон и упадёт.
- Тесты скриптов импорта — `python3 -m unittest discover tools/quiz-import`, только стандартная библиотека. `test_split_pdf.py` пропускается через `skipUnless(shutil.which("swift"))`, но `split_pdf.swift` использует PDFKit, которого на Linux нет, а `swift` в образе `ubuntu-latest` есть.
- Удалённый репозиторий — `github.com/zindzay/quiz`, рабочая ветка — `master`.

## Goals / Non-Goals

**Goals:**
- Один workflow, одна задача (job) — красный/зелёный статус у коммита и пулл-реквеста.
- Локальные команды (`./gradlew build`, хук) работают как раньше.

**Non-Goals:**
- Ускорение сборки сверх стандартного кеша Gradle.
- Запуск на форках с секретами — секреты не нужны.

## Decisions

### Триггеры: `push` в `master` и `pull_request` в `master`

```yaml
on:
  push:
    branches: [master]
  pull_request:
    branches: [master]
```

Мерж пулл-реквеста создаёт пуш в `master`, отдельного события «мерж» не нужно. У `pull_request` типы по умолчанию — `opened`, `synchronize`, `reopened`: проверка идёт при создании PR и на каждый новый коммит в нём.
Пуши в другие ветки без PR не проверяются — иначе каждый коммит в ветке с открытым PR прогонялся бы дважды (push + pull_request).
Альтернатива — `pull_request` без фильтра веток (PR в любые ветки). Отклонена: других долгоживущих веток нет; фильтр легко расширить.

`concurrency: ci-${{ github.ref }}` с `cancel-in-progress` только для PR: новый коммит в PR отменяет устаревший прогон, а прогоны `master` доводятся до конца, чтобы у каждого коммита `master` был статус.

`permissions: contents: read` — workflow ничего не пишет в репозиторий.

### Linux-раннер без скриншотных тестов

Решение пользователя: `ubuntu-latest`, `./gradlew build -x screenshotTest`. `-x` исключает только скриншоты; `e2eTest` остаётся в `check`.
Альтернативы — `macos-latest` с полным build (дороже в ~10 раз по минутам и ложные расхождения рендера между версиями macOS) и Linux-эталоны в Docker-образе Playwright (второй набор эталонов) — отклонены.

### JDK: `actions/setup-java` с Temurin 27

Toolchain в `build.gradle.kts` требует Java 27. `setup-java` ставит JDK и выставляет `JAVA_HOME`/`PATH`, Gradle находит его как toolchain, а e2e-фикстура — как `java`. Авто-скачивание toolchain через Foojay не настроено и не нужно.

### Кеш: `gradle/actions/setup-gradle`

Кеширует `~/.gradle` (зависимости, wrapper) и проверяет `gradle-wrapper.jar`. Node (`.gradle/nodejs` внутри проекта) и Chromium (`~/.cache/ms-playwright`) не кешируются: их скачивание занимает порядка минуты, а кеш браузера всё равно требует системных библиотек. Можно добавить позже, если прогон станет медленным.

### Системные библиотеки Chromium: `--with-deps` при `CI`

На чистом Ubuntu Chromium без системных библиотек не стартует. В `playwrightInstall`:

```kotlin
args = listOf("install") + (if (System.getenv("CI") != null) listOf("--with-deps") else emptyList()) + "chromium"
```

GitHub Actions задаёт `CI=true`; `--with-deps` ставит пакеты через `sudo apt-get`, на раннерах sudo без пароля. Локально (`CI` не задана) — прежнее поведение, на macOS `--with-deps` не нужен.
Альтернатива — отдельный шаг workflow `npx playwright install-deps chromium`. Отклонена: нужна бы своя Node до Gradle и дублирование версии Playwright.

### Python-тесты: отдельный шаг после Gradle

`actions/setup-python` с Python 3.12 (скрипты пишутся под python3 из Command Line Tools, только stdlib). Шаг выполняется и при падении Gradle (`if: success() || failure()`), чтобы за один прогон были видны обе группы ошибок.
`test_split_pdf.py`: условие пропуска — `sys.platform == "darwin" and shutil.which("swift")`, сообщение «нужен macOS со swift (PDFKit)». На Linux тесты PDF честно пропускаются (видно в выводе `skipped`).

### Отчёты при падении

`actions/upload-artifact` с `if: failure()`, срок хранения 7 дней:
- `build/reports/tests/test/` — HTML-отчёт JUnit;
- `ui-tests/playwright-report-e2e/` и `ui-tests/test-results-e2e/` — отчёт Playwright и трейсы (`trace: retain-on-failure`).

`forbidOnly: !!process.env.CI` в конфигах Playwright начинает работать: забытый `test.only` уронит CI — это желаемо.

### Таймаут

`timeout-minutes: 20` на job — зависший сервер в e2e не съест 6 часов минут по умолчанию.

## Risks / Trade-offs

- [Temurin 27 может быть недоступен в `setup-java` или Gradle 9.8 не поддерживать его как toolchain] → проверяется первым прогоном; запасной вариант — `distribution: oracle` или `zulu`.
- [E2e на Linux впервые: тайминги и шрифты отличаются от macOS] → e2e ищут элементы по ролям и текстам, не по пикселям; падения разбираются по трейсам из артефакта.
- [Регрессии внешнего вида CI не ловит] → остаётся локальный `./gradlew build` на macOS и хук Claude Code; в `CLAUDE.md` это сказано явно.
- [Красный CI не блокирует мерж сам по себе] → в разделе CI подсказка: включить в GitHub Branch protection для `master` с обязательной проверкой `CI / build`.

## Migration Plan

Файл workflow попадает в `master` обычным коммитом; первый прогон — на пуше этого коммита (или на PR с ним). Откат — удалить `.github/workflows/ci.yml`.
