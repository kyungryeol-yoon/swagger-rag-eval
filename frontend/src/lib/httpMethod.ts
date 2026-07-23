/**
 * HTTP 메서드 -> 색 매핑.
 *
 * 컴포넌트가 `method === "GET" ? ... : ...` 로 색을 정하지 않는다.
 * 메서드 뱃지는 실패 테이블·대상 API 카드·검색 결과 목록 등 여러 곳에 나오는데,
 * 판단이 흩어지면 화면마다 같은 GET 이 다른 색으로 보이게 된다.
 *
 * **범주색이다. 상태가 아니다.** DELETE 가 red 인 것은 위험하다는 뜻이 아니라
 * 다른 메서드와 구분되어야 하기 때문이다. 실패 여부는 MISS pill 이 따로 말한다.
 *
 * 지금은 원색 토큰을 그대로 가리킨다. 메서드 색이 팔레트와 달라져야 하면
 * `globals.css` 에 `--method-*` 토큰을 만들고 여기서 그것을 가리키게 바꾼다
 * (`--chart-type-*` 와 같은 방식).
 */

export const HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"] as const;

export type HttpMethod = (typeof HTTP_METHODS)[number];

export const httpMethodColorVar: Record<HttpMethod, string> = {
  GET: "--sky",
  POST: "--green",
  PUT: "--amber",
  PATCH: "--violet",
  DELETE: "--red",
};

/** 계약의 method 는 자유 문자열이라(open-questions #27) 모르는 값이 올 수 있다. */
const FALLBACK_COLOR_VAR = "--text-mute";

function isKnown(method: string): method is HttpMethod {
  return (HTTP_METHODS as readonly string[]).includes(method);
}

/**
 * 메서드 뱃지 색. 모르는 메서드는 중립색으로 떨어뜨린다 —
 * 화면이 깨지는 것보다 회색으로 보이는 편이 낫다.
 */
export function httpMethodColor(method: string): string {
  const name = isKnown(method) ? httpMethodColorVar[method] : FALLBACK_COLOR_VAR;
  return `var(${name})`;
}
