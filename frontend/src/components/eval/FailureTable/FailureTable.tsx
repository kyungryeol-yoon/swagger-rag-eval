"use client";

import { Check, X } from "lucide-react";
import { useState } from "react";

import { failureCategoryLabel } from "@/lib/enumTokens";
import { hasMultipleMethods, httpMethodColor } from "@/lib/httpMethod";
import type {
  EvaluationSummary,
  ExpectedApi,
  FailureCategory,
  FailureScope,
  QuestionResult,
  SearchResult,
} from "@/lib/types";

import styles from "./FailureTable.module.css";

/**
 * 문항별 평가 결과 표 — 100문항 전체 (Phase 7c).
 *
 * **더 이상 "실패만" 받지 않는다.** 성공 문항까지 포함한 `questions` 전체를
 * 받아, 어디까지 성공했는지(failureScope)를 셀에서 나눈다. 평가 대상은
 * 실패 22건이 아니라 문항 100개다 (contract.md §2).
 *
 * 정렬·필터·펼침 상태가 필요해 클라이언트 컴포넌트다. 다만 **상단 요약 수치는
 * 여기서 세지 않는다** — 100문항을 스캔해 실패 건수를 다시 계산하면 백엔드가
 * 확정한 summary 와 어긋날 수 있다. summary prop 을 그대로 읽는다.
 *
 * 정렬은 계약이 이미 해서 내려준다: TOP3 → TOP1_ONLY → NONE, 그 안에서 no
 * 오름차순 (contract.md §2). 여기서 다시 정렬하지 않는다 — grade 처럼, 백엔드가
 * 확정한 순서를 신뢰한다. 필터는 그 순서를 보존한다.
 */

/** 기본으로 펼쳐 보이는 행 수. 나머지는 "전체 보기" 로 넘긴다. */
const VISIBLE_COUNT = 5;

/** 실패 구분 필터의 선택 상태. "ALL" 은 전체(필터 없음). */
type ScopeFilter = FailureScope | "ALL";
/** 원인별 필터의 선택 상태. "ALL" 은 전체(필터 없음). */
type CategoryFilter = FailureCategory | "ALL";

/**
 * failureScope → 뱃지 문구·색.
 *
 * TOP3 는 완전 실패라 red, TOP1_ONLY 는 Top-3 안엔 있어 "먼저 손댈" 후보라 amber,
 * NONE(성공)은 **중립색**이다. 성공에 초록을 주면 표가 초록으로 뒤덮여 정작
 * 눈에 띄어야 할 실패가 묻힌다. 성공은 조용해야 한다.
 */
const SCOPE_BADGE: Record<FailureScope, { label: string; className: string }> = {
  TOP3: { label: "Top-3 실패", className: styles.scopeTop3 },
  TOP1_ONLY: { label: "Top-1 실패", className: styles.scopeTop1 },
  NONE: { label: "성공", className: styles.scopeNone },
};

/** 실패 구분 필터 칩의 순서·라벨. 정렬 방향(실패 먼저)과 같은 순서로 둔다. */
const SCOPE_CHIPS: { value: ScopeFilter; label: string }[] = [
  { value: "ALL", label: "전체" },
  { value: "TOP3", label: "Top-3 실패" },
  { value: "TOP1_ONLY", label: "Top-1 실패" },
  { value: "NONE", label: "성공" },
];

export type FailureTableProps = {
  /** 문항 100개 전체(성공 포함). 계약 순서 그대로 넘겨받는다. */
  questions: QuestionResult[];
  /** 백엔드가 확정한 요약. 상단 건수는 이 값만 쓴다 — 여기서 다시 세지 않는다. */
  summary: EvaluationSummary;
};

export default function FailureTable({ questions, summary }: FailureTableProps) {
  const [scope, setScope] = useState<ScopeFilter>("ALL");
  const [category, setCategory] = useState<CategoryFilter>("ALL");
  const [expanded, setExpanded] = useState(false);

  if (questions.length === 0) {
    return (
      <div className={styles.empty}>
        <p className={styles.emptyTitle}>표시할 문항이 없습니다</p>
        <p className={styles.emptyBody}>이 평가에는 문항이 담겨 있지 않습니다.</p>
      </div>
    );
  }

  // 메서드가 한 종류뿐이면(SELECT 전용 DAC 등) 뱃지가 정보를 주지 못한다
  // (open-questions #50). 필터와 무관하게 전체 기준으로 한 번만 판단해,
  // 필터를 바꿔도 뱃지 유무가 흔들리지 않게 한다.
  const allMethods = questions.flatMap((q) => [q.expected, q.top1, ...q.top3]);
  const showMethod = hasMultipleMethods(allMethods);

  // 원인별 칩에 붙일 건수. 전체 문항 기준(필터와 독립)이라 칩이 흔들리지 않는다.
  const categoryCounts = new Map<FailureCategory, number>();
  for (const q of questions) {
    if (q.failureCategory) {
      categoryCounts.set(q.failureCategory, (categoryCounts.get(q.failureCategory) ?? 0) + 1);
    }
  }
  // enum 정의 순서를 따르되 실제 등장한 원인만 칩으로 만든다.
  const presentCategories = (
    Object.keys(failureCategoryLabel) as FailureCategory[]
  ).filter((c) => categoryCounts.has(c));

  // 두 필터는 AND 로 겹친다. 계약 순서를 보존하려 filter 만 쓴다(정렬 안 함).
  const filtered = questions.filter((q) => {
    if (scope !== "ALL" && q.failureScope !== scope) {
      return false;
    }
    if (category !== "ALL" && q.failureCategory !== category) {
      return false;
    }
    return true;
  });

  const visible = expanded ? filtered : filtered.slice(0, VISIBLE_COUNT);
  const hidden = filtered.length - visible.length;
  const hasMore = filtered.length > VISIBLE_COUNT;

  return (
    <div className={styles.root}>
      {/* 상단 요약 — summary prop 그대로. 여기서 questions 를 세지 않는다. */}
      <p className={styles.summaryLine}>
        전체 <span className="tabular">{summary.totalQuestions}</span>문항 중{" "}
        <span className={styles.summaryFail}>
          Top-3 실패 <span className="tabular">{summary.top3FailCount}</span>건
        </span>
        <span className={styles.summarySep} aria-hidden="true">
          ·
        </span>
        <span className={styles.summaryWarn}>
          Top-1 실패 <span className="tabular">{summary.top1FailCount}</span>건
        </span>
      </p>

      {/* 필터 — 클라이언트 상태로만. URL 파라미터는 아직 쓰지 않는다. */}
      <div className={styles.filters}>
        <div className={styles.filterGroup} role="group" aria-label="실패 구분 필터">
          {SCOPE_CHIPS.map((chip) => {
            const count =
              chip.value === "ALL"
                ? questions.length
                : questions.filter((q) => q.failureScope === chip.value).length;
            return (
              <button
                key={chip.value}
                type="button"
                className={`${styles.chip} ${scope === chip.value ? styles.chipActive : ""}`}
                aria-pressed={scope === chip.value}
                onClick={() => setScope(chip.value)}
              >
                {chip.label}
                <span className={`${styles.chipCount} tabular`}>{count}</span>
              </button>
            );
          })}
        </div>

        {presentCategories.length > 0 && (
          <div className={styles.filterGroup} role="group" aria-label="원인별 필터">
            <button
              type="button"
              className={`${styles.chip} ${category === "ALL" ? styles.chipActive : ""}`}
              aria-pressed={category === "ALL"}
              onClick={() => setCategory("ALL")}
            >
              전체 원인
            </button>
            {presentCategories.map((cat) => (
              <button
                key={cat}
                type="button"
                className={`${styles.chip} ${category === cat ? styles.chipActive : ""}`}
                aria-pressed={category === cat}
                onClick={() => setCategory(cat)}
              >
                {failureCategoryLabel[cat]}
                <span className={`${styles.chipCount} tabular`}>{categoryCounts.get(cat)}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/*
        펼치면 표 영역에 스크롤을 걸고 thead 를 sticky 로 고정한다.
        100행을 한 번에 문서 흐름에 풀면 스크롤 중 헤더가 사라져 어느 열인지
        놓친다. 가상 스크롤은 쓰지 않는다 — 100행은 브라우저가 감당한다.

        display 를 카드형으로 바꾸면 표 시맨틱을 잃으므로 role 을 명시해둔다.
      */}
      <div className={`${styles.scrollArea} ${expanded ? styles.scrollAreaScroll : ""}`}>
        <table className={styles.table} role="table">
          <caption className="srOnly">
            문항별 평가 결과. 전체 {summary.totalQuestions}문항 중 {filtered.length}건 표시.
          </caption>
          <thead role="rowgroup">
            <tr role="row">
              <th role="columnheader" scope="col" className={styles.colNo}>
                No
              </th>
              <th role="columnheader" scope="col" className={styles.colQuestion}>
                질문
              </th>
              <th role="columnheader" scope="col" className={styles.colExpected}>
                기대 쿼리
              </th>
              <th role="columnheader" scope="col" className={styles.colTop3}>
                Top-3 검색 결과
              </th>
              <th role="columnheader" scope="col" className={styles.colHit}>
                Hit 여부
              </th>
              <th role="columnheader" scope="col" className={styles.colScope}>
                실패 구분
              </th>
              <th role="columnheader" scope="col" className={styles.colReason}>
                추정 원인
              </th>
            </tr>
          </thead>
          <tbody role="rowgroup">
            {visible.length === 0 ? (
              <tr role="row">
                <td role="cell" colSpan={7} className={styles.noMatch}>
                  선택한 필터에 해당하는 문항이 없습니다.
                </td>
              </tr>
            ) : (
              visible.map((q) => <Row key={q.no} question={q} showMethod={showMethod} />)
            )}
          </tbody>
        </table>
      </div>

      {(hasMore || expanded) && (
        <div className={styles.footer}>
          <button
            type="button"
            className={styles.moreButton}
            aria-expanded={expanded}
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? "접기" : `전체 ${filtered.length}건 보기`}
          </button>
          {!expanded && (
            <span className={styles.footerNote}>
              {visible.length}건 표시 중 · {hidden}건 더 있음
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function Row({ question, showMethod }: { question: QuestionResult; showMethod: boolean }) {
  const scope = SCOPE_BADGE[question.failureScope];

  return (
    <tr role="row" className={styles.row}>
      <td role="cell" data-label="No" className={styles.cellNo}>
        <span className="tabular">{question.no}</span>
      </td>

      <td role="cell" data-label="질문" className={styles.cellQuestion}>
        <p className={styles.question}>&ldquo;{question.question}&rdquo;</p>
      </td>

      <td role="cell" data-label="기대 쿼리" className={styles.cellExpected}>
        <Endpoint api={question.expected} showMethod={showMethod} />
      </td>

      <td role="cell" data-label="Top-3 검색 결과" className={styles.cellTop3}>
        <ol className={styles.results}>
          {question.top3.map((result) => (
            <ResultRow key={result.rank} result={result} showMethod={showMethod} />
          ))}
        </ol>
        <p className={styles.expectedRank}>
          {question.expectedRank == null
            ? "기대 쿼리: 순위 밖"
            : `${question.expectedRank}위 (기대 쿼리 위치)`}
        </p>
      </td>

      <td role="cell" data-label="Hit 여부" className={styles.cellHit}>
        {/* 두 지표를 한 셀에. 색(초록/빨강)에만 기대지 않고 아이콘 모양(✓/✗)과
            "Top-1/Top-3" 텍스트 + 스크린리더용 성공/실패로도 읽히게 한다. */}
        <div className={styles.hit}>
          <HitFlag label="Top-1" hit={question.top1Hit} />
          <HitFlag label="Top-3" hit={question.top3Hit} />
        </div>
      </td>

      <td role="cell" data-label="실패 구분" className={styles.cellScope}>
        <span className={`${styles.scope} ${scope.className}`}>{scope.label}</span>
      </td>

      <td role="cell" data-label="추정 원인" className={styles.cellReason}>
        {question.reason ? (
          <p className={styles.reason}>{question.reason}</p>
        ) : (
          // 성공 문항은 원인이 없다. 빈 셀 대신 대시를 둬 "없음" 을 명시한다.
          <span className={styles.reasonEmpty} aria-label="원인 없음">
            —
          </span>
        )}
      </td>
    </tr>
  );
}

function HitFlag({ label, hit }: { label: string; hit: boolean }) {
  const Icon = hit ? Check : X;
  return (
    <span className={`${styles.hitFlag} ${hit ? styles.hitYes : styles.hitNo}`}>
      <Icon size={13} strokeWidth={2.75} aria-hidden="true" />
      <span className={styles.hitLabel}>{label}</span>
      <span className="srOnly">{hit ? "성공" : "실패"}</span>
    </span>
  );
}

function Endpoint({ api, showMethod }: { api: ExpectedApi; showMethod: boolean }) {
  return (
    <span className={styles.endpoint}>
      {showMethod && <MethodBadge method={api.method} />}
      <code className={`${styles.path} pathText tabular`} title={api.path}>
        {api.path}
      </code>
    </span>
  );
}

function ResultRow({ result, showMethod }: { result: SearchResult; showMethod: boolean }) {
  return (
    <li className={styles.result}>
      <span className={`${styles.rank} tabular`} aria-hidden="true">
        {result.rank}
      </span>
      <span className="srOnly">{result.rank}위</span>
      {showMethod && <MethodBadge method={result.method} />}
      <code className={`${styles.path} pathText tabular`} title={result.path}>
        {result.path}
      </code>
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
