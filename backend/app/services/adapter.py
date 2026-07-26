"""외부 평가툴 출력 → 계약(EvaluationReport) 변환 경계.

**사내 이식 시 실제로 손대는 유일한 변환 파일이 되도록 격리한다.**
사내 평가툴의 원본 JSON 포맷이 확정되면 이 함수 **본문만** 교체하면 된다 —
라우터·저장소·프론트는 계약(`schemas/evaluation.py`)만 알고 이 변환은 모른다.

지금은 fixture 가 이미 계약 형태이므로 그대로 통과(passthrough)시킨다.

**계약 검증은 여기서 강제한다.** 외부 평가툴이 필드를 빠뜨리거나 형식이 어긋난
결과를 줄 수 있는데, 그걸 조용히 통과시키면 화면이 절반만 그려지거나 숫자가
비어 보인다. 어느 필드가 왜 틀렸는지를 붙여서 터뜨린다 — 원본 JSON 을 고쳐야
하는 사람은 이 시스템 밖에 있으므로, 메시지만 보고 원본을 찾아갈 수 있어야 한다.
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


def to_evaluation_report(raw: dict[str, Any], *, source: str = "평가툴 출력") -> EvaluationReport:
    """외부 평가툴의 원본 출력(raw)을 계약 EvaluationReport 로 변환한다.

    Args:
        raw: 사내 평가툴이 낸 원본 JSON(dict). 포맷은 아직 미확정
            (docs/open-questions.md #55 — 평가 엔진은 이 시스템 밖에 있다).
        source: 오류 메시지에 붙일 출처. 파일명이나 trace_id 를 넘긴다.
            어느 결과가 깨졌는지 모르면 고칠 데를 찾을 수 없다.

    Returns:
        계약 EvaluationReport. 대시보드 화면 전체가 이 하나로 그려진다.

    Raises:
        ContractViolation: raw 가 계약을 만족하지 못할 때. 어느 필드가
            없는지/어긋났는지를 메시지에 담는다.

    TODO(사내 이식 · 담당: 경렬):
        사내 평가툴 포맷이 확정되면 **매핑만** 교체한다. 원본 raw 의 필드명·구조를
        계약 필드로 매핑한다 — 필드 이름 변경, 중첩 평탄화, enum 값 정규화
        (예: 툴의 "critical" → 계약 Grade.CRITICAL), snake/camel 정리 등.
        아래 검증부는 그대로 둔다. 매핑이 늘어날수록 검증이 더 필요해진다.
    """
    if not isinstance(raw, dict):
        raise ContractViolation(source, [f"(최상위): 객체(JSON object)가 아닙니다 ({type(raw).__name__})"])

    # passthrough: fixture 는 이미 계약 형태다. 포맷이 확정되면 이 한 줄이
    # 실제 매핑 로직으로 바뀐다.
    try:
        return EvaluationReport.model_validate(raw)
    except ValidationError as exc:
        errors = exc.errors()
        problems = [_describe(error) for error in errors[:_MAX_REPORTED]]
        if len(errors) > _MAX_REPORTED:
            problems.append(f"… 외 {len(errors) - _MAX_REPORTED}건")
        raise ContractViolation(source, problems) from exc
