"""Smoke test: la app levanta y el health endpoint responde.

Bootstrap de la suite (antes no existía tests/). La cobertura real todavía
está muy por debajo del umbral de CI; sumar tests por módulo es trabajo aparte.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok() -> None:
    with TestClient(app) as client:
        res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
