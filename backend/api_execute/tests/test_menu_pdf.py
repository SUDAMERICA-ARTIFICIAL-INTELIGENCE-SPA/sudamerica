"""Tests for menu_pdf_service: size grouping, PDF generation, helpers."""

import pytest

from app.services.menu_pdf_service import (
    _generate_pdf_bytes,
    _group_size_variants,
    _render_section_items,
    _safe,
    _size_sort_key,
    MenuPDF,
)


# ── _safe ────────────────────────────────────────────────────────────

def test_safe_none():
    assert _safe(None) == ""


def test_safe_empty():
    assert _safe("") == ""


def test_safe_ascii():
    assert _safe("Pizza Margherita") == "Pizza Margherita"


def test_safe_unicode_fallback():
    result = _safe("Niño Envuelto — Edición Café")
    assert isinstance(result, str)
    assert len(result) > 0


# ── _size_sort_key ───────────────────────────────────────────────────

def test_size_sort_key_known():
    assert _size_sort_key("chica") < _size_sort_key("grande")
    assert _size_sort_key("mini") < _size_sort_key("familiar")
    assert _size_sort_key("small") < _size_sort_key("large")


def test_size_sort_key_unknown():
    assert _size_sort_key("gigante") == 999


def test_size_sort_key_case_insensitive():
    assert _size_sort_key("GRANDE") == _size_sort_key("grande")


# ── _group_size_variants ─────────────────────────────────────────────

def test_group_singles_only():
    products = [
        {"nombre": "Empanada de Queso", "precio": 2000, "descripcion": "Queso derretido"},
        {"nombre": "Ensalada Caesar", "precio": 5000, "descripcion": None},
    ]
    result = _group_size_variants(products)
    assert len(result) == 2
    assert all(item["type"] == "single" for item in result)
    assert result[0]["name"] == "Empanada de Queso"
    assert result[0]["price"] == 2000


def test_group_size_variants_detected():
    products = [
        {"nombre": "Hawaiana - Chica", "precio": 5000, "descripcion": "Pina y jamon"},
        {"nombre": "Hawaiana - Grande", "precio": 9000, "descripcion": "Pina y jamon"},
        {"nombre": "Hawaiana - Familiar", "precio": 14000, "descripcion": "Pina y jamon"},
    ]
    result = _group_size_variants(products)
    assert len(result) == 1
    grouped = result[0]
    assert grouped["type"] == "grouped"
    assert grouped["name"] == "Hawaiana"
    assert len(grouped["sizes"]) == 3
    # Should be sorted by size order: chica < grande < familiar
    assert grouped["sizes"][0]["size"] == "Chica"
    assert grouped["sizes"][1]["size"] == "Grande"
    assert grouped["sizes"][2]["size"] == "Familiar"


def test_group_mixed_singles_and_variants():
    products = [
        {"nombre": "Pepperoni - Chica", "precio": 6000, "descripcion": ""},
        {"nombre": "Pepperoni - Grande", "precio": 10000, "descripcion": ""},
        {"nombre": "Lasagna", "precio": 8500, "descripcion": "Clasica"},
    ]
    result = _group_size_variants(products)
    assert len(result) == 2
    types = {item["type"] for item in result}
    assert types == {"grouped", "single"}


def test_group_empty_list():
    assert _group_size_variants([]) == []


def test_group_variant_desc_from_first():
    products = [
        {"nombre": "Caprese - Chica", "precio": 4000, "descripcion": "Tomate y mozza"},
        {"nombre": "Caprese - Grande", "precio": 7000, "descripcion": ""},
    ]
    result = _group_size_variants(products)
    assert result[0]["desc"] == "Tomate y mozza"


# ── _generate_pdf_bytes ──────────────────────────────────────────────

def test_generate_pdf_empty_sections():
    pdf_bytes = _generate_pdf_bytes("Test Restaurant", [])
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 100
    assert pdf_bytes[:5] == b"%PDF-"


def test_generate_pdf_with_singles():
    sections = [
        {
            "category": "Entradas",
            "items": [
                {"type": "single", "name": "Empanada", "price": 2000, "desc": "De queso"},
                {"type": "single", "name": "Humita", "price": 3000, "desc": ""},
            ],
        },
    ]
    pdf_bytes = _generate_pdf_bytes("Mi Restaurante", sections)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:5] == b"%PDF-"


def test_generate_pdf_with_grouped():
    sections = [
        {
            "category": "Pizzas",
            "items": [
                {
                    "type": "grouped",
                    "name": "Margherita",
                    "desc": "Clasica",
                    "sizes": [
                        {"size": "Chica", "price": 5000},
                        {"size": "Grande", "price": 9000},
                    ],
                },
            ],
        },
    ]
    pdf_bytes = _generate_pdf_bytes("Pizzeria", sections)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 200


def test_generate_pdf_mixed_sections():
    sections = [
        {
            "category": "Pizzas",
            "items": [
                {
                    "type": "grouped",
                    "name": "Hawaiana",
                    "desc": "",
                    "sizes": [
                        {"size": "Chica", "price": 6000},
                        {"size": "Grande", "price": 10000},
                    ],
                },
            ],
        },
        {
            "category": "Bebidas",
            "items": [
                {"type": "single", "name": "Coca Cola", "price": 1500, "desc": "350ml"},
            ],
        },
        {
            "category": "Vacia",
            "items": [],  # Should be skipped
        },
    ]
    pdf_bytes = _generate_pdf_bytes("Test", sections)
    assert isinstance(pdf_bytes, bytes)


def test_generate_pdf_unicode_restaurant():
    sections = [
        {
            "category": "Platos",
            "items": [
                {"type": "single", "name": "Pollo", "price": 8000, "desc": ""},
            ],
        },
    ]
    pdf_bytes = _generate_pdf_bytes("Café Niño — Edición Especial", sections)
    assert isinstance(pdf_bytes, bytes)


# ── MenuPDF class ─────────────────────────────────────────────────────

def test_menu_pdf_header_footer():
    pdf = MenuPDF("Test")
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 10, "Test content")
    output = bytes(pdf.output())
    assert output[:5] == b"%PDF-"


# ── _render_section_items ─────────────────────────────────────────────

def test_render_section_items_no_crash():
    pdf = MenuPDF("Test")
    pdf.alias_nb_pages()
    pdf.add_page()
    items = [
        {"type": "single", "name": "Item A", "price": 1000, "desc": "Desc"},
        {"type": "single", "name": "Item B", "price": 2000, "desc": ""},
    ]
    _render_section_items(pdf, items)
    output = bytes(pdf.output())
    assert len(output) > 100
