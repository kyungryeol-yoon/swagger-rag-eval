/**
 * 등급 구간과 반원 게이지 좌표 변환.
 *
 * **`docs/contract.md` §3 이 진실이다.** 기준이 바뀌면 `GRADE_BANDS` 만 고치면
 * 호·범례·aria 라벨이 한꺼번에 따라온다. 컴포넌트에 숫자를 적지 않는다.
 *
 * 각도 변환이 컴포넌트가 아니라 여기 있는 이유: 프론트에는 테스트 러너가 없다
 * (새 npm 패키지 금지 — CLAUDE.md 절대 규칙 1). `.tsx` 안에 있으면 JSX 때문에
 * 어떤 방법으로도 따로 돌려볼 수 없지만, 타입만 걷어내면 실행되는 `.ts` 파일에
 * 두면 `node --experimental-strip-types` 로 실제 코드를 그대로 검증할 수 있다.
 */

import type { Grade } from "./types";

export type GradeBand = {
  grade: Grade;
  /** 구간 하한(포함). */
  min: number;
  /** 구간 상한(미만). 마지막 구간만 100 이하. */
  max: number;
};

/** 어느 지표의 등급인지. summary.top1Grade / top3Grade 와 짝을 이룬다. */
export type GradeMetric = "top1" | "top3";

/**
 * contract.md §3 등급 기준. 순서가 곧 게이지의 좌→우 순서다.
 *
 * **지표별로 나눠 둔다.** 현재는 Top-1 과 Top-3 의 임계값이 같지만
 * (0-70-85-95), 갈릴 수 있어서 구조를 분리한다 (open-questions #54).
 * 임계값이 달라지면 해당 지표의 배열만 고치면 호·범례·aria 라벨이 따라온다.
 */
export const GRADE_BANDS = {
  top1: [
    { grade: "CRITICAL", min: 0, max: 70 },
    { grade: "NEEDS_IMPROVEMENT", min: 70, max: 85 },
    { grade: "FAIR", min: 85, max: 95 },
    { grade: "GOOD", min: 95, max: 100 },
  ],
  top3: [
    { grade: "CRITICAL", min: 0, max: 70 },
    { grade: "NEEDS_IMPROVEMENT", min: 70, max: 85 },
    { grade: "FAIR", min: 85, max: 95 },
    { grade: "GOOD", min: 95, max: 100 },
  ],
} as const;

/**
 * 지표 안에서 등급에 해당하는 구간.
 *
 * **값이 아니라 등급으로 찾는다.** 등급은 백엔드가 확정해 내려주므로
 * 프론트가 value 로부터 구간을 추론하면 안 된다 — 백엔드 기준이 바뀌었을 때
 * 화면만 다른 값을 말하게 된다.
 */
export function bandOf(metric: GradeMetric, grade: Grade): GradeBand | undefined {
  return GRADE_BANDS[metric].find((band) => band.grade === grade);
}

/** "70 ~ 85%" */
export function formatBandRange(band: GradeBand): string {
  return `${band.min} ~ ${band.max}%`;
}

// ---------------------------------------------------------------------------
// 반원 게이지 좌표
// ---------------------------------------------------------------------------

/** 반원이므로 0% 에서 100% 까지가 180도다. */
export const SEMICIRCLE_DEGREES = 180;

export function clampPercent(value: number): number {
  return Math.min(100, Math.max(0, value));
}

/**
 * 0~100 을 반원 위의 각도로. **9시 방향이 0도, 3시 방향이 180도**다.
 *
 * 범위 밖 값은 잘라낸다. 그러지 않으면 바늘이 반원을 벗어나 아래쪽을 가리킨다.
 */
export function valueToAngle(value: number): number {
  return (clampPercent(value) / 100) * SEMICIRCLE_DEGREES;
}

export type Point = { x: number; y: number };

/**
 * 반원 위의 점. `angle` 은 9시 방향에서 위를 거쳐 잰 각도(도)다.
 *
 * SVG 는 y 가 아래로 증가하므로 위로 올리려면 빼야 한다.
 */
export function polarPoint(
  cx: number,
  cy: number,
  radius: number,
  angle: number,
): Point {
  const radians = ((SEMICIRCLE_DEGREES - angle) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(radians),
    y: cy - radius * Math.sin(radians),
  };
}

/**
 * 구간 하나의 호 경로(`d` 속성).
 *
 * `gap` 만큼 양쪽에서 깎아 구간 사이를 띄운다. 구간이 간격보다 좁으면
 * 빈 문자열을 돌려준다 — 억지로 그리면 옆 구간을 침범한다.
 */
export function bandArcPath(
  band: GradeBand,
  cx: number,
  cy: number,
  radius: number,
  gap: number,
): string {
  const start = valueToAngle(band.min) + gap / 2;
  const end = valueToAngle(band.max) - gap / 2;
  if (end <= start) {
    return "";
  }

  const from = polarPoint(cx, cy, radius, start);
  const to = polarPoint(cx, cy, radius, end);
  // 각 구간은 180도 미만이라 large-arc-flag 는 항상 0.
  // sweep-flag 1 = 화면 기준 시계 방향(9시 -> 위 -> 3시).
  return `M ${from.x} ${from.y} A ${radius} ${radius} 0 0 1 ${to.x} ${to.y}`;
}
