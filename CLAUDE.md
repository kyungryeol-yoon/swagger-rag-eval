# swagger-rag-eval

Swagger 명세의 RAG 검색 인식률 평가 대시보드.
사용자가 API를 만들면 Swagger가 자동 생성되고, 다른 사용자가 AI로 질문했을 때
그 Swagger를 잘 찾아내는지 평가한 리포트를 보여준다.

## 스택 (사내 프로젝트와 100% 일치 — 임의 변경 금지)

- Next.js 16 App Router / React 19 / TypeScript
- 스타일: CSS Modules + `globals.css`의 CSS 변수 토큰
- 아이콘: `lucide-react`
- 차트: **순수 SVG**. 차트 라이브러리 사용 금지
- 백엔드: FastAPI + Pydantic v2, Python 3.12

## 절대 규칙

1. **새 npm 패키지 추가 금지.** 이 저장소는 폐쇄망 프로젝트에 파일 단위로 복사되므로
   의존성이 늘면 그 파일은 이식 불가가 된다.
2. Tailwind / CSS-in-JS / UI 프레임워크 사용 금지.
3. CDN, 외부 폰트, 외부 이미지 참조 금지. 폰트는 `public/fonts`에 로컬 번들.
4. 컴포넌트는 `Foo.tsx` + `Foo.module.css` 한 쌍으로 자기 완결. 옆 폴더를 참조하지 않는다.
5. 색·간격·폰트 하드코딩 금지. 전부 `var(--token)`.
6. SSO / DB / LLM은 `backend/app/ports/` 뒤에만 존재한다. 로직에서 직접 호출 금지.
7. `backend/app/schemas/evaluation.py` 가 응답 계약의 단일 진실 공급원.
8. 프론트 타입은 `openapi-typescript`로 생성. 수기 작성 금지.
9. 커밋은 Phase 단위. 여러 Phase를 한 커밋에 섞지 말 것.

## 시안

`docs/mockup.svg` 는 레이아웃·색·분위기 참고용이다.
수치·문구·정보 구조의 진실은 `docs/contract.md` 이며, 둘이 충돌하면 contract.md 가 이긴다.
시안에는 알려진 오류가 있으므로 `docs/prompts.md` §9 를 반드시 함께 읽을 것.
시안 이미지는 Phase 7(조립)에서 처음 참조한다. Phase 5~6에서는 참조하지 않는다.

## 작업 방식

- 지시받은 Phase 하나만 수행하고 멈춘다. 앞서 나가지 않는다.
- 파일을 새로 만들 때마다 `docs/open-questions.md` 에 미정 사항을 기록한다.
- 작업 전 `docs/prompts.md` 의 해당 Phase를 읽는다.

## 디렉토리

```
sample-api/   평가 "대상". 진짜 openapi.json 을 생성하는 더미 API
backend/      평가기 + 대시보드 API
frontend/     대시보드 화면
docs/         계약·프롬프트·미정 항목
```
