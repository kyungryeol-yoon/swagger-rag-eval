import GaugeRing from "@/components/eval/GaugeRing/GaugeRing";
import SummaryCards from "@/components/eval/SummaryCards/SummaryCards";
import { gradeColorVar, gradeLabel } from "@/lib/enumTokens";
import type { EvaluationSummary, Grade, PreviousEvaluation } from "@/lib/types";

import styles from "./page.module.css";

/**
 * 컴포넌트 확인 페이지. 개발 전용
 * (`app/dev/layout.tsx` 가 프로덕션에서 404 처리).
 *
 * Phase 6 는 컴포넌트를 하나씩 만든다. 지금은 GaugeRing 뿐이다.
 */

const VALUES = [0, 40, 78, 100];

/** backend/app/fixtures/eval_A492.json 의 실제 값. 손으로 바꾸지 말 것. */
const FIXTURE_SUMMARY: EvaluationSummary = {
  totalQuestions: 100,
  top1Accuracy: 61.0,
  top3Accuracy: 78.0,
  top1FailCount: 39,
  top3FailCount: 22,
  grade: "NEEDS_IMPROVEMENT",
};

const FIXTURE_PREVIOUS: PreviousEvaluation = {
  traceId: "A311",
  evaluatedAt: "2026-07-15T09:12:00+09:00",
  top3Accuracy: 64.0,
};

export default function ComponentsPage() {
  const grades = Object.keys(gradeColorVar) as Grade[];

  return (
    <main className={styles.page}>
      <h1 className={styles.title}>컴포넌트</h1>
      <p className={styles.lead}>
        Phase 6 진행 중. 현재 <code>GaugeRing</code>, <code>SummaryCards</code> 2 / 7.
      </p>

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
            grade: "CRITICAL",
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
            grade: "GOOD",
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
            grade: "NEEDS_IMPROVEMENT",
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
