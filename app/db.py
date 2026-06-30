"""Configuración de base de datos (SQLAlchemy 2.0 + SQLite)."""
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

def _normalize_db_url(url: str) -> str:
    """Los hosts (Render/Neon/Supabase/Heroku) suelen dar `postgres://...` o
    `postgresql://...`. SQLAlchemy 2.0 con psycopg3 necesita el driver explícito
    `postgresql+psycopg://`. Normalizamos para que funcione sin tocar el env."""
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize_db_url(os.getenv("METAFIT_DB", "sqlite:///./metafit.db"))

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # evita conexiones muertas en hosts que duermen
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401  (registra los modelos)

    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate():
    """Migraciones ligeras para bases ya creadas (sin Alembic)."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "avatar" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar TEXT"))
    if "google_sub" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN google_sub TEXT"))
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub "
                "ON users(google_sub) WHERE google_sub IS NOT NULL"
            ))
    if "apple_sub" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN apple_sub TEXT"))
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_apple_sub "
                "ON users(apple_sub) WHERE apple_sub IS NOT NULL"
            ))
