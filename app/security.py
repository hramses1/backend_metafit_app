"""Hash de contraseñas + JWT + verificación Google + verificación Apple."""
import json
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
import jwt
from jwt.algorithms import ECAlgorithm

SECRET_KEY = os.getenv("METAFIT_SECRET", "dev-secret-change-in-prod")
ALGORITHM = "HS256"
TOKEN_TTL_MIN = int(os.getenv("METAFIT_TOKEN_TTL_MIN", "10080"))  # 7 días


def hash_password(password: str) -> str:
    # bcrypt limita a 72 bytes; truncamos los bytes para claves largas.
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    pw = password.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except ValueError:
        return False


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_TTL_MIN),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    "349347866924-1rc7uk6n8vd79vm3hpf7oe2f83f11dht.apps.googleusercontent.com",
)


APPLE_BUNDLE_ID = os.getenv("APPLE_BUNDLE_ID", "com.metafit.app")


def verify_apple_id_token(identity_token: str) -> dict | None:
    """Verifica un identity token de Sign in with Apple (ES256 vía JWKS).
    Retorna el payload si válido, None si no."""
    try:
        r = httpx.get("https://appleid.apple.com/auth/keys", timeout=10)
        if r.status_code != 200:
            return None
        keys = r.json().get("keys", [])
        header = jwt.get_unverified_header(identity_token)
        kid = header.get("kid")
        matching = next((k for k in keys if k["kid"] == kid), None)
        if not matching:
            return None
        public_key = ECAlgorithm.from_jwk(json.dumps(matching))
        return jwt.decode(
            identity_token,
            public_key,
            algorithms=["ES256"],
            audience=APPLE_BUNDLE_ID,
            issuer="https://appleid.apple.com",
        )
    except Exception:
        return None


def verify_google_id_token(id_token: str) -> dict | None:
    """Verifica un ID token de Google con el endpoint tokeninfo de Google.
    Retorna el payload si es válido, None si no."""
    try:
        r = httpx.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        # aud debe coincidir con el web client ID registrado
        if data.get("aud") != GOOGLE_CLIENT_ID:
            return None
        if str(data.get("email_verified", "")).lower() != "true":
            return None
        return data
    except Exception:
        return None
