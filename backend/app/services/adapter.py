"""평가 결과 → 계약(EvaluationReport) 검증 경계.

**계약 검증을 한곳으로 모은다.** 평가 파이프라인이 필드를 빠뜨리거나 형식이
어긋난 결과를 낼 수 있는데, 그걸 조용히 통과시키면 화면이 절반만 그려지거나
숫자가 비어 보인다. 어느 필드가 왜 틀렸는지를 붙여서 터뜨린다.

Phase 12 로 역할이 줄었다
---------------------------------------------------------------------------
이전에는 **외부 평가툴의 원본 JSON 을 계약으로 변환하는** 어댑터였다. 평가
엔진이 이 백엔드 안으로 들어오면서(contract.md §0) 변환할 원본이 없어졌고,
남은 일은 검증이다. 파이프라인이 계약 형태로 직접 만들면 되기 때문이다.

그래도 이 경계를 없애지 않는다 — 파이프라인이 내부에 있다는 것이 그 출력을
믿어도 된다는 뜻은 아니다. 100문항을 조립하는 코드가 수치를 어긋나게 만드는
쪽이 오히려 흔하다.
"""

import json
from typing import Any

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from app.schemas.evaluation import EvaluationReport

# 메시지에 나열할 오류 개수 상한. 필드 하나가 통째로 빠지면 하위 오류가
# 수십 개씩 딸려 오는데, 전부 찍으면 정작 첫 줄이 로그에서 밀린다.
_MAX_REPORTED = 12


class ContractViolation(ValueError):
    """평가 결과가 응답 계약을 만족하지 못한다.

    `pydantic.ValidationError` 를 그대로 올리지 않고 이 예외로 감싼다.
    호출부(저장소·라우터·평가 파이프라인)는 pydantic 을 알 필요가 없고,
    사람이 읽을 메시지 한 줄이면 충분하다.

    Attributes:
        source: 어디서 온 결과인지. 파일명이나 trace_id.
        problems: `필드경로: 사유` 목록. 사람이 읽는 용도다.
    """

    def __init__(self, source: str, problems: list[str]) -> None:
        self.source = source
        self.problems = problems
        detail = "\n".join(f"  - {p}" for p in problems)
        super().__init__(f"평가 결과가 응답 계약을 만족하지 않습니다 ({source}):\n{detail}")


def _format_location(location: tuple[int | str, ...]) -> str:
    """pydantic 의 loc 튜플을 `queries[3].top3Accuracy` 형태로 편다.

    계약의 진실은 camelCase 직렬화 이름이다(외부 툴이 주는 JSON 이 그 형태다).
    pydantic 은 `populate_by_name` 때문에 snake_case 필드명으로 loc 을 낼 수
    있으므로, 필드 이름은 계약 alias 로 되돌려 적는다. 그래야 원본 JSON 에서
    바로 찾을 수 있다.
    """
    parts: list[str] = []
    for item in location:
        if isinstance(item, int):
            parts.append(f"[{item}]")
        else:
            head, *rest = item.split("_")
            camel = head + "".join(word[:1].upper() + word[1:] for word in rest)
            parts.append(camel if not parts else f".{camel}")
    return "".join(parts) or "(최상위)"


def _describe(error: ErrorDetails) -> str:
    """pydantic 오류 하나를 한 줄로. 필수 누락은 특별히 또렷하게 적는다."""
    location = _format_location(error["loc"])
    kind = error["type"]

    if kind == "missing":
        return f"{location}: 필수 필드가 없습니다"
    if kind == "extra_forbidden":
        return f"{location}: 계약에 없는 필드입니다"

    message = error["msg"]
    given = error["input"]
    # 100문항 전체가 들어오면 로그가 못 쓰게 된다. 값은 짧게 잘라 붙인다.
    shown = json.dumps(given, ensure_ascii=False, default=str)
    if len(shown) > 60:
        shown = f"{shown[:60]}…"
    return f"{location}: {message} (받은 값: {shown})"


def to_evaluation_report(raw: dict[str, Any], *, source: str = "평가 결과") -> EvaluationReport:
    """평가 결과(raw)를 계약 EvaluationReport 로 검증해 반환한다.

    Args:
        raw: 평가 파이프라인이 낸 결과 JSON(dict). 로컬은 fixture 를 읽은 것이다.
        source: 오류 메시지에 붙일 출처. 파일명이나 query_id 를 넘긴다.
            어느 결과가 깨졌는지 모르면 고칠 데를 찾을 수 없다.

    Returns:
        계약 EvaluationReport. 대시보드 화면 전체가 이 하나로 그려진다.

    Raises:
        ContractViolation: raw 가 계약을 만족하지 못할 때. 어느 필드가
            없는지/어긋났는지를 메시지에 담는다.

    Note:
        지금은 매핑 없이 검증만 한다. 파이프라인 출력이 계약과 다른 형태로
        나오게 되면 **여기에** 매핑을 넣는다 — 라우터나 저장소가 아니다.
        검증부는 그대로 두어야 한다. 매핑이 늘어날수록 검증이 더 필요해진다.
    """
    if not isinstance(raw, dict):
        raise ContractViolation(source, [f"(최상위): 객체(JSON object)가 아닙니다 ({type(raw).__name__})"])

    # 지금은 매핑이 없다 — fixture 가 이미 계약 형태다.
    try:
        return EvaluationReport.model_validate(raw)
    except ValidationError as exc:
        errors = exc.errors()
        problems = [_describe(error) for error in errors[:_MAX_REPORTED]]
        if len(errors) > _MAX_REPORTED:
            problems.append(f"… 외 {len(errors) - _MAX_REPORTED}건")
        raise ContractViolation(source, problems) from exc
