import { redirect } from "next/navigation";

import { serverApiBase } from "@/lib/config";
import type { EvaluationListItem } from "@/lib/types";

/**
 * 루트는 **최신 평가로 리다이렉트**한다 — 여전히 임시안(docs/open-questions.md #1).
 *
 * 평가 대상 범위가 아직 미정이라 여기에 목록 화면을 둘지 대상 선택을 둘지
 * 정할 수 없다. 그때까지는 목록에서 가장 최근 평가로 보낸다. #1 이 확정되면
 * 이 파일이 실제 진입 화면(목록/선택)이 된다.
 *
 * 서버 컴포넌트. 목록은 백엔드가 evaluatedAt 내림차순으로 내려주므로 첫 항목이 최신.
 */
export default async function Home() {
  let latest: string | null = null;

  // redirect() 는 내부적으로 예외를 던지므로 try 안에서 부르면 안 된다.
  // 목록 조회만 try 로 감싸고, 리다이렉트는 밖에서 한다.
  try {
    const res = await fetch(`${serverApiBase}/api/v1/evaluations`, { cache: "no-store" });
    if (res.ok) {
      const items = (await res.json()) as EvaluationListItem[];
      if (items.length > 0) {
        latest = items[0].traceId;
      }
    }
  } catch {
    // 백엔드 미응답 등 — 아래 기본값으로 떨어진다.
  }

  // 목록이 비었거나 백엔드가 응답하지 않으면 기존 임시 기본값으로.
  redirect(`/eval/${encodeURIComponent(latest ?? "A492")}`);
}
