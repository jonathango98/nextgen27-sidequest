from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_dec_029_health_returns_plain_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.text == "ok"
    assert response.headers["content-type"].startswith("text/plain")


def test_api_001_builtin_docs_routes_are_off():
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404
