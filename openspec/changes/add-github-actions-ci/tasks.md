# Tasks

## 1. Подготовка тестов к Linux

- [x] 1.1 `tools/quiz-import/test_split_pdf.py`: пропускать тесты, если не `sys.platform == "darwin"` или нет `swift`; сообщение — «нужен macOS со swift (PDFKit)». Проверка: `python3 -m unittest discover tools/quiz-import` на macOS по-прежнему запускает тесты PDF (не `skipped`); мутация — временно заменить условие на `"linux"` и убедиться, что тесты PDF уходят в `skipped`.
- [x] 1.2 `build.gradle.kts`: `playwrightInstall` добавляет `--with-deps`, если задана переменная `CI`. Проверка: `./gradlew playwrightInstall --dry-run` проходит; `CI=true ./gradlew playwrightInstall --info` показывает в командной строке `install --with-deps chromium` (на macOS `--with-deps` безвреден), без `CI` — `install chromium`.

## 2. Workflow GitHub Actions

- [x] 2.1 Создать `.github/workflows/ci.yml` по `design.md`: имя `CI`, job `build` на `ubuntu-latest`, `timeout-minutes: 20`, `permissions: contents: read`; триггеры `push` и `pull_request` в `master`; `concurrency` с отменой устаревших прогонов только для PR; шаги — `actions/checkout`, `actions/setup-java` (Temurin 27), `gradle/actions/setup-gradle`, `./gradlew build -x screenshotTest`, `actions/setup-python` (3.12) и `python3 -m unittest discover tools/quiz-import` (`if: success() || failure()`), `actions/upload-artifact` отчётов JUnit и Playwright e2e при `failure()` (7 дней). Проверка: YAML разбирается — `ruby -ryaml -e 'YAML.load_file(".github/workflows/ci.yml")'` (PyYAML в stdlib нет); версии actions — актуальные мажорные.
- [x] 2.2 Локально воспроизвести команды CI: `./gradlew build -x screenshotTest` и `python3 -m unittest discover tools/quiz-import` проходят. Проверка: обе команды завершаются с кодом 0.

## 3. Документация

- [x] 3.1 `CLAUDE.md`: раздел «CI (GitHub Actions)» — когда запускается (push и PR в `master`), что выполняет, что скриншотные тесты в CI не запускаются и остаются локальной проверкой на macOS, где смотреть отчёты при падении (артефакты прогона), подсказка про Branch protection с обязательной проверкой `CI / build`; в разделе «Скриншотные тесты» заменить «на Linux/CI нужны свои эталоны — пока не настроено» ссылкой на этот раздел. Проверка: команды в разделе совпадают с шагами `ci.yml`.
- [x] 3.2 `README.md`: одна строка про CI и бейдж статуса workflow `https://github.com/zindzay/quiz/actions/workflows/ci.yml/badge.svg?branch=master`. Проверка: ссылка бейджа указывает на `ci.yml` и ветку `master`.

## 4. Проверка на GitHub

- [ ] 4.1 С согласия пользователя запушить ветку с изменением и открыть пулл-реквест в `master`. Проверка: workflow `CI` запустился на событии `pull_request` и завершился успешно; в логе Python-шага тесты PDF — `skipped`.
- [ ] 4.2 Мутация: в той же ветке временно сломать JUnit-тест (коммит с `fail()`), убедиться, что прогон PR красный и в артефактах есть отчёт JUnit; откатить коммит и убедиться, что прогон снова зелёный.
- [x] 4.3 Убедиться, что `./gradlew build` проходит локально (на macOS, включая `screenshotTest`).

## Workflow follow-up

- После мержа PR проверить, что workflow запустился на событии `push` в `master` и прошёл.
- По желанию — включить Branch protection для `master` с обязательной проверкой `CI / build` (настройка GitHub, делает пользователь).
- Архивировать изменение (`/opsx:archive add-github-actions-ci`).
