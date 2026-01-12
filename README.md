# oneTear

一个可观察的自动化框架以为了达到：一杯茶，一包烟，一个测试跑一天。

| 维度              | 状态 |
| --------------- | -- |
| pytest          | ✅  |
| DSL + DAG       | ✅  |
| 并行调度            | ✅  |
| Retry / Timeout | ✅  |
| Node Selector   | ✅  |
| Cache           | ✅  |
| Hooks           | ✅  |
| Allure          | ✅  |
| Trace           | ✅  |
| Metrics         | ✅  |




与repmgr和postgresql的解耦，设计成一套通用的自动化测试框架，整体架构分为四部分：（整体框架组件pytest+chaos+tempo+promethus+allure）

- 用例模块（用例采用原子命令组合，并且有预期结果，有before，有after，有on_fail）--》先定义原子命令，再由原子命令组合为测试用例
- 故障模块（故障也是采用原子命令组合，每一种故障时一个命令）--》先定义原子故障，再由命令和故障组合为测试用例
- trace+metric
- 报告查看跟踪（allure）

- 命令（Command）

- 故障（Chaos）

- 组合关系（DAG / Sequence）

- 期望结果（Assert）

- 可观测性（Trace / Metric）

- 报告（Allure）

```shell
┌───────────────────────────────────────────┐
│               pytest Runner                │
│                                           │
│  ┌───────────────┐   ┌─────────────────┐ │
│  │ Testcase DSL  │ → │ Execution Engine │ │
│  └───────────────┘   └────────┬────────┘ │
│                               │          │
│         ┌──────────────┬──────┴──────┐   │
│         │              │             │   │
│   Command Module   Chaos Module   Assert Module
│         │              │             │
│         └──────────────┴──────┬──────┘
│                                │
│        ┌─────────────── Observability ───────────────┐
│        │                                              │
│   OpenTelemetry Trace → Tempo         Metrics → Prometheus
│        │                                              │
│        └──────────────────┬──────────────────────────┘
│                           │
│                     Allure Report
└───────────────────────────────────────────┘
```

| 模块   | 职责                            |
| ---- | ----------------------------- |
| 用例模块 | 定义「**做什么 + 期望什么**」            |
| 故障模块 | 定义「**破坏什么 + 如何恢复**」           |
| 执行引擎 | 统一调度 Command / Chaos / Assert |
| 可观测  | Trace / Metric / Allure       |

## 核心抽象模型

### command

最小可执行单元。

- 配置接口

```shell
commands:
  - name: show_cluster
    run: shell
    cmd: "xxx cluster show"
    description: "cluster show"
    expect:
      contains: ["primary"]

    hooks:
      before: []
      after: []
      on_fail: []
```

- 抽象接口

```python
class Command:
    def execute(self, context) -> Result
```

### 原子故障（chaos）

也是一种命令，但语义是“破坏”。

```command
chaos:
  - name: kill_process
    run: shell
    cmd: "pkill -9 postgres"
    recover:
      cmd: "systemctl start postgres"
    duration: 10
```

```python
也是一种命令，但语义是“破坏”
```

### 测试用例

测试用例本身不关心“怎么执行”。

```yaml
testcases:
  - name: primary_failover
    steps:
      - show_cluster
      - kill_process
      - show_cluster
    assert:
      eventually:
        contains: ["new_primary"]
```

### 执行上下文

```yaml
context = {
  "nodes": [...],
  "env": {...},
  "params": {...},   # matrix 注入
}
```