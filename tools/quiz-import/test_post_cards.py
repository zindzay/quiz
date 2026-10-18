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


if __name__ == "__main__":
    unittest.main()
