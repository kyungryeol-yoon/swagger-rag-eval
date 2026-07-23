import { TriangleAlert } from "lucide-react";

import type { Priority, Recommendation } from "@/lib/types";

import styles from "./ActionPanel.module.css";

/**
 * 권장 액션 카드 — 시안 우하단.
 *
 * 서버 컴포넌트다. **`onClick` 을 달지 않는다.** 평가 엔진이 아직 없어
 * 버튼은 둘 다 비활성이고, 확인 다이얼로그도 활성화 시점에 만든다
 * (지금 만들면 `'use client'` 가 필요해지는데 동작할 대상이 없다).
 */

/** 높을수록 먼저. HIGH → MEDIUM → LOW. */
const PRIORITY_RANK: Record<Priority, number> = {
  HIGH: 0,
  MEDIUM: 1,
  LOW: 2,
};

/**
 * 요약 문장에 쓸 "가장 큰 원인" 한 건.
 *
 * **failShare 를 더하지 않는다.** 시안의 "실패 원인 중 62%" 는 카드의
 * 45/23/32% 와 맞지 않는 값이었다 (contract.md §5 알려진 오류).
 * failShare 는 한 실패에 원인이 둘 이상일 수 있어 중복 집계되므로
 * 합산 자체가 의미를 갖지 못한다. 그래서 **한 건만 골라 그 값만 인용한다.**
 *
 * 고르는 순서:
 *   1. 우선순위 (HIGH → MEDIUM → LOW)
 *   2. failShare 큰 순
 *   3. order 작은 순 — 동률일 때 화면이 매번 달라지지 않게 한다
 */
export function pickLeadingCause(
  recommendations: Recommendation[],
): Recommendation | null {
  if (recommendations.length === 0) {
    return null;
  }

  return [...recommendations].sort((a, b) => {
    const byPriority = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
    if (byPriority !== 0) {
      return byPriority;
    }
    const byShare = b.failShare - a.failShare;
    if (byShare !== 0) {
      return byShare;
    }
    return a.order - b.order;
  })[0];
}

/**
 * 조사 "으로 / 로" 를 고른다.
 *
 * 제목은 백엔드가 내려주므로 문장에 조사를 고정할 수 없다.
 * "보강" 뒤에는 "으로", "추가" 뒤에는 "로" 다 — 고정하면 둘 중 하나는 반드시 틀린다.
 *
 * 규칙: 받침이 없거나 받침이 ㄹ 이면 "로", 그 외에는 "으로".
 */
function particleRo(word: string): string {
  const last = word.trim().slice(-1);
  if (!last) {
    return "으로";
  }

  const code = last.charCodeAt(0);
  const isHangulSyllable = code >= 0xac00 && code <= 0xd7a3;
  if (!isHangulSyllable) {
    // 영문·숫자·기호로 끝나면 발음을 알 수 없다. 더 흔한 쪽으로 둔다.
    return "으로";
  }

  const finalConsonant = (code - 0xac00) % 28;
  const NO_FINAL = 0;
  const RIEUL = 8;
  return finalConsonant === NO_FINAL || finalConsonant === RIEUL ? "로" : "으로";
}

export type ActionPanelProps = {
  recommendations: Recommendation[];
  /** 재생성 대상 명세. 어느 명세가 덮어써지는지 밝힌다. */
  specId?: string;
};

export default function ActionPanel({ recommendations, specId }: ActionPanelProps) {
  const leading = pickLeadingCause(recommendations);

  // 근거가 없으면 카드를 만들지 않는다. 버튼만 남은 카드는 무엇을 위한
  // 조치인지 알 수 없다.
  if (!leading) {
    return null;
  }

  return (
    <section className={styles.root}>
      <header className={styles.header}>
        <h2 className={styles.title}>권장 액션</h2>
        {specId && <span className={`${styles.target} tabular`}>{specId}</span>}
      </header>

      <p className={styles.summary}>
        가장 큰 원인은 <strong className={styles.cause}>&lsquo;{leading.title}&rsquo;</strong>
        {particleRo(leading.title)}, 실패의{" "}
        <span className={`${styles.share} tabular`}>{leading.failShare.toFixed(1)}%</span>가
        여기 해당합니다.
      </p>

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.secondary}
          disabled
          aria-disabled="true"
          title="평가 엔진 연동 후 활성화됩니다"
        >
          설명 직접 수정
        </button>

        {/* 파괴적 동작이라 아이콘으로 먼저 표시한다. 문구만으로는
            "다시 만들기" 가 덮어쓰기라는 것이 읽히지 않는다 (§9-3). */}
        <button
          type="button"
          className={styles.primary}
          disabled
          aria-disabled="true"
          title="평가 엔진 연동 후 활성화됩니다"
        >
          <TriangleAlert className={styles.icon} size={14} aria-hidden="true" />
          AI로 설명 다시 만들기
        </button>
      </div>

      <p className={styles.warning}>재생성하면 기존 설명이 교체됩니다.</p>
    </section>
  );
}
