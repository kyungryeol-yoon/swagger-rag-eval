"""어댑터 경계의 계약 검증 (Phase 10).

외부 평가툴이 필드를 빠뜨리거나 형식이 어긋난 결과를 줄 수 있다.
그때 **조용히 통과시키지 않는 것**과, **어느 필드가 문제인지 말해 주는 것**이
여기서 잠그려는 두 가지다. 원본 JSON 을 고칠 사람은 이 시스템 밖에 있으므로
메시지만 보고 원본을 찾아갈 수 있어야 한다.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.adapter import ContractViolation, to_evaluation_report

client = TestClient(app)

FIXTURE_PATH: Path = settings.fixture_dir / "eval_q-lot-status.json"


@pytest.fixture
def raw() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_valid_payload_passes_through(raw: dict[str, Any]) -> None:
    assert to_evaluation_report(raw).target.query_id == "q-lot-status"


def test_missing_top_level_field_names_the_field(raw: dict[str, Any]) -> None:
    del raw["summary"]
    with pytest.raises(ContractViolation) as exc:
        to_evaluation_report(raw, source="eval_q-lot-status.json")

    message = str(exc.value)
    assert "summary" in message
    assert "필수 필드가 없습니다" in message
    # 어느 결과가 깨졌는지도 함께 나와야 고칠 데를 찾을 수 있다.
    assert "eval_q-lot-status.json" in message


def test_missing_nested_field_reports_full_path(raw: dict[str, Any]) -> None:
    del raw["summary"]["top3Accuracy"]
    with pytest.raises(ContractViolation) as exc:
        to_evaluation_report(raw)
    assert "summary.top3Accuracy" in str(exc.value)


def test_missing_field_inside_a_list_reports_the_index(raw: dict[str, Any]) -> None:
    del raw["questions"][3]["questionType"]
    with pytest.raises(ContractViolation) as exc:
        to_evaluation_report(raw)
    assert "questions[3].questionType" in str(exc.value)


def test_wrong_type_is_reported_with_the_given_value(raw: dict[str, Any]) -> None:
    raw["summary"]["totalQuestions"] = "백 개"
    with pytest.raises(ContractViolation) as exc:
        to_evaluation_report(raw)

    message = str(exc.value)
    assert "summary.totalQuestions" in message
    assert "백 개" in message


def test_out_of_range_ratio_is_rejected(raw: dict[str, Any]) -> None:
    """0~1 소수를 퍼센트 자리에 넣는 사고는 범위로 못 막는다. 반대쪽(초과)만 막힌다."""
    raw["summary"]["top3Accuracy"] = 178.0
    with pytest.raises(ContractViolation) as exc:
        to_evaluation_report(raw)
    assert "summary.top3Accuracy" in str(exc.value)


def test_unknown_field_is_rejected(raw: dict[str, Any]) -> None:
    """계약에 없는 필드가 조용히 흘러 들어가면 안 된다."""
    raw["unknownField"] = 1
    with pytest.raises(ContractViolation) as exc:
        to_evaluation_report(raw)
    assert "계약에 없는 필드입니다" in str(exc.value)


def test_non_object_payload_is_rejected() -> None:
    with pytest.raises(ContractViolation):
        to_evaluation_report([])  # type: ignore[arg-type]


def test_many_errors_are_truncated(raw: dict[str, Any]) -> None:
    """필드 하나가 통째로 빠지면 하위 오류가 수십 개 딸려 온다. 첫 줄이 밀리면 안 된다."""
    raw["questions"] = [{} for _ in range(50)]
    with pytest.raises(ContractViolation) as exc:
        to_evaluation_report(raw)
    assert len(exc.value.problems) <= 13  # 상한 12 + "… 외 N건" 한 줄


def test_optional_fields_may_be_absent(raw: dict[str, Any]) -> None:
    """target 의 선택 필드는 null 로 와도 통과해야 한다."""
    raw["target"]["appId"] = None
    raw["target"]["summary"] = None
    raw["target"]["description"] = None
    for question in raw["questions"]:
        question["top3"] = None
        question["top1Hit"] = False
        question["top3Hit"] = False
        question["failureScope"] = "TOP3"
        question["expectedRank"] = None
        question["failureCategory"] = "OTHER"
        question["reason"] = "결과 없음"

    report = to_evaluation_report(raw)
    assert report.target.app_id is None
    assert report.target.summary is None
    assert report.target.description is None
    assert all(q.top3 is None for q in report.questions)


def test_optional_fields_may_be_omitted_entirely(raw: dict[str, Any]) -> None:
    """null 이 아니라 키 자체가 없는 경우도 통과해야 한다."""
    del raw["target"]["appId"]
    del raw["target"]["summary"]
    del raw["target"]["description"]

    report = to_evaluation_report(raw)
    assert report.target.app_id is None
    assert report.target.summary is None
    assert report.target.description is None


def test_x_questions_is_required(raw: dict[str, Any]) -> None:
    """빈 배열은 되지만 **생략은 안 된다** (contract.md §2 필드 규약).

    기본값을 두면 프론트 타입이 `string[] | undefined` 가 되어 화면마다
    방어 코드가 붙는다. "항상 배열" 을 타입으로 보장하려면 필수여야 한다.
    """
    raw["target"]["xQuestions"] = []
    assert to_evaluation_report(raw).target.x_questions == []

    del raw["target"]["xQuestions"]
    with pytest.raises(ContractViolation) as exc:
        to_evaluation_report(raw)
    assert "target.xQuestions" in str(exc.value)


# ---------------------------------------------------------------------------
# 저장소 → API 경로에서도 같은 검증이 걸리는지
# ---------------------------------------------------------------------------


def test_repository_routes_through_the_adapter(tmp_path: Path) -> None:
    """저장소가 직접 model_validate 하면 이 검증이 우회된다."""
    from app.adapters.local.file_spec_repository import FileSpecRepository

    broken = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    del broken["target"]["path"]
    (tmp_path / "eval_q-broken.json").write_text(
        json.dumps(broken, ensure_ascii=False), encoding="utf-8"
    )

    repository = FileSpecRepository(tmp_path)
    with pytest.raises(ContractViolation) as exc:
        repository.evaluate("q-broken")

    assert "target.path" in str(exc.value)
    assert "eval_q-broken.json" in str(exc.value)


def test_contract_violation_returns_500_with_the_reason(tmp_path: Path) -> None:
    """계약이 깨진 결과를 200 으로 내보내면 화면이 반쯤 그려진다. 500 이어야 한다."""
    from app.adapters.local.file_spec_repository import FileSpecRepository
    from app.api.deps import get_spec_repository

    broken = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    del broken["summary"]["top3Grade"]
    (tmp_path / "eval_q-broken.json").write_text(
        json.dumps(broken, ensure_ascii=False), encoding="utf-8"
    )

    app.dependency_overrides[get_spec_repository] = lambda: FileSpecRepository(tmp_path)
    try:
        # 예외 핸들러의 응답을 보려면 TestClient 가 예외를 되던지지 않아야 한다.
        with TestClient(app, raise_server_exceptions=False) as local:
            res = local.post("/api/v1/evaluations", json={"query_id": "q-broken"})
    finally:
        app.dependency_overrides.clear()

    assert res.status_code == 500
    body = res.json()
    assert body["source"] == "eval_q-broken.json"
    assert any("summary.top3Grade" in problem for problem in body["problems"])


def test_question_count_mismatch_is_a_contract_violation(raw: dict[str, Any]) -> None:
    """세 자리에 있는 질문 수가 어긋나면 어댑터가 잡아 준다."""
    raw["summary"]["totalQuestions"] = 42
    with pytest.raises(ContractViolation) as exc:
        to_evaluation_report(raw)
    assert "질문 수가 서로 다릅니다" in str(exc.value)
