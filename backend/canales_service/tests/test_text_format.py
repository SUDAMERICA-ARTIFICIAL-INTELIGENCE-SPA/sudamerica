"""Tests for Markdown → WhatsApp text formatter."""

from app.services.text_format import markdown_to_whatsapp


def test_double_asterisk_to_single():
    assert markdown_to_whatsapp("**hola**") == "*hola*"


def test_double_underscore_to_single():
    assert markdown_to_whatsapp("__hola__") == "*hola*"


def test_headers_become_bold():
    assert markdown_to_whatsapp("## Título") == "*Título*"
    assert markdown_to_whatsapp("# Encabezado") == "*Encabezado*"


def test_markdown_links_become_plain():
    result = markdown_to_whatsapp("[click aquí](https://example.com)")
    assert result == "click aquí: https://example.com"


def test_code_block_lang_stripped():
    text = "```python\nprint('hi')\n```"
    result = markdown_to_whatsapp(text)
    assert "```python" not in result
    assert "print('hi')" in result


def test_excessive_newlines_collapsed():
    assert markdown_to_whatsapp("a\n\n\n\nb") == "a\n\nb"


def test_already_whatsapp_format_unchanged():
    text = "*negrita* y _cursiva_ y ~tachado~"
    assert markdown_to_whatsapp(text) == text


def test_mixed_content():
    text = "## Resumen\n\n**Total**: $1,500\n\n- Item 1\n- Item 2"
    result = markdown_to_whatsapp(text)
    assert result == "*Resumen*\n\n*Total*: $1,500\n\n- Item 1\n- Item 2"
