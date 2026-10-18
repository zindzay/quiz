package org.valgor.quiz.web;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

/** Каждый тест получает новый контекст и пустой файл данных. */
@SpringBootTest
@AutoConfigureMockMvc
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_EACH_TEST_METHOD)
class CardApiTest {

    @TempDir
    static Path tempDir;

    @Autowired
    MockMvcTester mvc;

    @DynamicPropertySource
    static void dataFile(DynamicPropertyRegistry registry) {
        registry.add("quiz.data-file", CardApiTest::dataFile);
    }

    static Path dataFile() {
        return tempDir.resolve("cards.csv");
    }

    @AfterEach
    void deleteDataFile() throws IOException {
        Files.deleteIfExists(dataFile());
    }

    @Test
    void listIsEmptyInitially() {
        assertThat(mvc.get().uri("/api/cards"))
                .hasStatusOk()
                .bodyJson().isLenientlyEqualTo("[]");
    }

    @Test
    void listReturnsCardsInInsertionOrder() {
        create("{\"question\": \"A?\", \"answer\": \"a\"}");
        create("{\"question\": \"B?\", \"answer\": \"b\"}");

        assertThat(mvc.get().uri("/api/cards"))
                .hasStatusOk()
                .bodyJson()
                .extractingPath("$[*].question").asArray().containsExactly("A?", "B?");
    }

    @Test
    void cardJsonHasExactlyIdQuestionAnswer() {
        String id = create("{\"question\": \"A?\", \"answer\": \"a\"}");

        assertThat(mvc.get().uri("/api/cards/" + id))
                .hasStatusOk()
                .bodyJson()
                .isStrictlyEqualTo("{\"id\": \"" + id + "\", \"question\": \"A?\", \"answer\": \"a\"}");
    }

    @Test
    void getReturns404ForUnknownId() {
        assertThat(mvc.get().uri("/api/cards/missing"))
                .hasStatus(HttpStatus.NOT_FOUND)
                .bodyJson().extractingPath("$.error").isNotNull();
    }

    @Test
    void createTrimsTextAndAssignsId() {
        MvcTestResult result = post("{\"question\": \"  2+2?  \", \"answer\": \"4\"}");

        assertThat(result).hasStatus(HttpStatus.CREATED);
        assertThat(result).bodyJson().extractingPath("$.question").isEqualTo("2+2?");
        assertThat(result).bodyJson().extractingPath("$.answer").isEqualTo("4");
        assertThat(result).bodyJson().extractingPath("$.id").asString().isNotBlank();
        assertThat(mvc.get().uri("/api/cards"))
                .bodyJson().extractingPath("$[*].question").asArray().containsExactly("2+2?");
    }

    @Test
    void createIgnoresClientId() {
        MvcTestResult result = post("{\"id\": \"client-id\", \"question\": \"Q\", \"answer\": \"A\"}");

        assertThat(result).hasStatus(HttpStatus.CREATED);
        assertThat(result).bodyJson().extractingPath("$.id").asString().isNotEqualTo("client-id");
    }

    @Test
    void createRejectsBlankQuestion() {
        assertBadRequest(post("{\"question\": \"   \", \"answer\": \"4\"}"));
        assertNoCards();
    }

    @Test
    void createRejectsMissingAnswer() {
        assertBadRequest(post("{\"question\": \"2+2?\"}"));
        assertNoCards();
    }

    @Test
    void createRejectsTooLongText() {
        String tooLong = "x".repeat(2001);

        assertBadRequest(post("{\"question\": \"" + tooLong + "\", \"answer\": \"A\"}"));
        assertBadRequest(post("{\"question\": \"Q\", \"answer\": \"" + tooLong + "\"}"));
        assertNoCards();
    }

    @Test
    void createRejectsMalformedJson() {
        assertBadRequest(post("{\"question\": "));
        assertBadRequest(post(""));
        assertNoCards();
    }

    @Test
    void createPreservesSpecialCharacters() {
        String id = create("{\"question\": \"Что такое \\\"CSV\\\", кратко?\", \"answer\": \"строка 1\\nстрока 2\"}");

        assertThat(mvc.get().uri("/api/cards/" + id))
                .bodyJson().extractingPath("$.question").isEqualTo("Что такое \"CSV\", кратко?");
        assertThat(mvc.get().uri("/api/cards/" + id))
                .bodyJson().extractingPath("$.answer").isEqualTo("строка 1\nстрока 2");
    }

    private MvcTestResult post(String json) {
        return mvc.post().uri("/api/cards")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json)
                .exchange();
    }

    private String create(String json) {
        MvcTestResult result = post(json);
        assertThat(result).hasStatus(HttpStatus.CREATED);
        try {
            return JsonPath.read(result.getResponse().getContentAsString(StandardCharsets.UTF_8), "$.id");
        } catch (UnsupportedEncodingException e) {
            throw new IllegalStateException(e);
        }
    }

    private void assertBadRequest(MvcTestResult result) {
        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result).bodyJson().extractingPath("$.error").asString().isNotBlank();
    }

    private void assertNoCards() {
        assertThat(mvc.get().uri("/api/cards")).bodyJson().isLenientlyEqualTo("[]");
    }
}
