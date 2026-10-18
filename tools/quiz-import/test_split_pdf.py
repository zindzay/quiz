"""Тесты split_pdf.swift: запуск скрипта на PDF-фикстурах из fixtures/.

Запуск: python3 -m unittest discover tools/quiz-import (нужен swift — macOS с Command Line Tools).
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "split_pdf.swift")
FIXTURES = os.path.join(HERE, "fixtures")
GENERATOR = os.path.join(FIXTURES, "make_pdfs.swift")


def fixture(name):
    return os.path.join(FIXTURES, name)


@unittest.skipUnless(shutil.which("swift"), "нужен swift (macOS Command Line Tools)")
class SplitPdfTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.big = os.path.join(cls.tmp, "big.pdf")
        subprocess.run(["swift", GENERATOR, "large", cls.big, "150"], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def split(self, path, count, pages=None):
        out = tempfile.mkdtemp(dir=self.tmp)
        argv = ["swift", SCRIPT, path, "--count", str(count), "--out", out]
        if pages:
            argv += ["--pages", pages]
        result = subprocess.run(argv, capture_output=True, text=True)
        meta = None
        if result.returncode == 0:
            with open(os.path.join(out, "meta.json"), encoding="utf-8") as f:
                meta = json.load(f)
        return result, meta, out

    def page_count(self, path):
        """Число страниц части — через сам скрипт (каждая часть — самостоятельный PDF)."""
        _, meta, _ = self.split(path, 1)
        return meta["pages"]

    def test_fixture_page_counts(self):
        for name, pages in (("short.pdf", 3), ("sections.pdf", 40), ("scanned.pdf", 2), ("blank.pdf", 3)):
            with self.subTest(name=name):
                result, meta, _ = self.split(fixture(name), 5)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(pages, meta["pages"])
                self.assertEqual({"from": 1, "to": pages}, meta["range"])

    def test_whole_document_in_parts_of_ten(self):
        result, meta, out = self.split(fixture("sections.pdf"), 10)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([(1, 10), (11, 20), (21, 30), (31, 40)], [(p["from"], p["to"]) for p in meta["parts"]])
        self.assertEqual(["part-01.pdf", "part-02.pdf", "part-03.pdf", "part-04.pdf"], [p["file"] for p in meta["parts"]])
        for part in meta["parts"]:
            self.assertEqual(10, self.page_count(os.path.join(out, part["file"])))
        self.assertEqual(10, sum(p["quota"] for p in meta["parts"]))
        self.assertTrue(all(p["quota"] >= 1 for p in meta["parts"]))

    def test_range(self):
        result, meta, out = self.split(fixture("sections.pdf"), 6, pages="3-5")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"from": 3, "to": 5}, meta["range"])
        self.assertEqual([{"file": "part-01.pdf", "from": 3, "to": 5, "quota": 6}], meta["parts"])
        self.assertEqual(3, self.page_count(os.path.join(out, "part-01.pdf")))

    def test_single_page_range(self):
        result, meta, _ = self.split(fixture("sections.pdf"), 2, pages="7")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([(7, 7)], [(p["from"], p["to"]) for p in meta["parts"]])

    def test_quota_sum_and_uneven_parts(self):
        result, meta, _ = self.split(fixture("sections.pdf"), 7, pages="1-25")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([3, 2, 2], [p["quota"] for p in meta["parts"]])

    def test_fewer_cards_than_parts(self):
        result, meta, _ = self.split(fixture("sections.pdf"), 3)
        self.assertEqual(0, result.returncode, result.stderr)
        quotas = [p["quota"] for p in meta["parts"]]
        self.assertEqual(3, sum(quotas))
        self.assertEqual(3, quotas.count(1))
        self.assertEqual(1, quotas[-1], "последняя часть документа тоже представлена")

    def test_range_outside_document(self):
        result, _, _ = self.split(fixture("short.pdf"), 5, pages="10-20")
        self.assertEqual(1, result.returncode)
        self.assertIn("3 стр.", result.stderr)

    def test_bad_arguments(self):
        for count, pages in ((0, None), (51, None), ("много", None), (5, "5-3"), (5, "0-2"), (5, "a-b")):
            with self.subTest(count=count, pages=pages):
                result, _, _ = self.split(fixture("short.pdf"), count, pages=pages)
                self.assertEqual(1, result.returncode)
                self.assertIn("Ошибка", result.stderr)

    def test_missing_file(self):
        result, _, _ = self.split(os.path.join(self.tmp, "нет.pdf"), 5)
        self.assertEqual(1, result.returncode)
        self.assertIn("не найден", result.stderr)

    def test_not_pdf(self):
        path = os.path.join(self.tmp, "notes.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("просто текст")
        result, _, _ = self.split(path, 5)
        self.assertEqual(3, result.returncode)
        self.assertIn("не PDF", result.stderr)

    def test_protected(self):
        result, _, out = self.split(fixture("protected.pdf"), 5)
        self.assertEqual(4, result.returncode)
        self.assertIn("паролем", result.stderr)
        self.assertEqual([], os.listdir(out))

    def test_large_document_without_range(self):
        result, _, out = self.split(self.big, 10)
        self.assertEqual(5, result.returncode)
        self.assertIn("150 стр.", result.stderr)
        self.assertEqual([], os.listdir(out))

    def test_large_document_with_range(self):
        result, meta, _ = self.split(self.big, 10, pages="101-150")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(150, meta["pages"])
        self.assertEqual(5, len(meta["parts"]))
        self.assertEqual(101, meta["parts"][0]["from"])


if __name__ == "__main__":
    unittest.main()
