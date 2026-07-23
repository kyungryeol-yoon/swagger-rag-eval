"""응답 계약 — 단일 진실 공급원.

`docs/contract.md` 의 구현체다. 계약이 바뀌면 **contract.md 를 먼저 고치고**
여기를 고친다 (`docs/prompts.md` §6 변경 전파 루프).

대시보드 화면 전체가 `EvaluationReport` 하나로 그려진다.

규약:
- 모든 비율은 0~100 실수. 0~1 소수 금지.
- 파이썬 쪽은 snake_case, 직렬화는 camelCase (alias).
- 시각은 전부 ISO 8601 + 타임존 문자열.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


def to_camel(name: str) -> str:
    """snake_case -> camelCase.

    숫자를 포함한 이름도 보존해야 한다: `top1_accuracy` -> `top1Accuracy`.
    (`str.title()` 은 `top1` 을 `Top1` 로 만들면서 뒤를 소문자로 눕히므로 쓰지 않는다.)
    """
    head, *rest = name.split("_")
    return head + "".join(word[:1].upper() + word[1:] for word in rest)


class ContractModel(BaseModel):
    """계약 모델 공통 설정."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


# ---------------------------------------------------------------------------
# Enum — 백엔드가 확정해서 내려준다. 프론트는 문자열 비교로 색을 정하지 않는다.
# ---------------------------------------------------------------------------


class Grade(StrEnum):
    """Top-3 인식률 등급. CRITICAL <70 / NEEDS_IMPROVEMENT 70~85 / FAIR 85~95 / GOOD >=95."""

    CRITICAL = "CRITICAL"
    NEEDS_IMPROVEMENT = "NEEDS_IMPROVEMENT"
    FAIR = "FAIR"
    GOOD = "GOOD"


class Priority(StrEnum):
    """권장 조치의 우선순위."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SearchMode(StrEnum):
    """검색 방식. HYBRID 는 BM25 + 벡터를 함께 쓴다."""

    BM25 = "BM25"
    VECTOR = "VECTOR"
    HYBRID = "HYBRID"


class QuestionType(StrEnum):
    """평가 문항의 유형."""

    DIRECT = "DIRECT"
    USER_NL = "USER_NL"
    DOMAIN_TERM = "DOMAIN_TERM"
    PARAMETER = "PARAMETER"
    ERROR_CASE = "ERROR_CASE"
    SHORT_KEYWORD = "SHORT_KEYWORD"
    MIXED_LANG = "MIXED_LANG"


class FailureCategory(StrEnum):
    """실패 원인 분류."""

    METHOD_MISMATCH = "METHOD_MISMATCH"
    SIMILAR_RESOURCE = "SIMILAR_RESOURCE"
    SYNONYM_MISS = "SYNONYM_MISS"
    DESCRIPTION_MISSING = "DESCRIPTION_MISSING"
    PARAM_MISSING = "PARAM_MISSING"
    OTHER = "OTHER"


# ---------------------------------------------------------------------------
# 구성 요소
# ---------------------------------------------------------------------------


class TargetApp(ContractModel):
    """평가 대상이 된 DAC 앱.

    평가 단위는 **쿼리 하나가 아니라 앱 하나**다. DAC 이 앱마다 Swagger 를
    생성하므로 Swagger 1개 = 앱 1개이고, 그 안의 엔드포인트 하나가 등록된
    SELECT 쿼리 하나다 (docs/contract.md §0).
    """

    app_id: str = Field(description="DAC 앱 식별자. 예: mf-worker")
    app_name: str = Field(description="화면에 표시할 앱 이름.")
    spec_version: str = Field(
        description="Swagger 버전. 재생성 전후를 구분하는 근거이므로 화면에 반드시 표기한다."
    )
    query_count: int = Field(
        ge=0, description="앱에 등록된 쿼리 수. queries 배열의 길이와 같다."
    )
    owner: str | None = Field(
        default=None,
        description="앱 담당 조직 또는 담당자. DAC 이 제공하지 않으면 null.",
    )


class QueryStat(ContractModel):
    """쿼리 1개의 설명 품질과 인식률.

    **이 화면의 실질 산출물이다.** 어느 쿼리의 설명을 고쳐야 하는지가
    여기서 정해지고, 그 목록이 그대로 재생성 요청 대상이 된다.
    """

    path: str = Field(description="쿼리 경로. 경로 파라미터는 중괄호 표기.")
    method: str = Field(description="HTTP 메서드. 대문자로 내려준다.")
    summary: str | None = Field(
        default=None,
        description="명세에 적힌 요약. 없으면 null — 비어 있다는 사실 자체가 평가 결과다.",
    )
    description_length: int = Field(
        ge=0,
        description="설명 길이(글자 수). 0 이면 설명이 없다. 길이만으로도 부실한 쿼리가 드러난다.",
    )
    has_param_description: bool = Field(
        description="파라미터 설명이 하나라도 있는지. 파라미터 기반 질문의 인식률과 직결된다."
    )
    question_count: int = Field(
        ge=0, description="이 쿼리를 기대 결과로 삼은 문항 수. 모든 쿼리의 합은 totalQuestions."
    )
    top3_accuracy: float = Field(
        ge=0, le=100, description="이 쿼리를 기대한 문항들의 Top-3 인식률(%)."
    )
    grade: Grade = Field(description="이 쿼리의 등급. 백엔드가 확정해 내려준다.")
    needs_regeneration: bool = Field(
        description=(
            "재생성 요청 대상 후보인지. **백엔드가 판단한다** — 프론트가 인식률로 "
            "다시 계산하지 않는다. 판정 기준은 docs/open-questions.md #53 참고."
        )
    )


class EvaluationMeta(ContractModel):
    """재현성 정보. 같은 조건으로 다시 돌릴 수 있어야 한다."""

    embedding_model: str = Field(description="검색에 사용한 임베딩 모델 이름. 예: bge-m3")
    search_mode: SearchMode = Field(description="검색 방식. HYBRID 는 BM25 + 벡터 병용.")
    top_k: int = Field(ge=1, description="Hit 판정 기준이 되는 상위 결과 개수. 보통 3.")
    question_source: str = Field(
        description=(
            "평가 문항의 출처. 신뢰도 판단 근거로 화면에 노출한다. "
            "예: LLM_GENERATED_HUMAN_REVIEWED"
        )
    )
    duration_ms: int = Field(ge=0, description="평가 전체 소요 시간(밀리초).")


class EvaluationSummary(ContractModel):
    """대시보드 상단 요약 지표."""

    total_questions: int = Field(ge=0, description="평가에 사용한 전체 문항 수.")
    top1_accuracy: float = Field(
        ge=0, le=100, description="1위 결과가 기대 API와 일치한 비율(%). 0~100 실수."
    )
    top3_accuracy: float = Field(
        ge=0,
        le=100,
        description="상위 3개 안에 기대 API가 포함된 비율(%). 게이지에 표시되는 대표 수치.",
    )
    top1_fail_count: int = Field(ge=0, description="1위가 기대 API와 달랐던 문항 수.")
    top3_fail_count: int = Field(
        ge=0, description="상위 3개 안에 기대 API가 없었던 문항 수. 실패 테이블의 전체 건수."
    )
    grade: Grade = Field(description="top3Accuracy 로 산출한 등급. 백엔드가 확정해 내려준다.")


class QuestionTypeStat(ContractModel):
    """문항 유형별 분포와 인식률.

    분포만으로는 액션이 안 나온다. "한영 혼합 질문이 40%" 처럼
    유형별 인식률이 같이 보여야 무엇을 고칠지 정해진다.
    """

    type: QuestionType = Field(description="문항 유형 enum.")
    label: str = Field(description="화면에 표시할 한글 라벨. 예: 한영 혼합 질문")
    count: int = Field(ge=0, description="해당 유형의 문항 수. 모든 유형의 합은 totalQuestions 와 같다.")
    ratio: float = Field(ge=0, le=100, description="전체 문항 중 이 유형이 차지하는 비율(%).")
    top3_accuracy: float = Field(
        ge=0, le=100, description="이 유형에서의 Top-3 인식률(%). 유형 간 편차가 개선 우선순위를 정한다."
    )


class Recommendation(ContractModel):
    """권장 조치."""

    order: int = Field(ge=1, description="표시 순서. 1이 가장 먼저.")
    title: str = Field(description="조치 제목. 예: 설명(Description) 보강")
    description: str = Field(description="왜 이 조치가 필요한지에 대한 한두 문장 설명.")
    priority: Priority = Field(description="우선순위 enum. 뱃지 색은 enum 매핑 테이블에서 정한다.")
    fail_share: float = Field(
        ge=0,
        le=100,
        description=(
            "이 원인이 관여한 실패의 비중(%). "
            "한 실패에 원인이 여럿일 수 있어 **모든 권장 조치의 합은 100을 넘을 수 있다**. "
            "화면에 '원인 중복 집계' 각주를 반드시 붙인다."
        ),
    )


class ExpectedApi(ContractModel):
    """문항이 찾아냈어야 하는 정답 쿼리."""

    method: str = Field(description="기대 쿼리의 HTTP 메서드.")
    path: str = Field(description="기대 쿼리의 경로.")


class SearchResult(ContractModel):
    """검색 결과 1건."""

    rank: int = Field(ge=1, description="검색 순위. 1이 가장 유사.")
    method: str = Field(description="검색된 쿼리의 HTTP 메서드.")
    path: str = Field(description="검색된 쿼리의 경로.")
    score: float = Field(
        ge=0,
        le=1,
        description="정규화된 유사도 점수(0~1). 아깝게 놓친 건지 완전히 빗나간 건지 구분하는 근거.",
    )


class Failure(ContractModel):
    """실패한 문항 1건."""

    id: str = Field(description="문항 식별자. 예: q_017")
    question: str = Field(description="실제로 던진 질문 문장.")
    question_type: QuestionType = Field(description="문항 유형 enum.")
    expected: ExpectedApi = Field(description="찾아냈어야 하는 정답 쿼리.")
    results: list[SearchResult] = Field(
        description="실제 검색 결과 상위 목록. 보통 topK 개."
    )
    hit: bool = Field(description="Top-K 안에 기대 쿼리가 있었는지. 실패 목록이므로 항상 false.")
    expected_rank: int | None = Field(
        default=None,
        ge=1,
        description="기대 쿼리가 전체 검색 결과에서 몇 위였는지. **Top-N 밖이면 null**.",
    )
    failure_category: FailureCategory = Field(description="실패 원인 분류 enum.")
    reason: str = Field(description="사람이 읽을 실패 원인 설명. 한 문장.")


class PreviousEvaluation(ContractModel):
    """직전 평가 결과. Before/After 델타의 기준점."""

    trace_id: str = Field(description="직전 평가의 추적 ID.")
    evaluated_at: str = Field(description="직전 평가 시각(ISO 8601 + 타임존).")
    top3_accuracy: float = Field(ge=0, le=100, description="직전 평가의 Top-3 인식률(%).")


# ---------------------------------------------------------------------------
# 최상위 응답
# ---------------------------------------------------------------------------


class EvaluationReport(ContractModel):
    """GET /api/v1/evaluations/{trace_id} 의 응답.

    대시보드 전체가 이 하나로 그려진다.
    """

    trace_id: str = Field(description="평가 실행의 추적 ID. 예: A492")
    evaluated_at: str = Field(description="평가 실행 시각(ISO 8601 + 타임존).")
    target: TargetApp = Field(description="평가 대상 DAC 앱.")
    meta: EvaluationMeta = Field(description="재현성 정보.")
    summary: EvaluationSummary = Field(description="요약 지표.")
    queries: list[QueryStat] = Field(
        description=(
            "쿼리별 설명 품질과 인식률. 앱에 등록된 쿼리 전부를 내려준다. "
            "이 목록에서 needsRegeneration 인 것이 재생성 요청 대상이 된다."
        )
    )
    question_types: list[QuestionTypeStat] = Field(
        description="문항 유형별 분포와 인식률. 7종 전부 내려준다."
    )
    recommendations: list[Recommendation] = Field(description="권장 조치 목록. order 오름차순.")
    failures: list[Failure] = Field(
        description="실패한 문항 전체. 건수는 summary.top3FailCount 와 같다."
    )
    previous: PreviousEvaluation | None = Field(
        default=None,
        description="직전 평가 결과. 이전 평가가 없으면 null 이며 프론트는 델타 뱃지를 숨긴다.",
    )
