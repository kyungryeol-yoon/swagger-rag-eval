"use client";

import styles from "./states.module.css";

/**
 * 에러 화면.
 *
 * **`'use client'` 는 여기서만 예외다.** Next 의 에러 경계는 클라이언트
 * 컴포넌트여야 하고 `reset` 도 클라이언트에서만 동작한다. 다른 컴포넌트는
 * 전부 서버 컴포넌트다.
 *
 * 사과하지 않는다. 무엇이 실패했고 무엇을 하면 되는지만 적는다
 * (docs/prompts.md §9-4).
 *
 * 로컬에서 이 화면이 뜨는 가장 흔한 이유는 백엔드가 안 떠 있는 것이다.
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className={styles.notice}>
      <h1 className={styles.noticeTitle}>평가 리포트를 불러오지 못했습니다</h1>

      <p className={styles.noticeBody}>
        백엔드 API에 연결하지 못했거나 응답이 올바르지 않습니다.
        대시보드는 백엔드 없이는 아무것도 표시할 수 없습니다.
      </p>

      <div className={styles.checklist}>
        <ol>
          <li>
            백엔드(8000)가 실행 중인지 확인합니다 — <code>make dev</code>
          </li>
          <li>
            직접 열어봅니다 — <code>http://localhost:8000/health</code>
          </li>
          <li>
            평가 결과가 있는지 봅니다 — <code>http://localhost:8000/ready</code>
          </li>
          <li>
            주소가 다르면 <code>API_BASE_URL</code> 을 확인합니다
          </li>
        </ol>
      </div>

      {error.message && <p className={styles.detail}>{error.message}</p>}
      {error.digest && <p className={styles.detail}>digest: {error.digest}</p>}

      <div className={styles.actions}>
        <button type="button" className={styles.buttonPrimary} onClick={reset}>
          다시 시도
        </button>
      </div>
    </main>
  );
}
