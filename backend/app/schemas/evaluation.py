"""응답 계약 — 단일 진실 공급원.

`docs/contract.md` 의 구현체다. 계약이 바뀌면 **contract.md 를 먼저 고치고**
여기를 고친다 (`docs/prompts.md` §6 변경 전파 루프).

대시보드 화면 전체가 `EvaluationReport` 하나로 그려진다.

**평가 단위는 쿼리 1개이고 결과를 저장하지 않는다** (Phase 12, contract.md §0).
그래서 이력·비교·목록에 쓰던 모델이 전부 없다 — `QueryStat`, `PreviousEvaluation`,
`EvaluationListItem`, `RawSource`, `ExpectedApi`, `TopResult`.

규약:
- 모든 비율은 0~100 실수. 0~1 소수 금지.
- 파이썬 쪽은 snake_case, 직렬화는 camelCase (alias).
- 시각은 전부 ISO 8601 + 타임존 문자열.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    """평가 문항의 유형.

    **자리표시다** (open-questions.md #69). 실제 분류 체계는 사내 질문 생성
    프롬프트가 정하며 미확정이다. 알려진 상위 갈래는 업무 관련 / 생성 관련 / 기타.

    **바꿀 때 고치는 곳은 여기와 `frontend/src/lib/enumTokens.ts` 두 곳뿐이다.**
    도넛·범례·막대·원인 필터는 그 두 테이블만 보고 그려진다. 프론트의 두 테이블은
    `Record<QuestionType, …>` 이라 enum 이 바뀌면 타입 에러로 빠진 항목을 알려준다.
    색이 모자라면 `globals.css` 의 `--chart-type-*` 도 함께 늘린다.
    """

    DIRECT = "DIRECT"
    USER_NL = "USER_NL"
    DOMAIN_TERM = "DOMAIN_TERM"
    PARAMETER = "PARAMETER"
    ERROR_CASE = "ERROR_CASE"
    SHORT_KEYWORD = "SHORT_KEYWORD"
    MIXED_LANG = "MIXED_LANG"


class FailureCategory(StrEnum):
    """실패 원인 분류. 담당자 확정 스펙 기준 (contract.md §3)."""

    SIMILAR_RESOURCE = "SIMILAR_RESOURCE"
    DESCRIPTION_MISSING = "DESCRIPTION_MISSING"
    DESCRIPTION_WEAK = "DESCRIPTION_WEAK"
    KEYWORD_MISMATCH = "KEYWORD_MISMATCH"
    DOMAIN_TERM_MISSING = "DOMAIN_TERM_MISSING"
    ERROR_CASE_MISSING = "ERROR_CASE_MISSING"
    PARAM_MISSING = "PARAM_MISSING"
    # DAC 이 단일 메서드면 쓰이지 않는다. enum 은 유지한다 (open-questions #50).
    METHOD_MISMATCH = "METHOD_MISMATCH"
    OTHER = "OTHER"


class FailureScope(StrEnum):
    """문항의 실패 범위.

    평가 대상은 실패 22건이 아니라 문항 100개 전체다. 각 문항이 어디까지
    성공했는지를 이 값으로 나눈다.
    """

    NONE = "NONE"  # Top-1 부터 맞음 (성공)
    TOP1_ONLY = "TOP1_ONLY"  # Top-1 은 틀렸으나 Top-3 안에는 있음
    TOP3 = "TOP3"  # Top-3 밖 (완전 실패)


# ---------------------------------------------------------------------------
# 구성 요소
# ---------------------------------------------------------------------------


class TargetQuery(ContractModel):
    """평가 대상이 된 DAC 쿼리 **하나**.

    이전 계약은 앱 하나를 평가하고 그 안의 쿼리 목록을 함께 내려줬다. 지금은
    쿼리 하나가 평가 단위다 (contract.md §0).

    `summary` / `description` / `x_questions` 를 그대로 실어 보내는 것은
    화면이 **"이 설명으로 검색이 걸릴 만한가" 를 사용자에게 직접 보여주기**
    위해서다. 인식률 숫자만 보여주면 무엇을 고쳐야 할지 알 수 없다.
    """

    query_id: str = Field(description="DAC 쿼리 식별자. 평가 요청의 query_id 와 같다.")
    app_id: str | None = Field(
        default=None,
        description="이 쿼리가 속한 DAC 앱. DAC 이 제공하지 않으면 null.",
    )
    method: str = Field(description="HTTP 메서드. 대문자로 내려준다.")
    path: str = Field(description="쿼리 경로. 경로 파라미터는 중괄호 표기.")
    summary: str | None = Field(
        default=None,
        description="명세의 summary. 없으면 null — **비어 있다는 사실 자체가 평가 결과다.**",
    )
    description: str | None = Field(
        default=None,
        description="명세의 description. 없으면 null. 검색이 참고하는 본문이다.",
    )
    x_questions: list[str] = Field(
        description=(
            "명세에 적힌 예시 질문(x-question). 없으면 **빈 배열**이다 — null 이 아니다. "
            "화면이 길이만 보고 분기할 수 있게 배열로 고정한다."
        ),
    )
    """예시 질문 목록.

    **기본값을 두지 않아 필수 필드로 만든다.** `default_factory=list` 를 주면
    OpenAPI 스키마에서 optional 이 되고, 생성된 프론트 타입이
    `string[] | undefined` 가 된다 — 그러면 화면마다 `?.length` 방어가 붙어
    "항상 배열" 이라는 계약이 무의미해진다.

    빠뜨리면 계약 위반으로 터지는 편이 낫다. 이 값을 만드는 것은 외부 시스템이
    아니라 이 백엔드의 파이프라인이다 (contract.md §0) — 빠졌다면 그쪽 버그다.
    """


class EvaluationMeta(ContractModel):
    """재현성 정보. 같은 조건으로 다시 돌릴 수 있어야 한다.

    저장 전제 필드(`raw_source`)와 문항 출처(`question_source`)가 빠졌다 —
    평가 엔진이 이 백엔드 안에 있고 질문은 항상 여기의 LLM 이 만든다.
    """

    embedding_model: str = Field(
        description="검색에 사용한 임베딩 모델. bge-m3 (1024차원, 코사인 유사도)."
    )
    search_mode: SearchMode = Field(description="검색 방식. HYBRID 는 BM25 + 벡터 병용.")
    top_k: int = Field(ge=1, description="Hit 판정 기준이 되는 상위 결과 개수. 보통 3.")
    question_count: int = Field(
        ge=0,
        description=(
            "LLM 이 생성한 질문 수. **summary.totalQuestions 와 반드시 같다** — "
            "같은 수가 두 자리에 있으므로 EvaluationReport 가 검증한다."
        ),
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
    top1_fail_count: int = Field(ge=0, description="1위가 기대 쿼리와 달랐던 문항 수.")
    top3_fail_count: int = Field(
        ge=0, description="상위 3개 안에 기대 쿼리가 없었던 문항 수. 완전 실패 건수."
    )
    top1_grade: Grade = Field(
        description="top1Accuracy 로 산출한 등급. 백엔드가 확정해 내려준다."
    )
    top3_grade: Grade = Field(
        description=(
            "top3Accuracy 로 산출한 등급. 게이지에 표시되는 대표 등급. "
            "**Top-1 과 Top-3 의 등급 임계값이 다를 수 있다** (open-questions #54) — "
            "그래서 두 등급을 따로 내려준다."
        )
    )


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


class SearchResult(ContractModel):
    """검색 결과 1건 (순위 포함).

    `method` 가 없다. 결과를 식별하는 것은 `query_id` 이고 `path` 는 표시용이다 —
    DAC 쿼리는 전부 조회라 메서드가 구별에 기여하지 않는다 (open-questions #50).
    """

    rank: int = Field(ge=1, description="검색 순위. 1이 가장 유사.")
    query_id: str = Field(
        description=(
            "검색된 쿼리의 DAC 식별자. **hit 판정은 이 값과 target.queryId 를 비교한다** — "
            "path 가 아니다. 같은 path 가 다른 쿼리일 수 있다."
        )
    )
    path: str = Field(description="검색된 쿼리의 경로. 표시용이다.")
    score: float = Field(
        ge=0,
        le=1,
        description=(
            "코사인 유사도(0~1). bge-m3 임베딩끼리의 값이다. "
            "아깝게 놓친 건지 완전히 빗나간 건지 구분하는 근거."
        ),
    )


class QuestionResult(ContractModel):
    """생성된 질문 1개의 평가 결과.

    **평가 대상은 실패만이 아니라 질문 100개 전체다.** 성공한 문항도 여기 들어온다
    (성공이면 `failure_category` 와 `reason` 이 null).

    `expected` 가 없다 — 평가 대상이 쿼리 하나이므로 100문항의 정답이 전부
    `target` 과 같다. `top1` 도 없다 — 항상 `top3[0]` 과 같은 값이었다.
    """

    no: int = Field(ge=1, description="표시 순번(1~questionCount).")
    question: str = Field(description="LLM 이 생성해 실제로 던진 질문 문장.")
    question_type: QuestionType = Field(description="문항 유형 enum. 자리표시(#69).")
    top3: list[SearchResult] | None = Field(
        default=None,
        description=(
            "상위 검색 결과. **1~topK 개이거나, 결과가 한 건도 없으면 null 이다.** "
            "코퍼스가 작거나 유사도 하한에 걸리면 실제로 그렇다. "
            "화면은 길이를 3으로 가정하지 않는다."
        ),
    )
    top1_hit: bool = Field(
        description="1위가 평가 대상 쿼리였는지. top3[0].queryId == target.queryId."
    )
    top3_hit: bool = Field(description="상위 3개 안에 평가 대상 쿼리가 있었는지.")
    failure_scope: FailureScope = Field(
        description="실패 범위. NONE(성공) / TOP1_ONLY / TOP3. 결과 없음도 TOP3 다."
    )
    expected_rank: int | None = Field(
        default=None,
        ge=1,
        description=(
            "**평가 대상 쿼리가** 전체 검색 결과에서 몇 위였는지. "
            "Top-N 밖이거나 결과가 없으면 null."
        ),
    )
    failure_category: FailureCategory | None = Field(
        default=None,
        description="실패 원인 분류. **성공(NONE)이면 null**. 항목 전체 목록은 미확정(#70).",
    )
    reason: str | None = Field(
        default=None,
        description="사람이 읽을 실패 원인 설명. 성공이면 null.",
    )


class EvaluateRequest(ContractModel):
    """POST /api/v1/evaluations 의 요청 본문.

    DAC 이 `{"query_id": "..."}` 를 보낸다. 이 계약의 직렬화 규약은 camelCase 이고
    DAC 이 보내는 형태는 snake_case 라 둘이 어긋난다 — `populate_by_name` 덕분에
    **`query_id` 와 `queryId` 를 모두 받는다.** 그 불일치를 경계에서 흡수하고,
    응답은 규약대로 camelCase 하나만 쓴다 (contract.md §1).
    """

    query_id: str = Field(
        min_length=1,
        max_length=128,
        description="평가할 DAC 쿼리 식별자.",
    )


class EvaluationReport(ContractModel):
    """POST /api/v1/evaluations 의 응답.

    대시보드 전체가 이 하나로 그려진다.
    """

    trace_id: str = Field(
        description=(
            "이 실행 한 번을 가리키는 값. **저장되지 않는다** — 로그 대조용이며 "
            "나중에 이 ID 로 다시 조회할 수 없다 (open-questions #68)."
        )
    )
    evaluated_at: str = Field(description="평가 실행 시각(ISO 8601 + 타임존).")
    target: TargetQuery = Field(description="평가 대상 DAC 쿼리 하나.")
    meta: EvaluationMeta = Field(description="재현성 정보.")
    summary: EvaluationSummary = Field(description="요약 지표.")
    question_types: list[QuestionTypeStat] = Field(
        description="문항 유형별 분포와 인식률. 분류 체계는 자리표시(#69)."
    )
    recommendations: list[Recommendation] = Field(
        description="권장 조치 목록. order 오름차순. 항목 전체 목록은 미확정(#70)."
    )
    questions: list[QuestionResult] = Field(
        description=(
            "생성된 질문 전체(성공 포함). 건수는 totalQuestions 와 같다. "
            "정렬: TOP3 실패 → TOP1_ONLY 실패 → 성공, 그 안에서 no 오름차순."
        )
    )

    @model_validator(mode="after")
    def check_question_count_agrees(self) -> "EvaluationReport":
        """같은 수를 담은 세 자리가 어긋나지 않게 잠근다.

        `meta.questionCount` / `summary.totalQuestions` / `len(questions)` 는
        모두 "생성한 질문 수" 다. 계약이 세 곳에 두고 있으므로 여기서 한 번
        확인한다 — 어긋나면 화면이 "100문항 중" 이라고 써놓고 표에 98줄을 그린다.

        조용히 맞춰주지 않고 터뜨린다. 값이 어긋난 것은 평가 파이프라인의 버그이고,
        화면에서 반쯤 맞는 숫자를 보여주는 것보다 낫다.
        """
        counts = {
            "meta.questionCount": self.meta.question_count,
            "summary.totalQuestions": self.summary.total_questions,
            "len(questions)": len(self.questions),
        }
        if len(set(counts.values())) > 1:
            detail = ", ".join(f"{k}={v}" for k, v in counts.items())
            raise ValueError(f"질문 수가 서로 다릅니다: {detail}")
        return self
