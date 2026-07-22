"""주문 라우터.

응답은 전부 더미다. 이 파일의 산출물은 동작이 아니라 openapi.json 이다.
등급별로 설명을 채우거나 비우는 것이 핵심이므로,
POOR/EMPTY 엔드포인트에는 **함수 docstring도 달지 않는다**
(FastAPI가 docstring을 description으로 채워버린다).
"""

from typing import Annotated

from fastapi import APIRouter, Path
from pydantic import BaseModel, Field

from app.quality import Quality, quality

router = APIRouter(prefix="/orders", tags=["orders"])


# --------------------------------------------------------------------------
# 모델
# --------------------------------------------------------------------------


class OrderDetail(BaseModel):
    """주문 1건의 상세 정보."""

    order_id: str = Field(description="주문 번호. 주문 조회·문의 시 사용하는 고유 식별자입니다.")
    status: str = Field(
        description=(
            "주문 상태. PAID(결제 완료), PREPARING(상품 준비 중), "
            "SHIPPED(발송됨), DELIVERED(배송 완료), CANCELLED(주문 취소됨) 중 하나입니다."
        )
    )
    total_amount: int = Field(description="결제 금액(원). 할인과 배송비가 모두 반영된 최종 금액입니다.")
    ordered_at: str = Field(description="주문 일시(ISO 8601). 주문이 접수된 시각입니다.")
    item_count: int = Field(description="주문에 포함된 상품 종류의 수입니다.")


class RefundStatus(BaseModel):
    """환불 처리 상태."""

    order_id: str = Field(description="환불 대상 주문 번호입니다.")
    refund_state: str = Field(
        description=(
            "환불 진행 상태. REQUESTED(환불 신청 접수), INSPECTING(반품 상품 검수 중), "
            "APPROVED(환불 승인), REJECTED(환불 거절), COMPLETED(환불 완료) 중 하나입니다."
        )
    )
    reason: str = Field(description="고객이 선택한 환불 사유. 단순 변심, 상품 불량 등입니다.")
    refund_amount: int = Field(description="환불 예정 또는 환불 완료된 금액(원)입니다.")
    processed_at: str | None = Field(
        default=None,
        description="환불 처리가 완료된 일시. 아직 처리 중이면 null 입니다.",
    )


class ShippingStatus(BaseModel):
    """배송 진행 상태."""

    order_id: str = Field(description="배송 대상 주문 번호입니다.")
    carrier: str = Field(description="배송을 담당하는 택배사 이름입니다.")
    tracking_number: str = Field(
        description="운송장 번호. 택배사 사이트에서 배송 추적에 사용하는 번호입니다."
    )
    shipping_state: str = Field(
        description=(
            "배송 상태. READY(배송 준비 중), PICKED_UP(택배사 집화 완료), "
            "IN_TRANSIT(배송 중), OUT_FOR_DELIVERY(배송 출발), DELIVERED(배송 완료) 중 하나입니다."
        )
    )
    estimated_arrival: str = Field(description="도착 예정일(ISO 8601). 택배사가 제공하는 예상 일자입니다.")


class RefundRequest(BaseModel):
    reason: str
    memo: str | None = None


class RefundAccepted(BaseModel):
    order_id: str
    refund_state: str


class ShippingAddressUpdate(BaseModel):
    postal_code: str
    address_line1: str
    address_line2: str | None = None
    receiver_phone: str | None = None


class ShippingAddressUpdated(BaseModel):
    order_id: str
    postal_code: str
    address_line1: str


class RefundCancelled(BaseModel):
    order_id: str
    refund_state: str


# --------------------------------------------------------------------------
# 엔드포인트
# --------------------------------------------------------------------------


# QUALITY: GOOD
@router.get(
    "/{id}",
    response_model=OrderDetail,
    summary="주문 상세 조회",
    description=(
        "주문 번호로 주문 1건의 상세 내역을 조회합니다. "
        "결제 금액, 주문 상태, 주문 일시, 담은 상품 수를 함께 반환합니다. "
        "내가 뭘 샀는지 확인하는 구매 내역·주문 내역·주문 확인 화면에서 사용합니다. "
        "(order detail, purchase history)"
    ),
    openapi_extra=quality(Quality.GOOD),
)
def get_order(
    id: Annotated[str, Path(description="조회할 주문 번호. 주문 완료 시 발급된 식별자입니다.")],
) -> OrderDetail:
    return OrderDetail(
        order_id=id,
        status="SHIPPED",
        total_amount=48900,
        ordered_at="2026-07-18T10:12:00+09:00",
        item_count=2,
    )


# QUALITY: GOOD
@router.get(
    "/{id}/refund-status",
    response_model=RefundStatus,
    summary="주문 환불 상태 조회",
    description=(
        "특정 주문 건의 환불 처리 상태, 환불 사유, 환불 금액, 처리 일자를 반환합니다. "
        "환불이 어디까지 진행됐는지, 환불 승인이 났는지, 언제 입금되는지 확인할 때 사용합니다. "
        "반품 진행 상황 확인에도 같은 엔드포인트를 씁니다. "
        "환불을 새로 신청하거나 취소하는 것이 아니라 **현재 상태를 읽기만** 합니다. "
        "(refund status, 환불 진행 상황, 반품 처리 상태)"
    ),
    openapi_extra=quality(Quality.GOOD),
)
def get_refund_status(
    id: Annotated[str, Path(description="환불 상태를 확인할 주문 번호입니다.")],
) -> RefundStatus:
    return RefundStatus(
        order_id=id,
        refund_state="INSPECTING",
        reason="단순 변심",
        refund_amount=48900,
        processed_at=None,
    )


# QUALITY: POOR
@router.post(
    "/{id}/refund",
    response_model=RefundAccepted,
    summary="환불 신청",
    openapi_extra=quality(Quality.POOR),
)
def create_refund(id: str, body: RefundRequest) -> RefundAccepted:
    return RefundAccepted(order_id=id, refund_state="REQUESTED")


# QUALITY: EMPTY
@router.delete(
    "/{id}/refund",
    response_model=RefundCancelled,
    openapi_extra=quality(Quality.EMPTY),
)
def delete_refund(id: str) -> RefundCancelled:
    return RefundCancelled(order_id=id, refund_state="CANCELLED")


# QUALITY: POOR
@router.patch(
    "/{id}/shipping-address",
    response_model=ShippingAddressUpdated,
    summary="배송지 변경",
    openapi_extra=quality(Quality.POOR),
)
def update_shipping_address(id: str, body: ShippingAddressUpdate) -> ShippingAddressUpdated:
    return ShippingAddressUpdated(
        order_id=id,
        postal_code=body.postal_code,
        address_line1=body.address_line1,
    )


# QUALITY: GOOD
@router.get(
    "/{id}/shipping-status",
    response_model=ShippingStatus,
    summary="주문 배송 상태 조회",
    description=(
        "주문 건의 현재 배송 상태와 운송장 번호, 택배사, 도착 예정일을 반환합니다. "
        "내 물건이 지금 어디쯤 왔는지, 언제 도착하는지 확인하는 배송 조회·배송 추적 화면에서 사용합니다. "
        "택배 조회, 운송장 번호 확인도 이 엔드포인트로 처리합니다. "
        "(shipping status, delivery tracking)"
    ),
    openapi_extra=quality(Quality.GOOD),
)
def get_shipping_status(
    id: Annotated[str, Path(description="배송 상태를 확인할 주문 번호입니다.")],
) -> ShippingStatus:
    return ShippingStatus(
        order_id=id,
        carrier="한진택배",
        tracking_number="123456789012",
        shipping_state="IN_TRANSIT",
        estimated_arrival="2026-07-24",
    )
