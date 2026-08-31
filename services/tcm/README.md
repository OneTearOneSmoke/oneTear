# TCM — Test Case Management（用例管理）

> 服务入口：`services/tcm/cmd/server`
> 语言：Go 1.22+
> 数据：PostgreSQL（JSONB + tsvector + pgvector）+ S3（cas 资产）
> 协议：gRPC（参考 [`contracts/`](../../contracts/) 的 `aitest.case.v1` 与 `aitest.plan.v1`）
> 关联设计：[`docs/architecture-v3-modules.md §3`](../../docs/architecture-v3-modules.md)

## 职责

- 用例 CRUD（content-hash 寻址 + semver 版本化）
- 标签 / 全文 / 向量 / lifecycle 多维检索
- Plan 提交时的 ResolvedCaseRef 展开（立即冻结，防 TCM 变更影响 EXF）
- 事件发布（Plan 提交 / 用例 lifecycle 变更 / 大规模 import）

## 不做的事

- 不执行用例（由 EXF 负责）
- 不存储执行结果（由 TRM 负责）
- 不分配机器（由 TMRM 负责）

## 目录结构

```
services/tcm/
├── cmd/server/                 # 入口
├── internal/
│   ├── domain/                 # Case / Lifecycle / Version / Store interface
│   ├── store/                  # Adapter: postgres / inmem / search
│   ├── api/                    # gRPC 服务实现 + HTTP Gateway
│   ├── publisher/              # 事件发布（NATS / Kafka）
│   └── observability/          # OTel 接入模板
└── migrations/                 # SQL 迁移
```

## 当前状态

骨架阶段：定义了 `CaseStore` 接口 + `Case` 领域类型 + gRPC server stub。
后续 Sprint 填充：

| Sprint | 交付 |
| --- | --- |
| S1 | InMem Adapter + 单测 + 烟囱测试 |
| S2 | Postgres + tsvector + pgvector |
| S3 | 事件发布（NATS） |
| S6 | Git Bridge（同步 git 仓的 case YAML） |
| S7 | MCP Server 暴露 search 工具 |
