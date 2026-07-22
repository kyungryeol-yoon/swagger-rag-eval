import type { NextConfig } from "next";

/**
 * basePath 는 배포 위치에 따라 달라진다.
 * Ingress 가 루트면 '' , 서브패스면 '/swagger-eval' 같은 값이 들어온다
 * (docs/open-questions.md #34).
 *
 * 빌드 타임에 고정되는 값이라 환경별 이미지가 갈릴 수 있는 지점이다.
 * 서브패스가 확정되면 그때 한 번만 정하면 된다.
 */
const basePath = process.env.BASE_PATH ?? "";

if (basePath !== "" && !basePath.startsWith("/")) {
  throw new Error(`BASE_PATH 는 '/' 로 시작해야 합니다: ${basePath}`);
}

const nextConfig: NextConfig = {
  // 폐쇄망 배포: node_modules 없이 옮길 수 있는 최소 산출물만 만든다.
  output: "standalone",
  basePath,
  reactStrictMode: true,
  // 폐쇄망 배포: 외부 이미지 최적화 대상이 없다.
  images: { remotePatterns: [] },
};

export default nextConfig;
