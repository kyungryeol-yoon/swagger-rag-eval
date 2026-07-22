.PHONY: help setup dev dev-sample dev-backend dev-frontend build test lint gen-types dump-spec show-quality clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## 의존성 설치
	cd sample-api && uv sync
	cd backend && uv sync
	cd frontend && ([ -f package-lock.json ] && npm ci || npm install)

dev: ## 세 서버 동시 실행
	@$(MAKE) -j3 dev-sample dev-backend dev-frontend

dev-sample: ## 평가 대상 API (8001)
	cd sample-api && uv run uvicorn app.main:app --reload --port 8001

dev-backend: ## 평가기 API (8000)
	cd backend && uv run uvicorn app.main:app --reload --port 8000

dev-frontend: ## 대시보드 (3000)
	@[ -d frontend/node_modules ] || (cd frontend && npm install)
	cd frontend && npm run dev

build: ## 프로덕션 빌드
	cd frontend && npm run build

test: ## 테스트
	cd backend && uv run pytest -q
	cd sample-api && uv run pytest -q

lint: ## 린트 + 타입체크
	cd backend && uv run ruff check . && uv run mypy app
	cd frontend && npm run lint && npx tsc --noEmit

gen-types: ## 백엔드 OpenAPI -> 프론트 타입 생성
	cd frontend && npm run gen:types

dump-spec: ## sample-api 의 openapi.json 덤프
	cd sample-api && uv run python -m app.scripts.dump_openapi

show-quality: ## sample-api 엔드포인트별 설명 품질 표
	cd sample-api && uv run python -m app.scripts.show_quality

clean:
	rm -rf frontend/.next frontend/out
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
