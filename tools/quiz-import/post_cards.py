#!/usr/bin/env python3
"""Отправка сгенерированных карточек в приложение quiz (используется скилами импорта).

    post_cards.py check [--api URL]       — доступно ли API; код 0 или 2
    post_cards.py post FILE [--api URL]   — отправить карточки из JSON, напечатать JSON-отчёт
    post_cards.py similar FILE [--api URL] — кандидаты в смысловые дубликаты (из приложения и набора)
    post_cards.py lint FILE               — явные признаки карточек без пользы; код 0 или 3

Базовый адрес: --api > переменная окружения QUIZ_API_URL > http://localhost:8080.
Только стандартная библиотека Python 3.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

DEFAULT_API = "http://localhost:8080"
MAX_LENGTH = 2000
TIMEOUT_SECONDS = 10

EXIT_OK = 0
EXIT_INPUT_ERROR = 1
EXIT_API_UNAVAILABLE = 2
EXIT_LINT_FOUND = 3

SIMILAR_THRESHOLD = 0.35
MAX_CANDIDATES = 3
STEM_LENGTH = 5
STOP_WORDS = {
    "и", "в", "во", "на", "с", "со", "к", "ко", "по", "о", "об", "от", "до", "из", "за", "для", "при", "у",
    "не", "ни", "а", "но", "или", "ли", "же", "бы", "то", "как", "так", "что", "чем", "это", "этот", "эта",
    "эти", "его", "ее", "их", "он", "она", "оно", "они", "какой", "какая", "какое", "какие", "каким", "какую",
    "какого", "каких", "где", "когда", "почему", "зачем", "сколько", "ли", "есть", "быть", "если",
    "a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "is", "are", "what", "which", "how",
    "why", "does", "do", "it", "with", "by", "be",
}
YES_NO_ANSWERS = {"да", "нет", "yes", "no"}
SOURCE_REFERENCE = re.compile(
    r"в\s+этом\s+уроке|в\s+уроке|в\s+статье|в\s+тексте|в\s+курсе|в\s+этой\s+главе|\bавтор|"
    r"this\s+article|this\s+lesson", re.I)
INLINE_CODE = re.compile(r"`[^`]*`")
QUESTION_WORD = (r"(?:как\w*|что|чем|зачем|почему|какой|какая|какое|какие|каким|какую|каких|каков\w*|когда|где|куда|"
                 r"откуда|сколько|кто|кого|чего|чём|what|why|how|when|where|which|who)")
COMPOUND_CONJUNCTION = re.compile(
    r"(?:\s|,)(?:и|а\s+также|and)\s+(?:в\s+|для\s+|на\s+|с\s+)?" + QUESTION_WORD + r"\b", re.I)
PAIRED_QUESTION_WORDS = re.compile(r"\b" + QUESTION_WORD + r"\s*$", re.I)


class ApiUnavailable(Exception):
    pass


def base_url(cli_value):
    return (cli_value or os.environ.get("QUIZ_API_URL") or DEFAULT_API).rstrip("/")


def normalize(question):
    return question.strip().casefold()


def stems(text):
    """Множество основ слов: без регистра и служебных слов, кириллица усечена до STEM_LENGTH букв."""
    result = set()
    for word in re.findall(r"\w+", text.casefold().replace("ё", "е")):
        if word in STOP_WORDS or (len(word) == 1 and not word.isdigit()):
            continue
        if re.search(r"[а-я]", word) and len(word) > STEM_LENGTH:
            word = word[:STEM_LENGTH]
        result.add(word)
    return result


def card_stems(card):
    return stems(f"{card.get('question', '')} {card.get('answer', '')}")


def similarity(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def similar(existing, cards):
    """Для каждой карточки набора — до MAX_CANDIDATES похожих из приложения и из предыдущих карточек набора."""
    app = [(card, card_stems(card)) for card in existing if isinstance(card, dict)]
    result = []
    seen = []
    for index, card in enumerate(cards):
        if not isinstance(card, dict):
            continue
        own = card_stems(card)
        found = []
        for other, other_stems in app:
            score = similarity(own, other_stems)
            if score >= SIMILAR_THRESHOLD:
                found.append({"source": "app", "question": other.get("question", ""),
                              "answer": other.get("answer", ""), "score": round(score, 2)})
        for other_index, other, other_stems in seen:
            score = similarity(own, other_stems)
            if score >= SIMILAR_THRESHOLD:
                found.append({"source": "set", "index": other_index, "question": other.get("question", ""),
                              "answer": other.get("answer", ""), "score": round(score, 2)})
        seen.append((index, card, own))
        if found:
            found.sort(key=lambda c: -c["score"])
            result.append({"index": index, "question": card.get("question", ""),
                           "candidates": found[:MAX_CANDIDATES]})
    return result


def is_compound(question):
    """Два вопроса в одном: несколько «?» вне `кода` или союз с новым вопросительным словом."""
    text = INLINE_CODE.sub("", question)
    if text.count("?") > 1:
        return True
    # «Кто и когда …?» — одна мысль: союз соединяет два вопросительных слова подряд
    return any(not PAIRED_QUESTION_WORDS.search(text[:match.start()])
               for match in COMPOUND_CONJUNCTION.finditer(text))


def lint(cards):
    """Явные признаки карточек без пользы: [{"index", "question", "reason"}]."""
    found = []
    for index, card in enumerate(cards):
        if not isinstance(card, dict):
            continue
        question, answer = str(card.get("question", "")), str(card.get("answer", ""))
        reason = None
        if answer.strip().strip(".!").casefold() in YES_NO_ANSWERS:
            reason = "yes_no"
        elif SOURCE_REFERENCE.search(question):
            reason = "source_reference"
        elif is_compound(question):
            reason = "compound_question"
        else:
            answer_stems = stems(answer)
            if answer_stems and answer_stems <= stems(question):
                reason = "answer_in_question"
        if reason:
            found.append({"index": index, "question": question, "reason": reason})
    return found


def request_json(method, url, body=None):
    """Возвращает (статус, разобранный JSON или None). Сетевая ошибка -> ApiUnavailable."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    except (urllib.error.URLError, OSError) as e:
        raise ApiUnavailable(str(getattr(e, "reason", e))) from e
    try:
        return status, json.loads(raw.decode("utf-8")) if raw else None
    except ValueError:
        return status, None


def unavailable_message(api, reason):
    return (f"Приложение quiz недоступно по адресу {api} ({reason}).\n"
            f"Запустите его командой ./gradlew bootRun в корне репозитория "
            f"или укажите адрес через --api / QUIZ_API_URL.")


def fetch_existing_cards(api):
    status, cards = request_json("GET", f"{api}/api/cards")
    if status != 200 or not isinstance(cards, list):
        raise ApiUnavailable(f"GET /api/cards вернул {status}")
    return cards


def fetch_existing_questions(api):
    return {normalize(card.get("question", "")) for card in fetch_existing_cards(api)}


def check(api):
    try:
        fetch_existing_questions(api)
    except ApiUnavailable as e:
        print(unavailable_message(api, e), file=sys.stderr)
        return EXIT_API_UNAVAILABLE
    print(f"Приложение quiz доступно: {api}")
    return EXIT_OK


def validate(card):
    """Сообщение об ошибке или None, если карточку можно отправлять."""
    if not isinstance(card, dict):
        return "карточка должна быть объектом {\"question\", \"answer\"}"
    for field in ("question", "answer"):
        value = card.get(field)
        if not isinstance(value, str) or not value.strip():
            return f"поле {field} отсутствует или пустое"
        if len(value.strip()) > MAX_LENGTH:
            return f"поле {field} длиннее {MAX_LENGTH} символов"
    return None


def post(api, cards):
    """Отправляет новые карточки по одной. Ошибка одной карточки не останавливает остальные."""
    seen = fetch_existing_questions(api)
    report = {"added": [], "skipped": [], "failed": []}
    for card in cards:
        question = card.get("question", "") if isinstance(card, dict) else ""
        error = validate(card)
        if error:
            report["failed"].append({"question": question, "error": error})
            continue
        key = normalize(question)
        if key in seen:
            report["skipped"].append(question.strip())
            continue
        seen.add(key)
        try:
            status, body = request_json("POST", f"{api}/api/cards",
                                        {"question": card["question"], "answer": card["answer"]})
        except ApiUnavailable as e:
            report["failed"].append({"question": question.strip(), "error": f"сеть: {e}"})
            continue
        if status == 201:
            report["added"].append(body["question"] if isinstance(body, dict) else question.strip())
        else:
            message = body.get("error") if isinstance(body, dict) else None
            report["failed"].append({"question": question.strip(), "error": message or f"HTTP {status}"})
    return report


def load_cards(path):
    with open(path, encoding="utf-8") as f:
        cards = json.load(f)
    if not isinstance(cards, list):
        raise ValueError("ожидался JSON-массив карточек [{\"question\": ..., \"answer\": ...}]")
    return cards


def main(argv=None):
    parser = argparse.ArgumentParser(description="Отправка карточек в приложение quiz")
    sub = parser.add_subparsers(dest="command", required=True)
    check_parser = sub.add_parser("check", help="проверить доступность API")
    check_parser.add_argument("--api")
    post_parser = sub.add_parser("post", help="отправить карточки из JSON-файла")
    post_parser.add_argument("file")
    post_parser.add_argument("--api")
    similar_parser = sub.add_parser("similar", help="кандидаты в смысловые дубликаты")
    similar_parser.add_argument("file")
    similar_parser.add_argument("--api")
    lint_parser = sub.add_parser("lint", help="явные признаки карточек без пользы")
    lint_parser.add_argument("file")
    args = parser.parse_args(argv)

    if args.command == "check":
        return check(base_url(args.api))

    try:
        cards = load_cards(args.file)
    except (OSError, ValueError) as e:
        print(f"Не удалось прочитать {args.file}: {e}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    if args.command == "lint":
        found = lint(cards)
        print(json.dumps(found, ensure_ascii=False, indent=2))
        return EXIT_LINT_FOUND if found else EXIT_OK

    api = base_url(args.api)
    try:
        if args.command == "similar":
            print(json.dumps(similar(fetch_existing_cards(api), cards), ensure_ascii=False, indent=2))
            return EXIT_OK
        report = post(api, cards)
    except ApiUnavailable as e:
        print(unavailable_message(api, e), file=sys.stderr)
        return EXIT_API_UNAVAILABLE
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
