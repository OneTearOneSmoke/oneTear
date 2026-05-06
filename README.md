# oneTear

一个面向 YAML 用例编排的轻量自动化测试框架原型。

## 当前完成度

| 能力项 | 状态 | 说明 |
| --- | --- | --- |
| 命令 DSL（Shell） | done | 支持 Jinja2 变量渲染，支持 `do/redo/undo` 模板 |
| 命令 DSL（SQL/Postgres） | done | 已接入统一执行协议，按需导入 `psycopg2` |
| TestCase Loader | done | 从 `conf/testcases/*.yaml` 加载 case |
| Matrix 参数展开 | done | 支持笛卡尔积展开多组执行上下文 |
| 执行引擎（串行） | done | 顺序执行 step，失败回滚，支持 hooks |
| 断言 contains/eventually | done | `eventually` 支持 `timeout/interval/max_retries`，可通过 `redo_cmd` 重试 |
| 日志观察器 | done | 控制台 + 文件日志 |
| pytest 集成 | done | 有可运行的集成测试 |
| Allure 观察器 | partial | 主入口默认尝试启用，报告配置与验证链路仍待完善 |
| 并行调度 / DAG / Node Selector / Cache / Trace / Metrics | planned | 尚未在代码中实现 |

## 项目结构

```text
src/
  command/        # 命令定义与注册（shell/sql）
  core/           # 引擎、上下文、loader
  domain/         # TestCase/Step/Hooks 模型
  assertor/       # 断言实现
  observer/       # 观察器（logger/allure）
  conf/           # 命令与测试用例配置
  cases/          # pytest 集成测试
  main.py         # 本地执行入口
```

## 快速开始

1. 进入源码目录

```bash
cd src
```

2. 安装依赖（任选其一）

```bash
pip install -e .
```

3. 运行测试

```bash
pytest -q
```

4. 执行示例用例

```bash
python main.py
```

运行成功后可在 `src/logs/` 下看到按 testcase 分组的日志文件。

## 配置示例

- 命令定义：`src/conf/command/test.yaml`
- SQL 命令定义：`src/conf/command/sql/postgres.yaml`
- 用例定义：`src/conf/testcases/file_ops.yaml`

### 配置兼容性

1. 命令目录同时支持：
- `conf/command/**`（当前主路径）
- `conf/commands/*.yaml`（兼容 new_frame 路径）
2. step 命令引用同时支持 `cmd_ref` 与 `cmd`（`cmd` 作为命令名别名）。
3. hooks 同时支持：
- 字符串 shell 命令（例如 `"echo start"`）
- 字典写法 `cmd_ref: xxx`（引用命令注册表）
- 字典写法 `cmd: "echo start"`（内联 shell 命令）

### Step 级重试策略

`eventually` 的重试参数可以写在断言中，也可以写在 step 的 `retry` 字段中。  
优先级：`step.retry` > `ExecutionEngine.retry_defaults` > 断言内默认值。

```yaml
steps:
  - name: list_file
    cmd_ref: list_file
    retry:
      timeout: 5
      interval: 0.5
      max_retries: 5
    expect:
      eventually:
        contains: "{{filename}}"
```

## 已知限制

1. SQL 命令要求上下文中存在 `pg_host/pg_user/pg_password/pg_db`。
2. `redo` 依赖命令定义中的 `redo_cmd`，未配置时会回退到主命令模板。
3. 文档中的高级能力（并行、DAG、指标、链路追踪）仍是规划项。

## 下一步建议

1. 设计 DAG 调度模型（拓扑排序 + 节点级失败策略）。
2. 接入 OpenTelemetry/Prometheus，补齐 Trace/Metrics。
3. 增加 SQL 集成测试（可选使用临时 Postgres 容器）。
