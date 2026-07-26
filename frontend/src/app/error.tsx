"use client";

import StateNotice from "@/components/common/StateNotice/StateNotice";

/**
 * 앱 최상단 에러 경계.
 *
 * `/eval/[traceId]` 밑에는 자기 경계가 따로 있다(그 화면은 안내 문구가 다르다).
 * 여기가 받는 것은 그 바깥 — 주로 **루트에서 평가 목록을 못 가져온 경우**다.
 * 경계가 없으면 Next 의 기본 오류 화면이 뜨는데, 거기에는 무엇을 하면 되는지가
 * 없다.
 *
 * `'use client'` 는 Next 의 에러 경계 규약이라 어쩔 수 없다.
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
      title="평가 목록을 불러오지 못했습니다"
      steps={[
        <>
          백엔드(8000)가 실행 중인지 확인합니다 — <code>make dev</code>
        </>,
        <>
          직접 열어봅니다 — <code>http://localhost:8000/health</code>
        </>,
        <>
          주소가 다르면 <code>API_BASE_URL</code> 을 확인합니다
        </>,
      ]}
      detail={isDevelopment ? error.message : undefined}
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
        어느 평가를 보여줄지 정하려면 백엔드에서 평가 목록을 받아야 합니다. 그
        요청이 실패했습니다.
      </p>
      {error.digest && <p>오류 식별자: {error.digest}</p>}
    </StateNotice>
  );
}
