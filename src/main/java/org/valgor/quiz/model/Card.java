package org.valgor.quiz.model;

/** review — карточка на повторении: на неё ответили «Не знал», и она попадает в следующие тесты первой. */
public record Card(String id, String question, String answer, boolean review) {

    /** Новая карточка — не на повторении. */
    public Card(String id, String question, String answer) {
        this(id, question, answer, false);
    }

    public Card withReview(boolean review) {
        return new Card(id, question, answer, review);
    }
}
