"""Tests for admin_service helper functions."""

from datetime import datetime, timezone

from app.services.admin_service import (
    _assemble_timeseries,
    _build_fk_map,
    _build_model_lookup,
    _extract_relations,
    _extract_unique_columns,
    _group_by_day,
    _serialize_default,
)


def test_group_by_day_basic():
    ts1 = datetime(2026, 3, 10, 8, 30, tzinfo=timezone.utc)
    ts2 = datetime(2026, 3, 10, 14, 0, tzinfo=timezone.utc)
    ts3 = datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc)
    result = _group_by_day([ts1, ts2, ts3])
    assert result == {"2026-03-10": 2, "2026-03-11": 1}


def test_group_by_day_empty():
    assert _group_by_day([]) == {}


def test_group_by_day_string_fallback():
    result = _group_by_day(["2026-01-15T10:00:00"])
    assert result == {"2026-01-15": 1}


def test_assemble_timeseries():
    start = datetime(2026, 3, 10, 0, 0, 0, tzinfo=timezone.utc)
    tenant_by_day = {"2026-03-10": 2, "2026-03-11": 1}
    lead_by_day = {"2026-03-10": 5}
    conv_by_day = {"2026-03-11": 3}
    result = _assemble_timeseries(start, 3, 10, tenant_by_day, lead_by_day, conv_by_day)
    assert len(result) == 3
    assert result[0]["date"] == "2026-03-10"
    assert result[0]["tenants"] == 12  # 10 base + 2
    assert result[0]["leads"] == 5
    assert result[1]["tenants"] == 13  # 12 + 1
    assert result[1]["conversations"] == 3
    assert result[2]["tenants"] == 13  # no new


def test_assemble_timeseries_zero_days():
    start = datetime(2026, 3, 10, tzinfo=timezone.utc)
    assert _assemble_timeseries(start, 0, 5, {}, {}, {}) == []


def test_serialize_default_none():
    assert _serialize_default(None) is None


def test_serialize_default_string():
    assert _serialize_default("some_default") == "some_default"


def test_serialize_default_number():
    assert _serialize_default(42) == "42"


def test_extract_unique_columns():
    constraints = [{"column_names": ["email"]}, {"column_names": ["a", "b"]}]
    indexes = [
        {"column_names": ["slug"], "unique": True},
        {"column_names": ["name"], "unique": False},
    ]
    result = _extract_unique_columns(constraints, indexes)
    assert result == {"email", "slug"}


def test_extract_unique_columns_empty():
    assert _extract_unique_columns([], []) == set()


def test_build_fk_map():
    result = _build_fk_map(["tenant_id"], ["id"], "tenants")
    assert result == {"tenant_id": "tenants.id"}


def test_build_fk_map_multiple():
    result = _build_fk_map(["col_a", "col_b"], ["id_a", "id_b"], "other")
    assert result == {"col_a": "other.id_a", "col_b": "other.id_b"}


def test_extract_relations():
    fks = [
        {
            "constrained_columns": ["tenant_id"],
            "referred_columns": ["id"],
            "referred_table": "tenants",
            "options": {"ondelete": "CASCADE"},
        },
        {
            "constrained_columns": ["lead_id"],
            "referred_columns": ["id"],
            "referred_table": "leads",
            "options": {},
        },
    ]
    relations, fk_map = _extract_relations(fks)
    assert len(relations) == 2
    assert relations[0]["references_table"] == "tenants"
    assert relations[0]["on_delete"] == "CASCADE"
    assert fk_map["tenant_id"] == "tenants.id"
    assert fk_map["lead_id"] == "leads.id"


def test_extract_relations_empty():
    relations, fk_map = _extract_relations([])
    assert relations == []
    assert fk_map == {}


def test_extract_relations_skips_invalid():
    fks = [{"constrained_columns": [], "referred_columns": [], "referred_table": None}]
    relations, fk_map = _extract_relations(fks)
    assert relations == []


def test_build_model_lookup():
    """Model lookup should contain at least our known models."""
    lookup = _build_model_lookup()
    assert "tenants" in lookup
    assert "usuarios" in lookup
    model_name, desc = lookup["tenants"]
    assert model_name == "Tenant"
