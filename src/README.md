## src 目录说明

`src` 是 oneTear 的主代码目录，包含可直接运行的最小框架实现。

### 本地运行

```bash
pytest -q
python main.py
```

### 关键入口

1. `main.py`：按 `conf/testcases` 加载并执行全部用例。
2. `core/engine.py`：核心调度逻辑（step 执行、hooks、observer 事件）。
3. `command/registry.py`：命令配置加载与命令对象构建。
