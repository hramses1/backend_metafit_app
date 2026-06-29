"""Tests de la API MetaFit."""
from datetime import datetime, timezone


def _session_payload(sid="s1", kg=60.0, reps=10):
    return {
        "id": sid,
        "routineName": "Push Day",
        "tag": "A",
        "date": datetime.now(timezone.utc).isoformat(),
        "durationSeconds": 3000,
        "prCount": 1,
        "exercises": [
            {
                "exerciseId": "bench",
                "name": "Press de Banca",
                "muscle": "pecho",
                "sets": [{"kg": kg, "reps": reps}, {"kg": kg, "reps": reps}],
            }
        ],
    }


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_login_me(client):
    r = client.post("/auth/register", json={"handle": "ana", "name": "Ana", "password": "secret123"})
    assert r.status_code == 201
    # Handle duplicado → 409.
    dup = client.post("/auth/register", json={"handle": "ana", "name": "Ana", "password": "secret123"})
    assert dup.status_code == 409
    # Login OK.
    login = client.post("/auth/login", json={"handle": "ana", "password": "secret123"})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    me = client.get("/me", headers=headers)
    assert me.json()["handle"] == "ana"


def test_update_profile_name_handle_avatar(client, auth):
    r = client.patch("/me", json={"name": "Marco P.", "handle": "marcop", "avatar": "Zm9v"}, headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Marco P."
    assert body["handle"] == "marcop"
    assert body["avatar"] == "Zm9v"
    # Quitar la foto con cadena vacía.
    assert client.patch("/me", json={"avatar": ""}, headers=auth).json()["avatar"] is None


def test_update_profile_handle_conflict(client, auth):
    client.post("/auth/register", json={"handle": "lucia", "name": "Lucia", "password": "secret123"})
    assert client.patch("/me", json={"handle": "lucia"}, headers=auth).status_code == 409


def test_change_password(client):
    reg = client.post("/auth/register", json={"handle": "leo", "name": "Leo", "password": "oldpass1"})
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    # Contraseña actual incorrecta → 401.
    bad = client.post("/me/password", json={"current_password": "wrong", "new_password": "newpass1"}, headers=headers)
    assert bad.status_code == 401
    # Cambio correcto → 204 y login con la nueva.
    ok = client.post("/me/password", json={"current_password": "oldpass1", "new_password": "newpass1"}, headers=headers)
    assert ok.status_code == 204
    assert client.post("/auth/login", json={"handle": "leo", "password": "oldpass1"}).status_code == 401
    assert client.post("/auth/login", json={"handle": "leo", "password": "newpass1"}).status_code == 200


def test_protected_requires_token(client):
    assert client.get("/sessions").status_code == 401
    assert client.get("/sessions", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_routines_crud(client, auth):
    body = {
        "id": "r1",
        "name": "Push",
        "tag": "A",
        "items": [{"exerciseId": "bench", "sets": 4, "kg": 60, "reps": 10}],
    }
    assert client.put("/routines/r1", json=body, headers=auth).status_code == 200
    lst = client.get("/routines", headers=auth).json()
    assert len(lst) == 1 and lst[0]["name"] == "Push"
    assert client.delete("/routines/r1", headers=auth).status_code == 204
    assert client.get("/routines", headers=auth).json() == []


def test_push_session_computes_volume_and_idempotent(client, auth):
    r = client.post("/sessions", json=_session_payload(kg=60, reps=10), headers=auth)
    assert r.status_code == 201
    assert r.json()["volume"] == 1200.0  # 60*10*2
    # Reenviar el mismo id no duplica (upsert).
    client.post("/sessions", json=_session_payload(kg=70, reps=10), headers=auth)
    sessions = client.get("/sessions", headers=auth).json()
    assert len(sessions) == 1
    assert sessions[0]["volume"] == 1400.0


def test_community_feed_and_kudos(client, auth):
    client.post("/sessions", json=_session_payload(), headers=auth)
    feed = client.get("/community/feed", headers=auth).json()
    assert len(feed) == 1 and feed[0]["author"] == "Marco"
    kud = client.post(f"/community/{feed[0]['sessionId']}/kudos", headers=auth)
    assert kud.json()["kudos"] == 1
