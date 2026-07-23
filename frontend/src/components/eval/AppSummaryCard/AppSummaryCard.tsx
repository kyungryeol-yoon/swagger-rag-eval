import type { TargetApp } from "@/lib/types";

import styles from "./AppSummaryCard.module.css";

/**
 * 평가 대상 앱 메타 카드 — 시안의 "평가 대상 API" 자리.
 *
 * **수치를 넣지 않는다.** 점수는 GaugeRing 과 SummaryCards 가 말한다.
 * 여기는 "무엇을 평가했는가"(어느 앱, 몇 개 쿼리, 어느 버전)만 낮은 높이로
 * 보여준다 (contract.md §0).
 *
 * 서버 컴포넌트.
 */

export type AppSummaryCardProps = {
  target: TargetApp;
};

export default function AppSummaryCard({ target }: AppSummaryCardProps) {
  return (
    <section className={styles.card} aria-label="평가 대상 앱">
      <div className={styles.identity}>
        <span className={styles.appName}>{target.appName}</span>
        <code className={`${styles.appId} tabular`}>{target.appId}</code>
      </div>

      <dl className={styles.meta}>
        <div className={styles.metaItem}>
          <dt className="srOnly">명세 버전</dt>
          <dd className={styles.version}>{target.specVersion}</dd>
        </div>
        <div className={styles.metaItem}>
          <dt className="srOnly">쿼리 수</dt>
          <dd className={styles.metaValue}>
            쿼리 <span className="tabular">{target.queryCount}</span>개
          </dd>
        </div>
        {target.owner && (
          <div className={styles.metaItem}>
            <dt className="srOnly">담당</dt>
            <dd className={styles.metaValue}>{target.owner}</dd>
          </div>
        )}
      </dl>
    </section>
  );
}
