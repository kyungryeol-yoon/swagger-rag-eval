/**
 * next/font/local 설정 — **폰트 파일 배치 전이라 전체 주석 처리 상태다.**
 *
 * 파일이 없는 상태에서 next/font/local 을 호출하면 빌드가 즉시 실패한다.
 * 그래서 설정만 미리 적어두고 꺼둔다. 지금은 globals.css 의
 * --font-sans / --font-mono 가 시스템 폰트 fallback 으로 동작한다.
 *
 * ---------------------------------------------------------------------------
 * 폰트 파일 배치 후 절차
 * ---------------------------------------------------------------------------
 * 1. src/styles/fonts/ 에 woff2 6개를 넣는다 (목록은 그곳 README.md)
 *
 * 2. 아래 블록의 주석을 해제한다
 *
 * 3. src/app/layout.tsx 에서 두 변수를 <html> 에 붙인다
 *
 *      import { pretendard, jetbrainsMono } from "./fonts";
 *      ...
 *      <html lang="ko" className={`${pretendard.variable} ${jetbrainsMono.variable}`}>
 *
 * 4. src/styles/globals.css 의 타이포 두 줄을 고친다
 *
 *      --font-sans: var(--font-pretendard), -apple-system, "Apple SD Gothic Neo", sans-serif;
 *      --font-mono: var(--font-jetbrains-mono), ui-monospace, monospace;
 *
 * 5. /dev/tokens 의 "폰트" 항목에서 적용 여부를 확인한다
 *
 * ---------------------------------------------------------------------------
 * 왜 @font-face 를 직접 쓰지 않는가
 * ---------------------------------------------------------------------------
 * public/ 에 두고 /fonts/... 절대 경로로 참조하면 basePath 를 붙였을 때
 * 404 가 된다 (Next 는 public 파일에 basePath 를 붙여주지 않는다).
 * next/font/local 은 번들러가 경로를 다시 써주므로 서브패스 배포에서도
 * 깨지지 않는다. 폰트 파일 해싱과 preload 도 함께 처리된다.
 */

// import localFont from "next/font/local";
//
// export const pretendard = localFont({
//   src: [
//     { path: "../styles/fonts/Pretendard-Regular.woff2", weight: "400", style: "normal" },
//     { path: "../styles/fonts/Pretendard-Medium.woff2", weight: "500", style: "normal" },
//     { path: "../styles/fonts/Pretendard-SemiBold.woff2", weight: "600", style: "normal" },
//     { path: "../styles/fonts/Pretendard-Bold.woff2", weight: "700", style: "normal" },
//   ],
//   variable: "--font-pretendard",
//   display: "swap",
//   // 폰트가 늦게 뜰 때 레이아웃이 튀지 않도록 시스템 폰트로 대체한다.
//   fallback: ["-apple-system", "Apple SD Gothic Neo", "sans-serif"],
// });
//
// export const jetbrainsMono = localFont({
//   src: [
//     { path: "../styles/fonts/JetBrainsMono-Regular.woff2", weight: "400", style: "normal" },
//     { path: "../styles/fonts/JetBrainsMono-Medium.woff2", weight: "500", style: "normal" },
//   ],
//   variable: "--font-jetbrains-mono",
//   display: "swap",
//   fallback: ["ui-monospace", "monospace"],
// });
