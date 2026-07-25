import { gradeColor } from "@/lib/enumTokens";
import { hasMultipleMethods, httpMethodColor } from "@/lib/httpMethod";
import type { QueryStat, TargetApp } from "@/lib/types";

import styles from "./AppInfoCard.module.css";

/**
 * 평가 대상 정보 카드 — 행1 좌상단 (담당자 요청).
 *
 * "어느 API/앱을 평가했는가" 를 한 카드에 담는다. 상단에 앱 식별(이름·appId·버전),
 * 하단 접이식에 이 앱에 속한 쿼리 경로 목록을 둔다 — "어느 path API 인지" 가
 * 개별 쿼리 단위 요구였어도 여기서 커버된다.
 *
 * **큰 점수는 넣지 않는다** (그건 GaugeRing / SummaryCards). 다만 목록에는 쿼리별
 * Top-3 인식률을 미니로 붙여 어느 경로가 약한지 바로 보이게 한다.
 *
 * 서버 컴포넌트.
 */

const formatPercent = (v: number) => `${v.toFixed(1)}%`;

export type AppInfoCardProps = {
  target: TargetApp;
  /** 이 앱에 속한 쿼리들. 접이식 경로 목록에 쓴다. */
  queries: QueryStat[];
};

export default function AppInfoCard({ target, queries }: AppInfoCardProps) {
  // 메서드가 한 종류뿐이면 뱃지가 정보를 주지 못한다 (open-questions #50).
  const showMethod = hasMultipleMethods(queries);

  return (
    <section className={styles.card} aria-label="평가 대상 정보">
      <div className={styles.head}>
        <span className={styles.appName}>{target.appName}</span>
        <code className={`${styles.appId} tabular`}>{target.appId}</code>
        <span className={styles.version}>{target.specVersion}</span>
      </div>

      <dl className={styles.meta}>
        <div className={styles.metaItem}>
          <dt className="srOnly">쿼리 수</dt>
          <dd>
            쿼리 <span className="tabular">{target.queryCount}</span>개
          </dd>
        </div>
        {target.owner && (
          <div className={styles.metaItem}>
            <dt className="srOnly">담당</dt>
            <dd>{target.owner}</dd>
          </div>
        )}
      </dl>

      {/* 이 앱의 쿼리 경로 목록. 기본 접힘 — 대상 식별이 먼저고 경로는 필요할 때만. */}
      <details className={styles.queries}>
        <summary className={styles.summary}>
          쿼리 <span className="tabular">{target.queryCount}</span>개 보기
        </summary>
        <ul className={styles.list}>
          {queries.map((q) => (
            <li key={`${q.method} ${q.path}`} className={styles.row}>
              {showMethod && (
                <span
                  className={styles.method}
                  style={{ "--method-color": httpMethodColor(q.method) } as React.CSSProperties}
                >
                  {q.method}
                </span>
              )}
              <code className={`${styles.path} pathText tabular`} title={q.path}>
                {q.path}
              </code>
              <span
                className={`${styles.acc} tabular`}
                style={{ color: gradeColor(q.grade) }}
                title="Top-3 인식률"
              >
                {formatPercent(q.top3Accuracy)}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
