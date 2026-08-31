# contracts/Makefile
#
# 常用入口。所有目标都基于本地 `buf`（推荐 v1.32+）。
# 安装 buf：https://buf.build/docs/installation

BUF ?= buf
PROTO_DIR := proto
GEN_DIR := gen

.PHONY: help
help: ## 列出本 Makefile 的所有目标
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## 安装 buf（macOS / Linux）
	@command -v $(BUF) >/dev/null 2>&1 || { \
		echo "buf 未安装。正在安装..."; \
		curl -sSL "https://github.com/bufbuild/buf/releases/download/v1.34.0/buf-Linux-x86_64" -o /usr/local/bin/buf && \
		chmod +x /usr/local/bin/buf; \
	}

.PHONY: format
format: ## buf format -w
	$(BUF) format -w $(PROTO_DIR)

.PHONY: lint
lint: ## buf lint 静态检查
	$(BUF) lint $(PROTO_DIR)

.PHONY: breaking
breaking: ## buf breaking 对比 git HEAD（CI 用）
	$(BUF) breaking --against '.git#branch=main,subdir=proto'

.PHONY: generate
generate: ## buf generate 生成多语言代码（Go/Rust/Python/Java/TS）
	$(BUF) generate

.PHONY: clean
clean: ## 清理生成产物
	rm -rf $(GEN_DIR)

.PHONY: all
all: format lint generate ## format + lint + generate

.PHONY: verify
verify: lint breaking ## CI 入口：lint + breaking
