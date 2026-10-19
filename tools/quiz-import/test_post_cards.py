"""Тесты post_cards.py на поддельном API (http.server в отдельном потоке).

Запуск: python3 -m unittest discover tools/quiz-import
"""

import contextlib
import io
import json
import os
import socket
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
import post_cards  # noqa: E402


class FakeApi:
    """Минимальная имитация /api/cards: хранит карточки, отклоняет вопросы из reject."""

    def __init__(self, cards=None, reject=None):
        self.cards = list(cards or [])
        self.reject = set(reject or [])
        self.posted = []
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, status, body):
                raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                self._send(200, api.cards)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                api.posted.append(body)
                if body["question"] in api.reject:
                    self._send(400, {"error": "Поле «Вопрос» не может быть пустым"})
                    return
                card = {"id": str(len(api.cards) + 1), "question": body["question"].strip(),
                        "answer": body["answer"].strip()}
                api.cards.append(card)
                self._send(201, card)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def unused_url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return f"http://127.0.0.1:{s.getsockname()[1]}"


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = post_cards.main(argv)
    return code, out.getvalue(), err.getvalue()


class BaseUrlTest(unittest.TestCase):
    def test_priority_cli_env_default(self):
        with mock.patch.dict(os.environ, {"QUIZ_API_URL": "http://env:1/"}):
            self.assertEqual(post_cards.base_url("http://cli:2"), "http://cli:2")
            self.assertEqual(post_cards.base_url(None), "http://env:1")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(post_cards.base_url(None), "http://localhost:8080")


class CheckTest(unittest.TestCase):
    def test_available_api(self):
        api = FakeApi()
        self.addCleanup(api.close)
        code, out, _ = run(["check", "--api", api.url])
        self.assertEqual(code, 0)
        self.assertIn(api.url, out)

    def test_unavailable_api_suggests_boot_run(self):
        code, _, err = run(["check", "--api", unused_url()])
        self.assertEqual(code, 2)
        self.assertIn("./gradlew bootRun", err)


class PostTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def post(self, api, cards):
        path = os.path.join(self.tmp.name, "cards.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cards, f, ensure_ascii=False)
        code, out, err = run(["post", path, "--api", api.url])
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def api(self, **kwargs):
        api = FakeApi(**kwargs)
        self.addCleanup(api.close)
        return api

    def test_successful_import(self):
        api = self.api()
        report = self.post(api, [{"question": "Что такое HTTP?", "answer": "Протокол."},
                                 {"question": "Что такое TCP?", "answer": "Транспорт."}])
        self.assertEqual(report["added"], ["Что такое HTTP?", "Что такое TCP?"])
        self.assertEqual(report["skipped"], [])
        self.assertEqual(report["failed"], [])
        self.assertEqual([c["question"] for c in api.cards], ["Что такое HTTP?", "Что такое TCP?"])

    def test_existing_question_skipped_ignoring_case_and_spaces(self):
        api = self.api(cards=[{"id": "1", "question": "Что такое HTTP?", "answer": "Протокол."}])
        report = self.post(api, [{"question": "  что такое http? ", "answer": "Другой ответ"}])
        self.assertEqual(report["added"], [])
        self.assertEqual(report["skipped"], ["что такое http?"])
        self.assertEqual(api.posted, [])

    def test_duplicate_within_file_skipped(self):
        api = self.api()
        report = self.post(api, [{"question": "Вопрос", "answer": "1"},
                                 {"question": "ВОПРОС ", "answer": "2"}])
        self.assertEqual(report["added"], ["Вопрос"])
        self.assertEqual(report["skipped"], ["ВОПРОС"])
        self.assertEqual(len(api.posted), 1)

    def test_partial_failure_does_not_stop_others(self):
        questions = [f"Вопрос {i}" for i in range(10)]
        api = self.api(reject={"Вопрос 3"})
        report = self.post(api, [{"question": q, "answer": "ответ"} for q in questions])
        self.assertEqual(len(report["added"]), 9)
        self.assertEqual(report["failed"], [{"question": "Вопрос 3", "error": "Поле «Вопрос» не может быть пустым"}])
        self.assertEqual(len(api.posted), 10)

    def test_too_long_field_fails_without_request(self):
        api = self.api()
        report = self.post(api, [{"question": "Q", "answer": "x" * 2001},
                                 {"question": "Q2", "answer": "ok"}])
        self.assertEqual(report["added"], ["Q2"])
        self.assertEqual(len(report["failed"]), 1)
        self.assertIn("2000", report["failed"][0]["error"])
        self.assertEqual([p["question"] for p in api.posted], ["Q2"])

    def test_missing_field_fails(self):
        api = self.api()
        report = self.post(api, [{"question": "Без ответа"}])
        self.assertEqual(report["added"], [])
        self.assertEqual(len(report["failed"]), 1)

    def test_unavailable_api_returns_code_2(self):
        path = os.path.join(self.tmp.name, "cards.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump([{"question": "Q", "answer": "A"}], f)
        code, _, err = run(["post", path, "--api", unused_url()])
        self.assertEqual(code, 2)
        self.assertIn("./gradlew bootRun", err)

    def test_invalid_json_file_returns_code_1(self):
        path = os.path.join(self.tmp.name, "cards.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{не json")
        code, _, _ = run(["post", path, "--api", unused_url()])
        self.assertEqual(code, 1)


EMPTY_VAR = {"question": "Почему у пустого списка, объявленного через var, тип указывают явно, например new ArrayList<String>()?",
             "answer": "Иначе создаётся ArrayList<Object>, и вернуть его из метода с типом List<String> не получится: "
                       "компилятор сообщит incompatible types."}
INCOMPATIBLE = {"question": "Какую ошибку сообщит компилятор, если вернуть var items = new ArrayList<>(); "
                            "из метода с типом List<String>?", "answer": "incompatible types."}
SET = {"question": "Что делает метод set() у ArrayList?", "answer": "Заменяет элемент списка по указанному индексу на новый."}
REMOVE = {"question": "Что делает метод remove() у ArrayList?", "answer": "Удаляет элемент списка по указанному индексу."}
INDEX_RULE = {"question": "С какого числа начинается индексация элементов ArrayList?", "answer": "С нуля, как и в массивах."}
INDEX_EXAMPLE = {"question": "Какой индекс получит первый элемент, добавленный в ArrayList через add()?", "answer": "Индекс 0."}
HTTPS = {"question": "Какой порт по умолчанию использует HTTPS?", "answer": "443."}


class SimilarTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def similar(self, existing, cards):
        api = FakeApi(cards=[dict(card, id=str(i)) for i, card in enumerate(existing)])
        self.addCleanup(api.close)
        path = os.path.join(self.tmp.name, "cards.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cards, f, ensure_ascii=False)
        code, out, err = run(["similar", path, "--api", api.url])
        self.assertEqual(0, code, err)
        self.assertEqual([], api.posted)
        return json.loads(out)

    def test_paraphrased_question_has_app_candidate(self):
        result = self.similar([EMPTY_VAR, HTTPS], [INCOMPATIBLE])
        self.assertEqual(1, len(result))
        self.assertEqual(0, result[0]["index"])
        candidate = result[0]["candidates"][0]
        self.assertEqual("app", candidate["source"])
        self.assertEqual(EMPTY_VAR["question"], candidate["question"])
        self.assertEqual(EMPTY_VAR["answer"], candidate["answer"])
        self.assertGreaterEqual(candidate["score"], post_cards.SIMILAR_THRESHOLD)
        self.assertNotIn(HTTPS["question"], [c["question"] for c in result[0]["candidates"]])

    def test_same_topic_other_fact_is_candidate_for_model(self):
        result = self.similar([SET], [REMOVE])
        self.assertEqual([SET["question"]], [c["question"] for c in result[0]["candidates"]])

    def test_rule_and_example_in_same_set(self):
        result = self.similar([], [INDEX_RULE, INDEX_EXAMPLE])
        self.assertEqual(1, len(result))
        self.assertEqual(1, result[0]["index"])
        self.assertEqual([{"source": "set", "index": 0, "question": INDEX_RULE["question"]}],
                         [{k: c[k] for k in ("source", "index", "question")} for c in result[0]["candidates"]])

    def test_unrelated_card_not_in_output(self):
        self.assertEqual([], self.similar([SET, EMPTY_VAR], [HTTPS]))

    def test_at_most_three_candidates_best_first(self):
        existing = [{"question": f"Что делает метод set() у ArrayList, вариант {i}?", "answer": SET["answer"]}
                    for i in range(5)] + [REMOVE]
        candidates = self.similar(existing, [SET])[0]["candidates"]
        self.assertEqual(post_cards.MAX_CANDIDATES, len(candidates))
        scores = [c["score"] for c in candidates]
        self.assertEqual(sorted(scores, reverse=True), scores)

    def test_unavailable_api_returns_code_2(self):
        path = os.path.join(self.tmp.name, "cards.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump([SET], f, ensure_ascii=False)
        code, _, err = run(["similar", path, "--api", unused_url()])
        self.assertEqual(2, code)
        self.assertIn("./gradlew bootRun", err)


class LintTest(unittest.TestCase):
    def lint(self, cards):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cards.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cards, f, ensure_ascii=False)
            code, out, _ = run(["lint", path])
        return code, json.loads(out)

    def test_answer_repeats_question(self):
        code, found = self.lint([{"question": "Что делает метод set(), заменяющий элемент?", "answer": "Заменяет элемент"}])
        self.assertEqual(3, code)
        self.assertEqual([{"index": 0, "question": "Что делает метод set(), заменяющий элемент?",
                           "reason": "answer_in_question"}], found)

    def test_yes_no_answers(self):
        code, found = self.lint([{"question": "Можно ли изменить List.of()?", "answer": "да"},
                                 {"question": "Компилируется ли ArrayList<int>?", "answer": "Нет."}])
        self.assertEqual(3, code)
        self.assertEqual(["yes_no", "yes_no"], [f["reason"] for f in found])

    def test_question_about_lesson(self):
        code, found = self.lint([{"question": "Какую библиотеку будут использовать в этом уроке и последующих курсах?",
                                  "answer": "commons-collections4."}])
        self.assertEqual(3, code)
        self.assertEqual("source_reference", found[0]["reason"])

    def test_clean_set(self):
        self.assertEqual((0, []), self.lint([SET, REMOVE, INDEX_RULE, HTTPS, INCOMPATIBLE]))

    def assertCompound(self, questions):
        code, found = self.lint([{"question": q, "answer": "Ответ про обход коллекций."} for q in questions])
        self.assertEqual(3, code)
        self.assertEqual([(i, "compound_question") for i in range(len(questions))],
                         [(f["index"], f["reason"]) for f in found])

    def test_conjunction_with_second_question_word(self):
        self.assertCompound(["Что такое итератор и зачем он нужен?",
                             "Что возвращает iterator() и в чём его преимущество перед for?",
                             "Как создать итератор, а также что вернёт next() в конце?"])

    def test_two_question_marks(self):
        self.assertCompound(["Какой список создаёт `List.of()`? Как сделать его изменяемым?"])

    def test_english_compound_question(self):
        self.assertCompound(["What is an iterator and why is it needed?"])

    def test_contrast_choice_comparison_and_enumeration_not_compound(self):
        questions = ["Когда обходить список циклом `for`, а когда `for-each`?",
                     "Чем `WHERE` отличается от `HAVING`?",
                     "Что выбрать для обхода списка — `for` или `for-each`?",
                     "Какие классы-обёртки используют вместо `int` и `char`?",
                     "Что вернёт выражение `x > 0 ? x : -x` при x = -3?",
                     "Кто и когда предложил реляционную модель данных?"]
        self.assertEqual((0, []), self.lint([{"question": q, "answer": "Ответ про обход коллекций."}
                                             for q in questions]))

    def test_real_sets_have_no_false_findings(self):
        """Наборы ручных прогонов: находки — только настоящие составные вопросы из наборов до one-thought-per-card."""
        path = os.path.join(os.path.dirname(__file__), "fixtures", "real-cards.json")
        with open(path, encoding="utf-8") as f:
            sets = json.load(f)
        found = {name: [(f["index"], f["reason"]) for f in post_cards.lint(cards)] for name, cards in sets.items()}
        self.assertEqual({"arraylist": [], "list-traversal": [],
                          "http": [(5, "compound_question"), (17, "compound_question")],
                          "databases": [(32, "compound_question")]}, found)


if __name__ == "__main__":
    unittest.main()
