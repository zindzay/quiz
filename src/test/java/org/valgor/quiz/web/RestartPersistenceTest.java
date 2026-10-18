package org.valgor.quiz.web;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Path;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.valgor.quiz.QuizApplication;

/** Сценарий «Карточки переживают перезапуск»: два независимых запуска приложения на одном файле. */
class RestartPersistenceTest {

    @TempDir
    Path dir;

    private final HttpClient http = HttpClient.newHttpClient();

    @Test
    void cardsSurviveRestart() throws Exception {
        Path file = dir.resolve("cards.csv");
        String body = "{\"question\": \"Что такое \\\"CSV\\\", кратко?\", \"answer\": \"строка 1\\nстрока 2\"}";

        String created;
        try (ConfigurableApplicationContext first = start(file)) {
            HttpResponse<String> response = http.send(
                    HttpRequest.newBuilder(uri(first, "/api/cards"))
                            .header("Content-Type", "application/json")
                            .POST(HttpRequest.BodyPublishers.ofString(body))
                            .build(),
                    HttpResponse.BodyHandlers.ofString());
            assertThat(response.statusCode()).isEqualTo(201);
            created = response.body();
        }

        try (ConfigurableApplicationContext second = start(file)) {
            String list = get(second, "/api/cards");
            assertThat(list).isEqualTo("[" + created + "]");
            assertThat(second.getEnvironment().getProperty("quiz.data-file")).isEqualTo(file.toString());
        }
    }

    private static ConfigurableApplicationContext start(Path file) {
        // Аргументы командной строки, а не properties(): те имеют низший приоритет и перекрываются application.properties
        return new SpringApplicationBuilder(QuizApplication.class)
                .run("--server.port=0", "--quiz.data-file=" + file);
    }

    private String get(ConfigurableApplicationContext context, String path) throws IOException, InterruptedException {
        return http.send(HttpRequest.newBuilder(uri(context, path)).build(), HttpResponse.BodyHandlers.ofString()).body();
    }

    private static URI uri(ConfigurableApplicationContext context, String path) {
        return URI.create("http://localhost:" + context.getEnvironment().getProperty("local.server.port") + path);
    }
}
