package org.valgor.quiz.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.valgor.quiz.model.Card;

class CsvCardRepositoryTest {

    @TempDir
    Path dir;

    @Test
    void createsFileWithHeaderWhenMissing() throws IOException {
        Path file = dir.resolve("nested/data/cards.csv");

        CsvCardRepository repository = new CsvCardRepository(file);

        assertThat(repository.findAll()).isEmpty();
        assertThat(Files.readString(file, StandardCharsets.UTF_8)).isEqualTo("id,question,answer,review\r\n");
    }

    @Test
    void failsOnWrongHeaderWithoutTouchingFile() throws IOException {
        Path file = dir.resolve("cards.csv");
        String content = "id,text\r\n1,hello\r\n";
        Files.writeString(file, content, StandardCharsets.UTF_8);

        assertThatThrownBy(() -> new CsvCardRepository(file))
                .isInstanceOf(DataFileException.class)
                .hasMessageContaining(file.toAbsolutePath().toString());
        assertThat(Files.readString(file, StandardCharsets.UTF_8)).isEqualTo(content);
    }

    @Test
    void failsOnBrokenStructureWithoutTouchingFile() throws IOException {
        Path file = dir.resolve("cards.csv");
        String content = "id,question,answer\r\n1,\"unterminated,answer\r\n";
        Files.writeString(file, content, StandardCharsets.UTF_8);

        assertThatThrownBy(() -> new CsvCardRepository(file))
                .isInstanceOf(DataFileException.class)
                .hasMessageContaining(file.toAbsolutePath().toString());
        assertThat(Files.readString(file, StandardCharsets.UTF_8)).isEqualTo(content);
    }

    @Test
    void failsOnRowWithWrongFieldCount() throws IOException {
        Path file = dir.resolve("cards.csv");
        Files.writeString(file, "id,question,answer\r\n1,only question\r\n", StandardCharsets.UTF_8);

        assertThatThrownBy(() -> new CsvCardRepository(file)).isInstanceOf(DataFileException.class);
    }

    @Test
    void keepsInsertionOrder() {
        CsvCardRepository repository = new CsvCardRepository(dir.resolve("cards.csv"));
        Card a = new Card("a", "Q1", "A1");
        Card b = new Card("b", "Q2", "A2");

        repository.save(a);
        repository.save(b);

        assertThat(repository.findAll()).containsExactly(a, b);
        assertThat(repository.findById("b")).contains(b);
        assertThat(repository.findById("missing")).isEmpty();
    }

    @Test
    void persistsAcrossInstancesWithSpecialCharacters() {
        Path file = dir.resolve("cards.csv");
        Card tricky = new Card("1", "Что такое \"CSV\", кратко?", "Первая строка,\nвторая строка «ёлка»");
        Card plain = new Card("2", "2+2?", "4");

        CsvCardRepository first = new CsvCardRepository(file);
        first.save(tricky);
        first.save(plain);

        CsvCardRepository reopened = new CsvCardRepository(file);
        assertThat(reopened.findAll()).containsExactly(tricky, plain);
    }

    @Test
    void leavesNoTemporaryFilesAfterSave() throws IOException {
        Path file = dir.resolve("cards.csv");
        CsvCardRepository repository = new CsvCardRepository(file);

        repository.save(new Card("1", "Q", "A"));

        try (var files = Files.list(dir)) {
            assertThat(files).containsExactly(file);
        }
    }

    @Test
    void persistsReviewFlag() {
        Path file = dir.resolve("cards.csv");
        CsvCardRepository repository = new CsvCardRepository(file);
        repository.save(new Card("1", "Q1", "A1"));
        repository.save(new Card("2", "Q2", "A2", true));

        assertThat(new CsvCardRepository(file).findAll())
                .containsExactly(new Card("1", "Q1", "A1", false), new Card("2", "Q2", "A2", true));
    }

    @Test
    void updatesCardInPlaceAndPersists() {
        Path file = dir.resolve("cards.csv");
        CsvCardRepository repository = new CsvCardRepository(file);
        repository.save(new Card("1", "Q1", "A1"));
        repository.save(new Card("2", "Q2", "A2"));

        repository.update(new Card("1", "Q1", "A1", true));

        assertThat(repository.findById("1")).contains(new Card("1", "Q1", "A1", true));
        assertThat(new CsvCardRepository(file).findAll())
                .containsExactly(new Card("1", "Q1", "A1", true), new Card("2", "Q2", "A2", false));
    }

    @Test
    void updateOfUnknownCardFails() {
        CsvCardRepository repository = new CsvCardRepository(dir.resolve("cards.csv"));

        assertThatThrownBy(() -> repository.update(new Card("missing", "Q", "A", true)))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void readsLegacyFileWithoutChangingIt() throws IOException {
        Path file = dir.resolve("cards.csv");
        String legacy = "id,question,answer\r\n1,Q1,A1\r\n2,\"Q, 2\",A2\r\n";
        Files.writeString(file, legacy, StandardCharsets.UTF_8);

        CsvCardRepository repository = new CsvCardRepository(file);

        assertThat(repository.findAll())
                .containsExactly(new Card("1", "Q1", "A1", false), new Card("2", "Q, 2", "A2", false));
        assertThat(Files.readString(file, StandardCharsets.UTF_8)).isEqualTo(legacy);
    }

    @Test
    void firstWriteMigratesLegacyFile() throws IOException {
        Path file = dir.resolve("cards.csv");
        Files.writeString(file, "id,question,answer\r\n1,Q1,A1\r\n2,Q2,A2\r\n", StandardCharsets.UTF_8);

        new CsvCardRepository(file).save(new Card("3", "Q3", "A3"));

        assertThat(Files.readString(file, StandardCharsets.UTF_8)).isEqualTo(
                "id,question,answer,review\r\n1,Q1,A1,false\r\n2,Q2,A2,false\r\n3,Q3,A3,false\r\n");
        assertThat(new CsvCardRepository(file).findAll()).extracting(Card::id).containsExactly("1", "2", "3");
    }

    @Test
    void failsOnInvalidReviewValueWithoutTouchingFile() throws IOException {
        Path file = dir.resolve("cards.csv");
        String content = "id,question,answer,review\r\n1,Q1,A1,yes\r\n";
        Files.writeString(file, content, StandardCharsets.UTF_8);

        assertThatThrownBy(() -> new CsvCardRepository(file))
                .isInstanceOf(DataFileException.class)
                .hasMessageContaining("review");
        assertThat(Files.readString(file, StandardCharsets.UTF_8)).isEqualTo(content);
    }
}
