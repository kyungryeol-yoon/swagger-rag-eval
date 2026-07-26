import { notFound } from "next/navigation";

import ActionPanel from "@/components/eval/ActionPanel/ActionPanel";
import AppInfoCard from "@/components/eval/AppInfoCard/AppInfoCard";
import FailureTable from "@/components/eval/FailureTable/FailureTable";
import GaugeRing from "@/components/eval/GaugeRing/GaugeRing";
import GradeScale from "@/components/eval/GradeScale/GradeScale";
import QueryQualityTable from "@/components/eval/QueryQualityTable/QueryQualityTable";
import QuestionTypeChart from "@/components/eval/QuestionTypeChart/QuestionTypeChart";
import RecommendationCards from "@/components/eval/RecommendationCards/RecommendationCards";
import SummaryCards, { formatDelta } from "@/components/eval/SummaryCards/SummaryCards";
import ThemeToggle from "@/components/common/ThemeToggle/ThemeToggle";
import { NotFoundError, fetchJson } from "@/lib/api";
import { gradeColor, gradeLabel, searchModeLabel } from "@/lib/enumTokens";
import { GRADE_BANDS, formatBandRange } from "@/lib/gradeBands";
import type { Evaluation } from "@/lib/types";

import styles from "./page.module.css";

/**
 * 평가 리포트 대시보드 — **레이아웃 정합성(Phase 7e)**.
 *
 * 카드 격자를 맞추고 표에 폭을 준다. 좌우 2:1 분할과 sticky 를 없애고 아래로 쌓는다:
 *   헤더(제목·메타 한 줄) / 1행 앱정보+요약 / 2행 평가기준+문항유형+권장조치(3열) /
 *   3행 쿼리 품질 / 4행 실패 상세(전체 폭) / 5행 권장 액션.
 *
 * 컴포넌트 내부는 건드리지 않고 배치·폭만 조정한다. 예외는 계약된 것 —
 * SummaryCards.omit, RecommendationCards.layout, 경로 말줄임.
 *
 * 서버 컴포넌트다. 백엔드 주소는 lib/config 를 경유한다.
 */

/**
 * **정적 프리렌더 금지.** 빌드 시점에 백엔드가 없다. 지금은 동적 세그먼트라
 * 어차피 요청 때 그려지지만, 나중에 `generateStaticParams` 를 붙이는 순간
 * 빌드가 백엔드에 붙으려다 깨진다. 루트와 같은 이유로 명시해 둔다.
 */
export const dynamic = "force-dynamic";

async function getEvaluation(traceId: string): Promise<Evaluation> {
  // 타임아웃·실패 분류·주소 표기는 lib/api 가 맡는다. 여기서는 404 만 갈라낸다 —
  // "결과가 없다" 와 "백엔드가 죽었다" 는 사용자가 할 일이 다르기 때문이다.
  try {
    return await fetchJson<Evaluation>(
      `/api/v1/evaluations/${encodeURIComponent(traceId)}`,
    );
  } catch (error) {
    if (error instanceof NotFoundError) {
      notFound();
    }
    // 나머지는 error.tsx 로. ApiError 의 message 에 원인과 호출 주소가 들어 있다.
    throw error;
  }
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

  // Top-3 인식률 델타는 GaugeRing 옆으로 옮겼다(요약 카드에서 top3Accuracy 를 뺐다).
  // 계산식은 SummaryCards 의 순수 함수를 재사용한다 — 두 곳에 두지 않는다.
  const top3Delta = report.previous
    ? formatDelta(report.summary.top3Accuracy, report.previous.top3Accuracy)
    : null;
  // 실패가 없으면 권장 조치도 재생성 후보도 없다. 그때 우 컬럼은 통째로 사라진다.
  const hasActions = report.recommendations.length > 0;

  const deltaClass =
    top3Delta?.direction === "up"
      ? styles.deltaUp
      : top3Delta?.direction === "down"
        ? styles.deltaDown
        : styles.deltaSame;

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

          {/* 어떤 버전의 외부 평가툴 결과인지 추적용(meta.rawSource). 없으면 숨김. */}
          {report.meta.rawSource && (
            <p className={styles.rawSource}>
              <span>
                평가툴{" "}
                <span className="tabular">{report.meta.rawSource.toolVersion}</span>
              </span>
              <span>
                프롬프트{" "}
                <span className="tabular">{report.meta.rawSource.promptVersion}</span>
              </span>
              <span>
                생성{" "}
                <span className="tabular">
                  {formatDateTime(report.meta.rawSource.generatedAt)}
                </span>
              </span>
            </p>
          )}
        </div>

        {/* 재현성 메타 한 줄 + 테마 토글. 항목이 늘면 줄바꿈으로 흡수된다. */}
        <div className={styles.headerRight}>
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

          <ThemeToggle />
        </div>
      </header>

      {/* 행1: 평가 대상 정보(고정 ~300px) + 전체 요약(게이지 + 카드 4장 한 줄) */}
      <section className={styles.overview} aria-label="요약">
        <AppInfoCard target={report.target} queries={report.queries} />

        <div className={`card ${styles.summaryBox}`}>
          <div className={styles.gaugeCol}>
            {/* 캡션·델타는 페이지가 그린다(label=""). 그래야 델타를 캡션 옆에 붙인다. */}
            <GaugeRing
              value={report.summary.top3Accuracy}
              grade={report.summary.top3Grade}
              size={88}
              label=""
            />
            <div className={styles.gaugeCaption}>
              <span>Top-3 인식률</span>
              {top3Delta && report.previous && (
                <span
                  className={`${styles.deltaBadge} ${deltaClass}`}
                  role="img"
                  aria-label={`이전 평가 ${report.previous.traceId} 대비 ${Math.abs(
                    report.summary.top3Accuracy - report.previous.top3Accuracy,
                  ).toFixed(1)} 퍼센트포인트 ${
                    top3Delta.direction === "up"
                      ? "상승"
                      : top3Delta.direction === "down"
                        ? "하락"
                        : "변화 없음"
                  }`}
                >
                  <span className="tabular" aria-hidden="true">
                    {top3Delta.text}
                  </span>
                </span>
              )}
            </div>
          </div>

          <div className={styles.summaryCards}>
            <SummaryCards
              summary={report.summary}
              previous={report.previous}
              omit={["top3Accuracy"]}
            />
          </div>
        </div>
      </section>

      {/* 행2: 평가 기준(1fr) + 문항 유형 분포(1fr, 도넛+범례만). 좌우 동일 높이. */}
      <div className={styles.rowTwo}>
        <section className={`card ${styles.grades}`} aria-label="지표별 등급">
          <div className="cardHead">
            <h2>평가 기준</h2>
          </div>

          <div className={styles.gradesBody}>
            {/* 헤드라인 지표는 Top-3 하나. 게이지가 둘이면 초점이 흐려진다. */}
            <div className={styles.gaugeSingle}>
              <span className={styles.gaugeSingleCaption}>Top-3 인식률</span>
              <GradeScale
                metric="top3"
                value={report.summary.top3Accuracy}
                grade={report.summary.top3Grade}
                size={200}
                strokeRatio={0.11}
                showLegend={false}
              />
            </div>

            {/* 등급 구간표는 기본 펼침으로 카드를 채운다. Top-1 등급은 여기 텍스트로.
                top1/top3 는 현재 임계값이 같아 '구간 범위' 한 열로 충분하다 —
                갈리면 GRADE_BANDS 만 고치면 된다({top1,top3} 구조 유지). */}
            <table className={styles.criteriaTable}>
              <caption className="srOnly">등급별 인식률 구간과 현재 Top-1 / Top-3 등급</caption>
              <thead>
                <tr>
                  <th scope="col">등급</th>
                  <th scope="col" className={styles.numeric}>
                    구간 범위
                  </th>
                  <th scope="col" className={styles.mark}>
                    Top-1
                  </th>
                  <th scope="col" className={styles.mark}>
                    Top-3
                  </th>
                </tr>
              </thead>
              <tbody>
                {GRADE_BANDS.top3.map((band) => {
                  const isTop1 = band.grade === report.summary.top1Grade;
                  const isTop3 = band.grade === report.summary.top3Grade;
                  return (
                    <tr key={band.grade} className={isTop3 ? styles.currentRow : ""}>
                      <th scope="row" style={{ color: gradeColor(band.grade) }}>
                        {gradeLabel[band.grade]}
                      </th>
                      <td className={`${styles.numeric} tabular`}>{formatBandRange(band)}</td>
                      <td className={styles.mark}>
                        {isTop1 && <span className={styles.nowBadge}>현재</span>}
                      </td>
                      <td className={styles.mark}>
                        {isTop3 && <span className={styles.nowBadge}>현재</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* 문항 유형 분포 — 도넛+범례만. 막대는 행3 좌상단으로 떼어 놓는다. */}
        <QuestionTypeChart
          questionTypes={report.questionTypes}
          overallTop3Accuracy={report.summary.top3Accuracy}
          show="distribution"
        />
      </div>

      {/* 행2.5: 쿼리별 설명 품질 (전체 폭) */}
      <section aria-label="쿼리별 설명 품질">
        <QueryQualityTable queries={report.queries} />
      </section>

      {/* 행3: 좌(2fr) 유형별 막대 + 100문항 표 / 우(1fr) 권장 조치 + 권장 액션.
          좌우 컬럼의 전체 높이만 같으면 된다 — 우측 마지막 카드가 flex-grow 로 바닥을 맞춘다. */}
      <div className={`${styles.rowMain} ${hasActions ? "" : styles.rowMainAlone}`}>
        <div className={styles.mainLeft}>
          {/* 유형별 Top-3 인식률 막대 — 도넛과 같은 계산을 공유하되 막대만. */}
          <QuestionTypeChart
            questionTypes={report.questionTypes}
            overallTop3Accuracy={report.summary.top3Accuracy}
            show="bars"
          />

          <section aria-label="문항별 결과">
            <FailureTable questions={report.questions} summary={report.summary} />
          </section>
        </div>

        {/* 권장 조치가 없으면 우 컬럼을 아예 만들지 않는다. 빈 채로 두면
            문항 표 옆에 1fr 짜리 빈 홈이 남아 무언가 못 불러온 것처럼 보인다.
            실패 0건인 평가에서 실제로 그렇다 (fixture E100). */}
        {hasActions && (
          <div className={styles.mainRight}>
            <div className={`card ${styles.recoBox}`}>
              <RecommendationCards recommendations={report.recommendations} layout="stack" />
            </div>
            {/* 권장 액션 — 우 컬럼 최하단. flex-grow 로 좌측 표 높이에 바닥을 맞춘다. */}
            <ActionPanel recommendations={report.recommendations} specId={report.target.appId} />
          </div>
        )}
      </div>
    </main>
  );
}
