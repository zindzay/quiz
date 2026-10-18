package org.valgor.quiz.service;

/** Входные данные карточки не прошли проверку. */
public class ValidationException extends RuntimeException {

    public ValidationException(String message) {
        super(message);
    }
}
