"""Тесты fetch_page.py: HTML-фикстуры из fixtures/ и сгенерированные страницы на локальном http.server.

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

sys.path.insert(0, os.path.dirname(__file__))
import fetch_page  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class PageServer:
    """Отдаёт файлы из fixtures/ и страницы, добавленные через add(); остальное — 404."""

    def __init__(self):
        self.pages = {}
        self.user_agents = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                server.user_agents.append(self.headers.get("User-Agent"))
                name = self.path.lstrip("/")
                if self.path in server.pages:
                    content_type, body = server.pages[self.path]
                elif name and "/" not in name and os.path.isfile(os.path.join(FIXTURES, name)):
                    content_type = "text/html"
                    with open(os.path.join(FIXTURES, name), "rb") as f:
                        body = f.read()
                else:
                    self.send_error(404, "Not Found")
                    return
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def add(self, path, html, content_type="text/html; charset=utf-8"):
        self.pages[path] = (content_type, html.encode("utf-8") if isinstance(html, str) else html)
        return self.url + path

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def unused_url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return f"http://127.0.0.1:{s.getsockname()[1]}/page"


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = fetch_page.main(argv)
    return code, out.getvalue(), err.getvalue()


def fixture_text(name):
    with open(os.path.join(FIXTURES, name), "rb") as f:
        raw = f.read()
    title, blocks = fetch_page.extract(raw.decode(fetch_page.detect_charset(raw, "text/html")))
    return title, fetch_page.join_blocks(blocks)


def paragraph(section, number, length=600):
    head = f"Раздел {section}, абзац {number}: "
    words = " ".join(f"слово{(section * 31 + number * 7 + k) % 97}" for k in range(length))
    return (head + words)[:length].rstrip() + "."


def make_article(sections, paragraph_length=600, intro=2):
    """sections — список (заголовок, число абзацев); перед ними вводные абзацы и <h1>."""
    parts = ["<html><head><title>Сгенерированная статья</title></head><body>",
             "<nav>НАВИГАЦИЯ</nav><main><h1>Сгенерированная статья</h1>"]
    parts += [f"<p>{paragraph(0, j, paragraph_length)}</p>" for j in range(intro)]
    for i, (title, count) in enumerate(sections, 1):
        parts.append(f"<h2>{title}</h2>")
        parts += [f"<p>{paragraph(i, j, paragraph_length)}</p>" for j in range(count)]
    parts.append("</main><footer>ФУТЕР</footer></body></html>")
    return "".join(parts)


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.server = PageServer()
        self.addCleanup(self.server.close)
        self.out = tempfile.mkdtemp()

    def read_meta(self):
        with open(os.path.join(self.out, "meta.json"), encoding="utf-8") as f:
            return json.load(f)

    def read_chunks(self, meta):
        texts = []
        for chunk in meta["chunks"]:
            with open(os.path.join(self.out, chunk["file"]), encoding="utf-8") as f:
                texts.append(f.read().rstrip("\n"))
        return texts


class ExtractionTest(unittest.TestCase):
    """Решение 2 design.md: корень, удаляемые элементы, Markdown."""

    @classmethod
    def setUpClass(cls):
        cls.title, cls.text = fixture_text("article.html")

    def test_title_from_title_tag(self):
        self.assertEqual("Протокол HTTP — Тестовая энциклопедия", self.title)

    def test_main_is_root(self):
        self.assertIn("HTTP — протокол прикладного уровня", self.text)
        for outside in ("ШАПКА-САЙТА", "НАВИГАЦИЯ-ССЫЛКА", "БОКОВАЯ-ПАНЕЛЬ", "ВРЕЗКА-ВНЕ-MAIN",
                        "КОММЕНТАРИЙ", "ПРОМО-ВНЕ-MAIN", "ФУТЕР-САЙТА", "КОНТАКТЫ-CONTENTINFO", "COOKIE-ТЕКСТ"):
            self.assertNotIn(outside, self.text)

    def test_service_tags_removed(self):
        for removed in ("СКРИПТ-ТЕКСТ", "display: none", "ВРЕЗКА-ASIDE", "ПОИСК-ТЕКСТ",
                        "СКРЫТЫЙ-HIDDEN", "СКРЫТЫЙ-ARIA"):
            self.assertNotIn(removed, self.text)

    def test_removed_by_class_and_id_words(self):
        for removed in ("ОГЛАВЛЕНИЕ", "ПРАВИТЬ-ССЫЛКА", "[1]", "СНОСКА-ТЕКСТ"):
            self.assertNotIn(removed, self.text)
        self.assertIn("Слово navigator в классе не совпадает", self.text)

    def test_role_removed_and_article_root_without_main(self):
        html = ("<body><div role='navigation'>РОЛЬ-НАВИГАЦИЯ</div>"
                "<article><p>Короткая заметка.</p></article>"
                "<article><div role='banner'>РОЛЬ-БАННЕР</div><p>Основная статья, самая длинная на странице.</p></article>"
                "<p>Текст вне статей.</p></body>")
        _, blocks = fetch_page.extract(html)
        self.assertEqual("Основная статья, самая длинная на странице.", fetch_page.join_blocks(blocks))

    def test_headings(self):
        self.assertIn("# Протокол HTTP\n\n", self.text)
        self.assertIn("\n\n## История\n\n", self.text)
        self.assertIn("\n\n## Коды состояния\n\n", self.text)

    def test_lists(self):
        self.assertIn("- GET — получение ресурса.\n"
                      "- POST — передача данных на сервер.\n"
                      "  - Форма отправляется методом POST.\n"
                      "- DELETE — удаление ресурса.", self.text)
        self.assertIn("1. Клиент открывает соединение.\n2. Клиент отправляет запрос.\n3. Сервер отвечает.",
                      self.text)

    def test_tables(self):
        self.assertIn("Частые коды\nКод | Значение\n200 | OK\n404 | Not Found\n500 | Internal Server Error",
                      self.text)

    def test_code(self):
        self.assertIn("```\nGET /index.html HTTP/1.1\nHost: example.com\n    Accept: text/html\n```", self.text)
        self.assertIn("Заголовок `Host` обязателен", self.text)

    def test_blockquote(self):
        self.assertIn("> Код 418 «I'm a teapot» появился как первоапрельская шутка.", self.text)

    def test_windows_1251_from_meta(self):
        title, text = fixture_text("cp1251.html")
        self.assertEqual("Кодировка Windows-1251", title)
        self.assertIn("Съешь же ещё этих мягких французских булок", text)


class FetchTest(ServerTestCase):
    def test_writes_meta_and_chunks(self):
        code, out, err = run([self.server.url + "/article.html", "--count", "5", "--out", self.out])
        self.assertEqual(0, code, err)
        self.assertIn("meta.json", out)
        meta = self.read_meta()
        self.assertEqual("Протокол HTTP — Тестовая энциклопедия", meta["title"])
        self.assertEqual(self.server.url + "/article.html", meta["url"])
        self.assertFalse(meta["truncated"])
        self.assertEqual(meta["total_chars"], meta["processed_chars"])
        _, text = fixture_text("article.html")
        self.assertEqual(text, "\n\n".join(self.read_chunks(meta)))
        self.assertTrue(self.server.user_agents[0].startswith("quiz-import/1.0"))

    def test_windows_1251_page(self):
        code, _, err = run([self.server.url + "/cp1251.html", "--count", "3", "--out", self.out])
        self.assertEqual(0, code, err)
        self.assertIn("французских булок", "".join(self.read_chunks(self.read_meta())))

    def test_charset_from_content_type(self):
        html = "<p>" + "Ёлка и ёжик. " * 50 + "</p>"
        url = self.server.add("/koi8.html", html.encode("koi8-r"), "text/html; charset=KOI8-R")
        code, _, err = run([url, "--count", "1", "--out", self.out])
        self.assertEqual(0, code, err)
        self.assertIn("Ёлка и ёжик.", self.read_chunks(self.read_meta())[0])

    def test_non_ascii_url(self):
        self.server.add("/wiki/%D0%A2%D0%B5%D1%81%D1%82?q=%D1%8F", "<p>" + "Текст статьи. " * 50 + "</p>")
        code, _, err = run([self.server.url + "/wiki/Тест?q=я", "--count", "1", "--out", self.out])
        self.assertEqual(0, code, err)
        self.assertEqual("http://xn--e1afmkfd.xn--p1ai/wiki/%D0%A2?a=%20b",
                         fetch_page.ascii_url("http://пример.рф/wiki/Т?a=%20b"))

    def test_http_404(self):
        code, _, err = run([self.server.url + "/missing.html", "--count", "5", "--out", self.out])
        self.assertEqual(4, code)
        self.assertIn("404", err)
        self.assertFalse(os.path.exists(os.path.join(self.out, "meta.json")))

    def test_unreachable_host(self):
        code, _, err = run([unused_url(), "--count", "5", "--out", self.out])
        self.assertEqual(4, code)
        self.assertIn("недоступен", err)

    def test_not_html(self):
        url = self.server.add("/doc.pdf", b"%PDF-1.7", "application/pdf")
        code, _, err = run([url, "--count", "5", "--out", self.out])
        self.assertEqual(4, code)
        self.assertIn("не HTML", err)

    def test_spa_without_static_text(self):
        code, _, err = run([self.server.url + "/spa.html", "--count", "5", "--out", self.out])
        self.assertEqual(3, code)
        self.assertIn("запасной путь", err)
        self.assertFalse(os.path.exists(os.path.join(self.out, "meta.json")))

    def test_bad_arguments(self):
        for argv in (["ftp://example.com", "--count", "5", "--out", self.out],
                     [self.server.url + "/article.html", "--count", "0", "--out", self.out],
                     [self.server.url + "/article.html", "--count", "51", "--out", self.out],
                     [self.server.url + "/article.html", "--count", "много", "--out", self.out],
                     [self.server.url + "/article.html", "--out", self.out]):
            with self.subTest(argv=argv):
                code, _, err = run(argv)
                self.assertEqual(1, code)
                self.assertIn("Ошибка", err)
        self.assertEqual([], self.server.user_agents)


class SectionsAndChunksTest(ServerTestCase):
    """Решение 3 design.md: разделы, справочные и короткие разделы, части до 12 000 символов."""

    def test_long_article_split_into_chunks(self):
        sections = [(f"Глава {i}", 18) for i in range(1, 12)] + [("Огромная глава", 60), ("Примечания", 5),
                                                                 ("See also", 2), ("Коротко", 0)]
        html = make_article(sections)
        _, blocks = fetch_page.extract(html)
        text = fetch_page.join_blocks(blocks)
        self.assertGreater(len(text), 130_000)

        code, _, err = run([self.server.add("/long.html", html), "--count", "10", "--out", self.out])
        self.assertEqual(0, code, err)
        meta = self.read_meta()
        chunks = self.read_chunks(meta)
        self.assertGreaterEqual(len(chunks), 11)
        for chunk, info in zip(chunks, meta["chunks"]):
            self.assertLessEqual(len(chunk), 12_000)
            self.assertEqual(len(chunk), info["chars"])
        self.assertEqual(text, "\n\n".join(chunks))
        self.assertNotIn("НАВИГАЦИЯ", text)

        by_title = {s["title"]: s for s in meta["sections"]}
        self.assertEqual(fetch_page.INTRO_TITLE, meta["sections"][0]["title"])
        self.assertGreaterEqual(len(by_title["Огромная глава"]["chunks"]), 3)
        for title in ("Примечания", "See also"):
            self.assertEqual(0, by_title[title]["quota"])
            self.assertEqual("справочный раздел", by_title[title]["skipped_reason"])
        self.assertEqual(0, by_title["Коротко"]["quota"])
        self.assertEqual("короткий раздел", by_title["Коротко"]["skipped_reason"])
        self.assertIsNone(by_title["Глава 11"]["skipped_reason"])

    def test_small_sections_share_chunk_and_paragraphs_not_split(self):
        html = make_article([("Первая", 3), ("Вторая", 3)])
        _, blocks = fetch_page.extract(html)
        meta, chunks = fetch_page.build(html, "http://x", 5)
        self.assertEqual(1, len(chunks))
        self.assertEqual(["s1", "s2", "s3"], meta["chunks"][0]["sections"])
        paragraphs = {b.text for b in blocks}
        for chunk in fetch_page.make_chunks(fetch_page.split_sections(blocks), max_chars=1500):
            for block, _ in chunk:
                self.assertIn(block.text, paragraphs)

    def test_h1_sections_when_no_h2(self):
        html = ("<main><p>" + "Вводный абзац. " * 30 + "</p>"
                "<h1>Первая часть</h1><p>" + "Текст первой части. " * 30 + "</p>"
                "<h1>Вторая часть</h1><p>" + "Текст второй части. " * 30 + "</p></main>")
        meta, _ = fetch_page.build(html, "http://x", 3)
        self.assertEqual(["Введение", "Первая часть", "Вторая часть"], [s["title"] for s in meta["sections"]])
        self.assertEqual([1, 1, 1], [s["quota"] for s in meta["sections"]])


class LimitTest(ServerTestCase):
    def test_page_over_limit_is_truncated(self):
        html = make_article([(f"Глава {i}", 50) for i in range(1, 21)])
        code, _, err = run([self.server.add("/huge.html", html), "--count", "20", "--out", self.out])
        self.assertEqual(0, code, err)
        meta = self.read_meta()
        self.assertGreater(meta["total_chars"], 600_000)
        self.assertTrue(meta["truncated"])
        self.assertLessEqual(meta["processed_chars"], 500_000)
        self.assertGreater(meta["processed_chars"], 490_000)
        chunks = self.read_chunks(meta)
        self.assertEqual(meta["processed_chars"], len("\n\n".join(chunks)))
        self.assertEqual(20, sum(s["quota"] for s in meta["sections"]))

    def test_single_huge_section_is_cut_by_paragraphs(self):
        html = "<main>" + "".join(f"<p>{paragraph(1, j)}</p>" for j in range(1000)) + "</main>"
        meta, chunks = fetch_page.build(html, "http://x", 5)
        self.assertTrue(meta["truncated"])
        self.assertLessEqual(meta["processed_chars"], 500_000)
        self.assertTrue(chunks[-1].endswith("."))


class QuotaTest(unittest.TestCase):
    """Решение 4 design.md и требование «Распределение карточек по разделам»."""

    def test_every_section_gets_card(self):
        html = make_article([("Один", 2), ("Два", 10), ("Три", 4), ("Четыре", 3), ("Пять", 6)], intro=0)
        meta, _ = fetch_page.build(html, "http://x", 10)
        quotas = {s["title"]: s["quota"] for s in meta["sections"] if s["skipped_reason"] is None}
        self.assertEqual(["Один", "Два", "Три", "Четыре", "Пять"], list(quotas))
        self.assertEqual(10, sum(quotas.values()))
        self.assertTrue(all(q >= 1 for q in quotas.values()), quotas)
        self.assertEqual(max(quotas.values()), quotas["Два"])

    def test_fewer_cards_than_sections(self):
        html = make_article([(f"Раздел {i}", 2) for i in range(1, 9)], intro=0)
        meta, _ = fetch_page.build(html, "http://x", 3)
        sections = [s for s in meta["sections"] if s["skipped_reason"] is None]
        chosen = [i for i, s in enumerate(sections) if s["quota"]]
        self.assertEqual(8, len(sections))
        self.assertEqual(3, sum(s["quota"] for s in meta["sections"]))
        self.assertTrue(all(sections[i]["quota"] == 1 for i in chosen))
        self.assertNotEqual([0, 1, 2], chosen)
        self.assertTrue(any(i >= 4 for i in chosen), chosen)

    def test_sum_equals_count(self):
        sizes = [300, 12000, 450, 7000, 900, 3100, 15000, 600, 2500, 800, 330, 5000]
        for n in range(1, len(sizes) + 1):
            for count in range(1, 51):
                with self.subTest(sections=n, count=count):
                    quotas = fetch_page.assign_quotas(sizes[:n], count)
                    self.assertEqual(count, sum(quotas))
                    if count >= n:
                        self.assertTrue(all(q >= 1 for q in quotas))

    def test_skipped_sections_get_no_quota(self):
        html = make_article([("Суть", 4), ("Литература", 3), ("External links", 1)])
        meta, _ = fetch_page.build(html, "http://x", 7)
        quotas = {s["title"]: s["quota"] for s in meta["sections"]}
        self.assertEqual(0, quotas["Литература"])
        self.assertEqual(0, quotas["External links"])
        self.assertEqual(7, quotas["Введение"] + quotas["Суть"])

    def test_only_short_sections_share_cards(self):
        html = "<main>" + "".join(f"<h2>Пункт {i}</h2><p>Короткий текст пункта номер {i}, " + "и ещё. " * 20 + "</p>"
                                  for i in range(1, 6)) + "</main>"
        meta, _ = fetch_page.build(html, "http://x", 5)
        self.assertEqual([1] * 5, [s["quota"] for s in meta["sections"]])
        self.assertTrue(all(s["skipped_reason"] is None for s in meta["sections"]))


if __name__ == "__main__":
    unittest.main()
