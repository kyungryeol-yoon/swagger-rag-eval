프론트엔드에서 브라우저가 백엔드를 직접 호출하는 부분을 수정한다.
현재 기능은 정상 동작하므로, 아래 범위 외에는 아무것도 바꾸지 말 것.

## 문제
HTTPS 로 서비스되는 페이지에서 브라우저가 http://backend-svc 를 직접 호출하고 있다.
브라우저는 이를 Mixed Content 로 판단해 "보안 연결이 사용되지 않았습니다" 경고를 띄운다.
또한 backend-svc 는 클러스터 내부 이름이므로 브라우저는 원래 접근할 수 없다.

## 1단계 — 조사 먼저 (코드를 고치기 전에 목록부터 보고할 것)
frontend/src 에서 아래를 모두 찾아 파일명과 줄번호를 목록으로 보고한다.
- 'use client' 가 선언된 파일 중 백엔드 주소를 사용하는 곳
- backend-svc, http:// , API_BASE_URL, NEXT_PUBLIC_ 문자열이 등장하는 곳
- 초기 화면 진입 시 호출되는 fetch 가 어디에 있는지

보고 후 승인을 받고 2단계로 넘어간다.

## 2단계 — 클라이언트 호출을 상대 경로로 변경
'use client' 파일에서 백엔드를 직접 호출하는 fetch 를 상대 경로로 바꾼다.
  변경 전: fetch("http://backend-svc:8000/api/v1/...")
  변경 후: fetch("/api/...")
백엔드 절대 주소는 클라이언트 코드에서 완전히 사라져야 한다.

## 3단계 — 대응되는 Route Handler 추가
2단계에서 바꾼 상대 경로마다 프론트 Route Handler 를 만든다.
파일 위치: frontend/src/app/api/<경로>/route.ts
각 파일 규칙:
- 첫 줄에 export const dynamic = "force-dynamic";
- 백엔드 주소는 process.env.API_BASE_URL 로 읽는다 (NEXT_PUBLIC_ 금지)
- 요청 body / 쿼리 파라미터를 그대로 백엔드로 전달하고,
  백엔드 응답을 그대로 반환한다. 가공하지 말 것
- 에러 시 백엔드의 상태 코드와 메시지를 그대로 전달

## 하지 말 것
- 기존에 동작하는 로직(평가 실행, 폴링 주기, 화면 렌더)을 변경하지 말 것
- next.config.ts 의 rewrites 를 추가하지 말 것
- 컴포넌트 구조나 스타일을 건드리지 말 것

## 검증
- grep -rn "backend-svc\|NEXT_PUBLIC" frontend/src → 결과 없음
- 'use client' 파일에 http:// 로 시작하는 백엔드 주소 없음
- npx tsc --noEmit 통과
- 로컬에서 기존과 동일하게 동작

