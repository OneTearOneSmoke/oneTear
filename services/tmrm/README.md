# TMRM — Test Machine Resource Management（机器资源管理）

> 服务入口：`services/tmrm/cmd/server`
> 语言：Go 1.22+
> 数据：PostgreSQL（machines / pools / sessions / health_records）
> 协议：gRPC（计划在 TMRM.proto v2 定义，与现有 services.proto 同源）
> 关联设计：[`docs/architecture-v3-modules.md §6`](../../docs/architecture-v3-modules.md)

## 职责

- 机器注册 / 心跳 / 健康探针
- 机器分配 / 释放 / Quota 检查
- 多种分配策略（轮询 / 最少任务 / 标签亲和 / 反亲和 / 容量预留）

## 不做的事

- 不执行用例（由 EXF 负责）
- 不分析结果（由 TRM 负责）

## 当前状态

骨架阶段：定义 `Machine` / `Pool` / `Allocator` / `HealthChecker` 领域类型。
Sprint 6 接入 gRPC + Postgres。
