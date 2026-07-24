import { notFound } from "next/navigation";

import FailureTable from "@/components/eval/FailureTable/FailureTable";
import GaugeRing from "@/components/eval/GaugeRing/GaugeRing";
import QuestionTypeChart from "@/components/eval/QuestionTypeChart/QuestionTypeChart";
import SummaryCards from "@/components/eval/SummaryCards/SummaryCards";
import { serverApiBase } from "@/lib/config";
import { searchModeLabel } from "@/lib/enumTokens";
import type { Evaluation } from "@/lib/types";

import styles from "./page.module.css";

/**
 * 평가 리포트 대시보드 — **임시 조립(Phase 6.5)**.
 *
 * 완성된 컴포넌트만 배치한다. TargetApiCard(6-3) / RecommendationCards(6-5) /
 * ActionPanel(6-7) 은 아직 없으므로 **자리를 비워둔다.**
 * "구현 예정" 플레이스홀더를 두면 화면 전체가 미완성으로 보인다 —
 * 없는 편이 낫다. Phase 7 정식 조립에서 채운다.
 *
 * 서버 컴포넌트다. 백엔드 주소는 lib/config 를 경유한다.
 */

async function getEvaluation(traceId: string): Promise<Evaluation> {
  // 평가 결과는 재실행마다 바뀐다. 캐시하면 재생성 후에도 옛 수치가 남는다.
  const res = await fetch(
    `${serverApiBase}/api/v1/evaluations/${encodeURIComponent(traceId)}`,
    { cache: "no-store" },
  );

  // 404 만 not-found 로 보낸다. 나머지 실패는 error.tsx 가 받아야
  // "백엔드가 떠 있는지" 를 안내할 수 있다.
  if (res.status === 404) {
    notFound();
  }
  if (!res.ok) {
    throw new Error(`평가 리포트를 불러오지 못했습니다 (HTTP ${res.status})`);
  }

  return (await res.json()) as Evaluation;
}

/**
 * ISO 문자열을 그대로 잘라 쓴다.
 *
 * `toLocaleString` 은 서버의 시간대를 타서, 응답에 담긴 오프셋(+09:00)과
 * 다른 시각이 찍힐 수 있다. 계약이 이미 오프셋을 포함해 내려주므로
 * 변환하지 않고 보이는 대로 쓴다.
 */
function formatDateTime(iso: string): string {
  return `${iso.slice(0, 10)} ${iso.slice(11, 16)}`;
}

function formatDuration(ms: number): string {
  if (ms < 60_000) {
    return `${(ms / 1000).toFixed(1)}초`;
  }
  const minutes = Math.floor(ms / 60_000);
  const seconds = Math.round((ms % 60_000) / 1000);
  return `${minutes}분 ${seconds}초`;
}

/**
 * 문항 출처 표기.
 *
 * `questionSource` 는 아직 enum 이 아니라 자유 문자열이다
 * (docs/open-questions.md #25). 확정되면 enumTokens 로 옮긴다.
 * 모르는 값은 그대로 보여준다 — 감추면 신뢰도 판단 근거가 사라진다.
 */
function formatQuestionSource(source: string): string {
  if (source === "LLM_GENERATED_HUMAN_REVIEWED") {
    return "LLM 생성 · 사람 검수";
  }
  return source;
}

export default async function EvaluationPage({
  params,
}: {
  params: Promise<{ traceId: string }>;
}) {
  const { traceId } = await params;
  const report = await getEvaluation(traceId);

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerMain}>
          <nav className={styles.breadcrumb} aria-label="위치">
            <span>SWAGGER-RAG-EVAL</span>
            <span className={styles.breadcrumbSep} aria-hidden="true">
              /
            </span>
            <span className={styles.breadcrumbCurrent}>SWAGGER SEARCH</span>
          </nav>
          <h1 className={styles.title}>RAG 검색 인식률 평가 리포트</h1>

          {/*
            평가 단위는 쿼리 하나가 아니라 DAC 앱 하나다 (contract.md §0).
            어느 앱의 몇 개 쿼리를 평가한 것인지가 제목 바로 아래에 있어야 한다.
            specVersion 은 재생성 전후를 구분하는 유일한 근거다 (§5).
          */}
          <p className={styles.subject}>
            <span className={styles.appName}>{report.target.appName}</span>
            <code className={`${styles.appId} tabular`}>{report.target.appId}</code>
            <span className={styles.subjectMeta}>
              쿼리 <span className="tabular">{report.target.queryCount}</span>개
            </span>
            <span className={styles.subjectMeta}>명세 {report.target.specVersion}</span>
            {report.target.owner && (
              <span className={styles.subjectMeta}>{report.target.owner}</span>
            )}
          </p>
        </div>

        <dl className={styles.headerMeta}>
          <div className={styles.metaItem}>
            <dt>평가일</dt>
            <dd className="tabular">{formatDateTime(report.evaluatedAt)}</dd>
          </div>
          <div className={styles.metaItem}>
            <dt>Trace ID</dt>
            <dd className="tabular">{report.traceId}</dd>
          </div>
          <div className={styles.metaItem}>
            <dt>모델</dt>
            <dd className="tabular">{report.meta.embeddingModel}</dd>
          </div>
          <div className={styles.metaItem}>
            <dt>검색</dt>
            <dd>
              {searchModeLabel[report.meta.searchMode]}, Top-{report.meta.topK}
            </dd>
          </div>
          <div className={styles.metaItem}>
            <dt>소요시간</dt>
            <dd className="tabular">{formatDuration(report.meta.durationMs)}</dd>
          </div>
          <div className={styles.metaItem}>
            <dt>문항</dt>
            <dd>{formatQuestionSource(report.meta.questionSource)}</dd>
          </div>
        </dl>
      </header>

      {/* 상단: 게이지 + 요약 카드 */}
      <section className={styles.hero} aria-label="요약">
        <div className={styles.gauge}>
          <GaugeRing
            value={report.summary.top3Accuracy}
            grade={report.summary.top3Grade}
            size={160}
          />
        </div>
        <div className={styles.cards}>
          <SummaryCards summary={report.summary} previous={report.previous} />
        </div>
      </section>

      {/* 중단: 유형별 분포와 인식률 */}
      <section aria-label="문항 유형">
        <QuestionTypeChart
          questionTypes={report.questionTypes}
          overallTop3Accuracy={report.summary.top3Accuracy}
        />
      </section>

      {/* 하단: 실패 목록.
          FailureTable 은 완전 실패(Top-3 밖)만 받는다. 100문항 전체 표는 Phase 7c. */}
      <section aria-label="실패한 문항">
        <h2 className={styles.sectionTitle}>실패한 문항</h2>
        <FailureTable
          failures={report.questions.filter((q) => !q.top3Hit)}
          totalFailCount={report.summary.top3FailCount}
        />
      </section>
    </main>
  );
}
