"""외부 평가툴 출력 → 계약(EvaluationReport) 변환 경계.

**사내 이식 시 실제로 손대는 유일한 변환 파일이 되도록 격리한다.**
사내 평가툴의 원본 JSON 포맷이 확정되면 이 함수 **본문만** 교체하면 된다 —
라우터·저장소·프론트는 계약(`schemas/evaluation.py`)만 알고 이 변환은 모른다.

지금은 fixture 가 이미 계약 형태이므로 그대로 통과(passthrough)시킨다.
"""

from typing import Any

from app.schemas.evaluation import EvaluationReport


def to_evaluation_report(raw: dict[str, Any]) -> EvaluationReport:
    """외부 평가툴의 원본 출력(raw)을 계약 EvaluationReport 로 변환한다.

    Args:
        raw: 사내 평가툴이 낸 원본 JSON(dict). 포맷은 아직 미확정
            (docs/open-questions.md #0 — 평가 엔진은 이 시스템 밖에 있다).

    Returns:
        계약 EvaluationReport. 대시보드 화면 전체가 이 하나로 그려진다.

    Raises:
        pydantic.ValidationError: raw 가 계약을 만족하지 못할 때.

    TODO(사내 이식 · 담당: 경렬):
        사내 평가툴 포맷이 확정되면 **여기만** 교체한다. 원본 raw 의 필드명·구조를
        계약 필드로 매핑한다 — 필드 이름 변경, 중첩 평탄화, enum 값 정규화
        (예: 툴의 "critical" → 계약 Grade.CRITICAL), snake/camel 정리 등.
        지금은 fixture 가 이미 계약 형태라 검증만 하고 그대로 통과시킨다.
    """
    # passthrough: fixture 는 이미 계약 형태다. 포맷이 확정되면 이 한 줄이
    # 실제 매핑 로직으로 바뀐다.
    return EvaluationReport.model_validate(raw)
