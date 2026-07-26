"""경계값 fixture 검증 (Phase 10).

`test_evaluation_contract.py` 는 정상 fixture(A492) **하나**를 자세히 잠근다.
여기서는 반대로, **모든 fixture 가 공통으로 지켜야 하는 것**만 본다.
극단 데이터라고 해서 요약과 표가 다른 말을 해도 되는 것은 아니다.

경계값 fixture 는 `app/scripts/make_edge_fixtures.py` 가 만든다.
계약이 바뀌면 그 스크립트를 다시 돌리고 결과 JSON 을 함께 커밋한다.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.schemas.evaluation import EvaluationReport, FailureScope, Grade, QuestionType

client = TestClient(app)

# 경계값 fixture 의 추적 ID. 각각이 무엇을 재현하는지는 스크립트의 docstring 에 있다.
EDGE_TRACE_IDS = ["E100", "ELOW", "E1Q", "E3T", "EFIRST", "ELONG"]

# 정상 fixture 를 포함한 전체. 공통 정합성은 전부가 지켜야 한다.
ALL_TRACE_IDS = ["A492", "A311", *EDGE_TRACE_IDS]


def load(trace_id: str) -> EvaluationReport:
    path: Path = settings.fixture_dir / f"eval_{trace_id}.json"
    return EvaluationReport.model_validate(json.loads(path.read_text(encoding="utf-8")))


def raw_of(trace_id: str) -> dict[str, Any]:
    path: Path = settings.fixture_dir / f"eval_{trace_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def grade_for(accuracy: float) -> Grade:
    """등급 기준 (contract.md §3). 지표별로 갈리면 여기가 나뉜다 (open-questions #54)."""
    if accuracy < 70:
        return Grade.CRITICAL
    if accuracy < 85:
        return Grade.NEEDS_IMPROVEMENT
    if accuracy < 95:
        return Grade.FAIR
    return Grade.GOOD


# ---------------------------------------------------------------------------
# 모든 fixture 공통
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("trace_id", ALL_TRACE_IDS)
def test_fixture_validates(trace_id: str) -> None:
    assert load(trace_id).trace_id == trace_id


@pytest.mark.parametrize("trace_id", ALL_TRACE_IDS)
def test_summary_matches_questions(trace_id: str) -> None:
    """요약 수치가 문항 목록에서 그대로 재구성되어야 한다."""
    report = load(trace_id)
    total = report.summary.total_questions
    assert len(report.questions) == total

    top1_hits = sum(1 for q in report.questions if q.top1_hit)
    top3_hits = sum(1 for q in report.questions if q.top3_hit)
    assert report.summary.top1_accuracy == pytest.approx(round(top1_hits / total * 100, 1))
    assert report.summary.top3_accuracy == pytest.approx(round(top3_hits / total * 100, 1))
    assert report.summary.top1_fail_count == total - top1_hits
    assert report.summary.top3_fail_count == total - top3_hits


@pytest.mark.parametrize("trace_id", ALL_TRACE_IDS)
def test_grades_match_accuracy(trace_id: str) -> None:
    report = load(trace_id)
    assert report.summary.top1_grade == grade_for(report.summary.top1_accuracy)
    assert report.summary.top3_grade == grade_for(report.summary.top3_accuracy)
    for query in report.queries:
        assert query.grade == grade_for(query.top3_accuracy), query.path


@pytest.mark.parametrize("trace_id", ALL_TRACE_IDS)
def test_scope_agrees_with_hit_flags(trace_id: str) -> None:
    for q in load(trace_id).questions:
        if q.failure_scope == FailureScope.NONE:
            assert q.top1_hit and q.top3_hit, q.no
            assert q.failure_category is None and q.reason is None, q.no
        elif q.failure_scope == FailureScope.TOP1_ONLY:
            assert not q.top1_hit and q.top3_hit, q.no
        else:
            assert not q.top1_hit and not q.top3_hit, q.no


@pytest.mark.parametrize("trace_id", ALL_TRACE_IDS)
def test_questions_are_sorted_and_numbered(trace_id: str) -> None:
    """정렬은 계약이 해서 내려준다 — 프론트는 다시 정렬하지 않는다."""
    report = load(trace_id)
    order = {FailureScope.TOP3: 0, FailureScope.TOP1_ONLY: 1, FailureScope.NONE: 2}
    keys = [(order[q.failure_scope], q.no) for q in report.questions]
    assert keys == sorted(keys)
    assert sorted(q.no for q in report.questions) == list(range(1, len(report.questions) + 1))


@pytest.mark.parametrize("trace_id", ALL_TRACE_IDS)
def test_top1_agrees_with_top3_head(trace_id: str) -> None:
    for q in load(trace_id).questions:
        assert q.top3, q.no
        head = q.top3[0]
        assert (q.top1.method, q.top1.path) == (head.method, head.path), q.no
        assert [r.rank for r in q.top3] == list(range(1, len(q.top3) + 1)), q.no


@pytest.mark.parametrize("trace_id", ALL_TRACE_IDS)
def test_query_stats_match_questions(trace_id: str) -> None:
    report = load(trace_id)
    assert report.target.query_count == len(report.queries)

    total_by_query: Counter[tuple[str, str]] = Counter(
        (q.expected.method, q.expected.path) for q in report.questions
    )
    hits_by_query: Counter[tuple[str, str]] = Counter(
        (q.expected.method, q.expected.path) for q in report.questions if q.top3_hit
    )
    for query in report.queries:
        key = (query.method, query.path)
        assert total_by_query[key] == query.question_count, key
        if query.question_count:
            expected = round(hits_by_query[key] / query.question_count * 100, 1)
            assert query.top3_accuracy == pytest.approx(expected), key

    # 모든 문항의 기대 쿼리는 이 앱의 쿼리 목록 안에 있어야 한다.
    known = {(q.method, q.path) for q in report.queries}
    for question in report.questions:
        assert (question.expected.method, question.expected.path) in known, question.no


@pytest.mark.parametrize("trace_id", ALL_TRACE_IDS)
def test_question_type_stats_match_questions(trace_id: str) -> None:
    report = load(trace_id)
    counted: Counter[QuestionType] = Counter(q.question_type for q in report.questions)
    total = report.summary.total_questions

    for stat in report.question_types:
        assert stat.count == counted[stat.type], stat.type
        assert stat.ratio == pytest.approx(round(stat.count / total * 100, 1)), stat.type

    # 목록에 없는 유형의 문항이 섞여 있으면 도넛의 합과 표가 어긋난다.
    declared = {stat.type for stat in report.question_types}
    assert set(counted) <= declared
    assert sum(stat.count for stat in report.question_types) == total


# ---------------------------------------------------------------------------
# 각 경계값이 실제로 그 경계인지
# ---------------------------------------------------------------------------


def test_e100_has_no_failures_and_no_actions() -> None:
    """실패 0건이면 권장 조치도 재생성 후보도 없다 — 화면에 빈 카드가 남으면 안 된다."""
    report = load("E100")
    assert report.summary.top3_fail_count == 0
    assert report.summary.top1_fail_count == 0
    assert report.summary.top3_accuracy == 100.0
    assert report.recommendations == []
    assert not any(q.needs_regeneration for q in report.queries)


def test_elow_fails_every_question() -> None:
    report = load("ELOW")
    assert report.summary.total_questions == 100
    assert report.summary.top3_fail_count == 100
    assert report.summary.top3_accuracy == 0.0
    assert all(q.failure_scope == FailureScope.TOP3 for q in report.questions)
    assert all(q.needs_regeneration for q in report.queries)


def test_e1q_has_one_query() -> None:
    report = load("E1Q")
    assert len(report.queries) == 1
    assert report.target.query_count == 1
    # 유형 7종을 다 내려주되 대부분이 0건 — 도넛 조각은 하나뿐이다.
    nonzero = [stat for stat in report.question_types if stat.count > 0]
    assert len(nonzero) == 1


def test_e3t_declares_only_three_types() -> None:
    report = load("E3T")
    assert len(report.question_types) == 3


def test_efirst_omits_every_optional_field() -> None:
    """previous / rawSource / owner 가 한꺼번에 없는 경우."""
    report = load("EFIRST")
    assert report.previous is None
    assert report.meta.raw_source is None
    assert report.target.owner is None


def test_elong_has_long_korean_and_english_text() -> None:
    report = load("ELONG")
    assert max(len(q.path) for q in report.queries) > 80
    assert max(len(q.question) for q in report.questions) > 120
    assert len(report.target.app_name) > 30


# ---------------------------------------------------------------------------
# 정상 경로를 건드리지 않았는지
# ---------------------------------------------------------------------------


def test_edge_fixtures_are_older_than_the_normal_one() -> None:
    """루트("/")는 최신 평가로 보낸다. 경계값이 최신이 되면 정상 경로가 바뀐다."""
    newest_edge = max(load(t).evaluated_at for t in EDGE_TRACE_IDS)
    assert newest_edge < load("A492").evaluated_at


def test_list_puts_the_normal_fixture_first() -> None:
    res = client.get("/api/v1/evaluations")
    assert res.status_code == 200
    items = res.json()
    assert items[0]["traceId"] == "A492"
    assert {item["traceId"] for item in items} >= set(ALL_TRACE_IDS)


@pytest.mark.parametrize("trace_id", EDGE_TRACE_IDS)
def test_edge_fixtures_are_servable(trace_id: str) -> None:
    res = client.get(f"/api/v1/evaluations/{trace_id}")
    assert res.status_code == 200
    assert res.json()["traceId"] == trace_id
