import type { EvaluationSummary, PreviousEvaluation } from "@/lib/types";

import styles from "./SummaryCards.module.css";

/**
 * 요약 지표 카드 5장.
 *
 * 시안은 6장이었다. 이모지 얼굴 "평가 상태" 카드는 뺐다 — 등급은 GaugeRing 이
 * 이미 표현하므로 의미가 겹친다 (docs/contract.md §5, prompts.md §9-1 #2).
 *
 * 서버 컴포넌트다. 상태도 이벤트도 없다.
 */

// ---------------------------------------------------------------------------
// 델타 계산 — 순수 함수
// ---------------------------------------------------------------------------

export type DeltaDirection = "up" | "down" | "same";

export type Delta = {
  text: string;
  direction: DeltaDirection;
};

/**
 * 이전 평가 대비 변화량.
 *
 * **단위는 "p"(퍼센트포인트)다. "%" 가 아니다.**
 * 64% -> 78% 는 14 퍼센트포인트 상승이지 14% 상승이 아니다
 * (14% 상승이면 64 * 1.14 = 72.96 이 된다).
 * 이걸 "%" 로 적으면 개선 폭을 잘못 읽게 된다.
 *
 * 표시가 소수 첫째자리까지이므로 0.05 미만 차이는 같은 값으로 본다.
 * 그러지 않으면 -0.0001 이 "▼ -0.0p" 로 나온다.
 */
export function formatDelta(current: number, previous: number): Delta {
  const diff = current - previous;

  if (Math.abs(diff) < 0.05) {
    return { text: "— 0.0p", direction: "same" };
  }
  if (diff > 0) {
    return { text: `▲ +${diff.toFixed(1)}p`, direction: "up" };
  }
  return { text: `▼ ${diff.toFixed(1)}p`, direction: "down" };
}

const DIRECTION_WORD: Record<DeltaDirection, string> = {
  up: "상승",
  down: "하락",
  same: "변화 없음",
};

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

export type SummaryCardsProps = {
  summary: EvaluationSummary;
  previous?: PreviousEvaluation | null;
};

export default function SummaryCards({ summary, previous }: SummaryCardsProps) {
  const delta = previous ? formatDelta(summary.top3Accuracy, previous.top3Accuracy) : null;

  return (
    <ul className={styles.grid}>
      <Card
        accent={styles.accentSky}
        label="총 질문 수"
        value={formatCount(summary.totalQuestions)}
        unit="개"
      />
      <Card
        accent={styles.accentViolet}
        label="Top-1 정확도"
        value={formatPercent(summary.top1Accuracy)}
        unit="%"
      />
      <Card
        accent={styles.accentGreen}
        label="Top-3 인식률"
        value={formatPercent(summary.top3Accuracy)}
        unit="%"
      >
        {/* previous 가 없으면 뱃지를 아예 렌더하지 않는다.
            빈 자리를 남기면 카드 높이가 서로 어긋난다. */}
        {delta && previous && (
          <span
            className={`${styles.delta} ${styles[delta.direction]}`}
            role="img"
            aria-label={`이전 평가 ${previous.traceId} 대비 ${Math.abs(
              summary.top3Accuracy - previous.top3Accuracy,
            ).toFixed(1)} 퍼센트포인트 ${DIRECTION_WORD[delta.direction]}`}
          >
            <span className="tabular" aria-hidden="true">
              {delta.text}
            </span>
          </span>
        )}
      </Card>
      <Card
        accent={styles.accentRed}
        label="Top-1 실패"
        value={formatCount(summary.top1FailCount)}
        unit="건"
      />
      <Card
        accent={styles.accentAmber}
        label="Top-3 실패"
        value={formatCount(summary.top3FailCount)}
        unit="건"
      />
    </ul>
  );
}

function Card({
  accent,
  label,
  value,
  unit,
  children,
}: {
  accent: string;
  label: string;
  value: string;
  unit: string;
  children?: React.ReactNode;
}) {
  return (
    <li className={`${styles.card} ${accent}`}>
      <span className={styles.label}>{label}</span>
      <span className={styles.figure}>
        <span className={`${styles.number} tabular`}>{value}</span>
        <span className={styles.unit}>{unit}</span>
      </span>
      {children}
    </li>
  );
}
