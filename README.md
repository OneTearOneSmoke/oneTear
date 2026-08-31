# OneTear — AI 时代测试平台（v3 架构）

> **新架构 v3**：所有模块按"海量用例 / 高并发 / 可扩展 / 可观测"原则重新设计。
>
> Python 原型（`src/aitest/`）作为**语义参考**保留，不再维护。

## 顶层结构

```
oneTear/
├── contracts/         # Protobuf IDL（4 个契约：case / plan / result / plugin）
├── services/          # 业务服务
│   ├── tcm/           # 用例管理（Go）
│   ├── exf/           # 执行框架（Rust workspace）
│   ├── trm/           # 测试报告（Go + Rust ingest）
│   └── tmrm/          # 机器资源（Go）
├── sdk/               # 插件 SDK
│   ├── plugin-sdk-go/
│   ├── plugin-sdk-rust/
│   └── plugin-sdk-python/
├── clients/           # 用户面客户端
│   ├── cli/           # Python CLI（Sprint 7）
│   └── mcp_server/    # MCP Server（Sprint 7）
├── docs/              # 设计文档
│   ├── architecture-v3-modules.md  ← 整体架构 + 各模块接口
│   └── ai-test/                     ← 原型阶段设计文档（保留为参考）
└── src/aitest/        # Python 原型（保留为语义参考，不再维护）
```

## Sprint 路线

| Sprint | 主题 | 状态 |
| --- | --- | --- |
| S0 | 协议（Protobuf IDL） | ✅ 已完成 |
| **S0.5** | **模块骨架 + 接口定义（当前）** | ✅ 已完成 |
| S1 | 最小端到端（TCM inmem + EXF inmem broker + db_sqlite 插件） | 待启动 |
| S2 | TCM PG + tsvector + pgvector | 待启动 |
| S3 | EXF NATS 分布式 | 待启动 |
| S4 | TRM 接入 | 待启动 |
| S5 | PLG 完善（多语言 SDK + Sandbox） | 待启动 |
| S6 | TMRM 接入 | 待启动 |
| S7 | CLI + MCP Server | 待启动 |
| S8 | v1.0 GA | 待启动 |

## 模块接口速查

详见 [`docs/architecture-v3-modules.md`](docs/architecture-v3-modules.md)

| 模块 | 关键接口 | 语言 |
| --- | --- | --- |
| TCM | `CaseStore` / `EventPublisher` | Go |
| EXF | `Scheduler` / `Worker` / `Broker` / `StateMachine` | Rust |
| TRM | `Analyzer` / `ResultStore` | Go |
| TMRM | `Allocator` / `HealthChecker` | Go |
| PLG SDK | `Plugin` trait / `PluginServer` 类 | Go / Rust / Python / Java |

## 当前已交付（S0 + S0.5）

- `contracts/`：4 个 proto + buf 配置 + 多语言生成
- `services/tcm/`：CaseStore 接口 + inmem Adapter + 3 个生命周期状态机
- `services/exf/`：workspace 骨架 + StateMachine trait + InMemoryScheduler / InMemoryBroker
- `services/trm/`：Analyzer 接口 + 3 个内置分析器 stub
- `services/tmrm/`：Allocator / HealthChecker 接口 + 默认探针
- `sdk/plugin-sdk-{go,rust,python}/`：PluginServer trait + 骨架
- `docs/architecture-v3-modules.md`：整体架构 + 各模块接口定义

## 不再维护

`src/aitest/` 的 Python 原型代码仅作为"语义参考"保留。新实现必须从 `services/` 起。
