"""Port — 명세·평가 결과 저장소.

**사내 이식 시 교체 지점.**
로컬은 `adapters/local/file_spec_repository.py` (fixtures 폴더 읽기),
사내는 DB 또는 사내 API 호출로 바뀐다 (`docs/open-questions.md` #5).

교체되는 것은 이 Protocol을 구현한 클래스 하나뿐이다.
라우터와 서비스는 이 파일의 타입만 알고, 구현체를 직접 import 하지 않는다.
"""

from typing import Any, Protocol, runtime_checkable

from app.schemas.evaluation import EvaluationListItem, EvaluationReport


@runtime_checkable
class SpecRepository(Protocol):
    """평가 결과와 원본 명세를 읽어오는 저장소."""

    def list_evaluations(self) -> list[EvaluationListItem]:
        """저장된 평가들의 요약 목록을 최신순으로 반환한다.

        목록·최신 리다이렉트용이라 100문항 전체를 싣지 않는다. 비어 있으면
        빈 목록. 사내에서 DB 어댑터로 바뀌면 여기서 인덱스 조회가 된다.
        """
        ...

    def get_evaluation(self, trace_id: str) -> EvaluationReport | None:
        """추적 ID로 평가 리포트를 반환한다. 없으면 None.

        찾지 못한 것은 예외가 아니라 None 이다. HTTP 404 로 바꾸는 판단은
        호출하는 라우터가 한다 — 저장소는 전송 계층을 몰라야 한다.
        """
        ...

    def get_spec(self, spec_id: str) -> dict[str, Any] | None:
        """명세 ID로 OpenAPI 문서(파싱된 dict)를 반환한다. 없으면 None."""
        ...
