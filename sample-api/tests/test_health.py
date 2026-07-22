from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_openapi_is_generated() -> None:
    """이 앱의 산출물은 openapi.json 이다. 항상 생성 가능해야 한다."""
    res = client.get("/openapi.json")
    assert res.status_code == 200
    assert res.json()["info"]["title"] == "Sample Commerce API"
