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
#     docker build --target backend \
#       --build-arg PYTHON_IMAGE=<사내레지스트리>/python:3.12-slim \
#       --build-arg UV_DEFAULT_INDEX=https://<사내index>/simple \
#       --build-arg UV_SYSTEM_CERTS=true \
#       -t <사내레지스트리>/swagger-rag-eval-backend:1.0 .
#
# TLS 재서명 환경이면 사내 CA 를 certs/ 에 넣는다 (certs/README.md).
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

# 사내 저장소 / TLS. 기본값은 공개 저장소다. 사내에서는 --build-arg 로 덮어쓴다.
#
# **빈 문자열을 기본값으로 두지 말 것.** ENV 는 빈 값도 "설정됨"으로 만들고,
# uv 는 UV_SYSTEM_CERTS="" 를 boolish 로 파싱하려다 실패한다:
#   error: Failed to parse environment variable `UV_SYSTEM_CERTS` with
#          invalid value ``: expected a boolish value
ARG UV_DEFAULT_INDEX=https://pypi.org/simple
ARG UV_SYSTEM_CERTS=false
ARG PIP_INDEX_URL=https://pypi.org/simple

ENV UV_DEFAULT_INDEX=${UV_DEFAULT_INDEX} \
    UV_SYSTEM_CERTS=${UV_SYSTEM_CERTS} \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 사내 CA 등록. certs/ 는 비어 있어도 되지만 **디렉토리는 있어야 한다** —
# COPY 는 대상이 없으면 빌드를 실패시킨다 (certs/.gitkeep 이 그 역할).
# 인증서가 없으면 등록할 것이 없을 뿐 빌드는 그대로 진행된다.
COPY certs/ /usr/local/share/ca-certificates/
RUN update-ca-certificates || true

# uv 자체를 설치한다. 이 단계만 pip 을 쓴다.
RUN pip install --no-cache-dir uv

WORKDIR /app

# 의존성 선언만 먼저 복사한다. 소스가 바뀌어도 이 레이어는 캐시된다.
COPY backend/pyproject.toml backend/uv.lock ./

# --frozen: 락을 그대로 쓴다. 락과 pyproject 가 어긋나면 조용히 다른 버전을
#   설치하는 대신 여기서 실패해야 한다.
# --no-dev: pytest/ruff/mypy 는 이미지에 넣지 않는다.
# --no-install-project: 아직 소스를 복사하지 않았다.
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/app ./app


# ===========================================================================
# backend — 런타임
# ===========================================================================

FROM ${PYTHON_IMAGE} AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# non-root. 시스템 계정이라 로그인 셸을 주지 않는다.
RUN useradd --system --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=backend-build --chown=appuser:appuser /app/.venv ./.venv
COPY --from=backend-build --chown=appuser:appuser /app/app ./app

USER appuser

EXPOSE 8000

# exec form 이어야 uvicorn 이 PID 1 이 되고 SIGTERM 을 직접 받는다.
# shell form 으로 쓰면 /bin/sh 가 PID 1 이 되어 신호를 자식에게 전달하지 않고,
# 파드 종료 때마다 grace period 를 다 쓰고 SIGKILL 당한다.
#
# --timeout-graceful-shutdown: 처리 중인 요청을 기다리는 시간.
#   k8s terminationGracePeriodSeconds 보다 짧아야 의미가 있다.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--timeout-graceful-shutdown", "20"]


# ===========================================================================
# frontend — 빌드
# ===========================================================================

FROM ${NODE_IMAGE} AS frontend-build

ARG NPM_REGISTRY=""
ARG NODE_EXTRA_CA_CERTS=""

# basePath 는 빌드 타임에 굳는다. 파일 상단 경고 참고.
ARG BASE_PATH=""

ENV NODE_EXTRA_CA_CERTS=${NODE_EXTRA_CA_CERTS} \
    BASE_PATH=${BASE_PATH} \
    NEXT_TELEMETRY_DISABLED=1

# alpine 은 ca-certificates 가 기본으로 없다.
COPY certs/ /usr/local/share/ca-certificates/
RUN apk add --no-cache ca-certificates && update-ca-certificates || true

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./

# registry 를 .npmrc 에 쓰지 않고 인자로 넘긴다 — 이미지 레이어에 사내 주소가
# 남지 않는다. 값이 비어 있으면 기본 registry 를 쓴다.
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

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

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
