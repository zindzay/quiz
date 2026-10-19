#!/usr/bin/env python3
"""Сверка покрытия ключевых положений карточками (автоматический режим скилов импорта).

    coverage.py check COVERAGE CARDS    — всё ли покрыто; код 0, 3 (есть пробелы) или 1
    coverage.py report COVERAGE CARDS   — «ключевых положений: X, покрыто: Y» и разбивка по разделам

COVERAGE — coverage.json (формат — tools/quiz-import/card-rules.md, «Полный охват»),
CARDS — JSON-массив карточек [{"question", "answer"}]. Положение с existing (вопрос карточки,
уже существующей в приложении) вместо card покрыто без новой карточки.
Только стандартная библиотека Python 3.
"""

import argparse
import json
import sys

EXIT_OK = 0
EXIT_FORMAT_ERROR = 1
EXIT_GAPS = 3


class FormatError(Exception):
    pass


def load_json(path, what):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise FormatError(f"не удалось прочитать {what} {path}: {e.strerror}") from e
    except ValueError as e:
        raise FormatError(f"{what} {path} — не JSON: {e}") from e


def load(coverage_path, cards_path):
    """Проверяет формат обоих файлов и возвращает (разделы, число карточек)."""
    coverage = load_json(coverage_path, "файл покрытия")
    cards = load_json(cards_path, "файл карточек")
    if not isinstance(cards, list):
        raise FormatError("файл карточек должен содержать JSON-массив")
    if not isinstance(coverage, dict) or not isinstance(coverage.get("sections"), list):
        raise FormatError("в файле покрытия нет списка sections")

    seen = set()
    for i, section in enumerate(coverage["sections"]):
        where = f"sections[{i}]"
        if not isinstance(section, dict) or not isinstance(section.get("id"), str) or not section["id"]:
            raise FormatError(f"{where}: нужен непустой строковый id")
        if not isinstance(section.get("title"), str):
            raise FormatError(f"{where} ({section['id']}): нужен строковый title")
        points = section.get("points", [])
        if not isinstance(points, list):
            raise FormatError(f"{where} ({section['id']}): points должен быть списком")
        section["points"] = points
        for j, point in enumerate(points):
            pwhere = f"{where}.points[{j}]"
            if not isinstance(point, dict) or not isinstance(point.get("id"), str) or not point["id"]:
                raise FormatError(f"{pwhere}: нужен непустой строковый id")
            if point["id"] in seen:
                raise FormatError(f"{pwhere}: повторяющийся id {point['id']}")
            seen.add(point["id"])
            if not isinstance(point.get("text"), str) or not point["text"].strip():
                raise FormatError(f"{pwhere} ({point['id']}): нужен непустой text")
            card = point.get("card")
            existing = point.get("existing")
            if existing is not None:
                if not isinstance(existing, str) or not existing.strip():
                    raise FormatError(f"{pwhere} ({point['id']}): existing должен быть непустой строкой")
                if card is not None:
                    raise FormatError(f"{pwhere} ({point['id']}): нужен card или existing, а не оба")
            if card is not None:
                if isinstance(card, bool) or not isinstance(card, int):
                    raise FormatError(f"{pwhere} ({point['id']}): card должен быть целым индексом или null")
                if not 0 <= card < len(cards):
                    raise FormatError(f"{pwhere} ({point['id']}): карточки с индексом {card} нет "
                                      f"(в наборе {len(cards)})")
    return coverage["sections"], len(cards)


def gaps(sections, card_count):
    linked = set()
    uncovered, empty_sections, without_points = [], [], []
    for section in sections:
        if not section["points"]:
            if not section.get("skipped_reason"):
                without_points.append(section["id"])
            continue
        section_cards = set()
        for point in section["points"]:
            if point.get("card") is not None:
                section_cards.add(point["card"])
            elif point.get("existing") is None:
                uncovered.append({"id": point["id"], "section": section["id"], "text": point["text"]})
        linked |= section_cards
        if not section_cards and not all(p.get("existing") is not None for p in section["points"]):
            empty_sections.append(section["id"])
    unlinked = [i for i in range(card_count) if i not in linked]
    return {
        "uncovered": uncovered,
        "unlinked_cards": unlinked,
        "empty_sections": empty_sections,
        "sections_without_points": without_points,
    }


def command_check(sections, card_count):
    found = gaps(sections, card_count)
    if any(found.values()):
        print(json.dumps(found, ensure_ascii=False, indent=2))
        return EXIT_GAPS
    total = sum(len(s["points"]) for s in sections)
    print(f"Всё покрыто: ключевых положений {total}, карточек {card_count}.")
    return EXIT_OK


def command_report(sections, card_count):
    total = sum(len(s["points"]) for s in sections)
    existing = sum(1 for s in sections for p in s["points"] if p.get("existing") is not None)
    covered = existing + sum(1 for s in sections for p in s["points"] if p.get("card") is not None)
    print(f"ключевых положений: {total}, покрыто: {covered}")
    if existing:
        print(f"из них существующими карточками: {existing}")
    print(f"карточек: {card_count}")
    print()
    print("раздел | положений | карточек" + (" | уже были" if existing else ""))
    for section in sections:
        if not section["points"] and section.get("skipped_reason"):
            print(f"{section['title']} | — | пропущен: {section['skipped_reason']}")
            continue
        cards = {p["card"] for p in section["points"] if p.get("card") is not None}
        line = f"{section['title']} | {len(section['points'])} | {len(cards)}"
        if existing:
            line += f" | {sum(1 for p in section['points'] if p.get('existing') is not None)}"
        print(line)
    return EXIT_OK


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise FormatError(message)


def main(argv=None):
    parser = ArgumentParser(prog="coverage.py", description="Сверка покрытия ключевых положений карточками.")
    parser.add_argument("command", choices=["check", "report"])
    parser.add_argument("coverage")
    parser.add_argument("cards")
    try:
        args = parser.parse_args(argv)
        sections, card_count = load(args.coverage, args.cards)
    except FormatError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return EXIT_FORMAT_ERROR
    if args.command == "check":
        return command_check(sections, card_count)
    return command_report(sections, card_count)


if __name__ == "__main__":
    sys.exit(main())
