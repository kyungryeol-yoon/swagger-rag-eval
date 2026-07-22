/**
 * 서버 전용 설정.
 *
 * **`NEXT_PUBLIC_` 접두사를 쓰지 않는다.** 그 접두사가 붙으면 값이 빌드 타임에
 * 클라이언트 번들로 박히고, 그 순간 이미지 하나를 dev → stg → prd 로 승격하는 게
 * 불가능해진다. 환경마다 다시 빌드해야 한다 (docs/open-questions.md #35).
 *
 * 여기 있는 값은 **서버 컴포넌트와 route handler 에서만** 읽는다.
 * 클라이언트 컴포넌트에서 import 하면 `process.env` 가 비어 있어 기본값으로 조용히
 * 되돌아가므로, 아래에서 명시적으로 막는다.
 */

if (typeof window !== "undefined") {
  throw new Error(
    "lib/config.ts 는 서버 전용입니다. 클라이언트 컴포넌트에서 import 하지 마세요.",
  );
}

/**
 * 대시보드 API(backend)의 베이스 URL.
 * 백엔드로 fetch 하는 코드는 전부 이 값을 경유한다. URL 을 직접 적지 않는다.
 */
export const serverApiBase = process.env.API_BASE_URL ?? "http://localhost:8000";
