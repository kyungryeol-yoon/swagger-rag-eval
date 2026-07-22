"""SpecRepository 의 로컬 구현 — fixtures 폴더에서 읽는다.

**사내 이식 시 이 파일은 버려진다.** 자리를 대신할 DB/사내 API 구현이
`SpecRepository` Protocol 만 만족하면 나머지 코드는 손댈 필요가 없다.

파일 이름 규칙:
    평가 리포트  fixtures/eval_{trace_id}.json
    OpenAPI 명세 fixtures/{spec_id}.json
"""

import json
import re
from pathlib import Path
from typing import Any

from app.schemas.evaluation import EvaluationReport

# ID가 그대로 파일 경로가 되므로 형태를 강제한다.
# 라우터에서도 막고 있지만, 저장소는 자기 입력을 스스로 지켜야 한다
# (Phase 8 의 평가 파이프라인은 HTTP를 거치지 않고 여기를 직접 부른다).
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class FileSpecRepository:
    """fixtures 디렉토리를 읽는 저장소."""

    def __init__(self, fixture_dir: Path) -> None:
        self._fixture_dir = fixture_dir

    def get_evaluation(self, trace_id: str) -> EvaluationReport | None:
        payload = self._read_json(f"eval_{trace_id}", key=trace_id)
        if payload is None:
            return None
        return EvaluationReport.model_validate(payload)

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
