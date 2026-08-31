# 新架构 v3 — 模块接口与设计总览

> 版本：v0.1 · 日期：2026-08-31
> 范围：5 大业务模块 + 3 类 SDK + 2 个客户端 + 横切关注点
> 关联：[`architecture.md`](ai-test/architecture.md) · [`contracts/`](../contracts/) · [`development-plan.md`](ai-test/development-plan.md)

本文件定义每个新模块的 **公开接口契约**（traits / interfaces）与 **设计意图**。
所有实现细节必须先在这里签字，然后再写代码。

---

## 0. 设计原则（适用于所有模块）

1. **只依赖 `contracts/` 的 Protobuf**，禁止共享进程内对象或私有协议
2. **接口先行**：先定义 trait/interface，再写实现；新模块对外只暴露 trait/interface
3. **错误统一**：每个模块的 `Error` 类型实现 `std::error::Error` / `error` / `Exception`
4. **可观测默认开启**：每个模块的入口方法必须接 `tracer` / `metrics` 注入
5. **可取消**：每个长操作接收 `ctx context.Context` / `CancellationToken`，禁止 hard-stop
6. **可重试**：调用外部依赖时声明 retry 策略，禁止在调用方偷偷重试
7. **测试即合同**：每个接口必须同时存在 `MockXxx` 实现，作为行为参考

---

## 1. 模块布局

```
oneTear/
├── contracts/                 # Protobuf IDL（已落地）
├── services/                  # 业务服务
│   ├── tcm/                   # TCM  用例管理（Go）
│   ├── exf/                   # EXF  执行框架（Rust workspace）
│   ├── trm/                   # TRM  测试报告（Go + Rust 摄取）
│   └── tmrm/                  # TMRM 机器资源（Go）
├── sdk/                       # 插件 SDK（多语言）
│   ├── plugin-sdk-go/
│   ├── plugin-sdk-rust/
│   ├── plugin-sdk-python/
│   └── plugin-sdk-java/
├── clients/                   # 客户端
│   ├── cli/                   # Python CLI
│   └── mcp_server/            # MCP Server（暴露给 AI Agent）
├── infra/                     # 部署 / 监控 / CI（后续 Sprint）
└── docs/                      # 设计文档
```

---

## 2. 模块职责矩阵

| 模块 | 语言 | 核心职责 | 不做的事 |
| --- | --- | --- | --- |
| **TCM** | Go | 用例 CRUD / 搜索 / 版本 / lifecycle / 矩阵展开 / MCP 暴露 | 不执行用例、不收结果 |
| **EXF** | Rust | 调度 Plan → DAG → Task；Worker Pool；状态机；结果回写 | 不存用例、不查业务数据 |
| **TRM** | Go + Rust | 摄取 Result 事件；冷热分层存储；Flaky / Baseline / Trend 分析；查询 API | 不调度、不直接调插件 |
| **TMRM** | Go | 机器注册 / 心跳 / 健康探针；分配 / 释放 / Quota | 不执行用例、不调度 |
| **PLG SDK** | 多语言 | 提供 `PluginServer` 基类；自动实现 Hello/Health/Invoke/Assert 路由 | 不实现具体命令逻辑 |

---

## 3. TCM 接口

**语言**：Go 1.22+
**入口**：`services/tcm/cmd/server/main.go` —— `PlanService`（gRPC）+ HTTP Gateway
**数据**：PostgreSQL（JSONB + tsvector + pgvector）
**关键约束**：所有外部调用必须带 `request_id` 与 `traceparent`

```go
// domain/case.go — 领域类型
type Case struct {
    ContentHash string
    Semver      string
    ID          string
    Tags        []string
    Lifecycle   Lifecycle
    Params      json.RawMessage
    Steps       []Step
    // ...
}

type Lifecycle int
const (
    Draft Lifecycle = iota
    Active
    Deprecated
    Retired
)

// domain/store.go — 存储接口（4 类 Adapter：PG / InMemory / Cas / Search）
type CaseStore interface {
    Get(ctx, contentHash string) (*Case, error)
    GetByVersion(ctx, id, semver string) (*Case, error)
    Put(ctx, c *Case) error                          // 写入或更新（content_hash 决定去重）
    List(ctx, q CaseQuery) (*CasePage, error)
    Transition(ctx, id, semver, from, to Lifecycle) error
    // 流式读取用于 EXF Plan 展开
    Stream(ctx, q CaseQuery) (<-chan *Case, <-chan error)
}

type CaseQuery struct {
    Tags       TagQuery        // all_of / any_of / none_of
    Lifecycle  []Lifecycle
    SemverRange string
    Search     string          // 全文检索
    Limit      int
    Cursor     string
}

// api/grpc.go — gRPC 入口（实现 contracts.proto 中定义的服务）
type PlanServiceServer struct {
    pb.UnimplementedPlanServiceServer
    store CaseStore
    pub   EventPublisher
}
```

---

## 4. EXF 接口

**语言**：Rust 1.78+ (edition 2024)
**入口**：`crates/server/src/main.rs` —— `PlanService`（gRPC）+ Broker 订阅
**运行时**：Tokio
**关键约束**：调度热路径无 GC、零拷贝、批处理

```rust
// crates/core/src/lib.rs — 核心类型
pub struct Plan { /* 来自 contracts.proto */ }
pub struct Task {
    pub instance_id: String,        // = plan_id × case_id × content_hash × params_hash
    pub state: TaskState,
    pub attempts: u32,
}

#[derive(Debug, Clone, Copy)]
pub enum TaskState {
    Queued, Assigned, Running, Succeeded,
    Failed, Retrying, Timeout, Canceled, Blocked, Error,
}

// crates/core/src/state_machine.rs — 状态机合法转移表
pub trait StateMachine {
    fn can_transition(from: TaskState, to: TaskState) -> bool;
    fn transition(&mut self, to: TaskState) -> Result<(), IllegalTransition>;
}

// crates/scheduler/src/lib.rs — 调度器（Plan → DAG → Task）
#[async_trait]
pub trait Scheduler: Send + Sync {
    /// 展开 Plan 为 DAG，并把 Task 提交到 Broker
    async fn submit(&self, plan: Plan) -> Result<PlanHandle, SchedulerError>;
    /// 取消整个 Plan
    async fn cancel(&self, plan_id: &str, reason: &str, force: bool) -> Result<CancelSummary, SchedulerError>;
    /// 查询 Plan 状态
    async fn status(&self, plan_id: &str) -> Result<PlanStatus, SchedulerError>;
}

// crates/worker/src/lib.rs — Worker Pool
#[async_trait]
pub trait Worker: Send + Sync {
    async fn run(self: Arc<Self>, broker: Arc<dyn Broker>) -> WorkerHandle;
    async fn shutdown(&self, grace: Duration) -> Result<(), WorkerError>;
}

// crates/broker/src/lib.rs — Broker（v0.8 用 NATS JetStream）
#[async_trait]
pub trait Broker: Send + Sync {
    async fn publish(&self, topic: &str, msg: Bytes) -> Result<(), BrokerError>;
    async fn subscribe(&self, topic: &str) -> Result<Subscription, BrokerError>;
    async fn ack(&self, msg: MessageId) -> Result<(), BrokerError>;
    async fn nack(&self, msg: MessageId, reason: &str) -> Result<(), BrokerError>;
}
```

---

## 5. TRM 接口

**语言**：Go (API) + Rust (ingest)
**入口**：`cmd/server/main.go`（Go API）+ `cmd/ingest-rs`（Rust 摄取）
**数据**：ClickHouse（聚合）+ PostgreSQL（元数据）+ S3（replays）

```go
// internal/analyzer/analyzer.go — Analyzer 协议
type Analyzer interface {
    Name() string
    Analyze(ctx context.Context, store ResultStore, q Query) (Result, error)
}

type ResultStore interface {
    // 抽象 EXF + 历史数据的统一视图
    ListResults(ctx, q ResultQuery) ([]*resultv1.Result, string, error)
    StreamResults(ctx, q ResultQuery) (<-chan *resultv1.ResultEvent, <-chan error)
    Summary(ctx, planID string) (*Summary, error)
}

// 内置分析器
type FlakyDetector struct{}      // 滑动窗口 N=50，失败率 ∈ [5%,50%]
type BaselineComparator struct{} // 两 run 之间的 7 类 diff
type TrendAnalyzer struct{}      // 时间线 + p50/p95 + 长尾告警

// internal/api/grpc.go — gRPC 服务（实现 contracts.proto 中 ResultService）
type ResultServiceServer struct {
    pb.UnimplementedResultServiceServer
    store  ResultStore
    analyzers *AnalyzerRegistry
}
```

---

## 6. TMRM 接口

**语言**：Go 1.22+
**入口**：`cmd/server/main.go` —— gRPC
**数据**：PostgreSQL（machines / pools / sessions / health_records）

```go
// internal/domain/machine.go
type Machine struct {
    ID       string
    Pool     string
    Type     MachineType  // host / browser / mobile / desktop / sandbox
    Status   MachineStatus // available / allocated / drained / retired
    Labels   map[string]string
    Region   string
    LastHeartbeat time.Time
}

// internal/domain/allocator.go
type QuotaPolicy struct {
    Team string
    Pool string
    MaxSessions int
}

type Allocator interface {
    Acquire(ctx, req AcquireRequest) (*Session, error)
    Release(ctx, sessionID string) error
    Heartbeat(ctx, machineID string) error
    HealthCheck(ctx, machineID string) (*HealthRecord, error)
    Sweep(ctx) ([]string, error) // 返回过期机器
}

// internal/api/grpc.go — RPC（与 contracts 同步定义在 TMRM.proto v2）
type AllocatorServiceServer struct {
    alloc Allocator
    store *FarmStore
}
```

---

## 7. PLG SDK 接口

**多语言**：Go / Rust / Python / Java
**目标**：插件作者只需 1. 注册命令处理器；2. 实现业务逻辑；3. 调用 `serve()`。SDK 自动接管 gRPC、Health、Trace、Cancel。

### Go SDK

```go
// pkg/server/server.go
type Server interface {
    RegisterCommand(name string, h CommandHandler)
    RegisterAssertor(name string, h AssertorHandler)
    Serve(ctx context.Context, addr string) error
}

type CommandHandler func(ctx context.Context, args json.RawMessage) (json.RawMessage, error)
type AssertorHandler func(ctx context.Context, value, spec json.RawMessage) (AssertResult, error)

type AssertResult struct {
    Passed      bool
    Message     string
    Diagnostics map[string]any
}
```

### Rust SDK

```rust
pub trait Plugin {
    fn manifest() -> Manifest;
    async fn invoke(&self, cmd: &str, args: Value, ctx: &InvokeContext) -> Result<Value, InvokeError>;
    async fn assert(&self, assertor: &str, value: Value, spec: Value, ctx: &AssertContext) -> Result<AssertResult, AssertError>;
}

pub async fn serve<P: Plugin>(plugin: P) -> Result<(), ServeError>;
```

### Python SDK

```python
class PluginServer:
    def command(self, name: str):
        """装饰器：注册命令处理器"""
    def assertor(self, name: str):
        """装饰器：注册断言器"""
    def serve(self, addr: str = "0.0.0.0:50051"):
        """启动 gRPC server"""
```

---

## 8. 客户端接口

### CLI（Python）

```
aitest plan submit  --suite cases/ --concurrency 100
aitest case list    --tag smoke --json
aitest result get   <result-id>
aitest farm ls      --json
aitest plugin ls
```

CLI 永远只调用 gRPC / HTTP 接口，**不直连数据库**。

### MCP Server（Python）

```python
# 暴露给 AI Agent 的工具集
@mcp.tool()
async def tcm_search_cases(tags: list[str]) -> list[Case]:
    """按 tag 搜索用例（用于 RAG）"""

@mcp.tool()
async def exf_submit_plan(case_ids: list[str]) -> PlanHandle:
    """提交一份 plan，返回 plan_id"""

@mcp.tool()
async def trm_get_flaky(window: int = 50) -> list[FlakyCase]:
    """返回 flaky 用例清单"""
```

---

## 9. 横切关注点（每个模块必须集成）

### 9.1 可观测

| 维度 | 工具 | 每个模块必须 |
| --- | --- | --- |
| Metrics | Prometheus / OpenTelemetry | 暴露 `*_requests_total` / `*_duration_seconds` / `*_inflight` |
| Logs | 结构化 JSON | 用 `tracing` / `zap` / `slog`，含 `trace_id` / `span_id` |
| Traces | OpenTelemetry → Tempo | 入口方法 + 外部调用 + DB 查询 都打 span |
| Health | gRPC Health v1 | `/healthz` (liveness) + `/readyz` (readiness) |

### 9.2 安全

- 服务间 mTLS（v1.0 落地）
- 镜像 cosign 签名（v1.0 落地）
- 插件 sandbox（rlimit + seccomp，v1.0 落地）

### 9.3 韧性

- 每个外部调用带超时（默认 5s）
- 重试策略显式声明（不重试 / 指数退避 / 永久重试）
- 熔断器（resilience4j / tower）

---

## 10. 数据流（端到端）

```
User / CI
   │
   ▼
[CLI / MCP] ──HTTP/gRPC──▶ [TCM]──查询──▶ (PG + cas + pgvector)
   │                              │
   │  PlanService.Submit          │ ResolvedCaseRef[]
   ▼                              │
[EXF Master] ◀───────────────────┘
   │
   │ 展开 DAG
   ▼
[Broker: NATS JetStream] ── push ──▶ [Worker Pool]
   │                                       │
   │                                       │ gRPC PluginService.Invoke
   │                                       ▼
   │                              [Plugin: db_sqlite / web_chrome / llm_gateway]
   │                                       │
   │  ResultEvent 流                        │ 结果
   ◀──────────────────────────────────────┘
   │
   ▼
[TRM Rust ingest] ──batch──▶ [ClickHouse] + [PG 元数据] + [S3 artifacts]
   │
   │ 查询
   ▼
[TRM Go API] ◀── HTTP / gRPC ── [CLI / MCP / Web UI]
                              ▲
                              │
[TMRM] ◀──心跳/分配── [EXF Worker]
```

---

## 11. Sprint 切分与本文件的关系

| Sprint | 落地此文件哪几章 |
| --- | --- |
| S0 (协议) | `contracts/` + `contracts.proto` 4 个文件（已完成） |
| S1 (最小端到端) | §3 TCM 接口（最小子集）+ §4 EXF 接口（核心类型）+ §7 PLG Go SDK + db_sqlite 插件 |
| S2 (数据层硬化) | §3 TCM PG Schema + §9.1 OTel 接入模板 |
| S3 (分布式 EXF) | §4 EXF NATS 实现 + §7 PLG Rust SDK |
| S4 (TRM 接入) | §5 TRM Go API + Rust 摄取 + §9 可观测 |
| S5 (PLG 完善) | §7 全语言 SDK + Sidecar + Sandbox |
| S6 (TMRM + 调度) | §6 TMRM 接口 + EXF 集成 |
| S7 (CI/MCP/Web) | §8 CLI + MCP Server |
| S8 (GA) | §9 安全 / 韧性 / 性能基线 |

---

## 12. 变更规则

- 修改本文件必须先开 PR，由至少 1 个架构师 + 1 个模块 owner 签字
- 任何在本文件中签字的 trait / interface，**签名变更** 必须走 breaking change 流程（提 v2）
- 本文件是 v0.1，下一次 review 在 S1 结束时
