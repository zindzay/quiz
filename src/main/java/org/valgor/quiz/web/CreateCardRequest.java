package org.valgor.quiz.web;

/** Тело запроса на создание карточки. Поля id нет, поэтому присланный клиентом id игнорируется. */
public record CreateCardRequest(String question, String answer) {
}
