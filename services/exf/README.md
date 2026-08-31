# EXF — Execution Framework（执行框架）

> 服务入口：`services/exf/crates/server`
> 语言：Rust 1.78+ (edition 2021)
> 运行时：Tokio
> 协议：gRPC（参考 [`contracts/`](../../contracts/) 的 `aitest.plan.v1`）
> 关联设计：[`docs/architecture-v3-modules.md §4`](../../docs/architecture-v3-modules.md)

## 职责

- 接收 Plan，展开为 DAG，分发到 Worker
- 维护 Task 状态机（合法转移表）
- 通过 Broker（NATS JetStream）实现分布式协调
- 调用 Plugin SDK（gRPC）执行命令
- 回写 Result 事件至 TRM

## 不做的事

- 不存用例（由 TCM 负责）
- 不分配机器（由 TMRM 负责）
- 不分析结果（由 TRM 负责）

## Workspace 结构

```
services/exf/
├── crates/
│   ├── core/           # 类型 + 状态机（无 IO）
│   ├── scheduler/      # Plan → DAG → Task
│   ├── worker/         # Worker Pool
│   ├── broker/         # Broker trait + InMemory impl（NATS v0.8 落地）
│   └── server/         # main + gRPC + 调度主循环
└── Cargo.toml          # workspace
```

## 关键设计

- **调度热路径无 GC**：单调度协程 + 无锁队列 + 零拷贝序列化
- **状态机合法性编译期检查**：每个 transition 都通过 `StateMachine::can_transition` 校验
- **每个外部调用带超时**：默认 5s，可配置
- **可取消**：所有 IO 方法接收 `tokio_util::sync::CancellationToken`
