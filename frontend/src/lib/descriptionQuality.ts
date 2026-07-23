/**
 * 쿼리 설명 품질을 3단계로 요약한다.
 *
 * **이것은 표시용 요약이지 판단이 아니다.** 어느 쿼리를 재생성할지는
 * 백엔드가 정한 `needsRegeneration` 이 진실이다 (contract.md §2, open-questions #53).
 * 여기서는 `descriptionLength` 와 `hasParamDescription` 만으로 "왜 인식률이
 * 낮은지" 를 사람이 읽을 수 있게 라벨을 붙일 뿐이다. 이 값으로 등급이나
 * 재생성 여부를 다시 계산하지 않는다.
 *
 * 판정 기준은 Phase 2 의 설명 품질 3등급과 같은 선이다:
 *   FULL    설명이 충실하고 파라미터 설명도 있다        (GOOD)
 *   SPARSE  summary 는 있으나 상세 설명/파라미터가 없다  (POOR)
 *   MISSING summary 도 상세 설명도 없다                (EMPTY)
 */

export type DescriptionQuality = "FULL" | "SPARSE" | "MISSING";

/**
 * "충실" 로 볼 최소 설명 길이(글자 수).
 *
 * fixture 의 GOOD 쿼리는 158~182 자, POOR/EMPTY 는 0 자다. 80 은 그 사이
 * 넉넉한 선이다 — 한두 문장짜리 설명이 들어와도 충실로 잡되, 공백은 확실히
 * 걸러낸다. 백엔드 판정 기준(#53)이 확정되면 그 값에 맞춰 조정한다.
 */
export const FULL_DESCRIPTION_MIN_LENGTH = 80;

/**
 * 설명 품질 요약.
 *
 * summary 가 없고 설명도 0 이면 MISSING. 설명이 충분히 길고 파라미터 설명까지
 * 있으면 FULL. 그 사이(summary 만 있거나 파라미터 설명이 빠짐)는 SPARSE.
 */
export function describeQuality(query: {
  // 생성된 타입에서 summary 는 optional 이라 undefined 도 받는다.
  summary?: string | null;
  descriptionLength: number;
  hasParamDescription: boolean;
}): DescriptionQuality {
  if (!query.summary && query.descriptionLength === 0) {
    return "MISSING";
  }
  if (
    query.descriptionLength >= FULL_DESCRIPTION_MIN_LENGTH &&
    query.hasParamDescription
  ) {
    return "FULL";
  }
  return "SPARSE";
}

export const descriptionQualityLabel: Record<DescriptionQuality, string> = {
  FULL: "설명 충실",
  SPARSE: "설명 부족",
  MISSING: "설명 없음",
};

/**
 * 3단계의 색.
 *
 * **상태색(grade)과 경쟁시키지 않는다.** 인식률의 좋고 나쁨은 옆 컬럼의
 * grade 막대가 이미 말하고, 재생성 필요 여부는 amber pill 이 말한다.
 * 여기서 또 빨강/노랑을 쓰면 한 행에서 세 곳이 같은 신호를 두고 다툰다.
 * 그래서 밝기만 나눈다 — 충실할수록 밝고, 없을수록 흐리게.
 */
export const descriptionQualityColorVar: Record<DescriptionQuality, string> = {
  FULL: "--text",
  SPARSE: "--text-dim",
  MISSING: "--text-mute",
};
