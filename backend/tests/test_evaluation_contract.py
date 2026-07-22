"""응답 계약 검증.

fixture 는 프론트가 화면을 그리는 유일한 근거다.
숫자끼리 어긋나면 대시보드가 서로 모순되는 값을 동시에 보여준다
("실패 22건"이라고 써놓고 표에는 19건이 뜨는 식).
그래서 스키마 통과 여부만이 아니라 **수치 간 정합성**까지 여기서 잠근다.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.schemas.evaluation import (
    EvaluationReport,
    FailureCategory,
    Grade,
    Priority,
    QuestionType,
    SearchMode,
)

client = TestClient(app)

FIXTURE_PATH: Path = settings.fixture_dir / "eval_A492.json"


@pytest.fixture(scope="module")
def raw() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report(raw: dict[str, Any]) -> EvaluationReport:
    return EvaluationReport.model_validate(raw)


# ---------------------------------------------------------------------------
# 스키마
# ---------------------------------------------------------------------------


def test_fixture_validates(report: EvaluationReport) -> None:
    assert report.trace_id == "A492"


def test_fixture_is_written_in_camel_case(raw: dict[str, Any]) -> None:
    """fixture 는 계약 그대로 camelCase 로 적는다."""
    assert "traceId" in raw
    assert "trace_id" not in raw


def test_extra_fields_are_rejected(raw: dict[str, Any]) -> None:
    """계약에 없는 필드가 조용히 흘러 들어가면 안 된다."""
    polluted = {**raw, "unknownField": 1}
    with pytest.raises(ValueError):
        EvaluationReport.model_validate(polluted)


def test_ratios_are_percentages_not_fractions() -> None:
    """0~1 소수 금지. 0.78 을 78% 로 착각해 넣는 사고를 막는다."""
    with pytest.raises(ValueError):
        EvaluationReport.model_validate({})  # 형태 자체가 틀리면 당연히 실패

    from app.schemas.evaluation import EvaluationSummary

    with pytest.raises(ValueError):
        EvaluationSummary.model_validate(
            {
                "totalQuestions": 100,
                "top1Accuracy": 61.0,
                "top3Accuracy": 178.0,  # 100 초과
                "top1FailCount": 39,
                "top3FailCount": 22,
                "grade": "NEEDS_IMPROVEMENT",
            }
        )


# ---------------------------------------------------------------------------
# 수치 정합성
# ---------------------------------------------------------------------------


def test_question_type_counts_sum_to_total(report: EvaluationReport) -> None:
    assert sum(t.count for t in report.question_types) == report.summary.total_questions


def test_all_seven_question_types_present(report: EvaluationReport) -> None:
    assert {t.type for t in report.question_types} == set(QuestionType)


def test_question_type_ratio_matches_count(report: EvaluationReport) -> None:
    total = report.summary.total_questions
    for stat in report.question_types:
        expected = round(stat.count / total * 100, 1)
        assert stat.ratio == pytest.approx(expected), stat.type


def test_failure_count_matches_summary(report: EvaluationReport) -> None:
    assert len(report.failures) == report.summary.top3_fail_count


def test_top3_accuracy_matches_fail_count(report: EvaluationReport) -> None:
    total = report.summary.total_questions
    hits = total - report.summary.top3_fail_count
    assert report.summary.top3_accuracy == pytest.approx(round(hits / total * 100, 1))


def test_top1_is_never_better_than_top3(report: EvaluationReport) -> None:
    assert report.summary.top1_accuracy <= report.summary.top3_accuracy
    assert report.summary.top1_fail_count >= report.summary.top3_fail_count


def test_per_type_accuracy_matches_actual_failures(report: EvaluationReport) -> None:
    """유형별 인식률이 실패 목록에서 실제로 재구성되는지 확인한다.

    이게 어긋나면 도넛 차트와 실패 테이블이 서로 다른 이야기를 하게 된다.
    """
    failures_by_type = Counter(f.question_type for f in report.failures)
    for stat in report.question_types:
        hits = stat.count - failures_by_type[stat.type]
        expected = round(hits / stat.count * 100, 1)
        assert stat.top3_accuracy == pytest.approx(expected), stat.type


def test_grade_matches_top3_accuracy(report: EvaluationReport) -> None:
    """등급 기준 (contract.md §3): <70 CRITICAL / 70~85 NEEDS_IMPROVEMENT / 85~95 FAIR / >=95 GOOD."""
    accuracy = report.summary.top3_accuracy
    if accuracy < 70:
        expected = Grade.CRITICAL
    elif accuracy < 85:
        expected = Grade.NEEDS_IMPROVEMENT
    elif accuracy < 95:
        expected = Grade.FAIR
    else:
        expected = Grade.GOOD
    assert report.summary.grade == expected


# ---------------------------------------------------------------------------
# 실패 목록
# ---------------------------------------------------------------------------


def test_failure_ids_are_unique(report: EvaluationReport) -> None:
    ids = [f.id for f in report.failures]
    assert len(set(ids)) == len(ids)


def test_failures_are_all_misses(report: EvaluationReport) -> None:
    assert all(f.hit is False for f in report.failures)


def test_failure_results_are_ranked_from_one(report: EvaluationReport) -> None:
    for failure in report.failures:
        assert [r.rank for r in failure.results] == list(range(1, len(failure.results) + 1))


def test_failure_results_are_sorted_by_score(report: EvaluationReport) -> None:
    for failure in report.failures:
        scores = [r.score for r in failure.results]
        assert scores == sorted(scores, reverse=True), failure.id


def test_expected_api_is_not_inside_top_k(report: EvaluationReport) -> None:
    """실패인데 Top-K 안에 정답이 있으면 그건 실패가 아니다."""
    for failure in report.failures:
        found = {(r.method, r.path) for r in failure.results}
        assert (failure.expected.method, failure.expected.path) not in found, failure.id


def test_expected_rank_is_outside_top_k(report: EvaluationReport) -> None:
    """expectedRank 는 topK 보다 뒤여야 하고, 아예 못 찾았으면 null 이다."""
    top_k = report.meta.top_k
    for failure in report.failures:
        if failure.expected_rank is not None:
            assert failure.expected_rank > top_k, failure.id


def test_failures_concentrate_on_undocumented_endpoints(report: EvaluationReport) -> None:
    """설명이 없는(EMPTY) / 한 줄뿐인(POOR) 엔드포인트가 실패의 대부분이어야 한다.

    이 제품의 전제 자체다. GOOD 엔드포인트가 실패를 주도하면
    "설명을 보강하라"는 권장 조치의 근거가 사라진다.
    """
    empty = {
        ("DELETE", "/orders/{id}/refund"),
        ("GET", "/products/{id}/restock-schedule"),
    }
    poor = {
        ("POST", "/orders/{id}/refund"),
        ("PATCH", "/orders/{id}/shipping-address"),
        ("GET", "/products/{id}/stock"),
        ("PATCH", "/users/{id}/address"),
    }
    expected_apis = [(f.expected.method, f.expected.path) for f in report.failures]

    empty_or_poor = sum(1 for api in expected_apis if api in empty | poor)
    assert empty_or_poor / len(expected_apis) >= 0.8

    assert sum(1 for api in expected_apis if api in empty) >= 8


# ---------------------------------------------------------------------------
# 권장 조치 / previous
# ---------------------------------------------------------------------------


def test_recommendations_are_ordered(report: EvaluationReport) -> None:
    assert [r.order for r in report.recommendations] == [1, 2, 3]


def test_fail_share_may_exceed_one_hundred(report: EvaluationReport) -> None:
    """원인은 중복 집계된다. 합이 100을 넘는 것이 정상이며 화면에 각주가 필요하다."""
    assert sum(r.fail_share for r in report.recommendations) > 100


def test_previous_is_present_and_worse(report: EvaluationReport) -> None:
    assert report.previous is not None
    assert report.previous.trace_id == "A311"
    assert report.previous.top3_accuracy == 64.0


def test_previous_is_optional() -> None:
    """이전 평가가 없으면 null. 프론트는 델타 뱃지를 숨긴다."""
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    raw["previous"] = None
    assert EvaluationReport.model_validate(raw).previous is None


def test_expected_rank_is_optional() -> None:
    """Top-N 밖이면 null 이어야 한다. fixture 에 실제로 null 인 건이 있어야 프론트가 대비된다."""
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert any(f["expectedRank"] is None for f in raw["failures"])


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------


def test_enum_members_match_contract() -> None:
    assert set(Grade) == {"CRITICAL", "NEEDS_IMPROVEMENT", "FAIR", "GOOD"}
    assert set(Priority) == {"HIGH", "MEDIUM", "LOW"}
    assert set(SearchMode) == {"BM25", "VECTOR", "HYBRID"}
    assert set(QuestionType) == {
        "DIRECT",
        "USER_NL",
        "DOMAIN_TERM",
        "PARAMETER",
        "ERROR_CASE",
        "SHORT_KEYWORD",
        "MIXED_LANG",
    }
    assert set(FailureCategory) == {
        "METHOD_MISMATCH",
        "SIMILAR_RESOURCE",
        "SYNONYM_MISS",
        "DESCRIPTION_MISSING",
        "PARAM_MISSING",
        "OTHER",
    }


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_get_evaluation_returns_camel_case() -> None:
    res = client.get("/api/v1/evaluations/A492")
    assert res.status_code == 200

    body = res.json()
    assert body["traceId"] == "A492"
    assert body["summary"]["top3FailCount"] == 22
    assert body["meta"]["embeddingModel"] == "bge-m3"
    assert body["questionTypes"][0]["top3Accuracy"] == 95.5
    assert body["recommendations"][0]["failShare"] == 45.5
    assert body["failures"][0]["questionType"] == "DIRECT"
    assert body["previous"]["top3Accuracy"] == 64.0


def test_no_snake_case_leaks_into_response() -> None:
    res = client.get("/api/v1/evaluations/A492")
    assert "_" not in "".join(_all_keys(res.json()))


def _all_keys(node: Any) -> list[str]:
    if isinstance(node, dict):
        keys: list[str] = []
        for key, value in node.items():
            keys.append(key)
            keys.extend(_all_keys(value))
        return keys
    if isinstance(node, list):
        return [k for item in node for k in _all_keys(item)]
    return []


def test_unknown_trace_id_returns_404() -> None:
    res = client.get("/api/v1/evaluations/ZZZZ")
    assert res.status_code == 404


def test_malformed_trace_id_is_rejected() -> None:
    """trace_id 가 파일 경로가 되므로 형태를 강제한다."""
    res = client.get("/api/v1/evaluations/..%2F..%2Fetc%2Fpasswd")
    assert res.status_code in (404, 422)


def test_response_model_is_documented_in_openapi() -> None:
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/evaluations/{trace_id}"]["get"]
    assert operation["responses"]["200"]
    assert operation["responses"]["404"]

    # 프론트 타입은 이 스펙에서 생성된다. 필드 설명이 비면 생성물이 빈껍데기가 된다.
    report_schema = schema["components"]["schemas"]["EvaluationReport"]
    for name, field in report_schema["properties"].items():
        assert field.get("description") or field.get("allOf") or "$ref" in field, name
