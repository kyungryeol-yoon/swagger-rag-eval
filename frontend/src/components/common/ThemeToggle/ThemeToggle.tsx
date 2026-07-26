"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

import styles from "./ThemeToggle.module.css";

/**
 * 테마 토글 — auto / light / dark 3단계 순환 (Phase 8a).
 *
 * 색 전환 자체는 CSS 가 한다(globals.css 의 data-theme / prefers-color-scheme).
 * 이 컴포넌트는 <html data-theme> 를 갱신하고 선택값을 localStorage 에 저장할 뿐이다.
 *   - auto : data-theme 를 지운다 → CSS 가 OS 설정(prefers-color-scheme)을 따른다.
 *            그래서 auto 에서는 OS 변경이 JS 없이 실시간 반영된다.
 *   - light/dark : data-theme 를 강제로 얹어 OS 설정을 무시한다.
 * 첫 페인트 적용은 layout.tsx 인라인 스크립트가 먼저 하므로 여기선 표시 상태만 맞춘다.
 *
 * 표시 상태는 localStorage(브라우저 외부 상태)에서 useSyncExternalStore 로 읽는다.
 * 서버 스냅샷은 'auto' 라 서버 렌더와 하이드레이션이 일치하고, 하이드레이션 직후
 * 클라이언트 값으로 자연스럽게 넘어간다. 저장소는 localStorage 1키뿐이라 서버 DB·
 * 유저관리가 필요 없다 (docs/open-questions.md #58).
 */

type Theme = "auto" | "light" | "dark";

// 순환 순서. auto 를 첫 상태로 둬 서버 렌더와 클라이언트 첫 렌더가 일치한다.
const ORDER: readonly Theme[] = ["auto", "light", "dark"];

const META: Record<Theme, { Icon: typeof Monitor; label: string }> = {
  auto: { Icon: Monitor, label: "시스템" },
  light: { Icon: Sun, label: "라이트" },
  dark: { Icon: Moon, label: "다크" },
};

// localStorage 를 외부 스토어로 다룬다. 같은 문서에서 바꿀 땐 storage 이벤트가
// 안 오므로 로컬 리스너를 따로 두고 cycle() 에서 직접 깨운다.
const listeners = new Set<() => void>();

function subscribe(onChange: () => void): () => void {
  listeners.add(onChange);
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", onChange);
  };
}

function getSnapshot(): Theme {
  try {
    const saved = localStorage.getItem("theme");
    return saved === "light" || saved === "dark" ? saved : "auto";
  } catch {
    return "auto";
  }
}

// 서버엔 localStorage 가 없다. 항상 auto 로 그려 하이드레이션을 맞춘다.
function getServerSnapshot(): Theme {
  return "auto";
}

function setTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === "auto") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", theme);
  }
  try {
    if (theme === "auto") {
      localStorage.removeItem("theme");
    } else {
      localStorage.setItem("theme", theme);
    }
  } catch {
    // 저장 실패(프라이빗 모드 등)는 무시한다 — 이번 세션 동안은 동작한다.
  }
  listeners.forEach((notify) => notify());
}

export default function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const { Icon, label } = META[theme];

  function cycle(): void {
    setTheme(ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length]);
  }

  return (
    <button
      type="button"
      className={styles.toggle}
      onClick={cycle}
      aria-label={`테마 전환 (현재: ${label})`}
      title={`테마: ${label} — 클릭하면 전환`}
    >
      <Icon size={15} aria-hidden="true" />
      <span className={styles.label}>{label}</span>
    </button>
  );
}
