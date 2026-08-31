# TRM — Test Report Management（测试报告管理）

> 服务入口：`services/trm/cmd/server`
> 语言：Go 1.22+（API）+ Rust（摄取，v0.8 落地）
> 数据：PostgreSQL（元数据）+ ClickHouse（聚合）+ S3（replays 资产）
> 协议：gRPC（参考 [`contracts/`](../../contracts/) 的 `aitest.result.v1`）
> 关联设计：[`docs/architecture-v3-modules.md §5`](../../docs/architecture-v3-modules.md)

## 职责

- 摄取 EXF 推送的 Result 事件（NATS → Rust 摄取 → ClickHouse）
- 提供查询 API（Result / Flaky / Baseline / Trend）
- 失败回放数据管理（S3 references）
- 告警规则（按 summary 阈值）

## 不做的事

- 不调度用例（由 EXF 负责）
- 不分析用例语义（只做时间序列与统计）

## 目录结构

```
services/trm/
├── cmd/server/                 # Go API 入口
├── internal/
│   ├── analyzer/               # FlakyDetector / Baseline / Trend
│   ├── store/                  # Adapter: postgres / clickhouse / s3
│   ├── api/                    # ResultService gRPC
│   ├── publisher/              # 告警事件
│   └── observability/
└── migrations/                 # SQL 迁移
```

## 当前状态

骨架阶段：定义了 `Analyzer` 接口 + `ResultStore` 接口 + 3 个内置分析器 stub。
