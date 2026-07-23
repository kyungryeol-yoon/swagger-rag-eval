import { redirect } from "next/navigation";

/**
 * 루트는 샘플 리포트로 보낸다 — **임시(Phase 6.5)**.
 *
 * 평가 대상 범위가 아직 미정이라(docs/open-questions.md #1) 여기에 무엇을
 * 둘지 정할 수 없다. API 1개짜리면 대상 선택 화면이 필요 없고, 서비스 전체면
 * 목록 화면이 먼저 와야 한다.
 *
 * 담당자 시연에서 주소를 외우지 않아도 되게 리다이렉트만 걸어둔다.
 * #1 이 확정되면 이 파일이 실제 진입 화면이 된다.
 */
export default function Home() {
  redirect("/eval/A492");
}
