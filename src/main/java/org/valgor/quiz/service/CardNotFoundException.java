package org.valgor.quiz.service;

public class CardNotFoundException extends RuntimeException {

    public CardNotFoundException(String id) {
        super("Карточка не найдена: " + id);
    }
}
