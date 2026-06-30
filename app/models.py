"""Modelos ORM."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    handle: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    # Foto de perfil como base64 (sin prefijo data:). Opcional.
    avatar: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    google_sub: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    routines: Mapped[list["Routine"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    sessions: Mapped[list["Session"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Routine(Base):
    __tablename__ = "routines"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    tag: Mapped[str] = mapped_column(String(8), default="A")
    items: Mapped[list] = mapped_column(JSON, default=list)  # [{exerciseId,sets,kg,reps}]

    owner: Mapped[User] = relationship(back_populates="routines")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    routine_name: Mapped[str] = mapped_column(String(120))
    tag: Mapped[str] = mapped_column(String(8), default="")
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    pr_count: Mapped[int] = mapped_column(Integer, default=0)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    exercises: Mapped[list] = mapped_column(JSON, default=list)  # payload completo
    kudos: Mapped[int] = mapped_column(Integer, default=0)

    owner: Mapped[User] = relationship(back_populates="sessions")
