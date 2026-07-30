import type { TargetQuery } from "@/lib/types";

import styles from "./QueryInfoCard.module.css";

/**
 * 평가 대상 쿼리 카드 — 행1 좌상단.
 *
 * **이 카드의 목적은 "왜 인식률이 이 수치인가" 를 사용자가 자기 설명에서
 * 바로 보게 하는 것이다.** 그래서 summary / description / x-question 을 요약하지
 * 않고 그대로 보여준다. 인식률 숫자만 보면 무엇을 고쳐야 할지 알 수 없다 —
 * 고쳐야 할 대상이 바로 이 텍스트다 (contract.md §2).
 *
 * 없는 것은 **경고색으로** 표시한다. summary 가 비어 있다는 사실 자체가 평가
 * 결과이므로, 조용히 감추면 이 화면의 핵심 정보가 사라진다.
 *
 * **큰 점수는 넣지 않는다** (그건 GaugeRing / SummaryCards).
 *
 * 이전 `AppInfoCard` 를 대신한다. 평가 단위가 앱에서 쿼리로 바뀌면서
 * 앱 이름·명세 버전·쿼리 수·담당 조직이 계약에서 사라졌다.
 *
 * 서버 컴포넌트.
 */

export type QueryInfoCardProps = {
  target: TargetQuery;
};

export default function QueryInfoCard({ target }: QueryInfoCardProps) {
  return (
    <section className={styles.card} aria-label="평가 대상 쿼리">
      {/* 메서드는 단독 뱃지로 만들지 않는다 — DAC 쿼리는 전부 조회라 메서드가
          구별에 기여하지 않는다 (open-questions #50). 경로 앞에 작게 붙여
          "무엇을 호출하는지" 만 밝힌다. */}
      <code className={`${styles.path} tabular`} title={`${target.method} ${target.path}`}>
        <span className={styles.method}>{target.method}</span>
        {target.path}
      </code>

      <dl className={styles.ids}>
        <div className={styles.idItem}>
          <dt>쿼리 ID</dt>
          <dd className="tabular">{target.queryId}</dd>
        </div>
        {/* appId 는 optional. DAC 이 주지 않으면 줄 자체를 그리지 않는다. */}
        {target.appId && (
          <div className={styles.idItem}>
            <dt>앱</dt>
            <dd className="tabular">{target.appId}</dd>
          </div>
        )}
      </dl>

      <div className={styles.spec}>
        <Field label="summary" value={target.summary} />
        <Field label="description" value={target.description} multiline />
      </div>

      {/* 예시 질문. 없으면 접이식 자체를 만들지 않는다 — 펼쳐도 아무것도 없는
          "0개 보기" 는 눌러 보게 만들고 아무것도 주지 않는다.
          계약이 빈 배열을 보장하므로 length 만 보면 된다 (null 이 아니다). */}
      {target.xQuestions.length > 0 ? (
        <details className={styles.examples}>
          <summary className={styles.examplesSummary}>
            예시 질문 <span className="tabular">{target.xQuestions.length}</span>개 보기
          </summary>
          <ul className={styles.exampleList}>
            {target.xQuestions.map((question) => (
              <li key={question} className={styles.exampleItem}>
                {question}
              </li>
            ))}
          </ul>
        </details>
      ) : (
        <p className={styles.fieldMissing}>예시 질문(x-question) 없음</p>
      )}
    </section>
  );
}

/**
 * 명세 필드 한 줄.
 *
 * 값이 없으면 "없음" 을 경고색으로 적는다. 빈 자리를 남기거나 대시로 흐리게
 * 두면, 이 화면에서 가장 중요한 신호("설명이 비어 있다")가 눈에 안 들어온다.
 */
function Field({
  label,
  value,
  multiline = false,
}: {
  label: string;
  value: string | null | undefined;
  multiline?: boolean;
}) {
  return (
    <div className={styles.field}>
      <span className={styles.fieldLabel}>{label}</span>
      {value ? (
        <p className={multiline ? styles.fieldBodyLong : styles.fieldBody}>{value}</p>
      ) : (
        <p className={styles.fieldMissing}>없음</p>
      )}
    </div>
  );
}
