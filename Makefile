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

# python 실행 파일 이름이 플랫폼마다 다르다.
# Windows 는 `python`, macOS/Linux 는 보통 `python3` 만 있다.
# 이건 셸 분기가 아니라 make 자체의 조건문이라 cmd.exe 를 거치지 않는다.
# 다르게 부르고 싶으면 덮어쓸 수 있다:  make PY=py test
ifeq ($(OS),Windows_NT)
PY ?= python
else
PY ?= python3
endif

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
