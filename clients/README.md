# Clients —— 用户面客户端

> 仅在 Sprint 7 落地。当前为占位。

## 组件

| 名称 | 语言 | 状态 |
| --- | --- | --- |
| CLI (`clients/cli`) | Python | Sprint 7 |
| MCP Server (`clients/mcp_server`) | Python | Sprint 7 |

## 设计原则

- 永远只调用 gRPC / HTTP 接口
- 不直连数据库 / 缓存 / 消息队列
- 跨平台（macOS / Linux / Windows）
- 自举：CLI 安装自身 / 升级自身

## CLI 命令矩阵

```
aitest plan submit --suite cases/ --concurrency 100
aitest case list --tag smoke --json
aitest result get <result-id>
aitest farm ls --json
aitest plugin ls
```

## MCP Server 暴露给 AI Agent 的工具

```python
@mcp.tool()
async def tcm_search_cases(tags: list[str]) -> list[Case]: ...
@mcp.tool()
async def exf_submit_plan(case_ids: list[str]) -> PlanHandle: ...
@mcp.tool()
async def trm_get_flaky(window: int = 50) -> list[FlakyCase]: ...
```
