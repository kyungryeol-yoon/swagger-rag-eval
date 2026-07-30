# 응답 계약 (Contract)

> **이 문서가 단일 진실 공급원이다.**
> 시안(`mockup.svg`)과 충돌하면 이 문서가 이긴다.
> 사내 요구사항이 바뀌면 **여기를 먼저 고치고** 나서 코드를 고친다.

구현 위치: `backend/app/schemas/evaluation.py` (Pydantic v2)
프론트 타입: `frontend/src/lib/api-types.ts` (`openapi-typescript` 생성물, 수기 편집 금지)

---

## 0. 도메인 — DAC 쿼리 1개를 평가한다

사내 Oracle 에 직접 접근할 수 있는 사람은 소수다. 그래서 **DAC** 이라는
조회 전용 중계 서비스를 통한다. 사용자는 DAC 에 **앱**을 만들고 그 안에
SELECT **쿼리**를 등록하며, DAC 이 앱마다 Swagger 를 생성해 준다.

**평가 단위는 쿼리 1개다** (`open-questions.md` #1 재확정, 2026-07-30).
앱 단위가 아니다 — 이전 계약은 앱에 등록된 쿼리 전부를 한 번에 평가했는데,
DAC 은 쿼리를 등록·수정하는 그 자리에서 "이 쿼리 하나가 검색에 잘 걸리는가" 를
묻는다. 그래서 요청도 결과도 쿼리 하나에 대한 것이다.

### 평가 파이프라인 — 이 백엔드가 직접 수행한다

```
DAC ──POST { "query_id": "..." }──▶ 백엔드
                                     │
      1. pgvector 에서 그 쿼리의 content 조회
         (summary / description / x-question)
      2. LLM 으로 질문 100개 생성
      3. 각 질문을 bge-m3 로 임베딩
      4. 벡터 검색으로 상위 3개 query_id
      5. top_1 / top_3 hit 계산, 개선 추천 도출
                                     │
                                     ▼
                          결과 JSON (아래 §2)
```

**이전 계약과 뒤집힌 점**: 평가 엔진은 더 이상 이 시스템 밖에 없다.
백엔드가 파이프라인을 직접 돌린다. 그래서 "외부 평가툴 출력을 계약으로 변환하는
어댑터" 라는 1차 역할과 그 흔적(`meta.rawSource`)이 사라졌다.

### 무상태 (stateless)

**평가 결과를 저장하지 않는다.** 요청이 올 때마다 처음부터 다시 평가한다.
여기서 따라오는 결과는 전부 계약에 반영돼 있다:

- 이력이 없으므로 **`previous` 도 델타 뱃지도 없다.**
- 조회할 과거 결과가 없으므로 **이력 목록 API 가 없다.**
- 결과를 가리키는 영속 식별자가 없다. `traceId` 는 **이 실행 한 번**을 뜻하며
  로그 대조용이다 — 나중에 그 ID 로 다시 조회할 수 없다 (#68).

### 인증

없다. 사내망 안에서 DAC 이 직접 호출한다.

### 용어

화면과 문서의 기본 용어는 **"쿼리"** 다. "API" 나 "엔드포인트" 로 쓰지 않는다 —
사용자는 REST 엔드포인트가 아니라 자기가 등록한 SELECT 쿼리로 인식한다.
JSON 필드 이름은 HTTP 규약을 따르므로 `method` / `path` 를 그대로 쓰지만,
라벨은 "평가 대상 쿼리", "검색된 쿼리" 처럼 적는다.

---

## 1. 엔드포인트

| 메서드 | 경로 | 설명 | 우선순위 |
|---|---|---|---|
| `POST` | `/api/v1/evaluations` | **쿼리 1개를 평가하고 결과를 반환한다** | **P0** |
| `POST` | `/api/v1/specs/{query_id}/regenerate-request` | 부실한 쿼리를 자동 생성 서비스로 넘기는 요청 | P2 |

**대시보드는 P0 하나로 전부 그려진다.**

### 요청 본문

```jsonc
{ "query_id": "q-lot-status" }
```

`queryId` (camelCase) 도 받는다. DAC 이 보내는 형태가 `query_id` 이고, 이 계약의
직렬화 규약은 camelCase 라 둘이 어긋난다 — 요청 모델만 **양쪽을 다 받아** 그
불일치를 경계에서 흡수한다. 응답은 규약대로 camelCase 하나뿐이다.

### 왜 GET 이 아니라 POST 인가

무상태라서 **요청 자체가 평가를 실행시킨다.** LLM 호출 100건과 벡터 검색이
매번 일어나고 수십 초가 걸린다. GET 으로 두면 브라우저 프리페치·새로고침·
크롤러가 그때마다 평가를 돌린다. 부수효과가 있는 조회는 GET 이 아니다.

---

## 2. POST /api/v1/evaluations — 응답

```jsonc
{
  // 이 실행 한 번을 가리키는 값. **저장되지 않는다** — 로그 대조용이다(#68).
  "traceId": "R-8f31c2",
  "evaluatedAt": "2026-07-30T11:38:00+09:00",

  // 평가 대상 쿼리 **하나**. 이전 계약의 앱 정보(appName/specVersion/queryCount)는 없다.
  // summary / description / xQuestions 를 그대로 내려주는 이유는, 화면이
  // "이 설명으로 검색이 걸릴 만한가" 를 사용자에게 직접 보여주기 위해서다.
  "target": {
    "queryId": "q-lot-status",
    "appId": "mf-worker",              // optional. DAC 이 안 주면 null
    "method": "GET",
    "path": "/queries/lot-status",
    "summary": "랏 현재 공정 단계 조회", // optional. 없으면 null — 없다는 사실이 곧 평가 결과다
    "description": "랏 번호로 ...",      // optional. 없으면 null
    "xQuestions": [                     // 명세에 적힌 예시 질문. 없으면 빈 배열
      "랏 번호로 지금 어느 공정에 있는지 확인하려면?"
    ]
  },

  "meta": {
    "embeddingModel": "bge-m3",
    "searchMode": "HYBRID",
    "topK": 3,
    "questionCount": 100,   // 생성한 질문 수. summary.totalQuestions 와 같아야 한다
    "durationMs": 48210
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

  // **자리표시다.** 실제 분류 체계가 미확정이다 (#69) — 아래 §3 참고.
  "questionTypes": [
    { "type": "DIRECT", "label": "직접 질문", "count": 22, "ratio": 22.0, "top3Accuracy": 95.5 }
  ],

  // **항목 전체 목록이 미확정이다** (#70).
  "recommendations": [
    {
      "order": 1,
      "title": "설명(Description) 보강",
      "description": "summary 는 있으나 description 이 비어 있어 검색이 참고할 문장이 부족합니다.",
      "priority": "HIGH",
      "failShare": 45.0
    }
  ],

  // 생성된 질문 전체(성공 포함). 건수 = totalQuestions = meta.questionCount.
  // 정렬: TOP3 실패 -> TOP1_ONLY 실패 -> 성공, 그 안에서 no 오름차순.
  //
  // **expected 가 없다.** 평가 대상이 쿼리 하나이므로 100문항의 정답이 전부
  // target 과 같다. 문항마다 되풀이하면 같은 값이 100번 실려 오고, 화면에도
  // 같은 경로가 100줄 반복된다. 화면은 표 위에 한 번만 적는다.
  //
  // **top1 도 없다.** 항상 top3[0] 과 같은 값이었다.
  "questions": [
    {
      "no": 17,
      "question": "스텝 사이클타임 조회 query 있나요?",
      "questionType": "MIXED_LANG",
      // 검색 결과 상위 3개. **3개 미만일 수 있고, 한 건도 없으면 null 이다.**
      // 코퍼스가 작거나 유사도 하한에 걸리면 실제로 그렇다.
      "top3": [
        { "rank": 1, "queryId": "q-wafer-yield", "path": "/queries/wafer-yield-daily", "score": 0.680 },
        { "rank": 2, "queryId": "q-lot-trace",   "path": "/queries/lot-trace",         "score": 0.635 },
        { "rank": 3, "queryId": "q-eqp-downtime","path": "/queries/equipment-downtime","score": 0.590 }
      ],
      "top1Hit": false,
      "top3Hit": false,
      "failureScope": "TOP3",                    // NONE | TOP1_ONLY | TOP3
      "expectedRank": null,                      // 대상 쿼리가 몇 위였는지. Top-N 밖이면 null
      "failureCategory": "DESCRIPTION_MISSING",  // 성공이면 null
      "reason": "설명이 전혀 없어 경로 토큰 외에 매칭 근거가 없음"
    },
    {
      "no": 3,
      "question": "랏 상태를 조회하는 쿼리는 무엇인가요?",
      "questionType": "DIRECT",
      "top3": [
        { "rank": 1, "queryId": "q-lot-status", "path": "/queries/lot-status", "score": 0.920 }
      ],
      "top1Hit": true,
      "top3Hit": true,
      "failureScope": "NONE",
      "expectedRank": 1,
      "failureCategory": null,
      "reason": null
    },
    {
      "no": 42,
      "question": "asdf",
      "questionType": "SHORT_KEYWORD",
      "top3": null,                    // 검색 결과가 한 건도 없음
      "top1Hit": false,
      "top3Hit": false,
      "failureScope": "TOP3",
      "expectedRank": null,
      "failureCategory": "KEYWORD_MISMATCH",
      "reason": "유사도 하한을 넘는 결과가 없음"
    }
  ]
}
```

### 필드 규약

- 모든 비율(`ratio`, `*Accuracy`, `failShare`)은 **0~100 실수**. 0~1 소수 금지.
- `score` 는 **코사인 유사도 0~1** (bge-m3, 1024차원). 정규화된 값이다.
- `expectedRank` 는 **평가 대상 쿼리(`target.queryId`)가 검색 결과에서 몇 위였는지**.
  Top-N 밖이거나 결과가 없으면 `null`.
- `recommendations[].failShare` 의 **합은 100을 넘을 수 있다** (한 실패에 원인이 복수).
  화면에 "원인 중복 집계" 각주 필수.
- 시각은 전부 ISO 8601 + 타임존.
- **`meta.questionCount` = `summary.totalQuestions` = `questions` 길이.**
  같은 수가 두 자리에 있으므로 백엔드가 검증한다 (`EvaluationReport` 의
  model_validator). 어긋난 응답은 계약 위반으로 거절된다 — 화면이 "100문항 중"
  이라고 써놓고 표에 98줄이 뜨는 상황을 만들지 않는다.
- `target.xQuestions` 는 예시 질문이 없으면 **빈 배열**이다. `null` 도 아니고
  생략도 아니다 — **필수 필드다.** 그래야 생성된 프론트 타입이 `string[]` 이 되고
  화면마다 `?.length` 방어를 달지 않는다. 값을 만드는 것이 외부 시스템이 아니라
  이 백엔드의 파이프라인이므로, 빠졌다면 계약 위반으로 거절하는 편이 낫다.

### 제거된 필드 (이전 계약과의 차이)

| 제거 | 이유 |
|---|---|
| `queries[]` | 평가 단위가 쿼리 1개다. 앱의 쿼리 목록이라는 개념 자체가 없다 |
| `previous` | 무상태 — 비교할 이전 평가가 없다 |
| `questions[].expected` | 항상 `target` 과 같다 |
| `questions[].top1` | 항상 `top3[0]` 과 같았다 |
| `meta.rawSource` | 외부 평가툴이 없다. 백엔드가 직접 평가한다 |
| `meta.questionSource` | 질문 생성 주체가 하나로 확정됐다 — 백엔드의 LLM |
| `target.appName` / `specVersion` / `queryCount` / `owner` | 앱 단위 정보 |
| `EvaluationListItem` / 이력 목록 API | 무상태 — 목록이 없다 |

### 선택 필드 · 빈 배열이 왔을 때

**누가 그 부재를 처리하는지를 여기 적어 둔다** — 계약에 선택 필드를 추가할 때는
이 표에 한 줄을 함께 추가한다. 표에 없는 자리가 생기면 화면 어딘가가 빈 채로 남는다.

| 자리 | 없을 때 | 처리하는 곳 |
|---|---|---|
| `target.appId` | 앱 표기를 그리지 않음 | `QueryInfoCard` |
| `target.summary` | "summary 없음" 을 **경고색으로** 표기 — 없다는 사실이 곧 평가 결과다 | `QueryInfoCard` |
| `target.description` | "description 없음" 을 경고색으로 표기 | `QueryInfoCard` |
| `target.xQuestions` 가 빈 배열 | 접이식 자체를 만들지 않음 | `QueryInfoCard` |
| `questions[].top3` 가 `null` | "검색 결과 없음" 으로 표기. 순위 목록을 그리지 않음 | `FailureTable` |
| `questions[].top3` 가 3개 미만 | 있는 만큼만 그림 | `FailureTable` |
| `questions[].expectedRank` | "대상 쿼리: 순위 밖" | `FailureTable` |
| `questions[].failureCategory` | 원인 필터 칩에서 제외 | `FailureTable` |
| `questions[].reason` | 대시(—)로 "없음" 을 명시 | `FailureTable` |
| `questionTypes` 가 빈 배열 | 빈 도넛 대신 "문항 유형 정보가 없습니다" | `QuestionTypeChart` |
| `questionTypes[].count` 가 0 | 범례는 남기되 인식률은 대시(—), 막대에서는 제외 | `QuestionTypeChart` |
| `recommendations` 가 빈 배열 | 권장 조치·권장 액션 컬럼을 통째로 없애고 좌측이 전체 폭 | `page.tsx`, `RecommendationCards`, `ActionPanel` |
| `questions` 가 빈 배열 | "표시할 문항이 없습니다" | `FailureTable` |

필드가 **아예 빠진 경우와 `null` 인 경우를 모두 통과**시켜야 한다
(`backend/tests/test_adapter_contract.py`).

### questions — 문항 100개 전체

- **평가 대상은 실패만이 아니라 문항 전체다.** `questions` 의 길이는
  `summary.totalQuestions` 와 같고, 성공 문항도 들어온다.
- `failureScope` 로 실패 범위를 나눈다.
  - `NONE` — Top-1 부터 맞음 (성공). `failureCategory` 와 `reason` 이 `null`.
  - `TOP1_ONLY` — Top-1 은 틀렸으나 Top-3 안에는 있음.
  - `TOP3` — Top-3 밖 (완전 실패). **검색 결과가 없는 경우(`top3: null`)도 여기다.**
- 개수 정합: `top1FailCount = TOP1_ONLY + TOP3`, `top3FailCount = TOP3`.
- `top1Hit` / `top3Hit` 은 **평가 대상 쿼리**가 각각 1위 / 상위 3위 안에 있었는지.
  비교 대상은 `top3[].queryId` 와 `target.queryId` 다 — path 가 아니라 **id 로 비교한다**.
  path 는 표시용이고, 같은 path 가 다른 쿼리일 수 있다.
- **정렬: `TOP3` → `TOP1_ONLY` → `NONE`, 그 안에서 `no` 오름차순.** 손봐야 할 것이 위로.
- `top3` 는 `null` 이거나 1~topK 개다. **길이를 3으로 가정하지 않는다.**

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

> **이 7종은 자리표시다** (`open-questions.md` #69).
> 실제 분류 체계는 사내 질문 생성 프롬프트가 정하며 아직 확정되지 않았다.
> 지금까지 알려진 것은 상위 갈래 세 개뿐이다 — **업무 관련 / 생성 관련 / 기타**.
> 개수 배분도 프롬프트가 정한다.
>
> **바꿀 때 고치는 곳은 두 곳뿐이다:**
>   1. `backend/app/schemas/evaluation.py` 의 `QuestionType`
>   2. `frontend/src/lib/enumTokens.ts` 의 `questionTypeColorVar` / `questionTypeLabel`
>
> 그러면 도넛·범례·막대·원인 필터가 전부 따라온다. 컴포넌트에 유형 이름을
> 적어둔 곳이 없기 때문이다. `enumTokens.ts` 의 두 테이블은 `Record<QuestionType, …>`
> 이라 enum 이 바뀌면 **타입 에러로 빠진 항목을 알려준다.** 색이 모자라면
> `globals.css` 의 `--chart-type-*` 를 함께 늘린다.

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

### POST /api/v1/specs/{query_id}/regenerate-request (P2)

부실한 쿼리를 **별도 팀의 Swagger 자동 생성 서비스로 넘기는 요청**이다.

**이 서비스가 설명을 직접 덮어쓰지 않는다.** 요청을 접수해 넘길 뿐이고,
실제 생성과 반영은 그쪽 팀의 절차를 따른다. 그래서 화면의 버튼도
"덮어쓰기" 가 아니라 "넘기기" 로 읽혀야 한다.

```jsonc
// 요청 — 대상이 쿼리 하나이므로 본문이 필요 없다. 경로의 query_id 가 대상이다.
// 응답 202
{
  "requestId": "req_20260730_001",
  "status": "SUBMITTED"             // SUBMITTED | ACCEPTED | REJECTED
}
```

> 받는 팀의 API 스펙이 아직 확정되지 않았다 (`open-questions.md` #52).
> 위 형태는 이쪽에서 필요한 최소치를 적어둔 것이며, 확정되면 여기를 먼저 고친다.

### 삭제된 P1 엔드포인트 — 비동기 실행 / 진행 상태

이전 계약에는 `POST /api/v1/evaluations` (202 + `jobId`) 와
`GET /{trace_id}/status` 가 P1 로 있었다. **무상태 전환으로 둘 다 성립하지 않는다** —
`jobId` 나 `traceId` 로 나중에 상태를 물으려면 그 실행을 서버가 기억해야 한다.

지금은 `POST /api/v1/evaluations` 가 평가를 **동기로** 수행하고 결과를 바로
반환한다. 수십 초 걸리는 요청을 한 번에 처리하는 방식이라 타임아웃 설계가
중요해진다 (`open-questions.md` #71).

## 5. 시안 대비 변경점

### 추가

| 필드 | 이유 |
|---|---|
| `questionTypes[].top3Accuracy` | 시안엔 분포만 있음. **"한영 혼합 40%"** 가 나와야 액션이 나온다. 추가 가치 1위 |
| `top3[].score` | 아깝게 놓친 건지 완전히 빗나간 건지 구분 |
| `meta` | 재현성 (모델·검색방식·문항 수·소요시간) |
| `target.summary` / `description` / `xQuestions` | **평가 대상 쿼리의 설명을 화면에 그대로 보여준다.** 인식률이 낮은 이유를 사용자가 숫자가 아니라 자기 설명에서 바로 보게 하는 것이 목적이다 (Phase 12) |

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
- 시안의 `previous` Before/After 델타 → **무상태 전환으로 제거**했다. 저장하지
  않으므로 비교할 이전 평가가 없다 (§0). 추이 비교가 필요해지면 저장 여부부터
  다시 결정해야 한다
- 평가 대상을 엔드포인트 1개로 그린 부분 → **결과적으로 시안이 맞았다.**
  Phase 12 에서 평가 단위가 쿼리 1개로 돌아왔다 (§0)

---

## 6. 변경 이력

| 날짜 | 변경 | 사유 |
|---|---|---|
| 2026-07-22 | 최초 작성 | — |
| 2026-07-23 | 평가 단위를 앱으로 변경, `queries` 신설, 용어를 "쿼리"로 통일, 재생성을 요청 방식으로 변경 | 미정 #1 확정 (DAC 앱 단위) |
| 2026-07-24 | 등급을 top1Grade/top3Grade 로 분리, failures→questions(100문항 전체), failureScope 신설, failureCategory 확장, meta.rawSource 추가 | 담당자 확정 스펙 반영 |
| 2026-07-26 | 계약 자체는 그대로. "선택 필드·빈 배열" 절 신설 | Phase 10 안정화 — 부재를 누가 처리하는지 계약 옆에 적어 둔다 |
| 2026-07-30 | **평가 단위를 쿼리 1개로, 무상태로 전환 (Phase 12).** 요청은 `POST { query_id }`. `queries[]` / `previous` / `questions[].expected` / `questions[].top1` / `meta.rawSource` / `meta.questionSource` / 이력 목록 API / 비동기 실행·상태 P1 제거. `target` 을 단일 쿼리로(`queryId`/`summary`/`description`/`xQuestions`). `top3[]` 에 `queryId` 추가·`method` 제거·`null` 허용. `meta.questionCount` 추가 | 평가 엔진이 이 백엔드 안으로 들어왔고 DAC 이 쿼리 단위로 호출한다 (#1 재확정) |
