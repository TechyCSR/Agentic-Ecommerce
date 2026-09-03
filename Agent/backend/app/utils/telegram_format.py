"""Render the agent's Markdown safely for Telegram.

Telegram's legacy `Markdown` mode is a trap for LLM output: it uses `*bold*`
(not `**bold**`), has no headings, and — worst — *rejects the entire message*
with a 400 when a `*`, `_` or `[` is unbalanced. A single stray underscore in
a product name meant the buyer saw nothing at all.

HTML mode has none of that ambiguity, so this converts to a small, safe HTML
subset: escape everything first, then re-introduce only the tags Telegram
supports.
"""

import html
import re

# Telegram supports only this handful of inline tags.
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
_BOLD_ALT = re.compile(r"__(.+?)__", re.S)
_ITALIC = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", re.S)
_CODE_BLOCK = re.compile(r"```[a-zA-Z]*\n?(.+?)```", re.S)
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*(.+?)\s*#*\s*$", re.M)
_BULLET = re.compile(r"^\s*[-*+]\s+", re.M)
_ORDERED = re.compile(r"^\s*(\d+)\.\s+", re.M)
_HR = re.compile(r"^\s*([-*_])\1{2,}\s*$", re.M)
_BLANKS = re.compile(r"\n{3,}")


def markdown_to_telegram_html(text: str) -> str:
    if not text:
        return ""

    # Escape first so nothing in the source can inject markup.
    out = html.escape(text, quote=False)

    # Code blocks before anything else, so their contents aren't restyled.
    out = _CODE_BLOCK.sub(lambda m: f"<pre>{m.group(1).strip()}</pre>", out)
    out = _INLINE_CODE.sub(lambda m: f"<code>{m.group(1)}</code>", out)

    # Links: the escaping above already neutralised the URL.
    out = _LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', out)

    out = _HEADING.sub(lambda m: f"<b>{m.group(1)}</b>", out)
    out = _BOLD.sub(lambda m: f"<b>{m.group(1)}</b>", out)
    out = _BOLD_ALT.sub(lambda m: f"<b>{m.group(1)}</b>", out)
    out = _ITALIC.sub(lambda m: f"<i>{m.group(1)}</i>", out)

    out = _HR.sub("──────────", out)
    out = _BULLET.sub("• ", out)
    out = _ORDERED.sub(lambda m: f"{m.group(1)}. ", out)

    # Any leftover stray markers would show up literally; tidy the common ones.
    out = out.replace("**", "").replace("* *", "")
    out = _BLANKS.sub("\n\n", out)
    return out.strip()


def plain_text(text: str) -> str:
    """Last-resort rendering with no markup at all — used if Telegram still
    refuses a message, so the buyer always sees the words."""
    if not text:
        return ""
    out = _CODE_BLOCK.sub(lambda m: m.group(1).strip(), text)
    out = _INLINE_CODE.sub(lambda m: m.group(1), out)
    out = _LINK.sub(lambda m: f"{m.group(1)} ({m.group(2)})", out)
    out = _HEADING.sub(lambda m: m.group(1), out)
    out = out.replace("**", "").replace("__", "")
    out = _BULLET.sub("• ", out)
    out = _HR.sub("──────────", out)
    return _BLANKS.sub("\n\n", out).strip()
