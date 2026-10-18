package org.valgor.quiz.repository;

import java.util.List;
import java.util.Optional;

import org.valgor.quiz.model.Card;

public interface CardRepository {

    /** Все карточки в порядке добавления. */
    List<Card> findAll();

    Optional<Card> findById(String id);

    /** Добавляет новую карточку в конец списка. */
    void save(Card card);

    /** Заменяет карточку с тем же id; если такой нет — IllegalArgumentException. */
    void update(Card card);
}
