# MetaFit API (FastAPI)

Backend opcional para sync en la nube y comunidad. La app Flutter funciona **local-first**;
este servicio añade respaldo de sesiones/rutinas y un feed social real.

## Stack
FastAPI · SQLAlchemy 2.0 · SQLite · JWT (PyJWT) · bcrypt (passlib).

## Ejecutar

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate     Linux/mac:  source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload          # http://127.0.0.1:8000
# Docs interactivas: http://127.0.0.1:8000/docs
```

## Tests
```bash
pytest -q
```

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Healthcheck |
| POST | `/auth/register` | Crea usuario → token |
| POST | `/auth/login` | Login → token |
| GET | `/me` | Perfil (requiere token) |
| GET | `/routines` | Rutinas del usuario |
| PUT | `/routines/{id}` | Crear/actualizar rutina |
| DELETE | `/routines/{id}` | Borrar rutina |
| POST | `/sessions` | Subir sesión completada (upsert por id) |
| GET | `/sessions` | Historial del usuario |
| GET | `/community/feed` | Feed global reciente |
| POST | `/community/{id}/kudos` | Dar kudos |

Auth: cabecera `Authorization: Bearer <token>`.

El contrato JSON de `/sessions` coincide con `CompletedSession` del cliente Flutter,
por lo que el `SyncService` puede empujar sesiones sin transformación.

## Variables de entorno
- `METAFIT_DB` (default `sqlite:///./metafit.db`)
- `METAFIT_SECRET` (¡cámbialo en producción!)
- `METAFIT_TOKEN_TTL_MIN` (default 10080 = 7 días)
