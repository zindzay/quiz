# Tasks

## 1. Каркас проекта

- [x] 1.1 Добавить в `build.gradle.kts` плагины `org.springframework.boot` и `io.spring.dependency-management` (последняя стабильная версия Boot), зависимости `spring-boot-starter-web`, Apache Commons CSV, `spring-boot-starter-test` (test); проверить: `./gradlew dependencies --configuration runtimeClasspath` разрешается без ошибок, а сборка работает на JDK 27 (иначе понизить toolchain, как сказано в `design.md`)
- [x] 1.2 Удалить `src/main/java/org/valgor/Main.java`, создать `org.valgor.quiz.QuizApplication` (`@SpringBootApplication`) и пакеты `org.valgor.quiz.{config,model,repository,service,web}`, `application.properties` с `quiz.data-file=data/cards.csv` и `server.port=8080`; добавить `data/` в `.gitignore` и пример `data/cards.example.csv` с двумя карточками; проверить: `./gradlew build` проходит (тест `contextLoads`), `git check-ignore data/cards.csv` срабатывает

## 2. Модель и CSV-хранилище

- [x] 2.1 Создать `record Card(String id, String question, String answer)` и интерфейс `CardRepository` (`findAll`, `findById`, `save`); проверить: `./gradlew compileJava`
- [x] 2.2 Реализовать `CsvCardRepository` (`@Repository`, путь из `QuizProperties`): чтение файла при создании бина, создание файла с заголовком при его отсутствии, ошибка с путём к файлу при неверном заголовке без изменения файла; проверить тестами без Spring в `@TempDir`: «Файл данных отсутствует» и «Повреждённый файл»
- [x] 2.3 Реализовать `save` с записью во временный файл и `ATOMIC_MOVE`, а также синхронизацию через `ReentrantReadWriteLock`; проверить тестами: порядок `findAll` совпадает с порядком добавления, данные сохраняются после пересоздания репозитория на том же файле, текст с запятыми, кавычками, переводами строк и кириллицей читается без искажений

## 3. Сервисный слой

- [x] 3.1 Реализовать `CardService.create`: обрезка пробелов, проверка на пустоту и длину не больше 2000 символов (`ValidationException`), генерация UUID; проверить юнит-тестами на репозитории в памяти: успешное создание с обрезкой, пустой вопрос, отсутствующий ответ, превышение длины, отклонённая карточка не сохраняется
- [x] 3.2 Реализовать `CardService.list` и `CardService.get` (`CardNotFoundException` для неизвестного id); проверить юнит-тестами: пустой список, найденная и ненайденная карточка

## 4. HTTP API

- [x] 4.1 Реализовать `QuizProperties` (`@ConfigurationProperties("quiz")`) и вывод в лог пути к файлу данных при старте; проверить: `./gradlew bootRun` стартует на 8080, а `QUIZ_DATA_FILE=/tmp/x.csv SERVER_PORT=9090 ./gradlew bootRun` использует переданные значения
- [x] 4.2 Реализовать `CardController` (`GET /api/cards`, `GET /api/cards/{id}`, `POST /api/cards` с `CreateCardRequest` без поля `id`) и `ApiExceptionHandler` (`ValidationException` и `HttpMessageNotReadableException` → 400, `CardNotFoundException` → 404, тело `{"error": "..."}`); проверить тестами `@SpringBootTest` + MockMvc с `quiz.data-file` во временной директории (`@DynamicPropertySource`) все сценарии из `specs/cards/spec.md`
- [x] 4.3 Добавить HTTP-тест «карточки переживают перезапуск»: создать карточку, поднять второй контекст через `SpringApplicationBuilder` на том же файле, проверить `GET /api/cards`

## 5. Веб-интерфейс

- [x] 5.1 Создать `static/index.html`, `styles.css`, `app.js`: загрузка и вывод списка через `textContent`, сообщение для пустого списка, раскрытие и скрытие ответа по клику; проверить автотестом, что `GET /` отдаёт 200 с `Content-Type: text/html`
- [x] 5.2 Реализовать форму добавления: `POST /api/cards`, добавление карточки в конец списка без перезагрузки, очистка полей при успехе; при ошибке — показ сообщения из `error` (или сообщения о недоступности сервера) без очистки полей; проверить вручную в браузере сценарии «Успешное добавление» и «Пустое поле»
- [x] 5.3 Проверить вручную в браузере сценарии «Открытие страницы», «Нет карточек», «Показ и скрытие ответа», «HTML в тексте карточки» (скрипт не выполняется, текст виден буквально)

## 6. Документация и итоговая проверка

- [x] 6.1 Обновить `CLAUDE.md`: стек Spring Boot, команда `./gradlew bootRun`, настройки `quiz.data-file`/`QUIZ_DATA_FILE` и `server.port`/`SERVER_PORT`, пакет `org.valgor.quiz`, предупреждение не редактировать CSV при работающем приложении; проверить, что описанная команда запускает приложение
- [x] 6.2 Выполнить `./gradlew clean build`, убедиться, что все тесты проходят

## Workflow follow-up

- После ревью и ручной проверки заархивировать изменение через `/opsx:archive add-card-view-and-create`.
