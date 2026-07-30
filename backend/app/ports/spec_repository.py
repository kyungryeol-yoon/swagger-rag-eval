"""Port — 쿼리 1개를 평가한다.

**사내 이식 시 교체 지점.** 로컬은 `adapters/local/file_spec_repository.py`
(fixtures 폴더에서 미리 만든 결과를 읽는다), 사내는 실제 파이프라인이 된다.

교체되는 것은 이 Protocol 을 구현한 클래스 하나뿐이다. 라우터는 이 파일의
타입만 알고 구현체를 직접 import 하지 않는다 (`app/api/deps.py` 에서 조립).

이름이 `SpecRepository` 인데 하는 일은 "평가" 다
---------------------------------------------------------------------------
Phase 12 에서 평가 엔진이 이 시스템 안으로 들어오면서 역할이 바뀌었다. 이전에는
외부 평가툴이 만든 결과를 **읽어오는** 저장소였고, 지금은 요청을 받아 평가를
**수행하는** 쪽이다. 이름을 `Evaluator` 로 바꾸는 것이 맞지만, 실제 파이프라인
구현이 없는 상태에서 이름만 바꾸면 이 커밋의 차이가 커져 "무엇이 실제로
바뀌었는지" 가 묻힌다. 파이프라인이 붙는 시점에 함께 정리한다
(open-questions #72).
"""

from typing import Any, Protocol, runtime_checkable

from app.schemas.evaluation import EvaluationReport


@runtime_checkable
class SpecRepository(Protocol):
    """쿼리 1개를 평가해 결과를 만든다.

    **무상태다.** 부를 때마다 평가하고 저장하지 않는다 (contract.md §0).
    그래서 목록 조회(`list_evaluations`)가 없다 — 조회할 과거 결과가 없다.
    """

    def evaluate(self, query_id: str) -> EvaluationReport | None:
        """쿼리 하나를 평가하고 결과를 반환한다. 그 쿼리가 없으면 None.

        사내 구현이 실제로 할 일 (contract.md §0):
            1. pgvector 에서 그 쿼리의 content 조회 (summary/description/x-question)
            2. LLM 으로 질문 100개 생성
            3. 각 질문을 bge-m3 로 임베딩
            4. 벡터 검색으로 상위 3개 query_id
            5. top_1 / top_3 hit 계산, 개선 추천 도출

        찾지 못한 것은 예외가 아니라 None 이다. HTTP 404 로 바꾸는 판단은
        호출하는 라우터가 한다 — 저장소는 전송 계층을 몰라야 한다.

        **실제 구현은 수십 초 걸린다.** 지금 이 시그니처는 동기라 그 동안
        이벤트 루프를 막는다 — 사내 구현을 붙일 때 `async def` 로 바꿔야 할
        가장 큰 후보다 (open-questions #30, #71).
        """
        ...

    def get_spec(self, spec_id: str) -> dict[str, Any] | None:
        """명세 ID로 OpenAPI 문서(파싱된 dict)를 반환한다. 없으면 None."""
        ...
