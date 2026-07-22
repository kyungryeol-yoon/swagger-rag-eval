/**
 * 프론트 컨테이너의 헬스 체크.
 *
 * 백엔드 상태는 보지 않는다. 백엔드가 죽었다고 프론트 파드까지 재시작되면
 * 장애가 번지기만 한다. 백엔드 상태는 backend 의 /health, /ready 가 답한다.
 *
 * basePath 가 설정되면 이 경로도 그 아래로 들어간다 (예: /swagger-eval/api/health).
 */

export const dynamic = "force-dynamic";

export function GET() {
  return Response.json({ status: "ok" });
}
