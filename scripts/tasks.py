#!/usr/bin/env python3
"""프로젝트 작업 실행기.

Makefile 이 하던 셸 로직을 전부 여기로 옮겼다.

**왜 옮겼나**: Windows 에서 make 는 레시피를 cmd.exe 로 실행한다.
`[ -f x ] && a || b` 같은 POSIX 문법이 cmd 에서 그대로 깨지고,
git bash 로 실행하면 되다가 cmd 에서 안 되는 상황이 반복된다.
Makefile 은 이제 이 스크립트를 한 줄로 부르기만 한다.

**제약 1 — 표준 라이브러리만.** 서드파티 금지.
의존성을 설치하기 위한 스크립트가 의존성을 요구하면 순환이다.

**제약 2 — Python 3.8 문법으로 유지한다.**
이 스크립트는 uv 가 관리하는 3.12 가 아니라 **시스템 python 으로 실행된다.**
macOS 기본 python3 는 3.9(Xcode 번들)이고, 사내 Windows PC 는 더 낮을 수 있다.
프로젝트가 3.12 를 요구하는 것과는 별개다 — 3.12 를 설치하기 위해 uv 를
부르는 것이 이 스크립트의 일이므로, 스스로는 오래된 python 에서도 돌아야 한다.

금지:
    match 문                     (3.10+)
    X | Y 타입 표기              (3.10+) -> typing.Optional / Union
    dict1 | dict2 병합           (3.9+)  -> {**a, **b}
    list[str] / dict[str, int]   (3.9+)  -> typing.List / Dict
                                 (annotations future import 로 표기 자체는
                                  가능하지만, 런타임 평가되는 자리에서 터진다)
    str.removeprefix / removesuffix (3.9+)
    tomllib                      (3.11+) -> 있으면 쓰고 없으면 폴백

`ruff` 가 `target-version = "py38"` 로 이 파일을 검사한다 (루트 ruff.toml).
**다만 전부 잡아주지는 않는다.** `match` 처럼 3.8 에 문법 자체가 없는 것은
막아주지만, `dict1 | dict2` 나 `str.removeprefix` 처럼 문법은 유효하고
런타임에만 터지는 것은 못 잡는다. 위 금지 목록은 사람이 지켜야 한다.

사용:
    python scripts/tasks.py <command>
    make <command>
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import unicodedata
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

# 문법 자체는 3.6 에서도 파싱되므로, 여기까지 와서 버전을 확인할 수 있다.
# 메시지 없이 알 수 없는 곳에서 터지는 것보다 낫다.
MIN_PYTHON = (3, 8)
if sys.version_info < MIN_PYTHON:
    _need = f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
    _have = f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
    sys.stderr.write(
        f"\n이 스크립트는 Python {_need} 이상이 필요합니다. 현재 {_have} 입니다.\n"
        f"  실행 파일: {sys.executable}\n\n"
        "더 새 python 으로 실행하세요:\n"
        "  python3 scripts/tasks.py <command>\n"
        "  make PY=python3.12 <command>\n\n"
        "참고: 프로젝트 자체는 Python 3.12 를 요구하지만, 그건 uv 가 따로\n"
        f"설치합니다. 이 스크립트만 {_need} 이상이면 됩니다.\n"
    )
    raise SystemExit(1)

# 프로젝트가 요구하는 런타임. tasks.py 가 이 버전으로 돌 필요는 없다.
PROJECT_PYTHON = "3.12"

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
SAMPLE_API = ROOT / "sample-api"
FRONTEND = ROOT / "frontend"

IS_WINDOWS = os.name == "nt"


# ---------------------------------------------------------------------------
# 실행 도우미
# ---------------------------------------------------------------------------


def tool(name: str) -> str:
    """실행 파일 경로를 찾는다.

    Windows 에서 npm 은 `npm.cmd` 다. shell=True 없이 리스트 인자로
    `["npm", ...]` 을 주면 찾지 못한다. `shutil.which` 가 확장자까지 붙여준다.
    """
    found = shutil.which(name)
    return found if found else name


def run(cmd: Sequence[str], cwd: Path, *, check: bool = True) -> int:
    """명령 하나를 실행한다. shell=True 를 쓰지 않는다."""
    printable = " ".join(cmd)
    rel = cwd.relative_to(ROOT) if cwd != ROOT else Path(".")
    print(f"\n> [{rel}] {printable}", flush=True)

    resolved = [tool(cmd[0])] + list(cmd[1:])
    result = subprocess.run(resolved, cwd=str(cwd))

    if check and result.returncode != 0:
        print(f"\n실패: {printable} (종료 코드 {result.returncode})", file=sys.stderr)
        raise SystemExit(result.returncode)
    return result.returncode


def width(text: str) -> int:
    """터미널에서 차지하는 칸 수. 한글은 두 칸이다."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def pad(text: str, size: int) -> str:
    return text + " " * max(0, size - width(text))


def capture(cmd: Sequence[str], cwd: Optional[Path] = None) -> Optional[str]:
    """명령의 첫 줄 출력을 가져온다. 실패하면 None (진단용이라 죽지 않는다)."""
    try:
        result = subprocess.run(
            [tool(cmd[0])] + list(cmd[1:]),
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    text = result.stdout.decode("utf-8", errors="replace").strip()
    return text.splitlines()[0] if text else None


# ---------------------------------------------------------------------------
# 명령
# ---------------------------------------------------------------------------

COMMANDS: List[Tuple[str, str]] = [
    ("setup", "의존성 설치"),
    ("dev", "세 서버 동시 실행 (8001 / 8000 / 3000)"),
    ("build", "프론트 프로덕션 빌드"),
    ("test", "백엔드 + sample-api 테스트"),
    ("lint", "린트 + 타입체크"),
    ("gen-types", "백엔드 OpenAPI -> 프론트 타입 생성"),
    ("dump-spec", "sample-api 의 openapi.json 덤프"),
    ("show-quality", "sample-api 엔드포인트별 설명 품질 표"),
    ("lock", "uv.lock 재생성 (사내 저장소 전환 시)"),
    ("doctor", "환경 진단 — 사내 PC 최초 셋업 시 먼저 실행"),
    ("clean", "빌드 산출물 삭제"),
]


def cmd_help() -> None:
    print()
    print("  swagger-rag-eval 작업 목록")
    print()
    for name, description in COMMANDS:
        print(f"  make {pad(name, 14)} {description}")
    print()
    print("  make 없이도 실행할 수 있다:  python scripts/tasks.py <command>")
    print()


def cmd_setup() -> None:
    run(["uv", "sync"], SAMPLE_API)
    run(["uv", "sync"], BACKEND)

    lockfile = FRONTEND / "package-lock.json"
    if lockfile.is_file():
        # 락 파일이 있으면 그대로 재현한다. 사내 저장소로 바꾼 뒤
        # 락과 registry 가 안 맞으면 여기서 실패하는데, 그게 맞다 —
        # 조용히 다른 버전을 설치하는 것보다 낫다 (docs/prompts.md §10).
        run(["npm", "ci"], FRONTEND)
    else:
        print("\npackage-lock.json 이 없다. npm install 로 락을 생성한다.")
        run(["npm", "install"], FRONTEND)


def cmd_build() -> None:
    run(["npm", "run", "build"], FRONTEND)


def cmd_test() -> None:
    run(["uv", "run", "pytest", "-q"], BACKEND)
    run(["uv", "run", "pytest", "-q"], SAMPLE_API)


def cmd_lint() -> None:
    run(["uv", "run", "ruff", "check", "."], BACKEND)
    run(["uv", "run", "mypy", "app"], BACKEND)
    # scripts/ 는 별도 설정(루트 ruff.toml)으로 검사한다. target-version = py38 이라
    # 신문법이 들어가면 여기서 걸린다. ruff 자체는 backend 환경의 것을 빌려 쓴다.
    run(["uv", "run", "--project", str(BACKEND), "ruff", "check", "scripts"], ROOT)
    run(["npm", "run", "lint"], FRONTEND)
    run(["npx", "tsc", "--noEmit"], FRONTEND)


def cmd_gen_types() -> None:
    print("\n주의: 백엔드가 8000 에 떠 있어야 한다. (다른 터미널에서 make dev)")
    run(["npm", "run", "gen:types"], FRONTEND)


def cmd_dump_spec() -> None:
    run(["uv", "run", "python", "-m", "app.scripts.dump_openapi"], SAMPLE_API)


def cmd_show_quality() -> None:
    run(["uv", "run", "python", "-m", "app.scripts.show_quality"], SAMPLE_API)


def cmd_lock() -> None:
    """uv.lock 을 다시 만든다.

    사내 저장소로 전환하면 락에 박힌 인덱스 URL 이 맞지 않아 재생성이 필요하다.
    **여기서 만들어진 락은 사내 로컬 전용이며 GitHub 로 되돌리지 않는다**
    (docs/prompts.md §10).
    """
    run(["uv", "lock"], BACKEND)
    run(["uv", "lock"], SAMPLE_API)
    print("\nuv.lock 을 재생성했다. 이 락은 사내 로컬 전용이며 GitHub 로 push 하지 않는다.")


def cmd_clean() -> None:
    targets = [FRONTEND / ".next", FRONTEND / "out"]
    for target in targets:
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
            print(f"삭제: {target.relative_to(ROOT)}")

    removed = 0
    for cache in ROOT.rglob("__pycache__"):
        if ".venv" in cache.parts or "node_modules" in cache.parts:
            continue
        shutil.rmtree(cache, ignore_errors=True)
        removed += 1
    print(f"__pycache__ {removed}개 삭제")


# ---------------------------------------------------------------------------
# doctor — 환경 진단
# ---------------------------------------------------------------------------

# 값이 비어 있으면 안 되는 항목만 여기에. 나머지는 참고용이다.
TLS_ENV_KEYS = [
    "UV_DEFAULT_INDEX",
    "UV_INDEX",
    "UV_SYSTEM_CERTS",
    "NODE_EXTRA_CA_CERTS",
    "SSL_CERT_FILE",
    "REQUESTS_CA_BUNDLE",
    "npm_config_registry",
]

# uv 에서 이름이 바뀐 것들. 설정돼 있으면 어떻게 취급되는지 알려줘야 한다.
LEGACY_ENV_KEYS = {
    "UV_NATIVE_TLS": "UV_SYSTEM_CERTS 로 바꿀 것",
    "UV_INDEX_URL": "UV_DEFAULT_INDEX 권장",
}

# 현행 키를 먼저 본다. 구 키는 폴백으로만 인정한다.
UV_TLS_KEYS = ("system-certs", "native-tls")


def _row(label: str, value: Optional[str], note: str = "") -> Tuple[str, str, str]:
    return (label, value if value else "(없음)", note)


def read_uv_tls_setting(pyproject: Path) -> Tuple[Optional[str], Optional[str]]:
    """pyproject.toml 의 [tool.uv] TLS 설정을 읽는다.

    `(키이름, 값)` 을 돌려준다. 설정이 없으면 `(None, None)`.

    tomllib 은 Python 3.11+ 라 3.9 에서는 못 쓴다. 진단용이므로
    없으면 정규식으로 훑는다 — 여기서만 쓰는 대충 읽기다.
    """
    if not pyproject.is_file():
        return (None, None)

    text = pyproject.read_text(encoding="utf-8")

    try:
        import tomllib  # type: ignore[import-not-found]

        data = tomllib.loads(text)
        uv_table = data.get("tool", {}).get("uv", {})
        for key in UV_TLS_KEYS:
            if key in uv_table:
                return (key, str(uv_table[key]).lower())
        return (None, None)
    except ImportError:
        pass

    # tomllib 이 없는 3.8~3.10 대비 폴백. [tool.uv] 섹션의 주석 아닌 줄만 본다.
    found = {}
    in_uv = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_uv = line == "[tool.uv]"
            continue
        if not in_uv or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key in UV_TLS_KEYS:
            found[key] = value.split("#")[0].strip().lower()

    for key in UV_TLS_KEYS:
        if key in found:
            return (key, found[key])
    return (None, None)


def cmd_doctor() -> None:
    rows: List[Tuple[str, str, str]] = []

    rows.append(("--- 도구 ---", "", ""))

    # tasks.py 는 시스템 python 으로 돈다. 프로젝트가 요구하는 3.12 와 달라도
    # 정상이다 — 3.12 는 uv 가 따로 설치한다.
    running = "{}.{}.{}".format(*sys.version_info[:3])
    rows.append(_row("tasks.py 실행 python", running, sys.executable))

    if running.startswith(PROJECT_PYTHON + "."):
        note = "프로젝트 런타임과 동일"
    else:
        note = f"프로젝트 런타임 {PROJECT_PYTHON} 와 다르지만 정상 — 3.12 는 uv 가 따로 설치한다"
    rows.append(_row("  최소 요구", "{}.{}+".format(*MIN_PYTHON), note))
    rows.append(_row("node", capture(["node", "-v"])))
    rows.append(_row("npm", capture(["npm", "-v"])))
    rows.append(_row("uv", capture(["uv", "--version"])))

    rows.append(("", "", ""))
    rows.append(("--- 패키지 저장소 ---", "", ""))
    rows.append(
        _row(
            "npm registry",
            capture(["npm", "config", "get", "registry"], FRONTEND),
            "사내 Nexus 로 바꾸려면 frontend/.npmrc",
        )
    )
    rows.append(
        _row(
            "frontend/.npmrc",
            "있음" if (FRONTEND / ".npmrc").is_file() else None,
            ".npmrc.example 참고. 커밋 금지",
        )
    )

    rows.append(("", "", ""))
    rows.append(("--- TLS / 사내 CA ---", "", ""))
    for label, pyproject in [
        ("backend [tool.uv]", BACKEND / "pyproject.toml"),
        ("sample-api [tool.uv]", SAMPLE_API / "pyproject.toml"),
    ]:
        key, value = read_uv_tls_setting(pyproject)
        if key is None:
            rows.append(_row(label, None, "TLS 설정 없음"))
        else:
            note = "사내 CA 사용" if value == "true" else "공인 인증서만 신뢰"
            if key == "native-tls":
                note += "  !! deprecated 키 — system-certs 로 바꿀 것"
            rows.append(_row(label, f"{key} = {value}", note))

    for key in TLS_ENV_KEYS:
        rows.append(_row(key, os.environ.get(key)))

    # 구 환경변수는 설정돼 있을 때만 보여준다.
    # 신 키 없이 구 키만 있으면 아무 효과가 없으므로 강하게 표시한다.
    has_current = bool(os.environ.get("UV_SYSTEM_CERTS"))
    for key, hint in LEGACY_ENV_KEYS.items():
        value = os.environ.get(key)
        if not value:
            continue
        if key == "UV_NATIVE_TLS" and not has_current:
            note = "!! deprecated + 무시됨 — " + hint
        else:
            note = "deprecated — " + hint
        rows.append(_row(key, value, note))

    rows.append(("", "", ""))
    rows.append(("--- 설치 상태 ---", "", ""))
    for label, path in [
        ("frontend/node_modules", FRONTEND / "node_modules"),
        ("frontend/package-lock.json", FRONTEND / "package-lock.json"),
        ("backend/.venv", BACKEND / ".venv"),
        ("backend/uv.lock", BACKEND / "uv.lock"),
        ("sample-api/.venv", SAMPLE_API / ".venv"),
        ("sample-api/uv.lock", SAMPLE_API / "uv.lock"),
    ]:
        rows.append(_row(label, "있음" if path.exists() else None))

    label_w = max(width(r[0]) for r in rows) + 2
    value_w = max(width(r[1]) for r in rows) + 2

    print()
    print(f"  플랫폼: {sys.platform} / os.name={os.name}")
    print(f"  저장소: {ROOT}")
    print()
    for label, value, note in rows:
        if not label and not value:
            print()
            continue
        if label.startswith("---"):
            print(f"  {label}")
            continue
        print(f"    {pad(label, label_w)}{pad(value, value_w)}{note}")
    print()

    missing = [k for k in ("UV_DEFAULT_INDEX",) if not os.environ.get(k)]
    if missing:
        print("  사내망이라면 아래를 설정해야 한다 (자세한 내용은 각 .env.example):")
        print("    UV_DEFAULT_INDEX   사내 Python index URL")
        print("    UV_SYSTEM_CERTS    사내 CA 재서명 대응 (OS 신뢰 저장소 사용)")
        print("    NODE_EXTRA_CA_CERTS  사내 CA 인증서 경로")
        print()


# ---------------------------------------------------------------------------
# dev — 세 서버 동시 실행
# ---------------------------------------------------------------------------

SERVICES: List[Tuple[str, List[str], Path]] = [
    (
        "sample-api",
        ["uv", "run", "uvicorn", "app.main:app", "--reload", "--port", "8001"],
        SAMPLE_API,
    ),
    (
        "backend",
        ["uv", "run", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
        BACKEND,
    ),
    ("frontend", ["npm", "run", "dev"], FRONTEND),
]


def _spawn(name: str, cmd: List[str], cwd: Path) -> subprocess.Popen:
    """자식을 별도 프로세스 그룹으로 띄운다.

    그래야 종료할 때 손자 프로세스(uvicorn --reload 의 워커, next dev 의
    자식)까지 한 번에 정리할 수 있다. 그룹을 나누지 않으면 Ctrl+C 후에도
    포트를 물고 있는 프로세스가 남는다.
    """
    env = dict(os.environ)
    # 파이프로 받으므로 버퍼링을 끈다. 안 그러면 로그가 뭉텅이로 늦게 나온다.
    env["PYTHONUNBUFFERED"] = "1"

    kwargs = {}
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    return subprocess.Popen(
        [tool(cmd[0])] + cmd[1:],
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        **kwargs,
    )


def _pump(name: str, process: subprocess.Popen, label_w: int) -> None:
    """자식의 출력에 이름을 붙여 흘린다.

    make -j3 는 세 서버 로그를 그대로 섞어버려서 어느 서버가 죽었는지
    알 수 없었다. 여기서 줄마다 접두사를 붙인다.
    """
    stream = process.stdout
    if stream is None:
        return
    prefix = pad(f"[{name}]", label_w)
    for raw in iter(stream.readline, b""):
        line = raw.decode("utf-8", errors="replace").rstrip()
        print(f"{prefix} {line}", flush=True)
    stream.close()


def _signal_stop(process: subprocess.Popen) -> None:
    """정중한 종료 요청. 프로세스 그룹 전체에 보낸다."""
    if process.poll() is not None:
        return
    try:
        if IS_WINDOWS:
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except (OSError, ProcessLookupError):
        pass


def _force_stop(name: str, process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    print(f"[{name}] 응답이 없어 강제 종료한다", flush=True)
    try:
        if IS_WINDOWS:
            process.kill()
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass


def _stop_all(running: Sequence[Tuple[str, subprocess.Popen]]) -> None:
    """전부에게 먼저 신호를 보내고 나서 기다린다.

    하나씩 보내고 기다리면 최악의 경우 대기 시간이 프로세스 수만큼 곱해진다.
    """
    for _, process in running:
        _signal_stop(process)

    deadline = time.time() + 8
    for name, process in running:
        remaining = max(0.0, deadline - time.time())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            _force_stop(name, process)


def cmd_dev() -> None:
    if not (FRONTEND / "node_modules").is_dir():
        print("frontend/node_modules 가 없다. 먼저 설치한다.")
        cmd_setup()

    label_w = max(len(name) for name, _, _ in SERVICES) + 2

    print()
    print("  sample-api  http://localhost:8001")
    print("  backend     http://localhost:8000")
    print("  frontend    http://localhost:3000")
    print()
    print("  종료: Ctrl+C")
    print()

    running: List[Tuple[str, subprocess.Popen]] = []
    threads: List[threading.Thread] = []

    # KeyboardInterrupt 에만 기대지 않는다. 백그라운드로 띄우거나
    # 프로세스 관리자가 SIGTERM 을 보내는 경우에도 자식을 정리해야 한다.
    # (실제로 이 스크립트를 백그라운드에서 실행하면 SIGINT 가 무시된 채
    #  상속돼서, KeyboardInterrupt 가 영영 오지 않는다.)
    stop_requested = threading.Event()

    def _on_signal(signum, frame):  # type: ignore[no-untyped-def]
        stop_requested.set()

    for signame in ("SIGINT", "SIGTERM", "SIGBREAK"):
        signum = getattr(signal, signame, None)
        if signum is None:
            continue
        try:
            signal.signal(signum, _on_signal)
        except (ValueError, OSError):
            # 메인 스레드가 아니거나 플랫폼이 지원하지 않으면 넘어간다.
            pass

    try:
        for name, cmd, cwd in SERVICES:
            process = _spawn(name, cmd, cwd)
            running.append((name, process))
            thread = threading.Thread(
                target=_pump, args=(name, process, label_w), daemon=True
            )
            thread.start()
            threads.append(thread)

        while not stop_requested.is_set():
            for name, process in running:
                code = process.poll()
                if code is not None:
                    print(f"\n[{name}] 종료됐다 (코드 {code}). 나머지도 정리한다.", flush=True)
                    if code != 0:
                        print(
                            "포트가 이미 사용 중인지 확인할 것 — make doctor 로는 안 보인다.",
                            flush=True,
                        )
                    stop_requested.set()
                    break
            stop_requested.wait(0.3)
    except KeyboardInterrupt:
        pass
    finally:
        print("\n종료 중...", flush=True)
        _stop_all(running)
        for thread in threads:
            thread.join(timeout=2)
        print("정리 완료.", flush=True)


# ---------------------------------------------------------------------------
# 진입점
# ---------------------------------------------------------------------------

HANDLERS = {
    "help": cmd_help,
    "setup": cmd_setup,
    "dev": cmd_dev,
    "build": cmd_build,
    "test": cmd_test,
    "lint": cmd_lint,
    "gen-types": cmd_gen_types,
    "dump-spec": cmd_dump_spec,
    "show-quality": cmd_show_quality,
    "lock": cmd_lock,
    "doctor": cmd_doctor,
    "clean": cmd_clean,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tasks.py",
        description="swagger-rag-eval 작업 실행기",
        add_help=False,
    )
    parser.add_argument("command", nargs="?", default="help", choices=sorted(HANDLERS))
    args = parser.parse_args()
    HANDLERS[args.command]()


if __name__ == "__main__":
    main()
