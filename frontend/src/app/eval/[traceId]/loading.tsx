import styles from "./states.module.css";

/**
 * 로딩 스켈레톤.
 *
 * 실제 화면과 **같은 골격·같은 높이**를 잡아둔다. 스피너 하나로 때우면
 * 데이터가 도착하는 순간 레이아웃이 튀고, 그게 매번 반복되면 화면이
 * 불안정해 보인다.
 *
 * 평가는 수십 초 걸린다. 진행 중 화면이 실제로는 가장 자주 보이는 화면이다
 * (docs/prompts.md §9-4).
 */
export default function Loading() {
  return (
    <main className={styles.page} aria-busy="true" aria-label="평가 리포트를 불러오는 중">
      <div className={styles.headerRow}>
        <div>
          <span className={`${styles.bar} ${styles.w120} ${styles.h10}`} />
          <span className={`${styles.bar} ${styles.w280} ${styles.h22}`} />
        </div>
        <div className={styles.metaRow}>
          {[0, 1, 2, 3].map((i) => (
            <span key={i} className={`${styles.bar} ${styles.w80} ${styles.h28}`} />
          ))}
        </div>
      </div>

      <div className={styles.hero}>
        <span className={styles.ring} />
        <div className={styles.cardRow}>
          {[0, 1, 2, 3, 4].map((i) => (
            <span key={i} className={styles.card} />
          ))}
        </div>
      </div>

      <span className={`${styles.block} ${styles.h280}`} />
      <span className={`${styles.block} ${styles.h320}`} />
    </main>
  );
}
