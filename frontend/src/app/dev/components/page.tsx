import FailureTable from "@/components/eval/FailureTable/FailureTable";
import GaugeRing from "@/components/eval/GaugeRing/GaugeRing";
import QuestionTypeChart from "@/components/eval/QuestionTypeChart/QuestionTypeChart";
import RecommendationCards from "@/components/eval/RecommendationCards/RecommendationCards";
import SummaryCards from "@/components/eval/SummaryCards/SummaryCards";
import { gradeColorVar, gradeLabel } from "@/lib/enumTokens";
import type {
  EvaluationSummary,
  Failure,
  Grade,
  PreviousEvaluation,
  QuestionTypeStat,
  Recommendation,
} from "@/lib/types";

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

/** fixture 의 questionTypes 7종. count 합 100, 인식률 40.0 ~ 95.5. */
const FIXTURE_TYPES: QuestionTypeStat[] = [
  { type: "DIRECT", label: "직접 질문", count: 22, ratio: 22.0, top3Accuracy: 95.5 },
  { type: "USER_NL", label: "사용자 자연어 질문", count: 20, ratio: 20.0, top3Accuracy: 75.0 },
  { type: "DOMAIN_TERM", label: "업무 용어 질문", count: 14, ratio: 14.0, top3Accuracy: 78.6 },
  { type: "PARAMETER", label: "파라미터 기반 질문", count: 12, ratio: 12.0, top3Accuracy: 83.3 },
  { type: "ERROR_CASE", label: "오류/에러 상황 질문", count: 11, ratio: 11.0, top3Accuracy: 81.8 },
  { type: "SHORT_KEYWORD", label: "짧은 키워드 질문", count: 11, ratio: 11.0, top3Accuracy: 72.7 },
  { type: "MIXED_LANG", label: "한영 혼합 질문", count: 10, ratio: 10.0, top3Accuracy: 40.0 },
];


/** fixture 의 recommendations 3건. failShare 합 113.7 — 100 을 넘는다. */
const FIXTURE_RECOMMENDATIONS: Recommendation[] = [
  {
    order: 1,
    title: "설명(Description) 보강",
    description:
      "설명이 아예 없는 엔드포인트 2개(DELETE /orders/{id}/refund, GET /products/{id}/restock-schedule)가 전체 실패의 절반 가까이를 차지합니다. summary와 description을 채우는 것만으로 가장 크게 개선됩니다.",
    priority: "HIGH",
    failShare: 45.5,
  },
  {
    order: 2,
    title: "동의어·업무 용어 추가",
    description:
      "사용자는 '재입고', '반품', '운송장'처럼 명세에 없는 표현으로 질문합니다. 설명 안에 실제 사용자 표현을 함께 적어두면 한영 혼합 질문과 짧은 키워드 질문의 인식률이 올라갑니다.",
    priority: "HIGH",
    failShare: 36.4,
  },
  {
    order: 3,
    title: "유사 리소스 구분 강화",
    description:
      "주문 배송지와 회원 기본 주소처럼 이름이 비슷한 엔드포인트가 서로의 상위 결과를 밀어냅니다. 각 설명에 '무엇이 아닌지'를 한 줄 덧붙이면 혼동이 줄어듭니다.",
    priority: "MEDIUM",
    failShare: 31.8,
  },
];

/** fixture failures 의 앞 3건. expectedRank 는 4 / null / null 이다. */
const FIXTURE_FAILURES: Failure[] = [
  {
    id: "q_003",
    question: "주문의 배송 상태를 조회하는 API는 무엇인가요?",
    questionType: "DIRECT",
    expected: { method: "GET", path: "/orders/{id}/shipping-status" },
    results: [
      { rank: 1, method: "GET", path: "/orders/{id}/refund-status", score: 0.781 },
      { rank: 2, method: "GET", path: "/orders/{id}", score: 0.759 },
      { rank: 3, method: "PATCH", path: "/orders/{id}/shipping-address", score: 0.724 },
    ],
    hit: false,
    expectedRank: 4,
    failureCategory: "SIMILAR_RESOURCE",
    reason:
      "같은 주문 리소스의 '-status' 엔드포인트끼리 설명이 겹쳐 환불 상태가 배송 상태를 밀어냄",
  },
  {
    id: "q_007",
    question: "재입고 언제 되나요?",
    questionType: "USER_NL",
    expected: { method: "GET", path: "/products/{id}/restock-schedule" },
    results: [
      { rank: 1, method: "GET", path: "/products/{id}/stock", score: 0.688 },
      { rank: 2, method: "GET", path: "/products/{id}", score: 0.671 },
      { rank: 3, method: "GET", path: "/orders/{id}/shipping-status", score: 0.603 },
    ],
    hit: false,
    expectedRank: null,
    failureCategory: "DESCRIPTION_MISSING",
    reason:
      "기대 엔드포인트에 summary와 description이 모두 없어 경로 문자열 외에는 매칭할 근거가 없음",
  },
  {
    id: "q_017",
    question: "환불 신청은 어떻게 취소하나요?",
    questionType: "USER_NL",
    expected: { method: "DELETE", path: "/orders/{id}/refund" },
    results: [
      { rank: 1, method: "GET", path: "/orders/{id}/refund-status", score: 0.812 },
      { rank: 2, method: "POST", path: "/orders/{id}/refund", score: 0.774 },
      { rank: 3, method: "GET", path: "/orders/{id}", score: 0.701 },
    ],
    hit: false,
    expectedRank: 7,
    failureCategory: "METHOD_MISMATCH",
    reason: "질문의 '취소'를 조회(GET) 의도로 오인식하여 DELETE 엔드포인트가 후순위로 밀림",
  },
];

const LONG_TEXT_FAILURE: Failure = {
  ...FIXTURE_FAILURES[0],
  id: "q_long",
  question:
    "주문한 상품의 배송이 지금 어디까지 진행됐는지, 택배사는 어디이고 운송장 번호는 무엇이며 언제쯤 도착하는지를 한 번에 확인할 수 있는 API가 따로 있나요? 아니면 주문 상세를 먼저 조회한 다음에 별도로 다시 호출해야 하나요?",
  expectedRank: 5,
  reason:
    "질문이 배송 조회·운송장 확인·도착 예정일이라는 세 가지 의도를 한 문장에 담고 있어 임베딩이 어느 쪽으로도 충분히 기울지 못했고, 그 결과 설명이 풍부한 주문 상세 엔드포인트가 상위를 차지했다. 질문을 쪼개면 각각은 Top-1로 잡힌다.",
};

const FAR_MISS_FAILURE: Failure = {
  ...FIXTURE_FAILURES[1],
  id: "q_far",
  question: "재고 수량",
  expectedRank: 20,
  failureCategory: "SYNONYM_MISS",
  reason: "기대 엔드포인트의 설명이 '재고 조회' 한 줄이라 '수량' 키워드와 연결되지 않음",
};

export default function ComponentsPage() {
  const grades = Object.keys(gradeColorVar) as Grade[];

  return (
    <main className={styles.page}>
      <h1 className={styles.title}>컴포넌트</h1>
      <p className={styles.lead}>
        Phase 6 진행 중 — <strong>5 / 7</strong>. 완료: <code>GaugeRing</code>,{" "}
        <code>SummaryCards</code>, <code>QuestionTypeChart</code>,{" "}
        <code>RecommendationCards</code>, <code>FailureTable</code>.
        <br />
        남음: <code>TargetApiCard</code>(6-3), <code>ActionPanel</code>(6-7).
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

      {/* --- FailureTable --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>FailureTable</h2>
        <p className={styles.sectionNote}>
          fixture <code>eval_A492.json</code> 의 실패 앞 3건. 기본 3건만 보이고
          나머지는 버튼으로 넘긴다. 버튼 문구는 <strong>실제 실패 건수(22건)</strong> 기준이다
          — 시안의 &ldquo;나머지 97건 보기&rdquo;는 오류였다 (§9-1 #3).
          <br />
          <code>expectedRank</code> 가 4~5면 <strong>MISS (근접)</strong> amber pill 이다.
          한두 칸 차이로 놓친 것이라 먼저 손댈 후보이고, 6위 이하나 순위 밖과는
          조치의 성격이 다르다.
        </p>
        <FailureTable failures={FIXTURE_FAILURES} totalFailCount={22} />

        <p className={styles.sectionNote}>
          경계: 순위 밖(null) / 근접(5위) / 아주 멀리(20위). 질문과 원인이 길면 말줄임된다.
        </p>
        <FailureTable
          failures={[FIXTURE_FAILURES[1], LONG_TEXT_FAILURE, FAR_MISS_FAILURE]}
          totalFailCount={22}
        />

        <p className={styles.sectionNote}>
          표시할 수 있는 건수가 전체와 같으면 &ldquo;더 있음&rdquo; 안내를 붙이지 않는다.
        </p>
        <FailureTable failures={FIXTURE_FAILURES} totalFailCount={3} />

        <p className={styles.sectionNote}>
          빈 상태 — 실패 0건(인식률 100%). 표 대신 안내를 보인다.
        </p>
        <FailureTable failures={[]} totalFailCount={0} />
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
