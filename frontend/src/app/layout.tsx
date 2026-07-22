import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "swagger-rag-eval",
  description: "Swagger 명세의 RAG 검색 인식률 평가 대시보드",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
