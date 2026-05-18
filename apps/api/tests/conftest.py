from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Text, create_engine
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.orm import Session, sessionmaker

import src.main as main_module
from src.db.base import Base
from src.db.session import get_db_session


# SQLite does not natively support PostgreSQL's ARRAY type.
# Teach the SQLite DDL type compiler to render ARRAY columns as TEXT so that
# Base.metadata.create_all() succeeds in SQLite-backed test fixtures.
def _visit_ARRAY(self, type_, **kw):  # noqa: N802
    return self.process(Text(), **kw)


SQLiteTypeCompiler.visit_ARRAY = _visit_ARRAY  # type: ignore[attr-defined]


# SQLite does not support PostgreSQL's JSONB type.
# Render it as TEXT for DDL in SQLite-backed test fixtures.
def _visit_JSONB(self, type_, **kw):  # noqa: N802
    return self.process(Text(), **kw)


SQLiteTypeCompiler.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]
from src.main import create_app


@pytest.fixture()
def test_engine(tmp_path):
    database_path = tmp_path / "test.sqlite3"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def session_factory(test_engine):
    return sessionmaker(
        bind=test_engine,
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
