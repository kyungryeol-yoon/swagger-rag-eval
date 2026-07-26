import { questionTypeColor, questionTypeLabel } from "@/lib/enumTokens";
import type { QuestionType, QuestionTypeStat } from "@/lib/types";

import styles from "./QuestionTypeChart.module.css";

/**
 * 문항 유형 분포(도넛) + 유형별 인식률(막대).
 *
 * 시안에는 분포만 있었다. **유형별 인식률이 이 대시보드에서 가장 중요한
 * 정보다** — 분포만 보면 "한영 혼합이 10%" 로 끝이지만, 인식률을 같이 보면
 * "한영 혼합에서 40%" 가 되어 무엇을 고칠지가 정해진다 (contract.md §5).
 *
 * 순수 SVG. 서버 컴포넌트.
 */

/** 조각 사이 간격(도). 조각이 하나뿐이면 원이 닫혀야 하므로 쓰지 않는다. */
const GAP_DEGREES = 1.5;

const DONUT_VIEWBOX = 100;
const DONUT_STROKE = 14;
const DONUT_RADIUS = (DONUT_VIEWBOX - DONUT_STROKE) / 2;
const DONUT_CIRCUMFERENCE = 2 * Math.PI * DONUT_RADIUS;

// ---------------------------------------------------------------------------
// 각도 계산 — 순수 함수
// ---------------------------------------------------------------------------

export type DonutSegment = {
  type: QuestionType;
  count: number;
  startAngle: number;
  endAngle: number;
  sweepAngle: number;
};

/**
 * 각 유형의 시작·끝 각도.
 *
 * **`ratio` 가 아니라 `count` 로 계산한다.** ratio 는 백엔드에서 반올림돼
 * 내려오므로 합이 정확히 100 이 아닐 수 있고(99.9 / 100.1), 그대로 각도로
 * 바꾸면 마지막 조각이 덜 닫히거나 첫 조각을 덮는다.
 *
 * 누적 개수를 전체로 나눠 각도를 만들면 마지막 끝각이 항상 정확히 360 이다.
 * 조각마다 각도를 구해 더하는 방식은 오차가 쌓인다.
 *
 * count 가 0 인 유형은 시작각과 끝각이 같아진다. 호출부에서 걸러 그리지 않되
 * 범례에는 남긴다 — 그 유형으로 만든 문항이 0개라는 것도 정보다.
 */
export function toDonutSegments(items: QuestionTypeStat[]): DonutSegment[] {
  const total = items.reduce((sum, item) => sum + item.count, 0);

  if (total <= 0) {
    return items.map((item) => ({
      type: item.type,
      count: item.count,
      startAngle: 0,
      endAngle: 0,
      sweepAngle: 0,
    }));
  }

  let cumulative = 0;
  return items.map((item) => {
    const startAngle = (cumulative / total) * 360;
    cumulative += item.count;
    const endAngle = (cumulative / total) * 360;
    return {
      type: item.type,
      count: item.count,
      startAngle,
      endAngle,
      sweepAngle: endAngle - startAngle,
    };
  });
}

// ---------------------------------------------------------------------------
// 표기
// ---------------------------------------------------------------------------

const formatPercent = (value: number) => value.toFixed(1);

// ---------------------------------------------------------------------------
// 컴포넌트
// ---------------------------------------------------------------------------

export type QuestionTypeChartProps = {
  questionTypes: QuestionTypeStat[];
  /** 전체 Top-3 인식률. 막대 차트의 기준선이 된다. */
  overallTop3Accuracy: number;
  /**
   * 어느 부분을 그릴지. 계산 로직은 그대로 두고 렌더만 나눈다.
   * "all"(기본): 도넛+범례 | 막대. "distribution": 도넛+범례만.
   * "bars": 유형별 인식률 막대만. 도넛과 막대를 다른 카드로 떼어 놓을 때 쓴다.
   */
  show?: "all" | "distribution" | "bars";
};

export default function QuestionTypeChart({
  questionTypes,
  overallTop3Accuracy,
  show = "all",
}: QuestionTypeChartProps) {
  // 유형 목록 자체가 비면 도넛도 막대도 그릴 것이 없다. 빈 원과 빈 범례를
  // 남기면 "유형이 없다" 가 아니라 "차트가 깨졌다" 로 읽힌다.
  if (questionTypes.length === 0) {
    return (
      <div className={styles.root}>
        <p className={styles.emptyTitle}>문항 유형 정보가 없습니다</p>
        <p className={styles.emptyBody}>
          이 평가 결과에는 문항 유형 분류가 담겨 있지 않습니다.
        </p>
      </div>
    );
  }

  const segments = toDonutSegments(questionTypes);
  const total = questionTypes.reduce((sum, item) => sum + item.count, 0);
  const visible = segments.filter((segment) => segment.sweepAngle > 0);

  // 조각이 하나뿐이면 간격을 두지 않는다. 간격을 그대로 두면 100% 인데
  // 원이 안 닫혀서 데이터가 잘못된 것처럼 보인다.
  const gap = visible.length > 1 ? GAP_DEGREES : 0;

  // 낮은 인식률이 위로 온다. 개선 대상이 먼저 보여야 한다.
  //
  // **문항이 0개인 유형은 막대에서 뺀다.** 그런 유형의 top3Accuracy 는 0 으로
  // 내려오는데(나눌 것이 없다), 막대로 그리면 길이 0 짜리 막대가 맨 위에 서서
  // "이 유형은 전부 실패" 처럼 보인다. 아무도 묻지 않은 유형일 뿐이다.
  // 범례에는 남긴다 — 0건이라는 사실 자체는 정보다.
  const ranked = questionTypes
    .filter((item) => item.count > 0)
    .sort((a, b) => a.top3Accuracy - b.top3Accuracy);

  // 기준선 위치와 라벨 정렬. 양 끝에서는 라벨을 안쪽으로 붙여 카드를 넘지 않게 한다.
  const refPosition = Math.min(100, Math.max(0, overallTop3Accuracy));
  const refLabelShift =
    refPosition <= 6 ? "translateX(0)" : refPosition >= 94 ? "translateX(-100%)" : undefined;

  const donutLabel = `문항 유형 분포. 전체 ${total}개. ${questionTypes
    .map((item) => `${questionTypeLabel[item.type]} ${item.count}개`)
    .join(", ")}`;

  const barsLabel = `유형별 Top-3 인식률. 전체 ${formatPercent(
    overallTop3Accuracy,
  )} 퍼센트. 낮은 순으로 ${ranked
    .map((item) => `${questionTypeLabel[item.type]} ${formatPercent(item.top3Accuracy)} 퍼센트`)
    .join(", ")}`;

  return (
    <div className={styles.root}>
      {/* 안쪽 그리드. container 쿼리는 컨테이너(.root)의 "자손" 만 다시 그릴 수
          있으므로, 2단 그리드는 .root 가 아니라 이 안쪽 요소에 둔다. */}
      {/* 한쪽만 그릴 때는 2단 격자를 쓰지 않는다. 그대로 두면 도넛이나 막대가
          카드의 절반만 채우고 나머지 절반이 빈 채로 남는다. */}
      <div className={`${styles.grid} ${show === "all" ? "" : styles.gridSingle}`}>
        {/* --- 분포: 도넛 + 범례 --- */}
        {show !== "bars" && (
        <section className={styles.distribution}>
        <h3 className={styles.heading}>문항 유형 분포</h3>

        <div className={styles.distributionBody}>
          <div className={styles.donutWrap} role="img" aria-label={donutLabel}>
            <svg
              className={styles.donut}
              viewBox={`0 0 ${DONUT_VIEWBOX} ${DONUT_VIEWBOX}`}
              aria-hidden="true"
              focusable="false"
            >
              <circle
                className={styles.donutTrack}
                cx={DONUT_VIEWBOX / 2}
                cy={DONUT_VIEWBOX / 2}
                r={DONUT_RADIUS}
                strokeWidth={DONUT_STROKE}
              />
              {visible.map((segment) => (
                <Slice key={segment.type} segment={segment} gap={gap} />
              ))}
            </svg>

            <div className={styles.donutCenter} aria-hidden="true">
              <span className={`${styles.donutTotal} tabular`}>{total}</span>
              <span className={styles.donutUnit}>문항</span>
            </div>
          </div>

          <table className={styles.legend}>
            <caption className="srOnly">문항 유형별 개수, 비율, Top-3 인식률</caption>
            <thead>
              <tr>
                <th scope="col">유형</th>
                <th scope="col" className={styles.numeric}>
                  개수
                </th>
                <th scope="col" className={styles.numeric}>
                  비율
                </th>
                <th scope="col" className={styles.numeric}>
                  Top-3 인식률
                </th>
              </tr>
            </thead>
            <tbody>
              {questionTypes.map((item) => (
                <tr key={item.type}>
                  <th scope="row" className={styles.legendLabel}>
                    <span
                      className={styles.dot}
                      style={{ background: questionTypeColor(item.type) }}
                      aria-hidden="true"
                    />
                    {questionTypeLabel[item.type]}
                  </th>
                  <td className={`${styles.numeric} tabular`}>{item.count}</td>
                  <td className={`${styles.numeric} tabular`}>
                    {formatPercent(item.ratio)}%
                  </td>
                  {/* 문항이 0건이면 인식률이라는 값 자체가 없다. 0.0% 로 적으면
                      "다 틀렸다" 로 읽힌다 — 대시로 없음을 명시한다. */}
                  <td className={`${styles.numeric} tabular`}>
                    {item.count > 0 ? `${formatPercent(item.top3Accuracy)}%` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
        )}

      {/* --- 유형별 인식률 막대 --- */}
      {show !== "distribution" && (
      <section className={styles.accuracy}>
        <h3 className={styles.heading}>
          유형별 Top-3 인식률
          <span className={styles.headingNote}>낮은 순</span>
        </h3>

        <div className={styles.bars} role="img" aria-label={barsLabel}>
          {ranked.map((item) => (
            <div key={item.type} className={styles.barRow}>
              <span className={styles.barLabel}>{questionTypeLabel[item.type]}</span>
              <span className={styles.barTrack}>
                <span
                  className={styles.barFill}
                  style={{
                    width: `${Math.min(100, Math.max(0, item.top3Accuracy))}%`,
                    background: questionTypeColor(item.type),
                  }}
                />
              </span>
              <span className={`${styles.barValue} tabular`}>
                {formatPercent(item.top3Accuracy)}%
              </span>
            </div>
          ))}

          {/*
            전체 인식률 기준선. 막대와 같은 그리드 열에 겹쳐 놓아 트랙 폭과
            정확히 맞춘다. 평균 아래 유형이 한눈에 드러난다 —
            등급을 다시 계산하지 않고도 같은 효과를 낸다.
          */}
          <div className={styles.overlay} aria-hidden="true">
            <div className={styles.refLine} style={{ left: `${refPosition}%` }}>
              {/*
                라벨은 기본적으로 선 위에 가운데 정렬된다. 그런데 인식률이 0%
                이거나 100% 면 절반이 트랙 밖으로 빠져나가 옆 카드를 침범한다
                (실패 0건 / 전부 실패 fixture 에서 실제로 그렇다).
                양 끝에서는 안쪽으로 붙인다.
              */}
              <span className={styles.refLabel} style={{ transform: refLabelShift }}>
                전체 {formatPercent(overallTop3Accuracy)}%
              </span>
            </div>
          </div>
        </div>
      </section>
        )}
      </div>
    </div>
  );
}

function Slice({ segment, gap }: { segment: DonutSegment; gap: number }) {
  // 간격만큼 양쪽에서 깎는다. 조각이 간격보다 얇으면 0 이 되어 사라진다 —
  // 억지로 그리면 옆 조각을 침범한다.
  const drawn = Math.max(0, segment.sweepAngle - gap);
  if (drawn <= 0) {
    return null;
  }

  const arcLength = (DONUT_CIRCUMFERENCE * drawn) / 360;
  const offset = -(DONUT_CIRCUMFERENCE * (segment.startAngle + gap / 2)) / 360;

  return (
    <circle
      className={styles.slice}
      cx={DONUT_VIEWBOX / 2}
      cy={DONUT_VIEWBOX / 2}
      r={DONUT_RADIUS}
      strokeWidth={DONUT_STROKE}
      stroke={questionTypeColor(segment.type)}
      strokeDasharray={`${arcLength} ${DONUT_CIRCUMFERENCE}`}
      strokeDashoffset={offset}
    />
  );
}
