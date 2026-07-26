import { redirect } from "next/navigation";

import StateNotice from "@/components/common/StateNotice/StateNotice";
import { fetchJson } from "@/lib/api";
import type { EvaluationListItem } from "@/lib/types";

/**
 * 루트는 **최신 평가로 리다이렉트**한다 — 여전히 임시안(docs/open-questions.md #1).
 *
 * 평가 대상 범위가 아직 미정이라 여기에 목록 화면을 둘지 대상 선택을 둘지
 * 정할 수 없다. 그때까지는 목록에서 가장 최근 평가로 보낸다. #1 이 확정되면
 * 이 파일이 실제 진입 화면(목록/선택)이 된다.
 *
 * **더 이상 실패를 삼키지 않는다** (Phase 10). 예전에는 백엔드가 죽어 있어도
 * 조용히 `/eval/A492` 로 보냈고, 사용자는 "A492 가 없다"는 엉뚱한 404 를 봤다.
 * 진짜 원인(백엔드 미기동)은 화면 어디에도 없었다. 이제 셋을 나눈다:
 *   목록이 있다  → 최신으로 보낸다
 *   목록이 비었다 → 첫 실행 안내 (여기서 렌더)
 *   못 가져왔다   → error.tsx (throw 를 그대로 올린다)
 *
 * 서버 컴포넌트. 목록은 백엔드가 evaluatedAt 내림차순으로 내려주므로 첫 항목이 최신.
 */
/**
 * **정적 프리렌더 금지.** 이 페이지는 백엔드 목록을 읽어야 하는데, 빌드 시점에는
 * 백엔드가 떠 있지 않다. 선언하지 않으면 Next 가 빌드 중에 프리렌더를 시도하고
 * 연결 실패로 빌드가 통째로 깨진다 (`cache: "no-store"` 만으로는 부족하다 —
 * 그 조합은 "동적이어야 한다" 는 신호를 예외로 던지는데, 우리 fetch 래퍼가
 * 그 예외를 ApiError 로 감싸 버려 신호가 사라진다).
 */
export const dynamic = "force-dynamic";

export default async function Home() {
  // redirect() 는 내부적으로 예외를 던진다. try 로 감싸면 그 예외를 삼키게 되므로
  // 조회만 먼저 끝내고 리다이렉트는 아래에서 한다.
  const items = await fetchJson<EvaluationListItem[]>("/api/v1/evaluations");

  if (items.length === 0) {
    return (
      <StateNotice
        title="아직 평가 이력이 없습니다"
        steps={[
          <>
            평가툴 결과를 저장소에 넣습니다 — 로컬은{" "}
            <code>backend/app/fixtures/eval_&#123;traceId&#125;.json</code>
          </>,
          <>
            백엔드가 읽는지 확인합니다 — <code>http://localhost:8000/ready</code>
          </>,
          "이 페이지를 새로고침하면 가장 최근 평가로 이동합니다",
        ]}
      >
        <p>
          백엔드는 정상이지만 저장된 평가 결과가 하나도 없습니다. 평가를 한 번도
          실행하지 않았거나, 결과가 아직 저장소에 들어오지 않았습니다.
        </p>
        <p>
          이 대시보드는 평가를 직접 실행하지 않습니다. 평가는 외부 평가툴이 하고,
          여기서는 그 결과를 보여줍니다 (docs/contract.md §0).
        </p>
      </StateNotice>
    );
  }

  redirect(`/eval/${encodeURIComponent(items[0].traceId)}`);
}
