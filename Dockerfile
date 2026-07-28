# swagger-rag-eval — 이미지 2개를 한 Dockerfile 에서 만든다.
#
#     docker build --target backend  -t swagger-rag-eval-backend:1.0 .
#     docker build --target frontend -t swagger-rag-eval-frontend:1.0 .
#
# sample-api 는 이미지를 만들지 않는다. 평가 "대상"인 더미 API 이고
# 배포 대상이 아니다 (sample-api/README.md).
#
# ---------------------------------------------------------------------------
# 사내망 빌드
# ---------------------------------------------------------------------------
# 베이스 이미지·패키지 저장소·CA 를 전부 ARG 로 뺐다. 값은 여기 적지 않는다 —
# 이 저장소는 공개돼 있다. 실제 값은 빌드할 때 --build-arg 로 준다.
#
# 사내 패키지 레포는 **HTTP(평문)** 다. 그래서 pip 은 --trusted-host 가 필요하다:
#
#     docker build --target backend \
#       --build-arg PYTHON_IMAGE=<사내레지스트리>/python:3.12-slim \
#       --build-arg PIP_INDEX_URL=http://<사내레포>/repository/pypi/simple \
#       --build-arg PIP_TRUSTED_HOST=<사내레포> \
#       --build-arg UV_DEFAULT_INDEX=http://<사내레포>/repository/pypi/simple \
#       -t <사내레지스트리>/swagger-rag-eval-backend:1.0 .
#
#     docker build --target frontend \
#       --build-arg NODE_IMAGE=<사내레지스트리>/node:22-alpine \
#       --build-arg NPM_REGISTRY=http://<사내레포>/repository/npm-group/ \
#       -t <사내레지스트리>/swagger-rag-eval-frontend:1.0 .
#
# TLS 재서명 환경이면 사내 CA 를 certs/ 에 넣는다 (certs/README.md).
# 다만 레포가 HTTP 면 그 레포에는 TLS 자체가 없어 CA 와 무관하다.
#
# ---------------------------------------------------------------------------
# --build-arg 는 저장소에는 안 남지만 이미지 메타데이터에는 남을 수 있다
# ---------------------------------------------------------------------------
# ARG 로 빼는 1차 목적은 **사내 주소를 저장소에 커밋하지 않는 것**이고, 그건
# 확실히 달성된다. 다만 `ENV` 로 다시 굳히면 그 값이 이미지 설정에 그대로 박혀
# `docker history` / `docker inspect` 로 보인다.
#
# 그래서 사내 레포 주소는 **ENV 로 옮기지 않는다.** ARG 는 그 스테이지의 RUN 에
# 이미 환경변수로 노출되고, pip 과 uv 는 같은 이름의 환경변수를 직접 읽으므로
# ENV 가 필요 없다. 게다가 이 값들은 빌드 스테이지에만 있고 런타임 이미지로
# 넘어가지 않는다(멀티 스테이지).
#
# ---------------------------------------------------------------------------
# BASE_PATH 경고 — 읽고 넘어갈 것
# ---------------------------------------------------------------------------
# Next 의 basePath 는 **빌드 타임에 고정된다.** 런타임에 못 바꾼다.
# 그래서 BASE_PATH 는 ENV 가 아니라 빌드 ARG 다.
#
# open-questions #35 는 "단일 이미지 + 런타임 env 로 전 환경 승격" 으로
# 확정했는데, 환경마다 BASE_PATH 가 다르면 **그 전제가 깨진다.**
# 이미지가 환경 수만큼 갈리고, dev 에서 검증한 이미지를 prd 로 올리는 것이
# 불가능해진다.
#
# 둘 중 하나를 골라야 한다:
#   (1) 전 환경 동일 경로로 통일한다  <- 권장
#   (2) #35 를 철회하고 환경별 빌드를 받아들인다
# 자세한 내용은 docs/open-questions.md #45.

ARG PYTHON_IMAGE=python:3.12-slim
ARG NODE_IMAGE=node:22-alpine


# ===========================================================================
# backend — 빌드
# ===========================================================================

FROM ${PYTHON_IMAGE} AS backend-build

# ---------------------------------------------------------------------------
# 사내 패키지 레포 — HTTP(평문)
# ---------------------------------------------------------------------------
# 사내 표준 레포가 HTTP 로만 제공된다. **이건 HTTPS 검증을 끄는 것과 다르다.**
# 평문 레포에는 검증할 인증서 자체가 없다. HTTPS 레포에 대고 검증을 끄는 설정
# (npm strict-ssl=false 등)은 여전히 쓰지 않는다 — 그건 중간자 공격과 사내 CA
# 재서명을 구분할 수 없게 만든다.
#
# 도구별로 필요한 것이 다르다. 컨테이너 안에서 실제로 확인한 결과다:
#
#   pip  HTTP index 를 **--trusted-host 없이는 조용히 무시한다.** 경고 한 줄만
#        남기고 PyPI 로 나가려다 폐쇄망에서 타임아웃으로 끝난다:
#          WARNING: The repository located at <host> is not a trusted or
#                   secure host and is being ignored.
#        -> --trusted-host 가 **필수**다.
#
#   uv   HTTP index 에 그냥 붙는다. --allow-insecure-host 는 http 스킴 허용이
#        아니라 **TLS 인증서 검증을 건너뛰는** 옵션이라, 평문 레포에는 필요 없다.
#        -> UV_INSECURE_HOST 는 기본적으로 비워 둔다. 레포가 http→https 로
#           리다이렉트하거나 사설 인증서를 쓰는 경우에만 채운다.
#
# 값은 여기 적지 않는다. 형식만:
#   PIP_INDEX_URL     http://<사내레포>/repository/pypi/simple  (스킴 포함, /simple 로 끝남)
#   PIP_TRUSTED_HOST  <사내레포>            (호스트만. 스킴·경로 없이. 포트가 있으면 host:port)
#   UV_DEFAULT_INDEX  http://<사내레포>/repository/pypi/simple
#   UV_INSECURE_HOST  <사내레포> 또는 <사내레포>:8081  (보통 필요 없음)
#
# **빈 문자열 기본값은 pip·uv 모두 "설정 안 함" 과 같게 동작한다**(확인함).
# 그래서 인자를 하나도 안 주면 공개망 빌드가 그대로 된다.
#
# 예외가 UV_SYSTEM_CERTS 다. 이것만 빈 문자열이면 파싱에서 터진다:
#   error: Failed to parse environment variable `UV_SYSTEM_CERTS` with
#          invalid value ``: expected a boolish value
# 그래서 이것만 기본값이 false 다. **빈 문자열로 두지 말 것.**
ARG PIP_INDEX_URL=""
ARG PIP_TRUSTED_HOST=""
ARG UV_DEFAULT_INDEX=""
ARG UV_INSECURE_HOST=""
ARG UV_SYSTEM_CERTS=false

# 위 ARG 들은 이 스테이지의 RUN 에 이미 환경변수로 노출된다. pip 과 uv 가 같은
# 이름을 직접 읽으므로 ENV 로 다시 굳히지 않는다 — 굳히면 사내 레포 주소가
# 이미지 설정에 박힌다(파일 상단 참고).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 사내 CA 등록. certs/ 는 비어 있어도 되지만 **디렉토리는 있어야 한다** —
# COPY 는 대상이 없으면 빌드를 실패시킨다 (certs/.gitkeep 이 그 역할).
# 인증서가 없으면 등록할 것이 없을 뿐 빌드는 그대로 진행된다.
COPY certs/ /usr/local/share/ca-certificates/
RUN update-ca-certificates || true

# uv 자체를 설치한다. 이 단계만 pip 을 쓴다.
#
# 인자를 배열처럼 쌓는다. `--trusted-host ""` 를 넘기지 않으려면 조건이 두 겹
# 필요한데, 한 줄 명령으로 쓰면 빈 값이 그대로 인자로 들어간다.
RUN set -e; \
    if [ -n "$PIP_INDEX_URL" ]; then \
      set -- --index-url "$PIP_INDEX_URL"; \
      if [ -n "$PIP_TRUSTED_HOST" ]; then \
        set -- "$@" --trusted-host "$PIP_TRUSTED_HOST"; \
      else \
        echo "경고: PIP_INDEX_URL 이 http 면 PIP_TRUSTED_HOST 가 없을 때 그 레포는 무시된다" >&2; \
      fi; \
    else \
      set --; \
    fi; \
    pip install --no-cache-dir "$@" uv

WORKDIR /app

# 의존성 선언만 먼저 복사한다. 소스가 바뀌어도 이 레이어는 캐시된다.
COPY backend/pyproject.toml backend/uv.lock ./

# --frozen: 락을 그대로 쓴다. 락과 pyproject 가 어긋나면 조용히 다른 버전을
#   설치하는 대신 여기서 실패해야 한다.
# --no-dev: pytest/ruff/mypy 는 이미지에 넣지 않는다.
# --no-install-project: 아직 소스를 복사하지 않았다.
#
# 사내 index 는 UV_DEFAULT_INDEX / UV_INSECURE_HOST 환경변수로 이미 전달된다
# (위 ARG). 비어 있으면 설정 안 한 것과 같아서 여기 분기가 없다.
#
# 락에 박힌 index URL 이 사내 레포와 다르면 여기서 실패하는 것이 맞다.
# 조용히 다른 곳에서 받아오는 것보다 낫다 (docs/prompts.md §10-2).
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/app ./app


# ===========================================================================
# backend — 런타임
# ===========================================================================

FROM ${PYTHON_IMAGE} AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# 바인딩 주소.
#
# **컨테이너 안에서는 0.0.0.0 이어야 한다.** 127.0.0.1 로 두면 컨테이너
# 네트워크 네임스페이스 밖에서 닿을 수 없어, 포트를 매핑해도 연결이 거부되고
# k8s 의 probe 도 전부 실패한다. 컨테이너 격리가 이미 경계 역할을 하므로
# 여기서 0.0.0.0 은 안전하다.
#
# 로컬 개발(`make dev`)은 127.0.0.1 그대로다 — 거기서 0.0.0.0 으로 열면
# 같은 네트워크의 다른 기기에 개발 서버가 그대로 노출된다 (scripts/tasks.py).
ENV HOST=0.0.0.0 \
    PORT=8000

# non-root. 시스템 계정이라 로그인 셸을 주지 않는다.
RUN useradd --system --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=backend-build --chown=appuser:appuser /app/.venv ./.venv
COPY --from=backend-build --chown=appuser:appuser /app/app ./app

USER appuser

EXPOSE 8000

# exec form 이어야 uvicorn 이 PID 1 이 되고 SIGTERM 을 직접 받는다.
# shell form(CMD uvicorn ...)으로 쓰면 /bin/sh 가 PID 1 이 되어 신호를 자식에게
# 전달하지 않고, 파드 종료 때마다 grace period 를 다 쓰고 SIGKILL 당한다.
#
# `sh -c` 를 거치는 이유는 HOST/PORT 를 실제로 반영하기 위해서다.
# 순수 exec form 은 변수를 치환하지 않아 ["--host", "$HOST"] 가 문자열
# "$HOST" 그대로 넘어간다. 그러면 ENV 가 있어도 무용지물이고, 값을 하드코딩하면
# `docker run -e PORT=9000` 이 조용히 무시된다.
#
# **`exec` 가 핵심이다.** sh 가 uvicorn 으로 자신을 대체하므로 uvicorn 이 PID 1 이
# 되어 SIGTERM 을 직접 받는다. `exec` 를 빼면 sh 가 PID 1 로 남아 신호가 막힌다.
#
# --timeout-graceful-shutdown: 처리 중인 요청을 기다리는 시간.
#   k8s terminationGracePeriodSeconds 보다 짧아야 의미가 있다.
CMD ["sh", "-c", \
     "exec uvicorn app.main:app --host \"$HOST\" --port \"$PORT\" --timeout-graceful-shutdown 20"]


# ===========================================================================
# frontend — 빌드
# ===========================================================================

FROM ${NODE_IMAGE} AS frontend-build

# 사내 npm 레포도 HTTP 다. 형식: http://<사내레포>/repository/npm-group/
#
# **npm 은 http registry 에 추가 설정 없이 붙는다.** strict-ssl 은 https 연결의
# 인증서 검증 옵션이라 평문 registry 와는 무관하다. 그러니 먼저 이대로 시도하고,
# 정말 TLS 관련 오류가 날 때만(= 레포가 https 로 리다이렉트하는 경우) 아래 줄을
# 살린다. 기본으로 켜 두지 않는다 — 검증을 통째로 끄는 설정이다:
#
#     RUN npm config set strict-ssl false
#
# NODE_EXTRA_CA_CERTS 는 사내 CA 재서명 환경용이다. HTTP 레포만 쓴다면 필요 없다.
ARG NPM_REGISTRY=""
ARG NODE_EXTRA_CA_CERTS=""

# basePath 는 빌드 타임에 굳는다. 파일 상단 경고 참고.
ARG BASE_PATH=""

# NPM_REGISTRY 는 ENV 로 올리지 않는다 — 이미지 설정에 사내 주소를 남기지
# 않기 위해서다. 아래 RUN 에 ARG 로 그대로 전달된다.
ENV NODE_EXTRA_CA_CERTS=${NODE_EXTRA_CA_CERTS} \
    BASE_PATH=${BASE_PATH} \
    NEXT_TELEMETRY_DISABLED=1

# alpine 은 ca-certificates 가 기본으로 없다.
COPY certs/ /usr/local/share/ca-certificates/
RUN apk add --no-cache ca-certificates && update-ca-certificates || true

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./

# registry 를 .npmrc 에 쓰지 않고 인자로 넘긴다 — 파일로 남기면 그 레이어에
# 사내 주소가 그대로 박힌다. 값이 비어 있으면 기본 registry 를 쓴다.
#
# http:// registry 여도 여기서 따로 할 일이 없다. 위 ARG 주석 참고.
#
# npm ci 는 락을 그대로 재현한다. 사내 registry 로 바꾸면 락에 박힌
# registry.npmjs.org URL 과 어긋나 실패할 수 있는데, 그게 맞다 —
# 조용히 다른 버전을 설치하는 것보다 낫다 (docs/prompts.md §10-2).
RUN if [ -n "$NPM_REGISTRY" ]; then npm ci --registry="$NPM_REGISTRY"; else npm ci; fi

COPY frontend/ ./

RUN npm run build


# ===========================================================================
# frontend — 런타임
# ===========================================================================

FROM ${NODE_IMAGE} AS frontend

# standalone 산출물의 server.js 는 HOSTNAME / PORT 환경변수를 읽는다.
#
# **명시적으로 설정한다.** Next 버전에 따라 기본 바인딩 주소가 달라진 이력이
# 있어서, 기본값에 기대면 버전을 올릴 때 조용히 127.0.0.1 로 바뀌어 있을 수 있다.
# 그러면 이미지는 정상 기동하는데 포트 매핑도 probe 도 전부 실패한다 —
# 로그에는 "Ready" 만 찍혀 있어 원인을 찾기 어렵다.
#
# 이름이 HOST 가 아니라 HOSTNAME 인 것에 주의. backend 는 HOST 를 쓴다.
# server.js 가 보는 이름이 HOSTNAME 이라 맞출 수 없다.
#
# 로컬 개발(`next dev`)에는 설정하지 않는다. Dockerfile 안에서만 준다.
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

WORKDIR /app

# node 이미지에 이미 있는 비특권 계정.
USER node

# output: 'standalone' 이 만든 최소 산출물만 가져온다.
# node_modules 전체가 아니라 실제로 쓰이는 것만 들어 있어 이미지가 훨씬 작다.
COPY --from=frontend-build --chown=node:node /app/.next/standalone ./
COPY --from=frontend-build --chown=node:node /app/.next/static ./.next/static

# public/ 은 복사하지 않는다. 이 프로젝트에는 정적 파일이 없어서 디렉토리 자체가
# 없다 (폰트는 next/font/local 로 번들된다 — frontend/src/styles/fonts/README.md).
# 정적 파일이 생기면 아래 줄을 살린다:
# COPY --from=frontend-build --chown=node:node /app/public ./public

EXPOSE 3000

# standalone 산출물의 진입점. exec form 이라 node 가 PID 1 로 SIGTERM 을 받는다.
CMD ["node", "server.js"]
