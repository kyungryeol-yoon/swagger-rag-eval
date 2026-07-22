from fastapi.testclient import TestClient

from app.api.deps import get_spec_repository
from app.core.config import Settings
from app.main import app
from app.schemas.evaluation import EvaluationReport

client = TestClient(app)


def test_health() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_cors_allows_dashboard_origin() -> None:
    res = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert res.headers["access-control-allow-origin"] == "http://localhost:3000"


# ---------------------------------------------------------------------------
# CORS 설정
# ---------------------------------------------------------------------------


def test_cors_origins_parses_comma_separated_value() -> None:
    settings = Settings(CORS_ORIGINS="https://a.example.com,https://b.example.com")
    assert settings.cors_origins == ["https://a.example.com", "https://b.example.com"]


def test_cors_origins_tolerates_spaces_and_trailing_commas() -> None:
    settings = Settings(CORS_ORIGINS=" https://a.example.com , , https://b.example.com ,")
    assert settings.cors_origins == ["https://a.example.com", "https://b.example.com"]


def test_cors_origins_defaults_to_localhost() -> None:
    assert Settings().cors_origins == ["http://localhost:3000"]


# ---------------------------------------------------------------------------
# 레디니스
# ---------------------------------------------------------------------------


class _EmptyRepository:
    def get_evaluation(self, trace_id: str) -> EvaluationReport | None:
        return None

    def get_spec(self, spec_id: str) -> dict[str, object] | None:
        return None


class _BrokenRepository:
    def get_evaluation(self, trace_id: str) -> EvaluationReport | None:
        raise OSError("저장소에 닿지 못했습니다")

    def get_spec(self, spec_id: str) -> dict[str, object] | None:
        raise OSError("저장소에 닿지 못했습니다")


def test_ready_returns_200_when_data_is_readable() -> None:
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"


def test_ready_returns_503_when_data_is_missing() -> None:
    app.dependency_overrides[get_spec_repository] = _EmptyRepository
    try:
        res = client.get("/ready")
        assert res.status_code == 503
        assert res.json()["status"] == "not_ready"
    finally:
        app.dependency_overrides.clear()


def test_ready_returns_503_when_storage_raises() -> None:
    """저장소가 터져도 500 이 아니라 503 이어야 트래픽에서 빠진다."""
    app.dependency_overrides[get_spec_repository] = _BrokenRepository
    try:
        res = client.get("/ready")
        assert res.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_health_stays_up_even_when_storage_is_broken() -> None:
    """liveness 는 데이터 소스와 무관해야 한다. 아니면 불필요한 재시작을 부른다."""
    app.dependency_overrides[get_spec_repository] = _BrokenRepository
    try:
        assert client.get("/health").status_code == 200
    finally:
        app.dependency_overrides.clear()
