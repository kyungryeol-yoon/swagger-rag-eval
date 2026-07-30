"use client";

import StateNotice from "@/components/common/StateNotice/StateNotice";

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
 * 원인 요약은 **개발 환경에서만** 보여준다 — 운영에서는 Next 가 message 를
 * 지우고 digest 만 남기므로 보여줄 것도 없고, 남아 있다 해도 내부 경로나
 * 주소를 사용자 화면에 흘릴 이유가 없다.
 */

const isDevelopment = process.env.NODE_ENV === "development";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <StateNotice
      title="평가 리포트를 불러오지 못했습니다"
      steps={[
        <>
          백엔드(8000)가 실행 중인지 확인합니다 — <code>make dev</code>
        </>,
        <>
          직접 열어봅니다 — <code>http://localhost:8000/health</code>
        </>,
        <>
          데이터 소스가 읽히는지 봅니다 — <code>http://localhost:8000/ready</code>
        </>,
        <>
          주소가 다르면 <code>API_BASE_URL</code> 을 확인합니다
        </>,
      ]}
      detail={isDevelopment ? formatCause(error) : undefined}
      actions={
        <button
          type="button"
          className="noticeButton noticeButtonPrimary"
          onClick={reset}
        >
          다시 시도
        </button>
      }
    >
      <p>
        평가 요청이 실패했습니다. 백엔드에 연결하지 못했거나 응답이 올바르지
        않습니다. 대시보드는 백엔드 없이는 아무것도 표시할 수 없습니다.
      </p>
      <p>
        평가는 <strong>요청할 때마다 실행</strong>됩니다. 다시 시도하면 처음부터
        평가합니다.
      </p>
      {/* digest 는 운영에서 로그와 화면을 잇는 유일한 끈이라 항상 남긴다. */}
      {error.digest && <p>오류 식별자: {error.digest}</p>}
    </StateNotice>
  );
}

/**
 * 개발 환경에서 보여줄 원인 요약.
 *
 * `lib/api.ts` 가 message 에 원인·호출 주소·백엔드가 준 detail 을 줄바꿈으로
 * 이어 붙여 둔다. 계약 위반이면 어느 필드가 없는지가 여기 그대로 들어온다.
 */
function formatCause(error: Error & { digest?: string }): string {
  const lines = [error.message];
  if (error.digest) {
    lines.push(`digest: ${error.digest}`);
  }
  return lines.join("\n");
}
