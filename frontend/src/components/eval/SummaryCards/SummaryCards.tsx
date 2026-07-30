import type { EvaluationSummary } from "@/lib/types";

import styles from "./SummaryCards.module.css";

/**
 * 요약 지표 카드 5장.
 *
 * 시안은 6장이었다. 이모지 얼굴 "평가 상태" 카드는 뺐다 — 등급은 GaugeRing 이
 * 이미 표현하므로 의미가 겹친다 (docs/contract.md §5, prompts.md §9-1 #2).
 *
 * **델타 뱃지가 없다** (Phase 12). 무상태 전환으로 `previous` 가 계약에서
 * 사라졌다 — 비교할 이전 평가가 없다 (contract.md §0).
 *
 * 서버 컴포넌트다. 상태도 이벤트도 없다.
 */

// ---------------------------------------------------------------------------
// 숫자 표기
// ---------------------------------------------------------------------------

/** 개수. 정수 그대로. 자릿수 구분 기호를 넣지 않는다 — 계약 값을 그대로 보인다. */
function formatCount(value: number): string {
  return String(value);
}

/**
 * 비율. 계약이 0~100 실수이므로 소수 첫째자리까지 고정한다.
 * 61.0 을 "61" 로 줄이지 않고, 100 을 "100.0" 으로 쓴다.
 */
function formatPercent(value: number): string {
  return value.toFixed(1);
}

// ---------------------------------------------------------------------------
// 컴포넌트
// ---------------------------------------------------------------------------

/** 카드 식별자. omit 으로 특정 카드를 뺄 때 이 키로 지정한다. */
export type SummaryCardKey =
  | "totalQuestions"
  | "top1Accuracy"
  | "top3Accuracy"
  | "top1FailCount"
  | "top3FailCount";

export type SummaryCardsProps = {
  summary: EvaluationSummary;
  /**
   * 렌더에서 뺄 카드. 예: GaugeRing 이 Top-3 인식률을 이미 보여줄 때
   * `["top3Accuracy"]` 로 중복을 없앤다. 뺀 자리는 남기지 않고 나머지가
   * flex 로 폭을 균등 분배한다.
   */
  omit?: SummaryCardKey[];
};

export default function SummaryCards({ summary, omit = [] }: SummaryCardsProps) {
  const cards: { key: SummaryCardKey; accent: string; label: string; value: string; unit: string }[] =
    [
      { key: "totalQuestions", accent: styles.accentSky, label: "총 질문 수", value: formatCount(summary.totalQuestions), unit: "개" },
      { key: "top1Accuracy", accent: styles.accentViolet, label: "Top-1 정확도", value: formatPercent(summary.top1Accuracy), unit: "%" },
      { key: "top3Accuracy", accent: styles.accentGreen, label: "Top-3 인식률", value: formatPercent(summary.top3Accuracy), unit: "%" },
      { key: "top1FailCount", accent: styles.accentRed, label: "Top-1 실패", value: formatCount(summary.top1FailCount), unit: "건" },
      { key: "top3FailCount", accent: styles.accentAmber, label: "Top-3 실패", value: formatCount(summary.top3FailCount), unit: "건" },
    ];

  const visible = cards.filter((c) => !omit.includes(c.key));

  return (
    <ul className={styles.grid}>
      {visible.map((c, index) => (
        <Card
          key={c.key}
          accent={c.accent}
          label={c.label}
          value={c.value}
          unit={c.unit}
          // 순차 등장용. omit 으로 카드를 뺀 뒤의 **보이는 순서**다 —
          // cards 배열의 위치를 쓰면 뺀 자리에서 stagger 가 끊긴다.
          index={index}
        />
      ))}
    </ul>
  );
}

function Card({
  accent,
  label,
  value,
  unit,
  index,
}: {
  accent: string;
  label: string;
  value: string;
  unit: string;
  index: number;
}) {
  return (
    <li
      className={`${styles.card} ${accent}`}
      style={{ "--card-index": index } as React.CSSProperties}
    >
      <span className={styles.label}>{label}</span>
      <span className={styles.figure}>
        <span className={`${styles.number} tabular`}>{value}</span>
        <span className={styles.unit}>{unit}</span>
      </span>
    </li>
  );
}
