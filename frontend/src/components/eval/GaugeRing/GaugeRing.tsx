import { gradeColor, gradeLabel } from "@/lib/enumTokens";
import type { Grade } from "@/lib/types";

import styles from "./GaugeRing.module.css";

/**
 * 인식률 게이지.
 *
 * 시안은 78% 를 우상단 링·게이지·등급표 세 곳에 중복 표시했다.
 * 이 컴포넌트 **하나로 대체한다** (docs/prompts.md §9-1).
 *
 * 순수 SVG 다. 차트 라이브러리를 쓰지 않는다.
 * 서버 컴포넌트다 — 상태도 이벤트도 없으므로 'use client' 가 필요 없다.
 */

/** 링 두께. 지름 대비 비율이라 size 를 바꿔도 인상이 유지된다. */
const STROKE_RATIO = 0.1;

export type GaugeRingProps = {
  /** 0~100 실수. 범위 밖은 잘라낸다. */
  value: number;
  /** 링 색과 등급 라벨을 결정한다. */
  grade: Grade;
  /** 지름(px). 링 두께와 글자 크기가 여기서 파생된다. */
  size?: number;
  /** 링 아래 캡션이자 스크린 리더가 읽는 접두사. */
  label?: string;
};

export default function GaugeRing({
  value,
  grade,
  size = 96,
  label = "Top-3 인식률",
}: GaugeRingProps) {
  // 계약상 0~100 이지만 방어한다. 범위를 벗어난 값이 오면
  // dashoffset 이 음수가 되면서 링이 반대로 그려진다.
  const clamped = Math.min(100, Math.max(0, value));
  const display = clamped.toFixed(1);

  const strokeWidth = size * STROKE_RATIO;
  const radius = (size - strokeWidth) / 2;
  const center = size / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - clamped / 100);

  // 캡션을 끈 경우(label="") 앞에 공백이 붙지 않게 한다.
  const summary = `${display}%, ${gradeLabel[grade]}`;
  const ariaLabel = label ? `${label} ${summary}` : summary;

  return (
    <div
      className={styles.root}
      // 링과 숫자는 하나의 그림이다. 조각조각 읽히면 오히려 알아듣기 어렵다.
      role="img"
      aria-label={ariaLabel}
      style={
        {
          "--gauge-size": `${size}px`,
          // 링을 그려 나가는 애니메이션의 **시작값**이다 (= 아무것도 안 그린 상태).
          // 도착값은 아래 stroke-dashoffset 속성이므로 CSS 에 적지 않는다.
          "--gauge-circumference": circumference,
        } as React.CSSProperties
      }
    >
      <div className={styles.ring}>
        <svg
          className={styles.svg}
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          aria-hidden="true"
          focusable="false"
        >
          <circle
            className={styles.track}
            cx={center}
            cy={center}
            r={radius}
            strokeWidth={strokeWidth}
          />
          {/* 0% 에서는 진행 링을 그리지 않는다. stroke-linecap: round 때문에
              길이가 0 이어도 점 하나가 남는 브라우저가 있다. */}
          {clamped > 0 && (
            <circle
              className={styles.progress}
              cx={center}
              cy={center}
              r={radius}
              strokeWidth={strokeWidth}
              stroke={gradeColor(grade)}
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
            />
          )}
        </svg>

        <div className={styles.center} aria-hidden="true">
          <span className={`${styles.value} tabular`}>
            {display}
            <span className={styles.unit}>%</span>
          </span>
          <span className={styles.grade} style={{ color: gradeColor(grade) }}>
            {gradeLabel[grade]}
          </span>
        </div>
      </div>

      {label && (
        <span className={styles.caption} aria-hidden="true">
          {label}
        </span>
      )}
    </div>
  );
}
