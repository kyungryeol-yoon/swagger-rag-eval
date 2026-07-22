"""사용자 라우터.

`/users/{id}/address`(POOR)와 `/orders/{id}/shipping-address`(POOR)가
서로 헷갈리게 배치돼 있다. "주소 바꾸려면?" 이라는 질문이
회원 기본 주소와 주문 배송지 중 어느 쪽인지 구분되지 않는 상황을 만든다.
"""

from typing import Annotated

from fastapi import APIRouter, Path
from pydantic import BaseModel, Field

from app.quality import Quality, quality

router = APIRouter(prefix="/users", tags=["users"])


# --------------------------------------------------------------------------
# 모델
# --------------------------------------------------------------------------


class UserProfile(BaseModel):
    """회원 1명의 프로필 정보."""

    user_id: str = Field(description="회원 번호. 회원을 구분하는 고유 식별자입니다.")
    email: str = Field(description="회원 이메일 주소. 로그인 아이디이자 알림 수신 주소입니다.")
    nickname: str = Field(description="회원이 설정한 표시 이름입니다.")
    grade: str = Field(
        description="회원 등급. BASIC, SILVER, GOLD, VIP 순으로 혜택이 올라갑니다."
    )
    joined_at: str = Field(description="가입 일시(ISO 8601). 회원으로 등록된 시각입니다.")


class AddressUpdate(BaseModel):
    postal_code: str
    address_line1: str
    address_line2: str | None = None


class AddressUpdated(BaseModel):
    user_id: str
    postal_code: str
    address_line1: str


# --------------------------------------------------------------------------
# 엔드포인트
# --------------------------------------------------------------------------


# QUALITY: GOOD
@router.get(
    "/{id}",
    response_model=UserProfile,
    summary="회원 정보 조회",
    description=(
        "회원 번호로 회원 1명의 프로필 정보를 조회합니다. "
        "이메일, 닉네임, 회원 등급, 가입 일자를 함께 반환합니다. "
        "내 정보 확인, 마이페이지, 계정 정보 조회 화면에서 사용합니다. "
        "(user profile, my account, 내 계정 정보)"
    ),
    openapi_extra=quality(Quality.GOOD),
)
def get_user(
    id: Annotated[str, Path(description="조회할 회원 번호입니다.")],
) -> UserProfile:
    return UserProfile(
        user_id=id,
        email="user@example.com",
        nickname="윤",
        grade="GOLD",
        joined_at="2024-03-02T09:00:00+09:00",
    )


# QUALITY: POOR
@router.patch(
    "/{id}/address",
    response_model=AddressUpdated,
    summary="주소 변경",
    openapi_extra=quality(Quality.POOR),
)
def update_address(id: str, body: AddressUpdate) -> AddressUpdated:
    return AddressUpdated(
        user_id=id,
        postal_code=body.postal_code,
        address_line1=body.address_line1,
    )
