"""응답 계약 검증 (Phase 12 — 쿼리 1개 단위, 무상태).

fixture 는 프론트가 화면을 그리는 유일한 근거다. 숫자끼리 어긋나면 대시보드가
서로 모순되는 값을 동시에 보여준다 ("실패 22건"이라고 써놓고 표에는 19건이
뜨는 식). 그래서 스키마 통과 여부만이 아니라 **수치 간 정합성**까지 여기서 잠근다.

fixture 는 `app/scripts/make_fixtures.py` 가 만든다. 계약이 바뀌면 그 스크립트를
다시 돌리고 결과 JSON 을 함께 커밋한다.
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
    FailureScope,
    Grade,
    Priority,
    QuestionType,
    SearchMode,
)

client = TestClient(app)

# 기준 fixture — 설명이 충실하고 성공·실패가 섞인 정상 상태.
NORMAL_QUERY_ID = "q-lot-status"

# 각 fixture 가 대표하는 경계. 공통 정합성은 전부가 지켜야 한다.
ALL_QUERY_IDS = [
    NORMAL_QUERY_ID,
    "q-step-cycle-time",  # 설명 없음, 인식률 매우 낮음
    "q-wafer-yield",  # 인식률 100%
    "q-no-result",  # top3 가 null 인 문항 다수
    "q-wafer-defect-daily-aggregation-by-step-line-equipment-shift",  # 초장문
]


def path_of(query_id: str) -> Path:
    return settings.fixture_dir / f"eval_{query_id}.json"


def load(query_id: str) -> EvaluationReport:
    return EvaluationReport.model_validate(
        json.loads(path_of(query_id).read_text(encoding="utf-8"))
    )


@pytest.fixture(scope="module")
def raw() -> dict[str, Any]:
    return json.loads(path_of(NORMAL_QUERY_ID).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report() -> EvaluationReport:
    return load(NORMAL_QUERY_ID)


def grade_for(accuracy: float) -> Grade:
    """등급 기준 (contract.md §3): <70 CRITICAL / 70~85 NEEDS / 85~95 FAIR / >=95 GOOD."""
    if accuracy < 70:
        return Grade.CRITICAL
    if accuracy < 85:
        return Grade.NEEDS_IMPROVEMENT
    if accuracy < 95:
        return Grade.FAIR
    return Grade.GOOD


# ---------------------------------------------------------------------------
# 스키마
# ---------------------------------------------------------------------------


def test_fixture_validates(report: EvaluationReport) -> None:
    assert report.target.query_id == NORMAL_QUERY_ID


def test_fixture_is_written_in_camel_case(raw: dict[str, Any]) -> None:
    assert "traceId" in raw
    assert "trace_id" not in raw
    assert "queryId" in raw["target"]


def test_extra_fields_are_rejected(raw: dict[str, Any]) -> None:
    """계약에 없는 필드가 조용히 흘러 들어가면 안 된다."""
    with pytest.raises(ValueError):
        EvaluationReport.model_validate({**raw, "unknownField": 1})


def test_removed_fields_are_actually_gone(raw: dict[str, Any]) -> None:
    """Phase 12 에서 뺀 필드가 fixture 에 남아 있으면 extra=forbid 로 터진다.

    그 전에 여기서 잡아 "무엇을 뺐는지" 를 이름으로 명시해 둔다.
    """
    assert "queries" not in raw
    assert "previous" not in raw
    assert "rawSource" not in raw["meta"]
    assert "questionSource" not in raw["meta"]
    for question in raw["questions"]:
        assert "expected" not in question
        assert "top1" not in question
    for absent in ("appName", "specVersion", "queryCount", "owner"):
        assert absent not in raw["target"]


def test_ratios_are_percentages_not_fractions() -> None:
    """0~1 소수 금지. 0.78 을 78% 로 착각해 넣는 사고를 막는다."""
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
# 평가 대상 — 쿼리 하나
# ---------------------------------------------------------------------------


def test_target_is_a_single_query(report: EvaluationReport) -> None:
    """평가 단위는 앱이 아니라 쿼리 하나다 (contract.md §0)."""
    assert report.target.query_id
    assert report.target.method
    assert report.target.path


def test_target_carries_its_own_description(report: EvaluationReport) -> None:
    """설명을 화면에 그대로 보여주는 것이 이 계약의 목적 중 하나다."""
    assert report.target.summary
    assert report.target.description
    assert report.target.x_questions


def test_x_questions_is_a_list_never_null() -> None:
    """없으면 빈 배열이다. 프론트가 `?.length` 로 방어하지 않아도 되게 고정한다."""
    empty = load("q-step-cycle-time")
    assert empty.target.x_questions == []
    assert empty.target.summary is None
    assert empty.target.description is None


def test_app_id_is_optional() -> None:
    without_app = load("q-no-result")
    assert without_app.target.app_id is None


# ---------------------------------------------------------------------------
# 수치 정합성 — 모든 fixture 공통
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("query_id", ALL_QUERY_IDS)
def test_question_count_agrees_in_all_three_places(query_id: str) -> None:
    """meta.questionCount = summary.totalQuestions = len(questions).

    스키마의 model_validator 가 강제한다. 여기서는 그 값이 실제로 100 인지까지 본다.
    """
    r = load(query_id)
    assert r.meta.question_count == r.summary.total_questions == len(r.questions) == 100


def test_mismatched_question_count_is_rejected(raw: dict[str, Any]) -> None:
    """같은 수가 세 자리에 있으므로 어긋난 응답은 거절되어야 한다."""
    broken = json.loads(json.dumps(raw))
    broken["meta"]["questionCount"] = 99
    with pytest.raises(ValueError, match="질문 수가 서로 다릅니다"):
        EvaluationReport.model_validate(broken)


@pytest.mark.parametrize("query_id", ALL_QUERY_IDS)
def test_summary_matches_questions(query_id: str) -> None:
    r = load(query_id)
    total = r.summary.total_questions
    top1_hits = sum(1 for q in r.questions if q.top1_hit)
    top3_hits = sum(1 for q in r.questions if q.top3_hit)

    assert r.summary.top1_accuracy == pytest.approx(round(top1_hits / total * 100, 1))
    assert r.summary.top3_accuracy == pytest.approx(round(top3_hits / total * 100, 1))
    assert r.summary.top1_fail_count == total - top1_hits
    assert r.summary.top3_fail_count == total - top3_hits


@pytest.mark.parametrize("query_id", ALL_QUERY_IDS)
def test_grades_match_accuracy(query_id: str) -> None:
    r = load(query_id)
    assert r.summary.top1_grade == grade_for(r.summary.top1_accuracy)
    assert r.summary.top3_grade == grade_for(r.summary.top3_accuracy)


@pytest.mark.parametrize("query_id", ALL_QUERY_IDS)
def test_top1_is_never_better_than_top3(query_id: str) -> None:
    r = load(query_id)
    assert r.summary.top1_accuracy <= r.summary.top3_accuracy
    assert r.summary.top1_fail_count >= r.summary.top3_fail_count


@pytest.mark.parametrize("query_id", ALL_QUERY_IDS)
def test_question_type_stats_match_questions(query_id: str) -> None:
    r = load(query_id)
    counted: Counter[QuestionType] = Counter(q.question_type for q in r.questions)
    total = r.summary.total_questions

    for stat in r.question_types:
        assert stat.count == counted[stat.type], stat.type
        assert stat.ratio == pytest.approx(round(stat.count / total * 100, 1)), stat.type
        hits = sum(
            1 for q in r.questions if q.question_type == stat.type and q.top3_hit
        )
        expected = round(hits / stat.count * 100, 1) if stat.count else 0.0
        assert stat.top3_accuracy == pytest.approx(expected), stat.type

    # 목록에 없는 유형의 문항이 섞여 있으면 도넛 합과 표가 어긋난다.
    assert set(counted) <= {stat.type for stat in r.question_types}
    assert sum(stat.count for stat in r.question_types) == total


# ---------------------------------------------------------------------------
# 문항 — 100개 전체
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("query_id", ALL_QUERY_IDS)
def test_question_numbers_are_unique_1_to_n(query_id: str) -> None:
    r = load(query_id)
    assert sorted(q.no for q in r.questions) == list(range(1, len(r.questions) + 1))


@pytest.mark.parametrize("query_id", ALL_QUERY_IDS)
def test_questions_are_sorted_top3_top1_none(query_id: str) -> None:
    """정렬: TOP3 → TOP1_ONLY → NONE, 그 안에서 no 오름차순."""
    r = load(query_id)
    order = {FailureScope.TOP3: 0, FailureScope.TOP1_ONLY: 1, FailureScope.NONE: 2}
    keys = [(order[q.failure_scope], q.no) for q in r.questions]
    assert keys == sorted(keys)


@pytest.mark.parametrize("query_id", ALL_QUERY_IDS)
def test_scope_counts_match_summary(query_id: str) -> None:
    """top1FailCount = TOP1_ONLY + TOP3, top3FailCount = TOP3."""
    r = load(query_id)
    scopes = Counter(q.failure_scope for q in r.questions)
    assert scopes[FailureScope.TOP3] == r.summary.top3_fail_count
    assert (
        scopes[FailureScope.TOP1_ONLY] + scopes[FailureScope.TOP3]
        == r.summary.top1_fail_count
    )


@pytest.mark.parametrize("query_id", ALL_QUERY_IDS)
def test_hit_flags_agree_with_scope(query_id: str) -> None:
    for q in load(query_id).questions:
        if q.failure_scope == FailureScope.NONE:
            assert q.top1_hit and q.top3_hit, q.no
            assert q.failure_category is None and q.reason is None, q.no
        elif q.failure_scope == FailureScope.TOP1_ONLY:
            assert not q.top1_hit and q.top3_hit, q.no
        else:
            assert not q.top1_hit and not q.top3_hit, q.no
            assert q.failure_category is not None and q.reason is not None, q.no


@pytest.mark.parametrize("query_id", ALL_QUERY_IDS)
def test_hit_is_decided_by_query_id_not_path(query_id: str) -> None:
    """hit 판정은 top3[].queryId 와 target.queryId 비교다. path 가 아니다."""
    r = load(query_id)
    target_id = r.target.query_id
    for q in r.questions:
        results = q.top3 or []
        ids = [item.query_id for item in results]
        assert q.top1_hit == (bool(ids) and ids[0] == target_id), q.no
        assert q.top3_hit == (target_id in ids), q.no


@pytest.mark.parametrize("query_id", ALL_QUERY_IDS)
def test_top3_is_ranked_and_sorted(query_id: str) -> None:
    for q in load(query_id).questions:
        results = q.top3
        if results is None:
            continue
        assert [item.rank for item in results] == list(range(1, len(results) + 1)), q.no
        scores = [item.score for item in results]
        assert scores == sorted(scores, reverse=True), q.no


@pytest.mark.parametrize("query_id", ALL_QUERY_IDS)
def test_top3_never_exceeds_top_k(query_id: str) -> None:
    r = load(query_id)
    for q in r.questions:
        if q.top3 is not None:
            assert 1 <= len(q.top3) <= r.meta.top_k, q.no


@pytest.mark.parametrize("query_id", ALL_QUERY_IDS)
def test_expected_rank_agrees_with_results(query_id: str) -> None:
    """expectedRank 는 평가 대상 쿼리가 몇 위였는지다. 결과에 없으면 null."""
    r = load(query_id)
    target_id = r.target.query_id
    for q in r.questions:
        results = q.top3 or []
        found = next((item.rank for item in results if item.query_id == target_id), None)
        if found is not None:
            assert q.expected_rank == found, q.no
        elif q.expected_rank is not None:
            # Top-N 밖에서 발견된 경우는 topK 보다 큰 순위여야 한다.
            assert q.expected_rank > r.meta.top_k, q.no


# ---------------------------------------------------------------------------
# 각 fixture 가 대표하는 경계
# ---------------------------------------------------------------------------


def test_no_result_fixture_has_null_top3() -> None:
    """유사도 하한을 넘는 결과가 없으면 배열이 아니라 null 이다."""
    r = load("q-no-result")
    empty = [q for q in r.questions if q.top3 is None]
    assert len(empty) >= 10
    for q in empty:
        assert q.failure_scope == FailureScope.TOP3
        assert not q.top1_hit and not q.top3_hit
        assert q.expected_rank is None


def test_no_result_fixture_has_partial_result_lists() -> None:
    """결과가 3개 미만인 문항도 있어야 프론트가 길이 3을 가정하지 않는다."""
    r = load("q-no-result")
    assert any(q.top3 is not None and len(q.top3) < 3 for q in r.questions)


def test_all_hit_fixture_has_no_failures_and_no_actions() -> None:
    r = load("q-wafer-yield")
    assert r.summary.top3_accuracy == 100.0
    assert r.summary.top3_fail_count == 0
    assert r.summary.top1_fail_count == 0
    assert r.recommendations == []


def test_undocumented_query_scores_badly() -> None:
    """이 제품의 전제다 — 설명이 없으면 검색이 못 찾는다."""
    r = load("q-step-cycle-time")
    assert r.target.summary is None
    assert r.target.description is None
    assert r.summary.top3_accuracy < 30
    assert r.summary.top3_grade == Grade.CRITICAL


def test_long_text_fixture_is_actually_long() -> None:
    """말줄임을 강제할 만큼 길어야 의미가 있는 fixture 다.

    길이는 **글자 수가 아니라 표시 폭**으로 잰다. 한글은 한 글자가 두 칸을
    차지하므로, 67자짜리 한글 경로가 80자 ASCII 경로보다 넓다. 글자 수로 재면
    "충분히 길지 않다" 는 잘못된 판정이 나온다.
    """

    def display_width(text: str) -> int:
        return sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)

    r = load("q-wafer-defect-daily-aggregation-by-step-line-equipment-shift")
    assert display_width(r.target.path) > 100
    assert len(r.target.query_id) > 40
    assert r.target.description is not None
    assert display_width(r.target.description) > 400
    assert max(display_width(q.question) for q in r.questions) > 200


# ---------------------------------------------------------------------------
# 권장 조치
# ---------------------------------------------------------------------------


def test_recommendations_are_ordered(report: EvaluationReport) -> None:
    orders = [r.order for r in report.recommendations]
    assert orders == sorted(orders)
    assert orders[0] == 1


def test_fail_share_may_exceed_one_hundred() -> None:
    """원인은 중복 집계된다. 합이 100을 넘는 것이 정상이며 화면에 각주가 필요하다."""
    r = load("q-step-cycle-time")
    assert sum(item.fail_share for item in r.recommendations) > 100


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------


def test_enum_members_match_contract() -> None:
    assert set(Grade) == {"CRITICAL", "NEEDS_IMPROVEMENT", "FAIR", "GOOD"}
    assert set(Priority) == {"HIGH", "MEDIUM", "LOW"}
    assert set(SearchMode) == {"BM25", "VECTOR", "HYBRID"}
    assert set(FailureScope) == {"NONE", "TOP1_ONLY", "TOP3"}
    # questionType 은 자리표시다 (open-questions #69). 개수가 바뀌면 이 목록도 바뀐다.
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


def test_question_type_change_is_a_two_file_edit() -> None:
    """유형 체계가 바뀔 때 고칠 곳이 두 곳뿐이라는 사실을 잠근다 (#69).

    컴포넌트에 유형 이름이 박혀 있으면 여기서 걸린다 — 그러면 enum 을 바꿀 때
    화면 곳곳을 찾아다녀야 한다.
    """
    app_dir = Path(__file__).resolve().parents[1] / "app"
    offenders = [
        path.relative_to(app_dir).as_posix()
        for path in app_dir.rglob("*.py")
        if path.name not in {"evaluation.py", "make_fixtures.py"}
        and any(name in path.read_text(encoding="utf-8") for name in ("MIXED_LANG", "SHORT_KEYWORD"))
    ]
    assert offenders == []


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_evaluate_accepts_snake_case_query_id() -> None:
    """DAC 이 보내는 형태다."""
    res = client.post("/api/v1/evaluations", json={"query_id": NORMAL_QUERY_ID})
    assert res.status_code == 200
    assert res.json()["target"]["queryId"] == NORMAL_QUERY_ID


def test_evaluate_also_accepts_camel_case_query_id() -> None:
    """계약의 직렬화 규약과 맞춰 둘 다 받는다 (contract.md §1)."""
    res = client.post("/api/v1/evaluations", json={"queryId": NORMAL_QUERY_ID})
    assert res.status_code == 200


def test_response_is_camel_case_only() -> None:
    res = client.post("/api/v1/evaluations", json={"query_id": NORMAL_QUERY_ID})
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


def test_response_carries_the_whole_dashboard() -> None:
    body = client.post("/api/v1/evaluations", json={"query_id": NORMAL_QUERY_ID}).json()
    assert body["traceId"]
    assert body["target"]["path"]
    assert body["target"]["xQuestions"]
    assert body["meta"]["embeddingModel"] == "bge-m3"
    assert body["meta"]["questionCount"] == 100
    assert body["summary"]["top3Grade"]
    assert body["questionTypes"][0]["top3Accuracy"] is not None
    assert body["recommendations"][0]["failShare"]
    assert len(body["questions"]) == 100
    assert body["questions"][0]["failureScope"] == "TOP3"
    assert body["questions"][0]["top3"][0]["queryId"]


def test_unknown_query_id_returns_404() -> None:
    res = client.post("/api/v1/evaluations", json={"query_id": "q-does-not-exist"})
    assert res.status_code == 404


def test_missing_query_id_returns_422() -> None:
    assert client.post("/api/v1/evaluations", json={}).status_code == 422


@pytest.mark.parametrize("bad_id", ["../secrets", "a/b", "", "x" * 200])
def test_malformed_query_id_is_rejected(bad_id: str) -> None:
    """query_id 가 저장소 키가 되므로 형태를 강제한다."""
    res = client.post("/api/v1/evaluations", json={"query_id": bad_id})
    assert res.status_code == 422


def test_history_endpoints_are_gone() -> None:
    """무상태 전환으로 목록·추적ID 조회가 사라졌다 (contract.md §0)."""
    assert client.get("/api/v1/evaluations").status_code == 405
    assert client.get(f"/api/v1/evaluations/{NORMAL_QUERY_ID}").status_code == 404


def test_openapi_documents_the_post_endpoint() -> None:
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/evaluations"]["post"]
    assert operation["responses"]["200"]
    assert operation["responses"]["404"]

    # 프론트 타입은 이 스펙에서 생성된다. 필드 설명이 비면 생성물이 빈껍데기가 된다.
    report_schema = schema["components"]["schemas"]["EvaluationReport"]
    for name, field in report_schema["properties"].items():
        assert field.get("description") or field.get("allOf") or "$ref" in field, name
