from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

import src.main as main_module
from src.db.base import Base
from src.db.session import get_db_session
from src.main import create_app

# ---------------------------------------------------------------------------
# PostgreSQL test database
# Uses the same Postgres instance as the app but a dedicated "rc7_test" DB
# so tests never touch production data. Tables are created once per session
# and truncated after each test for isolation.
# ---------------------------------------------------------------------------

_PG_USER = os.getenv("POSTGRES_USER", "postgres")
_PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
_PG_HOST = os.getenv("POSTGRES_HOST", "postgres")
_PG_PORT = os.getenv("POSTGRES_PORT", "5432")
_TEST_DB = "rc7_test"

_TEST_DATABASE_URL = (
    f"postgresql+psycopg://{_PG_USER}:{_PG_PASSWORD}@{_PG_HOST}:{_PG_PORT}/{_TEST_DB}"
)


def _ensure_test_db() -> None:
    """Create the rc7_test database if it does not already exist."""
    admin_url = (
        f"postgresql+psycopg://{_PG_USER}:{_PG_PASSWORD}@{_PG_HOST}:{_PG_PORT}/postgres"
    )
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": _TEST_DB},
        ).scalar()
        if not exists:
            conn.execute(text(f"CREATE DATABASE {_TEST_DB}"))  # noqa: S608
    admin_engine.dispose()


@pytest.fixture(scope="session")
def engine():
    _ensure_test_db()
    eng = create_engine(_TEST_DATABASE_URL)
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture(autouse=True)
def clean_tables(engine):
    """Truncate all tables after each test to guarantee a clean slate."""
    yield
    table_names = ", ".join(
        f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables)
    )
    if table_names:
        with engine.connect() as conn:
            conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))  # noqa: S608
            conn.commit()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


@pytest.fixture()
def db_session(session_factory) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory, monkeypatch) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(main_module, "initialize_database", lambda: None)

    app = create_app()

    def override_get_db_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
