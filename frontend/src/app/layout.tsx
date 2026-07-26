import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "swagger-rag-eval",
  description: "Swagger 명세의 RAG 검색 인식률 평가 대시보드",
};

/**
 * 테마 부트스트랩 스크립트 (FOUC 방지).
 *
 * 첫 페인트 **전에** 저장된 테마(localStorage 'theme')를 <html data-theme> 로 얹는다.
 * 이게 없으면 서버는 다크로 그리고 클라이언트가 라이트로 바꾸는 사이 화면이 번쩍인다.
 * 값이 없거나(=auto) 잘못된 값이면 아무것도 얹지 않아 CSS 가 prefers-color-scheme 로
 * OS 를 따른다. 예외적으로 허용된 유일한 인라인 스크립트 — 나머지 구조는 서버 컴포넌트.
 */
const themeInitScript = `(function(){try{var t=localStorage.getItem('theme');if(t==='light'||t==='dark'){document.documentElement.setAttribute('data-theme',t);}}catch(e){}})();`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
