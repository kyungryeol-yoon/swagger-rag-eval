/**
 * 백엔드 호출 — **서버 컴포넌트 전용**.
 *
 * 백엔드로 나가는 fetch 는 전부 여기를 거친다. 화면 코드가 URL 을 조립하거나
 * 실패를 각자 해석하면, 같은 장애가 페이지마다 다른 문구로 보인다.
 *
 * 여기서 책임지는 것은 셋이다:
 *   1. **타임아웃** — 백엔드가 응답하지 않으면 요청이 영원히 매달린다.
 *      Next 의 스트리밍은 그 사이 스켈레톤을 계속 보여주므로, 사용자는
 *      "평가가 오래 걸리는 중" 과 "백엔드가 죽음" 을 구분하지 못한다.
 *   2. **실패의 분류** — 연결 실패 / 준비 안 됨 / HTTP 오류는 사용자가 할 일이
 *      각각 다르다. 하나로 뭉뚱그리면 안내가 쓸모없어진다.
 *   3. **주소를 문장에 남기기** — 폐쇄망에서 가장 흔한 사고는 `API_BASE_URL`
 *      오타다. 어디로 걸었는지가 메시지에 없으면 원인을 찾는 데 한나절이 든다.
 */

import { serverApiBase } from "./config";

/**
 * 요청 하나의 상한(ms).
 *
 * **무상태 전환으로 이 값의 의미가 바뀌었다** (Phase 12). 예전에는 저장된 결과를
 * 읽어 오는 시간이라 8초로 넉넉했다. 지금은 요청이 평가를 실행시키므로 —
 * LLM 질문 생성 100건 + 벡터 검색 — 실제 파이프라인이 붙으면 **수십 초**가 걸린다.
 * fixture 대역을 읽는 지금은 8초로 충분하지만, 파이프라인 연동 시 반드시 올려야
 * 한다 (open-questions #71).
 */
const REQUEST_TIMEOUT_MS = 8_000;

/** `/ready` 확인은 이미 실패한 뒤의 원인 규명용이다. 더 짧게 끊는다. */
const PROBE_TIMEOUT_MS = 2_000;

/** 실패의 종류. 화면이 무엇을 안내할지가 이 값으로 갈린다. */
export type ApiFailureKind =
  /** 주소로 아무도 응답하지 않음. 백엔드가 안 떠 있거나 주소가 틀렸다. */
  | "unreachable"
  /** 제한 시간 안에 응답이 오지 않음. */
  | "timeout"
  /** 백엔드는 떠 있으나 데이터 소스를 아직 읽지 못함(`/ready` 가 503). */
  | "not_ready"
  /** 응답은 왔으나 상태 코드가 실패. */
  | "http"
  /** 응답 본문이 JSON 이 아님. 앞단(프록시·SSO)이 HTML 을 돌려준 경우가 대부분이다. */
  | "malformed";

export class ApiError extends Error {
  readonly kind: ApiFailureKind;
  /** 실제로 호출한 주소. 메시지에도 넣지만, 화면이 따로 쓸 수 있게 남긴다. */
  readonly url: string;
  readonly status?: number;
  /** 백엔드가 준 오류 본문(있으면). 계약 위반이면 어느 필드가 틀렸는지가 여기 들어온다. */
  readonly detail?: string;

  constructor(
    kind: ApiFailureKind,
    message: string,
    options: { url: string; status?: number; detail?: string; cause?: unknown },
  ) {
    super(message, { cause: options.cause });
    this.name = "ApiError";
    this.kind = kind;
    this.url = options.url;
    this.status = options.status;
    this.detail = options.detail;
  }
}

/** 요청한 리소스가 없음. 호출부가 `notFound()` 로 바꿔야 하므로 따로 둔다. */
export class NotFoundError extends Error {
  constructor(readonly url: string) {
    super(`대상을 찾지 못했습니다: ${url}`);
    this.name = "NotFoundError";
  }
}

/**
 * 백엔드가 살아는 있는지, 데이터까지 읽히는지 확인한다.
 *
 * 이미 실패한 뒤에만 부른다. 성공 경로에 넣으면 매 요청이 두 번 나간다.
 * `/ready` 는 저장소를 실제로 읽어 보므로, fixture 가 아직 안 올라온 상태
 * (컨테이너가 막 떴거나 볼륨이 안 붙은 경우)를 여기서 잡아낸다.
 */
async function probeReadiness(): Promise<ApiFailureKind | null> {
  try {
    const res = await fetch(`${serverApiBase}/ready`, {
      cache: "no-store",
      signal: AbortSignal.timeout(PROBE_TIMEOUT_MS),
    });
    // 200 이면 백엔드도 데이터도 멀쩡하다 — 원인은 요청 쪽에 있다.
    return res.ok ? null : "not_ready";
  } catch {
    return "unreachable";
  }
}

function describe(kind: ApiFailureKind, url: string, status?: number): string {
  switch (kind) {
    case "unreachable":
      return `백엔드에 연결하지 못했습니다 (${url}). 백엔드가 실행 중인지, API_BASE_URL 이 맞는지 확인하세요.`;
    case "timeout":
      return `백엔드가 ${REQUEST_TIMEOUT_MS / 1000}초 안에 응답하지 않았습니다 (${url}).`;
    case "not_ready":
      return `백엔드는 응답하지만 평가 데이터를 아직 읽지 못했습니다 (${url}). /ready 가 준비되지 않았다고 답했습니다.`;
    case "malformed":
      return `백엔드 응답이 JSON 이 아닙니다 (${url}). 앞단 프록시나 인증 화면이 대신 응답했는지 확인하세요.`;
    default:
      return `백엔드가 오류를 반환했습니다 (HTTP ${status} · ${url}).`;
  }
}

/**
 * 백엔드에서 JSON 을 가져온다 (GET).
 *
 * @param path `/api/v1/...` 처럼 슬래시로 시작하는 경로. 절대 URL 을 넣지 않는다.
 * @throws NotFoundError 404 일 때. 호출부가 `notFound()` 로 바꾼다.
 * @throws ApiError 그 밖의 모든 실패. `kind` 로 종류가 갈린다.
 */
export async function fetchJson<T>(path: string): Promise<T> {
  return request<T>(path, undefined);
}

/**
 * 백엔드에 JSON 을 보내고 JSON 을 받는다 (POST).
 *
 * 평가 실행이 POST 인 이유는 **요청 자체가 평가를 돌리기 때문**이다 — 무상태라
 * 조회할 저장된 결과가 없다 (contract.md §1). 부수효과가 있는 조회는 GET 이 아니다.
 *
 * @throws NotFoundError 404 일 때. 호출부가 `notFound()` 로 바꾼다.
 * @throws ApiError 그 밖의 모든 실패.
 */
export async function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, body);
}

/**
 * 실제 요청. `body` 가 없으면 GET, 있으면 POST 다.
 *
 * 타임아웃·실패 분류·주소 표기가 한 곳에 있어야 같은 장애가 페이지마다 다른
 * 문구로 보이지 않는다.
 */
async function request<T>(path: string, body: unknown): Promise<T> {
  const url = `${serverApiBase}${path}`;

  let res: Response;
  try {
    // 평가 결과는 실행마다 바뀐다. 캐시하면 옛 수치가 남는다.
    // 무상태라 애초에 캐시할 대상이 아니기도 하다.
    res = await fetch(url, {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (cause) {
    // 끊긴 이유가 시간 초과인지 연결 실패인지부터 나눈다. AbortSignal.timeout 은
    // TimeoutError 를, 연결 실패는 TypeError 를 던진다.
    const timedOut = cause instanceof DOMException && cause.name === "TimeoutError";
    const kind: ApiFailureKind = timedOut ? "timeout" : "unreachable";
    throw new ApiError(kind, describe(kind, url), { url, cause });
  }

  if (res.status === 404) {
    throw new NotFoundError(url);
  }

  if (!res.ok) {
    // 5xx 는 백엔드가 떠 있다는 뜻이므로 /ready 로 원인을 한 겹 더 좁힌다.
    // "데이터가 아직 없음" 과 "코드가 터짐" 은 기다리면 되는지가 다르다.
    const probed = res.status >= 500 ? await probeReadiness() : null;
    const kind: ApiFailureKind = probed ?? "http";
    const detail = await readErrorDetail(res);
    // detail 을 message 에 합쳐 둔다. Next 의 에러 경계는 `error.message` 만
    // 넘겨주므로, 여기 안 넣으면 계약 위반의 필드 이름이 화면까지 못 간다.
    const message = detail
      ? `${describe(kind, url, res.status)}\n${detail}`
      : describe(kind, url, res.status);
    throw new ApiError(kind, message, { url, status: res.status, detail });
  }

  try {
    return (await res.json()) as T;
  } catch (cause) {
    throw new ApiError("malformed", describe("malformed", url), { url, cause });
  }
}

/**
 * 오류 응답의 본문에서 사람이 읽을 부분만 뽑는다.
 *
 * 계약 위반(500)이면 백엔드가 `detail` 에 어느 필드가 틀렸는지를 담아 준다
 * (backend/app/services/adapter.py). 그 문장이 error.tsx 까지 그대로 흘러가야
 * 브라우저만 보고 원본 JSON 의 어느 줄을 고칠지 알 수 있다.
 */
async function readErrorDetail(res: Response): Promise<string | undefined> {
  try {
    const body: unknown = await res.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") {
        return detail;
      }
    }
  } catch {
    // 본문이 JSON 이 아니면 붙일 게 없다. 원래 오류가 더 중요하므로 삼킨다.
  }
  return undefined;
}
