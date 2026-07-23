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

> `UV_SYSTEM_CERTS` 는 uv 0.11 부터의 이름이다. 예전 문서의 `UV_NATIVE_TLS` 는
> **오류 없이 조용히 무시된다.** 설정했는데 인증서 오류가 그대로면 이걸 의심한다.
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
