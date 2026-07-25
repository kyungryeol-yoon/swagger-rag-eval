import {
  describeQuality,
  descriptionQualityColorVar,
  descriptionQualityLabel,
} from "@/lib/descriptionQuality";
import { gradeColor } from "@/lib/enumTokens";
import { hasMultipleMethods, httpMethodColor } from "@/lib/httpMethod";
import type { QueryStat } from "@/lib/types";

import styles from "./QueryQualityTable.module.css";

/**
 * 쿼리별 설명 품질과 인식률 표 — **이 화면의 실질 산출물**.
 *
 * 어느 쿼리의 설명을 고쳐야 하는지가 여기서 정해지고, 그 목록이 그대로
 * 재생성 요청 대상이 된다 (contract.md §2).
 *
 * 서버 컴포넌트다. 선택 체크박스는 아직 동작하지 않아(disabled) 클라이언트
 * 상태가 필요 없다. 자동 생성 서비스가 연동되면 그때 'use client' 로 올린다.
 */

export type QueryQualityTableProps = {
  queries: QueryStat[];
};

/**
 * 손봐야 할 것이 위로 온다.
 *   1. 재생성 필요(needsRegeneration)가 먼저
 *   2. 그 안에서 인식률 오름차순
 * 원본 배열은 건드리지 않는다.
 */
function sortForAction(queries: QueryStat[]): QueryStat[] {
  return [...queries].sort((a, b) => {
    if (a.needsRegeneration !== b.needsRegeneration) {
      return a.needsRegeneration ? -1 : 1;
    }
    return a.top3Accuracy - b.top3Accuracy;
  });
}

export default function QueryQualityTable({ queries }: QueryQualityTableProps) {
  const rows = sortForAction(queries);
  const showMethod = hasMultipleMethods(queries);
  const selectedCount = queries.filter((q) => q.needsRegeneration).length;

  const disabledTitle = "자동 생성 서비스 연동 후 활성화";

  return (
    <div className={styles.root}>
      <table className={styles.table} role="table">
        <caption className="srOnly">
          쿼리별 설명 품질과 Top-3 인식률. 재생성이 필요한 쿼리가 위에 온다.
        </caption>
        <thead role="rowgroup">
          <tr role="row">
            <th role="columnheader" scope="col" className={styles.colCheck}>
              <input
                type="checkbox"
                className={styles.checkbox}
                disabled
                aria-label="전체 선택"
                title={disabledTitle}
              />
            </th>
            <th role="columnheader" scope="col" className={styles.colQuery}>
              쿼리
            </th>
            <th role="columnheader" scope="col" className={styles.colQuality}>
              설명 품질
            </th>
            <th role="columnheader" scope="col" className={styles.colCount}>
              문항 수
            </th>
            <th role="columnheader" scope="col" className={styles.colAccuracy}>
              Top-3 인식률
            </th>
            <th role="columnheader" scope="col" className={styles.colRegen}>
              재생성 필요
            </th>
          </tr>
        </thead>
        <tbody role="rowgroup">
          {rows.map((query) => (
            <Row
              key={`${query.method} ${query.path}`}
              query={query}
              showMethod={showMethod}
              disabledTitle={disabledTitle}
            />
          ))}
        </tbody>
      </table>

      <div className={styles.footer}>
        <span className={styles.selected}>
          선택 <span className="tabular">{selectedCount}</span>건
        </span>
        <span className={styles.footerNote}>재생성이 필요한 쿼리가 기본 선택됩니다</span>
      </div>
    </div>
  );
}

function Row({
  query,
  showMethod,
  disabledTitle,
}: {
  query: QueryStat;
  showMethod: boolean;
  disabledTitle: string;
}) {
  const quality = describeQuality(query);
  const accuracy = Math.min(100, Math.max(0, query.top3Accuracy));

  return (
    <tr role="row" className={styles.row}>
      <td role="cell" className={styles.cellCheck}>
        <input
          type="checkbox"
          className={styles.checkbox}
          defaultChecked={query.needsRegeneration}
          disabled
          aria-label={`${query.path} 선택`}
          title={disabledTitle}
        />
      </td>

      <td role="cell" data-label="쿼리" className={styles.cellQuery}>
        <span className={styles.queryHead}>
          {showMethod && (
            <span
              className={styles.method}
              style={{ "--method-color": httpMethodColor(query.method) } as React.CSSProperties}
            >
              {query.method}
            </span>
          )}
          <code className={`${styles.path} pathText tabular`} title={query.path}>
            {query.path}
          </code>
        </span>
        {query.summary ? (
          <span className={styles.summary}>{query.summary}</span>
        ) : (
          <span className={styles.noSummary}>설명 없음</span>
        )}
      </td>

      <td role="cell" data-label="설명 품질" className={styles.cellQuality}>
        <span style={{ color: `var(${descriptionQualityColorVar[quality]})` }}>
          {descriptionQualityLabel[quality]}
        </span>
      </td>

      <td role="cell" data-label="문항 수" className={`${styles.cellCount} tabular`}>
        {query.questionCount}
      </td>

      <td role="cell" data-label="Top-3 인식률" className={styles.cellAccuracy}>
        <span className={styles.accuracyRow}>
          <span className={`${styles.accuracyValue} tabular`}>
            {query.top3Accuracy.toFixed(1)}%
          </span>
          <span className={styles.track}>
            {/* 색은 백엔드가 확정한 grade 를 따른다. 프론트가 인식률로
                등급을 재계산하지 않는다 (contract.md §3). */}
            <span
              className={styles.fill}
              style={{ width: `${accuracy}%`, background: gradeColor(query.grade) }}
            />
          </span>
        </span>
      </td>

      <td role="cell" data-label="재생성 필요" className={styles.cellRegen}>
        {query.needsRegeneration && <span className={styles.regenPill}>재생성 권장</span>}
      </td>
    </tr>
  );
}
