import next from "eslint-config-next";

const config = [
  ...next,
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      // 생성물. 수기 편집 금지이므로 린트 대상에서도 제외한다.
      "src/lib/api-types.ts",
    ],
  },
];

export default config;
