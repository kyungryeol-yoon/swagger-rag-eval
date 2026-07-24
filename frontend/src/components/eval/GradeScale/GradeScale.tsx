import { gradeColor, gradeLabel } from "@/lib/enumTokens";
import {
  GRADE_BANDS,
  bandArcPath,
  bandOf,
  clampPercent,
  formatBandRange,
  polarPoint,
  valueToAngle,
} from "@/lib/gradeBands";
import type { GradeMetric } from "@/lib/gradeBands";
import type { Grade } from "@/lib/types";

import styles from "./GradeScale.module.css";

/**
 * 등급 구간 반원 게이지 — 시안의 "평가 기준" 카드.
 *
 * **`GaugeRing` 과 역할이 다르다.**
 *   GaugeRing  = 얼마인가        "78.0%"
 *   GradeScale = 어느 구간인가   "개선 필요 / 70~85%"
 *
 * 그래서 여기에는 **큰 수치를 넣지 않는다.** 78% 가 화면에서 반복되는 것을
 * 막는 것이 이 분리의 목적이다 (contract.md §5, prompts.md §9-1 #1).
 *
 * 순수 SVG. 서버 컴포넌트.
 */

/** 구간 사이 간격(도). */
const GAP_DEGREES = 1.5;

/** 지름 대비 호 두께. */
const STROKE_RATIO = 0.075;

/** 지표별 라벨 접두사. Top-1 은 "정확도", Top-3 은 "인식률". */
const METRIC_LABEL: Record<GradeMetric, string> = {
  top1: "Top-1 정확도",
  top3: "Top-3 인식률",
};

export type GradeScaleProps = {
  /**
   * 어느 지표인지. 기본값을 두지 않는다 — 호출부가 top1/top3 를 명시해야
   * 등급 구간(GRADE_BANDS[metric])과 라벨이 그 지표 것으로 맞는다.
   */
  metric: GradeMetric;
  /** 0~100. 바늘 위치에만 쓴다. 범위 밖은 잘라낸다. */
  value: number;
  /** 백엔드가 확정한 등급. value 로부터 다시 계산하지 않는다. */
  grade: Grade;
  /** 반원의 지름(px). */
  size?: number;
};

export default function GradeScale({ metric, value, grade, size = 180 }: GradeScaleProps) {
  const clamped = clampPercent(value);
  const bands = GRADE_BANDS[metric];

  const stroke = size * STROKE_RATIO;
  const radius = size / 2 - stroke / 2;
  const cx = size / 2;
  const cy = size / 2;
  // 중심 아래로 허브가 조금 나온다. 그만큼 높이를 더 준다.
  const svgHeight = size / 2 + stroke * 0.9;

  const needleAngle = valueToAngle(clamped);
  // 바늘 끝은 호 안쪽 모서리 조금 앞에서 멈춘다. 호를 덮으면 구간색이 가려진다.
  const needleTip = polarPoint(cx, cy, radius - stroke * 0.9, needleAngle);

  const band = bandOf(metric, grade);
  const rangeText = band ? formatBandRange(band) : null;

  // "Top-3 인식률 78.0%, 개선 필요 구간 (70 ~ 85%)"
  // 구간과 범위 사이에는 쉼표를 넣지 않는다. 읽을 때 끊기면 범위가 별개 항목처럼 들린다.
  const bandPhrase = rangeText
    ? `${gradeLabel[grade]} 구간 (${rangeText})`
    : `${gradeLabel[grade]} 구간`;
  const label = `${METRIC_LABEL[metric]} ${clamped.toFixed(1)}%, ${bandPhrase}`;

  return (
    <div className={styles.root} role="img" aria-label={label}>
      <div className={styles.gauge} style={{ width: size }}>
        <svg
          className={styles.svg}
          width={size}
          height={svgHeight}
          viewBox={`0 0 ${size} ${svgHeight}`}
          aria-hidden="true"
          focusable="false"
        >
          {bands.map((b) => {
            const d = bandArcPath(b, cx, cy, radius, GAP_DEGREES);
            if (!d) {
              return null;
            }
            return (
              <path
                key={b.grade}
                className={styles.band}
                d={d}
                strokeWidth={stroke}
                stroke={gradeColor(b.grade)}
              />
            );
          })}

          {/* 바늘은 --text 다. 구간색과 같은 계열이면 어느 구간을 가리키는지
              읽히지 않는다. */}
          <line
            className={styles.needle}
            x1={cx}
            y1={cy}
            x2={needleTip.x}
            y2={needleTip.y}
            strokeWidth={Math.max(2, stroke * 0.18)}
          />
          <circle className={styles.hub} cx={cx} cy={cy} r={stroke * 0.42} />
        </svg>

        <div className={styles.readout}>
          <span className={styles.gradeName} style={{ color: gradeColor(grade) }}>
            {gradeLabel[grade]}
          </span>
          {rangeText && <span className={`${styles.range} tabular`}>{rangeText}</span>}
        </div>
      </div>

      <ul className={styles.legend}>
        {bands.map((b) => {
          const current = b.grade === grade;
          return (
            <li
              key={b.grade}
              className={`${styles.legendRow} ${current ? styles.current : ""}`}
            >
              <span
                className={styles.swatch}
                style={{ background: gradeColor(b.grade) }}
                aria-hidden="true"
              />
              <span className={styles.legendName}>{gradeLabel[b.grade]}</span>
              <span className={`${styles.legendRange} tabular`}>
                {formatBandRange(b)}
              </span>
              {current && <span className={styles.badge}>현재</span>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
