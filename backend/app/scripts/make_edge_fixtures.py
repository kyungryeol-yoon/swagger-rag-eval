"""경계값 fixture 를 만든다 (Phase 10).

    cd backend && uv run python -m app.scripts.make_edge_fixtures

정상 fixture(A492)는 손대지 않는다. 실제 데이터에서 실제로 벌어지는 극단만
따로 만들어, 화면이 그 상황에서 무너지지 않는지 눈으로 확인하기 위한 것이다.

만드는 것:
    E100    인식률 100% (실패 0건). 권장 조치도 재생성 후보도 없다
    ELOW    100문항 전부 Top-3 실패
    E1Q     쿼리 1개짜리 앱. 도넛 조각도 1개
    E3T     질문 유형이 3종만
    EFIRST  첫 평가 — previous / rawSource / owner 가 전부 없음
    ELONG   한글·영문 초장문 질문·경로

**출력물은 생성물이 아니라 커밋 대상이다.** 폐쇄망에서는 파일을 복사해 옮기므로
스크립트를 돌릴 수 없는 환경이 있다. 계약이 바뀌면 이 스크립트를 다시 돌려
결과 JSON 을 함께 커밋한다.

수치는 직접 적지 않고 문항 목록에서 **전부 유도한다**. 손으로 적으면 요약과
표가 서로 다른 말을 하게 되고, 그건 경계값 검증이 아니라 새 버그다.
"""

import json
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"

# 평가일. **전부 A492(2026-07-22)보다 과거로 둔다.** 루트("/")가 최신 평가로
# 보내므로, 경계값 fixture 가 최신이 되면 정상 경로가 바뀐다.
BASE_DATE = "2026-06"


# ---------------------------------------------------------------------------
# 등급 — contract.md §3. 백엔드가 확정해 내려주는 값이므로 여기서도 같은 규칙을 쓴다.
# ---------------------------------------------------------------------------


def grade_for(accuracy: float) -> str:
    if accuracy < 70:
        return "CRITICAL"
    if accuracy < 85:
        return "NEEDS_IMPROVEMENT"
    if accuracy < 95:
        return "FAIR"
    return "GOOD"


def pct(hits: int, total: int) -> float:
    """비율(%). 0~1 소수가 아니라 0~100 실수다."""
    return round(hits / total * 100, 1) if total else 0.0


# ---------------------------------------------------------------------------
# 문항 조립
# ---------------------------------------------------------------------------

# 문항 유형별 한글 라벨. 계약의 label 필드 값이다.
TYPE_LABELS: dict[str, str] = {
    "DIRECT": "직접 질문",
    "USER_NL": "사용자 자연어 질문",
    "DOMAIN_TERM": "업무 용어 질문",
    "PARAMETER": "파라미터 기반 질문",
    "ERROR_CASE": "오류/에러 상황 질문",
    "SHORT_KEYWORD": "짧은 키워드 질문",
    "MIXED_LANG": "한영 혼합 질문",
}

# 실패 범위별 원인·설명. 성공(NONE)이면 둘 다 null 이어야 한다 (계약).
FAIL_REASON: dict[str, tuple[str, str]] = {
    "TOP1_ONLY": ("SIMILAR_RESOURCE", "이름이 비슷한 쿼리가 1위를 차지함"),
    "TOP3": ("DESCRIPTION_MISSING", "설명이 없어 질문의 의도와 이어지지 않음"),
}

# 정렬 기준: TOP3 → TOP1_ONLY → NONE (계약 §2).
SCOPE_ORDER = {"TOP3": 0, "TOP1_ONLY": 1, "NONE": 2}


def make_question(
    no: int,
    text: str,
    qtype: str,
    expected: tuple[str, str],
    scope: str,
    others: list[tuple[str, str]],
) -> dict[str, Any]:
    """문항 1개. hit 플래그·순위·원인을 scope 하나에서 전부 유도한다.

    Args:
        no: 표시 순번.
        text: 실제로 던진 질문.
        qtype: 문항 유형 enum.
        expected: 기대 쿼리 (method, path).
        scope: NONE / TOP1_ONLY / TOP3.
        others: 오답 후보. 기대 쿼리는 자동으로 빠진다. 검색 코퍼스는 앱 경계를
            넘을 수 있으므로 다른 앱의 쿼리를 넣어도 된다 — 계약이 강제하는 것은
            `expected` 가 이 앱의 쿼리 목록에 있어야 한다는 것뿐이다.

    Raises:
        ValueError: 오답 후보가 없는데 실패 문항을 만들려 할 때.
    """
    pool = [key for key in others if key != expected]

    def at(index: int) -> tuple[str, str]:
        return pool[index % len(pool)]

    if scope == "NONE":
        # 후보가 없으면 결과가 1건뿐이다. 쿼리 1개짜리 앱에서 실제로 그렇다 —
        # 억지로 3건을 채우면 같은 경로가 세 번 나온다.
        ranked = [expected, *(at(no + i) for i in range(min(2, len(pool))))]
    elif scope == "TOP1_ONLY":
        if not pool:
            raise ValueError(f"오답 후보가 없어 Top-1 실패를 만들 수 없습니다: {expected}")
        ranked = [at(no), expected, *(at(no + 1) for _ in range(min(1, len(pool) - 1)))]
    else:
        # 완전 실패 — 상위 결과 어디에도 기대 쿼리가 없다.
        if not pool:
            raise ValueError(f"오답 후보가 없어 완전 실패를 만들 수 없습니다: {expected}")
        ranked = [at(no + i) for i in range(min(3, len(pool)))]

    scores = [0.91, 0.74, 0.62][: len(ranked)]
    top3 = [
        {"rank": i + 1, "method": m, "path": p, "score": s}
        for i, ((m, p), s) in enumerate(zip(ranked, scores, strict=True))
    ]

    category, reason = FAIL_REASON.get(scope, (None, None))
    expected_rank = {"NONE": 1, "TOP1_ONLY": 2}.get(scope)

    return {
        "no": no,
        "question": text,
        "questionType": qtype,
        "expected": {"method": expected[0], "path": expected[1]},
        "top1": {"method": ranked[0][0], "path": ranked[0][1], "score": scores[0]},
        "top3": top3,
        "top1Hit": scope == "NONE",
        "top3Hit": scope in ("NONE", "TOP1_ONLY"),
        "failureScope": scope,
        "expectedRank": expected_rank,
        "failureCategory": category,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# 리포트 조립 — 요약·쿼리 통계·유형 통계를 문항에서 유도한다
# ---------------------------------------------------------------------------


def build_report(
    *,
    trace_id: str,
    evaluated_at: str,
    target: dict[str, Any],
    query_specs: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    type_order: list[str],
    recommendations: list[dict[str, Any]],
    previous: dict[str, Any] | None,
    raw_source: dict[str, Any] | None,
    duration_ms: int,
) -> dict[str, Any]:
    """계약 형태의 평가 리포트 하나를 만든다.

    `query_specs` 는 쿼리의 **명세 쪽 사실**(경로·설명 길이 등)만 적는다.
    문항 수·인식률·등급·재생성 여부는 문항 목록에서 계산한다.
    """
    questions = sorted(questions, key=lambda q: (SCOPE_ORDER[q["failureScope"]], q["no"]))
    total = len(questions)

    top1_hits = sum(1 for q in questions if q["top1Hit"])
    top3_hits = sum(1 for q in questions if q["top3Hit"])
    top1_accuracy = pct(top1_hits, total)
    top3_accuracy = pct(top3_hits, total)

    queries: list[dict[str, Any]] = []
    for spec in query_specs:
        key = (spec["method"], spec["path"])
        mine = [q for q in questions if (q["expected"]["method"], q["expected"]["path"]) == key]
        hits = sum(1 for q in mine if q["top3Hit"])
        accuracy = pct(hits, len(mine))
        grade = grade_for(accuracy)
        queries.append(
            {
                "path": spec["path"],
                "method": spec["method"],
                "summary": spec["summary"],
                "descriptionLength": spec["descriptionLength"],
                "hasParamDescription": spec["hasParamDescription"],
                "questionCount": len(mine),
                "top3Accuracy": accuracy,
                "grade": grade,
                # 등급 CRITICAL 이면 재생성 후보 (open-questions #53 의 현재 기준).
                "needsRegeneration": grade == "CRITICAL",
            }
        )

    question_types: list[dict[str, Any]] = []
    for qtype in type_order:
        mine = [q for q in questions if q["questionType"] == qtype]
        hits = sum(1 for q in mine if q["top3Hit"])
        question_types.append(
            {
                "type": qtype,
                "label": TYPE_LABELS[qtype],
                "count": len(mine),
                "ratio": pct(len(mine), total),
                "top3Accuracy": pct(hits, len(mine)),
            }
        )

    meta: dict[str, Any] = {
        "embeddingModel": "bge-m3",
        "searchMode": "HYBRID",
        "topK": 3,
        "questionSource": "LLM_GENERATED_HUMAN_REVIEWED",
        "durationMs": duration_ms,
        "rawSource": raw_source,
    }

    return {
        "traceId": trace_id,
        "evaluatedAt": evaluated_at,
        "target": {**target, "queryCount": len(query_specs)},
        "meta": meta,
        "summary": {
            "totalQuestions": total,
            "top1Accuracy": top1_accuracy,
            "top3Accuracy": top3_accuracy,
            "top1FailCount": total - top1_hits,
            "top3FailCount": total - top3_hits,
            "top1Grade": grade_for(top1_accuracy),
            "top3Grade": grade_for(top3_accuracy),
        },
        "queries": queries,
        "questionTypes": question_types,
        "recommendations": recommendations,
        "questions": questions,
        "previous": previous,
    }


# ---------------------------------------------------------------------------
# 공통 소재 — A492 와 같은 도메인(MF Worker)을 쓴다
# ---------------------------------------------------------------------------

ALL_TYPES = list(TYPE_LABELS)

STANDARD_QUERIES: list[dict[str, Any]] = [
    {
        "method": "GET",
        "path": "/queries/lot-status",
        "summary": "랏 현재 공정 단계 조회",
        "descriptionLength": 168,
        "hasParamDescription": True,
    },
    {
        "method": "GET",
        "path": "/queries/wafer-yield-daily",
        "summary": "일간 웨이퍼 수율 집계",
        "descriptionLength": 142,
        "hasParamDescription": True,
    },
    {
        "method": "POST",
        "path": "/queries/defect-summary",
        "summary": "불량 유형별 집계",
        "descriptionLength": 96,
        "hasParamDescription": True,
    },
    {
        "method": "GET",
        "path": "/queries/equipment-downtime",
        "summary": "설비 비가동 시간 조회",
        "descriptionLength": 41,
        "hasParamDescription": False,
    },
    {
        "method": "GET",
        "path": "/queries/step-cycle-time",
        "summary": None,
        "descriptionLength": 0,
        "hasParamDescription": False,
    },
]

STANDARD_KEYS = [(q["method"], q["path"]) for q in STANDARD_QUERIES]

# 다른 앱의 쿼리. 검색 코퍼스는 앱 경계를 넘으므로 상위 결과에 섞여 들어올 수 있다.
# 이 앱의 쿼리 목록에는 없어야 한다 — 계약이 강제하는 것은 `expected` 뿐이다.
CROSS_APP_KEYS: list[tuple[str, str]] = [
    ("GET", "/queries/mes-order-progress"),
    ("GET", "/queries/facility-power-usage"),
    ("POST", "/queries/quality-hold-list"),
]

QUESTION_STEMS = [
    "랏 번호로 지금 어느 공정에 있는지 확인하려면 어떤 쿼리를 쓰나요",
    "어제 웨이퍼 수율을 라인별로 보고 싶습니다",
    "불량 유형별 집계를 주간 단위로 뽑으려면",
    "설비가 멈춰 있던 시간을 설비별로 확인하고 싶어요",
    "스텝별 사이클타임 추이를 보려면 무엇을 호출하나요",
    "eqp 다운타임 top5",
    "wafer yield 어제 기준으로 알려줘",
    "랏 계보를 거슬러 올라가려면 어떤 조회를 쓰나요",
    "택트타임이 튀는 스텝을 찾고 싶습니다",
    "챔버 센서 값이 비어 있을 때는 어떻게 확인하나요",
]


def stem(index: int) -> str:
    return QUESTION_STEMS[index % len(QUESTION_STEMS)]


# ---------------------------------------------------------------------------
# 경계값 fixture 6종
# ---------------------------------------------------------------------------


def fixture_all_hit() -> dict[str, Any]:
    """인식률 100% — 실패 0건.

    FailureTable 은 성공만 남고, 권장 조치도 재생성 후보도 없다.
    "고칠 게 없을 때" 화면에 빈 카드가 남지 않는지 보는 fixture 다.
    """
    questions = [
        make_question(
            no=i + 1,
            text=f"{stem(i)}?",
            qtype=ALL_TYPES[i % len(ALL_TYPES)],
            expected=STANDARD_KEYS[i % len(STANDARD_KEYS)],
            scope="NONE",
            others=STANDARD_KEYS,
        )
        for i in range(100)
    ]
    # 등급이 전부 GOOD 이 되도록 설명을 채운 상태로 둔다.
    specs = [
        {**spec, "summary": spec["summary"] or "스텝별 사이클타임 조회", "descriptionLength": max(spec["descriptionLength"], 120), "hasParamDescription": True}
        for spec in STANDARD_QUERIES
    ]
    return build_report(
        trace_id="E100",
        evaluated_at=f"{BASE_DATE}-01T10:00:00+09:00",
        target={
            "appId": "mf-worker",
            "appName": "MF Worker (전건 적중)",
            "specVersion": "v9",
            "owner": "데이터플랫폼팀",
        },
        query_specs=specs,
        questions=questions,
        type_order=ALL_TYPES,
        recommendations=[],
        previous={
            "traceId": "E099",
            "evaluatedAt": f"{BASE_DATE}-01T09:00:00+09:00",
            "top3Accuracy": 88.0,
        },
        raw_source={
            "toolVersion": "rageval-2.4.0",
            "promptVersion": "qgen-2026Q2",
            "generatedAt": f"{BASE_DATE}-01T09:58:00+09:00",
        },
        duration_ms=41200,
    )


def fixture_all_fail() -> dict[str, Any]:
    """인식률 0% — 100문항 전부 Top-3 실패.

    표 100행이 전부 빨간 뱃지가 된다. 필터 칩과 스크롤 영역이 그 상태에서
    읽히는지, 게이지가 0 에서 어떻게 그려지는지를 본다.
    """
    questions = [
        make_question(
            no=i + 1,
            text=f"{stem(i)}?",
            qtype=ALL_TYPES[i % len(ALL_TYPES)],
            expected=STANDARD_KEYS[i % len(STANDARD_KEYS)],
            scope="TOP3",
            others=STANDARD_KEYS,
        )
        for i in range(100)
    ]
    specs = [
        {**spec, "summary": None, "descriptionLength": 0, "hasParamDescription": False}
        for spec in STANDARD_QUERIES
    ]
    return build_report(
        trace_id="ELOW",
        evaluated_at=f"{BASE_DATE}-02T10:00:00+09:00",
        target={
            "appId": "mf-legacy",
            "appName": "MF Legacy (설명 없음)",
            "specVersion": "v1",
            "owner": "설비제어팀",
        },
        query_specs=specs,
        questions=questions,
        type_order=ALL_TYPES,
        recommendations=[
            {
                "order": 1,
                "title": "설명(Description) 보강",
                "description": "등록된 쿼리 전부에 summary 와 description 이 비어 있습니다. 검색이 참고할 문장이 하나도 없어 어떤 질문도 맞히지 못합니다.",
                "priority": "HIGH",
                "failShare": 100.0,
            },
            {
                "order": 2,
                "title": "현장 용어·동의어 추가",
                "description": "설명을 채운 뒤에는 현장 표현(eqp, 택트타임, 계보)을 함께 적어야 짧은 키워드 질문이 걸립니다.",
                "priority": "HIGH",
                "failShare": 62.0,
            },
            {
                "order": 3,
                "title": "유사 조회 구분 강화",
                "description": "이름이 비슷한 조회 쿼리끼리 서로의 상위 결과를 밀어냅니다. 무엇을 집계하는지 한 줄씩 덧붙입니다.",
                "priority": "MEDIUM",
                "failShare": 28.0,
            },
        ],
        previous={
            "traceId": "ELOW0",
            "evaluatedAt": f"{BASE_DATE}-02T09:00:00+09:00",
            "top3Accuracy": 12.0,
        },
        raw_source=None,
        duration_ms=52400,
    )


def fixture_single_query() -> dict[str, Any]:
    """쿼리 1개짜리 앱.

    QueryQualityTable 이 1행, 도넛 조각이 1개다. 조각이 하나면 간격을 두지
    않아야 원이 닫힌다(QuestionTypeChart). 오답 후보가 없어 완전 실패는
    만들 수 없으므로 성공과 Top-1 실패만 둔다.
    """
    only: list[dict[str, Any]] = [
        {
            "method": "GET",
            "path": "/queries/daily-throughput",
            "summary": "일간 생산량 조회",
            "descriptionLength": 88,
            "hasParamDescription": True,
        }
    ]
    key = (str(only[0]["method"]), str(only[0]["path"]))
    scopes = ["NONE", "NONE", "TOP1_ONLY", "NONE", "NONE", "NONE", "TOP1_ONLY", "NONE"]
    questions = [
        make_question(
            no=i + 1,
            text=f"{stem(i)}?",
            qtype="DIRECT",
            expected=key,
            scope=scope,
            # 앱에는 쿼리가 하나뿐이므로 오답은 다른 앱에서만 올 수 있다.
            others=CROSS_APP_KEYS,
        )
        for i, scope in enumerate(scopes)
    ]
    return build_report(
        trace_id="E1Q",
        evaluated_at=f"{BASE_DATE}-03T10:00:00+09:00",
        target={
            "appId": "throughput-only",
            "appName": "생산량 단일 조회",
            "specVersion": "v2",
            "owner": None,
        },
        query_specs=only,
        questions=questions,
        type_order=ALL_TYPES,
        recommendations=[
            {
                "order": 1,
                "title": "파라미터 설명 보강",
                "description": "쿼리가 하나뿐이라 경쟁 대상이 없는데도 Top-1 을 놓친 문항이 있습니다. 기간 파라미터의 설명을 채우면 1위 정확도가 올라갑니다.",
                "priority": "MEDIUM",
                "failShare": 25.0,
            }
        ],
        previous=None,
        raw_source={
            "toolVersion": "rageval-2.4.0",
            "promptVersion": "qgen-2026Q2",
            "generatedAt": f"{BASE_DATE}-03T09:50:00+09:00",
        },
        duration_ms=6100,
    )


def fixture_three_types() -> dict[str, Any]:
    """질문 유형이 3종만.

    계약은 7종 전부를 기대하지만 배열이므로 3종만 올 수 있다. 도넛 조각과
    막대가 3개일 때 범례·기준선이 어떻게 보이는지 확인한다.
    """
    types = ["DIRECT", "USER_NL", "MIXED_LANG"]
    plan = [
        ("NONE", "DIRECT"),
        ("NONE", "DIRECT"),
        ("NONE", "DIRECT"),
        ("TOP1_ONLY", "DIRECT"),
        ("NONE", "USER_NL"),
        ("NONE", "USER_NL"),
        ("TOP3", "USER_NL"),
        ("TOP3", "USER_NL"),
        ("NONE", "MIXED_LANG"),
        ("TOP3", "MIXED_LANG"),
        ("TOP3", "MIXED_LANG"),
        ("TOP3", "MIXED_LANG"),
    ]
    questions = [
        make_question(
            no=i + 1,
            text=f"{stem(i)}?",
            qtype=qtype,
            expected=STANDARD_KEYS[i % len(STANDARD_KEYS)],
            scope=scope,
            others=STANDARD_KEYS,
        )
        for i, (scope, qtype) in enumerate(plan)
    ]
    return build_report(
        trace_id="E3T",
        evaluated_at=f"{BASE_DATE}-04T10:00:00+09:00",
        target={
            "appId": "mf-worker",
            "appName": "MF Worker (축소 문항)",
            "specVersion": "v3",
            "owner": "데이터플랫폼팀",
        },
        query_specs=STANDARD_QUERIES,
        questions=questions,
        type_order=types,
        recommendations=[
            {
                "order": 1,
                "title": "현장 용어·동의어 추가",
                "description": "한영 혼합 질문에서만 실패가 몰립니다. 설명 안에 영문 약어와 한글 표현을 나란히 적어두면 걸립니다.",
                "priority": "HIGH",
                "failShare": 71.4,
            },
            {
                "order": 2,
                "title": "설명(Description) 보강",
                "description": "설명이 비어 있는 쿼리가 남아 있어 자연어 질문이 이어지지 않습니다.",
                "priority": "MEDIUM",
                "failShare": 42.9,
            },
        ],
        previous={
            "traceId": "E3T0",
            "evaluatedAt": f"{BASE_DATE}-04T09:00:00+09:00",
            "top3Accuracy": 50.0,
        },
        raw_source=None,
        duration_ms=9800,
    )


def fixture_first_run() -> dict[str, Any]:
    """첫 평가 — **선택 필드가 전부 없다**.

    previous(델타 뱃지), meta.rawSource(평가툴 출처 줄), target.owner(담당)가
    한꺼번에 null 이다. 셋 다 숨겨졌을 때 헤더와 카드가 비어 보이지 않는지 본다.
    """
    plan = ["NONE"] * 9 + ["TOP1_ONLY"] * 3 + ["TOP3"] * 3
    questions = [
        make_question(
            no=i + 1,
            text=f"{stem(i)}?",
            qtype=ALL_TYPES[i % len(ALL_TYPES)],
            expected=STANDARD_KEYS[i % len(STANDARD_KEYS)],
            scope=scope,
            others=STANDARD_KEYS,
        )
        for i, scope in enumerate(plan)
    ]
    return build_report(
        trace_id="EFIRST",
        evaluated_at=f"{BASE_DATE}-05T10:00:00+09:00",
        target={
            "appId": "new-app",
            "appName": "신규 등록 앱",
            "specVersion": "v1",
            "owner": None,
        },
        query_specs=STANDARD_QUERIES,
        questions=questions,
        type_order=ALL_TYPES,
        recommendations=[
            {
                "order": 1,
                "title": "설명(Description) 보강",
                "description": "설명이 비어 있는 쿼리에 실패가 몰립니다. summary 와 description 을 채우는 것만으로 가장 크게 개선됩니다.",
                "priority": "HIGH",
                "failShare": 66.7,
            }
        ],
        previous=None,
        raw_source=None,
        duration_ms=12500,
    )


# 말줄임을 강제하려면 표 열 폭을 확실히 넘겨야 한다. 현실에서도 DAC 앱 이름과
# 쿼리 경로가 이 정도로 길어지는 경우가 있다.
LONG_PATH_KO = (
    "/queries/반도체-웨이퍼-불량-유형별-일간-집계-및-공정-스텝-매핑-리포트-조회"
    "-라인별-설비별-교대조별-세분화-포함"
)
LONG_PATH_EN = (
    "/queries/semiconductor-wafer-defect-daily-aggregation-by-process-step-and-line"
    "-with-equipment-and-shift-breakdown-extended"
)
LONG_QUESTION_KO = (
    "어제부터 오늘 오전까지 3라인과 4라인에서 발생한 웨이퍼 불량을 공정 스텝별로 "
    "나눠서 보고 싶은데, 설비 번호와 교대조까지 같이 묶어서 집계하려면 어떤 조회 "
    "쿼리를 써야 하고 기간 파라미터는 어떤 형식으로 넣어야 하나요?"
)
LONG_QUESTION_EN = (
    "How can I retrieve the daily wafer defect aggregation broken down by process step, "
    "equipment identifier and shift for the last twenty four hours, and what is the exact "
    "date range parameter format that this endpoint expects for the query?"
)


def fixture_long_text() -> dict[str, Any]:
    """한글·영문 초장문 질문과 경로.

    표의 경로 셀(`.pathText`)이 말줄임으로 접히는지, 질문 문단이 행 높이를
    무너뜨리지 않는지, 앱 이름이 카드를 밀어내지 않는지를 본다.
    """
    specs: list[dict[str, Any]] = [
        {
            "method": "GET",
            "path": LONG_PATH_KO,
            "summary": (
                "반도체 웨이퍼 불량을 공정 스텝·라인·설비·교대조 단위로 세분화해 "
                "일간으로 집계하는 조회 쿼리입니다. 기간은 반드시 지정해야 합니다."
            ),
            "descriptionLength": 412,
            "hasParamDescription": True,
        },
        {
            "method": "GET",
            "path": LONG_PATH_EN,
            "summary": None,
            "descriptionLength": 0,
            "hasParamDescription": False,
        },
    ]
    keys = [(str(s["method"]), str(s["path"])) for s in specs]
    plan = [
        ("NONE", 0, LONG_QUESTION_KO),
        ("NONE", 0, LONG_QUESTION_EN),
        ("TOP1_ONLY", 0, LONG_QUESTION_KO),
        ("NONE", 0, "웨이퍼 불량 집계"),
        ("TOP3", 1, LONG_QUESTION_EN),
        ("TOP3", 1, LONG_QUESTION_KO),
        ("TOP3", 1, "defect aggregation by step"),
        ("TOP1_ONLY", 1, LONG_QUESTION_EN),
    ]
    questions = [
        make_question(
            no=i + 1,
            text=text,
            qtype=ALL_TYPES[i % len(ALL_TYPES)],
            expected=keys[which],
            scope=scope,
            others=[*keys, *CROSS_APP_KEYS],
        )
        for i, (scope, which, text) in enumerate(plan)
    ]
    return build_report(
        trace_id="ELONG",
        evaluated_at=f"{BASE_DATE}-06T10:00:00+09:00",
        target={
            "appId": "wafer-defect-daily-aggregation-reporting-service",
            "appName": "반도체 웨이퍼 불량 일간 집계 리포팅 서비스 (공정 스텝·라인·설비·교대조 세분화)",
            "specVersion": "v12-hotfix-20260606",
            "owner": "품질분석팀 / Quality Analytics Team (반도체 공정 데이터 파트)",
        },
        query_specs=specs,
        questions=questions,
        type_order=ALL_TYPES,
        recommendations=[
            {
                "order": 1,
                "title": "설명(Description) 보강",
                "description": (
                    "영문 경로 쿼리에 설명이 전혀 없어 한글 질문과 영문 질문 모두에서 "
                    "밀립니다. 경로 이름이 길다고 해서 검색이 그 뜻을 읽어내지는 않으므로, "
                    "무엇을 집계하는 쿼리인지 한 문단으로 적어두어야 합니다."
                ),
                "priority": "HIGH",
                "failShare": 75.0,
            }
        ],
        previous={
            "traceId": "ELONG0",
            "evaluatedAt": f"{BASE_DATE}-06T09:00:00+09:00",
            "top3Accuracy": 50.0,
        },
        raw_source={
            "toolVersion": "rageval-2.4.0-internal-build-20260606",
            "promptVersion": "qgen-2026Q2-long-context-variant",
            "generatedAt": f"{BASE_DATE}-06T09:55:00+09:00",
        },
        duration_ms=7300,
    )


# ---------------------------------------------------------------------------
# 직전 평가(A311) — 경계값이 아니라 **정합성 복구**
# ---------------------------------------------------------------------------

# v2 시점에 설명이 없거나 한 줄뿐이던 쿼리들. 개선 전 평가에서는 여기에 실패가 몰린다.
_EMPTY_QUERIES = {
    "/queries/step-cycle-time",
    "/queries/operator-shift",
    "/queries/chamber-sensor-trend",
}
_POOR_QUERIES = {
    "/queries/equipment-downtime",
    "/queries/recipe-history",
    "/queries/alarm-history",
}
_WEAK_QUERIES = _EMPTY_QUERIES | _POOR_QUERIES


def _degrade_to_top3(question: dict[str, Any], pool: list[tuple[str, str]]) -> None:
    """Top-3 안에 있던 기대 쿼리를 상위 결과에서 밀어낸다 (완전 실패로)."""
    expected = (question["expected"]["method"], question["expected"]["path"])
    present = {(r["method"], r["path"]) for r in question["top3"]}
    replacement = next((key for key in pool if key not in present), None)
    if replacement is None:
        raise ValueError(f"밀어낼 자리를 만들 수 없습니다: {expected}")

    for result in question["top3"]:
        if (result["method"], result["path"]) == expected:
            result["method"], result["path"] = replacement

    head = question["top3"][0]
    question["top1"] = {"method": head["method"], "path": head["path"], "score": head["score"]}
    question["top1Hit"] = False
    question["top3Hit"] = False
    question["failureScope"] = "TOP3"
    question["expectedRank"] = None
    question["failureCategory"] = (
        "DESCRIPTION_MISSING"
        if question["expected"]["path"] in _EMPTY_QUERIES
        else "DESCRIPTION_WEAK"
    )
    question["reason"] = (
        "설명이 없어 질문의 의도와 이어지지 않음"
        if question["expected"]["path"] in _EMPTY_QUERIES
        else "설명이 한 줄뿐이라 다른 쿼리에 밀림"
    )


def _degrade_to_top1_only(question: dict[str, Any]) -> None:
    """1위였던 기대 쿼리를 2위로 내린다. Top-3 안에는 남는다."""
    first, second = question["top3"][0], question["top3"][1]
    first["method"], second["method"] = second["method"], first["method"]
    first["path"], second["path"] = second["path"], first["path"]

    question["top1"] = {"method": first["method"], "path": first["path"], "score": first["score"]}
    question["top1Hit"] = False
    question["top3Hit"] = True
    question["failureScope"] = "TOP1_ONLY"
    question["expectedRank"] = 2
    question["failureCategory"] = "SIMILAR_RESOURCE"
    question["reason"] = "이름이 비슷한 쿼리가 1위를 차지함"


def fixture_previous_run() -> dict[str, Any]:
    """A492 의 직전 평가(A311) — **A492 에서 유도한다**.

    개선 전 상태이므로 A492 보다 나빠야 한다. 손으로 요약 숫자만 바꿔 적으면
    게이지는 64% 인데 아래 표에는 78건이 성공으로 남아 화면이 자기 모순에 빠진다.
    그래서 문항을 실제로 악화시키고 나머지 수치를 전부 다시 유도한다.

    목표치는 A492 의 `previous` 가 이미 약속한 값이다 — Top-3 64.0 / Top-1 50.0.
    그 약속을 지키려면 완전 실패 36건, Top-1 만 실패 14건, 성공 50건이 되어야 한다.
    """
    base = json.loads((FIXTURE_DIR / "eval_A492.json").read_text(encoding="utf-8"))
    questions = json.loads(json.dumps(base["questions"]))  # 깊은 복사
    pool = [(q["method"], q["path"]) for q in base["queries"]]

    def weak_first(question: dict[str, Any]) -> tuple[int, int]:
        # 설명이 부실한 쿼리부터 악화시킨다. 개선 전이라면 그쪽이 먼저 무너져 있다.
        return (0 if question["expected"]["path"] in _WEAK_QUERIES else 1, question["no"])

    top1_only = sorted((q for q in questions if q["failureScope"] == "TOP1_ONLY"), key=weak_first)
    for question in top1_only[:14]:
        _degrade_to_top3(question, pool)

    succeeded = sorted((q for q in questions if q["failureScope"] == "NONE"), key=weak_first)
    for question in succeeded[:11]:
        _degrade_to_top1_only(question)

    specs = [
        {
            "method": q["method"],
            "path": q["path"],
            "summary": q["summary"],
            "descriptionLength": q["descriptionLength"],
            "hasParamDescription": q["hasParamDescription"],
        }
        for q in base["queries"]
    ]

    return build_report(
        trace_id="A311",
        evaluated_at="2026-07-15T09:12:00+09:00",
        target={
            "appId": "mf-worker",
            "appName": "MF Worker",
            "specVersion": "v3",
            "owner": "데이터플랫폼팀",
        },
        query_specs=specs,
        questions=questions,
        type_order=ALL_TYPES,
        recommendations=[
            {
                "order": 1,
                "title": "설명(Description) 보강",
                "description": "설명이 아예 없는 조회 쿼리 3개(스텝 사이클타임, 작업자 교대, 챔버 센서 추이)에 완전 실패가 몰려 있습니다. summary와 description을 채우는 것만으로 가장 크게 개선됩니다.",
                "priority": "HIGH",
                "failShare": 58.3,
            },
            {
                "order": 2,
                "title": "현장 용어·동의어 추가",
                "description": "현장에서는 'eqp', '택트타임', '계보'처럼 명세에 없는 표현으로 검색합니다. 설명 안에 실제 현장 표현을 함께 적어두면 한영 혼합 질문과 짧은 키워드 질문의 인식률이 올라갑니다.",
                "priority": "HIGH",
                "failShare": 41.7,
            },
            {
                "order": 3,
                "title": "유사 조회 구분 강화",
                "description": "수율 집계와 불량 집계처럼 이름이 비슷한 조회 쿼리가 서로의 상위 결과를 밀어냅니다. 각 설명에 '무엇을 집계하는지'를 한 줄 덧붙이면 혼동이 줄어듭니다.",
                "priority": "MEDIUM",
                "failShare": 33.3,
            },
        ],
        previous=None,
        raw_source={
            "toolVersion": "rageval-2.3.1",
            "promptVersion": "qgen-2026Q1",
            "generatedAt": "2026-07-15T08:55:00+09:00",
        },
        duration_ms=48210,
    )


BUILDERS = [
    fixture_previous_run,
    fixture_all_hit,
    fixture_all_fail,
    fixture_single_query,
    fixture_three_types,
    fixture_first_run,
    fixture_long_text,
]


def write_all(fixture_dir: Path = FIXTURE_DIR) -> list[Path]:
    written: list[Path] = []
    for build in BUILDERS:
        report = build()
        path = fixture_dir / f"eval_{report['traceId']}.json"
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


def main() -> None:
    for path in write_all():
        report = json.loads(path.read_text(encoding="utf-8"))
        summary = report["summary"]
        print(
            f"{path.name}: {summary['totalQuestions']}문항 · "
            f"Top-3 {summary['top3Accuracy']}% ({summary['top3Grade']}) · "
            f"쿼리 {report['target']['queryCount']}개 · "
            f"유형 {len(report['questionTypes'])}종"
        )


if __name__ == "__main__":
    main()
