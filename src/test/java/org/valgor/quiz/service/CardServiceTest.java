package org.valgor.quiz.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.valgor.quiz.model.Card;
import org.valgor.quiz.repository.CardRepository;

class CardServiceTest {

    private final InMemoryCardRepository repository = new InMemoryCardRepository();
    private final CardService service = new CardService(repository);

    @Test
    void createsCardWithTrimmedTextAndNewId() {
        Card card = service.create("  2+2?  ", "4\n");

        assertThat(card.question()).isEqualTo("2+2?");
        assertThat(card.answer()).isEqualTo("4");
        assertThat(UUID.fromString(card.id())).isNotNull();
        assertThat(repository.findAll()).containsExactly(card);
    }

    @Test
    void generatesDistinctIds() {
        Card first = service.create("Q1", "A1");
        Card second = service.create("Q2", "A2");

        assertThat(first.id()).isNotEqualTo(second.id());
    }

    @Test
    void rejectsBlankQuestion() {
        assertThatThrownBy(() -> service.create("   ", "4"))
                .isInstanceOf(ValidationException.class)
                .hasMessage("Поле «Вопрос» не может быть пустым");
        assertThat(repository.findAll()).isEmpty();
    }

    @Test
    void rejectsMissingAnswer() {
        assertThatThrownBy(() -> service.create("2+2?", null))
                .isInstanceOf(ValidationException.class)
                .hasMessage("Поле «Ответ» обязательно");
        assertThat(repository.findAll()).isEmpty();
    }

    @Test
    void rejectsTooLongText() {
        String tooLong = "x".repeat(CardService.MAX_LENGTH + 1);

        assertThatThrownBy(() -> service.create(tooLong, "A"))
                .isInstanceOf(ValidationException.class)
                .hasMessage("Поле «Вопрос» длиннее 2000 символов");
        assertThatThrownBy(() -> service.create("Q", tooLong)).isInstanceOf(ValidationException.class);
        assertThat(repository.findAll()).isEmpty();
    }

    @Test
    void acceptsMaxLengthAfterTrimming() {
        String atLimit = "  " + "x".repeat(CardService.MAX_LENGTH) + "  ";

        assertThat(service.create(atLimit, "A").question()).hasSize(CardService.MAX_LENGTH);
    }

    @Test
    void listsEmpty() {
        assertThat(service.list()).isEmpty();
    }

    @Test
    void getsExistingCard() {
        Card card = service.create("Q", "A");

        assertThat(service.get(card.id())).isEqualTo(card);
    }

    @Test
    void failsToGetUnknownCard() {
        assertThatThrownBy(() -> service.get("missing")).isInstanceOf(CardNotFoundException.class);
    }

    private static class InMemoryCardRepository implements CardRepository {

        private final List<Card> cards = new ArrayList<>();

        @Override
        public List<Card> findAll() {
            return List.copyOf(cards);
        }

        @Override
        public Optional<Card> findById(String id) {
            return cards.stream().filter(card -> card.id().equals(id)).findFirst();
        }

        @Override
        public void save(Card card) {
            cards.add(card);
        }
    }
}
