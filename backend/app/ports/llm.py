"""Port — LLM / 임베딩.

**사내 이식 시 교체 지점.**
사내 LLM 엔드포인트 스펙과 임베딩 모델 제공 여부가 미확정이라
구현체를 만들지 않았다 (`docs/open-questions.md` #6, #7).

지금은 시그니처만 고정해둔다. 소비자는 Phase 8 의 평가 파이프라인
(문항 생성 · 검색 · 실패 원인 분류)이며, 그때 결정론적 mock 구현을 붙인다.
그때까지 이 파일을 import 하는 코드는 없어야 한다.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """텍스트 생성. 문항 생성과 실패 원인 분류에 쓴다."""

    def complete(self, prompt: str) -> str:
        """프롬프트에 대한 응답 텍스트를 반환한다."""
        ...


@runtime_checkable
class Embedder(Protocol):
    """텍스트 임베딩. 벡터 검색에 쓴다."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """입력 순서를 유지한 임베딩 벡터 목록을 반환한다.

        같은 입력에는 항상 같은 벡터를 반환해야 한다. 평가 결과가
        실행할 때마다 흔들리면 Before/After 비교가 성립하지 않는다.
        """
        ...
