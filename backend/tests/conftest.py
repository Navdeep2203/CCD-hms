"""Integration tests run against a real PostgreSQL database (default: hotel_test).

    createdb hotel_test            # once
    pytest                         # from backend/

Set TEST_DATABASE_NAME / DATABASE_USER / DATABASE_PASSWORD / DATABASE_HOST to point elsewhere.
WARNING: the test database is wiped and rebuilt for every test module.
"""
import itertools
import os

os.environ.setdefault("JWT_SECRET", "test-secret-for-automated-tests-0123456789abcdef")
os.environ["DATABASE_NAME"] = os.getenv("TEST_DATABASE_NAME", "hotel_test")
os.environ.setdefault("DATABASE_USER", "hotel_user")
os.environ.setdefault("DATABASE_PASSWORD", "hotel_password")

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import migrate
from app.database import _conninfo
from app.main import app
from app.routers import auth as auth_router

CREDENTIALS = {
    "admin": ("admin@hotel.com", "Admin@2026"),
    "manager": ("manager@hotel.com", "Manager@2026"),
    "staff": ("staff@hotel.com", "Staff@2026"),
    "customer": ("customer@hotel.com", "Guest@2026"),
}


def _reset_database() -> None:
    with psycopg.connect(_conninfo(), autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    migrate.run(seed=True)


@pytest.fixture(scope="module")
def client():
    _reset_database()
    auth_router._attempts.clear()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def tokens(client):
    result = {}
    for role, (email, password) in CREDENTIALS.items():
        response = client.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        result[role] = response.json()
    return result


@pytest.fixture(scope="module")
def H(tokens):
    """H('admin') -> Authorization headers for that seeded role."""
    return lambda role: {"Authorization": f"Bearer {tokens[role]['access_token']}"}


@pytest.fixture(scope="module")
def customer_id(tokens):
    return tokens["customer"]["user"]["customer_id"]


_room_numbers = itertools.count(900)


@pytest.fixture(scope="module")
def new_room(client, H):
    """Factory: create a brand-new AVAILABLE room so tests never collide on dates."""
    def make():
        types = client.get("/api/rooms/types", headers=H("admin")).json()
        response = client.post(
            "/api/rooms",
            headers=H("admin"),
            json={"room_number": next(_room_numbers), "room_type_id": types[0]["room_type_id"], "floor": 9},
        )
        assert response.status_code == 201, response.text
        return response.json()["room_id"]
    return make


def login(client, email, password):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    return response


def headers_for(response):
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
