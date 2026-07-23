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

/** GET /api/v1/evaluations/{trace_id} 의 응답. 대시보드 전체가 이것 하나로 그려진다. */
export type Evaluation = Schemas["EvaluationReport"];

// --- 구성 요소 -------------------------------------------------------------

/** 평가 대상 DAC 앱. 평가 단위는 쿼리 하나가 아니라 앱 하나다 (contract.md §0). */
export type TargetApp = Schemas["TargetApp"];

/** 쿼리 1개의 설명 품질과 인식률. 이 화면의 실질 산출물이다. */
export type QueryStat = Schemas["QueryStat"];
export type EvaluationMeta = Schemas["EvaluationMeta"];
export type EvaluationSummary = Schemas["EvaluationSummary"];
export type QuestionTypeStat = Schemas["QuestionTypeStat"];
export type Recommendation = Schemas["Recommendation"];
export type Failure = Schemas["Failure"];
/** 문항이 찾아냈어야 하는 정답 쿼리. */
export type ExpectedApi = Schemas["ExpectedApi"];
export type SearchResult = Schemas["SearchResult"];
export type PreviousEvaluation = Schemas["PreviousEvaluation"];

// --- Enum ------------------------------------------------------------------
// 문자열 리터럴 유니온으로 생성된다.
// 화면에서 이 값을 직접 비교해 색을 정하지 말 것 — enum → 토큰 매핑 테이블을 거친다.

export type Grade = Schemas["Grade"];
export type Priority = Schemas["Priority"];
export type SearchMode = Schemas["SearchMode"];
export type QuestionType = Schemas["QuestionType"];
export type FailureCategory = Schemas["FailureCategory"];
