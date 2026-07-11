"""Tests for shared/services/crud.py — generic tenant-scoped CRUD operations."""

import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

import pytest
import pytest_asyncio
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool

from datetime import datetime, timezone

from sqlalchemy import DateTime

from shared.services.crud import get_by_id, list_active, soft_delete, update_fields, reactivate
from shared.utils.exceptions import NotFoundError
from shared.utils.sql_helpers import escape_like


def _utcnow():
    return datetime.now(timezone.utc)


# ── Isolated test model (separate metadata) ───────────

class _TestBase(DeclarativeBase):
    pass


class FakeItem(_TestBase):
    __tablename__ = "fake_items"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    activo: Mapped[bool] = mapped_column(default=True)
    nombre: Mapped[str] = mapped_column(String(100), default="item")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow,
    )


# ── Fixtures ──────────────────────────────────────────

_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_SessionFactory = async_sessionmaker(_engine, expire_on_commit=False)

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()


@pytest_asyncio.fixture(scope="module", autouse=True)
async def _create_tables():
    async with _engine.begin() as conn:
        await conn.run_sync(_TestBase.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(_TestBase.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with _SessionFactory() as session:
        yield session
        await session.rollback()


class FakePagination:
    def __init__(self, page=1, page_size=10):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size


# ── Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_active_empty(db):
    result = await list_active(db, FakeItem, TENANT_A, FakePagination())
    assert result.data == []
    assert result.meta["total"] == 0


@pytest.mark.asyncio
async def test_crud_lifecycle(db):
    item = FakeItem(tenant_id=TENANT_A, nombre="Empanada")
    db.add(item)
    await db.flush()

    fetched = await get_by_id(db, FakeItem, TENANT_A, item.id)
    assert fetched.nombre == "Empanada"

    updated = await update_fields(db, FakeItem, TENANT_A, item.id, {"nombre": "Empanada Premium"})
    assert updated.nombre == "Empanada Premium"

    result = await list_active(db, FakeItem, TENANT_A, FakePagination())
    assert result.meta["total"] == 1

    deleted = await soft_delete(db, FakeItem, TENANT_A, item.id)
    assert deleted.activo is False

    result = await list_active(db, FakeItem, TENANT_A, FakePagination())
    assert result.meta["total"] == 0

    reactivated = await reactivate(db, FakeItem, TENANT_A, item.id)
    assert reactivated.activo is True


@pytest.mark.asyncio
async def test_get_by_id_not_found(db):
    with pytest.raises(NotFoundError):
        await get_by_id(db, FakeItem, TENANT_A, uuid.uuid4())


@pytest.mark.asyncio
async def test_tenant_isolation(db):
    item = FakeItem(tenant_id=TENANT_A, nombre="Pizza")
    db.add(item)
    await db.flush()

    with pytest.raises(NotFoundError):
        await get_by_id(db, FakeItem, TENANT_B, item.id)


@pytest.mark.asyncio
async def test_list_active_pagination(db):
    for i in range(5):
        db.add(FakeItem(tenant_id=TENANT_B, nombre=f"Item {i}"))
    await db.flush()

    page1 = await list_active(db, FakeItem, TENANT_B, FakePagination(page=1, page_size=2))
    assert len(page1.data) == 2
    assert page1.meta["total"] == 5
    assert page1.meta["total_pages"] == 3


def test_escape_like():
    assert escape_like("hello") == "hello"
    assert escape_like("50%_off") == "50\\%\\_off"
