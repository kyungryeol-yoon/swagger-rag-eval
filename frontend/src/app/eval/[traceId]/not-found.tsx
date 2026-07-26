import Link from "next/link";

import StateNotice from "@/components/common/StateNotice/StateNotice";

/**
 * 해당 추적 ID의 평가 결과가 없을 때.
 *
 * 백엔드가 404 를 준 경우에만 여기로 온다. 연결 실패는 error.tsx 가 받는다 —
 * "결과가 없다" 와 "백엔드가 죽었다" 는 해야 할 일이 다르다.
 *
 * 나가는 문은 **최신 평가**다. 특정 추적 ID(A492)를 박아두면 그 fixture 가
 * 사라지는 순간 안내가 또 다른 404 로 이어진다. 루트("/")가 목록을 보고
 * 최신으로 보내주므로 그쪽으로만 걸어둔다.
 */
export default function NotFound() {
  return (
    <StateNotice
      title="평가 결과가 없습니다"
      steps={[
        "추적 ID의 철자를 확인합니다",
        "그 앱으로 평가를 실행한 적이 있는지 확인합니다",
        <>
          저장된 평가 목록을 직접 봅니다 —{" "}
          <code>http://localhost:8000/api/v1/evaluations</code>
        </>,
      ]}
      actions={
        <Link className="noticeButton noticeButtonPrimary" href="/">
          최신 평가 보기
        </Link>
      }
    >
      <p>
        요청한 추적 ID로 저장된 평가 결과를 찾지 못했습니다. ID를 잘못 입력했거나,
        아직 그 앱으로 평가를 실행하지 않았습니다.
      </p>
    </StateNotice>
  );
}
