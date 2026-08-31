# aitest-contracts

> **跨模块 / 跨语言的协议契约** —— AI 时代测试平台的"宪法层"。
>
> 这是新架构（Sprint 0）的第一份交付。所有服务（EXF / TCM / TRM / TMRM / Plugin SDK / CLI / MCP / CI）
> 都必须只依赖本目录中的 Protobuf，**不允许共享进程内对象或私有协议**。

## 目录结构

```
contracts/
├── buf.yaml              # buf module 配置（lint + breaking 规则）
├── buf.gen.yaml          # buf generate 插件清单（多语言生成）
├── Makefile              # 常用命令入口
├── proto/
│   ├── case/v1/case.proto      # TCM 用例数据契约
│   ├── plan/v1/plan.proto      # EXF 执行计划 + PlanService RPC
│   ├── result/v1/result.proto  # EXF/TRM 结果 + ResultService RPC + 流式事件
│   └── plugin/v1/plugin.proto  # PLG 插件协议 + PluginService RPC
└── gen/                        # 自动生成的多语言代码（不提交）
```

## 四个核心契约的职责

| Proto 包 | 拥有者 | 用途 | 谁消费 |
| --- | --- | --- | --- |
| `aitest.case.v1` | TCM | 用例数据模型：content-hash + semver + lifecycle + 矩阵参数 + 步骤 | EXF、TCM 自身、MCP、CLI |
| `aitest.plan.v1` | EXF | 执行计划：选择器、调度策略、资源需求、触发上下文 | CI、CLI、MCP、Webhook |
| `aitest.result.v1` | TRM | 执行结果：状态、步骤详情、失败分类、产物引用、流式事件 | TRM、EXF、Web UI、告警 |
| `aitest.plugin.v1` | PLG | 插件协议：Manifest + Hello/Invoke/Assert/Cancel/Health/Stream | EXF、各语言 SDK、第三方插件 |

## 设计原则

### 1. 内容寻址 + 不可变快照

- `Case.content_hash` = SHA-256 前 16 hex，从规范化字段计算，剔除 path/timestamps
- 同一语义内容在不同路径 / 不同时刻写入，hash 必须相同
- 一份 Case 写入后**不可变**；修改即新 hash + 新 semver

### 2. 状态值大小写

为对齐 Rust 强类型与多语言互操作，统一使用 `SCREAMING_SNAKE_CASE`：

- `LIFECYCLE_DRAFT` 而非 `draft`
- `STATUS_SUCCESS` 而非 `success`

零值（未指定）一律为 `*_UNSPECIFIED` —— 服务端应显式拒绝未指定值。

### 3. 跨包复用

为避免循环依赖与版本耦合：

- `Status` 在 `result.v1` 与 `plugin.v1` 中**独立定义**（同语义）
- `ResourceUsage` 同上
- 后续如需统一，由 `aitest.common.v1` 包承载（v2 起再加）

### 4. 时间与字段编号

- 一律使用 `google.protobuf.Timestamp` 而非 `int64`
- `oneof` 用于语义互斥字段（selector / payload）
- 字段编号按"语义分桶"分配：`1-9` 标识、`10-19` 分类、`20-29` 主体、`30-39` 关系、`40-49` 行为、`50-59` 资源、`60-69` 上下文、`70-79` 时间、`80-89` 元数据、`90-99` 资产
- 预留 `1000+` 给后续扩展

### 5. 服务接口

每个 service 必须有：

- 健康检查（GRPC health）—— 由 [grpc-health-probe](https://github.com/grpc-ecosystem/grpc-health-probe) 标准
- 优雅停机
- 幂等键（防止重提）

## 版本管理

- Proto 包名 = `aitest.<module>.v1`
- 引入 v2 时**新建目录**（`aitest.case.v2`），v1 保留至少一个大版本周期
- 字段 tag 编号一旦分配**不可重用**
- 每次合并 PR 自动跑 `buf breaking`，禁止 wire-incompatible 改动

## 本地开发

```bash
# 1. 安装 buf
make install

# 2. 格式化 + lint + generate
make all

# 3. CI 校验（lint + breaking 对比 main）
make verify
```

## 多语言生成

| 语言 | 插件 | 落点 |
| --- | --- | --- |
| Go | `protocolbuffers/go` + `grpc/go` | `gen/go/aitest/<mod>/v1/` |
| Rust | `neoeinsteinpro/korrosion` (prost + tonic) | `gen/rust/aitest-contracts/src/pb/` |
| Python | `protocolbuffers/python` + `betterproto` | `gen/python/aitest/<mod>/v1/` |
| Java | `protocolbuffers/java` + `grpc/java` | `gen/java/com/aitest/contracts/<mod>/v1/` |
| TypeScript | `ts-proto` | `gen/ts/aitest/<mod>/v1/` |

> 生成产物不提交进仓库。服务方在 `Dockerfile` / `Cargo.toml` / `pyproject.toml` 中通过 CI 制品或 vendor 方式消费。

## 验收门槛（Sprint 0）

- [x] 4 个 proto 文件落地，每个含至少 1 service + 关键 message
- [x] `buf lint` 通过 STANDARD 规则
- [x] `buf breaking` 配置完成（CI 用）
- [x] `buf generate` 至少产出 Go 代码且能 import
- [x] README 写清每个包的职责与跨包复用规则

## 后续 Sprint 衔接

| Sprint | 消费本契约的服务 |
| --- | --- |
| S1（最小端到端） | EXF (Rust)、TCM (Go)、db_sqlite plugin (Python) |
| S2（数据层硬化） | TCM PG Schema |
| S3（分布式 EXF） | EXF + NATS、TRM 摄取 |
| S4（TRM 接入） | TRM API、ClickHouse 写入 |
| S5（PLG 完善） | Go/Rust/Python/Java SDK |
| S6（TMRM + 调度） | TMRM (Go) |
| S7（CI/MCP/Web） | MCP Server、Web UI |

## 变更流程

1. 创建分支：`git checkout -b feat/<scope>/<change>`
2. 修改 `proto/`，本地 `make format lint generate`
3. 提 PR；CI 自动跑 `buf breaking` 对比 main
4. 合并前必须由模块 owner（EXF / TCM / TRM / TMRM / PLG lead）+ 一个独立 reviewer 签字
5. wire-incompatible 改动 → 必须同步升级所有 consumer 的 major 版本
