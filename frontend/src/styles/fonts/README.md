# 폰트 로컬 번들

**폐쇄망 배포다. CDN·구글 폰트·외부 URL 참조 금지.**
폰트 파일을 이 디렉토리에 직접 넣어야 한다.

파일이 없어도 화면은 깨지지 않는다. `globals.css` 의 `--font-sans` /
`--font-mono` 가 시스템 폰트 fallback 체인이라 그대로 렌더된다 —
자간과 숫자 폭만 달라진다.

## 왜 `public/fonts` 가 아니라 `src/styles/fonts` 인가

`public/` 의 정적 파일은 `/fonts/...` 절대 경로로 참조하게 되는데,
**Next 는 public 파일에 basePath 접두사를 붙여주지 않는다.**
서브패스 배포(`BASE_PATH=/swagger-eval`, `docs/open-questions.md` #34)를 하면
실제 파일은 `/swagger-eval/fonts/...` 에 놓이므로 그 경로가 404 가 된다.

`src/` 안에 두고 `next/font/local` 로 import 하면 번들러가 경로를 다시 쓰고
해시를 붙여준다. basePath 를 바꿔도 폰트가 깨지지 않는다.

## 넣어야 할 파일

`src/app/fonts.ts` 가 아래 이름을 그대로 찾는다.

| 파일명 | 굵기 | 용도 |
|---|---|---|
| `Pretendard-Regular.woff2` | 400 | 본문 |
| `Pretendard-Medium.woff2` | 500 | 라벨 |
| `Pretendard-SemiBold.woff2` | 600 | 소제목 |
| `Pretendard-Bold.woff2` | 700 | 제목 |
| `JetBrainsMono-Regular.woff2` | 400 | 수치·경로 |
| `JetBrainsMono-Medium.woff2` | 500 | 강조된 수치 |

**woff2 를 쓴다.** ttf/otf 는 같은 글리프에 3~5배 크다.
woff2 는 모든 대상 브라우저가 지원한다.

## 어디서 받나

| 폰트 | 라이선스 | 배포처 |
|---|---|---|
| Pretendard | SIL Open Font License 1.1 | `github.com/orioncactus/pretendard` 릴리스의 `Pretendard-{weight}.subset.woff2` |
| JetBrains Mono | SIL Open Font License 1.1 | `github.com/JetBrains/JetBrainsMono` 릴리스의 `webfonts/` |

둘 다 OFL 이라 사내 재배포에 제약이 없다.

Pretendard 는 `.subset.woff2` 를 쓴다. 전체 한글 글리프를 담은 원본은
파일 하나가 수 MB 라 초기 로딩이 느려진다. 받은 뒤 `.subset` 을 뺀
이름으로 바꿔서 넣는다.

```
Pretendard-Regular.subset.woff2  ->  Pretendard-Regular.woff2
```

## 넣은 뒤 절차

1. 위 6개 파일을 이 디렉토리에 넣는다
2. `src/app/fonts.ts` 의 주석을 해제한다
3. `src/app/layout.tsx` 에서 `pretendard.variable` / `jetbrainsMono.variable` 을
   `<html>` 의 className 에 붙인다
4. `src/styles/globals.css` 의 두 줄을 고친다

```css
--font-sans: var(--font-pretendard), -apple-system, "Apple SD Gothic Neo", sans-serif;
--font-mono: var(--font-jetbrains-mono), ui-monospace, monospace;
```

5. 확인

```bash
make dev-frontend
```

http://localhost:3000/dev/tokens 의 "폰트" 항목에서 본문과 모노가
각각 적용됐는지 본다. fallback 과 구분이 안 되면 개발자 도구 Network 탭에서
`.woff2` 가 200 으로 내려오는지 확인한다.

## 반입 가능 여부

폰트 파일을 사내로 들여올 수 있는지는 확인 중이다
(`docs/open-questions.md` #12). 안 되면 시스템 폰트 fallback 으로 간다 —
그 경우 위 절차를 밟지 않고 지금 상태를 유지하면 된다.
