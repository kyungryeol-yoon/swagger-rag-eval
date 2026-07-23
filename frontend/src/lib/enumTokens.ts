/**
 * enum -> CSS 변수 / 표시 문자열 매핑.
 *
 * **컴포넌트는 색과 라벨을 정할 때 반드시 이 파일을 경유한다.**
 * `grade === "CRITICAL" ? "#f87171" : ...` 나 `type === "MIXED_LANG" ? "한영 혼합" : ...`
 * 같은 코드를 쓰지 않는다. 그렇게 하면 판단이 컴포넌트마다 흩어지고,
 * enum 이 하나 추가될 때 어디를 고쳐야 하는지 알 수 없게 된다.
 *
 * 색 값은 `styles/globals.css` 의 의미 토큰이다. 원색(--red 등)을 직접
 * 가리키지 않는다 — 그건 globals.css 안에서 한 번만 연결한다.
 *
 * 모든 테이블이 `Record<Enum, ...>` 이므로 계약에 값이 추가되면
 * (`make gen-types` 후) 여기서 컴파일 에러가 난다. 의도한 것이다.
 */

import type { FailureCategory, Grade, Priority, QuestionType } from "./types";

/** CSS 변수명 -> `var(--...)` 형태로. style 속성에 바로 넣을 수 있다. */
export function cssVar(name: string): string {
  return `var(${name})`;
}

// ---------------------------------------------------------------------------
// 등급 (grade) — 상태색
// ---------------------------------------------------------------------------
// 기준은 docs/contract.md §3:
//   CRITICAL <70% / NEEDS_IMPROVEMENT 70~85% / FAIR 85~95% / GOOD >=95%

export const gradeColorVar: Record<Grade, string> = {
  CRITICAL: "--grade-critical",
  NEEDS_IMPROVEMENT: "--grade-needs-improvement",
  FAIR: "--grade-fair",
  GOOD: "--grade-good",
};

/**
 * 등급의 표시 문구. docs/contract.md §3 확정안.
 *
 * **이 문자열은 여기 한 곳에만 존재한다.** 화면에 등급을 찍을 때
 * 문자열을 다시 적지 않는다.
 */
export const gradeLabel: Record<Grade, string> = {
  CRITICAL: "심각",
  NEEDS_IMPROVEMENT: "개선 필요",
  FAIR: "보통",
  GOOD: "우수",
};

/** 등급에 해당하는 색. `style={{ color: gradeColor(grade) }}` 처럼 쓴다. */
export function gradeColor(grade: Grade): string {
  return cssVar(gradeColorVar[grade]);
}

// ---------------------------------------------------------------------------
// 우선순위 (priority) — 상태색
// ---------------------------------------------------------------------------
// 시안의 권장조치 카드가 red / sky 2단계로만 구분한다. amber 는 grade 전용.

export const priorityColorVar: Record<Priority, string> = {
  HIGH: "--priority-high",
  MEDIUM: "--priority-medium",
  LOW: "--priority-low",
};

/** 우선순위에 해당하는 색. */
export function priorityColor(priority: Priority): string {
  return cssVar(priorityColorVar[priority]);
}

// ---------------------------------------------------------------------------
// 질문 유형 (questionType) — 범주색
// ---------------------------------------------------------------------------
// **범주 구분용이며 상태(위험/주의)를 의미하지 않는다.**
// ERROR_CASE 가 red 인 것은 그 유형이 나쁘다는 뜻이 아니라 도넛에서
// 옆 조각과 구분되어야 하기 때문이다. 유형별 인식률의 좋고 나쁨은
// grade 토큰이 따로 표현한다.

export const questionTypeColorVar: Record<QuestionType, string> = {
  DIRECT: "--chart-type-direct",
  USER_NL: "--chart-type-user-nl",
  DOMAIN_TERM: "--chart-type-domain-term",
  PARAMETER: "--chart-type-parameter",
  ERROR_CASE: "--chart-type-error-case",
  SHORT_KEYWORD: "--chart-type-short-keyword",
  MIXED_LANG: "--chart-type-mixed-lang",
};

/**
 * 질문 유형의 표시 문구. docs/contract.md §3 questionType 라벨 표.
 *
 * 응답의 `questionTypes[].label` 에도 같은 문자열이 내려오지만,
 * 실패 목록(`failures[].questionType`)에는 enum 만 있고 라벨이 없다.
 * 그래서 프론트에도 표가 필요하다.
 */
export const questionTypeLabel: Record<QuestionType, string> = {
  DIRECT: "직접 질문",
  USER_NL: "사용자 자연어 질문",
  DOMAIN_TERM: "업무 용어 질문",
  PARAMETER: "파라미터 기반 질문",
  ERROR_CASE: "오류/에러 상황 질문",
  SHORT_KEYWORD: "짧은 키워드 질문",
  MIXED_LANG: "한영 혼합 질문",
};

/** 질문 유형에 해당하는 범주색. */
export function questionTypeColor(type: QuestionType): string {
  return cssVar(questionTypeColorVar[type]);
}

// ---------------------------------------------------------------------------
// 실패 원인 (failureCategory)
// ---------------------------------------------------------------------------
// **색을 주지 않는다.** 실패의 종류를 나누는 범주일 뿐, 어느 원인이 더 나쁘다는
// 뜻이 아니다. 색을 붙이면 "빨간 원인이 더 심각한가?" 하고 읽게 된다.
// 화면에서는 중립 뱃지(--surface-2 배경 + --border 테두리)로 표시한다.

export const failureCategoryLabel: Record<FailureCategory, string> = {
  METHOD_MISMATCH: "Method 불일치",
  SIMILAR_RESOURCE: "유사 리소스 혼동",
  SYNONYM_MISS: "동의어 인식 실패",
  DESCRIPTION_MISSING: "설명 누락",
  PARAM_MISSING: "파라미터 설명 누락",
  OTHER: "기타",
};
