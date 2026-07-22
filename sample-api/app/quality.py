"""설명 품질 등급.

이 API의 존재 이유는 "description이 부실하면 RAG 인식률이 떨어진다"는
전제를 실제로 검증하는 것이다. 그래서 엔드포인트마다 설명 품질을
의도적으로 3등급으로 나눠 배치한다.

| 등급 | summary | description | 파라미터 설명 | 응답 필드 설명 |
|---|---|---|---|---|
| GOOD  | O | O (동의어 포함) | O | O |
| POOR  | O | X | X | X |
| EMPTY | X | X | X | X |

각 라우트에는 `openapi_extra=quality(...)` 로 `x-quality` 확장을 달아
생성된 openapi.json 에 정답지를 남긴다.

**주의**: `x-quality` 는 채점 결과를 등급별로 집계하기 위한 메타데이터일 뿐이다.
평가기의 *검색* 입력으로 쓰면 안 된다. 검색은 summary/description 텍스트만 본다.
"""

from enum import StrEnum


class Quality(StrEnum):
    GOOD = "GOOD"
    POOR = "POOR"
    EMPTY = "EMPTY"


def quality(grade: Quality) -> dict[str, str]:
    """라우트의 `openapi_extra` 에 넣을 등급 표식."""
    return {"x-quality": grade.value}
