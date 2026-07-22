"""대시보드 API 진입점.

현재는 저장된 평가 결과를 반환한다. 실제 평가 파이프라인은 Phase 8.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.deps import SpecRepositoryDep
from app.api.v1 import evaluations
from app.core.config import settings

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


@app.get("/health", tags=["system"], summary="헬스 체크")
def health() -> dict[str, str]:
    """프로세스가 살아 있는지만 본다. 의존 자원은 확인하지 않는다.

    liveness 용이다. 여기서 데이터 소스까지 확인하면, 데이터가 잠깐 안 읽힐 때
    파드가 재시작되면서 상황이 더 나빠진다.
    """
    return {"status": "ok", "service": "backend"}


@app.get("/ready", tags=["system"], summary="레디니스 체크")
def ready(repository: SpecRepositoryDep) -> JSONResponse:
    """데이터 소스에서 평가 결과가 실제로 읽히는지 확인한다.

    readiness 용이다. 실패하면 트래픽을 받지 않아야 하므로 503 을 준다.
    저장소는 Port 를 경유하므로, 사내에서 DB 어댑터로 바뀌면
    이 체크가 곧 DB 연결 확인이 된다.
    """
    trace_id = settings.readiness_trace_id
    try:
        found = repository.get_evaluation(trace_id) is not None
    except Exception:
        logger.exception("레디니스 체크 실패: 저장소를 읽지 못했습니다")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": "저장소를 읽지 못했습니다"},
        )

    if not found:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": f"평가 결과 없음: {trace_id}"},
        )

    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready"})
