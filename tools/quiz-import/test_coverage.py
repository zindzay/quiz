"""Тесты coverage.py.

Запуск: python3 -m unittest discover tools/quiz-import
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import coverage  # noqa: E402


def card(n):
    return {"question": f"Вопрос {n}?", "answer": f"Ответ {n}."}


def point(pid, card_index, text=None):
    return {"id": pid, "text": text or f"Положение {pid}", "card": card_index}


class CoverageTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def run_cli(self, command, sections, cards, raw_coverage=None):
        cov_path = os.path.join(self.dir, "coverage.json")
        cards_path = os.path.join(self.dir, "cards.json")
        with open(cov_path, "w", encoding="utf-8") as f:
            f.write(raw_coverage if raw_coverage is not None else json.dumps({"sections": sections}, ensure_ascii=False))
        with open(cards_path, "w", encoding="utf-8") as f:
            json.dump(cards, f, ensure_ascii=False)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = coverage.main([command, cov_path, cards_path])
        return code, out.getvalue(), err.getvalue()

    def full(self):
        sections = [
            {"id": "s1", "title": "Введение", "points": [point("s1-p1", 0), point("s1-p2", 1)]},
            {"id": "s2", "title": "Коды состояния", "points": [point("s2-p1", 2), point("s2-p2", 2)]},
            {"id": "s3", "title": "Примечания", "skipped_reason": "справочный раздел", "points": []},
        ]
        return sections, [card(0), card(1), card(2)]

    def test_full_coverage(self):
        code, out, _ = self.run_cli("check", *self.full())
        self.assertEqual(0, code)
        self.assertIn("Всё покрыто", out)

    def test_uncovered_point(self):
        sections, cards = self.full()
        sections[1]["points"].append(point("s2-p3", None, "Класс 4xx — ошибки клиента"))
        code, out, _ = self.run_cli("check", sections, cards)
        self.assertEqual(3, code)
        found = json.loads(out)
        self.assertEqual([{"id": "s2-p3", "section": "s2", "text": "Класс 4xx — ошибки клиента"}], found["uncovered"])

    def test_card_without_point(self):
        sections, cards = self.full()
        cards.append(card(3))
        code, out, _ = self.run_cli("check", sections, cards)
        self.assertEqual(3, code)
        self.assertEqual([3], json.loads(out)["unlinked_cards"])

    def test_section_without_cards(self):
        sections, cards = self.full()
        sections.append({"id": "s4", "title": "Безопасность", "points": [point("s4-p1", None)]})
        code, out, _ = self.run_cli("check", sections, cards)
        self.assertEqual(3, code)
        self.assertEqual(["s4"], json.loads(out)["empty_sections"])

    def test_section_without_points_and_reason(self):
        sections, cards = self.full()
        sections.append({"id": "s4", "title": "История", "points": []})
        code, out, _ = self.run_cli("check", sections, cards)
        self.assertEqual(3, code)
        self.assertEqual(["s4"], json.loads(out)["sections_without_points"])

    def test_card_index_out_of_range(self):
        sections, cards = self.full()
        sections[0]["points"][0]["card"] = 5
        code, _, err = self.run_cli("check", sections, cards)
        self.assertEqual(1, code)
        self.assertIn("индексом 5", err)

    def test_format_errors(self):
        sections, cards = self.full()
        broken = [
            ("not json", None),
            (None, {"id": "s1", "title": "X", "points": [{"id": "s1-p1", "text": "t", "card": "0"}]}),
            (None, {"id": "s1", "title": "X", "points": [{"id": "s1-p1", "text": "", "card": 0}]}),
            (None, {"title": "без id", "points": []}),
        ]
        for raw, section in broken:
            with self.subTest(raw=raw, section=section):
                code, _, err = self.run_cli("check", [section] if section else sections, cards, raw_coverage=raw)
                self.assertEqual(1, code)
                self.assertIn("Ошибка", err)

    def test_duplicate_point_ids(self):
        sections, cards = self.full()
        sections[1]["points"][0]["id"] = "s1-p1"
        code, _, err = self.run_cli("check", sections, cards)
        self.assertEqual(1, code)
        self.assertIn("повторяющийся id s1-p1", err)

    def test_report(self):
        sections, cards = self.full()
        sections[1]["points"].append(point("s2-p3", None))
        code, out, _ = self.run_cli("report", sections, cards)
        self.assertEqual(0, code)
        lines = out.splitlines()
        self.assertEqual("ключевых положений: 5, покрыто: 4", lines[0])
        self.assertIn("карточек: 3", lines)
        self.assertIn("Введение | 2 | 2", lines)
        self.assertIn("Коды состояния | 3 | 1", lines)
        self.assertIn("Примечания | — | пропущен: справочный раздел", lines)


    def existing_point(self, pid):
        return {"id": pid, "text": f"Положение {pid}", "card": None, "existing": f"Вопрос из приложения {pid}?"}

    def test_existing_point_is_covered(self):
        sections, cards = self.full()
        sections[0]["points"].append(self.existing_point("s1-p3"))
        code, out, _ = self.run_cli("check", sections, cards)
        self.assertEqual(0, code, out)

    def test_section_only_with_existing_is_not_empty(self):
        sections, cards = self.full()
        sections.append({"id": "s4", "title": "Повтор", "points": [self.existing_point("s4-p1")]})
        code, out, _ = self.run_cli("check", sections, cards)
        self.assertEqual(0, code, out)

    def test_card_and_existing_together_is_format_error(self):
        sections, cards = self.full()
        sections[0]["points"][0]["existing"] = "Вопрос из приложения?"
        code, _, err = self.run_cli("check", sections, cards)
        self.assertEqual(1, code)
        self.assertIn("не оба", err)
        sections[0]["points"][0] = {"id": "s1-p1", "text": "т", "card": None, "existing": " "}
        code, _, err = self.run_cli("check", sections, cards)
        self.assertEqual(1, code)
        self.assertIn("existing", err)

    def test_report_with_points_already_in_app(self):
        points = [point(f"s1-p{i}", i) for i in range(8)] + [self.existing_point(f"s1-p{i}") for i in range(8, 12)]
        sections = [{"id": "s1", "title": "Введение", "points": points}]
        cards = [card(i) for i in range(8)]
        self.assertEqual(0, self.run_cli("check", sections, cards)[0])
        code, out, _ = self.run_cli("report", sections, cards)
        self.assertEqual(0, code)
        lines = out.splitlines()
        self.assertEqual("ключевых положений: 12, покрыто: 12", lines[0])
        self.assertEqual("из них существующими карточками: 4", lines[1])
        self.assertIn("карточек: 8", lines)
        self.assertIn("раздел | положений | карточек | уже были", lines)
        self.assertIn("Введение | 12 | 8 | 4", lines)


if __name__ == "__main__":
    unittest.main()
