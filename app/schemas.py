"""Esquemas Pydantic (contrato de la API). Coinciden con el JSON del cliente Flutter."""
from datetime import datetime

from pydantic import BaseModel, Field


# ---- Auth ----
class RegisterIn(BaseModel):
    handle: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    handle: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    handle: str
    name: str
    avatar: str | None = None


class UpdateProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    handle: str | None = Field(default=None, min_length=2, max_length=64)
    avatar: str | None = None  # base64 sin prefijo; "" para quitar la foto


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


# ---- Rutinas ----
class RoutineItem(BaseModel):
    exerciseId: str
    sets: int
    kg: float
    reps: int


class RoutineIn(BaseModel):
    id: str
    name: str
    tag: str = "A"
    items: list[RoutineItem] = []


class RoutineOut(RoutineIn):
    pass


# ---- Sesiones ----
class CompletedSet(BaseModel):
    kg: float
    reps: int


class CompletedExercise(BaseModel):
    exerciseId: str
    name: str
    muscle: str
    sets: list[CompletedSet]


class SessionIn(BaseModel):
    id: str
    routineName: str
    tag: str = ""
    date: datetime
    durationSeconds: int = 0
    prCount: int = 0
    exercises: list[CompletedExercise] = []


class SessionOut(SessionIn):
    volume: float
    kudos: int = 0


class FeedItem(BaseModel):
    sessionId: str
    author: str
    handle: str
    routineName: str
    date: datetime
    volume: float
    durationSeconds: int
    prCount: int
    kudos: int
