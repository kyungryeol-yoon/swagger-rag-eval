import { failureCategoryLabel } from "@/lib/enumTokens";
import { httpMethodColor } from "@/lib/httpMethod";
import type { ExpectedApi, Failure, SearchResult } from "@/lib/types";

import styles from "./FailureTable.module.css";

/**
 * 실패한 문항 표.
 *
 * 서버 컴포넌트다. 정렬·필터·페이징은 후속 단계 (prompts.md §9-5).
 *
 * 표시 개수는 기본 3건이고 나머지는 버튼으로 넘긴다. 버튼 문구는
 * **실제 실패 건수**를 쓴다 — 시안의 "나머지 97건 보기" 는 오류다.
 * 실패는 22건인데 97건이라고 적혀 있었다 (contract.md §5, prompts.md §9-1 #3).
 */

/** 기본으로 펼쳐 보이는 건수. 나머지는 "전체 보기" 로 넘긴다. */
const VISIBLE_COUNT = 3;

/**
 * "근접" 으로 볼 마지막 순위.
 *
 * topK 가 3 이므로 4~5 위는 **한두 칸 차이로 놓친 것**이다. 이 구간은
 * 설명을 조금만 보강해도 Top-3 안으로 들어올 가능성이 높아, 6위 이하나
 * 순위 밖과는 조치의 성격이 다르다. 그래서 pill 색을 red 가 아닌 amber 로
 * 나눠서 "먼저 손댈 것" 을 눈에 띄게 한다.
 *
 * 5 는 topK(3) + 2 다. 계약이 topK 를 바꿀 수 있게 되어 있으므로
 * (meta.topK), 나중에는 이 값도 topK 에서 파생시키는 편이 낫다.
 */
const NEAR_MISS_MAX_RANK = 5;

function isNearMiss(expectedRank: number | null | undefined): boolean {
  return (
    typeof expectedRank === "number" &&
    expectedRank > VISIBLE_COUNT &&
    expectedRank <= NEAR_MISS_MAX_RANK
  );
}

export type FailureTableProps = {
  failures: Failure[];
  /** 전체 실패 건수. 표에 보이는 수가 아니라 summary.top3FailCount 다. */
  totalFailCount: number;
};

export default function FailureTable({ failures, totalFailCount }: FailureTableProps) {
  if (failures.length === 0) {
    return (
      <div className={styles.empty}>
        <p className={styles.emptyTitle}>실패한 문항이 없습니다</p>
        <p className={styles.emptyBody}>
          모든 질문이 Top-3 안에서 기대 쿼리를 찾았습니다. 설명을 이대로 유지하세요.
        </p>
      </div>
    );
  }

  const visible = failures.slice(0, VISIBLE_COUNT);
  const hidden = Math.max(0, totalFailCount - visible.length);

  return (
    <div className={styles.root}>
      {/*
        display 를 카드형으로 바꾸면 브라우저가 표 시맨틱을 잃어버린다.
        역할을 명시해두면 좁은 화면에서도 스크린 리더가 표로 읽는다.
      */}
      <table className={styles.table} role="table">
        <caption className="srOnly">
          실패한 문항 목록. 전체 {totalFailCount}건 중 {visible.length}건 표시.
        </caption>
        <thead role="rowgroup">
          <tr role="row">
            <th role="columnheader" scope="col" className={styles.colQuestion}>
              질문
            </th>
            <th role="columnheader" scope="col" className={styles.colExpected}>
              기대 쿼리
            </th>
            <th role="columnheader" scope="col" className={styles.colResults}>
              Top-3 검색 결과
            </th>
            <th role="columnheader" scope="col" className={styles.colHit}>
              Hit 여부
            </th>
            <th role="columnheader" scope="col" className={styles.colCategory}>
              실패 구분
            </th>
            <th role="columnheader" scope="col" className={styles.colReason}>
              추정 원인
            </th>
          </tr>
        </thead>
        <tbody role="rowgroup">
          {visible.map((failure) => (
            <Row key={failure.id} failure={failure} />
          ))}
        </tbody>
      </table>

      <div className={styles.footer}>
        <button
          type="button"
          className={styles.moreButton}
          disabled
          title="필터·정렬과 함께 구현 예정"
        >
          실패 {totalFailCount}건 전체 보기
        </button>
        {hidden > 0 && (
          <span className={styles.footerNote}>
            {visible.length}건 표시 중 · {hidden}건 더 있음
          </span>
        )}
      </div>
    </div>
  );
}

function Row({ failure }: { failure: Failure }) {
  const near = isNearMiss(failure.expectedRank);

  return (
    <tr role="row" className={styles.row}>
      <td role="cell" data-label="질문" className={styles.cellQuestion}>
        <p className={styles.question}>&ldquo;{failure.question}&rdquo;</p>
      </td>

      <td role="cell" data-label="기대 쿼리" className={styles.cellExpected}>
        <Endpoint api={failure.expected} />
      </td>

      <td role="cell" data-label="Top-3 검색 결과" className={styles.cellResults}>
        <ol className={styles.results}>
          {failure.results.map((result) => (
            <ResultRow key={result.rank} result={result} />
          ))}
        </ol>
        <p className={styles.expectedRank}>
          {failure.expectedRank == null
            ? "기대 쿼리: 순위 밖"
            : `${failure.expectedRank}위 (기대 쿼리 위치)`}
        </p>
      </td>

      <td role="cell" data-label="Hit 여부" className={styles.cellHit}>
        {failure.hit ? (
          <span className={`${styles.pill} ${styles.hit}`}>HIT</span>
        ) : (
          <span className={`${styles.pill} ${near ? styles.nearMiss : styles.miss}`}>
            {near ? "MISS (근접)" : "MISS"}
          </span>
        )}
      </td>

      <td role="cell" data-label="실패 구분" className={styles.cellCategory}>
        <span className={styles.category}>
          {failureCategoryLabel[failure.failureCategory]}
        </span>
      </td>

      <td role="cell" data-label="추정 원인" className={styles.cellReason}>
        <p className={styles.reason}>{failure.reason}</p>
      </td>
    </tr>
  );
}

function Endpoint({ api }: { api: ExpectedApi }) {
  return (
    <span className={styles.endpoint}>
      <MethodBadge method={api.method} />
      <code className={`${styles.path} tabular`}>{api.path}</code>
    </span>
  );
}

function ResultRow({ result }: { result: SearchResult }) {
  return (
    <li className={styles.result}>
      <span className={`${styles.rank} tabular`} aria-hidden="true">
        {result.rank}
      </span>
      <span className="srOnly">{result.rank}위</span>
      <MethodBadge method={result.method} />
      <code className={`${styles.path} tabular`}>{result.path}</code>
      <span className={`${styles.score} tabular`}>{result.score.toFixed(3)}</span>
    </li>
  );
}

function MethodBadge({ method }: { method: string }) {
  return (
    <span
      className={styles.method}
      style={{ "--method-color": httpMethodColor(method) } as React.CSSProperties}
    >
      {method}
    </span>
  );
}
