"""Markdown → WhatsApp text formatter.

WhatsApp uses its own markup: *bold*, _italic_, ~strike~, ```mono```.
LLMs typically output standard Markdown which renders as raw text.
This module converts common Markdown patterns to WhatsApp-compatible syntax.
"""

import re

_HEADER_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
_BOLD_DOUBLE_RE = re.compile(r"\*\*(.+?)\*\*")
_BOLD_UNDER_RE = re.compile(r"__(.+?)__")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_TRIPLE_NEWLINE_RE = re.compile(r"\n{3,}")
_CODE_BLOCK_LANG_RE = re.compile(r"```\w+\n", re.MULTILINE)


def markdown_to_whatsapp(text: str) -> str:
    """Convert standard Markdown formatting to WhatsApp-compatible markup."""
    # Headers → bold
    text = _HEADER_RE.sub(r"*\1*", text)
    # **bold** or __bold__ → *bold*
    text = _BOLD_DOUBLE_RE.sub(r"*\1*", text)
    text = _BOLD_UNDER_RE.sub(r"*\1*", text)
    # [text](url) → text: url
    text = _LINK_RE.sub(r"\1: \2", text)
    # ```lang\n → ``` (strip language tag from code blocks)
    text = _CODE_BLOCK_LANG_RE.sub("```\n", text)
    # Collapse excessive blank lines
    text = _TRIPLE_NEWLINE_RE.sub("\n\n", text)
    return text.strip()
