# OneTear 测试执行框架架构设计与实现文档

## 1. 设计目标

OneTear 是一个 **YAML 配置驱动的自动化测试执行框架**，目标是：

* 用 **声明式 YAML** 描述测试用例、步骤、矩阵参数
* 通过 **Command 抽象** 复用底层执行逻辑（shell / python / sql 等）
* 提供 **统一执行引擎**，支持 hooks / steps / context 渲染
* 通过 **Observer 机制** 解耦日志、Allure、Tracing 等能力
* 能无缝集成 **pytest + Allure**，同时支持独立运行

适用场景：

* 数据库（PostgreSQL / repmgr / HAProxy）集成测试
* 运维/中间件自动化验证
* Chaos / 故障注入测试

---

## 2. 总体架构

```
+-------------------+
|   YAML Testcase   |
|  (conf/testcases) |
+---------+---------+
          |
          v
+--------------------+       +--------------------+
| TestCaseRegistry   |-----> | CommandRegistry    |
| - load_dir()       |       | - load_dir()       |
+---------+----------+       +----------+---------+
          |                                 |
          v                                 v
+------------------------------------------------+
|              ExecutionEngine                   |
|------------------------------------------------|
| 1. before_hooks                                 |
| 2. steps -> Runner -> Command                  |
| 3. after_hooks                                  |
+-------------------+----------------------------+
                    |
                    v
        +-----------------------------+
        |         Observers            |
        | Logger / Allure / Trace      |
        +-----------------------------+
```

---

## 3. 核心模块说明

### 3.1 CommandRegistry（命令注册中心）

**职责**：

* 加载 `conf/commands/*.yaml`
* 维护 command name → Command 定义的映射
* 供 ExecutionEngine / Runner 查找并执行

**Command 抽象模型**：

```yaml
- name: create_file
  type: shell
  cmd: "touch {{filename}}"
  redo_cmd: "touch {{filename}}"
  undo_cmd: "rm -f {{filename}}"
  description: "创建文件"
```

**核心能力**：

* 占位符渲染（基于 context）
* redo / undo 支持（为失败回滚、重试准备）

---

### 3.2 TestCaseRegistry（用例注册中心）

**职责**：

* 加载 `conf/testcases/*.yaml`
* 每个 YAML 文件定义一个 TestCase
* 支持 matrix / context 扩展

**TestCase 结构示例**：

```yaml
name: file_operations_test
matrix:
  pg_version: [15]
  node_count: [3]
context:
  filename: "/tmp/demo.txt"
steps:
  - name: create_file
    cmd_ref: create_file
  - name: delete_file
    cmd_ref: delete_file
```

**expand() 机制**：

* 将 matrix 笛卡尔积展开为多个 context
* 每个 context 对应一次 testcase 执行

---

### 3.3 ExecutionEngine（执行引擎）

**职责**：

* 测试用例的生命周期管理
* 统一调度 hooks / steps
* 通知 Observer

**执行流程**：

```text
run_testcase(case, context)
 ├── notify testcase_start
 ├── run before_hooks
 ├── for step in steps:
 │     ├── notify step_start
 │     ├── Runner.run(step)
 │     ├── notify step_end
 ├── run after_hooks
 └── notify testcase_end
```

**关键设计点**：

* Engine 不关心 command 细节
* 所有执行统一交给 Runner

---

### 3.4 Runner（统一执行入口）

**职责**：

* 根据 command.type 调度不同执行器
* shell / python / sql / http 可插拔

```python
class Runner:
    def run(self, command, context):
        if command.type == "shell":
            ...
```

**设计收益**：

* 后续支持 chaos / fault 注入
* 与 pytest 执行模型天然兼容

---

### 3.5 Observer 机制

**设计模式**：Observer（观察者模式）

```python
class Observer:
    def testcase_start(self, case, ctx): pass
    def step_start(self, step): pass
    def step_end(self, step, result): pass
```

#### 已实现 Observer

* `LoggerObserver`：

  * 控制台 / 文件日志
* `AllureObserver`：

  * 对接 allure lifecycle
  * step / attachment / status

**优势**：

* 与执行逻辑完全解耦
* 可叠加多个 observer

---

## 4. 执行入口说明（main.py）

```python
cmds = CommandRegistry()
cmds.load_dir("conf/commands")

cases = TestCaseRegistry()
cases.load_dir("conf/testcases")

observers = [LoggerObserver(), AllureObserver()]
engine = ExecutionEngine(observers, cmds)

for case in cases.all():
    for ctx in case.expand():
        engine.run_testcase(case, ctx)
```

### 执行顺序总结

1. 加载 command 定义
2. 加载 testcase 定义
3. 构建 observer 链
4. Engine 调度 testcase × context

---

## 5. 与 pytest / Allure 集成设计

### pytest 模式

* 每个 YAML testcase 映射为一个 pytest test
* Engine.run_testcase 在 pytest test 内调用
* AllureObserver 使用 `allure.step` / `attach`

### 优势

* pytest 负责：

  * 并发
  * 重试
  * 失败统计
* OneTear 负责：

  * 领域建模
  * 执行语义

---

## 6. 扩展设计

### 6.1 Chaos / Fault 支持

```yaml
chaos:
  - type: kill_process
    target: postgres
```

由 Runner 调度 chaos executor

---

### 6.2 DAG / 条件执行（规划）

```yaml
steps:
  - name: step1
  - name: step2
    when: "step1 == success"
```

---

## 7. 设计原则总结

* **配置驱动** > 代码驱动
* **命令即能力**（Command as Capability）
* **执行与观测解耦**
* **最小核心，最大扩展**

---

## 8. 适用场景回顾

* PostgreSQL / repmgr 集群验证
* HAProxy 主备切换测试
* 运维脚本回归测试
* Chaos Engineering

---

> 该架构适合持续演进为：
>
> * 数据库专用测试 DSL
> * 运维验证平台执行内核
> * Chaos + 验证一体化框架
