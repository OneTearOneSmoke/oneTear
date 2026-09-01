# 顶层 Makefile —— 一键复现 CI
#
# 用法：
#   make ci              跑全部 CI 步骤
#   make ci-contracts    只跑 contracts 检查
#   make ci-rust         只跑 Rust 测试链
#   make ci-go           只跑 Go 测试链
#   make ci-python       只跑 Python 测试链
#   make clean           清理生成产物

BUF ?= $(shell command -v buf 2>/dev/null)
GO  ?= $(shell command -v go 2>/dev/null)
CARGO ?= $(shell command -v cargo 2>/dev/null)
PYTHON ?= $(shell command -v python3 2>/dev/null)

CONTRACTS_DIR := contracts
SERVICES_DIR  := services
SDK_DIR       := sdk
GEN_DIR       := $(CONTRACTS_DIR)/gen

.PHONY: help
help:
	@echo "Targets:"
	@echo "  ci           全部（contracts + rust + go + python）"
	@echo "  ci-contracts buf lint/format + generate"
	@echo "  ci-rust      cargo fmt + clippy + test"
	@echo "  ci-go        buf generate + go vet + build + test"
	@echo "  ci-python    pytest + import smoke"
	@echo "  clean        清理 gen/ 与 __pycache__"

.PHONY: ci
ci: ci-contracts ci-rust ci-go ci-python

.PHONY: ci-contracts
ci-contracts:
	@echo "=== contracts: lint ==="
	@if [ -z "$(BUF)" ]; then echo "buf not installed; install from https://buf.build/docs/installation"; exit 1; fi
	cd $(CONTRACTS_DIR) && $(BUF) lint
	@echo "=== contracts: format --exit-code ==="
	cd $(CONTRACTS_DIR) && $(BUF) format --exit-code -d

.PHONY: ci-rust
ci-rust:
	@echo "=== rust: fmt ==="
	cd $(SERVICES_DIR)/exf && $(CARGO) fmt --all -- --check
	cd $(SDK_DIR)/plugin-sdk-rust && $(CARGO) fmt -- --check
	@echo "=== rust: clippy ==="
	cd $(SERVICES_DIR)/exf && $(CARGO) clippy --workspace --all-targets -- -D warnings
	@echo "=== rust: test ==="
	cd $(SERVICES_DIR)/exf && $(CARGO) test --workspace
	cd $(SDK_DIR)/plugin-sdk-rust && $(CARGO) test

.PHONY: ci-go
ci-go:
	@echo "=== go: buf generate ==="
	cd $(CONTRACTS_DIR) && $(BUF) generate --template '{"version":"v2","managed":{"enabled":true,"override":[{"file_option":"go_package_prefix","path":"github.com/aitest/contracts/gen/go"}]},"plugins":[{"remote":"buf.build/protocolbuffers/go","out":"gen/go"},{"remote":"buf.build/grpc/go","out":"gen/go"}]}'
	@echo "=== go: services ==="
	@for svc in tcm trm tmrm; do \
		echo "--- go: $$svc ---"; \
		cd $(SERVICES_DIR)/$$svc && $(GO) vet ./... && $(GO) build ./... && $(GO) test -race -count=1 ./...; \
		cd ../..; \
	done
	@echo "=== go: sdk/plugin-sdk-go ==="
	cd $(SDK_DIR)/plugin-sdk-go && $(GO) vet ./... && $(GO) build ./... && $(GO) test -race -count=1 ./...

.PHONY: ci-python
ci-python:
	@echo "=== python: pytest ==="
	cd $(SDK_DIR)/plugin-sdk-python && $(PYTHON) -m pip install --quiet --user pytest
	cd $(SDK_DIR)/plugin-sdk-python && $(PYTHON) -m pytest tests/
	@echo "=== python: import smoke ==="
	cd $(SDK_DIR)/plugin-sdk-python && PYTHONPATH=src $(PYTHON) -c "from aitest_sdk import PluginServer; s=PluginServer(name='x'); print('SDK smoke OK')"

.PHONY: clean
clean:
	rm -rf $(GEN_DIR)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name target -exec rm -rf {} + 2>/dev/null || true
