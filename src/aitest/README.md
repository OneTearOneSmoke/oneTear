# aitest · AI 时代的极简测试框架与用例管理

> 与仓库原有 `OneTear`（运维/中间件集成测试）并存，**独立子包**。重点解决
> “AI 写的代码 / 模型输出，如何用一套简单、简洁、可扩展的方式验证”。

## 1. 一句话

```yaml
# cases/sort_correctness.yaml
id: ai.sort.correctness
params: { fn: [bubble, quick], input: [[3,1,2], [5,5,1,2]] }
run:    { cmd: python.eval, args: { import: aitest_demo.sort, call: "{{ params.fn }}", with: "{{ params.input }}" } }
asserts:
  - eq: { value: "{{ run.python.eval.result }}", expect: "{{ params.input | sorted }}" }
```

```bash
cd src && python3 -m aitest run --suite cases --junit report.xml --json-report report.json
```

## 2. 架构（5 个内核 + 4 类扩展点）

```
Case ──> Suite ──> Runner ──> Observer
                │
                └─> Registry (commands / assertors / providers / observers)
```

| 内核 | 作用 |
| --- | --- |
| `Case`   | 一条用例：id / tags / params(矩阵) / run / asserts / record / fixture |
| `Suite`  | 用例集合：load_dir / filter(tags) / search / expand(矩阵) / tag_index / to_json |
| `Registry` | 注册中心：command / assertor / provider / observer |
| `Runner` | 执行：fixture → run → asserts → teardown → observer → 失败回放 |
| `Loader` | YAML/JSON → Suite |

扩展点见 `aitest.commands.* / assertors.* / observers.* / providers.*`。

## 3. 内置能力

Commands: `shell.run / python.eval / http.request / llm.query / ast.diff / builtin.{make_tmp,clean_tmp,seed_rng,sleep}`
Assertors: `eq / ne / contains / regex / truthy / json_schema / embedding_sim / llm_judge / ast_struct / property / eventually`
Observers: `logger / junit / json_report / recorder`
Providers: `echo`（默认）、`openai`（兼容 OpenAI / DeepSeek / vLLM，通过 `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` 配置）

## 4. CLI

```bash
aitest run    --suite cases [--tag t1] [--not-tag flaky] [--only id] [--concurrency N]
              [--junit report.xml] [--json-report report.json] [--recorder replays/]
aitest ls     --suite cases [--tag t1]
aitest show   --suite cases <id>
aitest lint   --suite cases
aitest diff   <suiteA> <suiteB>
aitest new    --out cases/x.yaml [--id ai.x] [--name "..."]
```

## 5. 用例管理（这是和传统测试框架最大的区别）

- **用例即数据**：YAML/JSON，能进 git、能被 LLM 读写、能 code review。
- **矩阵展开**：`params` 里只要是 `list`，自动笛卡尔积。
- **失败即数据**：`record.on_failure: true` 把失败的输入/输出/上下文写到 `replays/`，可直接 `aitest new` 派生新用例。
- **标签检索**：`tag_index()` 给 LLM 当工具，LLM 也能 `aitest ls --tag smoke`。
- **套件 diff**：`aitest diff` 对比两套用例，找出差异（用于门禁 / 回归）。
- **LLM 协作**：`llm_judge` 让模型当评审；`llm.query` 让用例直接调模型；未来可让 LLM 在 CI 失败时生成新 case。

## 6. 一个最小可运行的 AI 验证示例

```python
# 假设 AI 生成了 ai/sort/bubble.py，调用 aitest_demo.sort.bubble
# 用 aitest_demo.sort.bubble 验证其行为等价于 sorted()
```

详见 `cases/sort_correctness.yaml`（pass）+ `cases/buggy_sort_must_fail.yaml`（故意失败，验证框架能抓到）。
