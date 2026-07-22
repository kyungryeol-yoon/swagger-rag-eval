"""평가 대상 API.

이 앱의 목적은 동작이 아니라 `/openapi.json` 이다.
엔드포인트마다 설명 품질을 GOOD/POOR/EMPTY 로 나눠 배치해두고,
평가기가 등급별 인식률 차이를 실제로 검출하는지 본다 (app/quality.py).
"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.quality import Quality
from app.routers import orders, products, users

app = FastAPI(
    title="Sample Commerce API",
    version="0.1.0",
    description="RAG 검색 인식률 평가의 대상이 되는 더미 커머스 API.",
)

app.include_router(orders.router)
app.include_router(products.router)
app.include_router(users.router)


# /health 는 평가 대상이 아니다. 스펙에 넣으면 검색 코퍼스만 오염된다.
@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sample-api"}


def custom_openapi() -> dict[str, Any]:
    """EMPTY 등급 operation에서 FastAPI가 자동 생성한 summary를 제거한다.

    FastAPI는 `summary` 를 주지 않으면 함수 이름으로 만들어 채운다
    (`delete_refund` -> "Delete Refund"). 그러면 EMPTY 등급이 성립하지 않는다.
    설명이 통째로 비어 있는 엔드포인트를 재현하려면 여기서 걷어내야 한다.
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if operation.get("x-quality") == Quality.EMPTY.value:
                operation.pop("summary", None)
                operation.pop("description", None)

    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi  # type: ignore[method-assign]
