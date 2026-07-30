"""대시보드 API 진입점.

POST /api/v1/evaluations 하나가 전부다. 쿼리 1개를 평가하고 결과를 반환하며
**저장하지 않는다** (contract.md §0).

지금 평가는 대역이다 — fixture 를 읽어 돌려준다. 실제 파이프라인(pgvector 조회 →
LLM 질문 생성 → bge-m3 임베딩 → 벡터 검색)이 붙는 자리는
`app/ports/spec_repository.py` 에 적혀 있다.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.deps import SpecRepositoryDep
from app.api.v1 import evaluations
from app.core.config import settings
from app.services.adapter import ContractViolation

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """기동/종료 훅.

    SIGTERM 자체는 uvicorn 이 받는다. uvicorn 은 신호를 받으면 새 연결을 끊고
    처리 중인 요청이 끝나기를 기다린 뒤 이 컨텍스트의 `finally` 로 들어온다.
    그래서 여기서 신호를 직접 잡지 않는다 — 잡으면 오히려 uvicorn 의
    graceful shutdown 을 가로채게 된다.

    종료 시 정리할 자원(DB 커넥션 풀, LLM 세션 등)이 생기면 `finally` 에 붙인다.
    지금은 파일만 읽으므로 닫을 것이 없다.

    유예 시간은 앱이 아니라 실행 옵션으로 정한다:
        uvicorn app.main:app --timeout-graceful-shutdown 20
    """
    logger.info("기동: %s v%s", settings.app_name, settings.version)
    try:
        yield
    finally:
        logger.info("종료: 처리 중이던 요청을 마치고 내려갑니다")


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(evaluations.router)


@app.exception_handler(ContractViolation)
def contract_violation_handler(request: Request, exc: ContractViolation) -> JSONResponse:
    """평가 결과가 계약을 만족하지 않을 때.

    **클라이언트 잘못이 아니므로 500 이다.** 평가 파이프라인이 낸 결과가 깨진
    것이고, 고쳐야 할 것은 그 출력이다. 그래서 `detail` 에 어느 필드가 왜
    틀렸는지를 그대로 실어 보낸다 — 대시보드의 error.tsx 가 개발 환경에서 이
    문장을 보여주면, 브라우저만 보고도 어디를 고칠지 알 수 있다.

    조용히 200 을 주고 화면을 반쯤 그리게 두지 않는다.
    """
    logger.error("계약 위반: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),
            "source": exc.source,
            "problems": exc.problems,
        },
    )


@app.get("/health", tags=["system"], summary="헬스 체크")
def health() -> dict[str, str]:
    """프로세스가 살아 있는지만 본다. 의존 자원은 확인하지 않는다.

    liveness 용이다. 여기서 데이터 소스까지 확인하면, 데이터가 잠깐 안 읽힐 때
    파드가 재시작되면서 상황이 더 나빠진다.
    """
    return {"status": "ok", "service": "backend"}


@app.get("/ready", tags=["system"], summary="레디니스 체크")
def ready(repository: SpecRepositoryDep) -> JSONResponse:
    """데이터 소스가 실제로 읽히는지 확인한다.

    기준 쿼리 하나를 평가해 본다. 로컬 대역은 fixture 를 읽는 것이고, 사내
    구현에서는 pgvector·LLM 까지 실제로 타므로 **readiness 체크가 비싸진다** —
    그때는 파이프라인 전체가 아니라 pgvector 연결만 보는 쪽으로 좁혀야 한다
    (open-questions #71).

    readiness 용이다. 실패하면 트래픽을 받지 않아야 하므로 503 을 준다.
    Port 를 경유하므로 사내 구현으로 바뀌면 이 체크가 곧 그 구현의 연결 확인이 된다.
    """
    query_id = settings.readiness_query_id
    try:
        found = repository.evaluate(query_id) is not None
    except ContractViolation as exc:
        # 읽히긴 했는데 계약을 만족하지 않는다. 트래픽을 받아 봐야 화면이 깨지므로
        # 마찬가지로 not_ready 다. 다만 "못 읽었다" 와는 원인이 다르니 구분해 적는다.
        logger.error("레디니스 체크 실패: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": f"계약 위반: {exc.source}"},
        )
    except Exception:
        logger.exception("레디니스 체크 실패: 저장소를 읽지 못했습니다")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": "저장소를 읽지 못했습니다"},
        )

    if not found:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": f"쿼리 없음: {query_id}"},
        )

    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready"})
