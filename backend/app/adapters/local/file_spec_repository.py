"""SpecRepository 의 로컬 구현 — fixtures 폴더에서 읽는다.

**사내 이식 시 이 파일은 버려진다.** 자리를 대신할 DB/사내 API 구현이
`SpecRepository` Protocol 만 만족하면 나머지 코드는 손댈 필요가 없다.

파일 이름 규칙:
    평가 리포트  fixtures/eval_{trace_id}.json
    OpenAPI 명세 fixtures/{spec_id}.json
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.schemas.evaluation import EvaluationListItem, EvaluationReport
from app.services.adapter import to_evaluation_report

logger = logging.getLogger("app")

# ID가 그대로 파일 경로가 되므로 형태를 강제한다.
# 라우터에서도 막고 있지만, 저장소는 자기 입력을 스스로 지켜야 한다
# (Phase 8 의 평가 파이프라인은 HTTP를 거치지 않고 여기를 직접 부른다).
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class FileSpecRepository:
    """fixtures 디렉토리를 읽는 저장소."""

    def __init__(self, fixture_dir: Path) -> None:
        self._fixture_dir = fixture_dir

    def list_evaluations(self) -> list[EvaluationListItem]:
        # eval_{trace_id}.json 을 훑어 요약 필드만 뽑는다. 100문항 전체를
        # model_validate 하지 않는다 — 목록은 가벼워야 한다.
        items: list[EvaluationListItem] = []
        for path in self._fixture_dir.glob("eval_*.json"):
            try:
                payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
                items.append(
                    EvaluationListItem(
                        trace_id=payload["traceId"],
                        app_name=payload["target"]["appName"],
                        evaluated_at=payload["evaluatedAt"],
                        top3_accuracy=payload["summary"]["top3Accuracy"],
                    )
                )
            except (KeyError, ValueError) as exc:
                # 형식이 깨진 파일 하나가 목록 전체를 막지 않게 건너뛴다.
                # **다만 조용히 넘기지는 않는다** — 목록에서 사라진 평가가
                # 왜 안 보이는지 알 길이 없으면 데이터가 없는 것과 구분되지 않는다.
                # (상세 조회는 건너뛰지 않고 ContractViolation 으로 터진다.)
                logger.warning("목록에서 제외: %s — %s", path.name, exc)
                continue

        # 최신순(evaluatedAt 내림차순). ISO 8601 문자열은 사전식 정렬이 곧 시간순이다.
        items.sort(key=lambda item: item.evaluated_at, reverse=True)
        return items

    def get_evaluation(self, trace_id: str) -> EvaluationReport | None:
        payload = self._read_json(f"eval_{trace_id}", key=trace_id)
        if payload is None:
            return None
        # 저장소가 직접 model_validate 하지 않는다. 계약 변환·검증은 어댑터 한 곳이다 —
        # 사내에서 이 파일이 DB 구현으로 바뀌어도 검증은 그대로 남는다.
        return to_evaluation_report(payload, source=f"eval_{trace_id}.json")

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
