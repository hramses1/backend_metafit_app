"""MetaFit API — auth, rutinas, sesiones y feed de comunidad."""
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from . import models, schemas
from .db import get_db, init_db
from .security import create_token, decode_token, hash_password, verify_password


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="MetaFit API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ───────────────────────── dependencias ─────────────────────────
DbDep = Annotated[OrmSession, Depends(get_db)]


def current_user(
    db: DbDep,
    authorization: Annotated[str | None, Header()] = None,
) -> models.User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta token")
    user_id = decode_token(authorization.split(" ", 1)[1])
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no existe")
    return user


UserDep = Annotated[models.User, Depends(current_user)]


def _volume(exercises: list[schemas.CompletedExercise]) -> float:
    return float(sum(s.kg * s.reps for e in exercises for s in e.sets))


# ───────────────────────── health ─────────────────────────
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ───────────────────────── auth ─────────────────────────
@app.post("/auth/register", response_model=schemas.Token, status_code=201)
def register(body: schemas.RegisterIn, db: DbDep) -> schemas.Token:
    exists = db.scalar(select(models.User).where(models.User.handle == body.handle))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Handle ya registrado")
    user = models.User(
        handle=body.handle,
        name=body.name,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.Token(access_token=create_token(user.id))


@app.post("/auth/login", response_model=schemas.Token)
def login(body: schemas.LoginIn, db: DbDep) -> schemas.Token:
    user = db.scalar(select(models.User).where(models.User.handle == body.handle))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    return schemas.Token(access_token=create_token(user.id))


@app.get("/me", response_model=schemas.UserOut)
def me(user: UserDep) -> models.User:
    return user


@app.patch("/me", response_model=schemas.UserOut)
def update_me(body: schemas.UpdateProfileIn, user: UserDep, db: DbDep) -> models.User:
    if body.handle is not None and body.handle != user.handle:
        taken = db.scalar(select(models.User).where(models.User.handle == body.handle))
        if taken is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Handle ya registrado")
        user.handle = body.handle
    if body.name is not None:
        user.name = body.name
    if body.avatar is not None:
        # "" elimina la foto; cualquier otro valor la reemplaza.
        user.avatar = body.avatar or None
    db.commit()
    db.refresh(user)
    return user


@app.post("/me/password", status_code=204)
def change_password(body: schemas.ChangePasswordIn, user: UserDep, db: DbDep) -> None:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Contraseña actual incorrecta")
    user.password_hash = hash_password(body.new_password)
    db.commit()


# ───────────────────────── rutinas ─────────────────────────
@app.get("/routines", response_model=list[schemas.RoutineOut])
def list_routines(user: UserDep, db: DbDep) -> list[models.Routine]:
    return list(db.scalars(select(models.Routine).where(models.Routine.owner_id == user.id)))


@app.put("/routines/{routine_id}", response_model=schemas.RoutineOut)
def upsert_routine(routine_id: str, body: schemas.RoutineIn, user: UserDep, db: DbDep) -> models.Routine:
    if routine_id != body.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "id no coincide")
    routine = db.get(models.Routine, routine_id)
    if routine and routine.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No es tu rutina")
    if routine is None:
        routine = models.Routine(id=body.id, owner_id=user.id)
        db.add(routine)
    routine.name = body.name
    routine.tag = body.tag
    routine.items = [i.model_dump() for i in body.items]
    db.commit()
    db.refresh(routine)
    return routine


@app.delete("/routines/{routine_id}", status_code=204)
def delete_routine(routine_id: str, user: UserDep, db: DbDep) -> None:
    routine = db.get(models.Routine, routine_id)
    if routine and routine.owner_id == user.id:
        db.delete(routine)
        db.commit()


# ───────────────────────── sesiones ─────────────────────────
@app.post("/sessions", response_model=schemas.SessionOut, status_code=201)
def push_session(body: schemas.SessionIn, user: UserDep, db: DbDep) -> models.Session:
    existing = db.get(models.Session, body.id)
    if existing and existing.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No es tu sesión")
    vol = _volume(body.exercises)
    if existing is None:
        existing = models.Session(id=body.id, owner_id=user.id)
        db.add(existing)
    existing.routine_name = body.routineName
    existing.tag = body.tag
    existing.date = body.date.replace(tzinfo=None)
    existing.duration_seconds = body.durationSeconds
    existing.pr_count = body.prCount
    existing.volume = vol
    existing.exercises = [e.model_dump() for e in body.exercises]
    db.commit()
    db.refresh(existing)
    return _session_out(existing)


@app.get("/sessions", response_model=list[schemas.SessionOut])
def list_sessions(user: UserDep, db: DbDep) -> list[schemas.SessionOut]:
    rows = db.scalars(
        select(models.Session)
        .where(models.Session.owner_id == user.id)
        .order_by(models.Session.date.desc())
    )
    return [_session_out(s) for s in rows]


def _session_out(s: models.Session) -> schemas.SessionOut:
    return schemas.SessionOut(
        id=s.id,
        routineName=s.routine_name,
        tag=s.tag,
        date=s.date,
        durationSeconds=s.duration_seconds,
        prCount=s.pr_count,
        exercises=s.exercises,
        volume=s.volume,
        kudos=s.kudos,
    )


# ───────────────────────── comunidad ─────────────────────────
@app.get("/community/feed", response_model=list[schemas.FeedItem])
def feed(user: UserDep, db: DbDep, limit: int = 20) -> list[schemas.FeedItem]:
    rows = db.scalars(
        select(models.Session).order_by(models.Session.date.desc()).limit(limit)
    )
    out: list[schemas.FeedItem] = []
    for s in rows:
        author = db.get(models.User, s.owner_id)
        out.append(schemas.FeedItem(
            sessionId=s.id,
            author=author.name if author else "?",
            handle=author.handle if author else "?",
            routineName=s.routine_name,
            date=s.date,
            volume=s.volume,
            durationSeconds=s.duration_seconds,
            prCount=s.pr_count,
            kudos=s.kudos,
        ))
    return out


@app.post("/community/{session_id}/kudos", response_model=schemas.FeedItem)
def give_kudos(session_id: str, user: UserDep, db: DbDep) -> schemas.FeedItem:
    s = db.get(models.Session, session_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión no existe")
    s.kudos += 1
    db.commit()
    db.refresh(s)
    author = db.get(models.User, s.owner_id)
    return schemas.FeedItem(
        sessionId=s.id,
        author=author.name if author else "?",
        handle=author.handle if author else "?",
        routineName=s.routine_name,
        date=s.date,
        volume=s.volume,
        durationSeconds=s.duration_seconds,
        prCount=s.pr_count,
        kudos=s.kudos,
    )
