package org.valgor.quiz.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Random;
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

    @Test
    void deletesCard() {
        Card a = service.create("A?", "a");
        Card b = service.create("B?", "b");

        service.delete(a.id());

        assertThat(service.list()).containsExactly(b);
        assertThatThrownBy(() -> service.delete(a.id())).isInstanceOf(CardNotFoundException.class);
    }

    @Test
    void newCardIsNotOnReview() {
        assertThat(service.create("Q?", "A").review()).isFalse();
    }

    @Test
    void setsAndClearsReview() {
        Card card = service.create("Q?", "A");

        assertThat(service.setReview(card.id(), true).review()).isTrue();
        assertThat(repository.findById(card.id())).get().extracting(Card::review).isEqualTo(true);

        assertThat(service.setReview(card.id(), false).review()).isFalse();
        assertThat(repository.findById(card.id())).get().extracting(Card::review).isEqualTo(false);
    }

    @Test
    void setReviewFailsForUnknownCard() {
        assertThatThrownBy(() -> service.setReview("missing", true)).isInstanceOf(CardNotFoundException.class);
    }

    @Test
    void randomReturnsRequestedNumberOfDistinctCards() {
        List<Card> all = createCards(30);

        List<Card> picked = seeded(1).random(10);

        assertThat(picked).hasSize(10).doesNotHaveDuplicates();
        assertThat(all).containsAll(picked);
    }

    @Test
    void randomIncludesAllReviewCardsFirst() {
        List<Card> all = createCards(30);
        List<String> review = all.subList(5, 8).stream().map(card -> service.setReview(card.id(), true).id()).toList();

        for (int seed = 0; seed < 20; seed++) {
            List<Card> picked = seeded(seed).random(10);

            assertThat(picked).hasSize(10).doesNotHaveDuplicates();
            assertThat(picked).extracting(Card::id).containsAll(review);
        }
    }

    @Test
    void randomTakesOnlyReviewCardsWhenThereAreMoreThanRequested() {
        createCards(30).subList(0, 15).forEach(card -> service.setReview(card.id(), true));

        List<Card> picked = seeded(3).random(10);

        assertThat(picked).hasSize(10).doesNotHaveDuplicates().allMatch(Card::review);
    }

    @Test
    void randomReturnsAllCardsWhenFewerThanRequested() {
        List<Card> all = createCards(4);

        assertThat(seeded(1).random(10)).hasSize(4).containsExactlyInAnyOrderElementsOf(all);
    }

    @Test
    void randomOfEmptyStorageIsEmpty() {
        assertThat(service.random(10)).isEmpty();
    }

    @Test
    void randomOrderDependsOnSeed() {
        createCards(30);

        assertThat(seeded(1).random(10)).isNotEqualTo(seeded(2).random(10));
        assertThat(new HashSet<>(seeded(1).random(10))).isNotEqualTo(new HashSet<>(seeded(2).random(10)));
        assertThat(seeded(7).random(10)).isEqualTo(seeded(7).random(10));
    }

    @Test
    void randomRejectsCountOutOfRange() {
        for (int count : new int[] {0, -1, 101}) {
            assertThatThrownBy(() -> service.random(count))
                    .isInstanceOf(ValidationException.class)
                    .hasMessage("Количество должно быть целым числом от 1 до 100");
        }
        assertThat(service.random(100)).isEmpty();
    }

    private List<Card> createCards(int count) {
        List<Card> cards = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            cards.add(service.create("Вопрос " + i + "?", "Ответ " + i));
        }
        return cards;
    }

    private CardService seeded(long seed) {
        return new CardService(repository, new Random(seed));
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

        @Override
        public void update(Card card) {
            cards.replaceAll(existing -> existing.id().equals(card.id()) ? card : existing);
        }

        @Override
        public boolean delete(String id) {
            return cards.removeIf(card -> card.id().equals(id));
        }
    }
}
