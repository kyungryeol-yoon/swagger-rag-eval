"""평가 결과 fixture 를 만든다 (Phase 12 — 쿼리 1개 단위).

    cd backend && uv run python -m app.scripts.make_fixtures
    # 또는 저장소 루트에서
    make fixtures

**출력물은 생성물이 아니라 커밋 대상이다.** 폐쇄망에서는 파일을 복사해 옮기므로
스크립트를 돌릴 수 없는 환경이 있다. 계약이 바뀌면 이 스크립트를 다시 돌려
결과 JSON 을 함께 커밋한다.

수치는 직접 적지 않고 문항 목록에서 **전부 유도한다**. 손으로 적으면 요약과
표가 서로 다른 말을 하게 되고, 그건 fixture 가 아니라 새 버그다.

만드는 것 — 파일명은 `eval_{queryId}.json`:

    q-lot-status          정상. 설명 충실, Top-3 78%
    q-step-cycle-time     설명이 아예 없는 쿼리. 인식률 매우 낮음(12%)
    q-wafer-yield         인식률 100% — 실패 0건, 권장 조치도 없음
    q-no-result           검색 결과가 아예 없는 문항(top3: null)이 다수
    q-wafer-defect-…      한글·영문 초장문 질문·경로·설명 (queryId 자체도 길다)

경계값을 따로 두지 않고 **각 쿼리가 하나의 경계를 대표하게** 했다. 평가 단위가
쿼리 1개가 되면서 "이 쿼리는 어떤 상태인가" 가 곧 경계값이 되었기 때문이다.
"""

import json
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"


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

# 문항 유형별 한글 라벨. **자리표시다** (open-questions #69).
TYPE_LABELS: dict[str, str] = {
    "DIRECT": "직접 질문",
    "USER_NL": "사용자 자연어 질문",
    "DOMAIN_TERM": "업무 용어 질문",
    "PARAMETER": "파라미터 기반 질문",
    "ERROR_CASE": "오류/에러 상황 질문",
    "SHORT_KEYWORD": "짧은 키워드 질문",
    "MIXED_LANG": "한영 혼합 질문",
}
ALL_TYPES = list(TYPE_LABELS)

# 실패 범위별 원인·설명. 성공(NONE)이면 둘 다 null 이어야 한다 (계약).
FAIL_REASON: dict[str, tuple[str, str]] = {
    "TOP1_ONLY": ("SIMILAR_RESOURCE", "이름이 비슷한 쿼리가 1위를 차지함"),
    "TOP3": ("DESCRIPTION_MISSING", "설명이 없어 질문의 의도와 이어지지 않음"),
}

# 정렬 기준: TOP3 → TOP1_ONLY → NONE (계약 §2).
SCOPE_ORDER = {"TOP3": 0, "TOP1_ONLY": 1, "NONE": 2}

# 오답으로 섞여 들어오는 다른 쿼리들. 검색 코퍼스는 이 앱·이 쿼리 밖까지 포함한다.
DISTRACTORS: list[tuple[str, str]] = [
    ("q-wafer-yield", "/queries/wafer-yield-daily"),
    ("q-defect-summary", "/queries/defect-summary"),
    ("q-equipment-downtime", "/queries/equipment-downtime"),
    ("q-lot-trace", "/queries/lot-trace"),
    ("q-inventory-wip", "/queries/inventory-wip"),
    ("q-operator-shift", "/queries/operator-shift"),
]

SCORES = [0.91, 0.74, 0.62]


def make_question(
    *,
    no: int,
    text: str,
    qtype: str,
    scope: str,
    target: tuple[str, str],
    distractors: list[tuple[str, str]],
    result_count: int = 3,
) -> dict[str, Any]:
    """문항 1개. hit 플래그·순위·원인을 scope 하나에서 전부 유도한다.

    Args:
        no: 표시 순번.
        text: 실제로 던진 질문.
        qtype: 문항 유형 enum.
        scope: NONE / TOP1_ONLY / TOP3.
        target: 평가 대상 쿼리 (queryId, path). 100문항의 정답이 전부 이것이다.
        distractors: 오답 후보. 대상 쿼리는 자동으로 빠진다.
        result_count: 검색 결과 개수. **0 이면 top3 가 null 이다** — 유사도 하한을
            넘는 결과가 없는 경우를 재현한다.
    """
    pool = [key for key in distractors if key[0] != target[0]]

    if result_count == 0:
        # 결과가 하나도 없으면 성공일 수 없다.
        if scope != "TOP3":
            raise ValueError(f"검색 결과가 없으면 TOP3 실패여야 한다: no={no}")
        return {
            "no": no,
            "question": text,
            "questionType": qtype,
            "top3": None,
            "top1Hit": False,
            "top3Hit": False,
            "failureScope": "TOP3",
            "expectedRank": None,
            "failureCategory": "KEYWORD_MISMATCH",
            "reason": "유사도 하한을 넘는 결과가 없음",
        }

    def at(i: int) -> tuple[str, str]:
        return pool[i % len(pool)]

    if scope == "NONE":
        ranked = [target, *(at(no + i) for i in range(result_count - 1))]
    elif scope == "TOP1_ONLY":
        if result_count < 2:
            raise ValueError(f"Top-1 실패는 결과가 2개 이상이어야 한다: no={no}")
        ranked = [at(no), target, *(at(no + 1 + i) for i in range(result_count - 2))]
    else:
        ranked = [at(no + i) for i in range(result_count)]

    top3 = [
        {"rank": i + 1, "queryId": qid, "path": path, "score": score}
        for i, ((qid, path), score) in enumerate(zip(ranked, SCORES, strict=False))
    ]

    # 성공(NONE)이면 둘 다 None 이다 — 계약이 그렇게 요구한다.
    category: str | None
    reason: str | None
    category, reason = FAIL_REASON.get(scope, (None, None))
    expected_rank = {"NONE": 1, "TOP1_ONLY": 2}.get(scope)

    return {
        "no": no,
        "question": text,
        "questionType": qtype,
        "top3": top3,
        "top1Hit": scope == "NONE",
        "top3Hit": scope in ("NONE", "TOP1_ONLY"),
        "failureScope": scope,
        "expectedRank": expected_rank,
        "failureCategory": category,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# 리포트 조립 — 요약·유형 통계를 문항에서 유도한다
# ---------------------------------------------------------------------------


def build_report(
    *,
    trace_id: str,
    evaluated_at: str,
    target: dict[str, Any],
    questions: list[dict[str, Any]],
    type_order: list[str],
    recommendations: list[dict[str, Any]],
    duration_ms: int,
    search_mode: str = "HYBRID",
) -> dict[str, Any]:
    """계약 형태의 평가 리포트 하나를 만든다."""
    questions = sorted(questions, key=lambda q: (SCOPE_ORDER[q["failureScope"]], q["no"]))
    total = len(questions)

    top1_hits = sum(1 for q in questions if q["top1Hit"])
    top3_hits = sum(1 for q in questions if q["top3Hit"])
    top1_accuracy = pct(top1_hits, total)
    top3_accuracy = pct(top3_hits, total)

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

    return {
        "traceId": trace_id,
        "evaluatedAt": evaluated_at,
        "target": target,
        "meta": {
            "embeddingModel": "bge-m3",
            "searchMode": search_mode,
            "topK": 3,
            # summary.totalQuestions 와 반드시 같다. 스키마가 검증한다.
            "questionCount": total,
            "durationMs": duration_ms,
        },
        "summary": {
            "totalQuestions": total,
            "top1Accuracy": top1_accuracy,
            "top3Accuracy": top3_accuracy,
            "top1FailCount": total - top1_hits,
            "top3FailCount": total - top3_hits,
            "top1Grade": grade_for(top1_accuracy),
            "top3Grade": grade_for(top3_accuracy),
        },
        "questionTypes": question_types,
        "recommendations": recommendations,
        "questions": questions,
    }


# ---------------------------------------------------------------------------
# 질문 소재
# ---------------------------------------------------------------------------

LOT_STATUS_QUESTIONS = [
    "랏 번호로 지금 어느 공정에 있는지 확인하려면 어떤 쿼리를 쓰나요?",
    "랏 현재 공정 단계를 조회하고 싶습니다",
    "lot status 조회 쿼리 있나요?",
    "특정 랏이 지금 어디까지 갔는지 보려면?",
    "랏 진행 상태를 스텝별로 확인하는 방법",
    "랏 번호 넣으면 현재 위치 나오는 조회",
    "지금 이 랏 어느 설비에 있어?",
    "랏 공정 단계 확인",
    "lot 진행현황 좀 알려줘",
    "랏이 어느 스텝에서 멈춰 있는지 확인하려면 어떻게 하나요?",
]

CYCLE_TIME_QUESTIONS = [
    "스텝별 사이클타임 추이를 보려면 무엇을 호출하나요?",
    "택트타임이 튀는 스텝을 찾고 싶습니다",
    "step cycle time 조회 query 있나요?",
    "공정별 소요 시간 통계",
    "사이클타임",
    "각 스텝이 얼마나 걸리는지 보려면?",
    "스텝 사이클타임이 비어 있는 구간을 확인하려면 어떤 쿼리를 쓰나요?",
    "cycle time 이 이상한 구간 조회",
    "스텝별 처리 시간 평균과 편차를 같이 보고 싶어요",
    "택트 타임 추이",
]

YIELD_QUESTIONS = [
    "어제 웨이퍼 수율을 라인별로 보고 싶습니다",
    "일별 수율 집계 조회",
    "wafer yield 어제 기준으로 알려줘",
    "수율이 떨어진 날을 찾으려면 어떤 쿼리를 쓰나요?",
    "라인별 일간 수율",
    "웨이퍼 수율 추이를 기간으로 조회하려면?",
    "yield daily 집계",
    "어제 라인 수율 얼마야?",
    "일자별 웨이퍼 수율과 투입량을 같이 보고 싶습니다",
    "수율 집계 쿼리",
]

NONSENSE_QUESTIONS = [
    "asdf",
    "?????",
    "그거 있잖아 그거",
    "ㅁㄴㅇㄹ",
    "test test",
    "1234",
    "아무거나",
    "zzz",
]


def cycle(items: list[str], i: int) -> str:
    return items[i % len(items)]


# ---------------------------------------------------------------------------
# fixture 5종
# ---------------------------------------------------------------------------


def fixture_lot_status() -> dict[str, Any]:
    """정상 — 설명이 충실한 쿼리. Top-3 78%.

    화면의 기준 상태다. 성공·Top-1 실패·완전 실패가 섞여 있다.
    """
    target = ("q-lot-status", "/queries/lot-status")
    # 78% = 성공 61 + Top-1만 실패 17, 완전 실패 22
    plan = ["NONE"] * 61 + ["TOP1_ONLY"] * 17 + ["TOP3"] * 22
    questions = [
        make_question(
            no=i + 1,
            text=cycle(LOT_STATUS_QUESTIONS, i),
            qtype=ALL_TYPES[i % len(ALL_TYPES)],
            scope=scope,
            target=target,
            distractors=DISTRACTORS,
        )
        for i, scope in enumerate(plan)
    ]
    return build_report(
        trace_id="R-8f31c2",
        evaluated_at="2026-07-30T11:38:00+09:00",
        target={
            "queryId": target[0],
            "appId": "mf-worker",
            "method": "GET",
            "path": target[1],
            "summary": "랏 현재 공정 단계 조회",
            "description": (
                "랏 번호를 입력하면 그 랏이 현재 어느 공정 스텝에 있는지, 어느 설비에 "
                "할당돼 있는지, 직전 스텝을 언제 빠져나왔는지를 함께 반환합니다. "
                "진행 중인 랏만 대상이며 완료된 랏은 이력 조회를 사용해야 합니다."
            ),
            "xQuestions": [
                "랏 번호로 지금 어느 공정에 있는지 확인하려면?",
                "이 랏이 어느 설비에 할당됐나요?",
                "랏 진행 상태 조회",
            ],
        },
        questions=questions,
        type_order=ALL_TYPES,
        recommendations=[
            {
                "order": 1,
                "title": "현장 용어·동의어 추가",
                "description": (
                    "현장에서는 'lot 진행현황', '어디까지 갔는지' 처럼 명세에 없는 표현으로 "
                    "찾습니다. description 에 이런 표현을 함께 적어두면 자연어 질문과 "
                    "짧은 키워드 질문의 인식률이 올라갑니다."
                ),
                "priority": "HIGH",
                "failShare": 54.5,
            },
            {
                "order": 2,
                "title": "유사 조회 구분 강화",
                "description": (
                    "랏 이력 조회(q-lot-trace)와 이름이 비슷해 서로의 상위 결과를 밀어냅니다. "
                    "'진행 중인 랏만' 이라는 범위를 summary 에도 드러내면 혼동이 줄어듭니다."
                ),
                "priority": "MEDIUM",
                "failShare": 31.8,
            },
        ],
        duration_ms=48210,
    )


def fixture_no_description() -> dict[str, Any]:
    """설명이 아예 없는 쿼리 — 인식률 매우 낮음(12%).

    summary 도 description 도 null 이고 x-question 도 없다. 화면이 그 사실을
    경고색으로 보여줘야 하는 fixture 다.
    """
    target = ("q-step-cycle-time", "/queries/step-cycle-time")
    plan = ["NONE"] * 8 + ["TOP1_ONLY"] * 4 + ["TOP3"] * 88
    questions = [
        make_question(
            no=i + 1,
            text=cycle(CYCLE_TIME_QUESTIONS, i),
            qtype=ALL_TYPES[i % len(ALL_TYPES)],
            scope=scope,
            target=target,
            distractors=DISTRACTORS,
        )
        for i, scope in enumerate(plan)
    ]
    return build_report(
        trace_id="R-2ac9e1",
        evaluated_at="2026-07-30T11:52:00+09:00",
        target={
            "queryId": target[0],
            "appId": "mf-worker",
            "method": "GET",
            "path": target[1],
            "summary": None,
            "description": None,
            "xQuestions": [],
        },
        questions=questions,
        type_order=ALL_TYPES,
        recommendations=[
            {
                "order": 1,
                "title": "설명(Description) 보강",
                "description": (
                    "summary 와 description 이 모두 비어 있습니다. 검색이 참고할 문장이 "
                    "경로 이름뿐이라 대부분의 질문을 놓칩니다. 이 하나만 채워도 가장 크게 "
                    "개선됩니다."
                ),
                "priority": "HIGH",
                "failShare": 88.6,
            },
            {
                "order": 2,
                "title": "예시 질문(x-question) 추가",
                "description": (
                    "명세에 예시 질문이 하나도 없습니다. 현장에서 실제로 쓰는 표현을 "
                    "2~3개 적어두면 짧은 키워드 질문이 걸립니다."
                ),
                "priority": "HIGH",
                "failShare": 45.5,
            },
            {
                "order": 3,
                "title": "현장 용어·동의어 추가",
                "description": "'택트타임' 처럼 현장에서만 쓰는 표현을 설명에 포함합니다.",
                "priority": "MEDIUM",
                "failShare": 27.3,
            },
        ],
        duration_ms=51900,
    )


def fixture_all_hit() -> dict[str, Any]:
    """인식률 100% — 실패 0건.

    권장 조치도 없다. "고칠 게 없을 때" 화면에 빈 카드가 남지 않는지 보는 fixture 다.
    """
    target = ("q-wafer-yield", "/queries/wafer-yield-daily")
    questions = [
        make_question(
            no=i + 1,
            text=cycle(YIELD_QUESTIONS, i),
            qtype=ALL_TYPES[i % len(ALL_TYPES)],
            scope="NONE",
            target=target,
            distractors=DISTRACTORS,
        )
        for i in range(100)
    ]
    return build_report(
        trace_id="R-55d0aa",
        evaluated_at="2026-07-30T12:10:00+09:00",
        target={
            "queryId": target[0],
            "appId": "mf-worker",
            "method": "GET",
            "path": target[1],
            "summary": "일별 웨이퍼 수율 집계 조회",
            "description": (
                "지정한 기간의 웨이퍼 수율을 일자별·라인별로 집계합니다. 투입량, 양품 수, "
                "수율(%)을 함께 반환하며 기간은 최대 90일까지 지정할 수 있습니다. "
                "현장에서는 '수율 집계', 'yield daily' 로도 부릅니다."
            ),
            "xQuestions": [
                "어제 웨이퍼 수율을 라인별로 보고 싶습니다",
                "일자별 수율 추이 조회",
                "yield daily 집계",
                "수율이 떨어진 날 찾기",
            ],
        },
        questions=questions,
        type_order=ALL_TYPES,
        recommendations=[],
        duration_ms=44100,
    )


def fixture_no_result() -> dict[str, Any]:
    """검색 결과가 아예 없는 문항(`top3: null`)이 섞인 경우.

    유사도 하한을 넘는 결과가 없으면 배열이 아니라 null 이 온다. 화면이 순위
    목록을 그리려다 깨지지 않는지 보는 fixture 다.
    """
    target = ("q-no-result", "/queries/chamber-sensor-trend")
    questions: list[dict[str, Any]] = []
    for i in range(100):
        no = i + 1
        # 20문항은 결과 없음, 12문항은 결과 1건뿐(3개 미만), 나머지는 정상 3건.
        if i % 5 == 0:
            questions.append(
                make_question(
                    no=no,
                    text=cycle(NONSENSE_QUESTIONS, i),
                    qtype="SHORT_KEYWORD",
                    scope="TOP3",
                    target=target,
                    distractors=DISTRACTORS,
                    result_count=0,
                )
            )
        elif i % 5 == 1:
            questions.append(
                make_question(
                    no=no,
                    text=cycle(CYCLE_TIME_QUESTIONS, i),
                    qtype=ALL_TYPES[i % len(ALL_TYPES)],
                    scope="NONE",
                    target=target,
                    distractors=DISTRACTORS,
                    result_count=1,
                )
            )
        else:
            questions.append(
                make_question(
                    no=no,
                    text=cycle(CYCLE_TIME_QUESTIONS, i),
                    qtype=ALL_TYPES[i % len(ALL_TYPES)],
                    scope="TOP1_ONLY" if i % 3 == 0 else "NONE",
                    target=target,
                    distractors=DISTRACTORS,
                )
            )
    return build_report(
        trace_id="R-71b4f0",
        evaluated_at="2026-07-30T12:24:00+09:00",
        target={
            "queryId": target[0],
            "appId": None,
            "method": "GET",
            "path": target[1],
            "summary": "챔버 센서 추이",
            "description": None,
            "xQuestions": [],
        },
        questions=questions,
        type_order=ALL_TYPES,
        recommendations=[
            {
                "order": 1,
                "title": "설명(Description) 보강",
                "description": (
                    "summary 한 줄만 있고 description 이 없습니다. 짧은 키워드나 의미 없는 "
                    "입력에서는 유사도 하한을 넘는 결과가 아예 나오지 않습니다."
                ),
                "priority": "HIGH",
                "failShare": 62.0,
            }
        ],
        duration_ms=39800,
        search_mode="VECTOR",
    )


LONG_PATH = (
    "/queries/반도체-웨이퍼-불량-유형별-일간-집계-및-공정-스텝-매핑-리포트-조회"
    "-라인별-설비별-교대조별-세분화-포함"
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
    """한글·영문 초장문 질문·경로·설명.

    표의 경로 셀이 말줄임으로 접히는지, 질문 문단이 행 높이를 무너뜨리지 않는지,
    카드의 description 이 카드를 밀어내지 않는지 본다.
    """
    target = ("q-wafer-defect-daily-aggregation-by-step-line-equipment-shift", LONG_PATH)
    texts = [LONG_QUESTION_KO, LONG_QUESTION_EN, "웨이퍼 불량 집계", "defect aggregation by step"]
    plan = ["NONE"] * 40 + ["TOP1_ONLY"] * 20 + ["TOP3"] * 40
    questions = [
        make_question(
            no=i + 1,
            text=texts[i % len(texts)],
            qtype=ALL_TYPES[i % len(ALL_TYPES)],
            scope=scope,
            target=target,
            distractors=DISTRACTORS,
        )
        for i, scope in enumerate(plan)
    ]
    return build_report(
        trace_id="R-c4e7d9-internal-build-20260730-long-trace-identifier",
        evaluated_at="2026-07-30T12:41:00+09:00",
        target={
            "queryId": target[0],
            "appId": "wafer-defect-daily-aggregation-reporting-service",
            "method": "GET",
            "path": target[1],
            "summary": (
                "반도체 웨이퍼 불량을 공정 스텝·라인·설비·교대조 단위로 세분화해 일간으로 "
                "집계하는 조회 쿼리입니다 (기간 필수 지정)"
            ),
            "description": (
                "지정한 기간 동안 발생한 웨이퍼 불량을 공정 스텝, 라인, 설비 번호, 교대조의 "
                "네 축으로 나누어 일자별로 집계합니다. 불량 유형별 건수와 전체 투입량 대비 "
                "불량률을 함께 반환하며, 교대조는 사내 3교대 기준(A/B/C)을 따릅니다. "
                "기간은 반드시 지정해야 하고 최대 31일까지 조회할 수 있습니다. 그보다 긴 "
                "기간이 필요하면 월간 집계 쿼리를 사용해야 하며, 이 쿼리는 완료된 랏만 "
                "대상으로 하므로 진행 중인 랏의 불량은 포함되지 않습니다. 현장에서는 "
                "'불량 집계', 'defect daily' 로도 부릅니다."
            ),
            "xQuestions": [
                LONG_QUESTION_KO,
                LONG_QUESTION_EN,
                "웨이퍼 불량을 스텝별로 집계하려면?",
            ],
        },
        questions=questions,
        type_order=ALL_TYPES,
        recommendations=[
            {
                "order": 1,
                "title": "설명(Description) 보강",
                "description": (
                    "설명은 길지만 현장 표현이 빠져 있습니다. 경로 이름이 길다고 해서 검색이 "
                    "그 뜻을 읽어내지는 않으므로, 무엇을 집계하는 쿼리인지를 짧은 표현으로도 "
                    "함께 적어두어야 합니다."
                ),
                "priority": "HIGH",
                "failShare": 40.0,
            }
        ],
        duration_ms=61200,
    )


BUILDERS = [
    fixture_lot_status,
    fixture_no_description,
    fixture_all_hit,
    fixture_no_result,
    fixture_long_text,
]


def write_all(fixture_dir: Path = FIXTURE_DIR) -> list[Path]:
    written: list[Path] = []
    for build in BUILDERS:
        report = build()
        path = fixture_dir / f"eval_{report['target']['queryId']}.json"
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


def main() -> None:
    for path in write_all():
        report = json.loads(path.read_text(encoding="utf-8"))
        s = report["summary"]
        no_result = sum(1 for q in report["questions"] if q["top3"] is None)
        print(
            f"{path.name}: {s['totalQuestions']}문항 · "
            f"Top-3 {s['top3Accuracy']}% ({s['top3Grade']}) · "
            f"Top-1 {s['top1Accuracy']}% · "
            f"결과없음 {no_result}건 · "
            f"권장조치 {len(report['recommendations'])}개"
        )


if __name__ == "__main__":
    main()
