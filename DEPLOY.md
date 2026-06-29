# Deploy de la API MetaFit

## Opción A — Render (recomendado, free + HTTPS)

1. Sube los cambios al repo (`backend_metafit_app`):
   ```bash
   git add -A && git commit -m "deploy: render + dockerfile + postgres" && git push
   ```
2. En https://render.com → **New → Blueprint** → conecta el repo. Render lee `render.yaml`.
3. Deploy. Te queda una URL tipo `https://metafit-api.onrender.com`.
4. Verifica: abre `https://metafit-api.onrender.com/health` → `{"status":"ok"}`.

> El plan free **duerme** tras ~15 min sin tráfico; el primer request luego tarda ~30 s.

### Datos persistentes (recomendado)
Por defecto usa SQLite efímera (se borra al redeploy). Para no perder usuarios:
1. Crea un Postgres free en **Neon** (https://neon.tech) o **Supabase**.
2. Copia su connection string (`postgresql://user:pass@host/db`).
3. En Render → tu servicio → **Environment** → `METAFIT_DB` = esa URL → Save (redeploy).

El código normaliza la URL solo (`postgres://`/`postgresql://` → driver psycopg).

## Opción B — Railway / Fly.io / Docker

Usa el `Dockerfile` incluido:
```bash
# Fly.io
fly launch        # detecta el Dockerfile
fly deploy
```
Setea `METAFIT_SECRET` (y `METAFIT_DB` si usas Postgres) como variables de entorno.

## Variables de entorno

| Var | Obligatoria | Descripción |
|-----|-------------|-------------|
| `METAFIT_SECRET` | Sí (prod) | Clave JWT. Larga y aleatoria. |
| `METAFIT_DB` | No | URL Postgres. Sin ella = SQLite local efímera. |
| `METAFIT_TOKEN_TTL_MIN` | No | Minutos de validez del token (default 7 días). |
| `PORT` | La pone el host | Puerto de escucha. |

## Construir el APK apuntando a la API

```bash
cd app_metafit
flutter build apk --release --split-per-abi \
  --dart-define=METAFIT_API=https://metafit-api.onrender.com
```
APK en `build/app/outputs/flutter-apk/app-arm64-v8a-release.apk`.
Pásalo al teléfono e instala. La app usará esa API por defecto (sin tocar nada).
