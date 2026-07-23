import { priorityColor, priorityLabel } from "@/lib/enumTokens";
import type { Recommendation } from "@/lib/types";

import styles from "./RecommendationCards.module.css";

/**
 * 권장 조치 카드.
 *
 * 시안의 "개선 추천" 은 "권장 조치" 로 바꿨다 (docs/prompts.md §9-2).
 *
 * 서버 컴포넌트. 항목이 없으면 섹션 제목까지 포함해 아무것도 렌더하지 않는다 —
 * 조치가 없는데 "권장 조치" 라는 빈 제목만 남으면 무언가 빠진 것처럼 보인다.
 */

/** 순번은 2자리로 맞춘다. "1" 과 "10" 이 섞이면 좌측 정렬이 흔들린다. */
function formatOrder(order: number): string {
  return String(order).padStart(2, "0");
}

const formatPercent = (value: number) => value.toFixed(1);

export type RecommendationCardsProps = {
  recommendations: Recommendation[];
};

export default function RecommendationCards({
  recommendations,
}: RecommendationCardsProps) {
  if (recommendations.length === 0) {
    return null;
  }

  return (
    <section className={styles.root}>
      <header className={styles.header}>
        <h2 className={styles.title}>권장 조치</h2>
        <span className={styles.caption}>실패 원인 기반 자동 분석</span>
      </header>

      <ul className={styles.grid}>
        {recommendations.map((item) => (
          <Card key={item.order} item={item} />
        ))}
      </ul>

      {/*
        합계를 계산해 보여주지 않는다. 시안의 "실패 원인 중 62%" 같은 문구는
        근거 없는 임의 합산이었다 (contract.md §5 알려진 오류).
        대신 각 값이 왜 100 을 넘을 수 있는지만 상시로 밝힌다.
      */}
      <p className={styles.footnote}>
        * 원인이 중복 집계되어 합계가 100%를 넘을 수 있습니다
      </p>
    </section>
  );
}

function Card({ item }: { item: Recommendation }) {
  const color = priorityColor(item.priority);
  // 막대는 0~100 안에서만 그린다. 계약상 범위 안이지만 넘치면 카드를 뚫는다.
  const width = Math.min(100, Math.max(0, item.failShare));

  return (
    <li
      className={styles.card}
      style={{ "--priority-color": color } as React.CSSProperties}
    >
      <div className={styles.cardHead}>
        <span className={`${styles.order} tabular`} aria-hidden="true">
          {formatOrder(item.order)}
        </span>
        <span className={styles.pill}>{priorityLabel[item.priority]}</span>
      </div>

      <h3 className={styles.cardTitle}>{item.title}</h3>
      <p className={styles.cardBody}>{item.description}</p>

      {/*
        margin-top: auto 로 하단부를 바닥에 붙인다. description 길이가 달라도
        카드끼리 막대 높이가 맞는다 — 어긋나면 비중을 눈으로 비교할 수 없다.
      */}
      <div className={styles.footer}>
        <div className={styles.footerRow}>
          <span className={styles.footerLabel}>관련 실패 비중</span>
          <span className={`${styles.footerValue} tabular`}>
            {formatPercent(item.failShare)}%
          </span>
        </div>
        <span className={styles.track}>
          <span className={styles.fill} style={{ width: `${width}%` }} />
        </span>
      </div>
    </li>
  );
}
