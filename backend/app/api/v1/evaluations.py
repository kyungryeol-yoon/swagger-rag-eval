"""평가 리포트 조회 API.

저장소는 `SpecRepository` Port 뒤에 있다. 이 파일은 구현체를 모른다
(어떤 어댑터가 주입되는지는 `app/api/deps.py`).

평가 로직은 아직 없다. 저장된 결과를 반환할 뿐이다 (Phase 8 에서 `services/evaluator.py`).
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from app.api.deps import SpecRepositoryDep
from app.schemas.evaluation import EvaluationReport

router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])

# trace_id 가 저장소 키로 내려가므로 형태를 강제한다.
TRACE_ID_PATTERN = r"^[A-Za-z0-9_-]{1,32}$"


@router.get(
    "/{trace_id}",
    response_model=EvaluationReport,
    summary="평가 리포트 조회",
    description="추적 ID로 평가 리포트 전체를 반환합니다. 대시보드 화면 전체가 이 응답 하나로 그려집니다.",
    responses={status.HTTP_404_NOT_FOUND: {"description": "해당 추적 ID의 평가 결과가 없음"}},
)
def get_evaluation(
    trace_id: Annotated[
        str,
        Path(pattern=TRACE_ID_PATTERN, description="평가 실행의 추적 ID. 예: A492"),
    ],
    repository: SpecRepositoryDep,
) -> EvaluationReport:
    report = repository.get_evaluation(trace_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"평가 결과를 찾을 수 없습니다: {trace_id}",
        )
    return report
