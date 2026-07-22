import json
from pathlib import Path

from app.scripts.dump_openapi import OUTPUT_PATH, dump


def test_dump_writes_valid_spec(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "openapi_sample.json"
    written = dump(target)

    assert written == target
    schema = json.loads(target.read_text(encoding="utf-8"))
    assert schema["info"]["title"] == "Sample Commerce API"
    # 경로 10개 / operation 11개 (/orders/{id}/refund 가 POST + DELETE)
    assert len(schema["paths"]) == 10


def test_default_output_path_points_at_backend_fixtures() -> None:
    assert OUTPUT_PATH.parts[-4:] == ("backend", "app", "fixtures", "openapi_sample.json")
