"""SQLite persistence layer."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import DB_URL, ensure_dirs

ensure_dirs()

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
    future=True,
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _connection_record):  # pragma: no cover - driver hook
    if DB_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    from . import models  # noqa: F401  (register mappers)
    from . import kb_models  # noqa: F401  (register knowledge-base mappers)
    from . import lp_models  # noqa: F401  (register learning-path mappers)

    Base.metadata.create_all(engine)
    _migrate_columns()


def _migrate_columns() -> None:
    """Additive column migrations for SQLite DBs created before a field existed.

    ``create_all`` never alters an existing table, so a new column on an old
    install would otherwise fail every query. Each entry is (table, column, DDL).
    """
    if not DB_URL.startswith("sqlite"):
        return
    from sqlalchemy import inspect, text

    wanted = [
        ("kb_sources", "noncommercial_reuse", "BOOLEAN DEFAULT 0"),
        ("lp_activities", "equipment", "VARCHAR(40) DEFAULT ''"),
    ]
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, column, ddl in wanted:
            if not inspector.has_table(table):
                continue
            existing = {col["name"] for col in inspector.get_columns(table)}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


@contextmanager
def db_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
