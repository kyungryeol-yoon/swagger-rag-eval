/**
 * 계약 타입 재노출.
 *
 * `api-types.ts` 는 백엔드 openapi.json 에서 생성된 산출물이라
 * `components["schemas"]["Failure"]` 같은 긴 표기를 그대로 쓰게 된다.
 * 컴포넌트가 그 표기를 직접 들고 있으면 생성기 출력 형태가 바뀔 때마다
 * 화면 코드를 전부 고쳐야 하므로, 이 파일 하나만 거치게 한다.
 *
 * 규칙:
 * - 타입을 여기서 **새로 정의하지 않는다**. 재노출만 한다.
 *   계약의 진실은 `backend/app/schemas/evaluation.py` 하나뿐이다.
 * - 계약에 없는 화면 전용 타입이 필요하면 그 컴포넌트 폴더 안에 둔다.
 */

import type { components } from "./api-types";

type Schemas = components["schemas"];

// --- 최상위 응답 -----------------------------------------------------------

/** POST /api/v1/evaluations 의 응답. 대시보드 전체가 이것 하나로 그려진다. */
export type Evaluation = Schemas["EvaluationReport"];

/** POST /api/v1/evaluations 의 요청 본문. `{ queryId }` — 백엔드는 `query_id` 도 받는다. */
export type EvaluateRequest = Schemas["EvaluateRequest"];

// --- 구성 요소 -------------------------------------------------------------

/**
 * 평가 대상 DAC 쿼리 **하나**.
 *
 * 평가 단위가 앱에서 쿼리로 바뀌면서 `TargetApp` 을 대신한다 (contract.md §0).
 * summary / description / xQuestions 를 그대로 들고 있어서, 화면이 "이 설명으로
 * 검색이 걸릴 만한가" 를 사용자에게 직접 보여줄 수 있다.
 */
export type TargetQuery = Schemas["TargetQuery"];

export type EvaluationMeta = Schemas["EvaluationMeta"];
export type EvaluationSummary = Schemas["EvaluationSummary"];
export type QuestionTypeStat = Schemas["QuestionTypeStat"];
export type Recommendation = Schemas["Recommendation"];

/** 생성된 질문 1개의 평가 결과(성공 포함). 실패만이 아니라 100문항 전체가 이 타입이다. */
export type QuestionResult = Schemas["QuestionResult"];

/**
 * 검색 결과 1건(순위 포함).
 *
 * `method` 가 없다 — 결과를 식별하는 것은 `queryId` 이고 `path` 는 표시용이다.
 * **hit 판정도 queryId 로 한다** (contract.md §2).
 */
export type SearchResult = Schemas["SearchResult"];

// --- Enum ------------------------------------------------------------------
// 문자열 리터럴 유니온으로 생성된다.
// 화면에서 이 값을 직접 비교해 색을 정하지 말 것 — enum → 토큰 매핑 테이블을 거친다.

export type Grade = Schemas["Grade"];
export type Priority = Schemas["Priority"];
export type SearchMode = Schemas["SearchMode"];

/** **자리표시다** — 실제 분류 체계는 미확정(open-questions #69). */
export type QuestionType = Schemas["QuestionType"];

/** 항목 전체 목록이 미확정(open-questions #70). */
export type FailureCategory = Schemas["FailureCategory"];

export type FailureScope = Schemas["FailureScope"];
