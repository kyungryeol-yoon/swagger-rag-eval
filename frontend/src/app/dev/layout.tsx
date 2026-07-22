import { notFound } from "next/navigation";

/**
 * 개발용 확인 페이지 영역.
 *
 * 프로덕션에서는 존재하지 않는다. 토큰 스와치나 컴포넌트 카탈로그가
 * 실제 배포에 딸려 나가면 내부 구현이 그대로 노출된다.
 *
 * 빌드 시점에도 NODE_ENV 가 production 이므로, `npm run build` 하면
 * 이 아래 페이지들은 404 로 확정된다.
 */
export default function DevLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  return <>{children}</>;
}
