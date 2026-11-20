import os
import tempfile
from pathlib import Path

# has to be set before importing the app
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp) / 'test.db'}"
os.environ["QUEUE_MODE"] = "inline"
os.environ["GEMINI_API_KEY"] = ""
os.environ["BOOTSTRAP_USERNAME"] = "admin"
os.environ["BOOTSTRAP_PASSWORD"] = "admin123"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import cache  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    cache.set_client(None)
    with TestClient(app) as c:
        yield c
    cache.set_client(None)


def login(client, username="admin", password="admin123") -> dict:
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def admin_headers(client):
    return login(client)


@pytest.fixture()
def officer_headers(client, admin_headers):
    r = client.post("/auth/users", json={"username": "officer1", "password": "officer-pass"}, headers=admin_headers)
    assert r.status_code == 201, r.text
    return login(client, "officer1", "officer-pass")
