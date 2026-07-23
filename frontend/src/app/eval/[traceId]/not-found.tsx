import Link from "next/link";

import styles from "./states.module.css";

/**
 * 해당 추적 ID의 평가 결과가 없을 때.
 *
 * 백엔드가 404 를 준 경우에만 여기로 온다. 연결 실패는 error.tsx 가 받는다 —
 * "결과가 없다" 와 "백엔드가 죽었다" 는 해야 할 일이 다르다.
 */
export default function NotFound() {
  return (
    <main className={styles.notice}>
      <h1 className={styles.noticeTitle}>평가 결과가 없습니다</h1>

      <p className={styles.noticeBody}>
        요청한 추적 ID로 저장된 평가 결과를 찾지 못했습니다. ID를 잘못 입력했거나,
        아직 그 명세로 평가를 실행하지 않았습니다.
      </p>

      <div className={styles.checklist}>
        <ol>
          <li>
            추적 ID 철자를 확인합니다 — 로컬 샘플은 <code>A492</code> 입니다
          </li>
          <li>
            백엔드에 직접 물어봅니다 —{" "}
            <code>http://localhost:8000/api/v1/evaluations/A492</code>
          </li>
        </ol>
      </div>

      <div className={styles.actions}>
        <Link className={styles.buttonPrimary} href="/eval/A492">
          샘플 리포트 보기
        </Link>
      </div>
    </main>
  );
}
