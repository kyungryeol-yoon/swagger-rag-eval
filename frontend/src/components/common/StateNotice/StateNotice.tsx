import type { ReactNode } from "react";

import styles from "./StateNotice.module.css";

/**
 * 데이터가 없거나 못 가져왔을 때 쓰는 안내 화면.
 *
 * 에러·없음·빈 목록은 서로 다른 화면이지만 **구조는 같다**:
 * 무엇이 일어났는가(제목) → 왜 그런가(본문) → 무엇을 하면 되는가(확인 순서·버튼).
 * 그래서 껍데기를 여기 하나로 두고 문구만 각 화면이 채운다. 세 화면이 각자
 * 마크업을 들고 있으면 하나만 고쳐지고 나머지는 옛 문구로 남는다.
 *
 * **사과하지 않는다.** "죄송합니다" 는 사용자가 다음에 할 일을 알려주지 않는다
 * (docs/prompts.md §9-4).
 *
 * 서버 컴포넌트다. 버튼이 필요한 화면은 `actions` 에 자기 클라이언트 컴포넌트를
 * 넣는다 — 이 컴포넌트가 클라이언트로 올라갈 이유는 없다.
 */

export type StateNoticeProps = {
  title: string;
  /** 왜 이 화면이 떴는지. 한두 문장. */
  children: ReactNode;
  /** 확인 순서. 순서가 있는 절차라서 ol 이다. 없으면 블록 자체를 그리지 않는다. */
  steps?: ReactNode[];
  /** 기술적 원인. 개발 환경에서만 넘긴다 — 운영 화면에 스택을 흘리지 않는다. */
  detail?: ReactNode;
  /** 버튼·링크. */
  actions?: ReactNode;
};

export default function StateNotice({
  title,
  children,
  steps,
  detail,
  actions,
}: StateNoticeProps) {
  return (
    <main className={styles.notice}>
      <h1 className={styles.title}>{title}</h1>

      <div className={styles.body}>{children}</div>

      {steps && steps.length > 0 && (
        <div className={styles.checklist}>
          <ol>
            {steps.map((step, index) => (
              // 문구는 고정 목록이고 순서가 바뀌지 않는다. 인덱스 키로 충분하다.
              <li key={index}>{step}</li>
            ))}
          </ol>
        </div>
      )}

      {detail && <pre className={styles.detail}>{detail}</pre>}

      {actions && <div className={styles.actions}>{actions}</div>}
    </main>
  );
}
