# 사내 백엔드 이식 가이드

이 저장소는 폐쇄망 사내 시스템에 **파일 단위로 복사**되어 붙는다. 그때 실제로
바꾸는 파일은 아래 5곳뿐이다. 나머지(라우터·스키마·프론트)는 전부 이 경계 뒤의
Port/계약만 알기 때문에 손대지 않는다.

**Phase 12 로 이식의 무게가 바뀌었다.** 이전에는 외부 평가툴의 출력을 계약으로
변환하는 것이 전부였고, 지금은 **평가 파이프라인 자체를 구현**해야 한다
(contract.md §0). 갈아끼우는 파일 수는 그대로지만 2번의 내용이 훨씬 커졌다.

원칙: **경계(Port)와 계약(schema)은 그대로, 구현체만 갈아끼운다.**
의존성 조립은 `backend/app/api/deps.py` 한 곳에서만 바뀐다.

## 바꾸는 파일 — 순서대로

| 순서 | 파일 | 지금(로컬) | 사내에서 무엇으로 |
|---|---|---|---|
| 1 | `backend/.env` | 없음(기본값으로 동작) | `SRE_*` / `CORS_ORIGINS` 환경변수. 사내 DB·SSO·LLM 엔드포인트, 대시보드 출처 URL 지정 |
| 2 | `backend/app/adapters/local/file_spec_repository.py` | fixture 를 읽어 돌려주는 **대역**. 진짜 평가를 하지 않는다 | **실제 평가 파이프라인.** pgvector 조회 → LLM 질문 생성 → bge-m3 임베딩 → 벡터 검색 → hit 계산 (contract.md §0). `SpecRepository` Protocol 의 `evaluate(query_id)` 만 만족하면 된다. 필요한 사내 스펙은 open-questions #72 |
| 3 | `backend/app/services/adapter.py` | 평가 결과의 계약 검증 | **그대로 둔다.** 파이프라인 출력 형태가 계약과 어긋나면 여기에 매핑을 넣는다 — 라우터나 저장소가 아니다. 검증은 없애지 않는다: 내부 코드라도 100문항 수치를 어긋나게 만드는 쪽이 흔하다 |
| 4 | `backend/app/ports/llm.py` (구현체) | 구현 없음(시그니처만) | 사내 **LLM/임베딩** 클라이언트 구현체. `LLMClient` / `Embedder` Protocol 만족. 위 파이프라인이 첫 소비자가 된다 |
| 5 | `backend/app/api/deps.py` | 위 로컬 어댑터를 주입 | 새 구현체를 주입하도록 **조립만** 변경. 라우터·스키마·화면은 안 바뀐다 |

> `ports/auth.py`·`ports/llm.py` 는 **시그니처(Protocol)만** 있고 구현체가 없다.
> 그전까지 이 파일들을 import 하는 코드는 없다.
>
> **`ports/auth.py` 는 당장 쓰이지 않는다** — 이 서비스에 인증이 없다.
> 사내망 안에서 DAC 이 직접 호출한다 (contract.md §0, open-questions #4).

## 왜 이 5곳뿐인가

- **계약이 단일 진실 공급원**이다: `backend/app/schemas/evaluation.py`.
  프론트 타입은 여기서 `openapi-typescript` 로 생성한다(수기 금지).
- 저장소·인증·LLM 은 전부 `ports/` 뒤에 있다. 라우터/서비스는 Protocol 타입만
  알고 구현체를 직접 import 하지 않는다.
- 그래서 사내 포맷·인프라가 바뀌어도 **경계 구현체와 `deps.py` 조립**만 바뀌고,
  화면·라우터·계약은 그대로다.

## 사내 패키지 레포 — HTTP(평문)

사내 표준 레포가 HTTP 로만 제공된다. **이건 HTTPS 검증을 끄는 것과 다르다.**
평문 레포에는 검증할 인증서 자체가 없다. HTTPS 저장소에 대고 검증을 끄는 설정
(`npm strict-ssl=false`, `PIP_DISABLE_...` 류)은 여전히 쓰지 않는다 — 그건
중간자 공격과 사내 CA 재서명을 구분할 수 없게 만든다.

도구마다 필요한 것이 다르다. 컨테이너 안에서 실제로 확인한 결과다:

| 도구 | HTTP 레포에 필요한 것 | 확인한 동작 |
|---|---|---|
| **pip** | **`--trusted-host` 필수** | 없으면 그 레포를 **조용히 무시**하고 PyPI 로 나간다. 경고 한 줄만 남기고 폐쇄망에서는 타임아웃으로 끝난다 |
| **uv** | 없음 | 평문 index 에 그대로 붙는다. `--allow-insecure-host` 는 http 스킴 허용이 아니라 **TLS 인증서 검증을 건너뛰는** 옵션이라 무관하다 (uv 0.11.7 기준) |
| **npm** | 없음 | `strict-ssl` 은 https 연결의 검증 옵션이라 평문 registry 와 무관하다 |

pip 이 `--trusted-host` 없이 내는 경고 — 이 줄이 보이면 원인은 이것 하나다:

```
WARNING: The repository located at <host> is not a trusted or secure host
         and is being ignored.
```

### 값 주입 — 전부 `--build-arg`, 커밋 금지

사내 레포 URL·호스트는 저장소에 넣지 않는다. `.example` 과 이 문서에는 **형식만**
적는다.

```
docker build --target backend \
  --build-arg PYTHON_IMAGE=<사내레지스트리>/python:3.12-slim \
  --build-arg PIP_INDEX_URL=http://<사내레포>/repository/pypi/simple \
  --build-arg PIP_TRUSTED_HOST=<사내레포> \
  --build-arg UV_DEFAULT_INDEX=http://<사내레포>/repository/pypi/simple \
  -t <사내레지스트리>/swagger-rag-eval-backend:1.0 .

docker build --target frontend \
  --build-arg NODE_IMAGE=<사내레지스트리>/node:22-alpine \
  --build-arg NPM_REGISTRY=http://<사내레포>/repository/npm-group/ \
  -t <사내레지스트리>/swagger-rag-eval-frontend:1.0 .
```

- `PIP_TRUSTED_HOST` 는 **호스트만**. 스킴·경로 없이. 포트가 있으면 `host:port`.
- `UV_INSECURE_HOST` 는 보통 비워 둔다. 레포가 http→https 로 리다이렉트하거나
  사설 인증서를 쓸 때만 채운다.
- `UV_SYSTEM_CERTS` 만 **빈 문자열을 주면 안 된다**. 나머지는 비어 있으면
  "설정 안 함" 과 같게 동작한다.

> **ARG 값이 이미지에 남는가**
> `--build-arg` 는 값을 **저장소에 커밋하지 않게** 해 주지만, 그것만으로 이미지에서
> 사라지지는 않는다. `ENV` 로 다시 굳히면 그 값이 이미지 설정에 박혀
> `docker inspect` / `docker history` 로 보인다. 그래서 이 Dockerfile 은 레포 주소를
> **ENV 로 옮기지 않고** 빌드 스테이지의 ARG 로만 둔다. 최종 이미지 두 개를 빌드해
> 확인했다 — `Config.Env` 와 history 어디에도 남지 않는다.
> 다만 **빌드 로그**에는 확장된 명령이 그대로 찍힌다. CI 로그 보존 정책은 별도로 본다.

로컬(컨테이너 밖) 개발은 같은 값을 셸 환경변수로 준다:
`backend/.env.example` 의 "사내망 전용" 절, `frontend/.npmrc.example` 참고.
설정 여부는 `make doctor` 로 확인한다.

## 이식 후 확인

```
make doctor      # 사내 index/registry·CA·환경변수 설정 점검
make gen-types   # 계약이 바뀌었으면 프론트 타입 재생성
make test        # backend 계약 테스트(test_evaluation_contract)
make fixtures    # 계약이 바뀌었으면 fixture 재생성 후 커밋
```

### 계약이 깨진 결과가 들어오면

평가 파이프라인이 필드를 빠뜨리거나 형식을 어기면 `adapter.to_evaluation_report()` 가
`ContractViolation` 을 던지고, API 는 **500 과 함께 어느 필드가 왜 틀렸는지**를
내려준다 (`detail` / `problems`). 대시보드의 error.tsx 가 개발 환경에서 그 문장을
그대로 보여주므로, 브라우저만 보고 원본 JSON 의 어느 줄을 고칠지 알 수 있다.

**조용히 통과시키지 않는다** — 반쯤 그려진 리포트는 틀린 숫자를 맞는 숫자처럼
보이게 한다. 다만 "한 필드가 틀려도 나머지는 보고 싶다" 는 요구가 오면 정책이
바뀐다 (`open-questions.md` #59).

화면이 극단 데이터에서 무너지지 않는지는 경계값 fixture 로 확인한다:

```
make fixtures   # 5종 재생성
```

각각 `/eval/{queryId}` 로 열어 본다. 쿼리 하나가 곧 하나의 경계다 —
`q-lot-status`(정상) / `q-step-cycle-time`(설명 없음·최저) /
`q-wafer-yield`(100%) / `q-no-result`(top3 null) / 초장문.
무엇을 재현하는지는 `backend/app/scripts/make_fixtures.py` 의 docstring 에 있다.

`/ready` 는 기준 쿼리(`SRE_READINESS_QUERY_ID`) 하나를 실제로 평가해 본다.
**사내 구현에서는 이 체크가 비싸진다** — pgvector·LLM 을 전부 타기 때문이다.
그때는 파이프라인 전체가 아니라 pgvector 연결만 보는 쪽으로 좁혀야 한다
(open-questions #71).

## 관련 문서

- 미확정 항목: `docs/open-questions.md`
  — 파이프라인 구현에 필요한 것: **#72**(pgvector 테이블·컬럼, LLM API 형태),
    **#69**(질문 유형 분류), **#70**(실패 원인 분류), **#71**(동기 POST 타임아웃),
    **#73**(프론트가 query_id 를 받는 경로), #6(사내 LLM 스펙)
- 저장소·인덱스·락 파일 정책: `docs/prompts.md` §10
