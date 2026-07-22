# sample-api

> **이 서비스는 배포 대상이 아니다. 로컬 개발과 시연 전용이다.**
> 실제 동작하는 커머스 API 가 아니며, 모든 응답은 고정된 더미 값이다.
> 사내망에 이식하는 것은 `backend/` 와 `frontend/` 뿐이다.

## 이것이 무엇인가

RAG 검색 인식률 평가의 **대상**이 되는 더미 API 다.
목적은 동작이 아니라 진짜 `/openapi.json` 을 만들어내는 것이다.

이 프로젝트는 "Swagger 설명이 부실하면 AI 가 그 API 를 못 찾는다"를 전제로 한다.
가짜 fixture JSON 만 가지고는 **그 전제 자체를 검증할 수 없다.**
그래서 설명을 잘 쓴 엔드포인트와 부실하게 쓴 엔드포인트를 한 명세 안에 섞어두고,
평가 점수가 실제로 갈리는지 본다.

설명 품질을 의도적으로 3등급으로 나눴다.

| 등급 | summary | description | 파라미터 설명 | 응답 필드 설명 |
|---|---|---|---|---|
| `GOOD` | O | O (사용자 표현·동의어 포함) | O | O |
| `POOR` | O (한 줄) | X | X | X |
| `EMPTY` | X | X | X | X |

## 단독 실행

```bash
cd sample-api
uv sync
uv run uvicorn app.main:app --port 8001
```

| 주소 | 내용 |
|---|---|
| http://localhost:8001/openapi.json | **산출물.** 평가기의 입력이 된다 |
| http://localhost:8001/docs | Swagger UI. 등급 차이를 눈으로 보기 좋다 |
| http://localhost:8001/health | 헬스 체크 (명세에는 포함되지 않는다) |

저장소 루트에서 `make dev-sample` 로 실행해도 같다.

## 엔드포인트 11개와 등급

| 등급 | 메서드 | 경로 | 비고 |
|---|---|---|---|
| `GOOD` | `GET` | `/orders/{id}` | 구매 내역·주문 내역 표현 포함 |
| `GOOD` | `GET` | `/orders/{id}/refund-status` | 반품·환불 진행 상황 표현 포함 |
| `GOOD` | `GET` | `/orders/{id}/shipping-status` | 택배·운송장·배송 추적 표현 포함 |
| `GOOD` | `GET` | `/products/{id}` | 품절·가격 표현 포함 |
| `GOOD` | `GET` | `/users/{id}` | 마이페이지·내 정보 표현 포함 |
| `POOR` | `POST` | `/orders/{id}/refund` | summary "환불 신청" 한 줄 |
| `POOR` | `PATCH` | `/orders/{id}/shipping-address` | summary "배송지 변경" 한 줄 |
| `POOR` | `GET` | `/products/{id}/stock` | summary "재고 조회" 한 줄 |
| `POOR` | `PATCH` | `/users/{id}/address` | summary "주소 변경" 한 줄 |
| `EMPTY` | `DELETE` | `/orders/{id}/refund` | 설명 없음 |
| `EMPTY` | `GET` | `/products/{id}/restock-schedule` | 설명 없음 |

등급이 무작위가 아니라 **함정을 만들도록** 배치돼 있다.

- `DELETE /orders/{id}/refund`(EMPTY) 는 같은 경로의 `POST`(POOR) 와 경쟁한다.
  "환불 신청은 어떻게 취소하나요?" 라는 질문이 설명 있는 POST 로 끌려간다.
- `GET /products/{id}/restock-schedule`(EMPTY) 는 착지할 텍스트가 아예 없다.
  "재입고 언제 되나요?" 가 갈 곳이 없어 상품 상세로 흘러간다.
  이것 때문에 `재입고`·`restock` 같은 표현은 **어느 설명에도 넣지 않았다.**
- `PATCH /orders/{id}/shipping-address` 와 `PATCH /users/{id}/address` 는
  둘 다 POOR 라서 "주소 바꾸려면?" 이 어느 쪽인지 구분되지 않는다.

## 등급 확인

```bash
uv run python -m app.scripts.show_quality   # 또는 루트에서 make show-quality
```

각 엔드포인트의 summary 유무와 description 길이를 표로 출력한다.
시연 중에 "이 API 는 설명이 0자입니다" 를 보여주는 용도다.

등급이 무너지지 않았는지는 테스트가 지킨다. EMPTY 엔드포인트에 누가 친절하게
description 을 달면 실패한다.

```bash
uv run pytest -q
```

## 평가기 입력 만들기

```bash
make dump-spec   # 루트에서
```

`/openapi.json` 을 `backend/app/fixtures/openapi_sample.json` 으로 덤프한다.
서버를 띄우지 않고 앱 객체에서 직접 뽑으므로 실행 중이 아니어도 된다.

## 구현 메모

- 등급은 라우터 코드에 `# QUALITY: GOOD` 주석으로 표시하고,
  생성된 명세에는 `x-quality` 확장으로 남긴다.
  이 확장은 **결과를 등급별로 집계하기 위한 정답지일 뿐이다.**
  평가기의 검색 입력으로 쓰면 자기 답을 베끼는 셈이 된다.
- FastAPI 는 `summary` 를 주지 않으면 함수 이름으로 만들어 채운다
  (`delete_refund` → "Delete Refund"). 진짜 EMPTY 를 재현하려고
  `app/main.py` 의 `custom_openapi()` 에서 이를 걷어낸다.
- `/health` 는 `include_in_schema=False` 다. 명세에 넣으면 평가 코퍼스가 오염된다.
