"""상품 라우터.

`/products/{id}/restock-schedule` 이 EMPTY 등급인 것이 이 파일의 핵심이다.
"재입고 언제 되나요?" 라는 가장 흔한 질문이 설명 없는 엔드포인트를 향한다.
"""

from typing import Annotated

from fastapi import APIRouter, Path
from pydantic import BaseModel, Field

from app.quality import Quality, quality

router = APIRouter(prefix="/products", tags=["products"])


# --------------------------------------------------------------------------
# 모델
# --------------------------------------------------------------------------


class ProductDetail(BaseModel):
    """상품 1건의 상세 정보."""

    product_id: str = Field(description="상품 번호. 상품을 구분하는 고유 식별자입니다.")
    name: str = Field(description="상품명. 고객에게 노출되는 이름입니다.")
    price: int = Field(description="판매가(원). 할인이 적용되기 전 정가입니다.")
    category: str = Field(description="상품이 속한 카테고리 이름입니다.")
    description: str = Field(description="상품 상세 설명. 소재, 규격, 사용법 등이 들어갑니다.")
    is_sold_out: bool = Field(
        description="품절 여부. true 이면 현재 구매할 수 없는 상태(재고 없음)입니다."
    )


class StockInfo(BaseModel):
    product_id: str
    quantity: int
    warehouse: str


class RestockSchedule(BaseModel):
    product_id: str
    expected_date: str
    quantity: int


# --------------------------------------------------------------------------
# 엔드포인트
# --------------------------------------------------------------------------


# QUALITY: GOOD
@router.get(
    "/{id}",
    response_model=ProductDetail,
    summary="상품 상세 조회",
    description=(
        "상품 번호로 상품 1건의 상세 정보를 조회합니다. "
        "상품명, 판매 가격, 카테고리, 상세 설명, 품절 여부를 함께 반환합니다. "
        "상품 상세 페이지에서 가격 확인, 품절 확인 용도로 사용합니다. "
        "(product detail, 상품 정보, 가격 조회)"
    ),
    openapi_extra=quality(Quality.GOOD),
)
def get_product(
    id: Annotated[str, Path(description="조회할 상품 번호입니다.")],
) -> ProductDetail:
    return ProductDetail(
        product_id=id,
        name="라이트 워크셔츠",
        price=39000,
        category="셔츠",
        description="구김이 적은 혼방 원단을 사용한 기본형 셔츠입니다.",
        is_sold_out=False,
    )


# QUALITY: POOR
@router.get(
    "/{id}/stock",
    response_model=StockInfo,
    summary="재고 조회",
    openapi_extra=quality(Quality.POOR),
)
def get_stock(id: str) -> StockInfo:
    return StockInfo(product_id=id, quantity=0, warehouse="ICN-1")


# QUALITY: EMPTY
@router.get(
    "/{id}/restock-schedule",
    response_model=RestockSchedule,
    openapi_extra=quality(Quality.EMPTY),
)
def get_restock_schedule(id: str) -> RestockSchedule:
    return RestockSchedule(product_id=id, expected_date="2026-08-05", quantity=120)
