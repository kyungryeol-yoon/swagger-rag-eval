"""엔드포인트별 설명 품질을 표로 출력한다.

    make show-quality
    # 또는
    cd sample-api && uv run python -m app.scripts.show_quality

등급 배치가 의도대로 유지되고 있는지 눈으로 확인하는 용도다.
"EMPTY 등급 3개가 실패의 62%를 차지" 같은 주장을 하기 전에
그 EMPTY 가 정말 비어 있는지 여기서 본다.

pytest 와 목적이 다르다. 테스트는 무너졌을 때 알려주고,
이 스크립트는 시연 중에 근거를 보여준다.
"""

import unicodedata

from app.main import app
from app.quality import Quality

# 표 너비. 경로가 가장 길어서 기준이 된다.
_METHOD_W = 6
_PATH_W = 34
_GRADE_W = 5


def _display_width(text: str) -> int:
    """터미널에서 차지하는 칸 수. 한글은 두 칸이다."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _pad(text: str, width: int, *, right: bool = False) -> str:
    """한글이 섞여도 표가 어긋나지 않도록 직접 채운다."""
    fill = " " * max(0, width - _display_width(text))
    return fill + text if right else text + fill


def _rows() -> list[tuple[str, str, str, str, int, str, str]]:
    schema = app.openapi()
    rows: list[tuple[str, str, str, str, int, str, str]] = []

    for path, path_item in sorted(schema["paths"].items()):
        for method, operation in path_item.items():
            summary = operation.get("summary") or ""
            description = operation.get("description") or ""

            params = [p for p in operation.get("parameters", []) if p.get("in") == "path"]
            param_described = all(p.get("description") for p in params) if params else False

            fields = _response_fields(schema, operation)
            fields_described = all(f.get("description") for f in fields.values()) if fields else False

            rows.append(
                (
                    operation.get("x-quality", "?"),
                    method.upper(),
                    path,
                    "O" if summary else "-",
                    len(description),
                    "O" if param_described else "-",
                    "O" if fields_described else "-",
                )
            )
    return rows


def _response_fields(schema: dict, operation: dict) -> dict:
    try:
        ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    except KeyError:
        return {}
    model_name = ref.rsplit("/", 1)[-1]
    fields: dict = schema["components"]["schemas"][model_name].get("properties", {})
    return fields


def main() -> None:
    rows = _rows()

    header = " ".join(
        [
            _pad("등급", _GRADE_W),
            _pad("메서드", _METHOD_W),
            _pad("경로", _PATH_W),
            _pad("summary", 7, right=True),
            _pad("desc길이", 8, right=True),
            _pad("파라미터", 8, right=True),
            _pad("응답필드", 8, right=True),
        ]
    )
    print()
    print(header)
    print("-" * _display_width(header))

    order = {Quality.GOOD: 0, Quality.POOR: 1, Quality.EMPTY: 2}
    for grade, method, path, has_summary, desc_len, params, fields in sorted(
        rows, key=lambda r: (order.get(r[0], 9), r[2], r[1])  # type: ignore[arg-type]
    ):
        print(
            " ".join(
                [
                    _pad(grade, _GRADE_W),
                    _pad(method, _METHOD_W),
                    _pad(path, _PATH_W),
                    _pad(has_summary, 7, right=True),
                    _pad(str(desc_len), 8, right=True),
                    _pad(params, 8, right=True),
                    _pad(fields, 8, right=True),
                ]
            )
        )

    print()
    counts = {grade.value: sum(1 for r in rows if r[0] == grade.value) for grade in Quality}
    total = len(rows)
    print(f"합계 {total} 개 — " + ", ".join(f"{g} {c}" for g, c in counts.items()))
    print()
    print("GOOD  = summary + 상세 description + 파라미터 설명 + 응답 필드 설명 + 동의어")
    print("POOR  = summary 한 줄만")
    print("EMPTY = 설명 없음")
    print()


if __name__ == "__main__":
    main()
