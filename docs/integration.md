# 사내 백엔드 이식 가이드

이 저장소는 폐쇄망 사내 시스템에 **파일 단위로 복사**되어 붙는다. 그때 실제로
바꾸는 파일은 아래 4곳뿐이다. 나머지(라우터·스키마·프론트)는 전부 이 경계 뒤의
Port/계약만 알기 때문에 손대지 않는다.

원칙: **경계(Port)와 계약(schema)은 그대로, 구현체만 갈아끼운다.**
의존성 조립은 `backend/app/api/deps.py` 한 곳에서만 바뀐다.

## 바꾸는 파일 — 순서대로

| 순서 | 파일 | 지금(로컬) | 사내에서 무엇으로 |
|---|---|---|---|
| 1 | `backend/.env` | 없음(기본값으로 동작) | `SRE_*` / `CORS_ORIGINS` 환경변수. 사내 DB·SSO·LLM 엔드포인트, 대시보드 출처 URL 지정 |
| 2 | `backend/app/services/adapter.py` | fixture 를 계약 형태 그대로 통과(passthrough) + 계약 검증 | 사내 **평가툴 원본 JSON → 계약(EvaluationReport)** 매핑. `to_evaluation_report()` 의 **매핑 부분만** 교체하고 **검증부는 그대로 둔다** — 매핑이 늘수록 검증이 더 필요해진다 |
| 3 | `backend/app/ports/auth.py` (구현체) | 구현 없음(시그니처만) | 사내 **SSO 토큰 검증** 구현체. `AuthProvider` Protocol 만족. `User` 필드는 사내 SSO 클레임에 맞춰 조정 |
| 4 | `backend/app/ports/llm.py` (구현체) | 구현 없음(시그니처만) | 사내 **LLM/임베딩** 클라이언트 구현체. `LLMClient` / `Embedder` Protocol 만족 |
| 5 | `backend/app/adapters/local/file_spec_repository.py` | fixtures 폴더 읽기 | 사내 **DB/사내 API** 저장소 구현체로 교체(또는 새 어댑터 추가). `SpecRepository` Protocol 만족 |
| 6 | `backend/app/api/deps.py` | 위 로컬 어댑터들을 주입 | 새 구현체를 주입하도록 **조립만** 변경. 라우터·서비스는 안 바뀐다 |

> `ports/auth.py`·`ports/llm.py` 는 **시그니처(Protocol)만** 있고 구현체가 없다.
> 소비자(권한 화면·평가 파이프라인)가 생기는 시점에 로컬 구현체부터 붙인다.
> 그전까지 이 파일들을 import 하는 코드는 없다.

## 왜 이 4곳뿐인가

- **계약이 단일 진실 공급원**이다: `backend/app/schemas/evaluation.py`.
  프론트 타입은 여기서 `openapi-typescript` 로 생성한다(수기 금지).
- 저장소·인증·LLM 은 전부 `ports/` 뒤에 있다. 라우터/서비스는 Protocol 타입만
  알고 구현체를 직접 import 하지 않는다.
- 그래서 사내 포맷·인프라가 바뀌어도 **경계 구현체와 `deps.py` 조립**만 바뀌고,
  화면·라우터·계약은 그대로다.

## 이식 후 확인

```
make doctor      # 사내 index/registry·CA·환경변수 설정 점검
make gen-types   # 계약이 바뀌었으면 프론트 타입 재생성
make test        # backend 계약 테스트(test_evaluation_contract)
```

### 계약이 깨진 결과가 들어오면

사내 평가툴이 필드를 빠뜨리거나 형식을 어기면 `adapter.to_evaluation_report()` 가
`ContractViolation` 을 던지고, API 는 **500 과 함께 어느 필드가 왜 틀렸는지**를
내려준다 (`detail` / `problems`). 대시보드의 error.tsx 가 개발 환경에서 그 문장을
그대로 보여주므로, 브라우저만 보고 원본 JSON 의 어느 줄을 고칠지 알 수 있다.

**조용히 통과시키지 않는다** — 반쯤 그려진 리포트는 틀린 숫자를 맞는 숫자처럼
보이게 한다. 다만 "한 필드가 틀려도 나머지는 보고 싶다" 는 요구가 오면 정책이
바뀐다 (`open-questions.md` #59).

화면이 극단 데이터에서 무너지지 않는지는 경계값 fixture 로 확인한다:

```
make edge-fixtures   # E100 / ELOW / E1Q / E3T / EFIRST / ELONG 재생성
```

각각 `/eval/{traceId}` 로 열어 본다. 무엇을 재현하는지는
`backend/app/scripts/make_edge_fixtures.py` 의 docstring 에 있다.

`/ready` 가 200 이면 저장소(사내 DB/API)에서 평가 결과가 실제로 읽히는 것이다.

## 관련 문서

- 미확정 항목: `docs/open-questions.md` (#0 평가엔진 외부, #4 SSO, #5 저장소, #6·#7 LLM)
- 저장소·인덱스·락 파일 정책: `docs/prompts.md` §10
