프론트엔드에서 백엔드 API 호출 방식을 수정한다. 아래 3단계를 순서대로 수행하고,
각 단계마다 변경한 파일 목록을 보고할 것.

## 1단계: NEXT_PUBLIC_ 제거
- frontend/src 전체에서 NEXT_PUBLIC_API_BASE_URL 을 사용하는 곳을 모두 찾는다
- 찾은 위치를 먼저 목록으로 보여준다
- 이 환경변수는 빌드 시점에 값이 고정되어 K8s 배포 시 변경이 불가능하므로
  코드에서 완전히 제거한다

## 2단계: 서버 전용 설정 파일
frontend/src/lib/config.ts 를 아래와 같이 만든다(또는 수정한다):

  // 서버 컴포넌트와 Route Handler 에서만 사용한다.
  // 클라이언트 컴포넌트('use client')에서 import 하지 말 것.
  export const backendBaseUrl =
    process.env.API_BASE_URL ?? "http://localhost:8000";

## 3단계: Route Handler 를 통한 중계
현재 클라이언트 컴포넌트(EvaluationRunner 등)가 백엔드를 직접 호출하고 있다.
이를 아래 구조로 바꾼다.

(a) 브라우저 → 프론트 자신의 상대 경로만 호출하도록 변경
    변경 전: fetch(`${API_BASE_URL}/api/v1/evaluations`)
    변경 후: fetch(`/api/evaluate`)
    폴링도 동일: fetch(`/api/evaluate/status?jobId=xxx`)

(b) 아래 Route Handler 를 새로 만든다.
    각 파일 첫 줄에 export const dynamic = "force-dynamic"; 를 넣을 것.

    frontend/src/app/api/evaluate/route.ts
      - POST 요청을 받는다
      - body 를 그대로 백엔드로 전달:
        POST `${backendBaseUrl}/api/v1/evaluations`
      - 백엔드 응답을 그대로 반환

    frontend/src/app/api/evaluate/status/route.ts
      - GET 요청, jobId 쿼리 파라미터를 받는다
      - GET `${backendBaseUrl}/api/v1/evaluations/${jobId}/status` 로 전달
      - 응답 그대로 반환

    frontend/src/app/api/evaluate/result/route.ts
      - GET 요청, jobId 쿼리 파라미터를 받는다
      - GET `${backendBaseUrl}/api/v1/evaluations/${jobId}/result` 로 전달
      - 응답 그대로 반환

    (백엔드 실제 경로가 다르면 그에 맞춰 조정할 것)

## 검증
- grep -rn "NEXT_PUBLIC" frontend/src → 결과가 없어야 한다
- grep -rn "8000" frontend/src → config.ts 의 기본값 한 곳에만 있어야 한다
- 'use client' 가 있는 파일에서 config.ts 를 import 하지 않아야 한다
- npx tsc --noEmit 통과
