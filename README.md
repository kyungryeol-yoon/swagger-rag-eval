# swagger-rag-eval

> API 명세는 AI에게 잘 검색될까?

Swagger(OpenAPI) 명세가 자연어 질문으로 얼마나 잘 검색되는지 평가하고,
낮은 인식률의 원인과 개선 방향을 리포트로 보여주는 대시보드.

## 왜 필요한가

사용자가 API를 만들면 Swagger가 자동 생성된다. 다른 사용자가 AI에게
"환불 신청은 어떻게 취소하나요?" 라고 물었을 때, RAG가 올바른 엔드포인트를
찾아내려면 `summary` / `description` 이 충분해야 한다.

이 프로젝트는 **그 명세가 실제로 검색되는지를 100개 질문으로 측정**하고,
실패 원인을 분류해 무엇을 보강해야 하는지 알려준다.

## 구조

| 디렉토리 | 역할 |
|---|---|
| `sample-api/` | 평가 대상. description 품질을 GOOD/POOR/EMPTY 3등급으로 의도적으로 나눈 더미 API. **배포 대상이 아니라 시연/실험용** ([README](sample-api/README.md)) |
| `backend/` | 평가 파이프라인 + 대시보드 API (FastAPI) |
| `frontend/` | 대시보드 (Next.js 16 App Router) |
| `docs/` | 응답 계약, 작업 프롬프트, 미정 항목 |

`sample-api`를 따로 두는 이유: 가짜 fixture만으로는
"description이 부실하면 인식률이 떨어진다"는 전제 자체를 검증할 수 없기 때문.

## 시작하기

```bash
make setup    # 의존성 설치
make dev      # sample-api(8001) + backend(8000) + frontend(3000) 동시 실행
make test
make lint
```

`make dev` 는 **세 개**를 띄우고, 로그에 서비스 이름을 붙여준다.
Ctrl+C 하면 자식 프로세스까지 정리한다. 하나가 죽으면 나머지도 함께 내린다.

그 외 타겟은 `make help` 로 볼 수 있다. 자주 쓰는 것:

| 타겟 | 하는 일 |
|---|---|
| `make doctor` | 환경 진단. 도구 버전·저장소·인증서·설치 상태를 표로 |
| `make dump-spec` | sample-api 의 `openapi.json` 을 평가기 입력으로 덤프 |
| `make show-quality` | sample-api 엔드포인트별 설명 품질을 표로 출력 |
| `make gen-types` | 백엔드 OpenAPI → 프론트 타입 생성 (백엔드가 8000에 떠 있어야 한다) |
| `make lock` | `uv.lock` 재생성 (사내 저장소 전환 시) |

**make 가 없어도 된다.** 모든 타겟은 아래와 동일하다. Windows cmd 에서
make 를 구하기 어려우면 이쪽을 쓴다.

```bash
python scripts/tasks.py <command>
```

**Python 3.12 이상이 필요하다.** `scripts/tasks.py` 최상단의 버전 가드가
미달이면 무엇을 하면 되는지 알려주고 멈춘다.

`python3` 가 3.12 미만으로 잡히는 환경이 흔하다 — 예를 들어 macOS 는
`/usr/bin/python3`(Xcode 번들, 3.9)가 Homebrew 보다 PATH 앞에 있는 경우가 많다.
그럴 때는 `PY` 를 덮어쓴다.

```bash
make PY=python3.12 test           # 한 번만
export PY=python3.12              # 셸에 걸어두면 이후 make 는 그냥 쓴다
```

Windows 에서 `python3` 를 찾지 못하면 `make PY=python` 을 쓴다.
(Windows 의 `python3.exe` 는 Microsoft Store 실행 별칭일 수 있어, 파이썬이
설치돼 있지 않으면 스토어 창이 뜨고 아무것도 실행되지 않는다.)

어떤 python 이 잡혔는지는 `make doctor` 의 맨 위 네 줄에서 확인한다.

Makefile 에는 셸 로직이 없다. Windows 에서 make 는 레시피를 `cmd.exe` 로
실행해서 `[ ]`·파이프·`grep` 이 전부 깨지기 때문에, 로직은 전부
`scripts/tasks.py` 에 있다. 고칠 일이 있으면 Makefile 이 아니라 그 파일을 고친다.

## 사내망 최초 셋업

폐쇄망은 PyPI·npmjs 에 나갈 수 없고 TLS 가 사내 CA 로 재서명된다.
**설치 전에 환경변수부터 잡는다.** 자세한 배경은 [`docs/prompts.md`](docs/prompts.md) §10.

### 1. 환경변수 설정

```bash
# macOS / Linux — ~/.zshrc 등에
export UV_DEFAULT_INDEX=https://<사내 index>/simple
export UV_SYSTEM_CERTS=true
export NODE_EXTRA_CA_CERTS=/path/to/corp-ca-bundle.pem
```

```powershell
# Windows PowerShell — 영구 설정
setx UV_DEFAULT_INDEX "https://<사내 index>/simple"
setx UV_SYSTEM_CERTS "true"
setx NODE_EXTRA_CA_CERTS "C:\path\to\corp-ca-bundle.pem"
```

npm registry 는 환경변수가 아니라 파일로 잡는다.

```bash
cp frontend/.npmrc.example frontend/.npmrc   # 실제 값을 채운다. 커밋하지 않는다
```

> 구 `UV_NATIVE_TLS` 는 deprecated 이고 현행은 `UV_SYSTEM_CERTS` 다.
> 구 이름은 **오류 없이 조용히 무시되므로**, 설정했는데 인증서 오류가 그대로면
> 이걸 의심한다. uv 구버전 호환이 필요하면 둘 다 설정해도 된다.
> 파일로 고정하려면 각 `pyproject.toml` 의 `[tool.uv] system-certs`.
>
> `strict-ssl=false` 는 쓰지 않는다. 인증서 검증을 통째로 끄는 것이라
> 오류의 해결이 아니라 은폐다.

### 2. 진단

```bash
make doctor
```

도구 버전, 활성 index/registry, 인증서 환경변수, 설치 상태가 한 화면에 나온다.
`(없음)` 으로 표시된 항목이 곧 빠진 설정이다.

### 3. 락 재생성

```bash
make lock          # uv.lock 을 사내 index 기준으로 다시 만든다
```

커밋된 락은 GitHub 기준이라 사내 index 와 맞지 않는다.
**여기서 만들어진 락은 사내 로컬 전용이며 GitHub 로 되돌리지 않는다.**
`package-lock.json` 도 마찬가지로, `npm ci` 가 실패하면 `npm install` 로 다시 만든다.

### 4. 설치

```bash
make setup
```

## 컨테이너 이미지

루트 `Dockerfile` 하나에서 두 이미지를 만든다. `sample-api` 는 만들지 않는다 —
평가 대상인 더미 API 이고 배포 대상이 아니다.

```bash
docker build --target backend  -t swagger-rag-eval-backend:1.0 .
docker build --target frontend -t swagger-rag-eval-frontend:1.0 .
```

**두 이미지는 같은 버전 태그를 붙여 세트로 승격한다.** 프론트는 백엔드의
응답 계약에 맞춰 타입이 생성돼 있어(`src/lib/api-types.ts`) 버전이 어긋나면
화면이 조용히 깨진다. `backend:1.1` 과 `frontend:1.0` 을 섞어 올리지 않는다.

### 사내 레지스트리 / 저장소

베이스 이미지와 패키지 저장소는 전부 빌드 ARG 다. 값은 저장소에 없다.

```bash
docker build --target backend \
  --build-arg PYTHON_IMAGE=<사내레지스트리>/python:3.12-slim \
  --build-arg UV_DEFAULT_INDEX=https://<사내index>/simple \
  --build-arg UV_SYSTEM_CERTS=true \
  -t <사내레지스트리>/swagger-rag-eval-backend:1.0 .

docker build --target frontend \
  --build-arg NODE_IMAGE=<사내레지스트리>/node:22-alpine \
  --build-arg NPM_REGISTRY=https://<사내nexus>/repository/npm-group/ \
  -t <사내레지스트리>/swagger-rag-eval-frontend:1.0 .
```

TLS 재서명 환경이면 사내 CA(`*.crt`)를 `certs/` 에 넣는다 ([certs/README.md](certs/README.md)).
인증서 파일은 커밋되지 않는다.

| ARG | 기본값 | 대상 |
|---|---|---|
| `PYTHON_IMAGE` | `python:3.12-slim` | backend |
| `NODE_IMAGE` | `node:22-alpine` | frontend |
| `UV_DEFAULT_INDEX` | `https://pypi.org/simple` | backend |
| `UV_SYSTEM_CERTS` | `false` | backend |
| `PIP_INDEX_URL` | `https://pypi.org/simple` | backend (uv 설치용) |
| `NPM_REGISTRY` | (비움 = 기본 registry) | frontend |
| `NODE_EXTRA_CA_CERTS` | (비움) | frontend |
| `BASE_PATH` | (비움 = 루트) | frontend |

> `UV_SYSTEM_CERTS` 를 빈 문자열로 두면 안 된다. `ENV` 는 빈 값도 "설정됨" 으로
> 만들고, uv 가 boolish 파싱에 실패해 빌드가 죽는다. 끄려면 `false` 를 명시한다.

> **`BASE_PATH` 는 이미지에 굳는다.** 런타임 환경변수가 아니라 빌드 ARG 다.
> 환경마다 값이 다르면 이미지가 갈리고, "단일 이미지를 dev→stg→prd 로 승격"
> 하는 전제가 깨진다. 자세한 내용은 [`docs/open-questions.md`](docs/open-questions.md) #45.

### 배포에 필요한 정보

k8s manifest 는 이 저장소에서 만들지 않는다 (사내에서 별도 작성).
매니페스트를 쓰는 데 필요한 것만 적는다.

| | backend | frontend |
|---|---|---|
| 포트 | `8000` | `3000` |
| 실행 유저 | `appuser` (uid 999) | `node` (uid 1000) |
| liveness | `GET /health` | `GET /api/health` |
| readiness | `GET /ready` (실패 시 503) | `GET /api/health` |
| 런타임 환경변수 | `CORS_ORIGINS`, `SRE_*` (아래 표) | `API_BASE_URL` |

- 두 이미지 모두 `CMD` 가 exec form 이라 **SIGTERM 이 앱에 직접 전달된다.**
  `terminationGracePeriodSeconds` 는 25 이상을 권장한다 —
  uvicorn 이 `--timeout-graceful-shutdown 20` 으로 처리 중인 요청을 기다린다.
- 프론트의 `/api/health` 는 백엔드 상태를 보지 않는다. 백엔드가 죽었다고
  프론트 파드까지 재시작되면 장애가 번지기만 한다.
- `BASE_PATH` 를 쓰면 프론트의 probe 경로도 그 아래로 내려간다
  (`/swagger-eval/api/health`).

## 환경변수

전부 **런타임**에 읽는다 (`BASE_PATH` 제외). 이미지를 다시 빌드하지 않고
같은 산출물을 dev → stg → prd 로 승격할 수 있어야 하기 때문이다.
각 디렉토리의 `.env.example` 을 복사해서 쓴다.

### backend

| 변수 | 기본값 | 설명 |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:3000` | 대시보드 출처. 콤마로 구분 |
| `SRE_SAMPLE_API_BASE_URL` | `http://localhost:8001` | 평가 대상 API 주소 |
| `SRE_FIXTURE_DIR` | `backend/app/fixtures` | 저장소가 읽는 디렉토리 |
| `SRE_READINESS_TRACE_ID` | `A492` | `/ready` 가 존재를 확인할 평가 결과 |

### frontend

| 변수 | 기본값 | 설명 |
|---|---|---|
| `API_BASE_URL` | `http://localhost:8000` | 백엔드 주소. **서버 컴포넌트 전용** |
| `BASE_PATH` | (빈 값) | 서브패스 배포 시 접두사. 예: `/swagger-eval`. **빌드 타임에 고정** |

`NEXT_PUBLIC_` 접두사를 쓴 변수는 의도적으로 하나도 없다. 그 접두사가 붙으면
값이 클라이언트 번들에 박혀서 단일 이미지 다환경 승격이 불가능해진다.
백엔드로 fetch 하는 코드는 전부 `frontend/src/lib/config.ts` 를 경유한다.

### 헬스 체크

| 경로 | 서비스 | 용도 |
|---|---|---|
| `/health` | backend | liveness. 프로세스 생존만 확인 |
| `/ready` | backend | readiness. 데이터 소스가 읽히는지 확인, 실패 시 503 |
| `/api/health` | frontend | liveness. 백엔드 상태는 보지 않는다 |

## 문서

- [`docs/contract.md`](docs/contract.md) — 응답 계약 (**단일 진실 공급원**)
- [`docs/prompts.md`](docs/prompts.md) — Phase별 작업 프롬프트
- [`docs/open-questions.md`](docs/open-questions.md) — 미정 항목 추적

## 제약

폐쇄망 배포를 전제로 한다. 외부 CDN·폰트·이미지를 참조하지 않으며,
새 npm 패키지를 추가하지 않는다. 자세한 내용은 [`CLAUDE.md`](CLAUDE.md).
