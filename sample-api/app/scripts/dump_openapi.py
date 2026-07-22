"""openapi.json 을 평가기 fixture 로 덤프한다.

    make dump-spec
    # 또는
    cd sample-api && uv run python -m app.scripts.dump_openapi

서버를 띄우지 않고 앱 객체에서 직접 뽑는다. HTTP를 거칠 이유가 없다.
출력물은 생성물이므로 .gitignore 대상이다.
"""

import json
from collections import Counter
from pathlib import Path

from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_PATH = REPO_ROOT / "backend" / "app" / "fixtures" / "openapi_sample.json"


def dump(output_path: Path = OUTPUT_PATH) -> Path:
    schema = app.openapi()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def _summarize(output_path: Path) -> str:
    schema = json.loads(output_path.read_text(encoding="utf-8"))
    grades: Counter[str] = Counter()
    operations = 0
    for path_item in schema["paths"].values():
        for operation in path_item.values():
            operations += 1
            grades[operation.get("x-quality", "UNGRADED")] += 1
    breakdown = ", ".join(f"{grade} {count}" for grade, count in sorted(grades.items()))
    return f"{operations} operations ({breakdown})"


if __name__ == "__main__":
    path = dump()
    print(f"wrote {path}")
    print(f"  {_summarize(path)}")
