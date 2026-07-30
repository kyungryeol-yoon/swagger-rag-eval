"""SpecRepository 의 로컬 구현 — fixtures 폴더에서 읽는다.

**사내 이식 시 이 파일은 버려진다.** 자리를 대신할 실제 파이프라인 구현이
`SpecRepository` Protocol 만 만족하면 나머지 코드는 손댈 필요가 없다.

여기서 `evaluate()` 는 진짜 평가를 하지 않는다 — 미리 만들어 둔 결과를 읽어
돌려줄 뿐이다. 화면과 계약을 고정하기 위한 대역이며, LLM·pgvector·임베딩이
붙는 자리는 `ports/spec_repository.py` 의 docstring 에 적어 두었다.

파일 이름 규칙:
    평가 결과    fixtures/eval_{query_id}.json
    OpenAPI 명세 fixtures/{spec_id}.json
"""

import json
import re
from pathlib import Path
from typing import Any

from app.schemas.evaluation import EvaluationReport
from app.services.adapter import to_evaluation_report

# ID가 그대로 파일 경로가 되므로 형태를 강제한다.
# 라우터에서도 막고 있지만, 저장소는 자기 입력을 스스로 지켜야 한다
# (파이프라인 구현은 HTTP를 거치지 않고 여기를 직접 부를 수 있다).
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class FileSpecRepository:
    """fixtures 디렉토리를 읽는 대역 구현."""

    def __init__(self, fixture_dir: Path) -> None:
        self._fixture_dir = fixture_dir

    def evaluate(self, query_id: str) -> EvaluationReport | None:
        payload = self._read_json(f"eval_{query_id}", key=query_id)
        if payload is None:
            return None
        # 계약 변환·검증은 어댑터 한 곳이다 — 사내에서 이 파일이 실제 파이프라인으로
        # 바뀌어도 검증은 그대로 남는다.
        return to_evaluation_report(payload, source=f"eval_{query_id}.json")

    def get_spec(self, spec_id: str) -> dict[str, Any] | None:
        return self._read_json(spec_id, key=spec_id)

    def _read_json(self, stem: str, *, key: str) -> dict[str, Any] | None:
        if not _SAFE_ID.fullmatch(key):
            raise ValueError(f"허용되지 않는 식별자입니다: {key!r}")

        path = self._fixture_dir / f"{stem}.json"
        if not path.is_file():
            return None

        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return payload
