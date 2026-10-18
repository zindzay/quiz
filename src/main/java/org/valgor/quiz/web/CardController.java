package org.valgor.quiz.web;

import java.net.URI;
import java.util.List;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.valgor.quiz.model.Card;
import org.valgor.quiz.service.CardService;
import org.valgor.quiz.service.ValidationException;

@RestController
@RequestMapping("/api/cards")
public class CardController {

    private final CardService service;

    public CardController(CardService service) {
        this.service = service;
    }

    @GetMapping
    public List<Card> list() {
        return service.list();
    }

    /** count разбирается вручную, чтобы «abc» и отсутствие параметра давали тот же понятный 400. */
    @GetMapping("/random")
    public List<Card> random(@RequestParam(required = false) String count) {
        int parsed;
        try {
            parsed = Integer.parseInt(count == null ? "" : count.strip());
        } catch (NumberFormatException e) {
            throw new ValidationException(CardService.randomCountMessage());
        }
        return service.random(parsed);
    }

    @GetMapping("/{id}")
    public Card get(@PathVariable String id) {
        return service.get(id);
    }

    @PostMapping
    public ResponseEntity<Card> create(@RequestBody(required = false) CreateCardRequest request) {
        if (request == null) {
            throw new ValidationException("Тело запроса обязательно");
        }
        Card card = service.create(request.question(), request.answer());
        return ResponseEntity.created(URI.create("/api/cards/" + card.id())).body(card);
    }

    @PutMapping("/{id}/review")
    public Card setReview(@PathVariable String id, @RequestBody(required = false) ReviewRequest request) {
        if (request == null || !(request.review() instanceof Boolean review)) {
            throw new ValidationException("Поле review обязательно и должно быть true или false");
        }
        return service.setReview(id, review);
    }
}
