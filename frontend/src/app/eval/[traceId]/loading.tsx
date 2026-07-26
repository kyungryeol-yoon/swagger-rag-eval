import styles from "./states.module.css";

/**
 * 로딩 스켈레톤.
 *
 * **실제 조립 레이아웃과 같은 골격을 그린다** — 같은 격자, 같은 순서, 같은
 * 카드 높이다. 스피너 하나로 때우거나 뭉뚱그린 블록 두 개를 놓으면, 데이터가
 * 도착하는 순간 레이아웃이 통째로 튄다. 그게 매번 반복되면 화면이 불안정해
 * 보이고, 사용자는 로딩이 끝난 뒤에도 눈으로 위치를 다시 찾아야 한다.
 *
 * 그래서 여기 격자는 page.module.css 를 그대로 따라간다:
 *   헤더 / 행1 앱정보+요약 / 행2 평가기준+문항유형 / 쿼리 품질 /
 *   행3 좌(막대+문항표) 우(권장조치+권장액션)
 * 한쪽을 고치면 다른 쪽도 고쳐야 한다. 어긋나면 레이아웃 시프트로 바로 보인다.
 *
 * 평가는 수십 초 걸린다. 진행 중 화면이 실제로는 가장 자주 보이는 화면이다
 * (docs/prompts.md §9-4).
 */
export default function Loading() {
  return (
    <main className={styles.page} aria-busy="true" aria-label="평가 리포트를 불러오는 중">
      {/* 헤더 — 제목(좌) + 메타 한 줄(우) */}
      <div className={styles.header}>
        <div className={styles.headerMain}>
          <span className={`${styles.bar} ${styles.w120} ${styles.h10}`} />
          <span className={`${styles.bar} ${styles.w280} ${styles.h22}`} />
          <span className={`${styles.bar} ${styles.w200} ${styles.h10}`} />
        </div>
        <div className={styles.headerMeta}>
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <span key={i} className={`${styles.bar} ${styles.w80} ${styles.h14}`} />
          ))}
        </div>
      </div>

      {/* 행1 — 앱 정보(300px) + 요약(게이지 + 카드 4장) */}
      <div className={styles.overview}>
        <div className={styles.appCard}>
          <span className={`${styles.bar} ${styles.w160} ${styles.h16}`} />
          <span className={`${styles.bar} ${styles.w120} ${styles.h10}`} />
          <span className={`${styles.bar} ${styles.full} ${styles.h10}`} />
        </div>

        <div className={styles.summaryBox}>
          <span className={`${styles.ring} ${styles.ringSm}`} />
          <div className={styles.summaryCards}>
            {[0, 1, 2, 3].map((i) => (
              <span key={i} className={styles.statCard} />
            ))}
          </div>
        </div>
      </div>

      {/* 행2 — 평가 기준(게이지+구간표) | 문항 유형 분포(도넛+범례) */}
      <div className={styles.rowTwo}>
        <div className={styles.chartCard}>
          <span className={`${styles.bar} ${styles.w120} ${styles.h14}`} />
          <div className={styles.chartBody}>
            <span className={styles.ring} />
            <div className={styles.lines}>
              {[0, 1, 2, 3].map((i) => (
                <span key={i} className={`${styles.bar} ${styles.full} ${styles.h14}`} />
              ))}
            </div>
          </div>
        </div>

        <div className={styles.chartCard}>
          <span className={`${styles.bar} ${styles.w120} ${styles.h14}`} />
          <div className={styles.chartBody}>
            <span className={styles.ring} />
            <div className={styles.lines}>
              {[0, 1, 2, 3, 4].map((i) => (
                <span key={i} className={`${styles.bar} ${styles.full} ${styles.h14}`} />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 쿼리별 설명 품질 — 전체 폭 표 */}
      <div className={styles.table}>
        <span className={styles.tableHead} />
        {[0, 1, 2, 3, 4].map((i) => (
          <span key={i} className={styles.tableRow} />
        ))}
      </div>

      {/* 행3 — 좌: 유형별 막대 + 문항 표 / 우: 권장 조치 + 권장 액션 */}
      <div className={styles.rowMain}>
        <div className={styles.mainCol}>
          <div className={styles.chartCard}>
            <span className={`${styles.bar} ${styles.w160} ${styles.h14}`} />
            <div className={styles.lines}>
              {[0, 1, 2, 3, 4, 5, 6].map((i) => (
                <span key={i} className={`${styles.bar} ${styles.full} ${styles.h14}`} />
              ))}
            </div>
          </div>

          <div className={styles.table}>
            <span className={styles.tableHead} />
            {[0, 1, 2, 3, 4].map((i) => (
              <span key={i} className={styles.tableRowTall} />
            ))}
          </div>
        </div>

        <div className={styles.mainCol}>
          <div className={styles.chartCard}>
            <span className={`${styles.bar} ${styles.w120} ${styles.h14}`} />
            {[0, 1, 2].map((i) => (
              <span key={i} className={styles.recoCard} />
            ))}
          </div>
          <div className={styles.actionCard}>
            <span className={`${styles.bar} ${styles.w120} ${styles.h14}`} />
            <span className={`${styles.bar} ${styles.full} ${styles.h10}`} />
            <span className={styles.button} />
            <span className={styles.button} />
          </div>
        </div>
      </div>
    </main>
  );
}
