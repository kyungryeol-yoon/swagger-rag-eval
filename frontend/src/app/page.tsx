import StateNotice from "@/components/common/StateNotice/StateNotice";

/**
 * 루트 — **어느 쿼리를 평가할지 알 수 없는 자리**.
 *
 * 이 페이지는 안내만 한다. Phase 12 에서 그렇게 바뀌었다:
 *
 *   이전: 평가 이력 목록을 받아 가장 최근 평가로 리다이렉트
 *   지금: 이력이 없다 (무상태 — contract.md §0). 목록 API 자체가 사라졌다
 *
 * 평가는 `query_id` 가 있어야 시작된다. 그 값을 프론트가 어떻게 받을지는 아직
 * 정해지지 않았다 (open-questions #73) — DAC 이 URL 파라미터로 넘길지, iframe 으로
 * 감쌀지. 정해지기 전까지 루트가 임의의 쿼리를 골라 평가를 돌리는 것은 옳지
 * 않다. 평가는 LLM 호출 100건이 드는 실제 작업이다.
 *
 * 서버 컴포넌트. 백엔드를 호출하지 않으므로 fetch 도, 에러 경계도 필요 없다.
 */
export default function Home() {
  return (
    <StateNotice
      title="평가할 쿼리를 지정해야 합니다"
      steps={[
        <>
          쿼리 ID 를 경로에 넣어 엽니다 — <code>/eval/&#123;queryId&#125;</code>
        </>,
        <>
          로컬 샘플 — <code>/eval/q-lot-status</code>
        </>,
        <>
          백엔드에 직접 물어봅니다 —{" "}
          <code>
            curl -X POST localhost:8000/api/v1/evaluations -d
            &apos;&#123;&quot;query_id&quot;:&quot;q-lot-status&quot;&#125;&apos;
          </code>
        </>,
      ]}
    >
      <p>
        이 대시보드는 <strong>DAC 쿼리 하나</strong>를 평가합니다. 어느 쿼리를 평가할지는
        요청에 담겨 와야 하므로, 루트 경로만으로는 보여줄 것이 없습니다.
      </p>
      <p>
        평가 결과는 <strong>저장되지 않습니다.</strong> 요청할 때마다 처음부터 평가하며,
        지난 평가를 다시 열어볼 수 있는 목록도 없습니다.
      </p>
    </StateNotice>
  );
}
