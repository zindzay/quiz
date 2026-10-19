package org.valgor.quiz.web;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

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
    void cardJsonHasExactlyIdQuestionAnswerReview() {
        String id = create("{\"question\": \"A?\", \"answer\": \"a\"}");

        assertThat(mvc.get().uri("/api/cards/" + id))
                .hasStatusOk()
                .bodyJson()
                .isStrictlyEqualTo("{\"id\": \"" + id + "\", \"question\": \"A?\", \"answer\": \"a\", \"review\": false}");
    }

    @Test
    void setsAndClearsReview() {
        String id = create("{\"question\": \"A?\", \"answer\": \"a\"}");

        assertThat(putReview(id, "{\"review\": true}"))
                .hasStatusOk()
                .bodyJson().extractingPath("$.review").isEqualTo(true);
        assertThat(mvc.get().uri("/api/cards/" + id)).bodyJson().extractingPath("$.review").isEqualTo(true);

        assertThat(putReview(id, "{\"review\": false}"))
                .hasStatusOk()
                .bodyJson().extractingPath("$.review").isEqualTo(false);
    }

    @Test
    void setReviewReturns404ForUnknownId() {
        assertThat(putReview("missing", "{\"review\": true}"))
                .hasStatus(HttpStatus.NOT_FOUND)
                .bodyJson().extractingPath("$.error").isNotNull();
    }

    @Test
    void setReviewRejectsInvalidBody() {
        String id = create("{\"question\": \"A?\", \"answer\": \"a\"}");

        for (String body : new String[] {"{}", "{\"review\": \"да\"}", "{\"review\": \"true\"}", "{\"review\": 1}", "{broken"}) {
            assertThat(putReview(id, body))
                    .as(body)
                    .hasStatus(HttpStatus.BAD_REQUEST)
                    .bodyJson().extractingPath("$.error").isNotNull();
        }
        assertThat(mvc.get().uri("/api/cards/" + id)).bodyJson().extractingPath("$.review").isEqualTo(false);
    }

    @Test
    void randomReturnsRequestedNumberOfDistinctCards() {
        for (int i = 0; i < 30; i++) {
            create("{\"question\": \"Q" + i + "?\", \"answer\": \"a\"}");
        }

        MvcTestResult result = mvc.get().uri("/api/cards/random?count=10").exchange();

        assertThat(result).hasStatusOk();
        List<String> ids = JsonPath.read(body(result), "$[*].id");
        assertThat(ids).hasSize(10).doesNotHaveDuplicates();
    }

    @Test
    void randomIncludesReviewCards() {
        List<String> review = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            String id = create("{\"question\": \"Q" + i + "?\", \"answer\": \"a\"}");
            if (i % 10 == 0) {
                putReview(id, "{\"review\": true}");
                review.add(id);
            }
        }

        List<String> ids = JsonPath.read(body(mvc.get().uri("/api/cards/random?count=10").exchange()), "$[*].id");

        assertThat(ids).hasSize(10).containsAll(review);
    }

    @Test
    void randomReturnsAllWhenFewerThanRequested() {
        for (int i = 0; i < 4; i++) {
            create("{\"question\": \"Q" + i + "?\", \"answer\": \"a\"}");
        }

        assertThat(mvc.get().uri("/api/cards/random?count=10"))
                .hasStatusOk()
                .bodyJson().extractingPath("$").asArray().hasSize(4);
    }

    @Test
    void randomOfEmptyStorageIsEmptyArray() {
        assertThat(mvc.get().uri("/api/cards/random?count=10"))
                .hasStatusOk()
                .bodyJson().isStrictlyEqualTo("[]");
    }

    @Test
    void randomRejectsInvalidCount() {
        for (String query : new String[] {"?count=0", "?count=101", "?count=abc", "?count=", ""}) {
            assertThat(mvc.get().uri("/api/cards/random" + query))
                    .as(query)
                    .hasStatus(HttpStatus.BAD_REQUEST)
                    .bodyJson().extractingPath("$.error").isEqualTo("Количество должно быть целым числом от 1 до 100");
        }
    }

    @Test
    void deletesCard() {
        String a = create("{\"question\": \"A?\", \"answer\": \"a\"}");
        create("{\"question\": \"B?\", \"answer\": \"b\"}");

        assertThat(mvc.delete().uri("/api/cards/" + a)).hasStatus(HttpStatus.NO_CONTENT);

        assertThat(mvc.get().uri("/api/cards"))
                .hasStatusOk()
                .bodyJson().extractingPath("$[*].question").asArray().containsExactly("B?");
        assertThat(mvc.get().uri("/api/cards/" + a)).hasStatus(HttpStatus.NOT_FOUND);
    }

    @Test
    void deleteReturns404ForUnknownId() {
        assertThat(mvc.delete().uri("/api/cards/missing"))
                .hasStatus(HttpStatus.NOT_FOUND)
                .bodyJson().extractingPath("$.error").isNotNull();
    }

    @Test
    void deletedReviewCardIsNotInRandom() {
        String a = create("{\"question\": \"A?\", \"answer\": \"a\"}");
        create("{\"question\": \"B?\", \"answer\": \"b\"}");
        putReview(a, "{\"review\": true}");

        mvc.delete().uri("/api/cards/" + a).exchange();

        List<String> ids = JsonPath.read(body(mvc.get().uri("/api/cards/random?count=10").exchange()), "$[*].id");
        assertThat(ids).hasSize(1).doesNotContain(a);
    }

    private MvcTestResult putReview(String id, String body) {
        return mvc.put().uri("/api/cards/" + id + "/review")
                .contentType(MediaType.APPLICATION_JSON)
                .content(body)
                .exchange();
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
        return JsonPath.read(body(result), "$.id");
    }

    private static String body(MvcTestResult result) {
        try {
            return result.getResponse().getContentAsString(StandardCharsets.UTF_8);
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
