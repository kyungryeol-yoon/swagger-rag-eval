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

### 실제 진행 이력

아래 절들은 Phase 번호순으로 정리돼 있지만, **실제로 작업한 순서는 다르다.**
번호는 성격별 묶음이고 순서가 아니다. 사내 이식은 이 표의 순서를 따를 필요가
없다 — §5 의 이식 순서를 쓴다.

커밋 순서대로:

| # | 커밋 | Phase | 내용 |
|---|---|---|---|
| 1 | `1a43496` | 0 | 프로젝트 규칙과 기획 문서 |
| 2 | `378e55d` | 1 | 모노레포 스캐폴딩 |
| 3 | `421565e` | 2 | sample-api 라우터와 설명 품질 3등급 |
| 4 | `096630c` | 3 | 응답 계약 Pydantic 모델과 fixture |
| 5 | `b9f31b0` | 3.5 | 백엔드 OpenAPI → 프론트 타입 생성 |
| 6 | `dc662b5` | 4 | Port 격리 (범위 축소) |
| 7 | `4cbc081` | 4.5 | 배포 대비 설정과 문서 정비 |
| 8 | `bd59c27` | 5 | 디자인 토큰 (5.1 결정사항 포함) |
| 9 | `be9c725` | 6-1 | GaugeRing |
| 10 | `91172f3` | 4.6 | 크로스 플랫폼 + 폐쇄망 패키지 저장소 |
| 11 | `cf12309` | 4.7 | uv TLS 설정 + Dockerfile |
| 12 | `0fa40ef` | 4.7a | uv 설정 키 정정 + tasks.py 3.8 호환 보강 |
| 13 | `19608d7` | 4.7b | Python 인터프리터 가시화 + Windows 대비 |
| 14 | `5d7fb5d` | 4.7c | Python 3.8 하위호환 제거, 3.12 로 통일 |
| 15 | `2d6eb94` | (docs) | prompts.md §4 Phase 6 확장 + 4.7a~4.7c 반영 |
| 16 | `d9b9594` | 6-1a | GaugeRing 정렬 수정 |
| 17 | `4fd219c` | 6-2 | SummaryCards |
| 18 | `b3db009` | 6-6 | FailureTable |
| 19 | `5ff0284` | 4.7d [^label] | 컨테이너 네트워크 바인딩 |
| 20 | `27bdc43` | 6-4 | QuestionTypeChart |

Phase 5 이후 4.x 로 되돌아간 것은, 사내 Windows PC 에서 `make` 가 깨지고
폐쇄망 저장소·TLS 문제가 드러나 **화면 작업을 멈추고 빌드 경로를 먼저 고쳤기**
때문이다. 그 뒤 6-1a → 6-2 → 6-6 → 6-4 로 컴포넌트를 이어갔다.

[^label]: **`4.7c` 라벨이 두 번 지시됐다.** 14번(Python 3.12 통일)이 이미
    `4.7c` 를 쓰고 있는데 19번(컨테이너 네트워크 바인딩)에도 같은 번호가
    지시돼서, 19번을 **`4.7d`** 로 기록했다. 같은 라벨이 둘이면 "어디까지
    이식했는지" 추적이 안 된다.
    같은 일이 13번에서도 있었다 — `4.7b`(Python 3.8 되돌리기)로 지시됐으나
    이미 `4.7b`(인터프리터 가시화)가 있어 `4.7c` 로 밀렸다.

### 번호 규칙

**4.x 는 종료. 신규 인프라 작업은 Phase 9 이후 번호를 쓴다.**
`4.7d` 까지 소진했고 접미사가 더 붙으면 순서를 읽을 수 없다.

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

### Phase 4.7 — uv TLS 설정 + Dockerfile (수행 완료)

```
A. uv TLS 설정
   backend/sample-api pyproject.toml 에 [tool.uv] system-certs = false.
   주석으로 사내망 전환 방법 + [[tool.uv.index]] 예시(실제 URL 금지).
   doctor 에 TLS 설정 상태 진단 추가.

B. Dockerfile (루트 1개, 멀티스테이지 2타겟)
   sample-api 는 이미지를 만들지 않는다.
   베이스 이미지·저장소·인증서는 전부 ARG. non-root 실행.
   CMD 는 exec form (SIGTERM 직접 전달).
   frontend 는 .next/standalone 만 복사.
   .dockerignore 신설.

C. README 빌드/실행 예시, probe 경로, k8s 에 필요한 정보만.
```

**확인한 것 — uv 키 이름**

`uv 0.11.7` 에서 `[tool.uv]` 에 없는 키를 넣고 `uv lock` 을 돌리면
유효한 키 목록이 에러로 다 나온다. 그걸로 확인한 결과:

| | `native-tls` | `system-certs` |
|---|---|---|
| `[tool.uv]` toml 키 | 유효 | 유효 |
| 환경변수 | **무효** (`UV_NATIVE_TLS` 는 조용히 무시) | 유효 (`UV_SYSTEM_CERTS`) |

toml 은 둘 다 파싱되지만 **환경변수는 새 이름만 동작한다.**

> **Phase 4.7a 에서 정정.** 처음에는 toml 키를 `native-tls` 로 뒀는데,
> 파일은 구 키·환경변수는 신 키가 되어 짝이 맞지 않았다.
> **양쪽 다 `system-certs` / `UV_SYSTEM_CERTS` 로 통일했다.**
> `make doctor` 가 `native-tls` 키나 `UV_NATIVE_TLS` 를 발견하면 deprecated 로 표시한다.

**핵심 판단**

- **빈 문자열 ARG 를 ENV 로 내리지 않는다.** `ARG UV_SYSTEM_CERTS=""` 로 두면
  `ENV` 가 빈 값도 "설정됨" 으로 만들고, uv 가 boolish 파싱에 실패해 빌드가 죽는다.
  실제로 첫 빌드가 이걸로 실패했다. 기본값은 `false` 처럼 유효한 값이어야 한다.
- **`CMD` 는 반드시 exec form.** shell form 이면 `/bin/sh` 가 PID 1 이 되어
  SIGTERM 을 자식에게 전달하지 않고, 파드 종료마다 grace period 를 다 쓰고
  SIGKILL 당한다. 실측으로 두 이미지 모두 `docker stop` 에 **0초** 만에 응답한다.
- **`certs/` 디렉토리는 비어 있어도 유지한다.** `COPY certs/` 는 대상이 없으면
  빌드를 실패시킨다. 인증서가 필요 없는 환경에서도 빌드가 되어야 하므로
  `.gitkeep` 으로 디렉토리만 남긴다.
- **`BASE_PATH` 는 이미지에 굳는다.** 실측 확인: `--build-arg BASE_PATH=/swagger-eval`
  로 빌드한 이미지는 `/` 에서 404, `/swagger-eval` 에서 200 이다.
  이것이 #35(단일 이미지 다환경 승격)와 정면으로 충돌한다 → #45 로 기록.

### Phase 4.7a — uv 설정 키 정정 (수행 완료)

4.7 이 pyproject 는 `native-tls`(구), doctor 는 `UV_SYSTEM_CERTS`(신)를 보게 두어
**짝이 맞지 않았다.** 양쪽을 현행 키로 통일한다.

```
[tool.uv] native-tls = false  ->  system-certs = false
```

`doctor` 가 구/신을 구분해 보여준다.

| 상태 | 표시 |
|---|---|
| toml 이 `native-tls` | `!! deprecated 키 — system-certs 로 바꿀 것` |
| `UV_NATIVE_TLS` 만 설정 | `!! deprecated + 무시됨` |
| 구·신 둘 다 설정 | `deprecated` (호환 목적이므로 경고 수위를 낮춤) |

> 이때 tasks.py 에 Python 3.8 호환 가드도 함께 넣었으나 **4.7c 에서 되돌렸다.**
> 아래 4.7c 참고.

### Phase 4.7b — Python 인터프리터 가시화 (수행 완료)

`tasks.py` 는 프로젝트 의존성이 필요 없다. uv/npm 을 호출하는 런처일 뿐이라
venv 활성화를 요구하지 않는다. **다만 어떤 python 이 실행 중인지는 보여야 한다.**

```
- Makefile 상단에 PY ?= python3 변수 선언, 모든 타겟이 $(PY) 로 호출
- doctor 에 3행 추가: 실행 python 버전 / sys.executable / VIRTUAL_ENV
- README 에 한 줄: Windows 에서 python3 를 못 찾으면 make PY=python
```

- 4.6 에서 넣었던 `ifeq ($(OS),Windows_NT)` 플랫폼 분기를 제거하고
  `PY ?= python3` 하나로 단순화했다. **Windows 는 이제 `make PY=python` 이 필요하다.**
- Windows 의 `python3.exe` 는 Microsoft Store 실행 별칭일 수 있다. 파이썬이
  설치돼 있지 않으면 스토어 창만 뜨고 아무것도 실행되지 않는다.

### Phase 4.7c — Python 3.12 로 통일 (수행 완료)

4.7a 에서 넣은 3.8 호환 가드를 되돌린다. 로컬·사내 PC·k8s 가 모두 3.12 라
하위호환이 불필요하고, `typing.List` / `Optional` 같은 낡은 표기만 남긴다.

```
- 버전 가드 (3, 8) -> (3, 12). 메시지도 3.12 기준으로
- docstring 의 3.8 문법 금지 목록 삭제
- ruff.toml target-version = py312, UP006/UP045 ignore 해제 후 --fix
- read_uv_tls_setting 의 tomllib 폴백 제거 (3.12 에는 항상 있다)
- doctor 에 "최소 요구 3.12+" 행, 미달이면 경고
```

`List[str] -> list[str]`, `Optional[X] -> X | None` 24건이 자동 변환되며
`tasks.py` 가 `+85 / -133` 로 줄었다.

**핵심 판단**

- **버전 가드는 import 보다 앞에 있어야 한다.** `tomllib` 은 3.11+ 라,
  가드가 뒤에 있으면 오래된 python 에서 친절한 안내 대신
  `ModuleNotFoundError: No module named 'tomllib'` 가 먼저 튀어나온다.
  실제로 그렇게 터지는 것을 확인하고 순서를 바꿨다 (파일 상단 `# ruff: noqa: E402`).
- **`python3` 가 3.12 미만인 환경이 흔하다.** macOS 는 `/usr/bin/python3`
  (Xcode 번들, 3.9)가 Homebrew 보다 PATH 앞에 오는 경우가 많다.
  `PY ?=` 라 환경변수가 이기므로 `export PY=python3.12` 를 셸에 걸어두면 된다.

> 커밋 라벨이 `4.7b` 와 겹쳐 `4.7c` 로 달았다. 같은 라벨이 둘이면
> "어디까지 이식했는지" 추적이 안 된다.

### Phase 4.7d — 컨테이너 네트워크 바인딩 (수행 완료)

Dockerfile 과 문서만. 컨테이너가 바깥에서 닿을 수 있게 바인딩 주소를 명시한다.

```
backend
- CMD 를 uvicorn --host 0.0.0.0 --port 8000 으로 명시, exec form 유지
- HOST/PORT 를 ENV 로 두되 기본값 0.0.0.0 / 8000

frontend
- standalone server.js 는 HOSTNAME 을 본다. 버전에 따라 기본값이 달라진
  이력이 있으므로 ENV HOSTNAME=0.0.0.0 / PORT=3000 을 명시
- 로컬 개발(next dev)은 기존 동작 유지. Dockerfile 에서만 설정

로컬 개발은 그대로
- tasks.py 의 dev 는 127.0.0.1 유지. 이유를 주석으로

probe 경로
- basePath 를 쓰면 프론트 health 가 /{basePath}/api/health 로 바뀐다.
  백엔드는 영향 없음. README 에 차이 명시
```

**핵심 판단 — `sh -c exec`**

순수 exec form 은 변수를 치환하지 않는다. `["--host", "$HOST"]` 는 문자열
`"$HOST"` 그대로 넘어간다. 그러면 `ENV HOST` 를 선언해도 **무용지물**이고,
값을 하드코딩하면 `docker run -e PORT=9000` 이 조용히 무시된다.

그래서 `sh -c` 를 거치되 **`exec` 를 붙인다.**

```dockerfile
CMD ["sh", "-c", \
     "exec uvicorn app.main:app --host \"$HOST\" --port \"$PORT\" --timeout-graceful-shutdown 20"]
```

`exec` 가 sh 를 uvicorn 으로 대체하므로 uvicorn 이 PID 1 이 되어 SIGTERM 을
직접 받는다. `exec` 를 빼면 sh 가 PID 1 로 남아 신호가 막히고, 파드 종료마다
grace period 를 다 쓰고 SIGKILL 당한다.

실측으로 확인했다.

```
$ docker exec t-be cat /proc/1/cmdline
/app/.venv/bin/python /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 ...
```

**변수 이름이 backend/frontend 가 다르다**

backend 는 `HOST`, frontend 는 `HOSTNAME` 이다. 맞추고 싶지만
standalone `server.js` 가 보는 이름이 `HOSTNAME` 이라 바꿀 수 없다.

**로컬은 127.0.0.1 그대로**

컨테이너에서 `0.0.0.0` 이 안전한 것은 컨테이너 격리가 경계 역할을 하기
때문이다. 로컬에서 그대로 열면 같은 네트워크의 다른 기기에서 개발 서버에
접속할 수 있다 — 공용 와이파이에서는 평가 fixture 와 명세가 그대로 노출된다.

**probe 경로는 프론트만 basePath 를 탄다**

| `BASE_PATH` | frontend | backend |
|---|---|---|
| (비움) | `/api/health` | `/health`, `/ready` |
| `/swagger-eval` | `/swagger-eval/api/health` | `/health`, `/ready` (그대로) |

매니페스트에서 이걸 놓치면 **파드는 정상인데 probe 만 404 로 실패해
무한 재시작**한다. 원인이 로그에 안 보여서 찾기 어렵다.

**검증** (실제 빌드·기동)

| 확인 | 결과 |
|---|---|
| 기본 바인딩 | backend `0.0.0.0:8000`, frontend `0.0.0.0:3000` |
| 외부 접속 | `/health` `/ready` `/api/health` 전부 200 |
| `-e PORT=9100` | 로그 `0.0.0.0:9100`, `/health` 200 — ENV 가 실제로 반영된다 |
| PID 1 | sh 가 아니라 uvicorn |
| SIGTERM | `docker stop` 0~1초, exit 0 / 143 |
| basePath probe | `/api/health` 404, `/swagger-eval/api/health` 200 |
| 사내 URL | Dockerfile 에 공개 URL(pypi.org) 외 없음 |

> 커밋 라벨이 `4.7c`(Python 3.12 통일)와 겹쳐 `4.7d` 로 달았다.

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

| 순서 | 컴포넌트 | 메모 | 상태 |
|---|---|---|---|
| 6-1 | `GaugeRing` | 78% 하나만. 중복 표시 제거 | **완료** (+ 6-1a 정렬 수정) |
| 6-2 | `SummaryCards` | 요약 지표 5장. `previous` 있으면 델타 뱃지 | **완료** |
| 6-3 | `AppSummaryCard` + `QueryQualityTable` | 앱 메타 + 쿼리별 품질 표 | **폐기 (Phase 12)** — `QueryInfoCard` 로 대체 |
| 6-4 | `QuestionTypeChart` | 도넛 + 범례 + **유형별 인식률 막대** | **완료** |
| 6-5 | `RecommendationCards` | priority 뱃지, failShare 바, 중복 집계 각주 | **완료** |
| 6-6 | `FailureTable` | 표시 3건 + 전체 보기. score 표시. 정렬·필터는 후속 | **완료** |
| 6-7 | `ActionPanel` | 재생성 CTA 2개(현재 비활성). 근거 문장 1건 인용 | **완료** |
| 6-8 | `GradeScale` | 등급 구간 반원 게이지. 시안의 "평가 기준" 카드 | **완료** |

프롬프트 형식은 6-1 을 그대로 따른다. 공통으로 반드시 넣을 것:

- `Foo.tsx` + `Foo.module.css` 한 쌍. 옆 폴더를 참조하지 않는다
- 색·라벨은 `lib/enumTokens.ts` 경유. hex·문자열 직접 작성 금지
- 상태나 이벤트가 없으면 서버 컴포넌트로 (`'use client'` 금지)
- `app/dev/components/page.tsx` 에 경계값까지 렌더해서 확인 가능하게

---

#### Phase 6-1 — GaugeRing (완료)

인식률 게이지. 시안이 78% 를 세 곳에 중복 표시하던 것을 이것 하나로 대체한다 (§9-1 #1).

**실제 사용한 프롬프트**

```
Phase 6-1. components/eval/GaugeRing/ 만 만들고 멈춘다.

GaugeRing.tsx + GaugeRing.module.css
- 순수 SVG. stroke-dasharray / stroke-dashoffset. 라이브러리 금지
- props: value (0~100), grade: Grade, size?: number (기본 96), label?: string
- 색은 enumTokens 의 gradeColor(grade) 경유. hex 금지
- 등급 라벨은 gradeLabel[grade] 경유. 문자열 직접 작성 금지
- 트랙(배경 링)은 var(--border), 진행 링만 등급색
- 숫자는 .tabular 클래스. 소수 첫째자리까지 (78.0)
- 서버 컴포넌트로 동작해야 한다 ('use client' 금지)
- transition 은 CSS로. @media (prefers-reduced-motion: reduce) 에서 제거
- 접근성: role="img" + aria-label="Top-3 인식률 78.0%, 개선 필요"

경계값 처리:
- value 0 / 100 에서 링이 깨지지 않을 것
- 0~100 밖의 값은 clamp

app/dev/components/page.tsx 신설:
  4등급 × (0, 40, 78, 100) 조합을 격자로 렌더.
  size 변화(64/96/160)도 한 줄.
  app/dev/layout.tsx 의 production 차단이 이미 적용되는지 확인

다른 컴포넌트는 만들지 마.
```

**결과에서 배운 것** (다음 컴포넌트에도 적용)

- **0% 는 진행 링을 아예 렌더하지 않는다.** `stroke-linecap: round` 는 길이가
  0 이어도 점 하나를 남기는 브라우저가 있어, "0% 인데 뭔가 칠해진" 상태가 된다.
- **크기를 전부 `--gauge-size` 에서 파생시킨다.** 두께 10%, 숫자 24%, 등급 11.5%.
  `size` 하나만 바꾸면 인상이 유지된 채 스케일된다.
- **`role="img"` + `aria-label` 은 래퍼에 두고 SVG·내부 텍스트는 `aria-hidden`.**
  링·숫자·등급이 따로 읽히면 오히려 알아듣기 어렵다.
- **등급과 값은 독립이다.** "우수 등급인데 0%" 같은 조합도 그대로 렌더한다 —
  등급은 백엔드가 확정해 내려주므로 프론트가 재계산하지 않는다 (contract.md §3).
- `prefers-reduced-motion` 은 `globals.css` 에 전역 규칙이 있어도 모듈에 다시 쓴다.
  파일 쌍만 복사해도 동작해야 한다 (CLAUDE.md 규칙 4).

**작업 중 발견해 고친 것**

`label=""` 로 캡션을 끄면 `aria-label` 이 `" 64.0%, 심각"` 처럼 공백으로 시작했다.
스크린 리더가 읽는 문자열이라 조건부로 조립하도록 고쳤다.

```tsx
const summary = `${display}%, ${gradeLabel[grade]}`;
const ariaLabel = label ? `${label} ${summary}` : summary;
```

**검증** — 렌더 결과로 확인했다. size=96 에서 `circumference 271.4336`,
value 78 → `dashoffset 59.7154` 로 계산값과 일치. value 0 은 `<circle>` 1개(트랙만),
100 은 `dashoffset 0`. `-20 → 0` / `140 → 100` clamp. 프로덕션에서 `/dev/components` 404.

---

#### Phase 6-1a — GaugeRing 정렬 수정 (완료)

**실제 사용한 프롬프트**

```
6-1a(게이지 정렬) 작업 시작해주세요.
```

**무엇이 어긋나 있었나**

브라우저 없이 CSS 기하를 계산해서 두 가지를 찾았다.

| | 원인 | 오차 |
|---|---|---|
| 세로 | `.center` 가 flex column 으로 **[숫자, 등급]을 묶음째** 가운데 정렬 | 숫자가 지름의 **7.9%** 만큼 위로 (size 64/96/160 에서 5.1 / 7.6 / 12.6px) |
| 가로 | `%` 까지 포함해 가운데 정렬 | 숫자만의 중심이 `%` 폭의 절반만큼 왼쪽 (size 96 에서 약 4.3px) |

게이지에서 눈이 먼저 가는 것은 숫자다. 그 숫자가 링 중심에 없었다.

**고친 방식 — 정렬을 내용이 아니라 기하로 정한다**

```css
/* 숫자: 링의 기하학적 중심에 고정.
   0.31ch 은 '%'(0.62em, 모노라 advance 가 정확히 0.62ch) 폭의 절반. */
.value {
  position: absolute;
  left: 50%;  top: 50%;
  transform: translate(calc(-50% + 0.31ch), -50%);
}

/* 등급: 중심에서 고정 거리만큼 아래. 문서 흐름에서 빠져 있어
   라벨이 "심각"이든 "개선 필요"든 숫자를 밀지 않는다. */
.grade {
  position: absolute;
  left: 50%;  top: calc(50% + var(--gauge-size) * 0.155);
  transform: translateX(-50%);
}
```

`.center` 는 좌표 기준(`position: absolute; inset: 0`)만 제공하고 정렬에서 손을 뗀다.

**왜 이렇게 하나**: 묶음 정렬은 *내용 길이*에 따라 결과가 달라진다. 등급 라벨이
한 글자만 길어져도 숫자가 움직인다. 절대 배치는 내용과 무관하게 항상 같은 자리다.
브라우저로 눈으로 볼 수 없을 때도 계산으로 검증할 수 있다는 점이 더 중요하다.

**함께 고친 것**

- 확인 페이지의 크기 비교 행을 `align-items: flex-end` → `center`.
  캡션 글자 크기가 `size` 에 비례해 달라져서, 아래를 맞추면 링이 서로 어긋났다.
- 확인 페이지에 **십자선 오버레이**를 추가했다. `label=""` 로 캡션을 끄면
  게이지 루트 높이가 곧 링 높이이므로, 상자의 50% 선이 링 정중앙과 일치한다.
  숫자가 그 위에 놓이는지 눈으로 볼 수 있다.

**검증** — size 64/96/120/160 에서 숫자 중심 오차 **0.00px**.
숫자 아래끝과 등급 위끝 간격 1.5~3.7px, 등급 아래끝과 링 안쪽 사이 여유 10~25px,
등급 텍스트 폭이 그 높이의 링 내부 폭보다 좁음(넘치지 않음).
빌드 산출물 CSS 에 규칙이 그대로 들어간 것까지 확인.

> **브라우저로 눈으로 확인하지는 못했다.** 기하 계산과 빌드 CSS 검사로만 검증했다.
> 남은 것은 폰트 메트릭에서 오는 광학적 차이다 — 숫자 글리프의 시각적 중심은
> 라인 박스 중심보다 약간 위에 있어(디센더가 없어서) 1~2px 높아 보일 수 있다.
> 폰트가 확정된 뒤(`open-questions` #12) 눈으로 보고 필요하면 미세 조정한다.

#### Phase 6-2 — SummaryCards (완료)

요약 지표 카드 5장. 시안은 6장이었으나 이모지 "평가 상태" 카드를 뺐다 —
등급은 `GaugeRing` 이 이미 표현한다 (contract.md §5, §9-1 #2).

**실제 사용한 프롬프트**

```
Phase 6-2. components/eval/SummaryCards/ 만 만들고 멈춘다.

SummaryCards.tsx + SummaryCards.module.css
props: summary: Summary, previous?: Previous | null

카드 5장 (시안의 6장에서 이모지 "평가 상태" 카드 제거 — contract.md §5.
등급은 GaugeRing 이 이미 표현하므로 중복):
  1 총 질문 수      totalQuestions   단위 "개"   --sky
  2 Top-1 정확도    top1Accuracy     단위 "%"    --violet
  3 Top-3 인식률    top3Accuracy     단위 "%"    --green
  4 Top-1 실패      top1FailCount    단위 "건"   --red
  5 Top-3 실패      top3FailCount    단위 "건"   --amber

## 스타일 (시안 기준)
- 좌측에 3px 세로 악센트 바
- 카드 배경은 해당 색 opacity 0.09, 테두리는 같은 색 opacity 0.55
- 숫자는 .tabular, 큰 글씨. 단위는 작게 --text-mute
- 라벨은 --text-dim 소형
- 색은 CSS 변수 사용. hex 금지

## 델타 뱃지 (Top-3 인식률 카드에만)
- previous 가 없으면 뱃지 자체를 렌더하지 않는다 (빈 자리도 남기지 말 것)
- 형식: "▲ +14.0p" / "▼ -3.2p" / "— 0.0p"
- 단위는 반드시 "p" (퍼센트포인트). "%" 아님.
  64% -> 78% 는 14 퍼센트포인트 상승이지 14% 상승이 아니다
- 상승 --green / 하락 --red / 동일 --text-mute
- 계산은 순수 함수로 분리(테스트 가능하게):
    formatDelta(current: number, previous: number): { text, direction }
- aria-label: "이전 평가 A311 대비 14.0 퍼센트포인트 상승"

## 기타
- 서버 컴포넌트 ('use client' 금지)
- 반응형: 기본 5열, 1024 이하 3열, 768 이하 2열
- 숫자 포맷은 계약 그대로. 임의 반올림 금지
  (top1Accuracy 61.0 은 "61.0" 으로, totalQuestions 100 은 "100" 으로)

app/dev/components/page.tsx 에 섹션 추가:
- fixture(eval_A492.json) 실제 값으로 렌더한 기본 예시
- previous 있음 / 없음 / 하락(previous 가 더 높음) 3가지
- 극단값: 전부 0, 전부 100, totalQuestions 가 4자리(1234)일 때 레이아웃

다른 컴포넌트는 만들지 마.
```

**결과에서 배운 것**

- **원색을 파일 곳곳에서 부르지 않는다.** `--accent` 하나만 카드별로 바꾸고
  배경·테두리·악센트 바가 전부 거기서 파생된다. 원색 매핑은 module.css 맨 아래
  `accent*` 클래스 다섯 줄에만 있다.
- **투명도는 `color-mix` 로 만든다.** 토큰이 hex 라 알파를 직접 붙일 수 없다.
  미지원 브라우저를 위해 불투명 폴백을 **앞줄에** 선언한다 — 지원하지 않으면
  뒷줄을 통째로 무시하므로 색만 빠지고 레이아웃은 살아 있다 (open-questions #48).
- **뱃지가 없으면 자리도 없다.** `previous` 가 null 일 때 빈 뱃지를 두면
  카드 높이가 다른 세트와 어긋난다. 조건부로 노드 자체를 만들지 않는다.
- **`0.05` 미만 차이는 같은 값으로 본다.** 표시가 소수 첫째자리까지인데
  그러지 않으면 `-0.0001` 이 `▼ -0.0p` 로 나온다.

**퍼센트포인트(p) vs 퍼센트(%)**

델타 단위는 반드시 `p` 다. 64% → 78% 는 **14 퍼센트포인트** 상승이지
14% 상승이 아니다 (14% 상승이면 64 × 1.14 = 72.96 이 된다).
`%` 로 적으면 개선 폭을 잘못 읽게 되고, 이 제품의 핵심 지표가 바로 그 값이다.

**검증** — 렌더 결과로 확인했다. 7개 세트 중 델타 뱃지는 6개
(`previous={null}` 세트에는 없음). 표시/aria 쌍이 전부 일치:

```
▲ +14.0p   이전 평가 A311 대비 14.0 퍼센트포인트 상승
▼ -7.0p    이전 평가 A311 대비 7.0 퍼센트포인트 하락
— 0.0p     이전 평가 A311 대비 0.0 퍼센트포인트 변화 없음
```

값 표기도 계약 그대로다: `100 개` / `61.0 %` / `78.0 %` / `39 건` / `22 건`.

> **타입 이름**: 프롬프트의 `Summary` / `Previous` 는 실제로
> `EvaluationSummary` / `PreviousEvaluation` 이다 (`lib/types.ts`).
> 계약 스키마 이름을 그대로 재노출한 것이라 그쪽을 썼다.

#### Phase 6-3 — AppSummaryCard + QueryQualityTable (완료 → **Phase 12 에서 폐기**)

> **이 절의 산출물은 지금 저장소에 없다.** Phase 12 에서 평가 단위가 앱에서
> 쿼리 1개로 바뀌면서(`open-questions.md` #1 재확정) 두 컴포넌트의 근거가
> 사라졌다 — 앱 메타(`AppSummaryCard`)와 쿼리 목록 표(`QueryQualityTable`)는
> 계약에 대응 필드가 없다. 대상 쿼리의 설명 품질은 `QueryInfoCard` 가 보여준다.
> 아래 내용은 **당시 판단의 기록**으로 남긴다.

**기존 `TargetApiCard`(단일 엔드포인트 카드) 설계는 폐기했다.** 평가 단위가
쿼리 하나가 아니라 DAC 앱 하나로 바뀌면서(contract.md §0, open-questions #1)
"대상 엔드포인트 하나를 보여주는 카드" 는 성립하지 않는다. 두 컴포넌트로 나눴다.

**AppSummaryCard — 앱 메타 (낮은 높이)**

- appName / appId / specVersion 뱃지 / "쿼리 11개" / owner
- **수치를 넣지 않는다.** 점수는 GaugeRing 과 SummaryCards 의 몫이다.
  여기에 78% 를 또 넣으면 시안이 지적받은 중복 표시가 된다.

**QueryQualityTable — 이 화면의 실질 산출물**

- 컬럼: 선택 / 쿼리 / 설명 품질 / 문항 수 / Top-3 인식률 / 재생성 필요
- **정렬: 재생성 필요가 위, 그 안에서 인식률 오름차순.** 손봐야 할 것이 먼저.
- **설명 품질은 표시용 요약이다.** `descriptionLength`·`hasParamDescription` 으로
  FULL/SPARSE/MISSING 을 붙이지만, 진짜 판단은 백엔드의 `needsRegeneration` 이다
  (`lib/descriptionQuality.ts`, open-questions #53). 이 값으로 등급이나 재생성
  여부를 재계산하지 않는다.
- **인식률 막대 색은 백엔드가 확정한 `grade` 를 따른다.** 프론트가 인식률로
  등급을 다시 계산하지 않는다 (contract.md §3).
- **method 뱃지는 `hasMultipleMethods` 가 참일 때만.** 전부 GET 이면 뱃지가
  정보를 주지 못하고 사라진다 (open-questions #50).

**설명 품질 색은 상태색과 경쟁시키지 않는다**

인식률의 좋고 나쁨은 grade 막대가, 재생성 여부는 amber pill 이 이미 말한다.
설명 품질에 또 빨강/노랑을 쓰면 한 행에서 세 곳이 같은 신호를 두고 다툰다.
그래서 밝기만 나눈다 — 충실할수록 밝고(`--text`), 없을수록 흐리게(`--text-mute`).

**서버 컴포넌트를 유지했다**

체크박스는 아직 동작하지 않아(disabled) 클라이언트 상태가 필요 없다.
`defaultChecked={needsRegeneration}` 로 기본 선택만 표시하고, 자동 생성 서비스가
연동되면 그때 `'use client'` 로 올린다. 지금 올리면 동작할 대상이 없다.

**검증** (렌더 결과)

```
첫 표 정렬 (재생성 필요가 위 · 인식률 오름차순):
  ★재생성   20.0%  chamber-sensor-trend
  ★재생성   42.9%  operator-shift
  ★재생성   44.4%  step-cycle-time
           75.0%  alarm-history
           ...
          100.0%  wafer-yield-daily
```

- AppSummaryCard 에 수치 문자 0건 (앱명·버전·쿼리 수·담당만)
- 설명 품질 3종(충실/부족/없음), 재생성 pill, 체크박스 disabled + title
- "선택 N건" = 재생성 필요 개수 (3 / 0 / 4)
- 전부 GET 인 표에서 method 뱃지 사라짐
- tsc / eslint / build 통과, 컴포넌트 hex 0건, make test 97개 통과

#### Phase 6-4 — QuestionTypeChart (완료)

문항 유형 분포(도넛) + 유형별 인식률(막대)을 한 카드에.
시안에는 분포만 있었다. **유형별 인식률이 이 대시보드에서 가장 중요한 정보다**
— "한영 혼합 10%" 로는 할 게 없지만 "한영 혼합에서 40%" 면 무엇을 고칠지가
정해진다 (contract.md §5).

**프롬프트는 지시서 그대로다.** 여기서는 결정 사항만 남긴다.

**핵심 결정**

- **각도는 `ratio` 가 아니라 `count` 로 계산한다.** ratio 는 백엔드에서
  반올림돼 내려오므로 합이 정확히 100 이 아닐 수 있다. 그대로 각도로 바꾸면
  마지막 조각이 덜 닫히거나 첫 조각을 덮는다.

  ```
  ratio 합 100.2 → 각도 합 360.72°   (원이 안 닫힌다)
  count 누적     → 마지막 끝각 항상 정확히 360°
  ```

  조각마다 각도를 구해 더하면 오차가 쌓인다. **누적 개수를 전체로 나눠**
  각 조각의 시작·끝을 만들면 마지막 끝각이 `total/total × 360 = 360` 이다.

- **조각이 하나면 간격을 두지 않는다.** 100% 인데 원이 안 닫혀 있으면
  데이터가 잘못된 것처럼 보인다.

- **`stroke-linecap: butt`.** round 로 두면 조각 끝이 서로를 덮어 간격이
  사라지고 각도도 실제보다 커 보인다. GaugeRing 과 반대 선택이다 —
  거기는 조각이 하나뿐이라 round 가 맞았다.

- **막대에 등급색을 쓰지 않는다.** `questionTypes` 에는 `grade` 필드가 없다.
  프론트가 인식률로 등급을 재계산하면 백엔드가 확정하는 값과 갈릴 수 있다
  (contract.md §3). 대신 **전체 인식률 기준선**을 그어 평균 아래 유형이
  왼쪽에 모이게 했다 — 등급 계산 없이 같은 효과를 낸다.

- **막대는 낮은 순.** 개선 대상이 먼저 보여야 한다.

- **범례 라벨은 응답의 `label` 이 아니라 `questionTypeLabel` 을 쓴다.**
  실패 목록에는 `questionType` enum 만 오고 label 이 없다. 두 곳이 다른 출처를
  쓰면 같은 유형이 화면마다 다르게 표기될 수 있다.

- **기준선 정렬은 결정론적으로.** 라벨·수치 열을 `max-content` 로 두면 폭을
  CSS 에서 알 수 없어 오버레이를 맞출 수 없고, 그리드 행 span 은 암시적 행에서
  `-1` 이 어디를 가리키는지 불확실하다. 양쪽 열 폭을 변수로 고정하고
  오버레이가 같은 계산식을 쓰게 했다.

**검증**

각도 계산을 따로 돌려 확인했다.

| 입력 | 마지막 끝각 | 조각 연속 |
|---|---|---|
| fixture 7종 (합 100) | 360 | OK |
| 단일 100% | 360 | OK |
| count 0 섞임 | 360 | OK (보이는 조각 4/7) |
| 2개뿐 | 360 | OK |
| 전부 0 | 0 | OK (조각 없음) |
| 3등분 · 7등분 (나누어떨어지지 않음) | 360 | OK |

렌더 결과도 확인했다.

```
시작각   0.75°  호  77.70°       ← 첫 조각 (간격 1.5°의 절반만큼 밀려서 시작)
...
시작각 324.75°  호  34.50°  끝 359.25°
호 합 349.50° + 간격 7 × 1.5° = 360.00°
```

- 막대 정렬 `40% → 72.7% → 75% → 78.6% → 81.8% → 83.3% → 95.5%` (낮은 순)
- 기준선 `left: 78%`, 라벨 `전체 78.0%`
- 도넛 중앙 총계 `100`, count 0 케이스는 `57` (22+14+11+10)
- 범례 시맨틱 table (`scope="col"` / `scope="row"`)
- 도넛·막대 각각 `role="img"` + 요약 aria-label

#### Phase 6-5 — RecommendationCards (완료)

권장 조치 카드. 시안의 "개선 추천" 은 "권장 조치" 로 바꿨다 (§9-2).

**프롬프트는 지시서 그대로다.** 여기서는 결정 사항만 남긴다.

**핵심 결정**

- **합계를 계산해 보여주지 않는다.** 시안의 "실패 원인 중 62%" 는 근거 없는
  임의 합산이었다 (contract.md §5 알려진 오류). 대신 각 값이 왜 100 을 넘을 수
  있는지만 **상시** 각주로 밝힌다. fixture 합은 113.7% 다 —
  한 실패에 원인이 둘 이상일 수 있어 중복 집계되기 때문이다 (계약 §2).
- **하단부를 `margin-top: auto` 로 바닥에 붙인다.** 설명 길이가 달라도 카드끼리
  막대 높이가 맞는다. 어긋나면 비중을 눈으로 비교할 수 없다. 그리드 항목이
  기본으로 늘어나므로(stretch) 한 줄 안의 카드 높이가 같아진다.
- **설명은 3줄에서 자른다.** 카드 높이가 설명 길이에 끌려다니면 위 정렬이 깨진다.
- **빈 배열이면 섹션 제목까지 렌더하지 않는다.** 조치가 없는데 "권장 조치" 라는
  빈 제목만 남으면 무언가 빠진 것처럼 보인다.
- **순번은 2자리로 맞춘다.** "1" 과 "10" 이 섞이면 좌측 정렬이 흔들린다.
- **막대는 0~100 으로 clamp.** 계약상 범위 안이지만 넘치면 카드를 뚫는다.
- `priorityLabel` 은 "우선순위 높음" 처럼 명사를 붙였다. "높음" 만으로는 무엇의
  높낮이인지 모호하다 — 인식률인지 비중인지 우선순위인지.

**검증** (렌더 결과)

| 확인 | 결과 |
|---|---|
| 순번 | `01` `02` `03` `04` `05` (zero-pad) |
| 우선순위 pill | 높음·중간·낮음 3종 모두 |
| failShare | `0.0%` `4.2%` `8.3%` `12.5%` `31.8%` `36.4%` `45.5%` `100.0%` |
| 막대 폭 | 값과 1:1 일치 (`0%` … `100%`) |
| 각주 | 렌더된 4개 묶음 전부에 표시 |
| 빈 배열 | 아무것도 렌더 안 됨 (호출 5회 중 4회만 출력) |
| 임의 합산 | 컴포넌트에 합산 계산도 문구도 없음 |

#### Phase 6-6 — FailureTable (완료)

실패 문항 표. 기본 3건만 보이고 나머지는 버튼으로 넘긴다.
정렬·필터·페이징은 후속 단계 (§9-5).

**프롬프트는 지시서 그대로다.** 컬럼 정의·색 매핑 위치·근접 판정·반응형 분기까지
전부 지정돼 있었으므로 여기서는 결정 사항만 남긴다.

**핵심 결정**

- **`NEAR_MISS_MAX_RANK = 5`.** topK 가 3 이므로 4~5 위는 한두 칸 차이로 놓친
  것이다. 설명을 조금만 보강해도 Top-3 안에 들어올 가능성이 높아, 6위 이하나
  순위 밖과는 **조치의 성격이 다르다.** 그래서 pill 을 red 가 아닌 amber 로
  나눠 "먼저 손댈 것" 을 눈에 띄게 한다.
  5 는 topK(3) + 2 다. 계약이 `meta.topK` 로 topK 를 바꿀 수 있게 되어 있으므로
  나중에는 이 값도 topK 에서 파생시키는 편이 낫다.
- **`failureCategory` 에는 색을 주지 않는다.** 실패의 *종류*를 나누는 범주일 뿐
  어느 원인이 더 심각하다는 뜻이 아니다. 색을 붙이면 "빨간 원인이 더 나쁜가?"
  하고 읽게 된다. 중립 뱃지(`--surface-2` + `--border`)로 둔다.
- ~~**method 색은 `lib/httpMethod.ts` 로 분리.**~~ (Phase 12 에서 파일 삭제 —
  DAC 쿼리가 전부 조회라 색이 정보를 주지 않는데 시선만 뺏는다. open-questions #50)
  메서드 뱃지는 실패 테이블·대상
  API 카드·검색 결과에 두루 나오는데, 판단이 흩어지면 화면마다 같은 GET 이
  다른 색으로 보인다. 계약의 `method` 가 자유 문자열이라(#27) **모르는 값은
  중립색으로 떨어뜨린다** — 화면이 깨지는 것보다 회색이 낫다.
- **버튼 문구는 실제 실패 건수 기준.** 시안의 "나머지 97건 보기" 는 오류였다.
  실패는 22건인데 97건이라고 적혀 있었다 (§9-1 #3).
- **카드형 전환 시 표 시맨틱을 지킨다.** `display: block` 으로 바꾸면 브라우저가
  표 역할을 잃는다. `role="table" / "row" / "cell" / "columnheader"` 를 명시해
  좁은 화면에서도 스크린 리더가 표로 읽게 했다. 각 셀은 `data-label` 로 자기
  컬럼명을 단다.
- **1280 이하에서 접는 것은 "추정 원인" 이다.** 가장 길고, `failureCategory` 가
  이미 같은 정보를 한 단어로 요약해 준다.

**검증** — 렌더 결과로 확인했다.

| 확인 | 결과 |
|---|---|
| Hit pill | `MISS` / `MISS (근접)` 분기 동작. `expectedRank` 4·5 만 근접 |
| expectedRank 표기 | `4위 (기대 API 위치)` / `7위` / `20위` / `기대 API: 순위 밖` |
| 전체 보기 버튼 | `실패 22건 전체 보기`, `disabled`, title 부착 |
| 하단 안내 | `3건 표시 중 · 19건 더 있음` — 전체와 같으면 안내 없음 |
| 점수 | `0.603` ~ `0.812` 소수 3자리 고정 |
| 시맨틱 | `<table>`/`<thead>`, `scope="col"` 18개, `data-label` 54개 |
| 빈 상태 | 실패 0건이면 표 대신 안내 |

#### Phase 6-7 — ActionPanel (완료)

시안 우하단의 "권장 액션". 서버 컴포넌트이고 `onClick` 이 없다.

**프롬프트는 지시서 그대로다.** 여기서는 결정 사항만 남긴다.

**핵심 결정**

- **failShare 를 더하는 코드가 없다.** 시안의 "실패 원인 중 62%" 는 카드의
  45/23/32% 와 맞지 않는 값이었다 (contract.md §5). failShare 는 중복 집계되므로
  합산 자체가 의미를 갖지 못한다. **한 건만 골라 그 값만 인용한다.**
- **고르는 순서: 우선순위 → failShare 큰 순 → order 작은 순.** 마지막 기준이
  없으면 동률일 때 화면이 매번 달라진다. `pickLeadingCause` 를 순수 함수로
  분리했고 원본 배열을 변형하지 않는다.
- **버튼은 둘 다 비활성.** 평가 엔진이 없다. `opacity 0.5` + `cursor: not-allowed`
  로 눌리지 않는다는 것이 눈에 보이게 했다 — 활성처럼 보이는 버튼을 눌렀는데
  아무 일도 안 일어나면 고장으로 읽힌다. `disabled` 와 `aria-disabled` 를 함께 준다.
- **확인 다이얼로그를 지금 만들지 않는다.** 만들면 `'use client'` 가 필요해지는데
  아직 동작할 대상이 없다. 문구만 준비해 두고 활성화 시점에 붙인다 (§9-3).
- **파괴적 동작 안내는 상시 표시.** 버튼이 활성화된 뒤에 알려주면 늦다.
- **primary 글자색은 `--bg`.** `--sky` 배경 위에서 `--text` 는 대비가 모자란다.

**한국어 조사를 계산해서 붙인다**

제목은 백엔드가 내려주므로 문장에 조사를 고정할 수 없다.

```
"보강" + 으로   (받침 ㅇ)
"추가" + 로     (받침 없음)
"정렬" + 로     (받침 ㄹ)
```

고정하면 둘 중 하나는 반드시 틀린다. 실제로 첫 구현에서 "동의어·업무 용어
추가**으로**", "유사 리소스 구분 강화**으로**" 가 나왔다.
받침이 없거나 ㄹ 이면 "로", 그 외에는 "으로" 로 고른다.
한글 음절이 아닌 글자로 끝나면 발음을 알 수 없어 "으로" 로 둔다.

**검증**

선택 로직과 조사 규칙을 따로 돌려 확인했다.

| 입력 | 선택 결과 |
|---|---|
| HIGH 45.5 / HIGH 36.4 / MEDIUM 31.8 | 설명 보강 (order 1, HIGH, 45.5%) |
| HIGH 없음, LOW 가 failShare 최대 | 유사 리소스 (order 3, **MEDIUM**, 31.8%) |
| failShare 동률(45.5) 2건 | 동의어 추가 (**order 2**) |
| 빈 배열 | null → 렌더 안 함 |

원본 배열 불변도 확인했다. 조사는 보강→으로 / 추가→로 / 강화→로 /
보완→으로 / 정렬→로 / 정리→로 / 통합→으로 전부 통과.

렌더 결과:

```
가장 큰 원인은 '설명(Description) 보강'으로, 실패의 45.5%가 여기 해당합니다.
가장 큰 원인은 '유사 리소스 구분 강화'로,   실패의 31.8%가 여기 해당합니다.
가장 큰 원인은 '동의어·업무 용어 추가'로,   실패의 45.5%가 여기 해당합니다.
```

- 버튼 2개 모두 `disabled` + `aria-disabled` + title, primary 에만 경고 아이콘
- 빈 배열이면 카드 자체가 안 나온다 (호출 5회 중 4회만 렌더)

> **수치는 `45.5%` 로 쓴다.** 지시서 예시는 `45%` 였지만 fixture 값은 45.5 이고,
> 바로 옆 `RecommendationCards` 가 45.5% 를 보여준다. 한 화면에서 같은 값이
> 다르게 나오면 그게 이 프로젝트가 계속 잡아온 종류의 결함이다.

#### Phase 6-8 — GradeScale (완료)

시안의 "평가 기준" 카드에 있던 반원 게이지.

**`GaugeRing` 과 역할이 다르다.**

| | 답하는 질문 | 표시 |
|---|---|---|
| `GaugeRing` | 얼마인가 | `78.0%` |
| `GradeScale` | 어느 구간인가 | `개선 필요 / 70 ~ 85%` |

그래서 **GradeScale 안에는 큰 수치를 넣지 않는다.** 78% 가 화면에서 반복되는
것을 막는 것이 이 분리의 목적이다 (contract.md §5, §9-1 #1).
둘을 나란히 써도 수치는 한 번만 나온다.

**프롬프트는 지시서 그대로다.** 여기서는 결정 사항만 남긴다.

**핵심 결정**

- **구간 정의를 `lib/gradeBands.ts` 로 분리.** `contract.md` §3 이 진실이고,
  기준이 바뀌면 `GRADE_BANDS` 배열만 고치면 호·범례·aria 라벨이 함께 따라온다.
  컴포넌트에 숫자를 적지 않는다.
- **각도 변환도 `lib` 에 뒀다.** 프론트에는 테스트 러너가 없다(새 npm 패키지
  금지). `.tsx` 안에 있으면 JSX 때문에 따로 돌려볼 방법이 없지만, 타입만
  걷어내면 실행되는 `.ts` 에 두면 `node --experimental-strip-types` 로
  **실제 코드를 그대로** 검증할 수 있다.
- **`bandOf(grade)` 는 등급으로 찾는다. 값으로 추론하지 않는다.** 등급은
  백엔드가 확정해 내려주므로, 프론트가 value 에서 구간을 유추하면 백엔드 기준이
  바뀌었을 때 화면만 다른 말을 하게 된다. 어긋난 조합(값 40%, 등급 GOOD)도
  그대로 렌더한다 — 바늘은 값이 가리키는 곳에, 강조는 등급이 말하는 구간에.
- **바늘은 `--text`.** 구간색과 같은 계열이면 어느 구간을 가리키는지 안 읽힌다.
- **호는 `stroke-linecap: butt`.** round 면 구간 끝이 서로를 덮어 간격이
  사라지고 경계 위치도 밀려 보인다 (QuestionTypeChart 와 같은 이유).
- **범례는 현재 등급 행만 강조한다.** 다 강조하면 아무것도 안 보인다.

**검증**

각도·좌표 변환을 실제 코드로 실행해 확인했다
(`node --experimental-strip-types`).

```
valueToAngle   0%→0°   25%→45°   50%→90°   70%→126°
               78%→140.4°   85%→153°   95%→171°   100%→180°
clamp          -20→0°   140→180°
polarPoint     0°→(6.75, 90) 9시   90°→(90, 6.75) 위   180°→(173.25, 90) 3시
               모든 각도에서 y ≤ cy — 반원을 벗어나지 않는다
GRADE_BANDS    0~70 / 70~85 / 85~95 / 95~100, 빈틈·겹침 없음
bandArcPath    간격(1.5°)보다 좁은 구간은 빈 문자열 → 그리지 않는다
```

렌더 결과의 바늘 각도도 값과 정확히 일치했다.

| value | 0 | 69.9 | 70 | 78 | 85 | 94.9 | 95 | 100 |
|---|---|---|---|---|---|---|---|---|
| 각도 | 0.0° | 125.8° | 126.0° | 140.4° | 153.0° | 170.8° | 171.0° | 180.0° |

- 범례 범위 `0 ~ 70%` / `70 ~ 85%` / `85 ~ 95%` / `95 ~ 100%`
- readout 에는 등급명과 범위만 (`개선 필요` + `70 ~ 85%`) — 큰 수치 없음
- `aria-label` = `Top-3 인식률 78.0%, 개선 필요 구간 (70 ~ 85%)`

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
| Python TLS | `UV_SYSTEM_CERTS=true` 또는 `[tool.uv] system-certs` | 구 `native-tls` / `UV_NATIVE_TLS` 는 deprecated. 환경변수 쪽 구 이름은 조용히 무시된다 |
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
