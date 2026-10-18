package org.valgor.quiz.service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Autowired;

import org.springframework.stereotype.Service;
import org.valgor.quiz.model.Card;
import org.valgor.quiz.repository.CardRepository;

@Service
public class CardService {

    static final int MAX_LENGTH = 2000;
    static final int MAX_RANDOM_COUNT = 100;

    private final CardRepository repository;
    private final Random random;

    @Autowired
    public CardService(CardRepository repository) {
        this(repository, new Random());
    }

    /** random — источник случайности; в тестах с фиксированным зерном. */
    CardService(CardRepository repository, Random random) {
        this.repository = repository;
        this.random = random;
    }

    public List<Card> list() {
        return repository.findAll();
    }

    public Card get(String id) {
        return repository.findById(id).orElseThrow(() -> new CardNotFoundException(id));
    }

    public Card create(String question, String answer) {
        Card card = new Card(
                UUID.randomUUID().toString(),
                validate("Вопрос", question),
                validate("Ответ", answer));
        repository.save(card);
        return card;
    }

    /**
     * До count разных карточек в случайном порядке: сначала карточки на повторении,
     * оставшиеся места — случайные из остальных.
     */
    public List<Card> random(int count) {
        if (count < 1 || count > MAX_RANDOM_COUNT) {
            throw new ValidationException(randomCountMessage());
        }
        List<Card> review = new ArrayList<>();
        List<Card> rest = new ArrayList<>();
        for (Card card : repository.findAll()) {
            (card.review() ? review : rest).add(card);
        }
        Collections.shuffle(review, random);
        Collections.shuffle(rest, random);
        List<Card> result = new ArrayList<>(review.subList(0, Math.min(count, review.size())));
        result.addAll(rest.subList(0, Math.min(count - result.size(), rest.size())));
        // Перемешиваем весь набор, чтобы вопросы на повторении не шли всегда первыми.
        Collections.shuffle(result, random);
        return result;
    }

    public static String randomCountMessage() {
        return "Количество должно быть целым числом от 1 до " + MAX_RANDOM_COUNT;
    }

    /** Ставит (true) или снимает (false) карточку с повторения. */
    public Card setReview(String id, boolean review) {
        Card card = get(id).withReview(review);
        repository.update(card);
        return card;
    }

    /** label — подпись поля в интерфейсе: сообщение показывается пользователю как есть. */
    private static String validate(String label, String value) {
        if (value == null) {
            throw new ValidationException("Поле «" + label + "» обязательно");
        }
        String trimmed = value.strip();
        if (trimmed.isEmpty()) {
            throw new ValidationException("Поле «" + label + "» не может быть пустым");
        }
        if (trimmed.length() > MAX_LENGTH) {
            throw new ValidationException("Поле «" + label + "» длиннее " + MAX_LENGTH + " символов");
        }
        return trimmed;
    }
}
