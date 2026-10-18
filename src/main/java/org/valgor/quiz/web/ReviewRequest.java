package org.valgor.quiz.web;

/** Тело PUT /api/cards/{id}/review. Object, а не boolean: строку "true" и другие типы отклоняем, а не приводим. */
public record ReviewRequest(Object review) {
}
