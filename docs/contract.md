# 응답 계약 (Contract)

> **이 문서가 단일 진실 공급원이다.**
> 시안(`mockup.svg`)과 충돌하면 이 문서가 이긴다.
> 사내 요구사항이 바뀌면 **여기를 먼저 고치고** 나서 코드를 고친다.

구현 위치: `backend/app/schemas/evaluation.py` (Pydantic v2)
프론트 타입: `frontend/src/lib/api-types.ts` (`openapi-typescript` 생성물, 수기 편집 금지)

---

## 1. 엔드포인트

| 메서드 | 경로 | 설명 | 우선순위 |
|---|---|---|---|
| `GET` | `/api/v1/evaluations/{trace_id}` | 대시보드 전체 데이터 | **P0** |
| `POST` | `/api/v1/evaluations` | 평가 실행 (비동기, `job_id` 반환) | P1 |
| `GET` | `/api/v1/evaluations/{trace_id}/status` | 진행 상태 | P1 |
| `GET` | `/api/v1/evaluations` | 이력 목록 | P2 |
| `POST` | `/api/v1/specs/{spec_id}/regenerate` | AI로 Swagger 설명 재생성 | P2 |

**대시보드는 P0 하나로 전부 그려진다.** 나머지는 나중에 붙여도 화면이 흔들리지 않는다.

---

## 2. GET /api/v1/evaluations/{trace_id}

```jsonc
{
  "traceId": "A492",
  "evaluatedAt": "2026-07-22T11:38:00+09:00",

  "target": {
    "specId": "orders-v3",
    "specVersion": "v3",
    "method": "GET",
    "path": "/api/v1/orders/{id}/refund-status",
    "summary": "주문 환불 상태 조회",
    "description": "특정 주문 건의 환불 처리 상태, 환불 사유, 처리 일자를 반환합니다."
  },

  "meta": {
    "embeddingModel": "bge-m3",
    "searchMode": "HYBRID",
    "topK": 3,
    "questionSource": "LLM_GENERATED_HUMAN_REVIEWED",
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
        { "rank": 1, "method": "GET",  "path": "/orders/{id}/refund-status", "score": 0.812 },
        { "rank": 2, "method": "POST", "path": "/orders/{id}/refund",        "score": 0.774 },
        { "rank": 3, "method": "GET",  "path": "/orders/{id}",               "score": 0.701 }
      ],
      "hit": false,
      "expectedRank": 7,
      "failureCategory": "METHOD_MISMATCH",
      "reason": "질문의 '취소'를 조회(GET) 의도로 오인식하여 DELETE 엔드포인트가 후순위로 밀림"
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
- `expectedRank` 는 기대 API가 전체 검색 결과에서 몇 위였는지. **Top-N 밖이면 `null`**.
- `previous` 는 이전 평가가 없으면 `null`. 프론트는 델타 뱃지를 숨긴다.
- `recommendations[].failShare` 의 **합은 100을 넘을 수 있다** (한 실패에 원인이 복수).
  화면에 "원인 중복 집계" 각주 필수.
- 시각은 전부 ISO 8601 + 타임존.

---

## 3. Enum (백엔드가 확정해서 내려준다)

```
grade            CRITICAL | NEEDS_IMPROVEMENT | FAIR | GOOD
priority         HIGH | MEDIUM | LOW
searchMode       BM25 | VECTOR | HYBRID
questionType     DIRECT | USER_NL | DOMAIN_TERM | PARAMETER
                 | ERROR_CASE | SHORT_KEYWORD | MIXED_LANG
failureCategory  METHOD_MISMATCH | SIMILAR_RESOURCE | SYNONYM_MISS
                 | DESCRIPTION_MISSING | PARAM_MISSING | OTHER
```

### 등급 기준

| grade | Top-3 인식률 | 라벨 | 색 토큰 |
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

## 4. POST /api/v1/evaluations (P1)

```jsonc
// 요청
{ "specId": "orders-v3", "questionCount": 100, "topK": 3, "searchMode": "HYBRID" }

// 응답 202
{ "jobId": "job_7f2a", "traceId": "A493", "statusUrl": "/api/v1/evaluations/A493/status" }
```

### GET /{trace_id}/status

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

---

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

---

## 6. 변경 이력

| 날짜 | 변경 | 사유 |
|---|---|---|
| 2026-07-22 | 최초 작성 | — |
