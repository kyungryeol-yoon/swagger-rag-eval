import ActionPanel from "@/components/eval/ActionPanel/ActionPanel";
import FailureTable from "@/components/eval/FailureTable/FailureTable";
import GaugeRing from "@/components/eval/GaugeRing/GaugeRing";
import GradeScale from "@/components/eval/GradeScale/GradeScale";
import QueryInfoCard from "@/components/eval/QueryInfoCard/QueryInfoCard";
import QuestionTypeChart from "@/components/eval/QuestionTypeChart/QuestionTypeChart";
import RecommendationCards from "@/components/eval/RecommendationCards/RecommendationCards";
import SummaryCards from "@/components/eval/SummaryCards/SummaryCards";
import { gradeColorVar, gradeLabel } from "@/lib/enumTokens";
import type { Evaluation, Grade, QuestionResult } from "@/lib/types";
import evalFixture from "@/mocks/eval_q-lot-status.json";

import styles from "./page.module.css";

/**
 * 컴포넌트 확인 페이지. 개발 전용
 * (`app/dev/layout.tsx` 가 프로덕션에서 404 처리).
 *
 * **이 페이지의 데이터는 backend fixture 가 단일 출처다.**
 * `frontend/src/mocks/eval_q-lot-status.json` 은 그 복사본이다 (make sync-fixture).
 * 계약이 바뀌면 fixture 를 고치고 다시 복사하면 이 페이지가 따라온다 —
 * 도메인 값을 여기에 손으로 적지 않는다. 경계 케이스만 fixture 를 가공해 만든다.
 */

// JSON import 는 리터럴 타입으로 추론되어 grade("CRITICAL"|...) 같은 union 과
// 어긋나므로, 계약 타입으로 한 번 좁힌다. 구조 검증은 backend 테스트가 이미 한다.
const REPORT = evalFixture as unknown as Evaluation;

const TARGET = REPORT.target;
const SUMMARY = REPORT.summary;
const TYPES = REPORT.questionTypes;
const RECOMMENDATIONS = REPORT.recommendations;
const QUESTIONS = REPORT.questions;

const VALUES = [0, 40, 78, 100];

// --- 경계 케이스: fixture 를 가공해 파생한다 (도메인 리터럴을 새로 적지 않는다) ---

/** 설명이 하나도 없는 쿼리. QueryInfoCard 가 경고색으로 드러내는지 확인. */
const BARE_TARGET: Evaluation["target"] = {
  ...TARGET,
  appId: null,
  summary: null,
  description: null,
  xQuestions: [],
};

/** 실패 0건. 성공 뱃지가 중립색으로 조용한지, 필터가 "Top-3 실패 0" 을 어떻게 보이는지. */
const ALL_SUCCESS_QUESTIONS: QuestionResult[] = QUESTIONS.map((q) => ({
  ...q,
  top3: [{ rank: 1, queryId: TARGET.queryId, path: TARGET.path, score: 0.93 }],
  top1Hit: true,
  top3Hit: true,
  failureScope: "NONE",
  expectedRank: 1,
  failureCategory: null,
  reason: null,
}));
const ALL_SUCCESS_SUMMARY: Evaluation["summary"] = {
  ...SUMMARY,
  top1Accuracy: 100,
  top3Accuracy: 100,
  top1FailCount: 0,
  top3FailCount: 0,
  top1Grade: "GOOD",
  top3Grade: "GOOD",
};

/**
 * 검색 결과가 아예 없는 문항(`top3: null`)과 3개 미만인 문항.
 *
 * 계약이 허용하는 형태이고 실제로 온다 (contract.md §2). 표가 길이를 3으로
 * 가정하고 있으면 여기서 깨진다.
 */
const SPARSE_RESULT_QUESTIONS: QuestionResult[] = QUESTIONS.slice(0, 12).map((q, i) => {
  if (i % 3 === 0) {
    return {
      ...q,
      top3: null,
      top1Hit: false,
      top3Hit: false,
      failureScope: "TOP3",
      expectedRank: null,
      failureCategory: "KEYWORD_MISMATCH",
      reason: "유사도 하한을 넘는 결과가 없음",
    };
  }
  if (i % 3 === 1) {
    return { ...q, top3: (q.top3 ?? []).slice(0, 1) };
  }
  return q;
});

export default function ComponentsPage() {
  const grades = Object.keys(gradeColorVar) as Grade[];

  return (
    <main className={styles.page}>
      <h1 className={styles.title}>컴포넌트</h1>
      <p className={styles.lead}>
        <code>QueryInfoCard</code>, <code>SummaryCards</code>, <code>GaugeRing</code>,{" "}
        <code>GradeScale</code>, <code>QuestionTypeChart</code>,{" "}
        <code>RecommendationCards</code>, <code>FailureTable</code>,{" "}
        <code>ActionPanel</code>.
        <br />
        <strong>Phase 12 에서 평가 단위가 쿼리 1개로 바뀌었다.</strong>{" "}
        <code>QueryQualityTable</code>(쿼리 목록 표)과 <code>AppSummaryCard</code>(앱
        메타)는 계약에서 근거가 사라져 삭제했고, <code>SummaryCards</code> 의 델타
        뱃지는 무상태 전환으로 없어졌다.
        <br />
        <strong>데이터는 backend fixture 가 단일 출처다.</strong> 도메인 값은 전부{" "}
        <code>@/mocks/eval_q-lot-status.json</code>(복사본)에서 오고, 경계 케이스만 그
        값을 가공해 만든다. 계약이 바뀌면 <code>make sync-fixture</code> 로 다시 복사한다.
      </p>

      {/* --- QueryInfoCard --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>QueryInfoCard</h2>
        <p className={styles.sectionNote}>
          평가 대상 쿼리 하나. <strong>수치를 넣지 않는다</strong> — 점수는 GaugeRing 과
          SummaryCards 의 몫이다. 여기는 <code>summary</code> / <code>description</code> /{" "}
          <code>x-question</code> 을 그대로 보여준다. 인식률이 낮은 이유를 사용자가 자기
          설명에서 바로 보게 하는 것이 목적이다.
        </p>
        <div className={styles.narrow}>
          <QueryInfoCard target={TARGET} />
        </div>

        <p className={styles.sectionNote}>
          설명이 전부 없는 경우 — <strong>없다는 사실이 곧 평가 결과다.</strong> 흐리게
          감추지 않고 경고색으로 드러낸다. 예시 질문이 없으면 접이식 자체를 만들지 않는다.
        </p>
        <div className={styles.narrow}>
          <QueryInfoCard target={BARE_TARGET} />
        </div>
      </section>

      {/* --- SummaryCards --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>SummaryCards</h2>
        <p className={styles.sectionNote}>
          fixture 실제 값. 카드 5장 — 시안의 이모지 &ldquo;평가 상태&rdquo; 카드는
          뺐다(등급은 GaugeRing 이 표현한다). <strong>델타 뱃지는 없다</strong> —
          무상태라 비교할 이전 평가가 없다.
        </p>
        <SummaryCards summary={SUMMARY} />

        <p className={styles.sectionNote}>
          <code>omit</code> — 게이지가 Top-3 인식률을 이미 보여줄 때 중복을 없앤다.
          뺀 자리는 남기지 않고 나머지가 폭을 균등 분배한다.
        </p>
        <SummaryCards summary={SUMMARY} omit={["top3Accuracy"]} />

        <p className={styles.sectionNote}>
          극단값 — 레이아웃 확인용이라 수치끼리 앞뒤가 맞지 않는다.
        </p>
        <SummaryCards summary={ALL_SUCCESS_SUMMARY} />
        <SummaryCards
          summary={{
            totalQuestions: 1234,
            top1Accuracy: 61,
            top3Accuracy: 78,
            top1FailCount: 1234,
            top3FailCount: 999,
            top1Grade: "CRITICAL",
            top3Grade: "NEEDS_IMPROVEMENT",
          }}
        />
      </section>

      {/* --- GaugeRing: 등급 × 값 --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>GaugeRing — 등급 × 값</h2>
        <p className={styles.sectionNote}>
          링 색은 등급이, 채워진 비율은 값이 정한다. 둘은 독립이라 실제로는 어긋난
          조합(우수 등급인데 0%)도 렌더된다 — 등급은 백엔드가 확정해 내려주므로
          프론트가 재계산하지 않는다.
        </p>

        <div className={styles.grid}>
          <div />
          {VALUES.map((value) => (
            <div key={value} className={styles.colHead}>
              value = {value}
            </div>
          ))}

          {grades.map((grade) => (
            <GaugeRow key={grade} grade={grade} />
          ))}
        </div>
      </section>

      {/* --- GaugeRing: 크기 --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>size</h2>
        <p className={styles.sectionNote}>
          링 두께와 글자 크기가 전부 <code>size</code> 에서 파생된다. 작은 크기에서
          숫자가 뭉개지지 않는지 본다.
        </p>
        <div className={styles.sizeRow}>
          {[64, 96, 160].map((size) => (
            <div key={size} className={styles.sizeItem}>
              <GaugeRing value={78} grade="NEEDS_IMPROVEMENT" size={size} />
              <span className={styles.sizeLabel}>size = {size}</span>
            </div>
          ))}
        </div>
      </section>

      {/* --- GradeScale --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>GradeScale</h2>
        <p className={styles.sectionNote}>
          <strong>GaugeRing 과 역할이 다르다.</strong> GaugeRing 은
          &ldquo;얼마인가&rdquo;, GradeScale 은 &ldquo;어느 구간인가&rdquo;. 그래서
          여기에는 큰 수치를 넣지 않는다.
        </p>
        <GradeScale metric="top3" value={78} grade="NEEDS_IMPROVEMENT" />

        <p className={styles.sectionNote}>
          등급 × 값 — 바늘 위치와 구간 강조는 독립이다.
        </p>
        <div className={styles.sizeRow}>
          {grades.map((g, i) => (
            <GradeScale
              key={g}
              metric="top3"
              value={VALUES[i % VALUES.length]}
              grade={g}
              size={120}
              showLegend={false}
            />
          ))}
        </div>

        <p className={styles.sectionNote}>
          <code>size</code> — 호 두께는 지름 비율이라 인상이 유지된다.
        </p>
        <div className={styles.sizeRow}>
          {[120, 180, 240].map((s) => (
            <GradeScale
              key={s}
              metric="top3"
              value={78}
              grade="NEEDS_IMPROVEMENT"
              size={s}
              showLegend={false}
            />
          ))}
        </div>
      </section>

      {/* --- QuestionTypeChart --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>QuestionTypeChart</h2>
        <p className={styles.sectionNote}>
          도넛(분포) + 막대(유형별 인식률). 분포만으로는 액션이 안 나온다 —
          &ldquo;한영 혼합이 10%&rdquo; 로 끝나지만, 인식률을 같이 보면 &ldquo;한영
          혼합에서 40%&rdquo; 가 되어 무엇을 고칠지 정해진다.
          <br />
          <strong>유형 7종은 자리표시다</strong> — 실제 분류 체계는 미확정이며, 바뀌면{" "}
          <code>enumTokens.ts</code> 와 계약 두 곳만 고치면 여기가 따라온다.
        </p>
        <QuestionTypeChart questionTypes={TYPES} overallTop3Accuracy={78.0} />

        <p className={styles.sectionNote}>
          유형 3종만 — 배열이라 7종이 아닐 수 있다. 조각·막대가 적을 때의 모습.
        </p>
        <QuestionTypeChart questionTypes={TYPES.slice(0, 3)} overallTop3Accuracy={78.0} />

        <p className={styles.sectionNote}>
          한 종류만 — 조각이 하나면 간격을 두지 않아야 원이 닫힌다.
        </p>
        <QuestionTypeChart questionTypes={TYPES.slice(0, 1)} overallTop3Accuracy={95.5} />

        <p className={styles.sectionNote}>빈 배열 — 빈 도넛 대신 문구만 남긴다.</p>
        <QuestionTypeChart questionTypes={[]} overallTop3Accuracy={0} />

        <p className={styles.sectionNote}>
          기준선이 0% / 100% 일 때 — 라벨이 트랙 밖으로 빠져 옆 카드를 침범하지
          않는지 본다.
        </p>
        <QuestionTypeChart questionTypes={TYPES} overallTop3Accuracy={0} show="bars" />
        <QuestionTypeChart questionTypes={TYPES} overallTop3Accuracy={100} show="bars" />
      </section>

      {/* --- RecommendationCards --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>RecommendationCards</h2>
        <p className={styles.sectionNote}>
          <code>failShare</code> 합이 100을 넘을 수 있다(한 실패에 원인이 복수).
          그래서 합계를 계산해 보여주지 않고 각주로 밝힌다.
        </p>
        <RecommendationCards recommendations={RECOMMENDATIONS} />

        <p className={styles.sectionNote}>
          <code>layout=&quot;stack&quot;</code> — 좁은 사이드 컬럼용 1열.
        </p>
        <div className={styles.narrow}>
          <RecommendationCards recommendations={RECOMMENDATIONS} layout="stack" />
        </div>

        <p className={styles.sectionNote}>
          빈 배열 — 섹션 제목까지 포함해 아무것도 렌더하지 않는다. 조치가 없는데
          &ldquo;권장 조치&rdquo; 라는 빈 제목만 남으면 무언가 빠진 것처럼 보인다.
        </p>
        <RecommendationCards recommendations={[]} />
      </section>

      {/* --- ActionPanel --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>ActionPanel</h2>
        <p className={styles.sectionNote}>
          가장 큰 원인 <strong>한 건만</strong> 인용한다. <code>failShare</code> 를
          더하지 않는다 — 중복 집계라 합산이 의미를 갖지 못한다. 버튼은 평가 엔진
          연동 전까지 비활성이다.
        </p>
        <div className={styles.narrow}>
          <ActionPanel recommendations={RECOMMENDATIONS} specId={TARGET.queryId} />
        </div>

        <p className={styles.sectionNote}>
          근거가 없으면 카드를 만들지 않는다 — 버튼만 남은 카드는 무엇을 위한 조치인지
          알 수 없다.
        </p>
        <ActionPanel recommendations={[]} />
      </section>

      {/* --- FailureTable --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>FailureTable</h2>
        <p className={styles.sectionNote}>
          문항 100개 전체(성공 포함).{" "}
          <strong>&ldquo;기대 쿼리&rdquo; 컬럼이 없다</strong> — 평가 단위가 쿼리
          하나라 100문항의 정답이 전부 같다. 표 위에 한 번만 적고, 확보한 폭은 Top-3
          결과와 추정 원인이 나눠 받았다.
        </p>
        <FailureTable questions={QUESTIONS} summary={SUMMARY} target={TARGET} />

        <p className={styles.sectionNote}>
          <strong>
            검색 결과가 없는 문항(<code>top3: null</code>)과 3개 미만인 문항.
          </strong>{" "}
          계약이 허용하는 형태다 — 표가 길이를 3으로 가정하면 여기서 깨진다.
        </p>
        <FailureTable
          questions={SPARSE_RESULT_QUESTIONS}
          summary={{ ...SUMMARY, totalQuestions: SPARSE_RESULT_QUESTIONS.length }}
          target={TARGET}
        />

        <p className={styles.sectionNote}>
          실패 0건 — 성공은 중립색으로 조용하다. 성공에 초록을 주면 표가 초록으로
          뒤덮여 정작 눈에 띄어야 할 실패가 묻힌다.
        </p>
        <FailureTable
          questions={ALL_SUCCESS_QUESTIONS}
          summary={ALL_SUCCESS_SUMMARY}
          target={TARGET}
        />

        <p className={styles.sectionNote}>빈 배열 — 표 대신 안내 문구.</p>
        <FailureTable
          questions={[]}
          summary={{ ...SUMMARY, totalQuestions: 0 }}
          target={TARGET}
        />
      </section>
    </main>
  );
}

function GaugeRow({ grade }: { grade: Grade }) {
  return (
    <>
      <div className={styles.rowHead}>
        <code>{grade}</code>
        <span>{gradeLabel[grade]}</span>
      </div>
      {VALUES.map((value) => (
        <div key={value} className={styles.cell}>
          <GaugeRing value={value} grade={grade} />
        </div>
      ))}
    </>
  );
}
