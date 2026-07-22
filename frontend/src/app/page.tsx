import styles from "./page.module.css";

/** Phase 1 기동 확인용 플레이스홀더. 대시보드는 Phase 7 에서 조립한다. */
export default function Home() {
  return (
    <main className={styles.main}>
      <h1 className={styles.title}>swagger-rag-eval</h1>
      <p className={styles.lead}>
        Swagger 명세의 RAG 검색 인식률 평가 대시보드 — 스캐폴딩(Phase 1)
      </p>
    </main>
  );
}
