#!/usr/bin/env python3
"""Отправка сгенерированных карточек в приложение quiz (используется скилами импорта).

    post_cards.py check [--api URL]       — доступно ли API; код 0 или 2
    post_cards.py post FILE [--api URL]   — отправить карточки из JSON, напечатать JSON-отчёт

Базовый адрес: --api > переменная окружения QUIZ_API_URL > http://localhost:8080.
Только стандартная библиотека Python 3.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_API = "http://localhost:8080"
MAX_LENGTH = 2000
TIMEOUT_SECONDS = 10

EXIT_OK = 0
EXIT_INPUT_ERROR = 1
EXIT_API_UNAVAILABLE = 2


class ApiUnavailable(Exception):
    pass


def base_url(cli_value):
    return (cli_value or os.environ.get("QUIZ_API_URL") or DEFAULT_API).rstrip("/")


def normalize(question):
    return question.strip().casefold()


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


def fetch_existing_questions(api):
    status, cards = request_json("GET", f"{api}/api/cards")
    if status != 200 or not isinstance(cards, list):
        raise ApiUnavailable(f"GET /api/cards вернул {status}")
    return {normalize(card.get("question", "")) for card in cards}


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
    args = parser.parse_args(argv)

    api = base_url(args.api)
    if args.command == "check":
        return check(api)

    try:
        cards = load_cards(args.file)
    except (OSError, ValueError) as e:
        print(f"Не удалось прочитать {args.file}: {e}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        report = post(api, cards)
    except ApiUnavailable as e:
        print(unavailable_message(api, e), file=sys.stderr)
        return EXIT_API_UNAVAILABLE
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
