import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://aaroh:aaroh@localhost:5432/aaroh_test")
os.environ["ENVIRONMENT"] = "test"
os.environ["AI_PROVIDER"] = "none"
os.environ["UPLOAD_DIR"] = "/tmp/aaroh-test-uploads"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client():
    return TestClient(app)


_counter = {"n": 0}


def make_user(client, name="User"):
    _counter["n"] += 1
    email = f"user{_counter['n']}@example.com"
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "S3cure-pass!", "full_name": name})
    assert r.status_code == 201, r.text
    tok = r.json()
    return {"email": email, "headers": {"Authorization": f"Bearer {tok['access_token']}"}, "refresh": tok["refresh_token"]}


@pytest.fixture()
def user(client):
    return make_user(client)
