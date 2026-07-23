# 이 Makefile 에는 셸 로직이 없다.
#
# Windows 에서 make 는 레시피를 cmd.exe 로 실행한다. [ ] 테스트, 서브셸,
# ||, 파이프, grep/awk 는 cmd 에서 그대로 깨진다. git bash 에서만 되는
# Makefile 은 사내 PC 에서 재현이 안 된다.
#
# 그래서 모든 타겟은 scripts/tasks.py 를 한 줄로 부르기만 한다.
# 로직을 고칠 일이 있으면 Makefile 이 아니라 그 파일을 고친다.
#
# make 없이도 같은 것을 할 수 있다:
#     python scripts/tasks.py <command>

# tasks.py 를 실행할 python. **3.12 이상이어야 한다** (버전 가드가 확인한다).
#
# `?=` 라서 환경변수나 인자로 덮어쓸 수 있다:
#     make PY=python3.12 test      python3 가 3.12 미만으로 잡힐 때
#     make PY=python test          Windows 에서 python3 를 못 찾을 때
#     export PY=python3.12         셸에 걸어두면 이후 make 는 그냥 쓴다
#
# venv 를 활성화해 두면 `python3` 가 그 venv 의 것으로 잡힌다 — 별도 설정이 없다.
# 다만 tasks.py 는 프로젝트 의존성이 필요 없으므로 활성화하지 않아도 된다.
# 지금 어떤 python 이 잡혔는지는 `make doctor` 로 확인한다.
PY ?= python3

TASKS := $(PY) scripts/tasks.py

.PHONY: help setup dev build test lint gen-types dump-spec show-quality lock doctor clean

help:
	$(TASKS) help

setup:
	$(TASKS) setup

dev:
	$(TASKS) dev

build:
	$(TASKS) build

test:
	$(TASKS) test

lint:
	$(TASKS) lint

gen-types:
	$(TASKS) gen-types

dump-spec:
	$(TASKS) dump-spec

show-quality:
	$(TASKS) show-quality

lock:
	$(TASKS) lock

doctor:
	$(TASKS) doctor

clean:
	$(TASKS) clean
