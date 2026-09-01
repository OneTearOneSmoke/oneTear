# 项目进度日志

> 本文件记录 v3 新架构自启动以来的 Sprint 进展、关键决策与下一步计划。
> 完整路线图：[`ai-test/development-plan.md`](ai-test/development-plan.md)
> 整体架构：[`architecture-v3-modules.md`](architecture-v3-modules.md)

---

## 当前快照（2026-09-01）

| 项 | 值 |
| --- | --- |
| 当前 Sprint | **S1 启动中**（接口先行 / 实现延后） |
| 分支 | `new_frame` |
| 最近提交 | `2260263` |
| Python 原型 | 保留为参考，**不再维护** |
| 整体评估 | 设计 v3 完整 / 接口签字 40% / 业务实现 ≈5% / **Sprint 1 重启** |
| 新优先级 | **EXF › PLG SDK › TCM › TRM › TMRM › CLI/MCP**（详见 D-006） |
| 4 原则 | 海量用例 / 高并发 / 可扩展 / 可观测 |

### 完成度快照（用户视角）

| 模块 | 接口 | 业务实现 | 真实 gRPC | 评估 |
| --- | --- | --- | --- | --- |
| **EXF** | ✅ 4 trait | 0%（InMemoryBroker/Scheduler 仅桩） | ❌ | P0-1 |
| **PLG SDK** | ✅ 3 语言 | 0%（Serve 全是 stub） | ❌ | P0-2 |
| **TCM** | ✅ CaseStore | 10%（inmem CRUD） | ❌ | P0-3 |
| **TRM** | ✅ Analyzer | 0%（3 个 stub） | ❌ | P0-4 |
| **TMRM** | ✅ Allocator | 5%（心跳检查） | ❌ | P1 |
| **SDK Python** | ✅ 装饰器 API | 100%（本地 6/6 pytest） | ❌ | 唯一本地绿 |
| CLI / MCP | ❌ | 0% | — | P2 |
| Contracts | ✅ 4 proto | buf.gen 已配置 | — | 基础完成 |

---

## Sprint 0 — Protobuf IDL（✅ 完成）

**提交**：`fad3085`

### 交付

- `contracts/proto/aitest/case/v1/case.proto`（229 行）
- `contracts/proto/aitest/plan/v1/plan.proto`（296 行）
- `contracts/proto/aitest/result/v1/result.proto`（399 行）
- `contracts/proto/aitest/plugin/v1/plugin.proto`（344 行）
- `contracts/{buf.yaml, buf.gen.yaml, Makefile, README.md}`
- 4 个 service 定义：`PlanService` / `ResultService` / `PluginService`

### 关键决策

1. **包路径与目录布局对齐**：`aitest.<mod>.v1` ↔ `proto/aitest/<mod>/v1/`，标准 buf 风格
2. **状态值用 SCREAMING_SNAKE_CASE**：与 Rust 强类型对齐
3. **跨包共用类型独立定义**：`Status` / `ResourceUsage` 在 result.proto 与 plugin.proto 中各定义一份，避免循环依赖
4. **生命周期 4 态**：`DRAFT` / `ACTIVE` / `DEPRECATED` / `RETIRED`
5. **内容寻址 + semver**：同一 case 多个版本共存
6. **RPC 字段编号按语义分桶**：标识 / 分类 / 主体 / 关系 / 行为 / 资源 / 上下文 / 时间 / 元数据 / 资产；预留 1000+

### 已修复

- `result.proto ListResultsRequest.tag_filter` / `started_after_ms` 都曾用 =4，已改为 =8

---

## Sprint 0.5 — 模块骨架 + 接口签字（✅ 完成）

**提交**：`5945ac5`

### 交付

```
services/
├── tcm/    Go   CaseStore + Lifecycle + inmem Adapter
├── exf/    Rust workspace (core/scheduler/worker/broker/server)
├── trm/    Go   Analyzer + 3 个内置分析器 stub
└── tmrm/   Go   Allocator + HealthChecker

sdk/
├── plugin-sdk-go/        BaseServer + CommandHandler
├── plugin-sdk-rust/      Plugin trait
└── plugin-sdk-python/    PluginServer + 装饰器

docs/architecture-v3-modules.md     418 行  整体架构 + 接口契约

clients/                            Sprint 7 占位
```

### 接口签字（已签字 / 待实现）

| 接口 | 文件 | 状态 |
| --- | --- | --- |
| `domain.CaseStore` | `services/tcm/internal/domain/store.go` | ✅ 签字 |
| `domain.Lifecycle` + `CanTransition` | 同上 | ✅ |
| `StateMachine` trait | `services/exf/crates/core/src/lib.rs` | ✅ |
| `Scheduler` trait | `services/exf/crates/scheduler/src/lib.rs` | ✅ |
| `Worker` trait | `services/exf/crates/worker/src/lib.rs` | ✅ |
| `Broker` trait | `services/exf/crates/broker/src/lib.rs` | ✅ |
| `analyzer.Analyzer` | `services/trm/internal/analyzer/analyzer.go` | ✅ |
| `domain.Allocator` + `HealthChecker` | `services/tmrm/internal/domain/allocator.go` | ✅ |
| `sdk.BaseServer` / `Plugin` trait / `PluginServer` | sdk/* | ✅ |

### 验证

- ✅ Python SDK 烟雾测试（命令 + 断言器）
- ✅ Rust 内置单元测试：状态机 4 个 + scheduler 2 个 + broker 1 个
- ⏸ Go 代码：手写语法检查通过，本环境无 `go` 工具链
- ⏸ Rust 全 workspace `cargo check`：本环境 rustup toolchain 未装

### 待办（无功能代码层面的技术债）

- TCM `core/` 兼容 shim 仍指向 Python 原型，新代码不要再 import
- Go 各模块的 `gRPC server` 当前是 stub（结构体已就位，handler 等 Sprint 1）
- Rust 整个 workspace 还未连接 `aitest-contracts` 生成的 proto 代码（S1 接入）
- PLG SDK 的 gRPC server 实际代码未写（Sprint 5）

---

## 关键决策记录（v3 阶段）

### D-001 架构重启，原型仅作参考

- **背景**：原 Python 单进程原型仅 148 单测通过，已达 v0.5-η，无法承载"海量/高并发/可扩展/可观测"目标
- **决定**：`src/aitest/` Python 代码仅保留为"语义参考"，新实现全部从 `services/` 起步
- **替代方案**：❌ 在 Python 原型上扩展；❌ 整体迁移到 Rust + Go 而保留原领域模型

### D-002 协议先行，4 个 proto 覆盖所有跨模块契约

- **背景**：原 5 个模块各自定义私有类型，集成成本高
- **决定**：先建 `contracts/`，所有模块**只允许**通过 protobuf 通信
- **受益**：模块边界清晰；多语言 SDK 接入成本为 0；breaking change 由 buf 自动检测

### D-003 关键路径优先级：EXF > TRM > TCM > TMRM

- **背景**：原计划按模块均匀推进
- **决定**：
  - **EXF** 是单一关键路径瓶颈（性能上限 + 阻塞所有插件执行），必须最先建
  - **TRM** 提到第二梯队（可观测的落点都在 TRM）
  - **TCM** 不必先做完（最小集即可跑）
  - **TMRM** 放最后（EXF 内置本地 worker 列表能跑前无真实接入对象）
- **替代方案**：❌ 先做完所有 TCM 再做 EXF

### D-004 纵向切片而非横向填满

- **背景**：原 Sprint 按模块逐个填满
- **决定**：每个 Sprint 产出**端到端可演示**的薄切片
- **Sprint 1 目标**：1 个用例从 TCM（inmem）→ EXF（inmem broker）→ plugin（db_sqlite）→ TRM（内存 sink）跑通

### D-005 接口先行 / 实现延后

- **背景**：v3 起点是"重画架构"
- **决定**：Sprint 0.5 只签字 trait/interface，不写实现；实现按 Sprint 1+ 逐步填充
- **好处**：实现开始前可被多 reviewer 同时审视设计

### D-006 基于 4 原则的模块重新优先级（2026-09-01）

- **背景**：原 D-003 优先级 EXF > TRM > TCM > TMRM 基于"Python 原型尚可跑通"假设；v3 彻底重画后该假设不成立
- **设计原则**（v3 唯一指引）：
  1. **海量用例** —— TCM 是数据基础，EXF 必须能流式拉取不下发全量
  2. **高并发** —— EXF 是 hot path bottleneck（tokio / 零拷贝 / 无锁）
  3. **可扩展** —— PLG SDK 与 EXF 同批落地（gRPC + 多语言 SDK + Manifest）
  4. **可观测** —— TRM 是观测中心；OTel/Metrics/Trace 必须在每个模块 S1 起就默认开启
- **决定**（新优先级）：

| # | 模块 | 原则侧重 | Sprint |
| --- | --- | --- | --- |
| **P0-1** | EXF（执行引擎） | 高并发、可扩展 | **S1** |
| **P0-2** | PLG SDK（插件系统） | 可扩展 | **S1**（与 EXF 并行） |
| **P0-3** | TCM（用例管理） | 海量用例 | **S1 最小 + S2 硬化** |
| **P0-4** | TRM（报告管理） | 可观测 | **S1 接口 + S4 落地** |
| P1 | TMRM（机器资源） | 高并发（分布式） | S6 |
| P2 | CLI / MCP / Web | 用户面 | S7 |
| P3 | 安全 / 韧性 / GA | GA | S8 |

- **与旧优先级对比**：
  - 旧 EXF #1 → 新 EXF #1（不变）
  - 旧 TRM #2 → 新 **PLG SDK #2**（"可扩展"原则要求 PLG 与 EXF 同批，旧优先级推到 S5 太晚）
  - 旧 TCM #3 → 新 **TCM #3**（"海量用例"原则让 TCM 进 P0；旧优先级 S2 太晚会让 EXF/PLG 早期只能 mock）
  - 旧 TMRM #4 → 新 **TRM #4**（"可观测"原则要求 TRM 与三大模块同批出埋点接口）
- **关键动作**：可观测埋点（OTel/Metrics/Trace）从 S4 提前到 **S1 默认开启**——每个模块入口方法必须接 tracer/metrics 注入

### D-007 "彻底重新实现"边界（2026-09-01）

- **背景**：原 Python 原型（`src/aitest/`）字段语义 / 插件命令可参考，但实现层（线程池、内存存储、同进程 import）全部不可沿用
- **决定**：
  - ✅ **可借鉴**：字段命名（case.id / step.plugin+action）、插件命令清单（如 db_sqlite 的 5 个命令）、Flaky 滑动窗口算法思路
  - ❌ **禁止沿用**：ThreadPoolExecutor、YAML 文件存储、同进程 import、内存分配器、即时聚合
  - **新实现起算点**：`services/`（业务）+ `sdk/`（插件 SDK）+ `plugins/`（内置插件）
- **后续动作**：
  - 把 `src/aitest/` 移入 `docs/archive/v0-python/`（Sprint 1 末尾统一迁移）
  - `docs/ai-test/*.md` 保留为"v0 设计参考"，**不**作为 v3 实现依据

---

## Sprint 1 — 最小真实闭环（🚧 启动中）

> **目标**：EXF + PLG SDK + TCM + TRM 四模块**接口先行**，实现延后；以最小可端到端冒烟（1 case 走通）为验收。

### 范围（接口优先）

**EXF（Rust）**
- `core/instance_id.rs`：实例 ID 稳定哈希算法
- `core/dag.rs`：DAG 展开 trait（前置依赖）
- `scheduler/dag.rs`：Plan → DAG → Task 展开
- `worker/pool.rs`：WorkerPool trait（并发数 / 背压）
- `server/grpc.rs`：tonic PlanServiceServer method 签名

**PLG SDK（多语言）**
- `plugin-sdk-go/server/grpc.go`：grpc-go PluginService 实现（Hello/Manifest/Invoke/Assert）
- `plugin-sdk-rust/src/grpc.rs`：tonic PluginServiceServer 实现
- `plugin-sdk-python/aitest_sdk/grpc_server.py`：grpcio PluginServiceServicer 实现

**TCM（Go）**
- `api/grpc.go`：从桩升级为 5 个 method 签名（Submit/Get/Cancel/List/Stream）
- `store/inmem/inmem.go`：补 `Stream`/`Transition` 当前返回 nil 的实现
- `domain/store.go`：增补 `BatchGet` 接口（EXF 展开用例用）

**TRM（Go）**
- `store/store.go`：ResultStore interface（Write / Read / Stream）
- `analyzer/analyzer.go`：3 个 Analyzer 保持 stub，但补 Method 签名文档
- `api/grpc.go`：从桩升级为 ResultService method 签名
- `observability/metrics.go`：Prometheus 注册接口

**demo 插件**
- `plugins/db_sqlite/`（Go）：5 命令 + 3 断言器，参考 `src/aitest/plugins/db_sqlite.py` 的语义

### 不在 S1 范围

- ❌ 真实 PG / ClickHouse / NATS 接入（推到 S2-S4）
- ❌ mTLS / Vault / cosign（推到 S8）
- ❌ 插件沙箱（推到 S5）
- ❌ MCP / Web（推到 S7）

---

## 路线图（接下来）

| Sprint | 主题 | 关键产出 | 依赖 |
| --- | --- | --- | --- |
| **S1**（P0 全开）| 最小真实闭环 | EXF 接口 + PLG SDK 真实 gRPC（3 端） + TCM inmem 流式读 + TRM ResultStore 接口 + db_sqlite demo + smoke E2E | S0, S0.5 |
| S2 | TCM 硬化 | PG Schema（JSONB + tsvector + pgvector）+ content_hash 索引 + 分页 + cursor | S1 |
| S3 | EXF 分布式 | NATS JetStream broker + 跨节点 Worker + 任务幂等 + 心跳 | S2 |
| S4 | TRM 落地 | Rust 摄取（ClickHouse）+ Go API + Flaky/Baseline/Trend 真实算法 | S3 |
| S5 | PLG 完善 | Java SDK + 真 sandbox（rlimit+seccomp）+ cosign + 5 官方插件 | S4 |
| S6 | TMRM 接入 | PG + 多策略 Allocator + EXF 集成 + Quota | S5 |
| S7 | 用户面 | Python CLI + MCP Server + Web UI + GitHub Actions | S6 |
| S8 | v1.0 GA | mTLS + Vault + OPA + 性能基线 + 灾备演练 | S7 |

---

## 待决策项（队列）

- [ ] EXF broker：S3 用 NATS JetStream 还是直接 Redis Streams？
- [ ] TRM 冷热分层策略：S3 多长时间下放？ClickHouse TTL 多少？
- [ ] TMRM Quota 维度：仅 team×pool，还是加上 region / provider？
- [ ] 插件 sandbox：rlimit + seccomp 是否在 v1.0 之前够用？v2 引入 gVisor？
- [ ] MCP Server：是否同时暴露 write 工具（plan submit / case update）？还是只暴露 read？
- [ ] docs/ai-test/ 旧设计文档：是保留为历史快照，还是迁移进 docs/archive/？

---

## 文件清单（本次 Sprint 已推送）

```
contracts/                        4 proto + buf 配置 + Makefile + README
docs/architecture-v3-modules.md   整体架构 + 接口契约
docs/PROGRESS.md                  本文件

services/
├── tcm/                          Go 骨架（8 个文件）
├── exf/                          Rust workspace（10 个文件）
├── trm/                          Go 骨架（6 个文件）
└── tmrm/                         Go 骨架（5 个文件）

sdk/
├── plugin-sdk-go/                3 文件
├── plugin-sdk-rust/              2 文件
└── plugin-sdk-python/            2 文件

clients/                          Sprint 7 占位
README.md                         顶层 README 重写
```

**总计**：约 1900 行手写代码 + 文档 / 0 行实现。

---

## Review Checklist（下次 review 时检查）

- [ ] TCM `CaseStore.Stream` 返回 chan 的设计是否符合 EXF 大规模拉取需求？
- [ ] EXF `TaskState` 是否覆盖 `Blocked`（前置依赖未就绪）的所有场景？
- [ ] TRM `Analyzer` 接口签名是否方便后期加 SQL 后端？
- [ ] TMRM `HealthChecker` 是否需要 `Check(ctx, *Machine) → *HealthRecord` 而不是 Probe 拿 Machine 引用？
- [ ] PLG SDK 的 `CommandHandler` 签名是否要支持 streaming args / streaming output？
- [ ] 文档 `architecture-v3-modules.md` 的"接口速查"是否覆盖到了所有 grpc.go 文件？
