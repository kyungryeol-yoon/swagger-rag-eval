# swagger-rag-eval — Claude Code 작업 계획 / 프롬프트 팩

> **이 문서의 용도**
> 로컬(또는 GitHub)에서 Claude Code로 하나씩 만들고, 사내망에서 이 저장소를 열람하며
> 같은 것을 CodeMate로 옮겨 심는다. 사내 요구사항이 바뀌면 여기로 돌아와 수정하고,
> 다시 사내에 반영한다. 아래 Phase는 **위에서 아래로, 한 번에 하나씩** 실행한다.

---

## 0. 전제와 제약

| 항목 | 값 | 비고 |
|---|---|---|
| 프론트 | Next.js 16 App Router / React 19 / TypeScript | 사내와 동일 |
| 스타일 | **CSS Modules + `globals.css` CSS 변수** | 사내에 Tailwind 없음 |
| 아이콘 | `lucide-react` | 사내에 이미 존재 |
| 차트 | **순수 SVG** (게이지·도넛·바) | echarts 5.5.0은 "있으면 쓸 수 있는 카드" |
| 백엔드 | FastAPI + Pydantic v2, Python 3.12 | |
| 배포 | 폐쇄망 | CDN·외부 폰트·외부 이미지 **금지** |

### 절대 규칙

1. **새 npm 패키지 추가 금지.** 이 저장소는 파일 단위로 사내에 복사된다. 의존성이 늘면 그 파일은 이식 불가.
2. 컴포넌트는 자기 완결적으로: `Foo.tsx` + `Foo.module.css` 한 쌍. 옆 폴더를 참조하지 않는다.
3. 색·간격·폰트는 하드코딩 금지. 전부 `var(--token)`.
4. SSO / DB / LLM은 **Port 뒤에만** 존재한다 (§2). 비즈니스 로직에서 직접 호출 금지.
5. 커밋은 Phase 단위. 여러 Phase를 한 커밋에 섞지 않는다 — 사내에서 "어디까지 옮겼는지" 추적이 안 된다.

---

## 1. 저장소 구조

```
swagger-rag-eval/
├── CLAUDE.md                     # Phase 0 산출물
├── docs/
│   ├── prompts.md                # 이 문서
│   ├── contract.md               # 응답 계약 (§3)
│   └── open-questions.md         # 미정 항목 추적 (§8)
├── sample-api/                   # ① 평가 "대상" — 진짜 Swagger 생성기
│   └── app/
│       ├── main.py
│       └── routers/{orders,products,users}.py
├── backend/                      # ② 평가기 + 대시보드 API
│   └── app/
│       ├── main.py
│       ├── api/v1/evaluations.py
│       ├── schemas/evaluation.py # ★ 단일 진실 공급원
│       ├── ports/                # ★ 미정 항목 격리 (§2)
│       │   ├── auth.py
│       │   ├── spec_repository.py
│       │   └── llm.py
│       ├── adapters/local/       # 로컬 구현체
│       ├── services/evaluator.py
│       └── fixtures/
└── frontend/                     # ③ 대시보드
    └── src/
        ├── app/eval/[traceId]/page.tsx
        ├── components/eval/*     # 컴포넌트별 tsx + module.css
        ├── lib/api-types.ts      # 생성물, 수기 편집 금지
        └── styles/globals.css    # 토큰
```

`sample-api`를 따로 두는 이유: fixtures로 가짜 JSON만 쓰면 **"description이 부실하면 인식률이 떨어진다"는 이 제품의 전제 자체를 검증할 수 없다.** 잘 쓴 API와 부실한 API를 섞어두고 점수가 실제로 갈리는지 보는 것이 로컬 작업의 진짜 목적이다.

---

## 2. Port — 미정 항목 격리

사내에서 아직 안 정해진 것(SSO, DB, LLM 연동 범위)은 전부 이 3개 파일 뒤로 숨긴다.
**나머지 코드는 이것들이 뭔지 몰라야 한다.**

| Port | 로컬 구현 | 사내 구현 |
|---|---|---|
| `AuthProvider` | 고정 유저 반환 | SSO 토큰 검증 |
| `SpecRepository` | `sample-api`의 `/openapi.json` fetch, 파일 저장 | 사내 DB |
| `LLMClient` / `Embedder` | 규칙 기반 mock (결정론적) | 사내 LLM API |

이렇게 해두면 사내 결정이 내려와도 **바꾸는 파일이 3개**다. 안 그러면 전부 헤집어야 한다.

---

## 3. 응답 계약

대시보드 전체가 이 하나로 그려진다. **화면보다 이 계약을 먼저 고정한다.**

```jsonc
{
  "traceId": "A492",
  "evaluatedAt": "2026-07-22T11:38:00+09:00",
  "target": {
    "method": "GET",
    "path": "/api/v1/orders/{id}/refund-status",
    "summary": "주문 환불 상태 조회",
    "description": "특정 주문 건의 환불 처리 상태, 환불 사유, 처리 일자를 반환합니다."
  },
  "meta": {
    "embeddingModel": "bge-m3",
    "searchMode": "BM25+Hybrid",
    "topK": 3,
    "specVersion": "v3",
    "durationMs": 48210
  },
  "summary": {
    "totalQuestions": 100,
    "top1Accuracy": 61.0,
    "top3Accuracy": 78.0,
    "top1FailCount": 39,
    "top3FailCount": 22,
    "grade": "NEEDS_IMPROVEMENT"
  },
  "questionTypes": [
    {
      "type": "DIRECT",
      "label": "직접 질문",
      "count": 22,
      "ratio": 22.0,
      "top3Accuracy": 95.5
    }
  ],
  "recommendations": [
    {
      "order": 1,
      "title": "설명(Description) 보강",
      "description": "summary/description이 비어있거나 지나치게 짧은 API가 다수 발견됐습니다.",
      "priority": "HIGH",
      "failShare": 45.0
    }
  ],
  "failures": [
    {
      "id": "q_017",
      "question": "환불 신청은 어떻게 취소하나요?",
      "questionType": "USER_NL",
      "expected": { "method": "DELETE", "path": "/orders/{id}/refund" },
      "results": [
        { "rank": 1, "method": "GET", "path": "/orders/{id}/refund-status", "score": 0.812 },
        { "rank": 2, "method": "POST", "path": "/orders/{id}/refund", "score": 0.774 },
        { "rank": 3, "method": "GET", "path": "/orders/{id}", "score": 0.701 }
      ],
      "hit": false,
      "expectedRank": 7,
      "failureCategory": "METHOD_MISMATCH",
      "reason": "질문의 '취소'를 조회(GET) 의도로 오인식하여 DELETE 엔드포인트가 후순위로 밀림"
    }
  ],
  "previous": { "traceId": "A311", "top3Accuracy": 64.0 }
}
```

### Enum (백엔드가 확정해서 내려준다)

```
grade            CRITICAL | NEEDS_IMPROVEMENT | FAIR | GOOD
priority         HIGH | MEDIUM | LOW
questionType     DIRECT | USER_NL | DOMAIN_TERM | PARAMETER | ERROR_CASE | SHORT_KEYWORD | MIXED_LANG
failureCategory  METHOD_MISMATCH | SIMILAR_RESOURCE | SYNONYM_MISS | DESCRIPTION_MISSING | PARAM_MISSING
```

> 프론트에서 문자열 비교로 색을 정하지 않는다. 반드시 enum → 토큰 매핑 테이블 하나를 둔다.

### 첨부 시안 대비 변경점

**추가**
- `questionTypes[].top3Accuracy` — 유형별 인식률. 시안엔 분포만 있는데, **"한영 혼합에서 40%"** 같은 게 나와야 액션이 나온다. 추가 가치가 가장 큰 항목.
- `previous` — 재생성 Before/After 델타(78% → 91%). 이 제품의 핵심 가치인데 시안에 없다.
- `results[].score` — 유사도 점수. "얼마나 아깝게 놓쳤나"가 보여야 한다.
- `meta` — 재현성(임베딩 모델, 인덱스 버전, 소요시간).

**제거**
- 브라우저 크롬(신호등·URL바) — 목업 장식.
- 78%가 우상단 링·게이지·등급표에 3번 중복 → **게이지 하나로**.
- 이모지 얼굴 "개선 필요" 카드 — 게이지와 의미 중복.
- "평가 기준" 상세 → `<details>` 접이식으로 격하.

---

## 4. Phase 프롬프트

각 블록을 **그대로 복사해서** Claude Code에 하나씩 준다. 앞 Phase 결과를 눈으로 확인한 뒤 다음으로 넘어간다.

### Phase 0 — CLAUDE.md

```
저장소 루트에 CLAUDE.md를 만들어줘. 내용은 아래 그대로.

---
# swagger-rag-eval

Swagger 명세의 RAG 검색 인식률 평가 대시보드.
사용자가 API를 만들면 Swagger가 자동 생성되고, 다른 사용자가 AI로 질문했을 때
그 Swagger를 잘 찾아내는지 평가한 리포트를 보여준다.

## 스택 (사내 프로젝트와 100% 일치 — 임의 변경 금지)
- Next.js 16 App Router / React 19 / TypeScript
- 스타일: CSS Modules + globals.css의 CSS 변수 토큰
- 아이콘: lucide-react
- 차트: 순수 SVG. 라이브러리 사용 금지
- 백엔드: FastAPI + Pydantic v2, Python 3.12

## 절대 규칙
- 새 npm 패키지 추가 금지. 이 저장소는 폐쇄망 프로젝트에 파일 단위로
  복사되므로 의존성이 늘면 이식 불가
- Tailwind / CSS-in-JS / UI 프레임워크 사용 금지
- CDN, 외부 폰트, 외부 이미지 참조 금지
- 컴포넌트는 Foo.tsx + Foo.module.css 한 쌍으로 자기 완결
- 색/간격/폰트 하드코딩 금지. 전부 var(--token)
- SSO/DB/LLM은 backend/app/ports/ 뒤에만 존재. 로직에서 직접 호출 금지
- backend/app/schemas/evaluation.py 가 응답 계약의 단일 진실 공급원
- 프론트 타입은 openapi-typescript로 생성. 수기 작성 금지
- 커밋은 Phase 단위. 여러 Phase를 한 커밋에 섞지 말 것

## 시안
docs/mockup.svg 는 레이아웃·색·분위기 참고용이다.
수치·문구·정보 구조의 진실은 docs/contract.md 이며, 둘이 충돌하면 contract.md 가 이긴다.
시안에는 알려진 오류가 있으므로 docs/prompts.md §9 를 반드시 함께 읽을 것.

## 작업 방식
- 지시받은 Phase 하나만 수행하고 멈춘다. 앞서 나가지 않는다
- 파일을 새로 만들 때마다 docs/open-questions.md 에 미정 사항을 기록한다
---
```

### Phase 1 — 스캐폴딩

```
CLAUDE.md를 읽고 모노레포 뼈대를 세팅해줘.

- sample-api/ : uv + FastAPI. /health 만. 라우터는 아직 없음
- backend/    : uv + FastAPI. CORS 허용. /health 만
- frontend/   : Next.js 16 App Router + TypeScript.
                Tailwind 없이(create-next-app 옵션에서 제외), src/ 디렉토리 사용
- 루트 Makefile: dev / build / lint / test 타겟
- .gitignore, README.md(1문단)

화면과 스키마는 아직 만들지 마. 세 서버가 각각 뜨는 것만 확인되면 끝.
```

### Phase 2 — sample-api (평가 대상)

```
sample-api에 라우터 3개를 만들어줘. 실제 동작은 필요 없고 응답은 더미면 된다.
목적은 /openapi.json 을 생성해서 평가기 입력으로 쓰는 것.

핵심: description 품질을 의도적으로 3등급으로 나눈다.
- GOOD  : summary + 상세 description + 파라미터 설명 + 응답 필드 설명 + 동의어 포함
- POOR  : summary만 한 줄
- EMPTY : 아무 설명 없음

엔드포인트 (등급은 코드 주석으로 명시):
  orders
    GET    /orders/{id}                      GOOD
    GET    /orders/{id}/refund-status        GOOD
    POST   /orders/{id}/refund               POOR
    DELETE /orders/{id}/refund               EMPTY
    PATCH  /orders/{id}/shipping-address     POOR
    GET    /orders/{id}/shipping-status      GOOD
  products
    GET    /products/{id}                    GOOD
    GET    /products/{id}/stock              POOR
    GET    /products/{id}/restock-schedule   EMPTY
  users
    GET    /users/{id}                       GOOD
    PATCH  /users/{id}/address               POOR

Pydantic 모델의 Field(description=...) 까지 등급에 맞춰 채우거나 비울 것.
완료 후 /openapi.json 을 backend/fixtures/openapi_sample.json 으로 덤프하는
스크립트도 만들어줘.
```

> 이 등급 배치가 나중에 부장님 앞에서의 **근거**가 된다. "EMPTY 등급 3개가 실패의 62%를 차지" 같은 문장이 여기서 나온다.

### Phase 3 — 응답 계약

```
docs/contract.md 의 JSON을 backend/app/schemas/evaluation.py 에
Pydantic v2 모델로 작성해줘.

- grade / priority / questionType / failureCategory 는 StrEnum
- 모든 필드에 description 달 것 (OpenAPI 문서화 겸용)
- backend/app/fixtures/eval_A492.json 에 이 스키마를 만족하는 더미 데이터 생성.
  100문항 요약 + questionTypes 7종 + recommendations 3건 + failures 22건 전체.
  failures 는 Phase 2의 EMPTY/POOR 엔드포인트에 집중되도록 현실적으로 구성
- GET /api/v1/evaluations/{trace_id} 가 fixture를 반환
- 스키마 검증 pytest 포함

평가 로직은 아직 만들지 마. fixture 반환만.
```

### Phase 3.5 — 타입 생성 (수행 완료)

계약이 확정된 직후, 화면을 만들기 전에 한다. 순서가 중요하다 —
컴포넌트를 먼저 만들면 타입을 수기로 적게 되고, 그 순간 계약이 두 곳으로 갈라진다.

```
백엔드 /openapi.json 으로부터 프론트 타입을 생성하는 파이프라인을 만들어줘.

- frontend 에 openapi-typescript 를 devDependency 로만 추가
- package.json scripts:
    "gen:types": "openapi-typescript http://localhost:8000/openapi.json -o src/lib/api-types.ts"
- 생성한 src/lib/api-types.ts 는 .gitignore 에서 제외하고 커밋할 것
  (사내 Nexus에 openapi-typescript가 없을 수 있어 생성물 자체가 이식 자산)
- src/lib/types.ts 에 자주 쓰는 것만 재노출:
    export type Evaluation = components["schemas"]["EvaluationReport"]
- make gen-types 가 동작하는지 확인

runtime dependency 는 절대 추가하지 말 것.
```

**실제 산출물**

| 파일 | 내용 |
|---|---|
| `frontend/src/lib/api-types.ts` | 생성물(471줄). 수기 편집 금지, **커밋 대상** |
| `frontend/src/lib/types.ts` | 재노출 15종. `Evaluation`, `Failure`, `Grade` 등 |

- Pydantic `StrEnum` 이 문자열 리터럴 유니온으로 떨어진다.
  `Grade: "CRITICAL" | "NEEDS_IMPROVEMENT" | "FAIR" | "GOOD"` —
  Phase 6 의 enum → 토큰 매핑 테이블이 컴파일 타임에 안전해지는 근거다.
- **생성물을 커밋하는 이유**: 사내에 `openapi-typescript` 가 없을 수 있다.
  파일만 복사하면 되도록 산출물 자체를 이식 자산으로 취급한다.
  대신 계약이 바뀌면 GitHub 쪽에서 재생성해 다시 복사한다 (§6 루프).
- **주의**: `gen:types` 는 백엔드가 8000에 떠 있어야 동작한다.
  안 떠 있으면 실패하는데, 기존 `api-types.ts` 가 남아 있어 실패를 놓치기 쉽다.
- 최상위 스키마 이름은 `EvaluationResponse` 가 아니라 **`EvaluationReport`** 다
  (`backend/app/schemas/evaluation.py`). 노출 이름은 `Evaluation` 이라 화면 코드에는 영향이 없다.

### Phase 4 — Port 격리

```
backend/app/ports/ 에 Protocol 3개를 정의하고,
adapters/local/ 에 로컬 구현체를 만들어줘.

ports/auth.py           AuthProvider.get_current_user() -> User
ports/spec_repository.py SpecRepository.get_spec(id), save_spec(id, spec)
ports/llm.py            LLMClient.complete(prompt), Embedder.embed(texts)

로컬 구현:
- LocalAuthProvider : 고정 유저 반환
- FileSpecRepository : backend/fixtures/*.json 읽고 쓰기
- MockLLMClient / MockEmbedder : 결정론적. 해시 기반 가짜 벡터 or 규칙 기반.
  같은 입력이면 항상 같은 출력 (테스트 안정성)

FastAPI Depends()로 주입. 서비스 코드는 Protocol 타입만 알게 할 것.
docs/open-questions.md 에 "사내 이식 시 교체 필요" 항목으로 3개 기록.
```

### Phase 4.5 — 배포 대비 설정 (수행 완료)

화면을 만들기 전에 한다. 나중에 하면 `NEXT_PUBLIC_` 이 이미 여기저기 박혀 있고,
그걸 걷어내는 것이 화면을 다시 만드는 일이 된다.

> **Dockerfile · docker-compose · k8s manifest 는 만들지 않는다.** 코드와 문서만.
> 배포 형태(#35)와 Ingress 경로(#34)가 미정인 상태에서 매니페스트를 쓰면
> 확정됐을 때 버리는 양이 더 커진다.

```
A. frontend
- next.config.ts 에 output: 'standalone' 추가
- basePath 를 process.env.BASE_PATH 로 읽되 기본값 ''
- src/lib/config.ts 신설:
    export const serverApiBase = process.env.API_BASE_URL ?? 'http://localhost:8000'
  서버 컴포넌트 전용. NEXT_PUBLIC_ 접두사 사용 금지
  fetch 하는 곳은 전부 이걸 경유
- app/api/health/route.ts : { status: 'ok' } 반환
- .env.example 작성

B. backend
- CORS allow_origins 를 환경변수 CORS_ORIGINS(콤마 구분)로. 기본값 http://localhost:3000
- /health 유지, /ready 추가 (fixture 로딩 확인 후 200)
- SIGTERM graceful shutdown
- .env.example 작성

C. sample-api
- sample-api/README.md 신설 (무엇인지 / 단독 실행법 / 등급표 /
  "배포 대상이 아니라 로컬·시연 전용" 명시)
- app/scripts/show_quality.py : 엔드포인트별 summary 유무와 description 길이 표 출력
  (Makefile 에 show-quality 타겟)

D. 공통
- 하드코딩된 localhost 전수 검사 후 config/env 로 치환
- 루트 README 에 환경변수 표 + "sample-api 는 시연용" 명시

제약: 기존 API 응답과 화면 동작은 바뀌면 안 된다.
```

**핵심 판단**

- **`NEXT_PUBLIC_` 을 하나도 쓰지 않는다.** 그 접두사가 붙은 값은 빌드 타임에
  클라이언트 번들로 박힌다. 그 순간 이미지 하나를 dev → stg → prd 로 승격하는 것이
  불가능해지고, 환경마다 다시 빌드해야 한다. 백엔드 주소는
  `frontend/src/lib/config.ts` 를 경유해 **서버에서만** 읽는다.
  이 파일은 브라우저에서 import 되면 예외를 던져 스스로를 지킨다.
- **`BASE_PATH` 만 빌드 타임 값이다.** Next 의 `basePath` 는 런타임에 못 바꾼다.
  Ingress 경로(#34)가 확정될 때까지 남는 유일한 빌드 타임 변수다.
- **`/health` 와 `/ready` 를 분리한다.** `/health` 는 프로세스 생존만 본다.
  여기서 데이터 소스까지 확인하면 데이터가 잠깐 안 읽힐 때 파드가 재시작되며
  상황이 악화된다. `/ready` 는 저장소를 Port 경유로 읽어보고 실패 시 503 을 준다 —
  사내에서 DB 어댑터로 바뀌면 이 체크가 그대로 DB 연결 확인이 된다.
- **SIGTERM 은 앱이 잡지 않는다.** uvicorn 이 받아서 새 연결을 끊고 처리 중인
  요청을 기다린 뒤 lifespan 의 `finally` 로 들어온다. 앱이 신호를 직접 잡으면
  오히려 그 graceful shutdown 을 가로챈다. 유예 시간은 실행 옵션으로 준다:
  `uvicorn app.main:app --timeout-graceful-shutdown 20`
- **`CORS_ORIGINS` 는 문자열로 받아 직접 쪼갠다.** pydantic-settings 는 list 타입
  필드를 환경변수에서 읽을 때 JSON 으로 파싱하려 들어서, 콤마 구분 문자열을 주면 터진다.

### Phase 4.6 — 크로스 플랫폼 + 폐쇄망 패키지 저장소 (수행 완료)

사내 Windows PC 에서 `make` 가 깨졌고, 사내 저장소·CA 전환이 필요해졌다.
**컴포넌트가 아니라 빌드·설치 경로만 고친다.**

```
A. Makefile 에서 셸 로직 제거
   scripts/tasks.py 신설(표준 라이브러리만). 모든 타겟은
       setup:
           python scripts/tasks.py setup
   형태 한 줄로만. [ ] ( ) || 파이프 grep awk sed find 금지.
   dev 는 make -j 대신 Python 이 프로세스를 띄우고 관리한다.
   doctor 서브커맨드 신설 — 사내 PC 최초 셋업 진단.

B. Python 저장소 (uv)
   pyproject.toml 에는 주석 예시만. 실제 URL 금지.
   전환은 환경변수로: UV_DEFAULT_INDEX / UV_SYSTEM_CERTS

C. Node 저장소 (npm)
   frontend/.npmrc.example 신설. .npmrc 는 gitignore.
   strict-ssl=false 금지.

D. 락 파일 정책 문서화 (§10)
E. README 사내망 최초 셋업 절
```

**핵심 판단**

- **`python` vs `python3`.** Windows 는 `python`, macOS/Linux 는 보통 `python3` 만 있다.
  make 조건문 `ifeq ($(OS),Windows_NT)` 로 가른다 — 셸이 아니라 make 문법이라
  cmd.exe 를 거치지 않는다. `make PY=py test` 로 덮어쓸 수도 있다.
- **`UV_NATIVE_TLS` 는 더 이상 유효하지 않다.** uv 0.11 에서
  `--native-tls` → `--system-certs`, `UV_NATIVE_TLS` → `UV_SYSTEM_CERTS` 로 바뀌었다.
  **옛 이름은 오류 없이 조용히 무시된다.** 설정했는데 인증서 오류가 그대로면
  이걸 가장 먼저 의심한다. (`uv sync --help` 로 현재 이름을 확인할 수 있다.)
- **`dev` 는 자식을 별도 프로세스 그룹으로 띄운다.** 안 그러면 uvicorn `--reload` 의
  워커와 next dev 의 자식이 남아 포트를 계속 물고 있다. POSIX 는
  `start_new_session` + `killpg(SIGTERM)`, Windows 는
  `CREATE_NEW_PROCESS_GROUP` + `CTRL_BREAK_EVENT`.
- **KeyboardInterrupt 에만 기대지 않는다.** 백그라운드로 실행하면 SIGINT 가
  무시된 채 상속돼 `KeyboardInterrupt` 가 영영 오지 않는다. SIGINT/SIGTERM/SIGBREAK
  핸들러를 명시적으로 설치한다.
- **로그에 서비스 이름을 붙인다.** `make -j3` 는 세 서버 출력을 그대로 섞어서
  어느 서버가 죽었는지 알 수 없었다. Python 이 줄마다 접두사를 붙인다.

### Phase 5 — 디자인 토큰

```
frontend/src/styles/globals.css 에 CSS 변수 토큰을 정의해줘.

색 (첨부 시안 기준, 임의 변경 금지):
  --bg #05070B  --surface #111827  --surface-2 #0F172A  --border #1E293B
  --text #E2E8F0  --text-dim #94A3B8  --text-mute #64748B
  --sky #38BDF8  --violet #A78BFA  --green #4ADE80  --amber #FBBF24  --red #F87171

그 외:
- 폰트: Pretendard(본문) + 모노 1종을 public/fonts 에 로컬 번들, @font-face 선언.
  외부 CDN 절대 금지. 폰트 파일이 아직 없으면 경로만 잡고 TODO 주석
- 수치·경로 표기에 font-variant-numeric: tabular-nums 적용 유틸 클래스
- 간격 스케일 --space-1..8, radius, 그림자 토큰
- enum → 색 매핑을 CSS 변수로: --grade-critical, --priority-high 등

확인용으로 app/dev/tokens/page.tsx 에 토큰 전체를 눈으로 볼 수 있는 페이지.
```

### Phase 6 — 컴포넌트 (하나씩!)

**한 번에 하나만 요청한다.** "컴포넌트 다 만들어줘"로 주면 품질이 급락한다.

```
components/eval/GaugeRing/ 을 만들어줘.
- GaugeRing.tsx + GaugeRing.module.css
- 순수 SVG. stroke-dasharray / stroke-dashoffset
- props: value(0-100), grade, size?
- 등급별 색은 var(--grade-*) 에서. 컴포넌트에 hex 하드코딩 금지
- prefers-reduced-motion 존중
- app/dev/components/page.tsx 에 여러 값으로 렌더해서 확인 가능하게
```

이 형식을 유지하며 아래 순서로 진행:

| 순서 | 컴포넌트 | 메모 |
|---|---|---|
| 1 | `GaugeRing` | 78% 하나만. 중복 표시 제거 |
| 2 | `SummaryCards` | 6개 지표. `previous` 있으면 델타 뱃지 |
| 3 | `TargetApiCard` | method 뱃지 + 경로 + 설명 |
| 4 | `QuestionTypeChart` | 도넛 + 범례. **유형별 인식률 컬럼 포함** |
| 5 | `RecommendationCards` | 3장. priority 뱃지, failShare 바 |
| 6 | `FailureTable` | 정렬·필터·페이징. score 표시 |
| 7 | `ActionPanel` | 재생성 CTA 2개 |

### Phase 7 — 조립

```
app/eval/[traceId]/page.tsx 를 서버 컴포넌트로 만들고
backend fetch 후 Phase 6 컴포넌트들을 조립해줘.

레이아웃은 docs/mockup.svg 참고. 단 prompts.md §9 의 "시안을 따르지 말 것"
목록을 먼저 읽고, 거기 해당하는 부분은 시안을 무시할 것.
색은 반드시 var(--token) 사용. 시안의 hex를 직접 옮겨 적지 말 것.

loading.tsx / error.tsx / not-found.tsx 도 함께.
반응형: 1440 기준, 1024 이하에서 2단, 768 이하에서 1단.
```

> **이미지는 이 Phase에서 처음 준다.** Phase 5~6에서 미리 주면 토큰을 무시하고
> 시안 hex를 하드코딩한다. SVG 원본(`docs/mockup.svg`)을 주는 것이 PNG보다 낫다 —
> 텍스트라서 좌표·색·라벨을 정확히 읽는다.

### Phase 8 — 평가 파이프라인 (요구사항 확정 후)

```
services/evaluator.py 에 실제 파이프라인을 구현해줘.
openapi.json 파싱 → 문항 생성 → 검색 → 채점 → 실패 원인 분류 → 계약 JSON 조립.
LLM/임베딩은 ports 경유. Phase 2의 sample-api openapi.json 으로 E2E 테스트.

검증 목표: GOOD 등급 엔드포인트의 인식률이 EMPTY 등급보다 유의하게 높게 나올 것.
안 나오면 파이프라인이 잘못된 것이므로 보고할 것.
```

---

## 5. 사내 이식 절차

### 원칙: CodeMate에게 **생성**을 시키지 말고 **번역**을 시킨다

성능이 약한 도구는 "대시보드 만들어줘" 같은 열린 과제에서 무너지고, 정답이 정해진 변환 작업은 그럭저럭 해낸다. 그래서 GitHub 저장소의 진짜 산출물은 **CodeMate에게 줄 정답지**다.

| CodeMate에게 줄 것 | 시킬 말 |
|---|---|
| `Foo.tsx` + `Foo.module.css` 원본 | "이 컴포넌트를 사내 컨벤션에 맞게 옮겨줘" |
| 함수 시그니처 + docstring (본문 비움) | "이 함수 본문을 채워줘" |
| pytest 케이스 | "이 테스트를 통과시켜줘" |
| 계약 JSON | "이 스키마에 맞는 응답을 만들어줘" |

### 이식 순서

1. `globals.css` 토큰 → **먼저**. 이게 없으면 컴포넌트가 색을 못 찾는다
2. 폰트 파일 + `@font-face`
3. 계약 스키마 (`evaluation.py` → 사내 백엔드)
4. 컴포넌트 1개 → 화면에서 확인 → 다음 1개
5. 페이지 조립
6. Port 3개를 사내 구현으로 교체

**한 번에 하나씩, 확인하고 다음.** 여러 개를 몰아 넣으면 뭐가 깨졌는지 못 찾는다.

### 이식 체크리스트 (파일마다)

- [ ] import에 저장소 밖 패키지가 없나
- [ ] hex 색상 하드코딩이 없나
- [ ] 외부 URL(폰트·이미지·CDN) 참조가 없나
- [ ] 옆 컴포넌트를 참조하지 않나

---

## 6. 변경 전파 루프

사내 요구사항이 바뀌면 **사내에서 바로 고치지 말고** 이 순서로 돈다.

```
사내 변경 발생
  → docs/open-questions.md 에 기록 (무엇이 확정됐는지)
  → 계약(contract.md + evaluation.py) 먼저 수정
  → fixture 갱신
  → 영향받는 컴포넌트만 수정
  → GitHub push
  → 사내에서 해당 파일만 다시 이식
```

사내에서 먼저 고치면 두 저장소가 갈라지고, 그 순간부터 "GitHub 참고" 전략이 무너진다. **계약이 항상 먼저다.**

---

## 7. 타임박스

**로컬 슬라이스는 2주 안에 끝낸다.**

SSO·DB·연동 범위가 확정되지 않은 상태에서 로컬을 너무 정교하게 만들면, 결정이 내려왔을 때 갈아엎을 양이 오히려 커진다.

완료 정의(DoD):

- [ ] `sample-api`가 진짜 `openapi.json`을 뱉는다
- [ ] 계약 JSON이 확정되고 Pydantic + TS 타입이 양쪽에 존재한다
- [ ] 대시보드 화면이 fixture로 완전히 그려진다
- [ ] Port 3개가 격리되어 있다
- [ ] **환경변수로 배포 환경을 분리할 수 있다** — 같은 산출물을 재빌드 없이
      dev → stg → prd 로 승격할 수 있고, 코드에 환경별 값이 박혀 있지 않다
- [ ] `docs/open-questions.md`에 사내에 물어볼 항목이 목록화되어 있다

**목표는 "완성"이 아니라 계약 확정 + UI 확정 + 미정 항목 목록화다.**

---

## 8. 미정 항목 (docs/open-questions.md 초기 내용)

사내에 확인해야 할 것들. 답이 오는 대로 여기 채우고 §6 루프를 돈다.

| # | 항목 | 왜 필요한가 | 상태 |
|---|---|---|---|
| 1 | SSO 인증 방식 (토큰 형태, 검증 엔드포인트) | `AuthProvider` 구현 | 미정 |
| 2 | Swagger 원본 저장 위치 (DB? 파일? API?) | `SpecRepository` 구현 | 미정 |
| 3 | 사내 LLM 엔드포인트 스펙 + 임베딩 모델 제공 여부 | `LLMClient` / `Embedder` | 일부 확인 |
| 4 | 평가 대상 범위 — API 1개인가, 서비스 전체인가 | 화면 구조가 바뀜 | 미정 |
| 5 | 질문 100개 생성 주체 — LLM 생성인가 사람 검수인가 | 파이프라인 설계 | 미정 |
| 6 | 실패 원인 분류를 LLM으로 할지 룰베이스로 할지 | `failureCategory` 산출 | 미정 |
| 7 | 평가 이력 보관 기간 / 재실행 주기 | `previous` 델타, 추이 차트 | 미정 |
| 8 | "Swagger 재생성" 결과의 반영 방식 (PR? 직접 수정?) | ActionPanel 동작 | 미정 |
| 9 | Next.js 버전 — 사내 16.0.0은 보안 패치 대상 | 16.2.11 LTS 권고 | 확인 필요 |

> 4번과 5번이 화면 구조를 가장 크게 흔든다. 가능하면 Phase 6 시작 전에 답을 받아둘 것.

---

## 9. 시안(mockup) 취급 규칙

`docs/mockup.svg` 는 **분위기와 레이아웃의 참고 자료**이지 사양서가 아니다.
시안에는 아래의 알려진 오류가 있으며, 그대로 옮기면 그대로 버그가 된다.

### 9-1. 시안을 따르지 말 것 (CLAUDE.md에도 반영)

| # | 시안의 문제 | 조치 |
|---|---|---|
| 1 | 78%가 우상단 링·게이지·등급표 3곳에 중복 표시 | 게이지 **하나만** 남긴다 |
| 2 | 이모지 얼굴 "평가 상태" 카드가 게이지와 의미 중복 | 제거 |
| 3 | "실패 22건 중 3건 표시"인데 버튼은 "나머지 97건 보기" | 실제 실패 건수 기준으로 계산 |
| 4 | "실패 원인 중 62%"가 카드의 45/23/32%와 불일치 | 계약에서 산출한 값으로 대체 |
| 5 | 원인 비중 3개 합이 100% | 한 실패에 원인이 둘일 수 있음 → "중복 집계" 주석 필요 |
| 6 | 브라우저 크롬(신호등·URL바) | 제거. 목업 장식일 뿐 |
| 7 | 요약 카드 6개 중 4개가 상호 계산 가능 (100/61/78/39/22) | 3개로 압축, 나머지는 툴팁 |
| 8 | "평가 기준" 블록이 본문 폭을 크게 차지 | `<details>` 접이식으로 격하 |
| 9 | 좌측 하단이 비어 있고 "권장 액션"만 우측에 붙음 | 좌측에 **유형별 인식률 막대** 배치 |

### 9-2. 문구 수정

| 현재 | 수정안 | 이유 |
|---|---|---|
| `BM25+Hybrid (K=3)` | `Hybrid (BM25 + 벡터), Top-3` | Hybrid가 이미 BM25+벡터를 의미. 중복 |
| `개선 추천` | `권장 조치` | recommendation 직역 티 |
| `평가 질문 100개 (검수 완료)` | 검수 주체 명시 (`LLM 생성 · 사람 검수` 등) | 신뢰도 판단 근거 |
| `Hit 판정: 상위 3위 이내 포함` | `Top-3 안에 기대 API가 있으면 성공` | 사용자 언어로 |
| `원인 추정` | `추정 원인` | 어순 |
| `더보기 · 나머지 N건 보기` | `실패 N건 전체 보기` | 동사 중복 제거 |

> **철회된 제안**: 등급 라벨을 `미흡/주의/양호/우수` 로 바꾸자는 항목이 여기 있었으나
> 2026-07-22 철회했다. `contract.md` §3 의 `심각/개선 필요/보통/우수` 를 확정으로 한다.
> 라벨 문자열은 프론트에서 `src/lib/enumTokens.ts` 의 `gradeLabel` 한 곳에만 존재한다.

### 9-3. CTA 재설계 (중요)

시안의 `Swagger 직접 보강하기` / `Swagger 재생성하기` 는 **차이가 안 보이고,
파괴적 동작이 primary 색을 달고 있다.**

- 재생성은 기존 `description`을 덮어쓰는 동작 → 확인 단계 필수
- 문구 제안: `설명 직접 수정` (secondary) / `AI로 설명 다시 만들기` (primary + 확인 다이얼로그)
- 다이얼로그 문구: "기존 설명이 교체됩니다. 되돌리려면 이전 버전에서 복원하세요."
- 실행 후에는 **Before/After 비교 화면**으로 이동 (78% → 91%)

### 9-4. 시안에 없어서 새로 그려야 할 화면

완료 화면만 있으면 실제 개발 때 반드시 막힌다. 평가가 수십 초 걸리므로
**진행 중 화면이 실제로는 가장 자주 보이는 화면이다.**

| 상태 | 필요한 것 |
|---|---|
| 실행 중 | 진행률, 현재 단계(문항 생성 → 검색 → 채점), 예상 시간, 취소 |
| 로딩 | 스켈레톤 (레이아웃 시프트 방지) |
| 에러 | 무엇이 실패했고 무엇을 하면 되는지. 사과하지 말 것 |
| 빈 상태 | 평가 이력 없음 → 첫 평가 실행 유도 |
| 권한 없음 | SSO 미인증 시 |

### 9-5. 그 외 보강 항목

- 실패 테이블에 **필터/정렬** (원인별·유형별·유사도순)
- 평가 대상의 **Swagger 버전 표기** — 재생성 전후 구분이 안 됨
- 재실행 시각 + "이 결과는 N일 전 명세 기준" 경고
- 키보드 포커스 링, `prefers-reduced-motion` 대응


---

## 10. 패키지 저장소와 락 파일 정책

폐쇄망은 PyPI·npmjs 에 나갈 수 없다. 사내 index/registry 를 쓰고,
TLS 는 사내 CA 로 재서명된다. 여기서 **락 파일이 갈라진다.**

### 10-1. 전환은 환경변수로만 한다

사내 URL 을 `pyproject.toml` 이나 `.npmrc` 에 박아 커밋하면
두 저장소가 갈라지고 §6 변경 전파 루프가 깨진다. 같은 파일이 양쪽에서
그대로 쓰이게 두고, 환경만 다르게 준다.

| 대상 | 설정 | 비고 |
|---|---|---|
| Python index | `UV_DEFAULT_INDEX` | PEP 503 경로. 보통 `/simple` 로 끝난다 |
| Python TLS | `UV_SYSTEM_CERTS=true` | **uv 0.11 부터의 이름.** 옛 `UV_NATIVE_TLS` 는 조용히 무시된다 |
| npm registry | `frontend/.npmrc` | `.npmrc.example` 복사. 커밋 금지 |
| Node TLS | `NODE_EXTRA_CA_CERTS` | npm 뿐 아니라 next build 에도 적용돼 `.npmrc` 의 `cafile` 보다 낫다 |

`strict-ssl=false` 는 쓰지 않는다. 인증서 검증을 통째로 끄는 것이라
중간자 공격과 사내 CA 재서명을 구분할 수 없게 된다. 오류의 해결이 아니라 은폐다.

설정이 됐는지는 `make doctor` 로 본다. 사내 PC 최초 셋업에서 뭐가 빠졌는지
한 화면에 나온다.

### 10-2. 락 파일은 한 방향으로만 흐른다

**커밋된 `uv.lock` / `package-lock.json` 은 GitHub·로컬 기준이다.**
사내에서 `uv lock` / `npm install` 로 다시 만들어진 락은
**사내 로컬 전용이며 GitHub 로 되돌리지 않는다.**

락에는 인덱스 URL 과 아티팩트 해시가 박힌다. 사내 락을 GitHub 에 올리면
사내 주소가 공개되고, 로컬에서는 그 락으로 설치가 안 된다.

의존성이 바뀌면 §6 과 같은 방향으로 돈다.

```
의존성 변경 필요
  → GitHub 에서 pyproject.toml / package.json 을 먼저 고친다
  → GitHub 에서 락을 갱신하고 커밋한다
  → 사내는 그 pyproject.toml / package.json 을 받는다
  → 사내에서 make lock / npm install 로 사내 락을 만든다 (커밋하지 않는다)
```

사내에서 먼저 의존성을 추가하면 그 사실이 GitHub 에 남지 않아,
다음 이식 때 "왜 여기선 안 되지"가 반복된다. **선언이 항상 먼저다.**

> 애초에 새 npm 패키지는 추가하지 않는다 (CLAUDE.md 절대 규칙 1).
> 이 절은 주로 Python 쪽과, 이미 있는 의존성의 버전 갱신에 해당한다.

### 10-3. Makefile 에 셸 로직을 두지 않는다

Windows 에서 make 는 레시피를 `cmd.exe` 로 실행한다. `[ -f x ]`, `( )`,
`||`, 파이프, `grep`/`awk` 는 전부 깨진다. git bash 에서만 되는 Makefile 은
사내 PC 에서 재현이 안 된다.

모든 타겟은 `scripts/tasks.py` 를 한 줄로 부르기만 한다. 로직은 Python 에 있다.
`python` 실행 파일 이름만 make 조건문(`ifeq ($(OS),Windows_NT)`)으로 가른다 —
이건 셸이 아니라 make 자체의 문법이라 cmd 를 거치지 않는다.

`tasks.py` 는 표준 라이브러리만 쓴다. 의존성을 설치하려는 스크립트가
의존성을 요구하면 순환이다.
