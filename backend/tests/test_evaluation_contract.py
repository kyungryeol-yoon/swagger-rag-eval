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
                "top1Grade": "CRITICAL",
                "top3Grade": "NEEDS_IMPROVEMENT",
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


def test_top3_accuracy_matches_fail_count(report: EvaluationReport) -> None:
    total = report.summary.total_questions
    hits = total - report.summary.top3_fail_count
    assert report.summary.top3_accuracy == pytest.approx(round(hits / total * 100, 1))


def test_top1_is_never_better_than_top3(report: EvaluationReport) -> None:
    assert report.summary.top1_accuracy <= report.summary.top3_accuracy
    assert report.summary.top1_fail_count >= report.summary.top3_fail_count


def test_per_type_accuracy_matches_actual_questions(report: EvaluationReport) -> None:
    """유형별 인식률이 문항 목록에서 실제로 재구성되는지 확인한다.

    이게 어긋나면 도넛 차트와 문항 표가 서로 다른 이야기를 하게 된다.
    """
    total_by_type = Counter(q.question_type for q in report.questions)
    top3_fail_by_type = Counter(
        q.question_type for q in report.questions if not q.top3_hit
    )
    for stat in report.question_types:
        assert total_by_type[stat.type] == stat.count, stat.type
        hits = stat.count - top3_fail_by_type[stat.type]
        expected = round(hits / stat.count * 100, 1)
        assert stat.top3_accuracy == pytest.approx(expected), stat.type


def _grade_for(accuracy: float) -> Grade:
    """등급 기준 (contract.md §3): <70 CRITICAL / 70~85 NEEDS_IMPROVEMENT / 85~95 FAIR / >=95 GOOD."""
    if accuracy < 70:
        return Grade.CRITICAL
    if accuracy < 85:
        return Grade.NEEDS_IMPROVEMENT
    if accuracy < 95:
        return Grade.FAIR
    return Grade.GOOD


def test_grades_match_accuracy(report: EvaluationReport) -> None:
    """Top-1 / Top-3 등급이 각 지표에서 산출된다.

    현재는 두 지표의 임계값이 같다(open-questions #54). 달라지면 이 헬퍼가
    지표별로 갈라져야 한다.
    """
    assert report.summary.top1_grade == _grade_for(report.summary.top1_accuracy)
    assert report.summary.top3_grade == _grade_for(report.summary.top3_accuracy)


# ---------------------------------------------------------------------------
# 문항 100개 전체
# ---------------------------------------------------------------------------


def test_questions_count_matches_total(report: EvaluationReport) -> None:
    assert len(report.questions) == report.summary.total_questions


def test_question_numbers_are_unique_1_to_100(report: EvaluationReport) -> None:
    nos = sorted(q.no for q in report.questions)
    assert nos == list(range(1, report.summary.total_questions + 1))


def test_scope_counts_match_summary(report: EvaluationReport) -> None:
    """실패 범위별 개수가 summary 의 실패 수와 정합해야 한다.

    top1FailCount = TOP1_ONLY + TOP3, top3FailCount = TOP3.
    """
    from app.schemas.evaluation import FailureScope

    scopes = Counter(q.failure_scope for q in report.questions)
    top3_fail = scopes[FailureScope.TOP3]
    top1_fail = scopes[FailureScope.TOP1_ONLY] + scopes[FailureScope.TOP3]

    assert top3_fail == report.summary.top3_fail_count
    assert top1_fail == report.summary.top1_fail_count
    assert scopes[FailureScope.NONE] == (
        report.summary.total_questions - top1_fail
    )


def test_hit_flags_agree_with_scope(report: EvaluationReport) -> None:
    """top1Hit / top3Hit 이 failureScope 와 모순되지 않아야 한다."""
    from app.schemas.evaluation import FailureScope

    for q in report.questions:
        if q.failure_scope == FailureScope.NONE:
            assert q.top1_hit and q.top3_hit, q.no
        elif q.failure_scope == FailureScope.TOP1_ONLY:
            assert not q.top1_hit and q.top3_hit, q.no
        else:
            assert not q.top1_hit and not q.top3_hit, q.no


def test_accuracy_matches_hit_flags(report: EvaluationReport) -> None:
    total = report.summary.total_questions
    top1_hits = sum(1 for q in report.questions if q.top1_hit)
    top3_hits = sum(1 for q in report.questions if q.top3_hit)
    assert report.summary.top1_accuracy == pytest.approx(round(top1_hits / total * 100, 1))
    assert report.summary.top3_accuracy == pytest.approx(round(top3_hits / total * 100, 1))


def test_success_questions_have_no_failure_fields(report: EvaluationReport) -> None:
    """성공(NONE)이면 failureCategory 와 reason 이 null 이다."""
    from app.schemas.evaluation import FailureScope

    for q in report.questions:
        if q.failure_scope == FailureScope.NONE:
            assert q.failure_category is None and q.reason is None, q.no
        else:
            assert q.failure_category is not None and q.reason is not None, q.no


def test_top3_is_ranked_and_sorted(report: EvaluationReport) -> None:
    for q in report.questions:
        assert [r.rank for r in q.top3] == list(range(1, len(q.top3) + 1)), q.no
        scores = [r.score for r in q.top3]
        assert scores == sorted(scores, reverse=True), q.no


def test_top1_agrees_with_top3_head(report: EvaluationReport) -> None:
    """top1 은 top3 의 1위와 같은 쿼리여야 한다."""
    for q in report.questions:
        head = q.top3[0]
        assert (q.top1.method, q.top1.path) == (head.method, head.path), q.no


def test_hit_flags_agree_with_results(report: EvaluationReport) -> None:
    for q in report.questions:
        exp = (q.expected.method, q.expected.path)
        assert (q.top1_hit) == ((q.top1.method, q.top1.path) == exp), q.no
        in_top3 = exp in {(r.method, r.path) for r in q.top3}
        assert q.top3_hit == in_top3, q.no


def test_questions_are_sorted_top3_top1_none(report: EvaluationReport) -> None:
    """정렬: TOP3 → TOP1_ONLY → NONE, 그 안에서 no 오름차순."""
    from app.schemas.evaluation import FailureScope

    order = {FailureScope.TOP3: 0, FailureScope.TOP1_ONLY: 1, FailureScope.NONE: 2}
    keys = [(order[q.failure_scope], q.no) for q in report.questions]
    assert keys == sorted(keys)


def test_failures_concentrate_on_undocumented_queries(report: EvaluationReport) -> None:
    """설명이 없는(EMPTY) / 한 줄뿐인(POOR) 쿼리가 완전 실패의 대부분이어야 한다.

    이 제품의 전제 자체다. 경로는 fixture 도메인에 종속되므로 fixture 를 바꾸면
    이 목록도 함께 갱신해야 검증이 유지된다.
    """
    from app.schemas.evaluation import FailureScope

    empty = {
        ("GET", "/queries/step-cycle-time"),
        ("GET", "/queries/operator-shift"),
        ("POST", "/queries/chamber-sensor-trend"),
    }
    poor = {
        ("GET", "/queries/equipment-downtime"),
        ("GET", "/queries/recipe-history"),
        ("POST", "/queries/alarm-history"),
    }
    top3_fails = [
        (q.expected.method, q.expected.path)
        for q in report.questions
        if q.failure_scope == FailureScope.TOP3
    ]

    empty_or_poor = sum(1 for q in top3_fails if q in empty | poor)
    assert empty_or_poor / len(top3_fails) >= 0.8
    assert sum(1 for q in top3_fails if q in empty) >= 8


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
    assert any(q["expectedRank"] is None for q in raw["questions"])


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
        "SIMILAR_RESOURCE",
        "DESCRIPTION_MISSING",
        "DESCRIPTION_WEAK",
        "KEYWORD_MISMATCH",
        "DOMAIN_TERM_MISSING",
        "ERROR_CASE_MISSING",
        "PARAM_MISSING",
        "METHOD_MISMATCH",
        "OTHER",
    }

    from app.schemas.evaluation import FailureScope

    assert set(FailureScope) == {"NONE", "TOP1_ONLY", "TOP3"}


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
    assert body["summary"]["top1Grade"]
    assert body["summary"]["top3Grade"]
    assert body["questions"][0]["failureScope"] == "TOP3"
    assert body["questions"][0]["top1Hit"] is False
    assert body["meta"]["rawSource"]["toolVersion"]
    assert body["previous"]["top3Accuracy"] == 64.0
    assert body["target"]["appId"] == "mf-worker"
    assert body["target"]["queryCount"] == 11
    assert body["queries"][0]["descriptionLength"] == 168
    assert body["queries"][0]["hasParamDescription"] is True
    # 설명 없는 EMPTY 쿼리는 재생성 후보다. 첫 needsRegeneration 쿼리로 확인한다.
    assert any(q["needsRegeneration"] is True for q in body["queries"])
    assert body["queries"][8]["needsRegeneration"] is True


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


# ---------------------------------------------------------------------------
# 평가 대상 앱 / 쿼리
# ---------------------------------------------------------------------------


def test_target_is_an_app_not_a_single_query(report: EvaluationReport) -> None:
    """평가 단위는 쿼리 하나가 아니라 DAC 앱 하나다 (contract.md §0)."""
    assert report.target.app_id == "mf-worker"
    assert report.target.spec_version
    assert report.target.query_count > 0


def test_query_count_matches_queries_length(report: EvaluationReport) -> None:
    """헤더의 쿼리 수와 실제 목록이 어긋나면 화면이 서로 다른 말을 한다."""
    assert report.target.query_count == len(report.queries)


def test_query_question_counts_sum_to_total(report: EvaluationReport) -> None:
    assert (
        sum(q.question_count for q in report.queries) == report.summary.total_questions
    )


def test_query_accuracy_matches_actual_questions(report: EvaluationReport) -> None:
    """쿼리별 인식률이 문항 목록에서 실제로 재구성되는지 확인한다.

    어긋나면 쿼리 표와 문항 표가 서로 다른 이야기를 하게 된다.
    """
    total_by_query = Counter((q.expected.method, q.expected.path) for q in report.questions)
    top3_fail_by_query = Counter(
        (q.expected.method, q.expected.path) for q in report.questions if not q.top3_hit
    )
    for query in report.queries:
        key = (query.method, query.path)
        assert total_by_query[key] == query.question_count, f"{query.method} {query.path}"
        hits = query.question_count - top3_fail_by_query[key]
        expected = round(hits / query.question_count * 100, 1)
        assert query.top3_accuracy == pytest.approx(expected), f"{query.method} {query.path}"


def test_query_grade_matches_its_accuracy(report: EvaluationReport) -> None:
    for query in report.queries:
        assert query.grade == _grade_for(query.top3_accuracy), query.path


def test_queries_are_unique(report: EvaluationReport) -> None:
    """같은 경로라도 메서드가 다르면 다른 쿼리다."""
    keys = [(q.method, q.path) for q in report.queries]
    assert len(set(keys)) == len(keys)


def test_every_expected_query_exists_in_queries(report: EvaluationReport) -> None:
    """모든 문항의 기대 쿼리는 쿼리 목록에 있어야 한다."""
    known = {(q.method, q.path) for q in report.queries}
    for question in report.questions:
        assert (question.expected.method, question.expected.path) in known, question.no


def test_queries_without_description_need_regeneration(report: EvaluationReport) -> None:
    """설명이 아예 없는 쿼리는 재생성 후보여야 한다.

    이게 무너지면 "부실한 쿼리를 자동 생성 서비스로 넘긴다"는 이 제품의
    목적 자체가 성립하지 않는다.
    """
    empty = [q for q in report.queries if q.description_length == 0 and q.summary is None]
    assert len(empty) >= 2
    for query in empty:
        assert query.needs_regeneration, f"{query.method} {query.path}"


def test_regeneration_candidates_are_backend_decided(report: EvaluationReport) -> None:
    """프론트가 인식률로 다시 계산하지 않도록, 후보는 응답에 들어 있어야 한다."""
    assert any(q.needs_regeneration for q in report.queries)
    assert not all(q.needs_regeneration for q in report.queries)
