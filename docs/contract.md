# 응답 계약 (Contract)

> **이 문서가 단일 진실 공급원이다.**
> 시안(`mockup.svg`)과 충돌하면 이 문서가 이긴다.
> 사내 요구사항이 바뀌면 **여기를 먼저 고치고** 나서 코드를 고친다.

구현 위치: `backend/app/schemas/evaluation.py` (Pydantic v2)
프론트 타입: `frontend/src/lib/api-types.ts` (`openapi-typescript` 생성물, 수기 편집 금지)

---

## 0. 도메인 — DAC 과 쿼리

사내 Oracle 에 직접 접근할 수 있는 사람은 소수다. 그래서 **DAC** 이라는
조회 전용 중계 서비스를 통한다. 사용자는 DAC 에 **앱**(예: `flops`,
`mf-worker`)을 만들고 그 안에 SELECT **쿼리**를 등록하며, DAC 이 앱마다
Swagger 를 생성해 준다.

```
DAC 앱 1개  =  Swagger 1개
엔드포인트 1개  =  등록된 SELECT 쿼리 1개
```

**평가 엔진은 이 시스템 밖에 있다.** 담당자 툴이 DAC Swagger 로부터 질문 100개를
생성하고 RAG 검색 후 Top-1 / Top-3 hit 를 계산한다. 이 프로젝트는 그 결과를 받아
평가 결과서를 보여주고, 부실한 쿼리를 Swagger 자동 생성 에이전트로 넘긴다.
따라서 **백엔드의 1차 역할은 외부 평가툴 출력을 이 계약으로 변환하는 어댑터**다.
평가툴의 지표나 컬럼이 바뀌어도 계약과 화면은 유지되어야 한다.

**이 프로젝트의 목적**은 각 쿼리의 설명(summary / description / 파라미터 설명)이
AI 검색에 충분한지 평가하고, 부실한 쿼리를 **별도 팀의 Swagger 자동 생성
서비스로 넘기는 것**이다. 설명을 이 서비스가 직접 고치지는 않는다.

### 용어

화면과 문서의 기본 용어는 **"쿼리"** 다. "API" 나 "엔드포인트" 로 쓰지 않는다 —
사용자는 REST 엔드포인트가 아니라 자기가 등록한 SELECT 쿼리로 인식한다.
JSON 필드 이름은 HTTP 규약을 따르므로 `method` / `path` 를 그대로 쓰지만,
라벨은 "기대 쿼리", "검색된 쿼리" 처럼 적는다.

**평가 단위는 앱 하나다** (docs/open-questions.md #1 확정).
쿼리 하나만 따로 평가하지 않는다.

---

## 1. 엔드포인트

| 메서드 | 경로 | 설명 | 우선순위 |
|---|---|---|---|
| `GET` | `/api/v1/evaluations/{trace_id}` | 대시보드 전체 데이터 | **P0** |
| `POST` | `/api/v1/evaluations` | 평가 실행 (비동기, `job_id` 반환) | P1 |
| `GET` | `/api/v1/evaluations/{trace_id}/status` | 진행 상태 | P1 |
| `GET` | `/api/v1/evaluations` | 이력 목록 | P2 |
| `POST` | `/api/v1/specs/{app_id}/regenerate-request` | 부실한 쿼리를 자동 생성 서비스로 넘기는 요청 | P2 |

**대시보드는 P0 하나로 전부 그려진다.** 나머지는 나중에 붙여도 화면이 흔들리지 않는다.

---

## 2. GET /api/v1/evaluations/{trace_id}

```jsonc
{
  "traceId": "A492",
  "evaluatedAt": "2026-07-22T11:38:00+09:00",

  "target": {
    "appId": "mf-worker",
    "appName": "MF Worker 조회",
    "specVersion": "v3",
    "queryCount": 11,
    "owner": "데이터플랫폼팀"
  },

  "meta": {
    "embeddingModel": "bge-m3",
    "searchMode": "HYBRID",
    "topK": 3,
    "questionSource": "LLM_GENERATED_HUMAN_REVIEWED",
    "durationMs": 48210,
    "rawSource": {                    // 외부 평가툴 원본. optional
      "toolVersion": "rageval-2.4.0",
      "promptVersion": "qgen-2026Q2",
      "generatedAt": "2026-07-22T11:20:00+09:00"
    }
  },

  "summary": {
    "totalQuestions": 100,
    "top1Accuracy": 61.0,
    "top3Accuracy": 78.0,
    "top1FailCount": 39,
    "top3FailCount": 22,
    "top1Grade": "CRITICAL",          // top1Accuracy 로 산출
    "top3Grade": "NEEDS_IMPROVEMENT"  // top3Accuracy 로 산출. 임계값이 다를 수 있다(#54)
  },

  // 쿼리별 설명 품질과 인식률. 앱에 등록된 쿼리 전부.
  // **이 화면의 실질 산출물이다** — 어느 쿼리를 고쳐야 하는지가 여기서 정해지고,
  // needsRegeneration 인 것이 그대로 재생성 요청 대상이 된다.
  "queries": [
    {
      "path": "/products/{id}/restock-schedule",
      "method": "GET",
      "summary": null,              // 없으면 null
      "descriptionLength": 0,       // 0 이면 설명 없음
      "hasParamDescription": false,
      "questionCount": 8,           // 이 쿼리를 기대 결과로 삼은 문항 수
      "top3Accuracy": 37.5,
      "grade": "CRITICAL",
      "needsRegeneration": true     // 백엔드가 판단한다
    }
  ],

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

  // 평가 문항 전체(성공 포함). 건수 = totalQuestions.
  // 정렬: TOP3 실패 -> TOP1_ONLY 실패 -> 성공, 그 안에서 no 오름차순.
  "questions": [
    {
      "no": 17,
      "question": "스텝 사이클타임 조회 query 있나요?",
      "questionType": "MIXED_LANG",
      "expected": { "method": "GET", "path": "/queries/step-cycle-time" },
      "top1": { "method": "GET", "path": "/queries/wafer-yield-daily", "score": 0.680 },
      "top3": [
        { "rank": 1, "method": "GET", "path": "/queries/wafer-yield-daily", "score": 0.680 },
        { "rank": 2, "method": "GET", "path": "/queries/lot-trace",        "score": 0.635 },
        { "rank": 3, "method": "GET", "path": "/queries/equipment-downtime","score": 0.590 }
      ],
      "top1Hit": false,
      "top3Hit": false,
      "failureScope": "TOP3",                    // NONE | TOP1_ONLY | TOP3
      "expectedRank": null,                      // Top-N 밖이면 null
      "failureCategory": "DESCRIPTION_MISSING",  // 성공이면 null
      "reason": "기대 쿼리에 설명이 전혀 없어 경로 토큰 외에 매칭 근거가 없음"
    },
    {
      "no": 3,
      "question": "랏 상태를 조회하는 쿼리는 무엇인가요?",
      "questionType": "DIRECT",
      "expected": { "method": "GET", "path": "/queries/lot-status" },
      "top1": { "method": "GET", "path": "/queries/lot-status", "score": 0.920 },
      "top3": [
        { "rank": 1, "method": "GET", "path": "/queries/lot-status", "score": 0.920 },
        { "rank": 2, "method": "GET", "path": "/queries/lot-trace",  "score": 0.710 },
        { "rank": 3, "method": "GET", "path": "/queries/inventory-wip","score": 0.640 }
      ],
      "top1Hit": true,
      "top3Hit": true,
      "failureScope": "NONE",         // 성공
      "expectedRank": 1,
      "failureCategory": null,        // 성공이면 null
      "reason": null
    }
  ],

  "previous": {
    "traceId": "A311",
    "evaluatedAt": "2026-07-15T09:12:00+09:00",
    "top3Accuracy": 64.0
  }
}
```

### 필드 규약

- 모든 비율(`ratio`, `*Accuracy`, `failShare`)은 **0~100 실수**. 0~1 소수 금지.
- `expectedRank` 는 기대 쿼리가 전체 검색 결과에서 몇 위였는지. **Top-N 밖이면 `null`**.
- `previous` 는 이전 평가가 없으면 `null`. 프론트는 델타 뱃지를 숨긴다.
- `recommendations[].failShare` 의 **합은 100을 넘을 수 있다** (한 실패에 원인이 복수).
  화면에 "원인 중복 집계" 각주 필수.
- 시각은 전부 ISO 8601 + 타임존.
- `target.queryCount` 는 `queries` 배열의 길이와 같다. 어긋나면 화면이 서로 다른
  말을 한다.
- `queries[].questionCount` 의 합은 `summary.totalQuestions` 와 같다.
- `queries[].top3Accuracy` 는 그 쿼리를 기대한 문항들만의 인식률이다. 전체
  인식률(`summary.top3Accuracy`)과 다르다.
- **`needsRegeneration` 은 백엔드가 판단한다.** 프론트가 인식률이나 설명 길이로
  다시 계산하지 않는다. 판정 기준은 `open-questions.md` #53 참고.

### 선택 필드 · 빈 배열이 왔을 때 (Phase 10)

외부 평가툴이 항상 모든 필드를 채워 주지는 않는다. **누가 그 부재를 처리하는지를
여기 적어 둔다** — 계약에 선택 필드를 추가할 때는 이 표에 한 줄을 함께 추가한다.
표에 없는 자리가 생기면 화면 어딘가가 빈 채로 남는다.

| 자리 | 없을 때 | 처리하는 곳 |
|---|---|---|
| `target.owner` | 담당 표기를 그리지 않음 | `AppInfoCard` |
| `meta.rawSource` | 헤더의 평가툴 출처 줄을 통째로 숨김 | `eval/[traceId]/page.tsx` |
| `previous` | 델타 뱃지를 숨김(자리를 남기지 않음) | `page.tsx`, `SummaryCards` |
| `queries[].summary` | "설명 없음" 으로 표기 | `QueryQualityTable` |
| `questions[].expectedRank` | "기대 쿼리: 순위 밖" | `FailureTable` |
| `questions[].failureCategory` | 원인 필터 칩에서 제외 | `FailureTable` |
| `questions[].reason` | 대시(—)로 "없음" 을 명시 | `FailureTable` |
| `queries` 가 빈 배열 | 빈 표 대신 "등록된 쿼리가 없습니다" 카드, 경로 접이식 자체를 생략 | `QueryQualityTable`, `AppInfoCard` |
| `questionTypes` 가 빈 배열 | 빈 도넛 대신 "문항 유형 정보가 없습니다" | `QuestionTypeChart` |
| `questionTypes[].count` 가 0 | 범례는 남기되 인식률은 대시(—), 막대에서는 제외 | `QuestionTypeChart` |
| `recommendations` 가 빈 배열 | 권장 조치·권장 액션 컬럼을 통째로 없애고 좌측이 전체 폭 | `page.tsx`, `RecommendationCards`, `ActionPanel` |
| `questions` 가 빈 배열 | "표시할 문항이 없습니다" | `FailureTable` |
| `top3` 가 3건 미만 | 있는 만큼만 그림(쿼리가 적은 앱에서 실제로 그렇다) | `FailureTable` |

필드가 **아예 빠진 경우와 `null` 인 경우를 모두 통과**시켜야 한다. 외부 툴은 보통
키 자체를 생략한다 (`backend/tests/test_adapter_contract.py`).

### questions — 문항 100개 전체

- **평가 대상은 실패만이 아니라 문항 전체다.** `questions` 의 길이는
  `summary.totalQuestions` 와 같고, 성공 문항도 들어온다.
- `failureScope` 로 실패 범위를 나눈다.
  - `NONE` — Top-1 부터 맞음 (성공). `failureCategory` 와 `reason` 이 `null`.
  - `TOP1_ONLY` — Top-1 은 틀렸으나 Top-3 안에는 있음.
  - `TOP3` — Top-3 밖 (완전 실패).
- 개수 정합: `top1FailCount = TOP1_ONLY + TOP3`, `top3FailCount = TOP3`.
- `top1` 은 1위 결과(순위 자명해 rank 없음). `top1` 은 `top3[0]` 과 같은 쿼리다.
- `top1Hit` / `top3Hit` 은 기대 쿼리가 각각 1위 / 상위 3위 안에 있었는지.
- **정렬: `TOP3` → `TOP1_ONLY` → `NONE`, 그 안에서 `no` 오름차순.** 손봐야 할 것이 위로.
- `questions[].expected` 는 "기대 쿼리" 다. 화면 라벨도 그렇게 적는다.

---

## 3. Enum (백엔드가 확정해서 내려준다)

```
grade            CRITICAL | NEEDS_IMPROVEMENT | FAIR | GOOD
priority         HIGH | MEDIUM | LOW
searchMode       BM25 | VECTOR | HYBRID
failureScope     NONE | TOP1_ONLY | TOP3
questionType     DIRECT | USER_NL | DOMAIN_TERM | PARAMETER
                 | ERROR_CASE | SHORT_KEYWORD | MIXED_LANG
failureCategory  SIMILAR_RESOURCE | DESCRIPTION_MISSING | DESCRIPTION_WEAK
                 | KEYWORD_MISMATCH | DOMAIN_TERM_MISSING | ERROR_CASE_MISSING
                 | PARAM_MISSING | METHOD_MISMATCH | OTHER
```

### failureCategory 라벨 (담당자 확정)

| enum | 라벨 | 비고 |
|---|---|---|
| `SIMILAR_RESOURCE` | 유사 API 혼동 | |
| `DESCRIPTION_MISSING` | 설명 누락 | |
| `DESCRIPTION_WEAK` | 설명 키워드 부족 | 신규 |
| `KEYWORD_MISMATCH` | 키워드 불일치 | 구 `SYNONYM_MISS` 대체 |
| `DOMAIN_TERM_MISSING` | 도메인 키워드 부족 | 신규 |
| `ERROR_CASE_MISSING` | 예외 상황 설명 부족 | 신규 |
| `PARAM_MISSING` | 파라미터 설명 누락 | |
| `METHOD_MISMATCH` | Method 불일치 | DAC 단일 메서드면 미사용. enum 유지 (#50) |
| `OTHER` | 기타 | |

### 등급 기준

`top1Grade` / `top3Grade` 각각 아래 표로 산출한다. **현재 두 지표의 임계값은
같지만 다를 수 있다** (open-questions #54) — 그래서 등급을 지표별로 따로 내려준다.
프론트의 `lib/gradeBands.ts` 도 이에 맞춰 지표별 구조로 나눈다(화면 수리 단계).

| grade | 인식률 | 라벨 | 색 토큰 |
|---|---|---|---|
| `CRITICAL` | < 70% | 심각 | `--red` |
| `NEEDS_IMPROVEMENT` | 70 ~ 85% | 개선 필요 | `--amber` |
| `FAIR` | 85 ~ 95% | 보통 | `--sky` |
| `GOOD` | ≥ 95% | 우수 | `--green` |

> 프론트에서 문자열 비교로 색을 정하지 않는다.
> `lib/enumTokens.ts` 에 enum → CSS 변수 매핑 테이블 하나만 둔다.

### questionType 라벨

| enum | 라벨 |
|---|---|
| `DIRECT` | 직접 질문 |
| `USER_NL` | 사용자 자연어 질문 |
| `DOMAIN_TERM` | 업무 용어 질문 |
| `PARAMETER` | 파라미터 기반 질문 |
| `ERROR_CASE` | 오류/에러 상황 질문 |
| `SHORT_KEYWORD` | 짧은 키워드 질문 |
| `MIXED_LANG` | 한영 혼합 질문 |

---

## 4. 그 외 엔드포인트

### POST /api/v1/evaluations (P1)

```jsonc
// 요청
{ "appId": "mf-worker", "questionCount": 100, "topK": 3, "searchMode": "HYBRID" }

// 응답 202
{ "jobId": "job_7f2a", "traceId": "A493", "statusUrl": "/api/v1/evaluations/A493/status" }
```

### GET /{trace_id}/status (P1)

```jsonc
{
  "traceId": "A493",
  "status": "RUNNING",              // QUEUED | RUNNING | SUCCEEDED | FAILED | CANCELLED
  "stage": "SEARCHING",             // GENERATING | SEARCHING | SCORING | ANALYZING
  "progress": { "current": 62, "total": 100 },
  "etaSeconds": 18,
  "startedAt": "2026-07-22T11:37:12+09:00",
  "error": null
}
```

> 평가가 수십 초 걸린다. **실행 중 화면이 실제로는 가장 자주 보이는 화면**이므로
> 이 엔드포인트를 P1로 둔다.

### POST /api/v1/specs/{app_id}/regenerate-request (P2)

부실한 쿼리를 **별도 팀의 Swagger 자동 생성 서비스로 넘기는 요청**이다.

**이 서비스가 설명을 직접 덮어쓰지 않는다.** 요청을 접수해 넘길 뿐이고,
실제 생성과 반영은 그쪽 팀의 절차를 따른다. 그래서 화면의 버튼도
"덮어쓰기" 가 아니라 "넘기기" 로 읽혀야 한다.

```jsonc
// 요청 — 화면에서 고른 쿼리 경로들
{ "queryPaths": ["/products/{id}/restock-schedule", "/orders/{id}/refund"] }

// 응답 202
{
  "requestId": "req_20260722_001",
  "submittedCount": 2,
  "status": "SUBMITTED"             // SUBMITTED | ACCEPTED | REJECTED
}
```

`queryPaths` 는 `queries[].path` 를 그대로 쓴다. 기본 선택값은
`needsRegeneration` 이 `true` 인 쿼리들이다.

> 받는 팀의 API 스펙이 아직 확정되지 않았다 (`open-questions.md` #52).
> 위 형태는 이쪽에서 필요한 최소치를 적어둔 것이며, 확정되면 여기를 먼저 고친다.

## 5. 시안 대비 변경점

### 추가

| 필드 | 이유 |
|---|---|
| `questionTypes[].top3Accuracy` | 시안엔 분포만 있음. **"한영 혼합 40%"** 가 나와야 액션이 나온다. 추가 가치 1위 |
| `previous` | 재생성 Before/After 델타. 이 제품의 핵심 가치인데 시안에 없음 |
| `results[].score` | 아깝게 놓친 건지 완전히 빗나간 건지 구분 |
| `meta` | 재현성 (모델·검색방식·소요시간·문항 출처) |
| `target.specVersion` | 재생성 전후 구분 |

### 제거 / 격하

| 시안 요소 | 조치 |
|---|---|
| 78%가 3곳 중복 표시 | 게이지 하나만 |
| 이모지 얼굴 "평가 상태" 카드 | 제거 (게이지와 중복) |
| 브라우저 크롬 | 제거 (목업 장식) |
| "평가 기준" 상세 블록 | `<details>` 접이식 |

### 알려진 오류 (그대로 옮기지 말 것)

- "실패 22건 중 3건 표시" ↔ "나머지 97건 보기" → **22건 기준으로 통일**
- "실패 원인 중 62%" ↔ 카드의 45/23/32% → **계약에서 산출한 값 사용**
- 평가 대상을 엔드포인트 1개로 그린 부분 → **앱 단위**로 바뀌었다 (§0)

---

## 6. 변경 이력

| 날짜 | 변경 | 사유 |
|---|---|---|
| 2026-07-22 | 최초 작성 | — |
| 2026-07-23 | 평가 단위를 앱으로 변경, `queries` 신설, 용어를 "쿼리"로 통일, 재생성을 요청 방식으로 변경 | 미정 #1 확정 (DAC 앱 단위) |
| 2026-07-24 | 등급을 top1Grade/top3Grade 로 분리, failures→questions(100문항 전체), failureScope 신설, failureCategory 확장, meta.rawSource 추가 | 담당자 확정 스펙 반영 |
| 2026-07-26 | 계약 자체는 그대로. "선택 필드·빈 배열" 절 신설 | Phase 10 안정화 — 부재를 누가 처리하는지 계약 옆에 적어 둔다 |
