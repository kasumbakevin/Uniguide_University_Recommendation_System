import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture()
def app(tmp_path):
    from config import Config

    class TestConfig(Config):
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(tmp_path / "test.db")
        TESTING = True
        WTF_CSRF_ENABLED = False

    from app import create_app

    return create_app(TestConfig)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def registered_client(app):
    client = app.test_client()
    client.post("/auth/register", data={
        "name": "Test Student",
        "email": "test@student.ug",
        "password": "secret123",
        "confirm": "secret123",
    })
    return client