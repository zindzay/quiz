package org.valgor.quiz.service;

import java.util.List;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.valgor.quiz.model.Card;
import org.valgor.quiz.repository.CardRepository;

@Service
public class CardService {

    static final int MAX_LENGTH = 2000;

    private final CardRepository repository;

    public CardService(CardRepository repository) {
        this.repository = repository;
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
