#!/usr/bin/env python3
"""Полный основной текст веб-страницы для скила /quiz-from-web-page.

    fetch_page.py URL --count N|auto --out DIR

Загружает HTML, выделяет основное содержимое в Markdown, делит его на крупные
разделы и части до ~12 000 символов, распределяет N карточек по разделам и пишет
в DIR файлы chunk-01.md, chunk-02.md, … и meta.json. С --count auto квоты не
считаются (quota: null): число карточек определяют ключевые положения.

Коды выхода: 0 — готово, 1 — неверные аргументы, 3 — основного текста меньше
500 символов (нужен запасной путь), 4 — HTTP-ошибка или недоступный хост.
Только стандартная библиотека Python 3.
"""

import argparse
import codecs
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

USER_AGENT = "quiz-import/1.0 (flashcards importer; python-urllib)"
TIMEOUT_SECONDS = 30
MAX_BYTES = 20 * 1024 * 1024

MIN_TEXT_CHARS = 500
MAX_TEXT_CHARS = 500_000
MAX_CHUNK_CHARS = 12_000
MIN_SECTION_CHARS = 300
MIN_COUNT, MAX_COUNT = 1, 50
AUTO = "auto"
SEPARATOR = "\n\n"

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NO_TEXT = 3
EXIT_FETCH_ERROR = 4

INTRO_TITLE = "Введение"
REFERENCE_TITLES = {
    "примечания", "литература", "ссылки", "см. также",
    "references", "see also", "external links", "notes", "further reading",
}
SKIP_REFERENCE = "справочный раздел"
SKIP_SHORT = "короткий раздел"

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
             "param", "source", "track", "wbr"}
DROP_TAGS = {"head", "script", "style", "noscript", "template", "svg", "iframe", "form", "button",
             "nav", "header", "footer", "aside"}
DROP_ROLES = {"navigation", "banner", "contentinfo", "search"}
DROP_WORDS = {"nav", "menu", "footer", "sidebar", "cookie", "comments", "breadcrumb", "toc",
              "mw-editsection", "reference"}
HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
BLOCK_TAGS = {"address", "article", "blockquote", "body", "caption", "center", "dd", "details",
              "dialog", "div", "dl", "dt", "fieldset", "figcaption", "figure", "hgroup", "hr",
              "html", "li", "main", "ol", "p", "pre", "section", "summary", "table", "ul",
              *HEADINGS, *DROP_TAGS}
# Открытие этих тегов неявно закрывает открытый <p>, как в браузере.
CLOSES_P = BLOCK_TAGS - {"body", "html", "li", "dd", "dt", "caption"}


class UsageError(Exception):
    pass


class FetchError(Exception):
    pass


# ---------- Загрузка ----------

def detect_charset(raw, content_type):
    candidates = []
    match = re.search(r"charset=[\"']?([\w.:-]+)", content_type or "", re.I)
    if match:
        candidates.append(match.group(1))
    head = raw[:4096].decode("ascii", "replace")
    match = re.search(r"<meta[^>]+charset=[\"']?([\w.:-]+)", head, re.I)
    if match:
        candidates.append(match.group(1))
    for name in candidates:
        try:
            return codecs.lookup(name).name
        except LookupError:
            continue
    return "utf-8"


def ascii_url(url):
    """Кириллица в пути и запросе -> %XX, домен -> punycode; уже закодированное не трогается."""
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ""
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        pass
    netloc = host if parts.port is None else f"{host}:{parts.port}"
    safe = "/%:@!$&'()*+,;=-._~?"
    return urllib.parse.urlunsplit((parts.scheme, netloc,
                                    urllib.parse.quote(parts.path, safe=safe),
                                    urllib.parse.quote(parts.query, safe=safe),
                                    urllib.parse.quote(parts.fragment, safe=safe)))


def fetch(url):
    """Возвращает HTML страницы строкой. Любая ошибка загрузки -> FetchError."""
    request = urllib.request.Request(ascii_url(url), headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            content_type = response.headers.get("Content-Type", "")
            raw = response.read(MAX_BYTES)
    except urllib.error.HTTPError as e:
        raise FetchError(f"HTTP {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise FetchError(f"сайт недоступен: {e.reason}") from e
    except (OSError, ValueError) as e:
        raise FetchError(f"не удалось загрузить страницу: {e}") from e
    if content_type and "html" not in content_type.lower():
        raise FetchError(f"страница не HTML (Content-Type: {content_type})")
    return raw.decode(detect_charset(raw, content_type), errors="replace")


# ---------- Разбор HTML в дерево ----------

class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = attrs
        self.children = []
        self.parent = parent

    def iter(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.iter()


class TreeBuilder(HTMLParser):
    """Терпимый к ошибкам разбор: незакрытые <p>, <li>, <td> закрываются, как в браузере."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {}, None)
        self.stack = [self.root]

    def _close_nearest(self, tags, stop):
        for i in range(len(self.stack) - 1, 0, -1):
            tag = self.stack[i].tag
            if tag in tags:
                del self.stack[i:]
                return
            if tag in stop:
                return

    def _implicit_close(self, tag):
        if tag in CLOSES_P:
            self._close_nearest({"p"}, {"table", "td", "th", "caption", "body", "html", "template"})
        if tag == "li":
            self._close_nearest({"li"}, {"ul", "ol", "menu", "table"})
        elif tag in ("dt", "dd"):
            self._close_nearest({"dt", "dd"}, {"dl", "table"})
        elif tag in ("td", "th"):
            self._close_nearest({"td", "th"}, {"tr", "table"})
        elif tag == "tr":
            self._close_nearest({"tr"}, {"table"})
        elif tag in ("thead", "tbody", "tfoot"):
            self._close_nearest({"thead", "tbody", "tfoot"}, {"table"})

    def _add(self, tag, attrs):
        self._implicit_close(tag)
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)
        return node

    def handle_starttag(self, tag, attrs):
        node = self._add(tag, attrs)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._add(tag, attrs)

    def handle_endtag(self, tag):
        self._close_nearest({tag}, ())

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(html):
    builder = TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


# ---------- Выделение основного текста ----------

def class_words(attrs):
    words = set()
    for token in f"{attrs.get('class', '')} {attrs.get('id', '')}".lower().split():
        words.add(token)
        words.update(w for w in re.split(r"[-_]", token) if w)
    return words


def is_dropped(node):
    if node.tag in DROP_TAGS:
        return True
    attrs = node.attrs
    if attrs.get("role", "").strip().lower() in DROP_ROLES:
        return True
    if "hidden" in attrs or attrs.get("aria-hidden", "").strip().lower() == "true":
        return True
    return bool(class_words(attrs) & DROP_WORDS)


def collapse(text):
    return re.sub(r"\s+", " ", text).strip()


def plain_text(node, keep_breaks=False):
    """Текст поддерева без выброшенных элементов; keep_breaks — сохранять пробелы (для <pre>)."""
    parts = []

    def walk(n):
        for child in n.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag == "br":
                parts.append("\n" if keep_breaks else " ")
            elif not is_dropped(child):
                if not keep_breaks and child.tag in BLOCK_TAGS:
                    parts.append(" ")
                walk(child)
                if not keep_breaks and child.tag in BLOCK_TAGS:
                    parts.append(" ")

    walk(node)
    text = "".join(parts)
    return text if keep_breaks else collapse(text)


def find_root(document):
    nodes = list(document.iter())
    for node in nodes:
        if node.tag == "main":
            return node
    articles = [n for n in nodes if n.tag == "article"]
    if articles:
        return max(articles, key=lambda n: len(plain_text(n)))
    for node in nodes:
        if node.tag == "body":
            return node
    return document


class Block:
    """Блок Markdown: абзац, заголовок, список, таблица, код или цитата."""
    __slots__ = ("text", "level", "title")

    def __init__(self, text, level=0, title=None):
        self.text = text
        self.level = level
        self.title = title


class Renderer:
    def __init__(self):
        self.blocks = []
        self.inline = []

    def flush(self):
        text = collapse("".join(self.inline))
        self.inline = []
        if text:
            self.blocks.append(Block(text))

    def render(self, node):
        for child in node.children:
            if isinstance(child, str):
                self.inline.append(child)
                continue
            tag = child.tag
            if is_dropped(child):
                continue
            if tag in HEADINGS:
                self.flush()
                title = plain_text(child)
                if title:
                    level = HEADINGS[tag]
                    self.blocks.append(Block(f"{'#' * level} {title}", level, title))
            elif tag == "pre":
                self.flush()
                code = plain_text(child, keep_breaks=True).strip("\n")
                if code.strip():
                    self.blocks.append(Block(f"```\n{code}\n```"))
            elif tag in ("ul", "ol"):
                self.flush()
                lines = list_lines(child, 0)
                if lines:
                    self.blocks.append(Block("\n".join(lines)))
            elif tag == "table":
                self.flush()
                lines = table_lines(child)
                if lines:
                    self.blocks.append(Block("\n".join(lines)))
            elif tag == "blockquote":
                self.flush()
                inner = Renderer()
                inner.render(child)
                inner.flush()
                for block in inner.blocks:
                    self.blocks.append(Block("\n".join("> " + line for line in block.text.split("\n"))))
            elif tag == "br":
                self.inline.append(" ")
            elif tag == "code":
                code = plain_text(child)
                if code:
                    self.inline.append(f"`{code}`")
            elif tag in BLOCK_TAGS:
                self.flush()
                self.render(child)
                self.flush()
            else:
                self.render(child)


def list_lines(list_node, depth):
    lines = []
    ordered = list_node.tag == "ol"
    number = 0
    for item in list_node.children:
        if not isinstance(item, Node) or item.tag != "li" or is_dropped(item):
            continue
        number += 1
        parts, nested = [], []

        def walk(n):
            for child in n.children:
                if isinstance(child, str):
                    parts.append(child)
                elif child.tag in ("ul", "ol"):
                    if not is_dropped(child):
                        nested.extend(list_lines(child, depth + 1))
                elif child.tag == "br":
                    parts.append(" ")
                elif not is_dropped(child):
                    parts.append(" ")
                    walk(child)
                    parts.append(" ")

        walk(item)
        text = collapse("".join(parts))
        if text:
            marker = f"{number}." if ordered else "-"
            lines.append(f"{'  ' * depth}{marker} {text}")
        lines.extend(nested)
    return lines


def table_lines(table):
    lines = []

    def walk(n):
        for child in n.children:
            if not isinstance(child, Node) or is_dropped(child):
                continue
            if child.tag == "caption":
                caption = plain_text(child)
                if caption:
                    lines.append(caption)
            elif child.tag == "tr":
                cells = [plain_text(c) for c in child.children
                         if isinstance(c, Node) and c.tag in ("td", "th") and not is_dropped(c)]
                if any(cells):
                    lines.append(" | ".join(cells))
            elif child.tag in ("thead", "tbody", "tfoot"):
                walk(child)

    walk(table)
    return lines


def extract(html):
    """HTML -> (заголовок страницы, список блоков Markdown основного текста)."""
    document = parse_html(html)
    title = ""
    for node in document.iter():
        if node.tag == "title":
            title = collapse("".join(c for c in node.children if isinstance(c, str)))
            break
    renderer = Renderer()
    renderer.render(find_root(document))
    renderer.flush()
    if not title:
        title = next((b.title for b in renderer.blocks if b.level == 1), "")
    return title, renderer.blocks


def join_blocks(blocks):
    return SEPARATOR.join(b.text for b in blocks)


# ---------- Разделы, лимит, части, квоты ----------

class Section:
    __slots__ = ("title", "blocks")

    def __init__(self, title, blocks):
        self.title = title
        self.blocks = blocks

    @property
    def chars(self):
        return len(join_blocks(self.blocks))


def split_sections(blocks):
    """Крупный раздел — от <h2> до <h2>; без <h2> — по <h1>; текст до первого заголовка — «Введение»."""
    levels = {b.level for b in blocks if b.level}
    split_level = 2 if 2 in levels else 1 if 1 in levels else None
    sections = []
    current = Section(INTRO_TITLE, [])
    for block in blocks:
        if split_level and block.level == split_level:
            if current.blocks:
                sections.append(current)
            current = Section(block.title, [block])
        else:
            current.blocks.append(block)
    if current.blocks:
        sections.append(current)
    return sections


def apply_limit(sections, limit=MAX_TEXT_CHARS):
    """Оставляет начало текста не длиннее limit: целые разделы, а последний — по целым блокам."""
    kept, used = [], 0
    for section in sections:
        sep = len(SEPARATOR) if kept else 0
        if used + sep + section.chars <= limit:
            kept.append(section)
            used += sep + section.chars
            continue
        part = []
        for block in section.blocks:
            add = len(block.text) + (len(SEPARATOR) if kept or part else 0)
            if used + add > limit:
                break
            part.append(block)
            used += add
        if part:
            kept.append(Section(section.title, part))
        break
    return kept


def skipped_reason(section):
    title = section.title.strip().rstrip(":").strip().casefold()
    if title in REFERENCE_TITLES:
        return SKIP_REFERENCE
    if section.chars < MIN_SECTION_CHARS:
        return SKIP_SHORT
    return None


def make_chunks(sections, max_chars=MAX_CHUNK_CHARS):
    """Упаковывает разделы в части; раздел целиком переносится в новую часть, если там помещается.
    Возвращает список частей, каждая — список пар (блок, индекс раздела)."""
    chunks, current, length = [], [], 0

    def new_chunk():
        nonlocal current, length
        if current:
            chunks.append(current)
        current, length = [], 0

    for index, section in enumerate(sections):
        if current and length + len(SEPARATOR) + section.chars > max_chars and section.chars <= max_chars:
            new_chunk()
        for block in section.blocks:
            add = len(block.text) + (len(SEPARATOR) if current else 0)
            if current and length + add > max_chars:
                new_chunk()
                add = len(block.text)
            current.append((block, index))
            length += add
    new_chunk()
    return chunks


def largest_remainder(total, weights):
    weight_sum = sum(weights)
    if total <= 0 or weight_sum <= 0:
        return [0] * len(weights)
    exact = [total * w / weight_sum for w in weights]
    result = [int(x) for x in exact]
    order = sorted(range(len(weights)), key=lambda i: (-(exact[i] - result[i]), i))
    for i in order[:total - sum(result)]:
        result[i] += 1
    return result


def assign_quotas(chars, count):
    """Квоты по решению 4 design.md: chars — объёмы осмысленных разделов, сумма квот = count."""
    n = len(chars)
    if n == 0:
        return []
    if count >= n:
        extra = largest_remainder(count - n, chars)
        return [1 + e for e in extra]
    quotas = [0] * n
    for i in range(count):
        quotas[int(i * n / count + 0.5)] = 1
    return quotas


def build(html, url, count):
    """Возвращает (meta, тексты частей); при тексте короче MIN_TEXT_CHARS — (None, None)."""
    title, blocks = extract(html)
    total_chars = len(join_blocks(blocks))
    if total_chars < MIN_TEXT_CHARS:
        return None, None
    sections = apply_limit(split_sections(blocks))
    processed_chars = len(SEPARATOR.join(join_blocks(s.blocks) for s in sections))

    reasons = [skipped_reason(s) for s in sections]
    meaningful = [i for i, r in enumerate(reasons) if r is None]
    if not meaningful:
        # Все разделы короткие: делим карточки между всеми, кроме справочных.
        meaningful = [i for i, r in enumerate(reasons) if r != SKIP_REFERENCE] or list(range(len(sections)))
        for i in meaningful:
            reasons[i] = None
    if count is None:
        quotas = [None] * len(sections)  # автоматический режим: число карточек задают ключевые положения
    else:
        quotas = [0] * len(sections)
        for i, q in zip(meaningful, assign_quotas([sections[i].chars for i in meaningful], count)):
            quotas[i] = q

    chunks = make_chunks(sections)
    section_chunks = [[] for _ in sections]
    chunk_meta, chunk_texts = [], []
    for number, chunk in enumerate(chunks, 1):
        text = join_blocks(b for b, _ in chunk)
        ids = []
        for _, index in chunk:
            if number not in section_chunks[index]:
                section_chunks[index].append(number)
            if f"s{index + 1}" not in ids:
                ids.append(f"s{index + 1}")
        chunk_texts.append(text)
        chunk_meta.append({"file": f"chunk-{number:02d}.md", "chars": len(text), "sections": ids})

    meta = {
        "url": url,
        "title": title,
        "count": AUTO if count is None else count,
        "total_chars": total_chars,
        "processed_chars": processed_chars,
        "truncated": processed_chars < total_chars,
        "sections": [
            {"id": f"s{i + 1}", "title": s.title, "chars": s.chars, "chunks": section_chunks[i],
             "quota": quotas[i], "skipped_reason": reasons[i]}
            for i, s in enumerate(sections)
        ],
        "chunks": chunk_meta,
    }
    return meta, chunk_texts


def write_output(out_dir, meta, chunk_texts):
    os.makedirs(out_dir, exist_ok=True)
    for info, text in zip(meta["chunks"], chunk_texts):
        with open(os.path.join(out_dir, info["file"]), "w", encoding="utf-8") as f:
            f.write(text + "\n")
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ---------- CLI ----------

def parse_count(value):
    if value == AUTO:
        return None
    try:
        count = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"количество должно быть целым числом или {AUTO}, получено «{value}»")
    if not MIN_COUNT <= count <= MAX_COUNT:
        raise argparse.ArgumentTypeError(f"количество должно быть от {MIN_COUNT} до {MAX_COUNT}, получено {count}")
    return count


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def main(argv=None):
    parser = ArgumentParser(prog="fetch_page.py", description="Полный текст страницы по частям для импорта карточек.")
    parser.add_argument("url")
    parser.add_argument("--count", required=True, type=parse_count, help=f"количество карточек, {MIN_COUNT}–{MAX_COUNT}, или {AUTO} — без квот")
    parser.add_argument("--out", required=True, help="каталог для chunk-XX.md и meta.json")
    try:
        args = parser.parse_args(argv)
        if not re.match(r"https?://", args.url, re.I):
            raise UsageError(f"адрес должен начинаться с http:// или https://: {args.url}")
    except UsageError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return EXIT_USAGE

    try:
        html = fetch(args.url)
    except FetchError as e:
        print(f"Не удалось загрузить {args.url}: {e}", file=sys.stderr)
        return EXIT_FETCH_ERROR

    meta, chunk_texts = build(html, args.url, args.count)
    if meta is None:
        print(f"На странице меньше {MIN_TEXT_CHARS} символов статического текста "
              f"(вероятно, она собирается JavaScript) — нужен запасной путь.", file=sys.stderr)
        return EXIT_NO_TEXT

    write_output(args.out, meta, chunk_texts)
    print(f"Готово: {meta['processed_chars']} из {meta['total_chars']} символов, "
          f"разделов {len(meta['sections'])}, частей {len(meta['chunks'])} → "
          f"{os.path.join(args.out, 'meta.json')}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
