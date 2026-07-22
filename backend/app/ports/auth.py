"""Port — 인증.

**사내 이식 시 교체 지점.**
사내 SSO 토큰 형태와 검증 엔드포인트가 미확정이라 구현체를 만들지 않았다
(`docs/open-questions.md` #4).

지금은 시그니처만 고정해둔다. 소비자가 생기는 시점
(권한 없음 화면 / 평가 실행 API)에 로컬 구현체를 붙인다.
그때까지 이 파일을 import 하는 코드는 없어야 한다.
"""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class User(BaseModel):
    """인증된 사용자. 사내 SSO 클레임에서 무엇을 꺼낼 수 있는지 확정되면 필드가 바뀐다."""

    id: str = Field(description="사용자 고유 식별자.")
    name: str = Field(description="화면에 표시할 이름.")
    email: str | None = Field(default=None, description="이메일. SSO가 제공하지 않으면 None.")


@runtime_checkable
class AuthProvider(Protocol):
    """요청 주체를 확인한다."""

    def get_current_user(self) -> User:
        """현재 요청의 사용자를 반환한다. 인증되지 않았으면 예외를 던진다."""
        ...
