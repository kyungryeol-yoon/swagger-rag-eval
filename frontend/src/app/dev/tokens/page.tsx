import {
  cssVar,
  gradeColorVar,
  gradeLabel,
  priorityColorVar,
  questionTypeColorVar,
  questionTypeLabel,
} from "@/lib/enumTokens";
import type { Grade, Priority, QuestionType } from "@/lib/types";

import styles from "./page.module.css";

/**
 * 토큰 확인 페이지. 개발 전용 (`app/dev/layout.tsx` 가 프로덕션에서 404 처리).
 *
 * 여기서 hex 값이 "글자로" 보이는 것은 의도된 것이다. 스와치의 색 자체는
 * 전부 var(--token) 으로 칠하고, 옆에 적힌 hex 는 대조용 라벨일 뿐이다.
 *
 * 등급·우선순위·질문유형 목록은 enumTokens 의 매핑 테이블에서 직접 뽑는다.
 * 계약에 enum 이 추가되면 이 페이지도 자동으로 늘어난다.
 */

const BASE_COLORS: { name: string; hex: string; note: string }[] = [
  { name: "--bg", hex: "#05070B", note: "페이지 배경" },
  { name: "--surface", hex: "#111827", note: "카드" },
  { name: "--surface-2", hex: "#0F172A", note: "카드 안쪽 영역" },
  { name: "--border", hex: "#1E293B", note: "경계선" },
  { name: "--text", hex: "#E2E8F0", note: "본문" },
  { name: "--text-dim", hex: "#94A3B8", note: "보조 텍스트" },
  { name: "--text-mute", hex: "#64748B", note: "각주·비활성" },
  { name: "--sky", hex: "#38BDF8", note: "강조" },
  { name: "--violet", hex: "#A78BFA", note: "강조" },
  { name: "--green", hex: "#4ADE80", note: "긍정" },
  { name: "--amber", hex: "#FBBF24", note: "주의" },
  { name: "--red", hex: "#F87171", note: "위험" },
  { name: "--indigo", hex: "#818CF8", note: "범주 전용" },
  { name: "--pink", hex: "#F472B6", note: "범주 전용" },
];

const GRADE_NOTE: Record<Grade, string> = {
  CRITICAL: "Top-3 < 70%",
  NEEDS_IMPROVEMENT: "70 ~ 85%",
  FAIR: "85 ~ 95%",
  GOOD: "≥ 95%",
};

const PRIORITY_NOTE: Record<Priority, string> = {
  HIGH: "가장 먼저",
  MEDIUM: "그다음",
  LOW: "여유 있을 때",
};

const SPACES = [1, 2, 3, 4, 5, 6, 7, 8] as const;
const SPACE_PX = ["4px", "8px", "12px", "16px", "24px", "32px", "48px", "64px"];

const RADII = [
  { name: "--radius-sm", value: "6px" },
  { name: "--radius-md", value: "10px" },
  { name: "--radius-lg", value: "16px" },
];

/** tabular-nums 효과를 보이려면 자릿수가 다른 값이 섞여 있어야 한다. */
const ACCURACIES = [
  { type: "직접 질문", value: "95.5" },
  { type: "파라미터 기반", value: "83.3" },
  { type: "사용자 자연어", value: "75.0" },
  { type: "짧은 키워드", value: "72.7" },
  { type: "한영 혼합", value: "40.0" },
];

function Swatch({
  token,
  hex,
  note,
}: {
  token: string;
  hex?: string;
  note: string;
}) {
  return (
    <div className={styles.swatch}>
      <div className={styles.swatchChip} style={{ background: cssVar(token) }} />
      <div className={styles.swatchBody}>
        <code className={styles.swatchName}>{token}</code>
        <span className={styles.swatchMeta}>
          {hex ? `${hex} · ${note}` : note}
        </span>
      </div>
    </div>
  );
}

export default function TokensPage() {
  const grades = Object.keys(gradeColorVar) as Grade[];
  const priorities = Object.keys(priorityColorVar) as Priority[];
  const questionTypes = Object.keys(questionTypeColorVar) as QuestionType[];

  return (
    <main className={styles.page}>
      <h1 className={styles.title}>디자인 토큰</h1>
      <p className={styles.lead}>
        컴포넌트는 여기 있는 <code>var(--token)</code> 만 쓴다. hex 를 직접 적지 않는다.
        <br />
        색과 라벨 매핑은 <code>src/lib/enumTokens.ts</code> 한 곳에만 있다.
      </p>

      {/* --- 원색 --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>1. 원색</h2>
        <p className={styles.sectionNote}>
          팔레트. 컴포넌트에서 직접 쓰지 않는다.
          <code>--indigo</code> 와 <code>--pink</code> 는 도넛 7종을 채우려고 추가했다 —
          강조색 5개로는 모자란다.
        </p>
        <div className={styles.swatchGrid}>
          {BASE_COLORS.map((color) => (
            <Swatch
              key={color.name}
              token={color.name}
              hex={color.hex}
              note={color.note}
            />
          ))}
        </div>
      </section>

      {/* --- 등급 --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>2. 상태색 — 등급 (grade)</h2>
        <p className={styles.sectionNote}>
          기준과 라벨 모두 docs/contract.md §3 확정안.
        </p>
        <div className={styles.swatchGrid}>
          {grades.map((grade) => (
            <Swatch
              key={grade}
              token={gradeColorVar[grade]}
              note={`${gradeLabel[grade]} · ${grade} · ${GRADE_NOTE[grade]}`}
            />
          ))}
        </div>
      </section>

      {/* --- 우선순위 --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>2. 상태색 — 우선순위 (priority)</h2>
        <p className={styles.sectionNote}>
          시안의 권장조치 카드가 red / sky 2단계로만 구분한다.
          <strong> amber 는 grade 전용</strong>이다 — priority 에 쓰면 화면에서
          &ldquo;개선 필요(등급)&rdquo;와 &ldquo;MEDIUM(우선순위)&rdquo;이 같은 색으로
          나와 무엇을 가리키는지 알 수 없게 된다. LOW 는 색을 빼서 시선을 끌지 않게 한다.
        </p>
        <div className={styles.swatchGrid}>
          {priorities.map((priority) => (
            <Swatch
              key={priority}
              token={priorityColorVar[priority]}
              note={`${priority} · ${PRIORITY_NOTE[priority]}`}
            />
          ))}
        </div>
      </section>

      {/* --- 질문 유형 --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>3. 범주색 — 질문 유형 (questionType)</h2>
        <p className={styles.sectionNote}>
          <strong>범주 구분용이며 상태(위험/주의)를 의미하지 않는다.</strong>
          <br />
          <code>--chart-type-error-case</code> 가 red 인 것은 &ldquo;오류 상황 질문&rdquo;이
          나쁘다는 뜻이 아니라, 도넛에서 옆 조각과 구분되어야 하기 때문이다.
          유형별 인식률의 좋고 나쁨은 등급 토큰이 따로 표현한다.
        </p>
        <div className={styles.swatchGrid}>
          {questionTypes.map((type) => (
            <Swatch
              key={type}
              token={questionTypeColorVar[type]}
              note={`${questionTypeLabel[type]} · ${type}`}
            />
          ))}
        </div>

        <p className={styles.sectionNote}>도넛에서 인접했을 때 구분되는지 확인:</p>
        <div className={styles.donutStrip}>
          {questionTypes.map((type) => (
            <div
              key={type}
              className={styles.donutSlice}
              style={{ background: cssVar(questionTypeColorVar[type]) }}
              title={questionTypeLabel[type]}
            />
          ))}
        </div>
      </section>

      {/* --- 간격 --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>간격</h2>
        <p className={styles.sectionNote}>4px 배수. 이 8단계 밖의 값을 쓰지 않는다.</p>
        {SPACES.map((step, i) => (
          <div key={step} className={styles.spaceRow}>
            <code className={styles.spaceLabel}>--space-{step}</code>
            <div
              className={styles.spaceBar}
              style={{ width: cssVar(`--space-${step}`) }}
            />
            <span className={styles.spaceValue}>{SPACE_PX[i]}</span>
          </div>
        ))}
      </section>

      {/* --- 모서리 · 그림자 --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>모서리 · 그림자</h2>
        <p className={styles.sectionNote}>
          어두운 배경에서는 그림자만으로 카드가 떠 보이지 않는다. 경계선을 함께 쓴다.
        </p>
        <div className={styles.boxRow}>
          {RADII.map((radius) => (
            <div
              key={radius.name}
              className={styles.box}
              style={{ borderRadius: cssVar(radius.name) }}
            >
              <code className={styles.boxName}>{radius.name}</code>
              <span className={styles.boxValue}>{radius.value}</span>
            </div>
          ))}
          <div className={styles.shadowBox}>
            <code className={styles.boxName}>--shadow-card</code>
            <span className={styles.boxValue}>+ --radius-md</span>
          </div>
        </div>
      </section>

      {/* --- 폰트 --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>폰트</h2>
        <p className={styles.sectionNote}>
          <strong>현재 시스템 폰트 fallback 상태다.</strong> 폰트 파일이 아직 저장소에 없다.
          넣는 절차는 <code>src/styles/fonts/README.md</code>,
          설정은 <code>src/app/fonts.ts</code>(주석 처리됨) 참고.
        </p>

        <div className={styles.fontRow}>
          <span className={styles.fontLabel}>본문 · --font-sans (Pretendard 예정)</span>
          <p className={styles.sampleSans}>
            환불 신청은 어떻게 취소하나요? Swagger 명세의 RAG 검색 인식률 0123456789
          </p>
          <div className={styles.weights}>
            <span className={styles.w400}>Regular 400</span>
            <span className={styles.w500}>Medium 500</span>
            <span className={styles.w600}>SemiBold 600</span>
            <span className={styles.w700}>Bold 700</span>
          </div>
        </div>

        <div className={styles.fontRow}>
          <span className={styles.fontLabel}>
            수치·경로 · --font-mono (JetBrains Mono 예정)
          </span>
          <p className={styles.sampleMono}>
            GET /orders/{"{id}"}/refund-status — 0.812 / 78.0%
          </p>
        </div>
      </section>

      {/* --- tabular-nums --- */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>tabular-nums</h2>
        <p className={styles.sectionNote}>
          <code>.tabular</code> 유틸 클래스. 숫자 폭이 고정돼 자릿수가 달라도 세로로
          정렬된다. 오른쪽 열이 흔들리면 값을 비교할 수 없다.
        </p>
        <table className={styles.numTable}>
          <thead>
            <tr>
              <th>문항 유형</th>
              <th className={styles.numRight}>기본 폰트</th>
              <th className={styles.numRight}>.tabular</th>
            </tr>
          </thead>
          <tbody>
            {ACCURACIES.map((row) => (
              <tr key={row.type}>
                <td>{row.type}</td>
                <td className={`${styles.numRight} ${styles.proportional}`}>
                  {row.value}%
                </td>
                <td className={`${styles.numRight} tabular`}>{row.value}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
