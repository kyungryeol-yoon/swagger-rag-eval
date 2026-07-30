"""평가 실행 API.

파이프라인은 `SpecRepository` Port 뒤에 있다. 이 파일은 구현체를 모른다
(어떤 어댑터가 주입되는지는 `app/api/deps.py`).

**무상태다.** 요청마다 평가하고 저장하지 않는다 (contract.md §0). 그래서
목록 조회도, 추적 ID 로 다시 꺼내는 조회도 없다.
"""

import re

from fastapi import APIRouter, HTTPException, status

from app.api.deps import SpecRepositoryDep
from app.schemas.evaluation import EvaluateRequest, EvaluationReport

router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])

# query_id 가 저장소 키(로컬은 파일 경로)로 내려가므로 형태를 강제한다.
# 저장소도 자기 입력을 따로 검사하지만, 잘못된 입력은 여기서 422 로 끊는 편이
# 낫다 — 500 보다 원인이 분명하다.
QUERY_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


@router.post(
    "",
    response_model=EvaluationReport,
    summary="쿼리 1개 평가",
    description=(
        "DAC 쿼리 하나를 평가하고 결과를 반환합니다. 대시보드 화면 전체가 이 응답 "
        "하나로 그려집니다.\n\n"
        "**무상태입니다.** 요청마다 처음부터 평가하며 결과를 저장하지 않습니다. "
        "실제 파이프라인은 LLM 질문 생성과 벡터 검색을 포함해 수십 초가 걸립니다.\n\n"
        "요청 본문은 `{\"query_id\": \"...\"}` 이며 `queryId` 도 받습니다."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "해당 query_id 의 쿼리를 찾을 수 없음"},
    },
)
def evaluate(
    payload: EvaluateRequest,
    repository: SpecRepositoryDep,
) -> EvaluationReport:
    query_id = payload.query_id

    if not QUERY_ID_PATTERN.fullmatch(query_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"허용되지 않는 query_id 형태입니다: {query_id!r}",
        )

    report = repository.evaluate(query_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"쿼리를 찾을 수 없습니다: {query_id}",
        )
    return report
