import ActionPanel from "@/components/eval/ActionPanel/ActionPanel";
import AppSummaryCard from "@/components/eval/AppSummaryCard/AppSummaryCard";
import FailureTable from "@/components/eval/FailureTable/FailureTable";
import GaugeRing from "@/components/eval/GaugeRing/GaugeRing";
import GradeScale from "@/components/eval/GradeScale/GradeScale";
import QueryQualityTable from "@/components/eval/QueryQualityTable/QueryQualityTable";
import QuestionTypeChart from "@/components/eval/QuestionTypeChart/QuestionTypeChart";
import RecommendationCards from "@/components/eval/RecommendationCards/RecommendationCards";
import SummaryCards from "@/components/eval/SummaryCards/SummaryCards";
import { gradeColorVar, gradeLabel } from "@/lib/enumTokens";
import type { Evaluation, Grade, QuestionResult } from "@/lib/types";
import evalFixture from "@/mocks/eval_A492.json";

import styles from "./page.module.css";

/**
 * 컴포넌트 확인 페이지. 개발 전용
 * (`app/dev/layout.tsx` 가 프로덕션에서 404 처리).
 *
 * **이 페이지의 데이터는 backend fixture(eval_A492)가 단일 출처다.**
 * frontend/src/mocks/eval_A492.json 은 그 복사본이다 (make sync-fixture).
 * 계약이 바뀌면 fixture 를 고치고 다시 복사하면 이 페이지가 따라온다 —
 * 도메인 값을 여기에 손으로 적지 않는다. 경계 케이스만 fixture 를 가공해 만든다.
 */

// backend fixture 가 단일 출처다. JSON import 는 리터럴 타입으로 추론되어
// grade("CRITICAL"|...) 같은 union 과 어긋나므로, 계약 타입으로 한 번 좁힌다.
// 구조 검증은 backend 테스트(test_evaluation_contract)가 이미 한다.
const REPORT = evalFixture as unknown as Evaluation;

const FIXTURE_TARGET = REPORT.target;
const FIXTURE_QUERIES = REPORT.queries;
const FIXTURE_SUMMARY = REPORT.summary;
// fixture 에는 previous 가 항상 있다(A311). 델타 뱃지 케이스에서 non-null 로 쓴다.
const FIXTURE_PREVIOUS = REPORT.previous!;
const FIXTURE_TYPES = REPORT.questionTypes;
const FIXTURE_RECOMMENDATIONS = REPORT.recommendations;
// FailureTable 은 이제 100문항 전체를 받는다 (Phase 7c). 계약 순서 그대로.
const FIXTURE_QUESTIONS = REPORT.questions;

const VALUES = [0, 40, 78, 100];

// --- 경계 케이스: fixture 를 가공해 파생한다 (도메인 리터럴을 새로 적지 않는다) ---

// 실패 0건(전부 성공). 모든 문항을 NONE 으로 눕히고 summary 도 맞춰 내린다 —
// 성공 뱃지가 중립색으로 조용한지, 필터가 "Top-3 실패 0" 을 어떻게 보이는지 확인.
const ALL_SUCCESS_QUESTIONS: QuestionResult[] = FIXTURE_QUESTIONS.map((q) => ({
  ...q,
  top1: { ...q.top1, path: q.expected.path, method: q.expected.method },
  top1Hit: true,
  top3Hit: true,
  failureScope: "NONE",
  expectedRank: 1,
  failureCategory: null,
  reason: null,
}));
const ALL_SUCCESS_SUMMARY: Evaluation["summary"] = {
  ...FIXTURE_SUMMARY,
  top1Accuracy: 100,
  top3Accuracy: 100,
  top1FailCount: 0,
  top3FailCount: 0,
  top1Grade: "GOOD",
  top3Grade: "GOOD",
};

// 단일 메서드(SELECT 전용 DAC) — 표 전체가 한 종류면 method 뱃지를 숨긴다.
const SINGLE_METHOD_QUESTIONS: QuestionResult[] = FIXTURE_QUESTIONS.map((q) => ({
  ...q,
  expected: { ...q.expected, method: "GET" },
  top1: { ...q.top1, method: "GET" },
  top3: q.top3.map((r) => ({ ...r, method: "GET" })),
}));

export default function ComponentsPage() {
  const grades = Object.keys(gradeColorVar) as Grade[];

  return (
    <main className={styles.page}>
      <h1 className={styles.title}>컴포넌트</h1>
      <p className={styles.lead}>
        Phase 6 진행 중 — <strong>8 / 8</strong>. 완료: <code>GaugeRing</code>,{" "}
        <code>AppSummaryCard</code>, <code>QueryQualityTable</code>,{" "}
        <code>SummaryCards</code>, <code>QuestionTypeChart</code>,{" "}
        <code>RecommendationCards</code>, <code>FailureTable</code>,{" "}
        <code>GradeScale</code>, <code>ActionPanel</code>.
        <br />
        <strong>이 페이지의 데이터는 backend fixture(eval_A492) 기준이다.</strong>{" "}
        도메인 값은 전부 <code>@/mocks/eval_A492.json</code>(복사본)에서 오고, 경계
        케이스만 그 값을 가공해 만든다. 계약이 바뀌면{" "}
        <code>make sync-fixture</code> 로 다시 복사한다.
      </p>


      {/* --- AppSummaryCard --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>AppSummaryCard</h2>
        <p className={styles.sectionNote}>
          평가 대상 앱 메타. <strong>수치를 넣지 않는다</strong> — 점수는 GaugeRing 과
          SummaryCards 의 몫이다. 여기는 어느 앱, 몇 개 쿼리, 어느 버전인지만 낮은
          높이로 보인다.
        </p>
        <AppSummaryCard target={FIXTURE_TARGET} />
        <p className={styles.sectionNote}>owner 없음.</p>
        <AppSummaryCard target={{ ...FIXTURE_TARGET, owner: null }} />
      </section>

      {/* --- QueryQualityTable --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>QueryQualityTable</h2>
        <p className={styles.sectionNote}>
          이 화면의 실질 산출물. <strong>재생성 필요가 위로, 그 안에서 인식률 오름차순</strong>
          — 손봐야 할 것이 먼저 보인다. 설명 품질은 표시용 요약이고 진짜 판단은
          needsRegeneration(백엔드)이다. 인식률 막대 색은 백엔드가 확정한 grade 를 따른다.
        </p>
        <QueryQualityTable queries={FIXTURE_QUERIES} />

        <p className={styles.sectionNote}>
          재생성 필요 0건 — pill 도 기본 선택도 없다. &ldquo;선택 0건&rdquo;.
        </p>
        <QueryQualityTable
          queries={FIXTURE_QUERIES.map((q) => ({ ...q, needsRegeneration: false }))}
        />

        <p className={styles.sectionNote}>전부 재생성 필요.</p>
        <QueryQualityTable
          queries={FIXTURE_QUERIES.slice(0, 4).map((q) => ({ ...q, needsRegeneration: true }))}
        />

        <p className={styles.sectionNote}>
          메서드가 1종(전부 GET)뿐일 때 — <strong>method 뱃지가 사라지고 경로만</strong>
          보인다 (open-questions #50).
        </p>
        <QueryQualityTable
          queries={FIXTURE_QUERIES.map((q) => ({ ...q, method: "GET" }))}
        />

        <p className={styles.sectionNote}>
          summary 없는 쿼리(&ldquo;설명 없음&rdquo;)와 경로가 매우 긴 쿼리.
        </p>
        <QueryQualityTable
          queries={[
            FIXTURE_QUERIES[8],
            {
              ...FIXTURE_QUERIES[0],
              path: "/queries/equipment-chamber-sensor-temperature-and-pressure-trend-by-recipe-step",
              summary: "설비 챔버 센서 온도·압력 추이를 레시피 스텝별로 조회",
              needsRegeneration: false,
            },
          ]}
        />
      </section>

      {/* --- SummaryCards --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>SummaryCards</h2>
        <p className={styles.sectionNote}>
          fixture <code>eval_A492.json</code> 실제 값. 카드 5장 — 시안의 이모지
          &ldquo;평가 상태&rdquo; 카드는 뺐다(등급은 GaugeRing 이 표현한다).
          델타 단위는 <strong>&ldquo;p&rdquo;(퍼센트포인트)</strong>다. 64% → 78% 는
          14 퍼센트포인트 상승이지 14% 상승이 아니다.
        </p>
        <SummaryCards summary={FIXTURE_SUMMARY} previous={FIXTURE_PREVIOUS} />

        <p className={styles.sectionNote}>
          <code>previous</code> 없음 — 뱃지를 아예 렌더하지 않는다. 빈 자리도 남기지 않아
          카드 높이가 위와 달라진다.
        </p>
        <SummaryCards summary={FIXTURE_SUMMARY} previous={null} />

        <p className={styles.sectionNote}>하락 — 이전 평가가 더 높았던 경우.</p>
        <SummaryCards
          summary={FIXTURE_SUMMARY}
          previous={{ ...FIXTURE_PREVIOUS, top3Accuracy: 85.0 }}
        />

        <p className={styles.sectionNote}>동일 — 변화가 없으면 방향 기호 없이 회색.</p>
        <SummaryCards
          summary={FIXTURE_SUMMARY}
          previous={{ ...FIXTURE_PREVIOUS, top3Accuracy: 78.0 }}
        />

        <p className={styles.sectionNote}>
          극단값 — 레이아웃 확인용이라 수치끼리 앞뒤가 맞지 않는다.
        </p>
        <SummaryCards
          summary={{
            totalQuestions: 0,
            top1Accuracy: 0,
            top3Accuracy: 0,
            top1FailCount: 0,
            top3FailCount: 0,
            top1Grade: "CRITICAL",
            top3Grade: "CRITICAL",
          }}
          previous={{ ...FIXTURE_PREVIOUS, top3Accuracy: 0 }}
        />
        <SummaryCards
          summary={{
            totalQuestions: 100,
            top1Accuracy: 100,
            top3Accuracy: 100,
            top1FailCount: 100,
            top3FailCount: 100,
            top1Grade: "GOOD",
            top3Grade: "GOOD",
          }}
          previous={{ ...FIXTURE_PREVIOUS, top3Accuracy: 0 }}
        />
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
          previous={FIXTURE_PREVIOUS}
        />
      </section>

      {/* --- 등급 × 값 --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>GaugeRing — 등급 × 값</h2>
        <p className={styles.sectionNote}>
          링 색은 등급이, 채워진 비율은 값이 정한다. 둘은 독립이라 실제로는
          어긋난 조합(우수 등급인데 0%)도 렌더된다 — 등급은 백엔드가 확정해
          내려주므로 프론트가 재계산하지 않는다.
        </p>

        <div className={styles.grid}>
          <div />
          {VALUES.map((value) => (
            <div key={value} className={styles.colHead}>
              value = {value}
            </div>
          ))}

          {grades.map((grade) => (
            <Row key={grade} grade={grade} />
          ))}
        </div>
      </section>

      {/* --- 크기 --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>size</h2>
        <p className={styles.sectionNote}>
          링 두께와 글자 크기가 전부 <code>size</code> 에서 파생된다.
          작은 크기에서 숫자가 뭉개지지 않는지 본다.
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
          시안의 &ldquo;평가 기준&rdquo; 카드. <strong>GaugeRing 과 역할이 다르다</strong> —
          GaugeRing 은 &ldquo;얼마인가&rdquo;(78.0%), GradeScale 은 &ldquo;어느
          구간인가&rdquo;(개선 필요 / 70~85%)를 말한다. 그래서 여기에는 큰 수치를 넣지
          않는다. 78%가 화면에서 반복되는 것을 막는 것이 이 분리의 목적이다 (§9-1 #1).
          <br />
          구간 정의는 <code>lib/gradeBands.ts</code> 한 곳에만 있다. contract.md §3 이
          바뀌면 그 배열만 고치면 호·범례·aria 라벨이 함께 따라온다.
        </p>
        <div className={styles.alignRow}>
          <GradeScale metric="top3" value={78} grade="NEEDS_IMPROVEMENT" />
        </div>

        <p className={styles.sectionNote}>
          구간 경계에서 바늘 위치 — 0 / 69.9 / 70 / 78 / 85 / 94.9 / 95 / 100.
          등급은 각 값이 속한 구간으로 맞춰 뒀지만, <strong>실제로는 백엔드가 확정한
          값을 그대로 쓴다</strong> (프론트가 value 로 구간을 추론하지 않는다).
        </p>
        <div className={styles.alignRow}>
          {(
            [
              [0, "CRITICAL"],
              [69.9, "CRITICAL"],
              [70, "NEEDS_IMPROVEMENT"],
              [78, "NEEDS_IMPROVEMENT"],
              [85, "FAIR"],
              [94.9, "FAIR"],
              [95, "GOOD"],
              [100, "GOOD"],
            ] as const
          ).map(([v, g]) => (
            <div key={v} className={styles.alignItem}>
              <GradeScale metric="top3" value={v} grade={g} size={120} />
              <span className={styles.sizeLabel}>value = {v}</span>
            </div>
          ))}
        </div>

        <p className={styles.sectionNote}>size 120 / 180 / 240.</p>
        <div className={styles.alignRow}>
          {[120, 180, 240].map((s) => (
            <div key={s} className={styles.alignItem}>
              <GradeScale metric="top3" value={78} grade="NEEDS_IMPROVEMENT" size={s} />
              <span className={styles.sizeLabel}>size = {s}</span>
            </div>
          ))}
        </div>

        <p className={styles.sectionNote}>
          등급과 값이 어긋난 조합 — 백엔드가 확정한 등급을 그대로 따른다.
          바늘은 값이 가리키는 곳에, 강조는 등급이 말하는 구간에 있다.
        </p>
        <div className={styles.alignRow}>
          <GradeScale metric="top3" value={40} grade="GOOD" size={140} />
          <GradeScale metric="top3" value={99} grade="CRITICAL" size={140} />
        </div>
      </section>

      {/* --- GaugeRing vs GradeScale --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>GaugeRing vs GradeScale</h2>
        <p className={styles.sectionNote}>
          조립할 때 어느 쪽을 어디에 쓸지 고르는 자리. 같은 데이터(78.0%, 개선 필요)를
          두 컴포넌트가 각각 어떻게 말하는지 나란히 본다.
          <strong> 둘을 같이 쓰면 78%가 두 번 나오지는 않는다</strong> —
          GradeScale 에는 수치가 없다.
        </p>
        <div className={styles.alignRow}>
          <div className={styles.alignItem}>
            <GaugeRing value={78} grade="NEEDS_IMPROVEMENT" size={180} />
            <span className={styles.sizeLabel}>GaugeRing — 얼마인가</span>
          </div>
          <div className={styles.alignItem}>
            <GradeScale metric="top3" value={78} grade="NEEDS_IMPROVEMENT" size={180} />
            <span className={styles.sizeLabel}>GradeScale — 어느 구간인가</span>
          </div>
        </div>
      </section>

      {/* --- QuestionTypeChart --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>QuestionTypeChart</h2>
        <p className={styles.sectionNote}>
          fixture <code>eval_A492.json</code> 의 7종. 시안에는 분포만 있었다 —
          <strong> 유형별 인식률이 이 대시보드에서 가장 중요한 정보다.</strong>
          &ldquo;한영 혼합 10%&rdquo;로는 할 게 없지만 &ldquo;한영 혼합에서
          40%&rdquo;면 무엇을 고칠지가 정해진다.
          <br />
          막대는 <strong>낮은 순</strong>이고, 점선은 전체 인식률(78.0%)이다.
          평균 아래 유형이 기준선 왼쪽에 모인다 — 등급을 다시 계산하지 않고 같은 효과를 낸다.
        </p>
        <QuestionTypeChart questionTypes={FIXTURE_TYPES} overallTop3Accuracy={78.0} />

        <p className={styles.sectionNote}>
          한 유형이 100% — 조각이 하나면 간격을 두지 않는다. 간격을 그대로 두면
          원이 안 닫혀서 데이터가 잘못된 것처럼 보인다.
        </p>
        <QuestionTypeChart
          questionTypes={[{ ...FIXTURE_TYPES[0], count: 100, ratio: 100.0 }]}
          overallTop3Accuracy={95.5}
        />

        <p className={styles.sectionNote}>
          <code>count</code> 가 0 인 유형이 섞였을 때 — 조각은 안 그려지고 범례엔 남는다.
          그 유형으로 만든 문항이 0개라는 것도 정보다.
        </p>
        <QuestionTypeChart
          questionTypes={FIXTURE_TYPES.map((t, i) =>
            i % 2 === 1 ? { ...t, count: 0, ratio: 0, top3Accuracy: 0 } : t,
          )}
          overallTop3Accuracy={78.0}
        />

        <p className={styles.sectionNote}>유형이 2개뿐일 때.</p>
        <QuestionTypeChart
          questionTypes={[
            { ...FIXTURE_TYPES[0], count: 60, ratio: 60.0 },
            { ...FIXTURE_TYPES[6], count: 40, ratio: 40.0 },
          ]}
          overallTop3Accuracy={73.3}
        />

        <p className={styles.sectionNote}>
          인식률이 전부 동일할 때 — 기준선과 막대 끝이 겹친다.
        </p>
        <QuestionTypeChart
          questionTypes={FIXTURE_TYPES.map((t) => ({ ...t, top3Accuracy: 78.0 }))}
          overallTop3Accuracy={78.0}
        />
      </section>


      {/* --- RecommendationCards --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>RecommendationCards</h2>
        <p className={styles.sectionNote}>
          fixture <code>eval_A492.json</code> 의 3건. 시안의 &ldquo;개선 추천&rdquo;은
          &ldquo;권장 조치&rdquo;로 변경 확정됐다 (§9-2).
          <br />
          <code>failShare</code> 합이 <strong>113.7%</strong>다. 한 실패에 원인이 둘 이상일 수
          있어 중복 집계되기 때문이다 (계약 §2). 시안의 &ldquo;실패 원인 중 62%&rdquo; 같은
          임의 합산 문구는 만들지 않는다 — 각주로 이유만 상시 표시한다.
        </p>
        <RecommendationCards recommendations={FIXTURE_RECOMMENDATIONS} />

        <p className={styles.sectionNote}>
          priority 3종 + 설명 길이 극단 + failShare 0% / 100%. 설명이 짧아도 하단부(비중 막대)가
          바닥에 붙어 카드끼리 높이가 맞는지 본다.
        </p>
        <RecommendationCards
          recommendations={[
            { ...FIXTURE_RECOMMENDATIONS[0], order: 1, priority: "HIGH", failShare: 100 },
            {
              order: 2,
              title: "짧은 설명",
              description: "한 줄.",
              priority: "MEDIUM",
              failShare: 0,
            },
            {
              order: 3,
              title: "아주 긴 설명이 들어간 조치 항목",
              description:
                "설명이 세 줄을 넘으면 말줄임된다. 이 문장은 그것을 확인하려고 일부러 길게 적은 것이다. 실제 백엔드가 이만큼 긴 설명을 내려줄지는 알 수 없지만, 길이에 따라 카드 높이가 달라지면 비중 막대가 서로 어긋나 눈으로 비교할 수 없게 되므로 상한을 둔다. 여기서부터는 화면에 보이지 않아야 한다.",
              priority: "LOW",
              failShare: 12.5,
            },
          ]}
        />

        <p className={styles.sectionNote}>항목 1개.</p>
        <RecommendationCards recommendations={[FIXTURE_RECOMMENDATIONS[0]]} />

        <p className={styles.sectionNote}>항목 5개 — 3열 그리드가 줄바꿈된다.</p>
        <RecommendationCards
          recommendations={[
            ...FIXTURE_RECOMMENDATIONS,
            { ...FIXTURE_RECOMMENDATIONS[0], order: 4, title: "네 번째 조치", priority: "LOW", failShare: 8.3 },
            { ...FIXTURE_RECOMMENDATIONS[1], order: 5, title: "다섯 번째 조치", priority: "MEDIUM", failShare: 4.2 },
          ]}
        />

        <p className={styles.sectionNote}>
          빈 배열 — <strong>섹션 제목과 각주까지 아무것도 렌더되지 않는다.</strong>
          아래에 빈 줄만 있으면 정상이다.
        </p>
        <RecommendationCards recommendations={[]} />
      </section>


      {/* --- ActionPanel --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>ActionPanel</h2>
        <p className={styles.sectionNote}>
          시안 우하단의 &ldquo;권장 액션&rdquo;. 요약 문장은{" "}
          <strong>가장 큰 원인 1건만 인용한다</strong> — 시안의 &ldquo;실패 원인 중
          62%&rdquo;는 카드의 45/23/32%와 맞지 않는 값이었다 (계약 §5).
          failShare 는 중복 집계되므로 합산 자체가 의미를 갖지 못한다.
          <br />
          평가 엔진이 없어 버튼은 둘 다 비활성이다. 확인 다이얼로그는 활성화 시점에
          만든다 — 지금 만들면 <code>&apos;use client&apos;</code>가 필요해지는데
          동작할 대상이 없다.
        </p>
        <ActionPanel recommendations={FIXTURE_RECOMMENDATIONS} specId="orders-v3" />

        <p className={styles.sectionNote}>
          HIGH 가 없고 MEDIUM 만 있는 경우 — 우선순위가 가장 높은 것 중에서 고른다.
          (MEDIUM 2건 중 failShare 가 큰 &ldquo;유사 리소스 구분 강화&rdquo; 31.8%)
        </p>
        <ActionPanel
          recommendations={[
            { ...FIXTURE_RECOMMENDATIONS[1], priority: "LOW", failShare: 36.4 },
            { ...FIXTURE_RECOMMENDATIONS[2], priority: "MEDIUM", failShare: 31.8 },
            { ...FIXTURE_RECOMMENDATIONS[0], order: 4, priority: "MEDIUM", failShare: 20.0 },
          ]}
        />

        <p className={styles.sectionNote}>
          failShare 동률 — <strong>order 가 작은 쪽</strong>을 택한다. 매번 다른 항목이
          뽑히면 화면이 흔들린다. (둘 다 HIGH · 45.5% → order 2 인
          &ldquo;동의어·업무 용어 추가&rdquo;)
        </p>
        <ActionPanel
          recommendations={[
            { ...FIXTURE_RECOMMENDATIONS[2], order: 5, priority: "HIGH", failShare: 45.5 },
            { ...FIXTURE_RECOMMENDATIONS[1], order: 2, priority: "HIGH", failShare: 45.5 },
          ]}
        />

        <p className={styles.sectionNote}>
          <code>specId</code> 없음 — 대상 표기만 빠지고 나머지는 그대로.
        </p>
        <ActionPanel recommendations={[FIXTURE_RECOMMENDATIONS[2]]} />

        <p className={styles.sectionNote}>
          빈 배열 — <strong>카드 자체를 렌더하지 않는다.</strong> 근거 없는 버튼만 남으면
          무엇을 위한 조치인지 알 수 없다. 아래에 빈 줄만 있으면 정상이다.
        </p>
        <ActionPanel recommendations={[]} specId="orders-v3" />
      </section>

      {/* --- FailureTable --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>FailureTable</h2>
        <p className={styles.sectionNote}>
          fixture <code>eval_A492.json</code> 의 <strong>문항 100개 전체</strong>.
          더 이상 실패만 받지 않고, 셀에서 <code>failureScope</code> 로 성공/부분
          실패/완전 실패를 나눈다 (Phase 7c). 정렬은 계약이 해서 내려준다
          (TOP3 → TOP1_ONLY → NONE, no 오름차순) — 컴포넌트는 다시 정렬하지 않는다.
          <br />
          <strong>여기서 확인할 것:</strong> ① 기본 5행만 보이고 &ldquo;전체 N건
          보기&rdquo; 로 펼침 ② 펼치면 표에 스크롤이 걸리고 헤더(thead)가 고정 ③
          실패 구분 칩(전체/Top-3 실패/Top-1 실패/성공)과 원인별 칩(건수 표시)으로
          필터 ④ Hit 여부 셀이 색뿐 아니라 ✓/✗ 아이콘·텍스트로도 읽히는지. 상단
          &ldquo;총 N건 중 실패 M건&rdquo; 은 <strong>summary prop</strong> 값이지
          문항을 세서 만든 값이 아니다.
        </p>
        <FailureTable questions={FIXTURE_QUESTIONS} summary={FIXTURE_SUMMARY} />

        <p className={styles.sectionNote}>
          <strong>실패 0건(전부 성공)</strong> — 모든 문항이 성공 뱃지(중립 회색)다.
          &ldquo;Top-3 실패&rdquo; 필터를 누르면 &ldquo;해당하는 문항이 없습니다&rdquo;.
          성공은 조용해야 실패가 묻히지 않는다.
        </p>
        <FailureTable questions={ALL_SUCCESS_QUESTIONS} summary={ALL_SUCCESS_SUMMARY} />

        <p className={styles.sectionNote}>
          <strong>단일 메서드</strong> — DAC 이 SELECT 전용이면 모든 쿼리가 GET 이다
          (open-questions #50). 표 전체에서 메서드가 1종뿐이면 뱃지를 숨기고 경로만
          보인다. 뱃지가 전부 &ldquo;GET&rdquo;이면 정보를 주지 못하고 자리만 차지한다.
        </p>
        <FailureTable questions={SINGLE_METHOD_QUESTIONS} summary={FIXTURE_SUMMARY} />

        <p className={styles.sectionNote}>
          빈 상태 — 문항이 하나도 없을 때. 표 대신 안내를 보인다.
        </p>
        <FailureTable questions={[]} summary={FIXTURE_SUMMARY} />
      </section>

      {/* --- 정렬 --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>정렬</h2>
        <p className={styles.sectionNote}>
          십자선이 링의 정중앙이다. <strong>숫자가 그 위에 놓여야 한다.</strong>
          <br />
          예전에는 [숫자 + 등급]을 묶음째 가운데 정렬해서 숫자가 지름의 7.9%만큼
          위로 떠 있었다 (size 96 에서 7.6px). 등급 라벨은 이제 문서 흐름에서
          빠져 있어, 라벨이 &ldquo;심각&rdquo;이든 &ldquo;개선 필요&rdquo;든 숫자는
          움직이지 않는다.
        </p>
        <div className={styles.alignRow}>
          {[64, 96, 160].map((size) => (
            <div key={size} className={styles.alignItem}>
              <div className={styles.alignBox}>
                <div className={styles.crosshair} />
                <GaugeRing value={78} grade="NEEDS_IMPROVEMENT" size={size} label="" />
              </div>
              <span className={styles.sizeLabel}>size = {size}</span>
            </div>
          ))}
        </div>

        <p className={styles.sectionNote}>
          자릿수와 등급 라벨 길이가 달라도 숫자 위치가 흔들리지 않는지:
        </p>
        <div className={styles.alignRow}>
          {(
            [
              { value: 0, grade: "CRITICAL" },
              { value: 7.5, grade: "CRITICAL" },
              { value: 78, grade: "NEEDS_IMPROVEMENT" },
              { value: 100, grade: "GOOD" },
            ] as const
          ).map((c) => (
            <div key={c.value} className={styles.alignBox}>
              <div className={styles.crosshair} />
              <GaugeRing value={c.value} grade={c.grade} size={120} label="" />
            </div>
          ))}
        </div>
      </section>

      {/* --- 경계값 --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>경계값</h2>
        <p className={styles.sectionNote}>
          범위 밖의 값은 잘라낸다. 방어하지 않으면 dashoffset 이 음수가 되면서
          링이 반대로 그려진다.
        </p>
        <div className={styles.edgeRow}>
          <div className={styles.edgeItem}>
            <GaugeRing value={0} grade="CRITICAL" />
            <span className={styles.edgeLabel}>
              0 — 진행 링을 아예 그리지 않는다 (round cap 잔점 방지)
            </span>
          </div>
          <div className={styles.edgeItem}>
            <GaugeRing value={0.4} grade="CRITICAL" />
            <span className={styles.edgeLabel}>0.4 — 아주 작은 값</span>
          </div>
          <div className={styles.edgeItem}>
            <GaugeRing value={99.9} grade="GOOD" />
            <span className={styles.edgeLabel}>99.9 — 거의 한 바퀴</span>
          </div>
          <div className={styles.edgeItem}>
            <GaugeRing value={100} grade="GOOD" />
            <span className={styles.edgeLabel}>100 — 이음매가 보이지 않아야</span>
          </div>
          <div className={styles.edgeItem}>
            <GaugeRing value={-20} grade="CRITICAL" />
            <span className={styles.edgeLabel}>-20 → 0 으로 clamp</span>
          </div>
          <div className={styles.edgeItem}>
            <GaugeRing value={140} grade="GOOD" />
            <span className={styles.edgeLabel}>140 → 100 으로 clamp</span>
          </div>
        </div>
      </section>

      {/* --- label --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>label</h2>
        <p className={styles.sectionNote}>
          캡션이자 스크린 리더가 읽는 접두사다. 기본값은 &ldquo;Top-3 인식률&rdquo;.
          개발자 도구로 <code>aria-label</code> 을 확인한다.
        </p>
        <div className={styles.edgeRow}>
          <div className={styles.edgeItem}>
            <GaugeRing value={78} grade="NEEDS_IMPROVEMENT" />
            <span className={styles.edgeLabel}>기본값</span>
          </div>
          <div className={styles.edgeItem}>
            <GaugeRing value={61} grade="CRITICAL" label="Top-1 인식률" />
            <span className={styles.edgeLabel}>label=&quot;Top-1 인식률&quot;</span>
          </div>
          <div className={styles.edgeItem}>
            <GaugeRing value={64} grade="CRITICAL" label="" />
            <span className={styles.edgeLabel}>
              빈 문자열 — 캡션 없음. aria-label 은 여전히 등급을 읽는다
            </span>
          </div>
        </div>
      </section>
    </main>
  );
}

function Row({ grade }: { grade: Grade }) {
  return (
    <>
      <div className={styles.rowHead}>
        {gradeLabel[grade]}
        <code>{grade}</code>
      </div>
      {VALUES.map((value) => (
        <div key={value} className={styles.cell}>
          <GaugeRing value={value} grade={grade} />
        </div>
      ))}
    </>
  );
}
