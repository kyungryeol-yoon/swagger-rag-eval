"""Port 격리 검증.

사내 이식의 전제는 "구현체를 갈아끼워도 나머지 코드가 그대로"다.
그 전제가 실제로 성립하는지를 여기서 확인한다.
가짜 저장소를 주입했을 때 라우터가 그대로 동작하지 않으면
사내에서 DB 어댑터로 바꾸는 순간 라우터까지 헤집게 된다.
"""

import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.adapters.local.file_spec_repository import FileSpecRepository
from app.api import deps
from app.api.v1 import evaluations as evaluations_module
from app.api.deps import get_spec_repository
from app.core.config import settings
from app.main import app
from app.ports.auth import AuthProvider, User
from app.ports.llm import Embedder, LLMClient
from app.ports.spec_repository import SpecRepository
from app.schemas.evaluation import EvaluationReport

client = TestClient(app)


@pytest.fixture
def report() -> EvaluationReport:
    payload = json.loads((settings.fixture_dir / "eval_A492.json").read_text(encoding="utf-8"))
    return EvaluationReport.model_validate(payload)


# ---------------------------------------------------------------------------
# 경계가 지켜지는가
# ---------------------------------------------------------------------------


def test_router_does_not_import_adapters() -> None:
    """라우터가 구현체를 직접 알면 Port를 둔 의미가 없다."""
    source = inspect.getsource(evaluations_module)
    assert "adapters" not in source
    assert "FileSpecRepository" not in source


def test_deps_is_the_only_composition_root() -> None:
    """구현체를 import 하는 곳은 deps.py 하나여야 한다."""
    assert "FileSpecRepository" in inspect.getsource(deps)


def test_local_adapter_satisfies_the_protocol() -> None:
    repository = FileSpecRepository(settings.fixture_dir)
    assert isinstance(repository, SpecRepository)


def test_port_protocols_expose_expected_signatures() -> None:
    """구현이 비어 있는 Port도 시그니처는 고정돼 있어야 한다."""
    assert set(SpecRepository.__protocol_attrs__) == {"get_evaluation", "get_spec"}
    assert set(AuthProvider.__protocol_attrs__) == {"get_current_user"}
    assert set(LLMClient.__protocol_attrs__) == {"complete"}
    assert set(Embedder.__protocol_attrs__) == {"embed"}


def test_unimplemented_ports_have_no_consumers_yet() -> None:
    """auth / llm 은 시그니처만 있다. 소비자가 생기기 전에 구현을 만들지 않는다."""
    app_dir = Path(__file__).resolve().parents[1] / "app"
    importers = [
        path.name
        for path in app_dir.rglob("*.py")
        if path.name not in {"auth.py", "llm.py"}
        and any(
            marker in path.read_text(encoding="utf-8")
            for marker in ("ports.auth", "ports.llm")
        )
    ]
    assert importers == []


def test_user_model_is_defined_for_future_auth() -> None:
    user = User(id="u1", name="윤")
    assert user.email is None


# ---------------------------------------------------------------------------
# 주입이 실제로 갈아끼워지는가
# ---------------------------------------------------------------------------


class FakeSpecRepository:
    """파일 시스템을 전혀 쓰지 않는 저장소. Protocol 만 만족한다."""

    def __init__(self, report: EvaluationReport | None) -> None:
        self._report = report
        self.seen: list[str] = []

    def get_evaluation(self, trace_id: str) -> EvaluationReport | None:
        self.seen.append(trace_id)
        return self._report

    def get_spec(self, spec_id: str) -> dict[str, Any] | None:
        return {"openapi": "3.1.0", "info": {"title": spec_id}}


def test_fake_repository_satisfies_the_protocol(report: EvaluationReport) -> None:
    assert isinstance(FakeSpecRepository(report), SpecRepository)


def test_endpoint_works_with_an_injected_fake(report: EvaluationReport) -> None:
    """가짜 저장소를 주입해도 라우터는 그대로 동작한다."""
    fake = FakeSpecRepository(report)
    app.dependency_overrides[get_spec_repository] = lambda: fake
    try:
        res = client.get("/api/v1/evaluations/A492")
        assert res.status_code == 200
        assert res.json()["traceId"] == "A492"
        assert fake.seen == ["A492"]
    finally:
        app.dependency_overrides.clear()


def test_endpoint_serves_whatever_the_repository_returns(report: EvaluationReport) -> None:
    """저장소가 파일이 아니어도 된다는 것을 보인다. 응답은 저장소가 준 값 그대로."""
    renamed = report.model_copy(update={"trace_id": "B001"})
    app.dependency_overrides[get_spec_repository] = lambda: FakeSpecRepository(renamed)
    try:
        res = client.get("/api/v1/evaluations/B001")
        assert res.status_code == 200
        assert res.json()["traceId"] == "B001"
    finally:
        app.dependency_overrides.clear()


def test_endpoint_returns_404_when_repository_has_nothing() -> None:
    """404 판단은 라우터가 한다. 저장소는 None 만 돌려준다."""
    app.dependency_overrides[get_spec_repository] = lambda: FakeSpecRepository(None)
    try:
        res = client.get("/api/v1/evaluations/A492")
        assert res.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 로컬 어댑터
# ---------------------------------------------------------------------------


def test_file_repository_reads_the_fixture() -> None:
    repository = FileSpecRepository(settings.fixture_dir)
    found = repository.get_evaluation("A492")
    assert found is not None
    assert found.trace_id == "A492"


def test_file_repository_returns_none_for_missing_evaluation() -> None:
    repository = FileSpecRepository(settings.fixture_dir)
    assert repository.get_evaluation("NOPE") is None


def test_file_repository_reads_the_dumped_openapi_spec() -> None:
    """Phase 2 의 `make dump-spec` 산출물을 읽는다. 없으면 건너뛴다."""
    repository = FileSpecRepository(settings.fixture_dir)
    spec = repository.get_spec("openapi_sample")
    if spec is None:
        pytest.skip("openapi_sample.json 이 없다. `make dump-spec` 을 먼저 실행할 것")
    assert spec["info"]["title"] == "Sample Commerce API"


def test_file_repository_returns_none_for_missing_spec() -> None:
    repository = FileSpecRepository(settings.fixture_dir)
    assert repository.get_spec("no_such_spec") is None


@pytest.mark.parametrize("bad_id", ["../secrets", "a/b", "", "x" * 65])
def test_file_repository_rejects_unsafe_ids(bad_id: str) -> None:
    """HTTP를 거치지 않고 직접 호출될 수 있으므로 저장소가 스스로 막아야 한다."""
    repository = FileSpecRepository(settings.fixture_dir)
    with pytest.raises(ValueError):
        repository.get_spec(bad_id)
    with pytest.raises(ValueError):
        repository.get_evaluation(bad_id)
