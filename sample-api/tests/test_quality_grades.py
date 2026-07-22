"""설명 품질 등급이 생성된 openapi.json 에 실제로 반영됐는지 검증한다.

이 테스트가 이 저장소에서 가장 중요하다.
등급 배치가 무너지면 평가 결과 전체가 근거를 잃는다
("EMPTY 등급 3개가 실패의 62%를 차지" 같은 문장이 여기서 나온다).

EMPTY 엔드포인트에 누가 친절하게 description을 달면 **이 테스트가 실패해야 한다.**
"""

from typing import Any

import pytest

from app.main import app
from app.quality import Quality

# 등급 정답지. 라우터 파일의 `# QUALITY:` 주석과 일치해야 한다.
EXPECTED_GRADES: dict[tuple[str, str], Quality] = {
    ("get", "/orders/{id}"): Quality.GOOD,
    ("get", "/orders/{id}/refund-status"): Quality.GOOD,
    ("post", "/orders/{id}/refund"): Quality.POOR,
    ("delete", "/orders/{id}/refund"): Quality.EMPTY,
    ("patch", "/orders/{id}/shipping-address"): Quality.POOR,
    ("get", "/orders/{id}/shipping-status"): Quality.GOOD,
    ("get", "/products/{id}"): Quality.GOOD,
    ("get", "/products/{id}/stock"): Quality.POOR,
    ("get", "/products/{id}/restock-schedule"): Quality.EMPTY,
    ("get", "/users/{id}"): Quality.GOOD,
    ("patch", "/users/{id}/address"): Quality.POOR,
}

# GOOD 등급은 사용자가 실제로 쓰는 표현을 description 안에 품고 있어야 한다.
# 이게 없으면 "설명을 잘 쓰면 인식률이 오른다"는 주장이 성립하지 않는다.
EXPECTED_SYNONYMS: dict[tuple[str, str], list[str]] = {
    ("get", "/orders/{id}"): ["구매 내역", "주문 내역"],
    ("get", "/orders/{id}/refund-status"): ["반품", "환불 진행 상황"],
    ("get", "/orders/{id}/shipping-status"): ["택배", "배송 추적", "운송장"],
    ("get", "/products/{id}"): ["품절", "가격"],
    ("get", "/users/{id}"): ["마이페이지", "내 정보"],
}


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    return app.openapi()


def operation_of(schema: dict[str, Any], method: str, path: str) -> dict[str, Any]:
    op = schema["paths"][path][method]
    assert isinstance(op, dict)
    return op


def response_properties(schema: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
    """200 응답 본문 모델의 필드 정의를 꺼낸다."""
    content = operation["responses"]["200"]["content"]["application/json"]["schema"]
    ref = content["$ref"]
    model_name = ref.rsplit("/", 1)[-1]
    props = schema["components"]["schemas"][model_name].get("properties", {})
    assert isinstance(props, dict)
    return props


def path_parameters(operation: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in operation.get("parameters", []) if p.get("in") == "path"]


# --------------------------------------------------------------------------
# 스펙 형태
# --------------------------------------------------------------------------


def test_all_expected_endpoints_exist(schema: dict[str, Any]) -> None:
    actual = {
        (method, path)
        for path, path_item in schema["paths"].items()
        for method in path_item
    }
    assert actual == set(EXPECTED_GRADES)


def test_health_is_not_in_spec(schema: dict[str, Any]) -> None:
    """평가 코퍼스에 시스템 엔드포인트가 섞이면 안 된다."""
    assert "/health" not in schema["paths"]


def test_every_operation_is_graded(schema: dict[str, Any]) -> None:
    for (method, path), grade in EXPECTED_GRADES.items():
        op = operation_of(schema, method, path)
        assert op.get("x-quality") == grade.value, f"{method.upper()} {path}"


def test_tags_group_by_resource(schema: dict[str, Any]) -> None:
    for (method, path), _ in EXPECTED_GRADES.items():
        op = operation_of(schema, method, path)
        expected_tag = path.split("/")[1]
        assert op.get("tags") == [expected_tag], f"{method.upper()} {path}"


def test_grade_distribution(schema: dict[str, Any]) -> None:
    """등급이 한쪽으로 쏠리면 대조군이 없어진다."""
    counts = {grade: list(EXPECTED_GRADES.values()).count(grade) for grade in Quality}
    assert counts == {Quality.GOOD: 5, Quality.POOR: 4, Quality.EMPTY: 2}


# --------------------------------------------------------------------------
# 등급별 검증
# --------------------------------------------------------------------------


GOOD_ENDPOINTS = [k for k, v in EXPECTED_GRADES.items() if v is Quality.GOOD]
POOR_ENDPOINTS = [k for k, v in EXPECTED_GRADES.items() if v is Quality.POOR]
EMPTY_ENDPOINTS = [k for k, v in EXPECTED_GRADES.items() if v is Quality.EMPTY]


@pytest.mark.parametrize(("method", "path"), GOOD_ENDPOINTS)
def test_good_is_fully_described(schema: dict[str, Any], method: str, path: str) -> None:
    op = operation_of(schema, method, path)

    assert op.get("summary"), "GOOD 은 summary 가 있어야 한다"
    description = op.get("description", "")
    assert len(description) >= 80, "GOOD 은 상세한 description 이 있어야 한다"

    for param in path_parameters(op):
        assert param.get("description"), f"GOOD 은 파라미터 설명이 있어야 한다: {param['name']}"

    for name, field in response_properties(schema, op).items():
        assert field.get("description"), f"GOOD 은 응답 필드 설명이 있어야 한다: {name}"


@pytest.mark.parametrize(("method", "path"), GOOD_ENDPOINTS)
def test_good_contains_user_synonyms(schema: dict[str, Any], method: str, path: str) -> None:
    op = operation_of(schema, method, path)
    description = op["description"]
    for synonym in EXPECTED_SYNONYMS[(method, path)]:
        assert synonym in description, f"동의어 누락: {synonym}"


@pytest.mark.parametrize(("method", "path"), POOR_ENDPOINTS)
def test_poor_has_summary_only(schema: dict[str, Any], method: str, path: str) -> None:
    op = operation_of(schema, method, path)

    assert op.get("summary"), "POOR 는 summary 한 줄은 있어야 한다"
    assert not op.get("description"), "POOR 에 description 이 있으면 안 된다"

    for param in path_parameters(op):
        assert not param.get("description"), f"POOR 에 파라미터 설명이 있으면 안 된다: {param['name']}"

    for name, field in response_properties(schema, op).items():
        assert not field.get("description"), f"POOR 에 응답 필드 설명이 있으면 안 된다: {name}"


@pytest.mark.parametrize(("method", "path"), EMPTY_ENDPOINTS)
def test_empty_has_no_description_at_all(schema: dict[str, Any], method: str, path: str) -> None:
    op = operation_of(schema, method, path)

    # FastAPI 는 summary 를 안 주면 함수명으로 만들어 채운다.
    # main.custom_openapi() 가 이를 걷어내지 않으면 여기서 걸린다.
    assert not op.get("summary"), "EMPTY 에 summary 가 있으면 안 된다"
    assert not op.get("description"), "EMPTY 에 description 이 있으면 안 된다"

    for param in path_parameters(op):
        assert not param.get("description"), f"EMPTY 에 파라미터 설명이 있으면 안 된다: {param['name']}"

    for name, field in response_properties(schema, op).items():
        assert not field.get("description"), f"EMPTY 에 응답 필드 설명이 있으면 안 된다: {name}"


@pytest.mark.parametrize(("method", "path"), POOR_ENDPOINTS + EMPTY_ENDPOINTS)
def test_non_good_models_have_no_schema_description(
    schema: dict[str, Any], method: str, path: str
) -> None:
    """Pydantic 모델 docstring 은 스키마 description 이 된다. POOR/EMPTY 는 없어야 한다."""
    content = operation_of(schema, method, path)["responses"]["200"]["content"]
    model_name = content["application/json"]["schema"]["$ref"].rsplit("/", 1)[-1]
    assert not schema["components"]["schemas"][model_name].get("description")
