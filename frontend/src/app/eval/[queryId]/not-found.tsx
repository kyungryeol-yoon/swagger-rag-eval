import Link from "next/link";

import StateNotice from "@/components/common/StateNotice/StateNotice";

/**
 * 그 `query_id` 의 쿼리를 찾지 못했을 때.
 *
 * 백엔드가 404 를 준 경우에만 여기로 온다. 연결 실패는 error.tsx 가 받는다 —
 * "그런 쿼리가 없다" 와 "백엔드가 죽었다" 는 해야 할 일이 다르다.
 *
 * **"평가 결과가 없다" 가 아니다** (Phase 12). 무상태라 결과는 애초에 저장되지
 * 않는다 — 없는 것은 결과가 아니라 **쿼리 자체**다. 문구가 이걸 구분해야
 * 사용자가 "예전 결과를 못 찾는 건가?" 하고 헤매지 않는다.
 */
export default function NotFound() {
  return (
    <StateNotice
      title="쿼리를 찾을 수 없습니다"
      steps={[
        "쿼리 ID의 철자를 확인합니다",
        "그 쿼리가 DAC 에 등록돼 있는지 확인합니다",
        <>
          로컬 샘플로 확인해 봅니다 — <code>/eval/q-lot-status</code>
        </>,
      ]}
      actions={
        <Link className="noticeButton noticeButtonPrimary" href="/">
          안내 화면으로
        </Link>
      }
    >
      <p>
        요청한 쿼리 ID를 데이터 소스에서 찾지 못했습니다. ID를 잘못 입력했거나, 그
        쿼리가 아직 등록되지 않았습니다.
      </p>
      <p>
        평가 결과를 못 찾은 것이 아닙니다 — 이 대시보드는 결과를 저장하지 않고 요청할
        때마다 평가합니다. 없는 것은 <strong>평가할 쿼리</strong>입니다.
      </p>
    </StateNotice>
  );
}
